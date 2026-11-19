import logging
from typing import Optional

from aiogram import Bot

from app.keyboards.admin_kb import new_order_kb
from app.models.bouquet import Bouquet
from app.models.order import Order
from app.repositories import bouquet_repo, client_repo, history_repo, order_repo
from app.services import loyalty_service
from app.utils.config import config
from app.utils.constants import CANCELLABLE_STATUSES, ORDER_STATUS_CLIENT_TEXT
from app.utils.dt import now_iso
from app.utils.texts import (
    LOYALTY_LEVEL_UP,
    NEW_ORDER_ADMIN_TEMPLATE,
    ORDER_CANCELLED_BY_CLIENT,
    ORDER_CANNOT_CANCEL,
)

logger = logging.getLogger(__name__)


async def create_order(
    bot: Bot,
    telegram_id: int,
    bouquet: Bouquet,
    recipient_name: str,
    recipient_phone: str,
    delivery_address: str,
    delivery_time: str,
    comment: Optional[str],
) -> int:
    """Создать заказ, увеличить счётчик заказов букета и уведомить администраторов."""
    order_id = await order_repo.create(
        telegram_id=telegram_id,
        bouquet_id=bouquet.id,
        bouquet_name=bouquet.name,
        recipient_name=recipient_name,
        recipient_phone=recipient_phone,
        delivery_address=delivery_address,
        delivery_time=delivery_time,
        comment=comment,
        total_price=bouquet.price,
    )
    await bouquet_repo.increment_orders_count(bouquet.id)
    await _notify_admins_new_order(
        bot,
        order_id,
        telegram_id,
        bouquet,
        recipient_name,
        recipient_phone,
        delivery_address,
        delivery_time,
        comment,
    )
    return order_id


async def _notify_admins_new_order(
    bot: Bot,
    order_id: int,
    telegram_id: int,
    bouquet: Bouquet,
    recipient_name: str,
    recipient_phone: str,
    delivery_address: str,
    delivery_time: str,
    comment: Optional[str],
) -> None:
    client = await client_repo.get(telegram_id)
    text = NEW_ORDER_ADMIN_TEMPLATE.format(
        order_id=order_id,
        client_name=(client.full_name if client and client.full_name else "—"),
        client_phone=(client.phone if client and client.phone else "—"),
        bouquet_name=bouquet.name,
        price=bouquet.price,
        recipient_name=recipient_name,
        recipient_phone=recipient_phone,
        delivery_address=delivery_address,
        delivery_time=delivery_time,
        comment=comment or "—",
    )
    for admin_id in config.admin_ids:
        try:
            await bot.send_message(admin_id, text, reply_markup=new_order_kb(order_id))
        except Exception:
            logger.exception("Не удалось отправить уведомление админу %s", admin_id)


async def change_status(bot: Bot, order_id: int, new_status: str, changed_by: str) -> bool:
    """Сменить статус заказа, уведомить клиента и обработать побочные эффекты."""
    order = await order_repo.get(order_id)
    if order is None:
        return False

    await order_repo.update_status(order_id, new_status, changed_by)

    template = ORDER_STATUS_CLIENT_TEXT.get(new_status)
    if template:
        text = template.format(order_id=order_id, shop_phone=config.shop_phone)
        try:
            await bot.send_message(order.telegram_id, text)
        except Exception:
            logger.exception("Не удалось уведомить клиента %s", order.telegram_id)

    if new_status == "completed":
        await _handle_completed(bot, order)

    return True


async def _handle_completed(bot: Bot, order: Order) -> None:
    bouquet = await bouquet_repo.get(order.bouquet_id) if order.bouquet_id else None
    await history_repo.add(
        telegram_id=order.telegram_id,
        bouquet_id=order.bouquet_id,
        bouquet_name=order.bouquet_name,
        occasion=bouquet.occasion if bouquet else None,
        season=bouquet.season if bouquet else None,
        price=order.total_price or 0,
        ordered_at=now_iso(),
    )

    new_level = await loyalty_service.register_completed_order(
        order.telegram_id, order.total_price or 0
    )
    if new_level:
        try:
            await bot.send_message(
                order.telegram_id, LOYALTY_LEVEL_UP.format(level=new_level)
            )
        except Exception:
            logger.exception("Не удалось уведомить клиента %s о повышении уровня", order.telegram_id)


async def cancel_order_by_client(bot: Bot, order_id: int, telegram_id: int) -> tuple[bool, str]:
    """Попытаться отменить заказ по запросу клиента.

    Возвращает (успех, текст сообщения для клиента).
    """
    order = await order_repo.get(order_id)
    if order is None or order.telegram_id != telegram_id:
        return False, "Заказ не найден."

    if order.status not in CANCELLABLE_STATUSES:
        return False, ORDER_CANNOT_CANCEL.format(order_id=order_id, shop_phone=config.shop_phone)

    await change_status(bot, order_id, "cancelled", changed_by="client")
    return True, ORDER_CANCELLED_BY_CLIENT.format(order_id=order_id)
