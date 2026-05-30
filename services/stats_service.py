from __future__ import annotations
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from models.db import ClubNight, HourlyStat
from repositories import stats_repo
from utils.time import now_msk

logger = logging.getLogger(__name__)


def calc_deviation(current: float, avg: float) -> float:
    if avg == 0:
        return 0.0
    return round((current / avg - 1) * 100, 1)


def compute_night_stats(stats: list) -> dict:
    """
    Вычисляет итоги и почасовые дельты из списка HourlyStat.

    Два режима:
    - Накопительный (live, is_historical=False): каждая запись хранит
      нарастающий итог с начала ночи. Итог = последняя запись,
      почасовой поток = дельта между соседними записями.
    - Дельта (исторический импорт, is_historical=True): каждая запись
      уже хранит данные за конкретный час. Итог = сумма всех записей.
    """
    if not stats:
        return {
            "total_girls": 0, "total_boys": 0, "total": 0,
            "total_denied": 0, "total_left": 0,
            "total_girls_left": 0, "total_boys_left": 0,
            "girls_inside": 0, "boys_inside": 0, "inside": 0,
            "ratio_girls": 0, "ratio_boys": 0,
            "hourly": [],
        }

    is_delta = bool(stats[0].is_historical)

    if is_delta:
        # Исторические данные — каждая запись уже дельта
        total_girls      = sum(s.girls_entered      for s in stats)
        total_boys       = sum(s.boys_entered        for s in stats)
        total_denied     = sum(s.denied              for s in stats)
        total_girls_left = sum((s.girls_left or 0)   for s in stats)
        total_boys_left  = sum((s.boys_left  or 0)   for s in stats)
        total_left       = sum(s.left_count          for s in stats)
        hourly = [
            {
                "time":    s.recorded_at.strftime("%H:%M"),
                "entered": s.girls_entered + s.boys_entered,
                "left":    s.left_count,
                "girls":   s.girls_entered,
                "boys":    s.boys_entered,
            }
            for s in stats
        ]
    else:
        # Накопительные данные — счётчик только растёт,
        # поэтому сортируем по значению счётчика (надёжнее чем по времени,
        # т.к. 23:55 может оказаться позже 02:00 при одной дате)
        sorted_stats = sorted(stats, key=lambda s: s.girls_entered + s.boys_entered)
        last             = sorted_stats[-1]
        total_girls      = last.girls_entered
        total_boys       = last.boys_entered
        total_denied     = last.denied
        total_girls_left = last.girls_left or 0
        total_boys_left  = last.boys_left  or 0
        total_left       = last.left_count

        # Почасовые дельты в порядке роста счётчика
        hourly = []
        prev_g = prev_b = prev_gl = prev_bl = prev_l = 0
        for s in sorted_stats:
            dg  = max(0, s.girls_entered       - prev_g)
            db  = max(0, s.boys_entered        - prev_b)
            dgl = max(0, (s.girls_left or 0)   - prev_gl)
            dbl = max(0, (s.boys_left  or 0)   - prev_bl)
            dl  = max(0, s.left_count          - prev_l)
            hourly.append({
                "time":    s.recorded_at.strftime("%H:%M"),
                "entered": dg + db,
                "left":    dl,
                "girls":   dg,
                "boys":    db,
            })
            prev_g  = s.girls_entered
            prev_b  = s.boys_entered
            prev_gl = s.girls_left or 0
            prev_bl = s.boys_left  or 0
            prev_l  = s.left_count

    total        = total_girls + total_boys
    girls_inside = max(0, total_girls - total_girls_left)
    boys_inside  = max(0, total_boys  - total_boys_left)
    inside       = girls_inside + boys_inside
    ratio_girls  = round(girls_inside / inside * 100) if inside > 0 else 0

    return {
        "total_girls":      total_girls,
        "total_boys":       total_boys,
        "total":            total,
        "total_denied":     total_denied,
        "total_left":       total_left,
        "total_girls_left": total_girls_left,
        "total_boys_left":  total_boys_left,
        "girls_inside":     girls_inside,
        "boys_inside":      boys_inside,
        "inside":           inside,
        "ratio_girls":      ratio_girls,
        "ratio_boys":       100 - ratio_girls,
        "hourly":           hourly,
    }


async def get_current_night(session: AsyncSession) -> Optional[ClubNight]:
    """Возвращает текущую открытую ночь.
    Страховка: если ночь открыта, но сейчас 08:00-20:00 МСК и
    ночь началась до сегодняшних 08:00 — считаем её завершённой."""
    night = await stats_repo.get_current_night(session)
    if not night:
        return None
    now = now_msk()
    if 8 <= now.hour < 20:
        # Проверяем что ночь началась до сегодняшних 8:00
        today_8am = now.replace(hour=8, minute=0, second=0, microsecond=0)
        if night.opened_at < today_8am:
            return None  # планировщик не успел закрыть — игнорируем
    return night


async def get_live_occupancy(session: AsyncSession, night_id: int) -> int:
    stats = await stats_repo.get_night_stats(session, night_id)
    return compute_night_stats(stats)["inside"]


