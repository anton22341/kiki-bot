from __future__ import annotations
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from utils.time import now_msk
from models.db import ClubNight, HourlyStat, EditLog, User
from repositories import stats_repo
from services.stats_service import calc_deviation, get_historical_avg
from bot.messages import progress_bar

logger = logging.getLogger(__name__)

MONTH_RU = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь",
}

WEEKDAY_RU = {"mon": "Пн", "tue": "Вт", "wed": "Ср", "thu": "Чт", "fri": "Пт", "sat": "Сб", "sun": "Вс"}


async def build_night_report(session: AsyncSession, night_id: int) -> str:
    from sqlalchemy import select
    result = await session.execute(select(ClubNight).where(ClubNight.id == night_id))
    night = result.scalar_one_or_none()
    if not night:
        return "Ночь не найдена."

    stats = await stats_repo.get_night_stats(session, night_id)
    if not stats:
        return "Данных за эту ночь нет."

    total_entered = sum(s.girls_entered + s.boys_entered for s in stats)
    total_left = sum(s.left_count for s in stats)
    total_denied = sum(s.denied for s in stats)
    total_girls = sum(s.girls_entered for s in stats)
    total_boys = sum(s.boys_entered for s in stats)
    inside = max(0, total_entered - total_left)
    peak_stat = max(stats, key=lambda s: s.girls_entered + s.boys_entered)
    peak_val = peak_stat.girls_entered + peak_stat.boys_entered
    peak_time = peak_stat.recorded_at.strftime("%H:%M")

    fc = round(total_entered / (total_entered + total_denied) * 100) if (total_entered + total_denied) > 0 else 0
    avg_occ = round(total_entered / len(stats)) if stats else 0
    ratio_g = round(total_girls / total_entered * 100) if total_entered > 0 else 0

    try:
        night_dt = datetime.strptime(night.date, "%Y-%m-%d")
        date_str = f"{WEEKDAY_RU.get(night.day_of_week, '')} {night_dt.day} {list(MONTH_RU.values())[night_dt.month - 1]}"
    except Exception:
        date_str = night.date

    lines = [f"📊 Итог ночи · {date_str}\n"]
    lines.append(f"Вошло всего:   {total_entered}")
    lines.append(f"Пик:           {peak_val} чел ({peak_time})")
    lines.append(f"Внутри сейчас: {inside}")
    lines.append(f"\n👧 Девушки: {ratio_g}%  👦 Парни: {100 - ratio_g}%")
    lines.append(f"🎯 FC конверсия: {fc}%")
    lines.append(f"⏱ Avg occupancy: {avg_occ} чел")
    lines.append("\nПочасовой трафик:")

    max_val = max(s.girls_entered + s.boys_entered for s in stats)
    from services.stats_service import get_benchmark, _emoji
    for s in stats:
        entered = s.girls_entered + s.boys_entered
        bar = progress_bar(entered, max_val, 8)
        bm = await get_benchmark(session, night.id, s.recorded_at.hour, night.day_of_week)
        if bm and bm["avg_inside"] > 0:
            inside_cum = 0
            for prev in stats:
                if prev.recorded_at <= s.recorded_at:
                    inside_cum += prev.girls_entered + prev.boys_entered - prev.left_count
            inside_cum = max(0, inside_cum)
            d = round((inside_cum / bm["avg_inside"] - 1) * 100)
            delta_str = f" {_emoji('green' if d > 15 else 'red' if d < -15 else 'orange')}{'+' if d >= 0 else ''}{d}%"
        else:
            delta_str = " (сейчас)" if not night.closed_at and s == stats[-1] else ""
        lines.append(f"{s.recorded_at.strftime('%H:%M')}  {bar} {entered}{delta_str}")

    # Benchmark итог за ночь
    bm_night = await get_benchmark(session, night.id, stats[0].recorded_at.hour, night.day_of_week)
    if bm_night:
        night_avg_entered = bm_night["avg_inside"] * len(stats) if bm_night else 0
        if night_avg_entered > 0:
            d_night = round((total_entered / night_avg_entered - 1) * 100)
            em = _emoji("green" if d_night > 15 else "red" if d_night < -15 else "orange")
            lines.append(f"\n{em} vs исторический avg ({night.day_of_week}): {'+' if d_night >= 0 else ''}{d_night}%")

    return "\n".join(lines)


CLUB_DAYS = ("fri", "sat")  # клуб работает только пт и сб


async def build_week_report(session: AsyncSession) -> str:
    now = now_msk()
    # Ищем последние 2 рабочих уик-энда (8 последних ночей — с запасом)
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
        entered = sum(s.girls_entered + s.boys_entered for s in stats)
        total += entered
        if entered > best_count:
            best_count = entered
            best_night = night
        night_lines.append((night, entered))
        if entered > max_n:
            max_n = entered

    start = datetime.strptime(nights[0].date, "%Y-%m-%d")
    end = datetime.strptime(nights[-1].date, "%Y-%m-%d")
    date_range = f"{start.day}–{end.day} {list(MONTH_RU.values())[end.month - 1]}"

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
        entered = sum(s.girls_entered + s.boys_entered for s in stats)
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
        for s in stats:
            entered = s.girls_entered + s.boys_entered
            total_entered += entered
            total_g += s.girls_entered
            total_b += s.boys_entered
            total_denied += s.denied
            h = s.recorded_at.hour
            peak_hour_counts[h] = peak_hour_counts.get(h, 0) + entered

    fc = round(total_entered / (total_entered + total_denied) * 100) if (total_entered + total_denied) > 0 else 0
    ratio_g = round(total_g / total_entered * 100) if total_entered > 0 else 0

    fc_ok = "✅" if fc >= 90 else "⚠️"
    ratio_ok = "✅" if ratio_g >= 55 else "⚠️"

    peak_h = max(peak_hour_counts, key=peak_hour_counts.get) if peak_hour_counts else None
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

    now = now_msk()
    last = stats[-1]
    hour_entered = last.girls_entered + last.boys_entered
    hour_left = last.left_count
    inside = await get_live_occupancy(session, night.id)
    hist_avg = await get_historical_avg(session, now.hour, night.day_of_week)
    dev = calc_deviation(inside, hist_avg)
    dev_str = f"{dev:+.0f}% 📈" if dev > 0 else f"{dev:.0f}% 📉" if dev < 0 else "—"

    return (
        f"⏱ Hourly Report · {now.strftime('%H:%M')}\n\n"
        f"Этот час: +{hour_entered} вошло · {hour_left} ушло\n"
        f"Внутри:   {inside} чел\n\n"
        f"vs история {night.day_of_week.upper()} {now.hour:02d}:00:  {dev_str}"
    )


async def build_edit_logs_report(session: AsyncSession, limit: int = 10) -> str:
    from sqlalchemy.orm import joinedload
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
