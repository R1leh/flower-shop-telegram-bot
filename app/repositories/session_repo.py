from typing import Optional

from app.database.connection import get_connection
from app.utils.dt import now_iso


async def create(telegram_id: int) -> int:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "INSERT INTO selection_sessions (telegram_id, started_at, completed) VALUES (?, ?, 0)",
            (telegram_id, now_iso()),
        )
        await conn.commit()
        return cursor.lastrowid


async def update(session_id: int, **fields) -> None:
    allowed = {
        "occasion",
        "budget_from",
        "budget_to",
        "season",
        "recipient",
        "color_preference",
        "flower_preferences",
        "mood",
        "result_bouquet_id",
    }
    columns = [key for key in fields if key in allowed]
    if not columns:
        return
    set_clause = ", ".join(f"{col} = ?" for col in columns)
    values = [fields[col] for col in columns] + [session_id]
    async with get_connection() as conn:
        await conn.execute(
            f"UPDATE selection_sessions SET {set_clause} WHERE id = ?", values
        )
        await conn.commit()


async def mark_completed(session_id: int, result_bouquet_id: Optional[int]) -> None:
    async with get_connection() as conn:
        await conn.execute(
            "UPDATE selection_sessions SET completed = 1, result_bouquet_id = ? WHERE id = ?",
            (result_bouquet_id, session_id),
        )
        await conn.commit()


async def count_total_in_period(start_iso: str, end_iso: str) -> int:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM selection_sessions WHERE started_at BETWEEN ? AND ?",
            (start_iso, end_iso),
        )
        row = await cursor.fetchone()
        return row[0]


async def count_completed_in_period(start_iso: str, end_iso: str) -> int:
    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT COUNT(*) FROM selection_sessions
            WHERE started_at BETWEEN ? AND ? AND completed = 1
            """,
            (start_iso, end_iso),
        )
        row = await cursor.fetchone()
        return row[0]
