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

        import datetime as _dt
        now = _dt.datetime.utcnow()
        cur_hour = now.hour

        inside = await stats_service.get_live_occupancy(session, night.id)
        split  = await stats_service.get_live_split(session, night.id)
        peak_time, peak_val = await stats_service.get_peak_hour(session, night.id)
        fc = await stats_service.get_fc_conversion(session, night.id)

        stats = await stats_repo.get_night_stats(session, night.id)
        total_girls  = sum(s.girls_entered for s in stats)
        total_boys   = sum(s.boys_entered  for s in stats)
        total_left   = sum(s.left_count    for s in stats)
        total_denied = sum(s.denied        for s in stats)

        bm = await stats_service.get_benchmark(session, night.id, cur_hour, night.day_of_week)

    from bot.messages import progress_bar
    capacity = 200
    bar = progress_bar(inside, capacity, 15)
    pct = round(inside / capacity * 100)
    now_str = now.strftime("%H:%M")

    dow_ru = {"fri": "пятницам", "sat": "субботам", "sun": "воскресеньям",
              "mon": "понедельникам", "tue": "вторникам", "wed": "средам", "thu": "четвергам"}

    def fmt_delta(cur, avg):
        if avg == 0:
            return ""
        d = round((cur / avg - 1) * 100)
        sig = stats_service._signal(d)
        em  = stats_service._emoji(sig)
        return f"  {em} {'+' if d >= 0 else ''}{d}% vs avg"

    inside_delta = fmt_delta(inside, bm["avg_inside"]) if bm else ""
    girls_delta  = fmt_delta(split["girls_inside"], bm["avg_girls"]) if bm else ""
    boys_delta   = fmt_delta(split["boys_inside"],  bm["avg_boys"])  if bm else ""

    text = (
        f"🟢 KIKI — Live сейчас\n\n"
        f"👥 Внутри: {inside} чел{inside_delta}\n"
        f"📊 Загрузка: {bar} {pct}%\n\n"
        f"👧 Девушки: {split['girls_inside']}{girls_delta}\n"
        f"👦 Парни: {split['boys_inside']}{boys_delta}\n"
        f"🚫 Отказано: {total_denied}\n\n"
        f"🔥 Пик: {peak_time} — {peak_val} чел\n"
        f"🎯 FC конверсия: {fc}%\n"
    )
    if bm:
        text += (
            f"\n📊 Ср по {dow_ru.get(night.day_of_week, night.day_of_week)} в {cur_hour:02d}:00:\n"
            f"   Внутри: ~{bm['avg_inside']:.0f}  "
            f"Девушки: ~{bm['avg_girls']:.0f}  Парни: ~{bm['avg_boys']:.0f}\n"
            f"   (выборка: {bm['sample_count']} ночей)\n"
        )
    text += f"🕐 Обновлено: {now_str}"
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
