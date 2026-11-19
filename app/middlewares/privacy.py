from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.repositories import client_repo

# Эти команды/колбэки доступны и без принятого согласия на обработку ПДн
ALLOWED_CALLBACKS = {"privacy_accept", "privacy_decline"}


class PrivacyMiddleware(BaseMiddleware):
    """Блокирует доступ к боту, пока клиент не принял политику конфиденциальности."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        if isinstance(event, Message) and event.text and event.text.startswith("/start"):
            return await handler(event, data)

        if isinstance(event, CallbackQuery) and event.data in ALLOWED_CALLBACKS:
            return await handler(event, data)

        client = await client_repo.get(user.id)
        if client is None or not client.privacy_accepted:
            if isinstance(event, Message):
                await event.answer(
                    "Чтобы пользоваться ботом, примите политику конфиденциальности: /start"
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "Сначала примите политику конфиденциальности: /start", show_alert=True
                )
            return None

        data["client"] = client
        return await handler(event, data)
