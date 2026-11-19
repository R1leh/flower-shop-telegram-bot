from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.reminder_service import check_and_send_reminders
from app.utils.config import config
from app.utils.dt import TZ


def register(scheduler: AsyncIOScheduler, bot: Bot) -> None:
    """Ежедневная проверка напоминаний о важных датах клиентов."""
    hour, minute = (int(part) for part in config.reminder_check_time.split(":"))
    scheduler.add_job(
        check_and_send_reminders,
        CronTrigger(hour=hour, minute=minute, timezone=TZ),
        args=[bot],
        id="daily_reminders",
        replace_existing=True,
    )
