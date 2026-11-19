from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.models.bouquet import Bouquet
from app.utils.constants import (
    BOUQUET_COLORS,
    BOUQUET_SEASONS,
    FINAL_STATUSES,
    MOODS,
    OCCASIONS,
    RECIPIENTS,
)


def _options_kb(options: list[tuple], prefix: str, columns: int = 2) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code, label, *_ in options:
        builder.button(text=label, callback_data=f"{prefix}:{code}")
    builder.adjust(columns)
    return builder.as_markup()


# --- Главное меню админа ------------------------------------------------------

def admin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Активные заказы", callback_data="adm_orders")
    builder.button(text="📊 Статистика", callback_data="adm_stats")
    builder.button(text="🌸 Каталог", callback_data="adm_catalog")
    builder.adjust(1)
    return builder.as_markup()


def catalog_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить букет", callback_data="adm_add_bouquet")
    builder.button(text="📃 Список букетов", callback_data="adm_list_bouquets")
    builder.button(text="✏️ Редактировать", callback_data="adm_edit_bouquet")
    builder.button(text="💰 Изменить цену", callback_data="adm_set_price")
    builder.button(text="👁 Скрыть/показать", callback_data="adm_toggle_bouquet")
    builder.button(text="🗑 Удалить", callback_data="adm_delete_bouquet")
    builder.adjust(2)
    return builder.as_markup()


# --- Новая заявка / смена статуса заказа --------------------------------------

def new_order_kb(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принять", callback_data=f"adm_status:{order_id}:accepted")
    builder.button(text="❌ Отклонить", callback_data=f"adm_status:{order_id}:rejected")
    builder.adjust(2)
    return builder.as_markup()


NEXT_STATUS_LABELS: dict[str, str] = {
    "new": "✅ Принять",
    "accepted": "💐 На сборку",
    "assembling": "📦 Готов",
    "ready": "🚚 В доставку",
    "delivery": "🏁 Завершить",
}

NEXT_STATUS_MAP: dict[str, str] = {
    "new": "accepted",
    "accepted": "assembling",
    "assembling": "ready",
    "ready": "delivery",
    "delivery": "completed",
}


def order_status_kb(order_id: int, current_status: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    next_status = NEXT_STATUS_MAP.get(current_status)
    if next_status:
        builder.button(
            text=NEXT_STATUS_LABELS[current_status],
            callback_data=f"adm_status:{order_id}:{next_status}",
        )
    if current_status not in FINAL_STATUSES:
        if current_status == "new":
            reject_status, reject_label = "rejected", "❌ Отклонить"
        else:
            reject_status, reject_label = "cancelled", "🚫 Отменить"
        builder.button(
            text=reject_label, callback_data=f"adm_status:{order_id}:{reject_status}"
        )
    builder.adjust(1)
    return builder.as_markup()


def orders_pagination_kb(page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if has_prev:
        builder.button(text="⬅️ Назад", callback_data=f"adm_orders_page:{page - 1}")
    if has_next:
        builder.button(text="Вперёд ➡️", callback_data=f"adm_orders_page:{page + 1}")
    builder.adjust(2)
    return builder.as_markup()


# --- Выбор букета из каталога (для редактирования/удаления/цены/видимости) ---

def bouquet_choice_kb(
    bouquets: list[Bouquet], action: str, page: int, has_next: bool
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for bouquet in bouquets:
        status_icon = "🟢" if bouquet.is_active else "⚪️"
        builder.button(
            text=f"{status_icon} {bouquet.name} — {bouquet.price:.0f}₽",
            callback_data=f"{action}:{bouquet.id}",
        )
    builder.adjust(1)

    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"adm_bq_page:{action}:{page - 1}")
        )
    if has_next:
        nav_buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"adm_bq_page:{action}:{page + 1}")
        )
    if nav_buttons:
        builder.row(*nav_buttons)
    return builder.as_markup()


def catalog_pagination_kb(page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if has_prev:
        builder.button(text="⬅️ Назад", callback_data=f"adm_catalog_page:{page - 1}")
    if has_next:
        builder.button(text="Вперёд ➡️", callback_data=f"adm_catalog_page:{page + 1}")
    builder.adjust(2)
    return builder.as_markup()


def confirm_delete_kb(bouquet_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🗑 Да, удалить", callback_data=f"adm_delete_confirm:{bouquet_id}")
    builder.button(text="Отмена", callback_data="adm_delete_cancel")
    builder.adjust(2)
    return builder.as_markup()


# --- Поля букета для добавления/редактирования ---------------------------------

EDIT_FIELDS: list[tuple[str, str]] = [
    ("name", "Название"),
    ("description", "Описание"),
    ("price", "Цена"),
    ("occasion", "Повод"),
    ("season", "Сезон"),
    ("mood", "Настроение"),
    ("colors", "Цвета"),
    ("recipient", "Получатель"),
    ("photo_path", "Фото"),
]


def edit_field_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for field, label in EDIT_FIELDS:
        builder.button(text=label, callback_data=f"adm_edit_field:{field}")
    builder.adjust(2)
    return builder.as_markup()


def bouquet_occasion_kb(prefix: str = "bq_occ") -> InlineKeyboardMarkup:
    return _options_kb(OCCASIONS, prefix, 2)


def bouquet_recipient_kb(prefix: str = "bq_rcp") -> InlineKeyboardMarkup:
    return _options_kb(RECIPIENTS, prefix, 2)


def bouquet_season_kb(prefix: str = "bq_season") -> InlineKeyboardMarkup:
    return _options_kb(BOUQUET_SEASONS, prefix, 2)


def bouquet_mood_kb(prefix: str = "bq_mood") -> InlineKeyboardMarkup:
    return _options_kb(MOODS, prefix, 2)


def bouquet_colors_kb(selected: list[str], prefix: str = "bq_color") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code, label in BOUQUET_COLORS:
        mark = "✅ " if code in selected else ""
        builder.button(text=f"{mark}{label}", callback_data=f"{prefix}:{code}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="Готово ➡️", callback_data=f"{prefix}_done"))
    return builder.as_markup()


def skip_photo_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Пропустить", callback_data="bq_photo_skip")
    return builder.as_markup()


def keep_value_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Оставить без изменений", callback_data="adm_edit_keep")
    return builder.as_markup()


# --- Статистика -----------------------------------------------------------------

STATS_PERIODS: list[tuple[str, str]] = [
    ("today", "Сегодня"),
    ("week", "Неделя"),
    ("month", "Месяц"),
    ("all", "Всё время"),
]


def stats_period_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code, label in STATS_PERIODS:
        builder.button(text=label, callback_data=f"adm_stats_period:{code}")
    builder.adjust(2)
    return builder.as_markup()


def stats_result_kb(period_code: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📥 Выгрузить заказы в Excel", callback_data=f"adm_export:{period_code}")
    return builder.as_markup()
