from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards.client_kb import BTN_PROFILE, profile_menu_kb
from app.models.client import Client
from app.repositories import client_repo
from app.utils.states import ProfileEditStates
from app.utils.validators import (
    is_valid_address,
    is_valid_birth_date,
    is_valid_name,
    is_valid_phone,
    normalize_phone,
)

router = Router(name="client_profile")

FIELD_PROMPTS: dict[str, str] = {
    "full_name": "Введите новое имя и фамилию.",
    "phone": "Введите новый номер телефона.",
    "delivery_address": "Введите новый адрес доставки.",
    "birth_date": "Введите дату рождения в формате ДД.ММ.ГГГГ.",
}

FIELD_STATES = {
    "full_name": ProfileEditStates.waiting_full_name,
    "phone": ProfileEditStates.waiting_phone,
    "delivery_address": ProfileEditStates.waiting_address,
    "birth_date": ProfileEditStates.waiting_birth_date,
}


def _format_profile(client: Client) -> str:
    lines = [
        "👤 <b>Личный кабинет</b>\n",
        f"Имя: {client.full_name or '—'}",
        f"Телефон: {client.phone or '—'}",
        f"Дата рождения: {client.birth_date or '—'}",
        f"Адрес доставки: {client.delivery_address or '—'}",
    ]
    if client.is_vip:
        lines.append("\n⭐ Статус: VIP-клиент")
    return "\n".join(lines)


@router.message(Command("profile"))
@router.message(F.text == BTN_PROFILE)
async def cmd_profile(message: Message) -> None:
    client = await client_repo.get(message.from_user.id)
    if client is None:
        await message.answer("Профиль не найден. Используйте /start.")
        return
    await message.answer(_format_profile(client), reply_markup=profile_menu_kb())


@router.callback_query(F.data.startswith("profile_edit:"))
async def cb_profile_edit(callback: CallbackQuery, state: FSMContext) -> None:
    field = callback.data.split(":", 1)[1]
    prompt = FIELD_PROMPTS.get(field)
    target_state = FIELD_STATES.get(field)
    if not prompt or target_state is None:
        await callback.answer()
        return
    await callback.message.answer(prompt)
    await state.set_state(target_state)
    await callback.answer()


@router.message(ProfileEditStates.waiting_full_name, F.text)
async def process_edit_full_name(message: Message, state: FSMContext) -> None:
    full_name = message.text.strip()
    if not is_valid_name(full_name):
        await message.answer(
            "Введите имя и фамилию, используя только буквы (от 2 до 100 символов)."
        )
        return
    await client_repo.update_profile(message.from_user.id, full_name=full_name)
    await message.answer("Имя обновлено ✅")
    await state.clear()


@router.message(ProfileEditStates.waiting_phone, F.text)
async def process_edit_phone(message: Message, state: FSMContext) -> None:
    phone = message.text.strip()
    if not is_valid_phone(phone):
        await message.answer("Не похоже на номер телефона. Попробуйте ещё раз.")
        return
    await client_repo.update_profile(message.from_user.id, phone=normalize_phone(phone))
    await message.answer("Телефон обновлён ✅")
    await state.clear()


@router.message(ProfileEditStates.waiting_address, F.text)
async def process_edit_address(message: Message, state: FSMContext) -> None:
    address = message.text.strip()
    if not is_valid_address(address):
        await message.answer(
            "Адрес должен быть от 5 до 200 символов и содержать номер дома. Попробуйте ещё раз."
        )
        return
    await client_repo.update_profile(message.from_user.id, delivery_address=address)
    await message.answer("Адрес доставки обновлён ✅")
    await state.clear()


@router.message(ProfileEditStates.waiting_birth_date, F.text)
async def process_edit_birth_date(message: Message, state: FSMContext) -> None:
    raw = message.text.strip()
    if not is_valid_birth_date(raw):
        await message.answer(
            "Не получилось распознать дату. Введите дату рождения в формате ДД.ММ.ГГГГ, "
            "она не должна быть в будущем."
        )
        return
    await client_repo.update_profile(message.from_user.id, birth_date=raw)
    await message.answer("Дата рождения сохранена ✅")
    await state.clear()
