from typing import Optional

from app.repositories import loyalty_repo
from app.utils.constants import (
    DEFAULT_LOYALTY_LEVEL,
    LOYALTY_LEVEL_NAMES,
    LOYALTY_THRESHOLDS,
    POINTS_PER_RUBLE_DIVISOR,
)


def _level_for_completed_orders(completed_orders: int) -> str:
    for level, threshold in LOYALTY_THRESHOLDS:
        if completed_orders >= threshold:
            return level
    return DEFAULT_LOYALTY_LEVEL


async def register_completed_order(telegram_id: int, total_price: float) -> Optional[str]:
    """Начислить баллы за заказ и пересчитать уровень лояльности.

    Возвращает русское название нового уровня, если клиент только что
    повысился, иначе None.
    """
    points_earned = int(total_price // POINTS_PER_RUBLE_DIVISOR)
    await loyalty_repo.add_points_and_spent(telegram_id, points_earned, total_price)

    info = await loyalty_repo.get(telegram_id)
    completed_orders = await loyalty_repo.count_completed_orders(telegram_id)
    new_level = _level_for_completed_orders(completed_orders)

    if new_level != info["level"]:
        await loyalty_repo.set_level(telegram_id, new_level)
        return LOYALTY_LEVEL_NAMES[new_level]
    return None
