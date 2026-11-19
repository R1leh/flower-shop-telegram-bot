from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards.client_kb import (
    BTN_HELP,
    main_menu_kb,
    phone_request_kb,
    privacy_kb,
)
from app.repositories import client_repo
from app.utils.dt import now_iso
from app.utils.states import RegistrationStates
from app.utils.validators import is_valid_name, is_valid_phone, normalize_phone
from app.utils.texts import (
    ASK_FULL_NAME,
    ASK_PHONE,
    HELP_TEXT,
    PRIVACY_DECLINED,
    PRIVACY_POLICY,
    REGISTRATION_DONE,
    WELCOME_BACK,
)

router = Router(name="client_start")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    client = await client_repo.get(message.from_user.id)

    if client and client.privacy_accepted:
        if client.is_registered:
            await message.answer(
                WELCOME_BACK.format(name=client.full_name), reply_markup=main_menu_kb()
            )
        else:
            await message.answer(ASK_FULL_NAME)
            await state.set_state(RegistrationStates.waiting_full_name)
        return

    await message.answer(PRIVACY_POLICY, reply_markup=privacy_kb())


@router.callback_query(F.data == "privacy_accept")
async def cb_privacy_accept(callback: CallbackQuery, state: FSMContext) -> None:
    await client_repo.accept_privacy(callback.from_user.id, now_iso())
    await callback.message.edit_text("Спасибо! Согласие на обработку ПДн получено ✅")
    await callback.message.answer(ASK_FULL_NAME)
    await state.set_state(RegistrationStates.waiting_full_name)
    await callback.answer()


@router.callback_query(F.data == "privacy_decline")
async def cb_privacy_decline(callback: CallbackQuery) -> None:
    await callback.message.edit_text(PRIVACY_DECLINED)
    await callback.answer()


@router.message(RegistrationStates.waiting_full_name, F.text)
async def process_full_name(message: Message, state: FSMContext) -> None:
    full_name = message.text.strip()
    if not is_valid_name(full_name):
        await message.answer(
            "Введите имя и фамилию, используя только буквы (от 2 до 100 символов)."
        )
        return

    await state.update_data(full_name=full_name)
    await message.answer(
        ASK_PHONE.format(name=full_name), reply_markup=phone_request_kb()
    )
    await state.set_state(RegistrationStates.waiting_phone)


@router.message(RegistrationStates.waiting_phone, F.contact)
async def process_phone_contact(message: Message, state: FSMContext) -> None:
    await _finish_registration(message, state, message.contact.phone_number)


@router.message(RegistrationStates.waiting_phone, F.text)
async def process_phone_text(message: Message, state: FSMContext) -> None:
    phone = message.text.strip()
    if not is_valid_phone(phone):
        await message.answer(
            "Не похоже на номер телефона. Введите номер ещё раз или нажмите кнопку ниже.",
            reply_markup=phone_request_kb(),
        )
        return
    await _finish_registration(message, state, phone)


async def _finish_registration(message: Message, state: FSMContext, phone: str) -> None:
    data = await state.get_data()
    full_name = data.get("full_name", "")
    await client_repo.complete_registration(message.from_user.id, full_name, normalize_phone(phone))
    await state.clear()
    await message.answer(REGISTRATION_DONE, reply_markup=main_menu_kb())


@router.message(Command("help"))
@router.message(F.text == BTN_HELP)
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)
