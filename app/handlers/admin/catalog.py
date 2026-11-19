import os
import uuid
from typing import Optional

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.keyboards.admin_kb import (
    EDIT_FIELDS,
    bouquet_choice_kb,
    bouquet_colors_kb,
    bouquet_mood_kb,
    bouquet_occasion_kb,
    bouquet_recipient_kb,
    bouquet_season_kb,
    catalog_pagination_kb,
    confirm_delete_kb,
    edit_field_kb,
    skip_photo_kb,
)
from app.repositories import bouquet_repo
from app.utils.config import config
from app.utils.constants import (
    BOUQUET_COLORS,
    BOUQUET_SEASONS,
    CATALOG_PAGE_SIZE,
    MOODS,
    OCCASIONS,
    RECIPIENTS,
    label_by_code,
)
from app.utils.states import AddBouquetStates, EditBouquetStates, SetPriceStates

router = Router(name="admin_catalog")

FIELD_LABELS: dict[str, str] = dict(EDIT_FIELDS)

_PROMPTS: dict[str, str] = {
    "adm_edit_select": "Выберите букет для редактирования:",
    "adm_delete_select": "Выберите букет для удаления:",
    "adm_toggle_select": "Выберите букет, чтобы скрыть или показать:",
    "adm_price_select": "Выберите букет для изменения цены:",
}


def _parse_price(raw: str) -> Optional[float]:
    raw = raw.strip().replace(",", ".").replace(" ", "")
    try:
        price = float(raw)
    except ValueError:
        return None
    return price if price > 0 else None


async def _save_photo(bot: Bot, file_id: str, ext: str) -> str:
    file = await bot.get_file(file_id)
    filename = f"{uuid.uuid4().hex}.{ext}"
    destination = os.path.join(config.photos_dir, filename)
    await bot.download_file(file.file_path, destination=destination)
    return destination


# --- Список каталога -----------------------------------------------------------

async def _format_catalog_page(page: int) -> tuple[Optional[str], Optional[InlineKeyboardMarkup]]:
    total = await bouquet_repo.count_all()
    if total == 0:
        return None, None
    bouquets = await bouquet_repo.get_all(page=page, page_size=CATALOG_PAGE_SIZE)
    lines = [f"📃 <b>Каталог</b> (стр. {page + 1}):\n"]
    for bouquet in bouquets:
        status = "🟢" if bouquet.is_active else "⚪️ скрыт"
        lines.append(
            f"#{bouquet.id} {bouquet.name} — {bouquet.price:.0f} ₽ {status} "
            f"(рейтинг {bouquet.rating:.1f}, заказов {bouquet.orders_count})"
        )
    has_prev = page > 0
    has_next = (page + 1) * CATALOG_PAGE_SIZE < total
    kb = catalog_pagination_kb(page, has_prev, has_next) if (has_prev or has_next) else None
    return "\n".join(lines), kb


@router.callback_query(F.data == "adm_list_bouquets")
async def cb_list_bouquets(callback: CallbackQuery) -> None:
    text, kb = await _format_catalog_page(0)
    if text is None:
        await callback.answer("Каталог пуст", show_alert=True)
        return
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("adm_catalog_page:"))
async def cb_catalog_page(callback: CallbackQuery) -> None:
    page = int(callback.data.split(":", 1)[1])
    text, kb = await _format_catalog_page(page)
    if text is None:
        await callback.answer("Каталог пуст", show_alert=True)
        return
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# --- Выбор букета из каталога (для редактирования/удаления/цены/видимости) -----

async def _build_bouquet_choice(
    action: str, page: int
) -> tuple[Optional[str], Optional[InlineKeyboardMarkup]]:
    total = await bouquet_repo.count_all()
    if total == 0:
        return None, None
    bouquets = await bouquet_repo.get_all(page=page, page_size=CATALOG_PAGE_SIZE)
    has_next = (page + 1) * CATALOG_PAGE_SIZE < total
    return _PROMPTS[action], bouquet_choice_kb(bouquets, action, page, has_next)


async def _start_choice(message: Message, state: FSMContext, action: str) -> None:
    prompt, kb = await _build_bouquet_choice(action, 0)
    if prompt is None:
        await message.answer("В каталоге пока нет букетов.")
        return
    await state.update_data(catalog_action=action, catalog_page=0)
    await message.answer(prompt, reply_markup=kb)


