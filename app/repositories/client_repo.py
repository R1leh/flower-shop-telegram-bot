from typing import Optional

from app.database.connection import get_connection
from app.models.client import Client


async def get(telegram_id: int) -> Optional[Client]:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM clients WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cursor.fetchone()
        return Client.from_row(row) if row else None


async def accept_privacy(telegram_id: int, accepted_at: str) -> None:
    """Создать клиента (если его ещё нет) и зафиксировать согласие на ПДн."""
    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO clients (telegram_id, privacy_accepted, privacy_accepted_at, registered_at)
            VALUES (?, 1, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                privacy_accepted = 1,
                privacy_accepted_at = excluded.privacy_accepted_at
            """,
            (telegram_id, accepted_at, accepted_at),
        )
        await conn.commit()


async def complete_registration(telegram_id: int, full_name: str, phone: str) -> None:
    async with get_connection() as conn:
        await conn.execute(
            "UPDATE clients SET full_name = ?, phone = ? WHERE telegram_id = ?",
            (full_name, phone, telegram_id),
        )
        await conn.commit()


async def update_profile(telegram_id: int, **fields) -> None:
    """Обновить произвольные поля профиля клиента."""
    if not fields:
        return
    allowed = {"full_name", "phone", "birth_date", "delivery_address", "is_vip"}
    columns = [key for key in fields if key in allowed]
    if not columns:
        return
    set_clause = ", ".join(f"{col} = ?" for col in columns)
    values = [fields[col] for col in columns] + [telegram_id]
    async with get_connection() as conn:
        await conn.execute(
            f"UPDATE clients SET {set_clause} WHERE telegram_id = ?", values
        )
        await conn.commit()


async def count_total() -> int:
    async with get_connection() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM clients")
        row = await cursor.fetchone()
        return row[0]


async def count_registered_since(since_iso: str) -> int:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM clients WHERE registered_at >= ?", (since_iso,)
        )
        row = await cursor.fetchone()
        return row[0]


async def get_all_telegram_ids() -> list[int]:
    async with get_connection() as conn:
        cursor = await conn.execute("SELECT telegram_id FROM clients")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]
