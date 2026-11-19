from collections import Counter
from typing import Optional, TypedDict

from app.database.connection import get_connection


class HistoryRow(TypedDict):
    id: int
    telegram_id: int
    bouquet_id: int
    bouquet_name: str
    occasion: Optional[str]
    season: Optional[str]
    price: float
    ordered_at: str
    rating: Optional[int]


async def add(
    telegram_id: int,
    bouquet_id: int,
    bouquet_name: str,
    occasion: Optional[str],
    season: Optional[str],
    price: float,
    ordered_at: str,
) -> int:
    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            INSERT INTO order_history (
                telegram_id, bouquet_id, bouquet_name, occasion, season, price, ordered_at, rating
            ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (telegram_id, bouquet_id, bouquet_name, occasion, season, price, ordered_at),
        )
        await conn.commit()
        return cursor.lastrowid


async def list_by_client(telegram_id: int, limit: int = 20) -> list[HistoryRow]:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM order_history WHERE telegram_id = ? ORDER BY id DESC LIMIT ?",
            (telegram_id, limit),
        )
        rows = await cursor.fetchall()
        return [HistoryRow(**dict(row)) for row in rows]


async def get_purchased_bouquet_ids(telegram_id: int) -> set[int]:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT DISTINCT bouquet_id FROM order_history WHERE telegram_id = ?",
            (telegram_id,),
        )
        rows = await cursor.fetchall()
        return {row[0] for row in rows}


async def get_occasion_counts(telegram_id: int) -> Counter:
    """Сколько раз клиент заказывал букеты под каждый повод (для скоринга)."""
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT occasion FROM order_history WHERE telegram_id = ? AND occasion IS NOT NULL",
            (telegram_id,),
        )
        rows = await cursor.fetchall()
        return Counter(row[0] for row in rows)


async def find_unrated_entry(telegram_id: int, bouquet_id: int) -> Optional[HistoryRow]:
    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT * FROM order_history
            WHERE telegram_id = ? AND bouquet_id = ? AND rating IS NULL
            ORDER BY id DESC LIMIT 1
            """,
            (telegram_id, bouquet_id),
        )
        row = await cursor.fetchone()
        return HistoryRow(**dict(row)) if row else None


async def set_rating(history_id: int, rating: int) -> None:
    async with get_connection() as conn:
        await conn.execute(
            "UPDATE order_history SET rating = ? WHERE id = ?", (rating, history_id)
        )
        await conn.commit()
