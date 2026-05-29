from __future__ import annotations
import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from models.db import AsyncSessionLocal
from repositories import stats_repo
from services import stats_service, report_service

logger = logging.getLogger(__name__)
router = Router()

ALLOWED_ROLES = {"superadmin", "owner"}


@router.message(Command("live"))
async def cmd_live(message: Message, role: str) -> None:
    if role not in ALLOWED_ROLES:
        await message.answer("⛔ Только для owner.")
        return

    async with AsyncSessionLocal() as session:
        night = await stats_service.get_current_night(session)
        if not night:
            await message.answer("🔴 Активной ночи нет. Данные ещё не введены.")
            return

        inside = await stats_service.get_live_occupancy(session, night.id)
        peak_time, peak_val = await stats_service.get_peak_hour(session, night.id)
        fc = await stats_service.get_fc_conversion(session, night.id)
        ratio_g, ratio_b = await stats_service.get_ratio(session, night.id)
        hist_avg = await stats_service.get_historical_avg(session, __import__("datetime").datetime.utcnow().hour, night.day_of_week)
        dev = stats_service.calc_deviation(inside, hist_avg)
        dev_str = f"+{dev:.0f}% 📈" if dev > 0 else f"{dev:.0f}% 📉" if dev < 0 else "—"

        stats = await stats_repo.get_night_stats(session, night.id)
        total_girls = sum(s.girls_entered for s in stats)
        total_boys = sum(s.boys_entered for s in stats)
        total_left = sum(s.left_count for s in stats)
        total_denied = sum(s.denied for s in stats)

    capacity = 200
    bar = __import__("bot.messages", fromlist=["progress_bar"]).progress_bar(inside, capacity, 15)
    pct = round(inside / capacity * 100)
    import datetime
    now_str = datetime.datetime.utcnow().strftime("%H:%M")

    text = (
        f"🟢 KIKI — Live сейчас\n\n"
        f"👥 Внутри: {inside} чел\n"
        f"📊 Загрузка: {bar} {pct}%\n\n"
        f"👧 Девушки: {total_girls}  👦 Парни: {total_boys}\n"
        f"🚪 Ушло: {total_left}    🚫 Отказано: {total_denied}\n\n"
        f"🔥 Пик: {peak_time} — {peak_val} чел\n"
        f"📈 vs история {night.day_of_week}: {dev_str}\n"
        f"🕐 Обновлено: {now_str}"
    )
    await message.answer(text)


@router.message(Command("night"))
async def cmd_night(message: Message, role: str) -> None:
    if role not in ALLOWED_ROLES:
        await message.answer("⛔ Только для owner.")
        return
    async with AsyncSessionLocal() as session:
        night = await stats_service.get_current_night(session)
        if not night:
            from sqlalchemy import select
            from models.db import ClubNight
            result = await session.execute(select(ClubNight).order_by(ClubNight.opened_at.desc()).limit(1))
            night = result.scalar_one_or_none()
        if not night:
            await message.answer("Данных нет.")
            return
        report = await report_service.build_night_report(session, night.id)
    await message.answer(report)


@router.message(Command("week"))
async def cmd_week(message: Message, role: str) -> None:
    if role not in ALLOWED_ROLES:
        await message.answer("⛔ Только для owner.")
        return
    async with AsyncSessionLocal() as session:
        report = await report_service.build_week_report(session)
    await message.answer(report)


@router.message(Command("month"))
async def cmd_month(message: Message, role: str) -> None:
    if role not in ALLOWED_ROLES:
        await message.answer("⛔ Только для owner.")
        return
    async with AsyncSessionLocal() as session:
        report = await report_service.build_month_report(session)
    await message.answer(report)


@router.message(Command("kpi"))
async def cmd_kpi(message: Message, role: str) -> None:
    if role not in ALLOWED_ROLES:
        await message.answer("⛔ Только для owner.")
        return
    async with AsyncSessionLocal() as session:
        report = await report_service.build_kpi_report(session)
    await message.answer(report)


@router.message(Command("logs"))
async def cmd_logs(message: Message, role: str) -> None:
    if role not in ALLOWED_ROLES:
        await message.answer("⛔ Только для owner.")
        return
    async with AsyncSessionLocal() as session:
        report = await report_service.build_edit_logs_report(session)
    await message.answer(report)
