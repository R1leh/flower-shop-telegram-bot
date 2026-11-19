import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _parse_admin_ids(raw: str) -> list[int]:
    result = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            result.append(int(part))
    return result


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: list[int] = field(default_factory=list)
    timezone: str = "Asia/Yekaterinburg"
    db_path: str = "data/buton.db"
    photos_dir: str = "data/photos"
    backup_dir: str = "backup"
    max_photo_size_mb: int = 5
    shop_phone: str = "+7 (900) 000-00-00"
    manager_reminder_hours: int = 2
    backup_keep_count: int = 30
    backup_time: str = "03:00"
    reminder_check_time: str = "09:00"

    @property
    def max_photo_size_bytes(self) -> int:
        return self.max_photo_size_mb * 1024 * 1024


def load_config() -> Config:
    return Config(
        bot_token=os.getenv("BOT_TOKEN", ""),
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),
        timezone=os.getenv("TIMEZONE", "Asia/Yekaterinburg"),
        db_path=os.getenv("DB_PATH", "data/buton.db"),
        photos_dir=os.getenv("PHOTOS_DIR", "data/photos"),
        backup_dir=os.getenv("BACKUP_DIR", "backup"),
        max_photo_size_mb=int(os.getenv("MAX_PHOTO_SIZE_MB", "5")),
        shop_phone=os.getenv("SHOP_PHONE", "+7 (900) 000-00-00"),
        manager_reminder_hours=int(os.getenv("MANAGER_REMINDER_HOURS", "2")),
        backup_keep_count=int(os.getenv("BACKUP_KEEP_COUNT", "30")),
        backup_time=os.getenv("BACKUP_TIME", "03:00"),
        reminder_check_time=os.getenv("REMINDER_CHECK_TIME", "09:00"),
    )


config = load_config()