async def get_live_split(session: AsyncSession, night_id: int) -> dict:
    stats = await stats_repo.get_night_stats(session, night_id)
    ns = compute_night_stats(stats)
    return {
        "girls_inside": ns["girls_inside"],
        "boys_inside":  ns["boys_inside"],
        "ratio_girls":  ns["ratio_girls"],
        "ratio_boys":   ns["ratio_boys"],
    }


async def get_historical_avg(session: AsyncSession, hour: int, day_of_week: str) -> float:
    hist = await stats_repo.get_historical_stats(session, day_of_week, hour)
    if not hist:
        return 0.0
    totals = [s.girls_entered + s.boys_entered for s in hist]
    return round(sum(totals) / len(totals), 1)


async def get_peak_hour(session: AsyncSession, night_id: int) -> tuple[str, int]:
    stats = await stats_repo.get_night_stats(session, night_id)
    ns = compute_night_stats(stats)
    if not ns["hourly"]:
        return ("—", 0)
    peak = max(ns["hourly"], key=lambda h: h["entered"])
    return (peak["time"], peak["entered"])


async def get_fc_conversion(session: AsyncSession, night_id: int) -> float:
    stats = await stats_repo.get_night_stats(session, night_id)
    ns = compute_night_stats(stats)
    total  = ns["total"]
    denied = ns["total_denied"]
    if total + denied == 0:
        return 0.0
    return round(total / (total + denied) * 100, 1)


BENCHMARK_GREEN = 15
BENCHMARK_RED   = -15


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
    Почасовой benchmark: сравниваем последний введённый час с тем же часом
    в прошлых ночах. Если данных за этот час < 2 — ищем ближайший час.
    """
    from sqlalchemy import select

    result = await session.execute(
        select(ClubNight).where(
            ClubNight.day_of_week == day_of_week,
            ClubNight.id != night_id,
        )
    )
    hist_nights = result.scalars().all()
    if len(hist_nights) < 2:
        return None

    def _get_hour_delta(night_stats: list, target_hour: int):
        """
        Возвращает (girls_delta, boys_denied_delta) для конкретного часа ночи.
        Для накопительных ночей (is_historical=False) считает дельту между записями.
        Для исторических (is_historical=True) берёт значение записи напрямую.
        """
        if not night_stats:
            return None
        is_cumul = not night_stats[0].is_historical
        if is_cumul:
            sorted_s = sorted(night_stats, key=lambda s: s.girls_entered + s.boys_entered)
            for i, s in enumerate(sorted_s):
                if s.recorded_at.hour == target_hour:
                    prev = sorted_s[i - 1] if i > 0 else None
                    pg = prev.girls_entered if prev else 0
                    pb = prev.boys_entered  if prev else 0
                    pd = prev.denied        if prev else 0
                    return {
                        "girls":  max(0, s.girls_entered - pg),
                        "boys":   max(0, s.boys_entered  - pb),
                        "denied": max(0, s.denied        - pd),
                        "recorded_at": s.recorded_at,
                    }
            return None
        else:
            for s in night_stats:
                if s.recorded_at.hour == target_hour:
                    return {
                        "girls":  s.girls_entered,
                        "boys":   s.boys_entered,
                        "denied": s.denied,
                        "recorded_at": s.recorded_at,
                    }
            return None

    # Загружаем все записи исторических ночей один раз
    nights_stats: dict[int, list] = {}
    for n in hist_nights:
        res = await session.execute(select(HourlyStat).where(HourlyStat.night_id == n.id))
        nights_stats[n.id] = list(res.scalars().all())

    # Собираем дельты за нужный час
    def collect_for_hour(target_hour: int) -> list[dict]:
        result = []
        for n in hist_nights:
            d = _get_hour_delta(nights_stats[n.id], target_hour)
            if d is not None:
                result.append(d)
        return result

    hour_records = collect_for_hour(hour)
    records   = hour_records
    used_hour = hour

    # Если меньше 2 записей — ищем ближайший час
    if len(records) < 2:
        found_hour = None
        for delta in range(1, 12):
            for candidate in (hour - delta, hour + delta):
                h = candidate % 24
                recs = collect_for_hour(h)
                if len(recs) >= 2:
                    found_hour = h
                    records = recs
                    break
            if found_hour is not None:
                break
            found_hour = None  # reset inner loop result

        if not records or len(records) < 2:
            return None

        used_hour = found_hour if found_hour is not None else hour

    avg_girls  = sum(r["girls"]  for r in records) / len(records)
    avg_boys   = sum(r["boys"]   for r in records) / len(records)
    avg_denied = sum(r["denied"] for r in records) / len(records)

    return {
        "avg_girls":    round(avg_girls, 1),
        "avg_boys":     round(avg_boys, 1),
        "avg_denied":   round(avg_denied, 1),
        "avg_total":    round(avg_girls + avg_boys, 1),
        "sample_count": len(records),
        "mode":         "hour",
        "used_hour":    used_hour,
        "used_minute":  records[0]["recorded_at"].minute if records else 0,
    }


async def get_ratio(session: AsyncSession, night_id: int) -> tuple[float, float]:
    stats = await stats_repo.get_night_stats(session, night_id)
    ns = compute_night_stats(stats)
    total = ns["total"]
    if total == 0:
        return (0.0, 0.0)
    g = round(ns["total_girls"] / total * 100, 1)
    b = round(ns["total_boys"]  / total * 100, 1)
    return (g, b)
