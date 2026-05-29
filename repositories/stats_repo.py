from __future__ import annotations
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from utils.time import now_msk
from models.db import ClubNight, HourlyStat, EditLog

logger = logging.getLogger(__name__)

DAY_MAP = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}


async def get_or_create_night(session: AsyncSession, date: str, day_of_week: str) -> ClubNight:
    result = await session.execute(select(ClubNight).where(ClubNight.date == date))
    night = result.scalar_one_or_none()
    if not night:
        night = ClubNight(date=date, day_of_week=day_of_week, opened_at=now_msk())
        session.add(night)
        await session.commit()
        await session.refresh(night)
    return night


async def get_current_night(session: AsyncSession) -> Optional[ClubNight]:
    result = await session.execute(
        select(ClubNight)
        .where(ClubNight.closed_at.is_(None))
        .order_by(ClubNight.opened_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def save_stat(session: AsyncSession, night_id: int, data: dict) -> HourlyStat:
    girls_left = data.get("girls_left", 0)
    boys_left  = data.get("boys_left",  0)
    stat = HourlyStat(
        night_id=night_id,
        recorded_at=data["recorded_at"],
        is_manual_time=data.get("is_manual_time", False),
        girls_entered=data.get("girls_entered", 0),
        boys_entered=data.get("boys_entered", 0),
        denied=data.get("denied", 0),
        girls_left=girls_left,
        boys_left=boys_left,
        left_count=girls_left + boys_left,
        created_by=data.get("created_by"),
    )
    session.add(stat)
    await session.commit()
    await session.refresh(stat)
    return stat


async def get_night_stats(session: AsyncSession, night_id: int) -> list[HourlyStat]:
    result = await session.execute(
        select(HourlyStat).where(HourlyStat.night_id == night_id).order_by(HourlyStat.recorded_at)
    )
    return list(result.scalars().all())


async def get_historical_stats(session: AsyncSession, day_of_week: str, hour: int) -> list[HourlyStat]:
    result = await session.execute(
        select(HourlyStat)
        .join(ClubNight)
        .where(
            ClubNight.day_of_week == day_of_week,
            ClubNight.closed_at.isnot(None),
            func.extract("hour", HourlyStat.recorded_at) == hour,
        )
    )
    return list(result.scalars().all())


async def save_edit_log(
    session: AsyncSession,
    stat_id: int,
    field: str,
    old_val: str,
    new_val: str,
    user_id: int,
) -> EditLog:
    log = EditLog(
        stat_id=stat_id,
        field_name=field,
        old_value=old_val,
        new_value=new_val,
        edited_by=user_id,
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log


async def get_edit_logs(session: AsyncSession, limit: int = 20) -> list[EditLog]:
    result = await session.execute(
        select(EditLog).order_by(EditLog.edited_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def get_stat_by_id(session: AsyncSession, stat_id: int) -> Optional[HourlyStat]:
    result = await session.execute(select(HourlyStat).where(HourlyStat.id == stat_id))
    return result.scalar_one_or_none()


async def close_night(session: AsyncSession, night_id: int) -> None:
    result = await session.execute(select(ClubNight).where(ClubNight.id == night_id))
    night = result.scalar_one_or_none()
    if night:
        night.closed_at = now_msk()
        await session.commit()
