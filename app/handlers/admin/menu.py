from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.keyboards.admin_kb import admin_menu_kb, catalog_menu_kb

router = Router(name="admin_menu")

ADMIN_MENU_TEXT = "🛠 <b>Панель администратора «Бутон»</b>\n\nВыберите раздел:"


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    await message.answer(ADMIN_MENU_TEXT, reply_markup=admin_menu_kb())


@router.callback_query(F.data == "adm_menu")
async def cb_admin_menu(callback: CallbackQuery) -> None:
    await callback.message.answer(ADMIN_MENU_TEXT, reply_markup=admin_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "adm_catalog")
async def cb_catalog_menu(callback: CallbackQuery) -> None:
    await callback.message.answer("🌸 Управление каталогом:", reply_markup=catalog_menu_kb())
    await callback.answer()
