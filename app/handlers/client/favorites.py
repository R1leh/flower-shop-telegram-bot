import os

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile, Message

from app.keyboards.client_kb import BTN_FAVORITES, bouquet_card_kb, favorite_item_kb
from app.repositories import favorite_repo

router = Router(name="client_favorites")


@router.message(Command("favorites"))
@router.message(F.text == BTN_FAVORITES)
async def cmd_favorites(message: Message) -> None:
    bouquets = await favorite_repo.list_bouquets(message.from_user.id)
    if not bouquets:
        await message.answer("В избранном пока пусто. Добавляйте понравившиеся букеты ❤️")
        return

    await message.answer(f"❤️ Ваши избранные букеты ({len(bouquets)}):")
    for bouquet in bouquets:
        caption = f"💐 <b>{bouquet.name}</b>\n💰 {bouquet.price:.0f} ₽"
        kb = favorite_item_kb(bouquet.id)
        if bouquet.photo_path and os.path.exists(bouquet.photo_path):
            await message.answer_photo(FSInputFile(bouquet.photo_path), caption=caption, reply_markup=kb)
        else:
            await message.answer(caption, reply_markup=kb)


@router.callback_query(F.data.startswith("fav_toggle:"))
async def cb_fav_toggle(callback: CallbackQuery) -> None:
    bouquet_id = int(callback.data.split(":", 1)[1])
    telegram_id = callback.from_user.id

    is_fav = await favorite_repo.is_favorite(telegram_id, bouquet_id)
    if is_fav:
        await favorite_repo.remove(telegram_id, bouquet_id)
        await callback.answer("Удалено из избранного")
    else:
        await favorite_repo.add(telegram_id, bouquet_id)
        await callback.answer("Добавлено в избранное ❤️")

    await callback.message.edit_reply_markup(reply_markup=bouquet_card_kb(bouquet_id, not is_fav))


@router.callback_query(F.data.startswith("fav_remove:"))
async def cb_fav_remove(callback: CallbackQuery) -> None:
    bouquet_id = int(callback.data.split(":", 1)[1])
    await favorite_repo.remove(callback.from_user.id, bouquet_id)
    await callback.message.delete()
    await callback.answer("Удалено из избранного")
