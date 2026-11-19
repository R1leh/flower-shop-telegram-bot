from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards.client_kb import (
    BTN_HISTORY,
    history_review_kb,
    order_cancel_kb,
    review_rating_kb,
    review_skip_kb,
    skip_comment_kb,
    use_saved_address_kb,
)
from app.repositories import bouquet_repo, client_repo, history_repo, order_repo, review_repo
from app.services import order_service
from app.utils import texts
from app.utils.constants import CANCELLABLE_STATUSES, ORDER_STATUS_LABELS
from app.utils.states import OrderStates, ReviewStates
from app.utils.validators import is_valid_address, is_valid_name, is_valid_phone, normalize_phone

router = Router(name="client_orders")


# --- Оформление заказа --------------------------------------------------------

@router.callback_query(F.data.startswith("order_start:"))
async def cb_order_start(callback: CallbackQuery, state: FSMContext) -> None:
    bouquet_id = int(callback.data.split(":", 1)[1])
    bouquet = await bouquet_repo.get(bouquet_id)
    if bouquet is None or not bouquet.is_active:
        await callback.answer("Этот букет больше недоступен 😔", show_alert=True)
        return

    await state.update_data(bouquet_id=bouquet_id)
    await callback.message.answer(texts.ORDER_ASK_RECIPIENT_NAME)
    await state.set_state(OrderStates.recipient_name)
    await callback.answer()


@router.message(OrderStates.recipient_name, F.text)
async def process_recipient_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not is_valid_name(name):
        await message.answer(
            "Введите имя получателя, используя только буквы (от 2 до 100 символов)."
        )
        return
    await state.update_data(recipient_name=name)
    await message.answer(texts.ORDER_ASK_RECIPIENT_PHONE)
    await state.set_state(OrderStates.recipient_phone)


@router.message(OrderStates.recipient_phone, F.text)
async def process_recipient_phone(message: Message, state: FSMContext) -> None:
    phone = message.text.strip()
    if not is_valid_phone(phone):
        await message.answer("Не похоже на номер телефона. Введите ещё раз.")
        return
    await state.update_data(recipient_phone=normalize_phone(phone))

    client = await client_repo.get(message.from_user.id)
    if client and client.delivery_address:
        await message.answer(
            texts.ORDER_ASK_ADDRESS_SAVED.format(saved_address=client.delivery_address),
            reply_markup=use_saved_address_kb(),
        )
    else:
        await message.answer(texts.ORDER_ASK_ADDRESS)
    await state.set_state(OrderStates.address)


@router.callback_query(OrderStates.address, F.data == "order_use_saved_address")
async def cb_use_saved_address(callback: CallbackQuery, state: FSMContext) -> None:
    client = await client_repo.get(callback.from_user.id)
    address = client.delivery_address if client else None
    if not address:
        await callback.answer("Сохранённый адрес не найден", show_alert=True)
        return
    await state.update_data(delivery_address=address)
    await callback.message.edit_text(f"{texts.ORDER_ASK_ADDRESS}\n\n✅ {address}")
    await callback.message.answer(texts.ORDER_ASK_TIME)
    await state.set_state(OrderStates.delivery_time)
    await callback.answer()


@router.message(OrderStates.address, F.text)
async def process_address_text(message: Message, state: FSMContext) -> None:
    address = message.text.strip()
    if not is_valid_address(address):
        await message.answer(
            "Введите полный адрес доставки с номером дома (от 5 до 200 символов)."
        )
        return
    await state.update_data(delivery_address=address)
    await message.answer(texts.ORDER_ASK_TIME)
    await state.set_state(OrderStates.delivery_time)


@router.message(OrderStates.delivery_time, F.text)
async def process_delivery_time(message: Message, state: FSMContext) -> None:
    delivery_time = message.text.strip()
    if len(delivery_time) < 3:
        await message.answer("Укажите дату и время доставки текстом, например «15 мая, 14:00».")
        return
    await state.update_data(delivery_time=delivery_time)
    await message.answer(texts.ORDER_ASK_COMMENT, reply_markup=skip_comment_kb())
    await state.set_state(OrderStates.comment)


@router.message(OrderStates.comment, F.text)
async def process_comment_text(message: Message, state: FSMContext, bot: Bot) -> None:
    await state.update_data(comment=message.text.strip())
    await _finalize_order(message, message.from_user.id, state, bot)


