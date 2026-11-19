from typing import Optional, TypedDict

from app.database.connection import get_connection
from app.utils.constants import DEFAULT_LOYALTY_LEVEL


class LoyaltyInfo(TypedDict):
    telegram_id: int
    points: int
    total_spent: float
    level: str


async def get(telegram_id: int) -> LoyaltyInfo:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM loyalty WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cursor.fetchone()
        if row:
            return LoyaltyInfo(**dict(row))
        await conn.execute(
            "INSERT INTO loyalty (telegram_id, points, total_spent, level) VALUES (?, 0, 0, ?)",
            (telegram_id, DEFAULT_LOYALTY_LEVEL),
        )
        await conn.commit()
        return LoyaltyInfo(
            telegram_id=telegram_id, points=0, total_spent=0, level=DEFAULT_LOYALTY_LEVEL
        )


async def add_points_and_spent(telegram_id: int, points: int, amount: float) -> None:
    await get(telegram_id)  # гарантируем наличие строки
    async with get_connection() as conn:
        await conn.execute(
            """
            UPDATE loyalty
            SET points = points + ?, total_spent = total_spent + ?
            WHERE telegram_id = ?
            """,
            (points, amount, telegram_id),
        )
        await conn.commit()


async def set_level(telegram_id: int, level: str) -> None:
    await get(telegram_id)
    async with get_connection() as conn:
        await conn.execute(
            "UPDATE loyalty SET level = ? WHERE telegram_id = ?", (level, telegram_id)
        )
        await conn.commit()


async def count_completed_orders(telegram_id: int) -> int:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM orders WHERE telegram_id = ? AND status = 'completed'",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        return row[0]
