from app.database.connection import get_connection
from app.utils.dt import now_iso


async def create(bouquet_id: int, telegram_id: int, rating: int, review_text: str) -> int:
    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            INSERT INTO bouquet_reviews (bouquet_id, telegram_id, rating, review_text, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (bouquet_id, telegram_id, rating, review_text, now_iso()),
        )
        await conn.commit()
        return cursor.lastrowid
