from __future__ import annotations
import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from models.db import AsyncSessionLocal
from repositories import stats_repo
from services import stats_service, report_service
from utils.time import now_msk

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

        now = now_msk()
        stats = await stats_repo.get_night_stats(session, night.id)
        ns    = stats_service.compute_night_stats(stats)
        last_h_time = ns["hourly"][-1]["time"] if ns["hourly"] else None
        cur_hour = int(last_h_time.split(":")[0]) if last_h_time else now.hour
        bm    = await stats_service.get_benchmark(session, night.id, cur_hour, night.day_of_week)

    from bot.messages import progress_bar
    inside       = ns["inside"]
    total_girls  = ns["total_girls"]
    total_boys   = ns["total_boys"]
    total_denied = ns["total_denied"]
    hourly       = ns["hourly"]
    last_h       = hourly[-1] if hourly else None
    peak_h       = max(hourly, key=lambda h: h["entered"]) if hourly else None
    peak_time    = peak_h["time"]    if peak_h else "—"
    peak_val     = peak_h["entered"] if peak_h else 0
    fc           = round(ns["total"] / (ns["total"] + total_denied) * 100) if (ns["total"] + total_denied) > 0 else 0

    capacity = 200
    bar = progress_bar(inside, capacity, 15)
    pct = round(inside / capacity * 100)
    now_str = now.strftime("%H:%M")

    dow_ru = {"fri": "пятницам", "sat": "субботам", "sun": "воскресеньям",
              "mon": "понедельникам", "tue": "вторникам", "wed": "средам", "thu": "четвергам"}

    def fmt_delta(cur, avg):
        if not avg:
            return ""
        d = round((cur / avg - 1) * 100)
        em = stats_service._emoji(stats_service._signal(d))
        return f" {em} {'+' if d >= 0 else ''}{d}% vs avg"

    # Для бенчмарка сравниваем дельту последнего часа, не накопленный итог
    last_g = last_h["girls"]   if last_h else 0
    last_b = last_h["boys"]    if last_h else 0
    girls_delta = fmt_delta(last_g,         bm["avg_girls"]) if bm else ""
    boys_delta  = fmt_delta(last_b,         bm["avg_boys"])  if bm else ""
    total_delta = fmt_delta(last_g + last_b, bm["avg_total"]) if bm else ""

    text = (
        f"🟢 KIKI — Live сейчас\n\n"
        f"👥 Внутри: {inside} чел\n"
        f"📊 Загрузка: {bar} {pct}%\n\n"
        f"👧 Девушки: {total_girls}{girls_delta}\n"
        f"👦 Парни: {total_boys}{boys_delta}\n"
        f"🚫 Отказано: {total_denied}\n"
        f"📥 Всего вошло: {total_girls + total_boys}{total_delta}\n\n"
        f"🔥 Пик: {peak_time} — {peak_val} чел\n"
        f"🎯 FC конверсия: {fc}%\n"
    )
    if bm:
        text += (
            f"\n📊 Ср по {dow_ru.get(night.day_of_week, night.day_of_week)} "
            f"в {bm.get('used_hour', cur_hour):02d}:{bm.get('used_minute', 0):02d} "
            f"({bm['sample_count']} ночей):\n"
            f"   Д: ~{bm['avg_girls']:.0f} | П: ~{bm['avg_boys']:.0f} | Всего: ~{bm['avg_total']:.0f}\n"
        )
    text += f"\n🕐 Обновлено: {now_str}"
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
