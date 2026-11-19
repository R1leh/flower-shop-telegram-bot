from aiogram.types import (
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.utils.constants import BUDGETS, COLORS, MOODS, OCCASIONS, RECIPIENTS, SEASONS

# --- Главное меню (Reply-клавиатура) ----------------------------------------

BTN_SELECT = "🌷 Подобрать букет"
BTN_PROFILE = "👤 Профиль"
BTN_HISTORY = "📜 История заказов"
BTN_FAVORITES = "❤️ Избранное"
BTN_REMINDERS = "⏰ Напоминания"
BTN_LOYALTY = "🎁 Программа лояльности"
BTN_HELP = "ℹ️ Помощь"


def main_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=BTN_SELECT)
    builder.button(text=BTN_PROFILE)
    builder.button(text=BTN_HISTORY)
    builder.button(text=BTN_FAVORITES)
    builder.button(text=BTN_REMINDERS)
    builder.button(text=BTN_LOYALTY)
    builder.button(text=BTN_HELP)
    builder.adjust(1, 2, 2, 2)
    return builder.as_markup(resize_keyboard=True)


# --- Согласие на обработку персональных данных ------------------------------

def privacy_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принимаю", callback_data="privacy_accept")
    builder.button(text="❌ Не принимаю", callback_data="privacy_decline")
    builder.adjust(1)
    return builder.as_markup()


# --- Регистрация --------------------------------------------------------------

def phone_request_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📱 Отправить номер телефона", request_contact=True))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


# --- Подбор букета: шаги ------------------------------------------------------

def _options_kb(options: list[tuple], prefix: str, columns: int = 2) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code, label, *_ in options:
        builder.button(text=label, callback_data=f"{prefix}:{code}")
    builder.adjust(columns)
    return builder.as_markup()


def occasion_kb() -> InlineKeyboardMarkup:
    return _options_kb(OCCASIONS, "sel_occ", 2)


def recipient_kb() -> InlineKeyboardMarkup:
    return _options_kb(RECIPIENTS, "sel_rcp", 2)


def budget_kb() -> InlineKeyboardMarkup:
    return _options_kb(BUDGETS, "sel_bud", 1)


def season_kb() -> InlineKeyboardMarkup:
    return _options_kb(SEASONS, "sel_season", 2)


def mood_kb() -> InlineKeyboardMarkup:
    return _options_kb(MOODS, "sel_mood", 2)


def color_kb() -> InlineKeyboardMarkup:
    return _options_kb(COLORS, "sel_color", 2)


def flowers_skip_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Пропустить", callback_data="sel_flowers_skip")
    return builder.as_markup()


# --- Результаты подбора ------------------------------------------------------

def bouquet_card_kb(bouquet_id: int, is_favorite: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Заказать", callback_data=f"order_start:{bouquet_id}")
    fav_text = "💔 Из избранного" if is_favorite else "❤️ В избранное"
    builder.button(text=fav_text, callback_data=f"fav_toggle:{bouquet_id}")
    builder.adjust(2)
    return builder.as_markup()


def more_results_kb(has_more: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if has_more:
        builder.button(text="👀 Показать ещё", callback_data="sel_more")
    builder.button(text="🔄 Подобрать заново", callback_data="sel_restart")
    builder.adjust(1)
    return builder.as_markup()


# --- Оформление заказа --------------------------------------------------------

def use_saved_address_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📍 Использовать сохранённый адрес", callback_data="order_use_saved_address")
    return builder.as_markup()


def skip_comment_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Пропустить", callback_data="order_skip_comment")
    return builder.as_markup()


def order_cancel_kb(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🚫 Отменить заказ", callback_data=f"order_cancel:{order_id}")
    return builder.as_markup()


# --- Избранное -----------------------------------------------------------------

def favorite_item_kb(bouquet_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Заказать", callback_data=f"order_start:{bouquet_id}")
    builder.button(text="🗑 Удалить", callback_data=f"fav_remove:{bouquet_id}")
    builder.adjust(2)
    return builder.as_markup()


# --- Напоминания -----------------------------------------------------------------

REMINDER_OCCASIONS = [
    ("birthday", "🎂 День рождения"),
    ("anniversary", "💍 Годовщина"),
    ("holiday", "🎉 Праздник"),
    ("other", "✨ Другое"),
]


def reminder_occasion_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code, label in REMINDER_OCCASIONS:
        builder.button(text=label, callback_data=f"rem_occ:{code}")
    builder.adjust(2)
    return builder.as_markup()


def reminder_item_kb(reminder_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🗑 Удалить напоминание", callback_data=f"rem_delete:{reminder_id}")
    return builder.as_markup()


# --- Отзывы -----------------------------------------------------------------------

def review_rating_kb(history_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for n in range(1, 6):
        builder.button(text="⭐" * n, callback_data=f"review_rate:{history_id}:{n}")
    builder.adjust(5)
    return builder.as_markup()


def review_skip_kb(history_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Пропустить", callback_data=f"review_skip:{history_id}")
    return builder.as_markup()


def history_review_kb(bouquet_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐ Оставить отзыв", callback_data=f"review_start:{bouquet_id}")
    return builder.as_markup()


# --- Профиль -----------------------------------------------------------------------

def profile_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Имя", callback_data="profile_edit:full_name")
    builder.button(text="📱 Телефон", callback_data="profile_edit:phone")
    builder.button(text="📍 Адрес доставки", callback_data="profile_edit:delivery_address")
    builder.button(text="🎂 Дата рождения", callback_data="profile_edit:birth_date")
    builder.adjust(2)
    return builder.as_markup()
