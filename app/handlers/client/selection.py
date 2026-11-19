import os

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from app.keyboards.client_kb import (
    BTN_SELECT,
    bouquet_card_kb,
    budget_kb,
    color_kb,
    flowers_skip_kb,
    mood_kb,
    more_results_kb,
    occasion_kb,
    recipient_kb,
    season_kb,
)
from app.models.bouquet import Bouquet
from app.repositories import bouquet_repo, favorite_repo, session_repo
from app.services.recommendation import get_recommendations
from app.utils import texts
from app.utils.constants import (
    BUDGETS,
    COLORS,
    MOODS,
    OCCASIONS,
    RECIPIENTS,
    RESULTS_PAGE_SIZE,
    SEASONS,
    label_by_code,
)
from app.utils.states import SelectionStates

router = Router(name="client_selection")


async def _start_selection(message: Message, telegram_id: int, state: FSMContext) -> None:
    await state.clear()
    session_id = await session_repo.create(telegram_id)
    await state.update_data(session_id=session_id)
    await message.answer(texts.SELECTION_START)
    await message.answer(texts.SELECTION_STEP_OCCASION, reply_markup=occasion_kb())
    await state.set_state(SelectionStates.occasion)


@router.message(Command("select"))
@router.message(F.text == BTN_SELECT)
async def cmd_select(message: Message, state: FSMContext) -> None:
    await _start_selection(message, message.from_user.id, state)


