import logging
from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from models.db import AsyncSessionLocal
from repositories import user_repo

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from_user = None
        if isinstance(event, Message):
            from_user = event.from_user
        elif isinstance(event, CallbackQuery):
            from_user = event.from_user

        if not from_user:
            return await handler(event, data)

        async with AsyncSessionLocal() as session:
            user = await user_repo.get_by_telegram_id(session, from_user.id)
            if not user:
                user = await user_repo.create_pending(
                    session,
                    telegram_id=from_user.id,
                    username=from_user.username,
                    full_name=from_user.full_name,
                )
                logger.info("New pending user: %s", from_user.id)

            data["user"] = user
            data["role"] = user.role
            data["session"] = session

            if user.role == "pending":
                if isinstance(event, Message):
                    await event.answer(
                        "🚫 У тебя нет доступа к боту.\n\nОбратись к администратору."
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer("Нет доступа", show_alert=True)
                return

            return await handler(event, data)
