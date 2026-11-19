from dataclasses import dataclass
from typing import Optional

import aiosqlite


@dataclass
class Order:
    id: int
    telegram_id: int
    bouquet_id: Optional[int]
    bouquet_name: Optional[str]
    recipient_name: Optional[str]
    recipient_phone: Optional[str]
    delivery_address: Optional[str]
    delivery_time: Optional[str]
    comment: Optional[str]
    total_price: Optional[float]
    status: str = "new"
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "Order":
        return cls(**dict(row))


@dataclass
class OrderStatusHistoryEntry:
    id: int
    order_id: int
    old_status: Optional[str]
    new_status: str
    changed_by: Optional[str]
    changed_at: Optional[str]

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "OrderStatusHistoryEntry":
        return cls(**dict(row))
