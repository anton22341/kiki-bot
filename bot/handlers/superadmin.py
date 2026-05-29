from __future__ import annotations
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from models.db import User, AsyncSessionLocal
from repositories import user_repo
from bot.messages import format_users_list, format_role_granted

logger = logging.getLogger(__name__)
router = Router()


def _require_superadmin(role: str) -> bool:
    return role == "superadmin"


@router.message(Command("users"))
async def cmd_users(message: Message, role: str) -> None:
    if not _require_superadmin(role):
        await message.answer("⛔ Только для superadmin.")
        return
    async with AsyncSessionLocal() as session:
        users = await user_repo.get_all(session)
    from config import settings
    users = [u for u in users if u.telegram_id != settings.SUPERADMIN_ID]
    await message.answer(format_users_list(users))


@router.message(Command("addowner"))
async def cmd_addowner(message: Message, role: str, user: User) -> None:
    await _set_role_cmd(message, role, user, "owner")


@router.message(Command("addadmin"))
async def cmd_addadmin(message: Message, role: str, user: User) -> None:
    await _set_role_cmd(message, role, user, "admin")


async def _set_role_cmd(message: Message, role: str, actor: User, new_role: str) -> None:
    if not _require_superadmin(role):
        await message.answer("⛔ Только для superadmin.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(f"Использование: /{message.text.split()[0].lstrip('/')} @username")
        return

    target_str = args[1].strip()
    async with AsyncSessionLocal() as session:
        if target_str.lstrip("@").isdigit():
            target = await user_repo.get_by_telegram_id(session, int(target_str))
        else:
            target = await user_repo.get_by_username(session, target_str)

        if not target:
            await message.answer("Пользователь не найден. Попроси его написать /start боту сначала.")
            return

        await user_repo.set_role(session, target.telegram_id, new_role, added_by_id=actor.id)

    try:
        await message.bot.send_message(target.telegram_id, format_role_granted(new_role))
    except Exception:
        logger.warning("Could not notify user %s", target.telegram_id)

    uname = f"@{target.username}" if target.username else str(target.telegram_id)
    await message.answer(f"✅ {uname} теперь {new_role}.")


@router.message(Command("removeuser"))
async def cmd_removeuser(message: Message, role: str) -> None:
    if not _require_superadmin(role):
        await message.answer("⛔ Только для superadmin.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /removeuser @username")
        return

    target_str = args[1].strip()
    async with AsyncSessionLocal() as session:
        if target_str.lstrip("@").isdigit():
            target = await user_repo.get_by_telegram_id(session, int(target_str))
        else:
            target = await user_repo.get_by_username(session, target_str)

        if not target:
            await message.answer("Пользователь не найден.")
            return

        await user_repo.set_role(session, target.telegram_id, "pending")

    uname = f"@{target.username}" if target.username else str(target.telegram_id)
    await message.answer(f"✅ {uname} — доступ отозван.")
