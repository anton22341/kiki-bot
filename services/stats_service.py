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


async def get_ratio(session: AsyncSession, night_id: int) -> tuple[float, float]:
    stats = await stats_repo.get_night_stats(session, night_id)
    girls = sum(s.girls_entered for s in stats)
    boys = sum(s.boys_entered for s in stats)
    total = girls + boys
    if total == 0:
        return (0.0, 0.0)
    return (round(girls / total * 100, 1), round(boys / total * 100, 1))