@router.callback_query(OrderStates.comment, F.data == "order_skip_comment")
async def cb_skip_comment(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await state.update_data(comment=None)
    await callback.message.edit_text(f"{texts.ORDER_ASK_COMMENT}\n\n✅ Без комментария")
    await _finalize_order(callback.message, callback.from_user.id, state, bot)
    await callback.answer()


async def _finalize_order(message: Message, telegram_id: int, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    bouquet = await bouquet_repo.get(data["bouquet_id"])
    if bouquet is None:
        await message.answer("Букет больше недоступен. Попробуйте подобрать другой через /select.")
        await state.clear()
        return

    order_id = await order_service.create_order(
        bot=bot,
        telegram_id=telegram_id,
        bouquet=bouquet,
        recipient_name=data["recipient_name"],
        recipient_phone=data["recipient_phone"],
        delivery_address=data["delivery_address"],
        delivery_time=data["delivery_time"],
        comment=data.get("comment"),
    )
    await message.answer(
        texts.ORDER_CREATED.format(
            order_id=order_id, bouquet_name=bouquet.name, price=bouquet.price
        )
    )
    await state.clear()


# --- История заказов и отмена ---------------------------------------------------

@router.message(Command("history"))
@router.message(F.text == BTN_HISTORY)
async def cmd_history(message: Message) -> None:
    orders = await order_repo.get_by_client(message.from_user.id)
    if not orders:
        await message.answer(
            "У вас пока нет заказов. Используйте /select, чтобы подобрать букет 🌷"
        )
        return

    await message.answer(f"📜 Ваши последние заказы ({len(orders)}):")
    for order in orders:
        status_label = ORDER_STATUS_LABELS.get(order.status, order.status)
        text = (
            f"<b>Заказ #{order.id}</b> от {order.created_at}\n"
            f"💐 {order.bouquet_name}\n"
            f"💰 {order.total_price:.0f} ₽\n"
            f"Статус: {status_label}"
        )

        kb = None
        if order.status in CANCELLABLE_STATUSES:
            kb = order_cancel_kb(order.id)
        elif order.status == "completed" and order.bouquet_id:
            unrated = await history_repo.find_unrated_entry(message.from_user.id, order.bouquet_id)
            if unrated:
                kb = history_review_kb(order.bouquet_id)

        await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("order_cancel:"))
async def cb_order_cancel(callback: CallbackQuery, bot: Bot) -> None:
    order_id = int(callback.data.split(":", 1)[1])
    success, text = await order_service.cancel_order_by_client(bot, order_id, callback.from_user.id)
    if success:
        await callback.message.edit_text(text)
    else:
        await callback.answer(text, show_alert=True)
        return
    await callback.answer()


# --- Отзывы о букетах -----------------------------------------------------------

@router.callback_query(F.data.startswith("review_start:"))
async def cb_review_start(callback: CallbackQuery, state: FSMContext) -> None:
    bouquet_id = int(callback.data.split(":", 1)[1])
    entry = await history_repo.find_unrated_entry(callback.from_user.id, bouquet_id)
    if entry is None:
        await callback.answer("Вы уже оставили отзыв на этот букет. Спасибо! 🌸", show_alert=True)
        return

    await state.update_data(history_id=entry["id"], bouquet_id=bouquet_id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Оцените букет от 1 до 5 ⭐", reply_markup=review_rating_kb(entry["id"])
    )
    await state.set_state(ReviewStates.waiting_rating)
    await callback.answer()


@router.callback_query(ReviewStates.waiting_rating, F.data.startswith("review_rate:"))
async def cb_review_rate(callback: CallbackQuery, state: FSMContext) -> None:
    _, history_id, rating = callback.data.split(":")
    await state.update_data(rating=int(rating))
    await callback.message.edit_text(f"Спасибо за оценку: {'⭐' * int(rating)}")
    await callback.message.answer(
        "Хотите добавить комментарий к отзыву?", reply_markup=review_skip_kb(int(history_id))
    )
    await state.set_state(ReviewStates.waiting_text)
    await callback.answer()


@router.message(ReviewStates.waiting_text, F.text)
async def process_review_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await _save_review(message.from_user.id, data, review_text=message.text.strip())
    await message.answer("Спасибо за отзыв! 🌸")
    await state.clear()


@router.callback_query(ReviewStates.waiting_text, F.data.startswith("review_skip:"))
async def cb_review_skip(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await _save_review(callback.from_user.id, data, review_text=None)
    await callback.message.edit_text("Спасибо за оценку! 🌸")
    await state.clear()
    await callback.answer()


async def _save_review(telegram_id: int, data: dict, review_text: str | None) -> None:
    history_id = data["history_id"]
    bouquet_id = data["bouquet_id"]
    rating = data["rating"]

    await review_repo.create(bouquet_id, telegram_id, rating, review_text)
    await history_repo.set_rating(history_id, rating)
    await bouquet_repo.recalculate_rating(bouquet_id)
