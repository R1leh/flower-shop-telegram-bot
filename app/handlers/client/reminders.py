from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards.client_kb import (
    BTN_REMINDERS,
    REMINDER_OCCASIONS,
    reminder_item_kb,
    reminder_occasion_kb,
)
from app.repositories import reminder_repo
from app.utils import texts
from app.utils.constants import label_by_code
from app.utils.states import ReminderStates
from app.utils.validators import is_valid_event_date, is_valid_name

router = Router(name="client_reminders")


@router.message(Command("remind"))
@router.message(F.text == BTN_REMINDERS)
async def cmd_remind(message: Message, state: FSMContext) -> None:
    reminders = await reminder_repo.list_active_for_client(message.from_user.id)
    if reminders:
        await message.answer("⏰ Ваши напоминания:")
        for reminder in reminders:
            text = f"{reminder['person_name']} — {reminder['remind_date']} ({reminder['occasion']})"
            await message.answer(text, reply_markup=reminder_item_kb(reminder["id"]))

    await message.answer(texts.REMINDER_ASK_NAME)
    await state.set_state(ReminderStates.waiting_name)


@router.message(ReminderStates.waiting_name, F.text)
async def process_reminder_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not is_valid_name(name):
        await message.answer("Введите имя, используя только буквы (от 2 до 100 символов).")
        return
    await state.update_data(person_name=name)
    await message.answer(texts.REMINDER_ASK_DATE)
    await state.set_state(ReminderStates.waiting_date)


@router.message(ReminderStates.waiting_date, F.text)
async def process_reminder_date(message: Message, state: FSMContext) -> None:
    raw = message.text.strip()
    if not is_valid_event_date(raw):
        await message.answer(texts.REMINDER_INVALID_DATE)
        return
    await state.update_data(remind_date=raw)
    await message.answer(texts.REMINDER_ASK_OCCASION, reply_markup=reminder_occasion_kb())
    await state.set_state(ReminderStates.waiting_occasion)


@router.callback_query(ReminderStates.waiting_occasion, F.data.startswith("rem_occ:"))
async def process_reminder_occasion(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":", 1)[1]
    label = label_by_code(REMINDER_OCCASIONS, code)
    data = await state.get_data()

    await reminder_repo.create(callback.from_user.id, data["person_name"], data["remind_date"], label)

    await callback.message.edit_text(f"{texts.REMINDER_ASK_OCCASION}\n\n✅ {label}")
    await callback.message.answer(texts.REMINDER_CREATED)
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("rem_delete:"))
async def cb_rem_delete(callback: CallbackQuery) -> None:
    reminder_id = int(callback.data.split(":", 1)[1])
    await reminder_repo.deactivate(reminder_id)
    await callback.message.delete()
    await callback.answer("Напоминание удалено")
