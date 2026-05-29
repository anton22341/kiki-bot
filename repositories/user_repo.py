from __future__ import annotations
import logging
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from models.db import User
from utils.time import now_msk

logger = logging.getLogger(__name__)


async def get_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_by_username(session: AsyncSession, username: str) -> Optional[User]:
    clean = username.lstrip("@").lower()
    result = await session.execute(
        select(User).where(User.username.ilike(clean))
    )
    return result.scalar_one_or_none()


async def set_role(session: AsyncSession, telegram_id: int, role: str, added_by_id: Optional[int] = None) -> Optional[User]:
    from datetime import datetime
    await session.execute(
        update(User)
        .where(User.telegram_id == telegram_id)
        .values(role=role, role_set_at=now_msk(), added_by=added_by_id)
    )
    await session.commit()
    return await get_by_telegram_id(session, telegram_id)


async def get_all(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())


async def get_by_role(session: AsyncSession, role: str) -> list[User]:
    result = await session.execute(select(User).where(User.role == role).order_by(User.created_at))
    return list(result.scalars().all())


async def get_pending(session: AsyncSession) -> list[User]:
    return await get_by_role(session, "pending")


async def create_pending(session: AsyncSession, telegram_id: int, username: Optional[str], full_name: Optional[str]) -> User:
    user = User(
        telegram_id=telegram_id,
        username=username,
        full_name=full_name,
        role="pending",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def remove_user(session: AsyncSession, telegram_id: int) -> bool:
    user = await get_by_telegram_id(session, telegram_id)
    if not user:
        return False
    await session.delete(user)
    await session.commit()
    return True
