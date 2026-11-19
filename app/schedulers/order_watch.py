import logging
from datetime import timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.repositories import client_repo, order_repo
from app.utils.config import config
from app.utils.dt import now
from app.utils.texts import ORDER_REMINDER_ADMIN_TEMPLATE

logger = logging.getLogger(__name__)

CHECK_INTERVAL_MINUTES = 30


async def check_stale_orders(bot: Bot) -> None:
    """Напомнить администраторам о заявках, которые дольше лимита висят в статусе 'new'."""
    threshold_iso = (now() - timedelta(hours=config.manager_reminder_hours)).isoformat(
        timespec="seconds"
    )
    orders = await order_repo.get_stale_new_orders(threshold_iso)

    for order in orders:
        client = await client_repo.get(order.telegram_id)
        text = ORDER_REMINDER_ADMIN_TEMPLATE.format(
            order_id=order.id,
            hours=config.manager_reminder_hours,
            bouquet_name=order.bouquet_name or "—",
            client_name=(client.full_name if client and client.full_name else "—"),
            client_phone=(client.phone if client and client.phone else "—"),
        )
        for admin_id in config.admin_ids:
            try:
                await bot.send_message(admin_id, text)
            except Exception:
                logger.exception("Не удалось отправить напоминание админу %s", admin_id)
        await order_repo.mark_manager_reminded(order.id)


def register(scheduler: AsyncIOScheduler, bot: Bot) -> None:
    scheduler.add_job(
        check_stale_orders,
        IntervalTrigger(minutes=CHECK_INTERVAL_MINUTES),
        args=[bot],
        id="order_watch",
        replace_existing=True,
    )