async def _refresh_choice_message(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    action = data.get("catalog_action")
    page = data.get("catalog_page", 0)
    if action is None:
        return
    prompt, kb = await _build_bouquet_choice(action, page)
    if prompt is None:
        await callback.message.edit_text("В каталоге больше нет букетов.")
        return
    await callback.message.edit_text(prompt, reply_markup=kb)


@router.callback_query(F.data.startswith("adm_bq_page:"))
async def cb_bouquet_page(callback: CallbackQuery, state: FSMContext) -> None:
    _, action, page_raw = callback.data.split(":")
    page = int(page_raw)
    prompt, kb = await _build_bouquet_choice(action, page)
    if prompt is None:
        await callback.answer("Каталог пуст", show_alert=True)
        return
    await state.update_data(catalog_action=action, catalog_page=page)
    await callback.message.edit_text(prompt, reply_markup=kb)
    await callback.answer()


# --- Добавление букета ----------------------------------------------------------

@router.message(Command("add_bouquet"))
async def cmd_add_bouquet(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Введите название букета.")
    await state.set_state(AddBouquetStates.waiting_name)


@router.callback_query(F.data == "adm_add_bouquet")
async def cb_add_bouquet(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Введите название букета.")
    await state.set_state(AddBouquetStates.waiting_name)
    await callback.answer()


@router.message(AddBouquetStates.waiting_name, F.text)
async def process_add_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Название слишком короткое. Введите ещё раз.")
        return
    await state.update_data(name=name)
    await message.answer("Введите описание букета.")
    await state.set_state(AddBouquetStates.waiting_description)


@router.message(AddBouquetStates.waiting_description, F.text)
async def process_add_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text.strip())
    await message.answer("Введите цену букета в рублях, например 2500.")
    await state.set_state(AddBouquetStates.waiting_price)


@router.message(AddBouquetStates.waiting_price, F.text)
async def process_add_price(message: Message, state: FSMContext) -> None:
    price = _parse_price(message.text)
    if price is None:
        await message.answer("Введите цену числом, например 2500 или 2500.50.")
        return
    await state.update_data(price=price)
    await message.answer("Выберите повод.", reply_markup=bouquet_occasion_kb())
    await state.set_state(AddBouquetStates.waiting_occasion)


@router.callback_query(AddBouquetStates.waiting_occasion, F.data.startswith("bq_occ:"))
async def process_add_occasion(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":", 1)[1]
    label = label_by_code(OCCASIONS, code)
    await state.update_data(occasion=label)
    await callback.message.edit_text(f"Повод: ✅ {label}")
    await callback.message.answer("Выберите сезон.", reply_markup=bouquet_season_kb())
    await state.set_state(AddBouquetStates.waiting_season)
    await callback.answer()


@router.callback_query(AddBouquetStates.waiting_season, F.data.startswith("bq_season:"))
async def process_add_season(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":", 1)[1]
    label = label_by_code(BOUQUET_SEASONS, code)
    await state.update_data(season=label)
    await callback.message.edit_text(f"Сезон: ✅ {label}")
    await callback.message.answer("Выберите настроение.", reply_markup=bouquet_mood_kb())
    await state.set_state(AddBouquetStates.waiting_mood)
    await callback.answer()


@router.callback_query(AddBouquetStates.waiting_mood, F.data.startswith("bq_mood:"))
async def process_add_mood(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":", 1)[1]
    label = label_by_code(MOODS, code)
    await state.update_data(mood=label, colors=[])
    await callback.message.edit_text(f"Настроение: ✅ {label}")
    await callback.message.answer("Выберите цвета (можно несколько):", reply_markup=bouquet_colors_kb([]))
    await state.set_state(AddBouquetStates.waiting_colors)
    await callback.answer()


@router.callback_query(AddBouquetStates.waiting_colors, F.data.startswith("bq_color:"))
async def process_add_color_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":", 1)[1]
    data = await state.get_data()
    selected: list[str] = list(data.get("colors", []))
    if code in selected:
        selected.remove(code)
    else:
        selected.append(code)
    await state.update_data(colors=selected)
    await callback.message.edit_reply_markup(reply_markup=bouquet_colors_kb(selected))
    await callback.answer()


@router.callback_query(AddBouquetStates.waiting_colors, F.data == "bq_color_done")
async def process_add_colors_done(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    selected: list[str] = data.get("colors", [])
    if not selected:
        await callback.answer("Выберите хотя бы один цвет", show_alert=True)
        return
    labels = [label_by_code(BOUQUET_COLORS, code) for code in selected]
    await state.update_data(colors=labels)
    await callback.message.edit_text(f"Цвета: ✅ {', '.join(labels)}")
    await callback.message.answer("Кому подходит букет?", reply_markup=bouquet_recipient_kb())
    await state.set_state(AddBouquetStates.waiting_recipient)
    await callback.answer()


@router.callback_query(AddBouquetStates.waiting_recipient, F.data.startswith("bq_rcp:"))
async def process_add_recipient(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":", 1)[1]
    label = label_by_code(RECIPIENTS, code)
    await state.update_data(recipient=label)
    await callback.message.edit_text(f"Получатель: ✅ {label}")
    await callback.message.answer(
        f"Отправьте фото букета (JPG/PNG, до {config.max_photo_size_mb} МБ) "
        "или нажмите «Пропустить».",
        reply_markup=skip_photo_kb(),
    )
    await state.set_state(AddBouquetStates.waiting_photo)
    await callback.answer()


@router.message(AddBouquetStates.waiting_photo, F.photo)
async def process_add_photo(message: Message, state: FSMContext, bot: Bot) -> None:
    photo = message.photo[-1]
    if photo.file_size and photo.file_size > config.max_photo_size_bytes:
        await message.answer(f"Файл слишком большой. Максимум {config.max_photo_size_mb} МБ.")
        return
    photo_path = await _save_photo(bot, photo.file_id, "jpg")
    await _create_bouquet(message, state, photo_path)


@router.message(AddBouquetStates.waiting_photo, F.document)
async def process_add_photo_document(message: Message, state: FSMContext, bot: Bot) -> None:
    document = message.document
    if document.mime_type not in ("image/jpeg", "image/png"):
        await message.answer("Поддерживаются только форматы JPG и PNG.")
        return
    if document.file_size and document.file_size > config.max_photo_size_bytes:
        await message.answer(f"Файл слишком большой. Максимум {config.max_photo_size_mb} МБ.")
        return
    ext = "png" if document.mime_type == "image/png" else "jpg"
    photo_path = await _save_photo(bot, document.file_id, ext)
    await _create_bouquet(message, state, photo_path)


@router.callback_query(AddBouquetStates.waiting_photo, F.data == "bq_photo_skip")
async def process_add_photo_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    await _create_bouquet(callback.message, state, None)
    await callback.answer()


async def _create_bouquet(message: Message, state: FSMContext, photo_path: Optional[str]) -> None:
    data = await state.get_data()
    bouquet_id = await bouquet_repo.create(
        name=data["name"],
        description=data["description"],
        price=data["price"],
        occasion=data["occasion"],
        season=data["season"],
        mood=data["mood"],
        colors=",".join(data.get("colors", [])),
        recipient=data["recipient"],
        photo_path=photo_path,
    )
    await message.answer(f"✅ Букет «{data['name']}» добавлен в каталог (ID {bouquet_id}).")
    await state.clear()


# --- Редактирование букета -------------------------------------------------------

@router.message(Command("edit_bouquet"))
async def cmd_edit_bouquet(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _start_choice(message, state, "adm_edit_select")


@router.callback_query(F.data == "adm_edit_bouquet")
async def cb_edit_bouquet_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _start_choice(callback.message, state, "adm_edit_select")
    await callback.answer()


@router.callback_query(F.data.startswith("adm_edit_select:"))
async def cb_edit_select_bouquet(callback: CallbackQuery, state: FSMContext) -> None:
    bouquet_id = int(callback.data.split(":", 1)[1])
    bouquet = await bouquet_repo.get(bouquet_id)
    if bouquet is None:
        await callback.answer("Букет не найден", show_alert=True)
        return
    await state.update_data(bouquet_id=bouquet_id)
    await callback.message.answer(
        f"💐 <b>{bouquet.name}</b>\nЧто изменить?", reply_markup=edit_field_kb()
    )
    await state.set_state(EditBouquetStates.choosing_field)
    await callback.answer()


@router.callback_query(EditBouquetStates.choosing_field, F.data.startswith("adm_edit_field:"))
async def cb_edit_choose_field(callback: CallbackQuery, state: FSMContext) -> None:
    field = callback.data.split(":", 1)[1]
    await state.update_data(field=field)

    if field == "occasion":
        await callback.message.answer("Выберите новый повод:", reply_markup=bouquet_occasion_kb("bq_edit_occ"))
    elif field == "season":
        await callback.message.answer("Выберите новый сезон:", reply_markup=bouquet_season_kb("bq_edit_season"))
    elif field == "mood":
        await callback.message.answer("Выберите новое настроение:", reply_markup=bouquet_mood_kb("bq_edit_mood"))
    elif field == "recipient":
        await callback.message.answer("Выберите нового получателя:", reply_markup=bouquet_recipient_kb("bq_edit_rcp"))
    elif field == "colors":
        await state.update_data(edit_colors=[])
        await callback.message.answer("Выберите цвета:", reply_markup=bouquet_colors_kb([], "bq_edit_color"))
    elif field == "photo_path":
        await callback.message.answer(
            f"Отправьте новое фото букета (JPG/PNG, до {config.max_photo_size_mb} МБ)."
        )
    else:
        prompts = {
            "name": "Введите новое название.",
            "description": "Введите новое описание.",
            "price": "Введите новую цену.",
        }
        await callback.message.answer(prompts[field])

    await state.set_state(EditBouquetStates.waiting_value)
    await callback.answer()


async def _apply_edit(callback: CallbackQuery, state: FSMContext, value) -> None:
    data = await state.get_data()
    bouquet_id = data["bouquet_id"]
    field = data["field"]
    await bouquet_repo.update_field(bouquet_id, field, value)
    await callback.message.edit_text(f"✅ Поле «{FIELD_LABELS.get(field, field)}» обновлено: {value}")
    await state.clear()
    await callback.answer()


@router.callback_query(EditBouquetStates.waiting_value, F.data.startswith("bq_edit_occ:"))
async def cb_edit_value_occasion(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":", 1)[1]
    await _apply_edit(callback, state, label_by_code(OCCASIONS, code))


@router.callback_query(EditBouquetStates.waiting_value, F.data.startswith("bq_edit_season:"))
async def cb_edit_value_season(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":", 1)[1]
    await _apply_edit(callback, state, label_by_code(BOUQUET_SEASONS, code))


@router.callback_query(EditBouquetStates.waiting_value, F.data.startswith("bq_edit_mood:"))
async def cb_edit_value_mood(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":", 1)[1]
    await _apply_edit(callback, state, label_by_code(MOODS, code))


@router.callback_query(EditBouquetStates.waiting_value, F.data.startswith("bq_edit_rcp:"))
async def cb_edit_value_recipient(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":", 1)[1]
    await _apply_edit(callback, state, label_by_code(RECIPIENTS, code))


@router.callback_query(EditBouquetStates.waiting_value, F.data.startswith("bq_edit_color:"))
async def cb_edit_color_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":", 1)[1]
    data = await state.get_data()
    selected: list[str] = list(data.get("edit_colors", []))
    if code in selected:
        selected.remove(code)
    else:
        selected.append(code)
    await state.update_data(edit_colors=selected)
    await callback.message.edit_reply_markup(reply_markup=bouquet_colors_kb(selected, "bq_edit_color"))
    await callback.answer()


@router.callback_query(EditBouquetStates.waiting_value, F.data == "bq_edit_color_done")
async def cb_edit_color_done(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    selected: list[str] = data.get("edit_colors", [])
    if not selected:
        await callback.answer("Выберите хотя бы один цвет", show_alert=True)
        return
    labels = [label_by_code(BOUQUET_COLORS, code) for code in selected]
    await _apply_edit(callback, state, ", ".join(labels))


@router.message(EditBouquetStates.waiting_value, F.text)
async def process_edit_value_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    field = data["field"]
    bouquet_id = data["bouquet_id"]

    if field == "photo_path":
        await message.answer(f"Отправьте фото букета (JPG/PNG, до {config.max_photo_size_mb} МБ).")
        return

    value: object = message.text.strip()
    if field == "price":
        price = _parse_price(message.text)
        if price is None:
            await message.answer("Введите цену числом, например 2500.")
            return
        value = price

    await bouquet_repo.update_field(bouquet_id, field, value)
    await message.answer(f"✅ Поле «{FIELD_LABELS.get(field, field)}» обновлено.")
    await state.clear()


@router.message(EditBouquetStates.waiting_value, F.photo)
async def process_edit_value_photo(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    if data.get("field") != "photo_path":
        return
    photo = message.photo[-1]
    if photo.file_size and photo.file_size > config.max_photo_size_bytes:
        await message.answer(f"Файл слишком большой. Максимум {config.max_photo_size_mb} МБ.")
        return
    photo_path = await _save_photo(bot, photo.file_id, "jpg")
    await bouquet_repo.update_field(data["bouquet_id"], "photo_path", photo_path)
    await message.answer("✅ Фото обновлено.")
    await state.clear()


@router.message(EditBouquetStates.waiting_value, F.document)
async def process_edit_value_document(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    if data.get("field") != "photo_path":
        return
    document = message.document
    if document.mime_type not in ("image/jpeg", "image/png"):
        await message.answer("Поддерживаются только форматы JPG и PNG.")
        return
    if document.file_size and document.file_size > config.max_photo_size_bytes:
        await message.answer(f"Файл слишком большой. Максимум {config.max_photo_size_mb} МБ.")
        return
    ext = "png" if document.mime_type == "image/png" else "jpg"
    photo_path = await _save_photo(bot, document.file_id, ext)
    await bouquet_repo.update_field(data["bouquet_id"], "photo_path", photo_path)
    await message.answer("✅ Фото обновлено.")
    await state.clear()


# --- Скрыть/показать букет ---------------------------------------------------------

@router.message(Command("toggle_bouquet"))
async def cmd_toggle_bouquet(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _start_choice(message, state, "adm_toggle_select")


@router.callback_query(F.data == "adm_toggle_bouquet")
async def cb_toggle_bouquet_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _start_choice(callback.message, state, "adm_toggle_select")
    await callback.answer()


@router.callback_query(F.data.startswith("adm_toggle_select:"))
async def cb_toggle_select(callback: CallbackQuery, state: FSMContext) -> None:
    bouquet_id = int(callback.data.split(":", 1)[1])
    new_value = await bouquet_repo.toggle_active(bouquet_id)
    if new_value is None:
        await callback.answer("Букет не найден", show_alert=True)
        return
    await callback.answer("Букет показан ✅" if new_value else "Букет скрыт 🚫")
    await _refresh_choice_message(callback, state)


# --- Удаление букета -----------------------------------------------------------------

@router.message(Command("delete_bouquet"))
async def cmd_delete_bouquet(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _start_choice(message, state, "adm_delete_select")


@router.callback_query(F.data == "adm_delete_bouquet")
async def cb_delete_bouquet_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _start_choice(callback.message, state, "adm_delete_select")
    await callback.answer()


@router.callback_query(F.data.startswith("adm_delete_select:"))
async def cb_delete_select(callback: CallbackQuery) -> None:
    bouquet_id = int(callback.data.split(":", 1)[1])
    bouquet = await bouquet_repo.get(bouquet_id)
    if bouquet is None:
        await callback.answer("Букет не найден", show_alert=True)
        return
    await callback.message.answer(
        f"Удалить букет «{bouquet.name}» из каталога? Это действие необратимо.",
        reply_markup=confirm_delete_kb(bouquet_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_delete_confirm:"))
async def cb_delete_confirm(callback: CallbackQuery) -> None:
    bouquet_id = int(callback.data.split(":", 1)[1])
    await bouquet_repo.delete(bouquet_id)
    await callback.message.edit_text("🗑 Букет удалён из каталога.")
    await callback.answer()


@router.callback_query(F.data == "adm_delete_cancel")
async def cb_delete_cancel(callback: CallbackQuery) -> None:
    await callback.message.edit_text("Удаление отменено.")
    await callback.answer()


# --- Изменение цены -------------------------------------------------------------------

@router.message(Command("set_price"))
async def cmd_set_price(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _start_choice(message, state, "adm_price_select")
    await state.set_state(SetPriceStates.choosing_bouquet)


@router.callback_query(F.data == "adm_set_price")
async def cb_set_price_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _start_choice(callback.message, state, "adm_price_select")
    await state.set_state(SetPriceStates.choosing_bouquet)
    await callback.answer()


@router.callback_query(SetPriceStates.choosing_bouquet, F.data.startswith("adm_price_select:"))
async def cb_price_select(callback: CallbackQuery, state: FSMContext) -> None:
    bouquet_id = int(callback.data.split(":", 1)[1])
    bouquet = await bouquet_repo.get(bouquet_id)
    if bouquet is None:
        await callback.answer("Букет не найден", show_alert=True)
        return
    await state.update_data(bouquet_id=bouquet_id)
    await callback.message.answer(
        f"Текущая цена «{bouquet.name}»: {bouquet.price:.0f} ₽\nВведите новую цену."
    )
    await state.set_state(SetPriceStates.waiting_price)
    await callback.answer()


@router.message(SetPriceStates.waiting_price, F.text)
async def process_set_price(message: Message, state: FSMContext) -> None:
    price = _parse_price(message.text)
    if price is None:
        await message.answer("Введите цену числом, например 2500.")
        return
    data = await state.get_data()
    await bouquet_repo.update_field(data["bouquet_id"], "price", price)
    await message.answer(f"✅ Цена обновлена: {price:.0f} ₽")
    await state.clear()
