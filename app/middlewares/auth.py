from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.utils.config import config


class AdminMiddleware(BaseMiddleware):
    """Пропускает только пользователей из ADMIN_IDS, остальным не отвечает."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None or user.id not in config.admin_ids:
            return None
        return await handler(event, data)
