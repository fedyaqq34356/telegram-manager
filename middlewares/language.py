from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from database.db import get_user

class LanguageMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any]
    ) -> Any:
        user = None
        if isinstance(event, Update):
            if event.message:
                user = await get_user(event.message.from_user.id)
            elif event.callback_query:
                user = await get_user(event.callback_query.from_user.id)

        data['lang'] = user['language'] if user else 'ru'
        return await handler(event, data)