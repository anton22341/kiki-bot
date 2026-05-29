from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from models.db import ClubNight, HourlyStat
from repositories import stats_repo

logger = logging.getLogger(__name__)


def calc_deviation(current: float, avg: float) -> float:
    if avg == 0:
        return 0.0
    return round((current / avg - 1) * 100, 1)


async def get_current_night(session: AsyncSession) -> Optional[ClubNight]:
    return await stats_repo.get_current_night(session)


async def get_live_occupancy(session: AsyncSession, night_id: int) -> int:
    stats = await stats_repo.get_night_stats(session, night_id)
    inside = sum(s.girls_entered + s.boys_entered for s in stats) - sum(s.left_count for s in stats)
    return max(0, inside)


async def get_live_split(session: AsyncSession, night_id: int) -> dict:
    """Возвращает сколько девушек и парней сейчас внутри."""
    stats = await stats_repo.get_night_stats(session, night_id)
    girls_in  = sum(s.girls_entered for s in stats) - sum(s.girls_left for s in stats)
    boys_in   = sum(s.boys_entered  for s in stats) - sum(s.boys_left  for s in stats)
    girls_in  = max(0, girls_in)
    boys_in   = max(0, boys_in)
    total     = girls_in + boys_in
    ratio_g   = round(girls_in / total * 100) if total > 0 else 0
    return {
        "girls_inside": girls_in,
        "boys_inside":  boys_in,
        "ratio_girls":  ratio_g,
        "ratio_boys":   100 - ratio_g,
    }


async def get_historical_avg(session: AsyncSession, hour: int, day_of_week: str) -> float:
    hist = await stats_repo.get_historical_stats(session, day_of_week, hour)
    if not hist:
        return 0.0
    totals = [s.girls_entered + s.boys_entered for s in hist]
    return round(sum(totals) / len(totals), 1)


async def get_peak_hour(session: AsyncSession, night_id: int) -> tuple[str, int]:
    stats = await stats_repo.get_night_stats(session, night_id)
    if not stats:
        return ("—", 0)
    peak = max(stats, key=lambda s: s.girls_entered + s.boys_entered)
    return (peak.recorded_at.strftime("%H:%M"), peak.girls_entered + peak.boys_entered)


async def get_fc_conversion(session: AsyncSession, night_id: int) -> float:
    stats = await stats_repo.get_night_stats(session, night_id)
    total = sum(s.girls_entered + s.boys_entered for s in stats)
    denied = sum(s.denied for s in stats)
    if total + denied == 0:
        return 0.0
    return round(total / (total + denied) * 100, 1)


BENCHMARK_GREEN = 15   # % выше среднего → зелёный
BENCHMARK_RED   = -15  # % ниже среднего → красный


def _signal(delta: float) -> str:
    if delta > BENCHMARK_GREEN:
        return "green"
    if delta < BENCHMARK_RED:
        return "red"
    return "orange"


def _emoji(signal: str) -> str:
    return {"green": "🟢", "orange": "🟠", "red": "🔴"}.get(signal, "🟠")


async def get_benchmark(session: AsyncSession, night_id: int, hour: int, day_of_week: str) -> dict | None:
    """
    Считает benchmark на основе всех записей в БД за тот же день недели и час,
    кроме текущей ночи. Возвращает None если данных < 2 ночей.
    """
    from sqlalchemy import select, func
    from models.db import HourlyStat, ClubNight

    # Берём все записи за нужный день недели и час (кроме текущей ночи)
    result = await session.execute(
        select(HourlyStat, ClubNight)
        .join(ClubNight, HourlyStat.night_id == ClubNight.id)
        .where(
            ClubNight.day_of_week == day_of_week,
            ClubNight.id != night_id,
        )
    )
    rows = result.all()

    # Фильтруем по часу
    hist = [(s, n) for s, n in rows if s.recorded_at.hour == hour]
    if len(hist) < 2:
        return None

    # Считаем средние по часовым записям
    avg_girls  = sum(s.girls_entered for s, _ in hist) / len(hist)
    avg_boys   = sum(s.boys_entered  for s, _ in hist) / len(hist)
    avg_denied = sum(s.denied        for s, _ in hist) / len(hist)

    # Накопленный inside на этот час (по ночам)
    night_ids = list({n.id for _, n in hist})
    inside_per_night = []
    for nid in night_ids:
        night_stats_res = await session.execute(
            select(HourlyStat)
            .join(ClubNight, HourlyStat.night_id == ClubNight.id)
            .where(HourlyStat.night_id == nid)
            .where(HourlyStat.recorded_at <= next(s.recorded_at for s, n in hist if n.id == nid))
            .order_by(HourlyStat.recorded_at)
        )
        night_stats = night_stats_res.scalars().all()
        inside = max(0, sum(s.girls_entered + s.boys_entered - s.left_count for s in night_stats))
        inside_per_night.append(inside)
    avg_inside = sum(inside_per_night) / len(inside_per_night) if inside_per_night else 0

    return {
        "avg_girls":     round(avg_girls, 1),
        "avg_boys":      round(avg_boys, 1),
        "avg_inside":    round(avg_inside, 1),
        "avg_denied":    round(avg_denied, 1),
        "sample_count":  len(hist),
    }


async def get_ratio(session: AsyncSession, night_id: int) -> tuple[float, float]:
    stats = await stats_repo.get_night_stats(session, night_id)
    girls = sum(s.girls_entered for s in stats)
    boys = sum(s.boys_entered for s in stats)
    total = girls + boys
    if total == 0:
        return (0.0, 0.0)
    return (round(girls / total * 100, 1), round(boys / total * 100, 1))
