from __future__ import annotations
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from utils.time import now_msk
from models.db import ClubNight, HourlyStat, EditLog
from repositories import stats_repo
from services.stats_service import compute_night_stats, get_benchmark, _emoji, _signal
from bot.messages import progress_bar

logger = logging.getLogger(__name__)

MONTH_RU = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь",
}
MONTH_SHORT = {
    1: "Янв", 2: "Фев", 3: "Мар", 4: "Апр", 5: "Май", 6: "Июн",
    7: "Июл", 8: "Авг", 9: "Сен", 10: "Окт", 11: "Ноя", 12: "Дек",
}
WEEKDAY_RU = {"mon": "Пн", "tue": "Вт", "wed": "Ср", "thu": "Чт", "fri": "Пт", "sat": "Сб", "sun": "Вс"}
CLUB_DAYS = ("fri", "sat")


async def build_night_report(session: AsyncSession, night_id: int) -> str:
    result = await session.execute(select(ClubNight).where(ClubNight.id == night_id))
    night = result.scalar_one_or_none()
    if not night:
        return "Ночь не найдена."

    stats = await stats_repo.get_night_stats(session, night_id)
    if not stats:
        return "Данных за эту ночь нет."

    ns = compute_night_stats(stats)
    total    = ns["total"]
    denied   = ns["total_denied"]
    inside   = ns["inside"]
    hourly   = ns["hourly"]

    fc      = round(total / (total + denied) * 100) if (total + denied) > 0 else 0
    avg_occ = round(total / len(hourly)) if hourly else 0
    ratio_g = round(ns["total_girls"] / total * 100) if total > 0 else 0

    peak_h  = max(hourly, key=lambda h: h["entered"]) if hourly else None
    peak_val  = peak_h["entered"] if peak_h else 0
    peak_time = peak_h["time"]    if peak_h else "—"

    try:
        night_dt = datetime.strptime(night.date, "%Y-%m-%d")
        date_str = f"{WEEKDAY_RU.get(night.day_of_week, '')} {night_dt.day} {MONTH_SHORT.get(night_dt.month, '')}"
    except Exception:
        date_str = night.date

    lines = [f"📊 Итог ночи · {date_str}\n"]
    lines.append(f"Вошло всего:   {total}")
    lines.append(f"Пик:           {peak_val} чел ({peak_time})")
    lines.append(f"Внутри сейчас: {inside}")
    lines.append(f"\n👧 Девушки: {ratio_g}%  👦 Парни: {100 - ratio_g}%")
    lines.append(f"🎯 FC конверсия: {fc}%")
    lines.append(f"⏱ Avg за час: {avg_occ} чел")
    lines.append("\nПочасовой трафик:")

    max_val = max((h["entered"] for h in hourly), default=1)
    for h in hourly:
        entered = h["entered"]
        bar = progress_bar(entered, max_val, 8)
        bm = await get_benchmark(session, night.id, int(h["time"].split(":")[0]), night.day_of_week)
        avg_t = bm.get("avg_total", 0) if bm else 0
        if bm and avg_t > 0:
            d = round((entered / avg_t - 1) * 100)
            delta_str = f" {_emoji(_signal(d))}{'+' if d >= 0 else ''}{d}%"
        else:
            delta_str = " (сейчас)" if not night.closed_at and h == hourly[-1] else ""
        lines.append(f"{h['time']}  {bar} {entered}{delta_str}")

    # Benchmark итог: сравниваем последний час с историческим
    if hourly:
        last_h = hourly[-1]
        last_hour = int(last_h["time"].split(":")[0])
        bm_last = await get_benchmark(session, night.id, last_hour, night.day_of_week)
        if bm_last and bm_last.get("avg_total", 0) > 0:
            d_last = round((last_h["entered"] / bm_last["avg_total"] - 1) * 100)
            em = _emoji(_signal(d_last))
            lines.append(
                f"\n{em} Последний час vs история ({night.day_of_week}): "
                f"{'+' if d_last >= 0 else ''}{d_last}%"
            )

    return "\n".join(lines)


async def build_week_report(session: AsyncSession) -> str:
    now = now_msk()
    week_ago = now - timedelta(days=14)
    result = await session.execute(
        select(ClubNight)
        .where(ClubNight.date >= week_ago.strftime("%Y-%m-%d"))
        .where(ClubNight.day_of_week.in_(CLUB_DAYS))
        .order_by(ClubNight.date)
    )
    nights = list(result.scalars().all())
    if not nights:
        return "Данных за последние недели нет.\n\nКлуб работает пт/сб — данные появятся после первого ввода."

    total = 0
    best_night = None
    best_count = 0
    night_lines = []
    max_n = 1

    for night in nights:
        stats = await stats_repo.get_night_stats(session, night.id)
        ns = compute_night_stats(stats)
        entered = ns["total"]
        total += entered
        if entered > best_count:
            best_count = entered
            best_night = night
        night_lines.append((night, entered))
        if entered > max_n:
            max_n = entered

    start = datetime.strptime(nights[0].date, "%Y-%m-%d")
    end   = datetime.strptime(nights[-1].date, "%Y-%m-%d")
    date_range = f"{start.day}–{end.day} {MONTH_SHORT.get(end.month, '')}"

    lines = [f"📅 Последние ночи · {date_range}\n(только Пт и Сб)\n"]
    lines.append(f"Ночей: {len(nights)}  |  Посетителей: {total}")
    if best_night:
        bd = datetime.strptime(best_night.date, "%Y-%m-%d")
        lines.append(f"Лучшая: {WEEKDAY_RU.get(best_night.day_of_week, '')} {bd.day} — {best_count} чел")
    lines.append("")

    for night, entered in night_lines:
        bar = progress_bar(entered, max_n, 8)
        nd = datetime.strptime(night.date, "%Y-%m-%d")
        lines.append(f"{WEEKDAY_RU.get(night.day_of_week, '')} {nd.day}  {bar} {entered}")

    return "\n".join(lines)


