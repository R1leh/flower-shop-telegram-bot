from dataclasses import dataclass
from typing import Optional

import aiosqlite


@dataclass
class Client:
    telegram_id: int
    full_name: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[str] = None
    delivery_address: Optional[str] = None
    is_vip: int = 0
    privacy_accepted: int = 0
    privacy_accepted_at: Optional[str] = None
    registered_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "Client":
        return cls(**dict(row))

    @property
    def is_registered(self) -> bool:
        return bool(self.full_name and self.phone)
