from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.keyboards.client_kb import BTN_LOYALTY
from app.repositories import loyalty_repo
from app.utils.constants import LOYALTY_LEVEL_NAMES, LOYALTY_THRESHOLDS

router = Router(name="client_loyalty")


def _next_level_progress(completed_orders: int) -> str:
    for level, threshold in reversed(LOYALTY_THRESHOLDS):
        if completed_orders < threshold:
            remaining = threshold - completed_orders
            return f"До уровня «{LOYALTY_LEVEL_NAMES[level]}» осталось заказов: {remaining}"
    return "У вас максимальный уровень лояльности! 🏆"


@router.message(Command("loyalty"))
@router.message(F.text == BTN_LOYALTY)
async def cmd_loyalty(message: Message) -> None:
    info = await loyalty_repo.get(message.from_user.id)
    completed = await loyalty_repo.count_completed_orders(message.from_user.id)
    level_name = LOYALTY_LEVEL_NAMES.get(info["level"], info["level"])

    text = (
        "🎁 <b>Программа лояльности</b>\n\n"
        f"Уровень: <b>{level_name}</b>\n"
        f"Баллов: {info['points']}\n"
        f"Сумма покупок: {info['total_spent']:.0f} ₽\n"
        f"Завершённых заказов: {completed}\n\n"
        f"{_next_level_progress(completed)}"
    )
    await message.answer(text)
