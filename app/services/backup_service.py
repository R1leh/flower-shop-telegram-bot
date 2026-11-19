import asyncio
import logging
import shutil
from pathlib import Path

from app.utils.config import config
from app.utils.dt import now

logger = logging.getLogger(__name__)


async def create_backup() -> Path:
    """Скопировать БД в backup/ с отметкой времени и удалить копии сверх лимита."""
    db_path = Path(config.db_path)
    backup_dir = Path(config.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{db_path.stem}_{timestamp}.db"

    await asyncio.to_thread(shutil.copy2, db_path, backup_path)
    logger.info("Создана резервная копия БД: %s", backup_path)

    await asyncio.to_thread(_cleanup_old_backups, backup_dir, db_path.stem)
    return backup_path


def _cleanup_old_backups(backup_dir: Path, stem: str) -> None:
    backups = sorted(
        backup_dir.glob(f"{stem}_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old_backup in backups[config.backup_keep_count :]:
        old_backup.unlink(missing_ok=True)
        logger.info("Удалена устаревшая резервная копия: %s", old_backup)
