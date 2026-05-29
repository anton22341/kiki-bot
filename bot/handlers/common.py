from __future__ import annotations
import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from models.db import User
from bot.messages import format_start
from bot.keyboards import admin_menu, owner_menu
from config import settings

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, user: User, role: str) -> None:
    text = format_start(user)
    if role in ("admin", "superadmin"):
        kb = admin_menu(settings.WEBAPP_URL, is_superadmin=(role == "superadmin"))
        await message.answer(text, reply_markup=kb)
    elif role == "owner":
        await message.answer(text, reply_markup=owner_menu())
    else:
        await message.answer(text)


@router.message(Command("myrole"))
async def cmd_myrole(message: Message, user: User, role: str) -> None:
    icons = {"superadmin": "👑", "owner": "🏠", "admin": "👔", "pending": "⏳"}
    icon = icons.get(role, "❓")
    uname = f"@{user.username}" if user.username else str(user.telegram_id)
    await message.answer(f"{icon} {uname} — роль: {role}")