@router.callback_query(F.data == "sel_restart")
async def cb_restart(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _start_selection(callback.message, callback.from_user.id, state)


@router.callback_query(SelectionStates.occasion, F.data.startswith("sel_occ:"))
async def process_occasion(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":", 1)[1]
    label = label_by_code(OCCASIONS, code)
    await state.update_data(occasion=label)
    await callback.message.edit_text(f"{texts.SELECTION_STEP_OCCASION}\n\n✅ {label}")
    await callback.message.answer(texts.SELECTION_STEP_RECIPIENT, reply_markup=recipient_kb())
    await state.set_state(SelectionStates.recipient)
    await callback.answer()


@router.callback_query(SelectionStates.recipient, F.data.startswith("sel_rcp:"))
async def process_recipient(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":", 1)[1]
    label = label_by_code(RECIPIENTS, code)
    await state.update_data(recipient=label)
    await callback.message.edit_text(f"{texts.SELECTION_STEP_RECIPIENT}\n\n✅ {label}")
    await callback.message.answer(texts.SELECTION_STEP_BUDGET, reply_markup=budget_kb())
    await state.set_state(SelectionStates.budget)
    await callback.answer()


@router.callback_query(SelectionStates.budget, F.data.startswith("sel_bud:"))
async def process_budget(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":", 1)[1]
    label, budget_from, budget_to = code, 0, None
    for item_code, item_label, item_from, item_to in BUDGETS:
        if item_code == code:
            label, budget_from, budget_to = item_label, item_from, item_to
            break
    await state.update_data(budget_from=budget_from, budget_to=budget_to)
    await callback.message.edit_text(f"{texts.SELECTION_STEP_BUDGET}\n\n✅ {label}")
    await callback.message.answer(texts.SELECTION_STEP_SEASON, reply_markup=season_kb())
    await state.set_state(SelectionStates.season)
    await callback.answer()


@router.callback_query(SelectionStates.season, F.data.startswith("sel_season:"))
async def process_season(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":", 1)[1]
    label = label_by_code(SEASONS, code)
    await state.update_data(season=label)
    await callback.message.edit_text(f"{texts.SELECTION_STEP_SEASON}\n\n✅ {label}")
    await callback.message.answer(texts.SELECTION_STEP_MOOD, reply_markup=mood_kb())
    await state.set_state(SelectionStates.mood)
    await callback.answer()


@router.callback_query(SelectionStates.mood, F.data.startswith("sel_mood:"))
async def process_mood(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":", 1)[1]
    label = label_by_code(MOODS, code)
    await state.update_data(mood=label)
    await callback.message.edit_text(f"{texts.SELECTION_STEP_MOOD}\n\n✅ {label}")
    await callback.message.answer(texts.SELECTION_STEP_COLOR, reply_markup=color_kb())
    await state.set_state(SelectionStates.color)
    await callback.answer()


@router.callback_query(SelectionStates.color, F.data.startswith("sel_color:"))
async def process_color(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":", 1)[1]
    label = label_by_code(COLORS, code)
    await state.update_data(color_preference=label)
    await callback.message.edit_text(f"{texts.SELECTION_STEP_COLOR}\n\n✅ {label}")
    await callback.message.answer(texts.SELECTION_STEP_FLOWERS, reply_markup=flowers_skip_kb())
    await state.set_state(SelectionStates.flowers)
    await callback.answer()


@router.message(SelectionStates.flowers, F.text)
async def process_flowers_text(message: Message, state: FSMContext) -> None:
    await state.update_data(flower_preferences=message.text.strip())
    await _finalize_selection(message, message.from_user.id, state)


@router.callback_query(SelectionStates.flowers, F.data == "sel_flowers_skip")
async def process_flowers_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(flower_preferences=None)
    await callback.message.edit_text(f"{texts.SELECTION_STEP_FLOWERS}\n\n✅ Пропущено")
    await _finalize_selection(callback.message, callback.from_user.id, state)
    await callback.answer()


@router.message(
    StateFilter(
        SelectionStates.occasion,
        SelectionStates.recipient,
        SelectionStates.budget,
        SelectionStates.season,
        SelectionStates.mood,
        SelectionStates.color,
    )
)
async def process_unexpected_text(message: Message) -> None:
    await message.answer("Пожалуйста, выберите один из вариантов на кнопках выше ⬆️")


def _format_bouquet_caption(bouquet: Bouquet) -> str:
    lines = [f"💐 <b>{bouquet.name}</b>"]
    if bouquet.description:
        lines.append(bouquet.description)
    lines.append(f"\n💰 Цена: {bouquet.price:.0f} ₽")
    if bouquet.rating:
        lines.append(f"⭐ Рейтинг: {bouquet.rating:.1f}")
    return "\n".join(lines)


async def _finalize_selection(message: Message, telegram_id: int, state: FSMContext) -> None:
    data = await state.get_data()
    session_id = data["session_id"]
    await session_repo.update(
        session_id,
        occasion=data.get("occasion"),
        budget_from=data.get("budget_from"),
        budget_to=data.get("budget_to"),
        season=data.get("season"),
        recipient=data.get("recipient"),
        color_preference=data.get("color_preference"),
        flower_preferences=data.get("flower_preferences"),
        mood=data.get("mood"),
    )

    await message.answer(texts.SELECTION_SEARCHING)

    bouquets, has_exact = await get_recommendations(telegram_id, data)

    if not bouquets:
        await session_repo.mark_completed(session_id, None)
        await message.answer(texts.SELECTION_NO_RESULTS)
        await state.clear()
        return

    bouquet_ids = [b.id for b in bouquets]
    await session_repo.mark_completed(session_id, bouquet_ids[0])

    await state.update_data(bouquet_ids=bouquet_ids, shown_count=0, telegram_id=telegram_id)
    await state.set_state(SelectionStates.showing_results)

    header = texts.SELECTION_RESULTS_HEADER if has_exact else texts.SELECTION_NO_EXACT_MATCH
    await message.answer(header)

    await _show_next_batch(message, state)


async def _show_next_batch(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    bouquet_ids: list[int] = data["bouquet_ids"]
    shown_count: int = data["shown_count"]
    telegram_id: int = data["telegram_id"]

    batch_ids = bouquet_ids[shown_count : shown_count + RESULTS_PAGE_SIZE]
    if not batch_ids:
        await message.answer(texts.SELECTION_NO_MORE)
        return

    for bouquet_id in batch_ids:
        bouquet = await bouquet_repo.get(bouquet_id)
        if bouquet is None:
            continue
        is_fav = await favorite_repo.is_favorite(telegram_id, bouquet_id)
        caption = _format_bouquet_caption(bouquet)
        kb = bouquet_card_kb(bouquet_id, is_fav)
        if bouquet.photo_path and os.path.exists(bouquet.photo_path):
            await message.answer_photo(
                FSInputFile(bouquet.photo_path), caption=caption, reply_markup=kb
            )
        else:
            await message.answer(caption, reply_markup=kb)

    new_shown = shown_count + len(batch_ids)
    await state.update_data(shown_count=new_shown)
    has_more = new_shown < len(bouquet_ids)
    await message.answer("Что дальше?", reply_markup=more_results_kb(has_more))


@router.callback_query(SelectionStates.showing_results, F.data == "sel_more")
async def cb_show_more(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _show_next_batch(callback.message, state)
