from __future__ import annotations
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from models.db import AsyncSessionLocal
from repositories import stats_repo, user_repo
from services import stats_service, report_service

logger = logging.getLogger(__name__)


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
    scheduler.start()
    logger.info("Scheduler started")
    return scheduler
