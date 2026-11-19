from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.backup_service import create_backup
from app.utils.config import config
from app.utils.dt import TZ


def register(scheduler: AsyncIOScheduler) -> None:
    """Ежедневное резервное копирование БД в configured время."""
    hour, minute = (int(part) for part in config.backup_time.split(":"))
    scheduler.add_job(
        create_backup,
        CronTrigger(hour=hour, minute=minute, timezone=TZ),
        id="daily_backup",
        replace_existing=True,
    )
