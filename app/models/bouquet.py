from dataclasses import dataclass
from typing import Optional

import aiosqlite


@dataclass
class Bouquet:
    id: int
    name: str
    description: Optional[str]
    price: float
    occasion: Optional[str]
    season: Optional[str]
    mood: Optional[str]
    colors: Optional[str]
    recipient: Optional[str]
    photo_path: Optional[str]
    is_active: int = 1
    rating: float = 0.0
    orders_count: int = 0
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "Bouquet":
        return cls(**dict(row))

    @property
    def color_list(self) -> list[str]:
        if not self.colors:
            return []
        return [c.strip() for c in self.colors.split(",") if c.strip()]
