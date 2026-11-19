from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.schedulers import backup, order_watch, reminders
from app.utils.dt import TZ


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Создать планировщик и зарегистрировать все фоновые задачи."""
    scheduler = AsyncIOScheduler(timezone=TZ)
    backup.register(scheduler)
    reminders.register(scheduler, bot)
    order_watch.register(scheduler, bot)
    return scheduler