async def build_month_report(session: AsyncSession) -> str:
    now = now_msk()
    month_start = now.replace(day=1).strftime("%Y-%m-%d")
    result = await session.execute(
        select(ClubNight)
        .where(ClubNight.date >= month_start)
        .where(ClubNight.day_of_week.in_(CLUB_DAYS))
        .order_by(ClubNight.date)
    )
    nights = list(result.scalars().all())
    if not nights:
        return "Данных за этот месяц нет.\n\nКлуб работает пт/сб — данные появятся после первого ввода."

    totals = []
    best_night = None
    best_count = 0
    for night in nights:
        stats = await stats_repo.get_night_stats(session, night.id)
        ns = compute_night_stats(stats)
        entered = ns["total"]
        totals.append(entered)
        if entered > best_count:
            best_count = entered
            best_night = night

    total = sum(totals)
    avg = round(total / len(totals)) if totals else 0
    month_name = MONTH_RU.get(now.month, "")

    lines = [f"📆 {month_name} {now.year}\n"]
    lines.append(f"Ночей: {len(nights)}  |  Посетителей: {total}")
    lines.append(f"Avg за ночь: {avg}")
    if best_night:
        bd = datetime.strptime(best_night.date, "%Y-%m-%d")
        lines.append(f"Лучшая: {WEEKDAY_RU.get(best_night.day_of_week, '')} {bd.day} — {best_count}")

    return "\n".join(lines)


async def build_kpi_report(session: AsyncSession) -> str:
    now = now_msk()
    month_start = now.replace(day=1).strftime("%Y-%m-%d")
    result = await session.execute(
        select(ClubNight).where(ClubNight.date >= month_start).order_by(ClubNight.date)
    )
    nights = list(result.scalars().all())
    if not nights:
        return "Данных для KPI нет."

    total_g = total_b = total_denied = total_entered = 0
    peak_hour_counts: dict[int, int] = {}

    for night in nights:
        stats = await stats_repo.get_night_stats(session, night.id)
        ns = compute_night_stats(stats)
        total_entered += ns["total"]
        total_g       += ns["total_girls"]
        total_b       += ns["total_boys"]
        total_denied  += ns["total_denied"]
        for h in ns["hourly"]:
            hour = int(h["time"].split(":")[0])
            peak_hour_counts[hour] = peak_hour_counts.get(hour, 0) + h["entered"]

    fc      = round(total_entered / (total_entered + total_denied) * 100) if (total_entered + total_denied) > 0 else 0
    ratio_g = round(total_g / total_entered * 100) if total_entered > 0 else 0

    fc_ok    = "✅" if fc >= 90 else "⚠️"
    ratio_ok = "✅" if ratio_g >= 55 else "⚠️"

    peak_h   = max(peak_hour_counts, key=peak_hour_counts.get) if peak_hour_counts else None
    peak_str = f"{peak_h:02d}:00 — {(peak_h + 1) % 24:02d}:00" if peak_h is not None else "—"

    month_name = MONTH_RU.get(now.month, "")
    lines = [f"🎯 KPI · {month_name} {now.year}\n"]
    lines.append(f"FC конверсия:     {fc}%  (цель 90%) {fc_ok}")
    lines.append(f"Girls/Boys ratio:  {ratio_g}/{100 - ratio_g}           {ratio_ok}")
    lines.append(f"Ночей:             {len(nights)}")
    lines.append(f"Пиковый час:       {peak_str}")

    return "\n".join(lines)


async def build_hourly_report(session: AsyncSession, night: ClubNight) -> str:
    from services.stats_service import get_live_occupancy, get_historical_avg, calc_deviation
    stats = await stats_repo.get_night_stats(session, night.id)
    if not stats:
        return ""

    ns   = compute_night_stats(stats)
    now  = now_msk()
    last_h = ns["hourly"][-1] if ns["hourly"] else None
    hour_entered = last_h["entered"] if last_h else 0
    hour_left    = last_h["left"]    if last_h else 0
    inside       = ns["inside"]

    hist_avg = await get_historical_avg(session, now.hour, night.day_of_week)
    dev = calc_deviation(hour_entered, hist_avg)
    dev_str = f"{dev:+.0f}% 📈" if dev > 0 else f"{dev:.0f}% 📉" if dev < 0 else "—"

    return (
        f"⏱ Hourly Report · {now.strftime('%H:%M')}\n\n"
        f"Этот час: +{hour_entered} вошло · {hour_left} ушло\n"
        f"Внутри:   {inside} чел\n\n"
        f"vs история {night.day_of_week.upper()} {now.hour:02d}:00:  {dev_str}"
    )


async def build_edit_logs_report(session: AsyncSession, limit: int = 10) -> str:
    logs = await stats_repo.get_edit_logs(session, limit)
    if not logs:
        return "📝 Изменений нет."

    lines = ["📝 Последние изменения\n"]
    for i, log in enumerate(logs, 1):
        time_str = log.edited_at.strftime("%H:%M")
        lines.append(
            f"{i}. {time_str} · запись #{log.stat_id} → {log.field_name}\n"
            f"   Было {log.old_value} → Стало {log.new_value}"
        )

    return "\n".join(lines)
