from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """Регистрация нового клиента после согласия с политикой конфиденциальности."""

    waiting_full_name = State()
    waiting_phone = State()


class SelectionStates(StatesGroup):
    """Пошаговый подбор букета (/select)."""

    occasion = State()
    recipient = State()
    budget = State()
    season = State()
    mood = State()
    color = State()
    flowers = State()
    showing_results = State()


class OrderStates(StatesGroup):
    """Оформление заказа после выбора букета."""

    recipient_name = State()
    recipient_phone = State()
    address = State()
    delivery_time = State()
    comment = State()


class ProfileEditStates(StatesGroup):
    """Редактирование данных в личном кабинете."""

    waiting_full_name = State()
    waiting_phone = State()
    waiting_address = State()
    waiting_birth_date = State()


class ReminderStates(StatesGroup):
    """Создание напоминания о важной дате (/remind)."""

    waiting_name = State()
    waiting_date = State()
    waiting_occasion = State()


class ReviewStates(StatesGroup):
    """Оставление отзыва о букете после завершения заказа."""

    waiting_rating = State()
    waiting_text = State()


class AddBouquetStates(StatesGroup):
    """Добавление нового букета в каталог (админ)."""

    waiting_name = State()
    waiting_description = State()
    waiting_price = State()
    waiting_occasion = State()
    waiting_season = State()
    waiting_mood = State()
    waiting_colors = State()
    waiting_recipient = State()
    waiting_photo = State()


class EditBouquetStates(StatesGroup):
    """Редактирование существующего букета (админ)."""

    choosing_bouquet = State()
    choosing_field = State()
    waiting_value = State()


class SetPriceStates(StatesGroup):
    """Быстрое изменение цены букета (админ)."""

    choosing_bouquet = State()
    waiting_price = State()
