import os
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

from app.utils.config import config

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


@asynccontextmanager
async def get_connection():
    """Открыть новое подключение к SQLite с разумными настройками.

    Подключение на каждый вызов проще и надёжнее, чем общий объект на всё
    приложение: SQLite сам сериализует доступ, а WAL позволяет читать и
    писать одновременно без блокировок "database is locked" на слабом сервере.
    """
    conn = await aiosqlite.connect(config.db_path)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON")
    await conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
    finally:
        await conn.close()


async def init_db() -> None:
    """Создать каталоги данных и применить схему БД (idempotent)."""
    os.makedirs(Path(config.db_path).parent, exist_ok=True)
    os.makedirs(config.photos_dir, exist_ok=True)
    os.makedirs(config.backup_dir, exist_ok=True)

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    async with get_connection() as conn:
        await conn.executescript(schema_sql)
        await conn.commit()
