"""Единая точка получения текущего времени в часовом поясе магазина (UTC+5)."""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.utils.config import config

TZ = ZoneInfo(config.timezone)


def now() -> datetime:
    return datetime.now(TZ)


def now_iso() -> str:
    return now().isoformat(timespec="seconds")
