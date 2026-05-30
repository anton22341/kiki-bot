from __future__ import annotations
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from models.db import AsyncSessionLocal
from repositories import stats_repo, user_repo
from services import stats_service, report_service

logger = logging.getLogger(__name__)


async def close_night_job(bot: Bot) -> None:
    """Закрывает открытую ночь в 8:00 МСК и отправляет итог."""
    from sqlalchemy import select
    from models.db import ClubNight
    from utils.time import now_msk
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ClubNight).where(ClubNight.closed_at.is_(None)).order_by(ClubNight.opened_at.desc()).limit(1)
        )
        night = result.scalar_one_or_none()
        if not night:
            return
        night.closed_at = now_msk()
        await session.commit()
        logger.info("Night %s auto-closed at 8:00", night.date)

        report = await report_service.build_night_report(session, night.id)
        owners = await user_repo.get_by_role(session, "owner")
        superadmins = await user_repo.get_by_role(session, "superadmin")

    for user in owners + superadmins:
        try:
            await bot.send_message(user.telegram_id, f"🌅 Ночь завершена автоматически\n\n{report}")
        except Exception as e:
            logger.error("Failed to send night report to %s: %s", user.telegram_id, e)


async def hourly_report(bot: Bot) -> None:
    async with AsyncSessionLocal() as session:
        night = await stats_service.get_current_night(session)
        if not night:
            return
        report = await report_service.build_hourly_report(session, night)
        if not report:
            return
        owners = await user_repo.get_by_role(session, "owner")
        superadmins = await user_repo.get_by_role(session, "superadmin")

    for user in owners + superadmins:
        try:
            await bot.send_message(user.telegram_id, report)
        except Exception as e:
            logger.error("Failed to send hourly report to %s: %s", user.telegram_id, e)


def start_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        hourly_report,
        trigger="cron",
        hour="23,0,1,2,3,4,5",
        minute=5,
        args=[bot],
    )
    scheduler.add_job(
        close_night_job,
        trigger="cron",
        hour=8,
        minute=0,
        args=[bot],
    )
    scheduler.start()
    logger.info("Scheduler started")
    return scheduler
