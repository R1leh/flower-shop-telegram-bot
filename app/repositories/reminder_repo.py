from typing import TypedDict

from app.database.connection import get_connection


class ReminderRow(TypedDict):
    id: int
    telegram_id: int
    person_name: str
    remind_date: str
    occasion: str
    is_active: int


async def create(telegram_id: int, person_name: str, remind_date: str, occasion: str) -> int:
    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            INSERT INTO reminders (telegram_id, person_name, remind_date, occasion, is_active)
            VALUES (?, ?, ?, ?, 1)
            """,
            (telegram_id, person_name, remind_date, occasion),
        )
        await conn.commit()
        return cursor.lastrowid


async def list_active_for_client(telegram_id: int) -> list[ReminderRow]:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM reminders WHERE telegram_id = ? AND is_active = 1 ORDER BY id DESC",
            (telegram_id,),
        )
        rows = await cursor.fetchall()
        return [ReminderRow(**dict(row)) for row in rows]


async def list_all_active() -> list[ReminderRow]:
    async with get_connection() as conn:
        cursor = await conn.execute("SELECT * FROM reminders WHERE is_active = 1")
        rows = await cursor.fetchall()
        return [ReminderRow(**dict(row)) for row in rows]


async def deactivate(reminder_id: int) -> None:
    async with get_connection() as conn:
        await conn.execute(
            "UPDATE reminders SET is_active = 0 WHERE id = ?", (reminder_id,)
        )
        await conn.commit()
