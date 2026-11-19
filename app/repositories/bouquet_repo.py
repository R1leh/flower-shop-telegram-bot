from typing import Optional

from app.database.connection import get_connection
from app.models.bouquet import Bouquet
from app.utils.dt import now_iso


async def get(bouquet_id: int) -> Optional[Bouquet]:
    async with get_connection() as conn:
        cursor = await conn.execute("SELECT * FROM bouquets WHERE id = ?", (bouquet_id,))
        row = await cursor.fetchone()
        return Bouquet.from_row(row) if row else None


async def get_active() -> list[Bouquet]:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM bouquets WHERE is_active = 1 ORDER BY id DESC"
        )
        rows = await cursor.fetchall()
        return [Bouquet.from_row(row) for row in rows]


async def get_all(page: int = 0, page_size: Optional[int] = None) -> list[Bouquet]:
    """Все букеты (включая скрытые) для админ-панели, с опциональной пагинацией."""
    async with get_connection() as conn:
        if page_size:
            cursor = await conn.execute(
                "SELECT * FROM bouquets ORDER BY id DESC LIMIT ? OFFSET ?",
                (page_size, page * page_size),
            )
        else:
            cursor = await conn.execute("SELECT * FROM bouquets ORDER BY id DESC")
        rows = await cursor.fetchall()
        return [Bouquet.from_row(row) for row in rows]


async def count_all() -> int:
    async with get_connection() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM bouquets")
        row = await cursor.fetchone()
        return row[0]


async def create(
    name: str,
    description: str,
    price: float,
    occasion: str,
    season: str,
    mood: str,
    colors: str,
    recipient: str,
    photo_path: Optional[str],
) -> int:
    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            INSERT INTO bouquets (
                name, description, price, occasion, season, mood,
                colors, recipient, photo_path, is_active, rating,
                orders_count, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, 0, ?)
            """,
            (
                name,
                description,
                price,
                occasion,
                season,
                mood,
                colors,
                recipient,
                photo_path,
                now_iso(),
            ),
        )
        await conn.commit()
        return cursor.lastrowid


async def update_field(bouquet_id: int, field: str, value) -> None:
    allowed = {
        "name",
        "description",
        "price",
        "occasion",
        "season",
        "mood",
        "colors",
        "recipient",
        "photo_path",
    }
    if field not in allowed:
        raise ValueError(f"Недопустимое поле для обновления: {field}")
    async with get_connection() as conn:
        await conn.execute(
            f"UPDATE bouquets SET {field} = ? WHERE id = ?", (value, bouquet_id)
        )
        await conn.commit()


async def delete(bouquet_id: int) -> None:
    async with get_connection() as conn:
        await conn.execute("DELETE FROM bouquets WHERE id = ?", (bouquet_id,))
        await conn.commit()


async def toggle_active(bouquet_id: int) -> Optional[int]:
    """Переключить видимость букета. Возвращает новое значение is_active."""
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT is_active FROM bouquets WHERE id = ?", (bouquet_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        new_value = 0 if row[0] else 1
        await conn.execute(
            "UPDATE bouquets SET is_active = ? WHERE id = ?", (new_value, bouquet_id)
        )
        await conn.commit()
        return new_value


async def increment_orders_count(bouquet_id: int) -> None:
    async with get_connection() as conn:
        await conn.execute(
            "UPDATE bouquets SET orders_count = orders_count + 1 WHERE id = ?",
            (bouquet_id,),
        )
        await conn.commit()


async def recalculate_rating(bouquet_id: int) -> None:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT AVG(rating) FROM bouquet_reviews WHERE bouquet_id = ?",
            (bouquet_id,),
        )
        row = await cursor.fetchone()
        avg_rating = row[0] or 0
        await conn.execute(
            "UPDATE bouquets SET rating = ? WHERE id = ?", (round(avg_rating, 2), bouquet_id)
        )
        await conn.commit()


async def top_popular(limit: int = 5) -> list[Bouquet]:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM bouquets ORDER BY orders_count DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [Bouquet.from_row(row) for row in rows]
