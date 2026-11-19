import logging
from datetime import date, datetime
from typing import Optional

from aiogram import Bot

from app.repositories import reminder_repo
from app.utils.dt import now
from app.utils.texts import REMINDER_NOTIFICATION

logger = logging.getLogger(__name__)

REMINDER_DAYS_BEFORE = (7, 3, 1)


def _parse_remind_date(raw: str, today: date) -> Optional[date]:
    """Разобрать дату в формате ДД.ММ.ГГГГ или ДД.ММ (без года — ежегодное событие)."""
    raw = raw.strip()
    has_year = raw.count(".") == 2
    fmt = "%d.%m.%Y" if has_year else "%d.%m"
    try:
        parsed = datetime.strptime(raw, fmt)
    except ValueError:
        return None

    if has_year:
        return parsed.date()

    candidate = date(today.year, parsed.month, parsed.day)
    if candidate < today:
        candidate = date(today.year + 1, parsed.month, parsed.day)
    return candidate


async def check_and_send_reminders(bot: Bot) -> None:
    """Проверить все активные напоминания и уведомить клиентов за 7, 3 и 1 день."""
    today = now().date()
    reminders = await reminder_repo.list_all_active()

    for reminder in reminders:
        target_date = _parse_remind_date(reminder["remind_date"], today)
        if target_date is None:
            continue

        days_left = (target_date - today).days

        if days_left in REMINDER_DAYS_BEFORE:
            text = REMINDER_NOTIFICATION.format(
                days=days_left,
                occasion=reminder["occasion"],
                person_name=reminder["person_name"],
            )
            try:
                await bot.send_message(reminder["telegram_id"], text)
            except Exception:
                logger.exception(
                    "Не удалось отправить напоминание клиенту %s", reminder["telegram_id"]
                )
        elif days_left < 0 and reminder["remind_date"].count(".") == 2:
            # Разовое событие с указанным годом уже прошло — деактивируем
            await reminder_repo.deactivate(reminder["id"])
