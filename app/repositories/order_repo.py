from typing import Optional

from app.database.connection import get_connection
from app.models.order import Order, OrderStatusHistoryEntry
from app.utils.constants import FINAL_STATUSES
from app.utils.dt import now_iso


async def create(
    telegram_id: int,
    bouquet_id: Optional[int],
    bouquet_name: str,
    recipient_name: str,
    recipient_phone: str,
    delivery_address: str,
    delivery_time: str,
    comment: Optional[str],
    total_price: float,
) -> int:
    created_at = now_iso()
    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            INSERT INTO orders (
                telegram_id, bouquet_id, bouquet_name, recipient_name,
                recipient_phone, delivery_address, delivery_time, comment,
                total_price, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?)
            """,
            (
                telegram_id,
                bouquet_id,
                bouquet_name,
                recipient_name,
                recipient_phone,
                delivery_address,
                delivery_time,
                comment,
                total_price,
                created_at,
            ),
        )
        order_id = cursor.lastrowid
        await conn.execute(
            """
            INSERT INTO order_status_history (order_id, old_status, new_status, changed_by, changed_at)
            VALUES (?, NULL, 'new', 'client', ?)
            """,
            (order_id, created_at),
        )
        await conn.commit()
        return order_id


async def get(order_id: int) -> Optional[Order]:
    async with get_connection() as conn:
        cursor = await conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = await cursor.fetchone()
        return Order.from_row(row) if row else None


async def get_by_client(telegram_id: int, limit: int = 20) -> list[Order]:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM orders WHERE telegram_id = ? ORDER BY id DESC LIMIT ?",
            (telegram_id, limit),
        )
        rows = await cursor.fetchall()
        return [Order.from_row(row) for row in rows]


async def get_active(page: int = 0, page_size: int = 5) -> list[Order]:
    """Заказы, которые ещё не доведены до финального статуса (для админки)."""
    placeholders = ",".join("?" for _ in FINAL_STATUSES)
    async with get_connection() as conn:
        cursor = await conn.execute(
            f"""
            SELECT * FROM orders
            WHERE status NOT IN ({placeholders})
            ORDER BY id ASC
            LIMIT ? OFFSET ?
            """,
            (*FINAL_STATUSES, page_size, page * page_size),
        )
        rows = await cursor.fetchall()
        return [Order.from_row(row) for row in rows]


async def count_active() -> int:
    placeholders = ",".join("?" for _ in FINAL_STATUSES)
    async with get_connection() as conn:
        cursor = await conn.execute(
            f"SELECT COUNT(*) FROM orders WHERE status NOT IN ({placeholders})",
            tuple(FINAL_STATUSES),
        )
        row = await cursor.fetchone()
        return row[0]


async def update_status(order_id: int, new_status: str, changed_by: str) -> Optional[str]:
    """Сменить статус заказа, вернуть старый статус (или None, если заказ не найден)."""
    async with get_connection() as conn:
        cursor = await conn.execute("SELECT status FROM orders WHERE id = ?", (order_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        old_status = row[0]
        changed_at = now_iso()
        await conn.execute(
            "UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id)
        )
        await conn.execute(
            """
            INSERT INTO order_status_history (order_id, old_status, new_status, changed_by, changed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (order_id, old_status, new_status, changed_by, changed_at),
        )
        await conn.commit()
        return old_status


async def get_status_history(order_id: int) -> list[OrderStatusHistoryEntry]:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM order_status_history WHERE order_id = ? ORDER BY id ASC",
            (order_id,),
        )
        rows = await cursor.fetchall()
        return [OrderStatusHistoryEntry.from_row(row) for row in rows]


# --- Напоминания менеджеру о необработанных заявках -------------------------

async def get_stale_new_orders(threshold_iso: str) -> list[Order]:
    """Заказы в статусе 'new', созданные раньше threshold_iso, ещё без напоминания."""
    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT o.* FROM orders o
            LEFT JOIN order_manager_reminders r ON r.order_id = o.id
            WHERE o.status = 'new' AND o.created_at <= ? AND r.order_id IS NULL
            """,
            (threshold_iso,),
        )
        rows = await cursor.fetchall()
        return [Order.from_row(row) for row in rows]


async def mark_manager_reminded(order_id: int) -> None:
    async with get_connection() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO order_manager_reminders (order_id, sent_at) VALUES (?, ?)",
            (order_id, now_iso()),
        )
        await conn.commit()


# --- Статистика ---------------------------------------------------------------

async def get_in_period(start_iso: str, end_iso: str) -> list[Order]:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM orders WHERE created_at BETWEEN ? AND ? ORDER BY id ASC",
            (start_iso, end_iso),
        )
        rows = await cursor.fetchall()
        return [Order.from_row(row) for row in rows]


async def count_in_period(start_iso: str, end_iso: str) -> int:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM orders WHERE created_at BETWEEN ? AND ?",
            (start_iso, end_iso),
        )
        row = await cursor.fetchone()
        return row[0]


async def revenue_in_period(start_iso: str, end_iso: str) -> float:
    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT COALESCE(SUM(total_price), 0) FROM orders
            WHERE status = 'completed' AND created_at BETWEEN ? AND ?
            """,
            (start_iso, end_iso),
        )
        row = await cursor.fetchone()
        return row[0] or 0.0


async def average_check_in_period(start_iso: str, end_iso: str) -> float:
    async with get_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT AVG(total_price) FROM orders
            WHERE status = 'completed' AND created_at BETWEEN ? AND ?
            """,
            (start_iso, end_iso),
        )
        row = await cursor.fetchone()
        return row[0] or 0.0


async def repeat_clients_ratio(start_iso: str, end_iso: str) -> float:
    """Доля клиентов в периоде, у которых более одного заказа за всё время."""
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT DISTINCT telegram_id FROM orders WHERE created_at BETWEEN ? AND ?",
            (start_iso, end_iso),
        )
        client_ids = [row[0] for row in await cursor.fetchall()]
        if not client_ids:
            return 0.0
        repeat_count = 0
        for telegram_id in client_ids:
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM orders WHERE telegram_id = ?", (telegram_id,)
            )
            row = await cursor.fetchone()
            if row[0] > 1:
                repeat_count += 1
        return repeat_count / len(client_ids)
