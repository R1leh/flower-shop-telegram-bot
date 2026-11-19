from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.keyboards.admin_kb import order_status_kb, orders_pagination_kb
from app.models.order import Order
from app.repositories import order_repo
from app.services import order_service
from app.utils.constants import FINAL_STATUSES, ORDER_STATUS_LABELS, ORDERS_PAGE_SIZE

router = Router(name="admin_orders")


def _format_order(order: Order) -> str:
    lines = [
        ORDER_STATUS_LABELS.get(order.status, order.status),
        f"<b>Заказ #{order.id}</b>",
        f"💐 Букет: {order.bouquet_name or '—'}",
        f"💰 Сумма: {order.total_price:.0f} ₽" if order.total_price else "",
        f"👤 Получатель: {order.recipient_name}, {order.recipient_phone}",
        f"📍 Адрес: {order.delivery_address}",
        f"🕐 Время доставки: {order.delivery_time}",
    ]
    if order.comment:
        lines.append(f"💬 Комментарий: {order.comment}")
    lines.append(f"🕓 Создан: {order.created_at}")
    return "\n".join(line for line in lines if line)


async def _show_orders_page(message: Message, page: int) -> None:
    total = await order_repo.count_active()
    if total == 0:
        await message.answer("Активных заказов нет ✅")
        return

    orders = await order_repo.get_active(page=page, page_size=ORDERS_PAGE_SIZE)
    if not orders:
        await message.answer("Больше заказов нет.")
        return

    await message.answer(f"📋 <b>Активные заказы</b> (стр. {page + 1}):")
    for order in orders:
        await message.answer(_format_order(order), reply_markup=order_status_kb(order.id, order.status))

    has_prev = page > 0
    has_next = (page + 1) * ORDERS_PAGE_SIZE < total
    if has_prev or has_next:
        await message.answer("Навигация:", reply_markup=orders_pagination_kb(page, has_prev, has_next))


@router.message(Command("orders"))
async def cmd_orders(message: Message) -> None:
    await _show_orders_page(message, 0)


@router.callback_query(F.data == "adm_orders")
async def cb_orders(callback: CallbackQuery) -> None:
    await _show_orders_page(callback.message, 0)
    await callback.answer()


@router.callback_query(F.data.startswith("adm_orders_page:"))
async def cb_orders_page(callback: CallbackQuery) -> None:
    page = int(callback.data.split(":", 1)[1])
    await _show_orders_page(callback.message, page)
    await callback.answer()


@router.callback_query(F.data.startswith("adm_status:"))
async def cb_change_status(callback: CallbackQuery, bot: Bot) -> None:
    _, order_id_raw, new_status = callback.data.split(":")
    order_id = int(order_id_raw)

    success = await order_service.change_status(bot, order_id, new_status, changed_by="admin")
    if not success:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    label = ORDER_STATUS_LABELS.get(new_status, new_status)
    new_markup = None if new_status in FINAL_STATUSES else order_status_kb(order_id, new_status)
    await callback.message.edit_text(f"{callback.message.text}\n\n➡️ {label}", reply_markup=new_markup)
    await callback.answer("Статус обновлён ✅")
