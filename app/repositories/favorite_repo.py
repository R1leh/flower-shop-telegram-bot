from app.database.connection import get_connection
from app.models.bouquet import Bouquet
from app.utils.dt import now_iso


async def add(telegram_id: int, bouquet_id: int) -> None:
    async with get_connection() as conn:
        await conn.execute(
            "INSERT OR IGNORE INTO favorites (telegram_id, bouquet_id, added_at) VALUES (?, ?, ?)",
            (telegram_id, bouquet_id, now_iso()),
        )
        await conn.commit()


async def remove(telegram_id: int, bouquet_id: int) -> None:
    async with get_connection() as conn:
        await conn.execute(
            "DELETE FROM favorites WHERE telegram_id = ? AND bouquet_id = ?",
            (telegram_id, bouquet_id),
        )
        await conn.commit()


async def is_favorite(telegram_id: int, bouquet_id: int) -> bool:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT 1 FROM favorites WHERE telegram_id = ? AND bouquet_id = ?",
            (telegram_id, bouquet_id),
        )
        return await cursor.fetchone() is not None


async def list_bouquets(telegram_id: int) -> list[Bouquet]:
    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT b.* FROM bouquets b
            INNER JOIN favorites f ON f.bouquet_id = b.id
            WHERE f.telegram_id = ?
            ORDER BY f.added_at DESC
            """,
            (telegram_id,),
        )
        rows = await cursor.fetchall()
        return [Bouquet.from_row(row) for row in rows]


async def get_favorite_occasions(telegram_id: int) -> set[str]:
    """Поводы букетов из избранного клиента (для повышения приоритета в подборе)."""
    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT DISTINCT b.occasion FROM bouquets b
            INNER JOIN favorites f ON f.bouquet_id = b.id
            WHERE f.telegram_id = ? AND b.occasion IS NOT NULL
            """,
            (telegram_id,),
        )
        rows = await cursor.fetchall()
        return {row[0] for row in rows}
