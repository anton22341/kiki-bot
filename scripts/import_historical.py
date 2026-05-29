"""
Импорт исторических данных из хардкода в БД.
Данные кумулятивные (нарастающим итогом), конвертируем в почасовые.

Запуск из корня проекта:
    python scripts/import_historical.py
"""
from __future__ import annotations
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from sqlalchemy import select
from models.db import AsyncSessionLocal, ClubNight, HourlyStat, init_db

# ─── Сырые кумулятивные данные ───────────────────────────────────────────────
# Формат: (excel_serial, hour, girls_cum, boys_cum, entered_cum, denied_cum, left_cum, left_g_cum, left_b_cum)
# Excel serial → реальная дата: 46157=2026-05-15, 46158=2026-05-16, 46164=2026-05-22, 46165=2026-05-23

EXCEL_DATE_MAP = {
    46157: "2026-05-15",
    46158: "2026-05-16",
    46164: "2026-05-22",
    46165: "2026-05-23",
}

DAY_OF_WEEK_MAP = {
    "2026-05-15": "fri",
    "2026-05-16": "sat",
    "2026-05-22": "fri",
    "2026-05-23": "sat",
}

RAW_DATA = [
    # (excel_serial, hour, girls_cum, boys_cum, total_entered_cum, denied_cum, left_cum, left_g_cum, left_b_cum)
    (46157, 0,  81,  40,  121, 32,  10,  7,   3),
    (46157, 1,  266, 141, 407, 80,  44,  29,  15),
    (46157, 2,  365, 225, 590, 113, 140, 93,  47),
    (46157, 3,  415, 257, 672, 150, 234, 156, 78),
    (46157, 4,  442, 269, 711, 157, 369, 246, 123),

    (46158, 0,  70,  39,  109, 54,  5,   3,   2),
    (46158, 1,  216, 100, 316, 104, 24,  16,  8),
    (46158, 2,  435, 225, 660, 173, 165, 110, 55),
    (46158, 3,  465, 244, 708, 190, 356, 237, 119),
    (46158, 4,  480, 250, 730, 193, 437, 291, 146),

    (46164, 0,  68,  28,  96,  31,  3,   2,   1),
    (46164, 1,  170, 115, 285, 80,  21,  14,  7),
    (46164, 2,  270, 147, 417, 103, 57,  38,  19),
    (46164, 3,  311, 173, 484, 118, 113, 75,  38),
    (46164, 4,  332, 197, 529, 132, 226, 151, 75),

    (46165, 0,  58,  45,  103, 37,  8,   5,   3),
    (46165, 1,  160, 138, 298, 78,  34,  23,  11),
    (46165, 2,  233, 189, 422, 114, 81,  54,  27),
    (46165, 3,  298, 217, 515, 139, 162, 108, 54),
    (46165, 4,  326, 232, 558, 157, 261, 174, 87),
]


def cumulative_to_hourly(night_rows: list[tuple]) -> list[dict]:
    """Конвертирует кумулятивные строки в почасовые."""
    hourly = []
    prev = (0, 0, 0, 0, 0, 0, 0, 0, 0)  # нули для prev перед первым часом
    for row in night_rows:
        serial, hour, g_cum, b_cum, ent_cum, den_cum, left_cum, lg_cum, lb_cum = row
        _, _, pg, pb, pent, pden, pleft, plg, plb = prev

        girls_entered = g_cum  - pg
        boys_entered  = b_cum  - pb
        denied        = den_cum - pden
        left_total    = left_cum - pleft
        girls_left    = lg_cum  - plg
        boys_left     = lb_cum  - plb

        date_str = EXCEL_DATE_MAP[serial]
        # recorded_at = дата + час + :30 (середина часа)
        recorded_at = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=hour, minute=30, second=0)

        hourly.append({
            "date_str":     date_str,
            "hour":         hour,
            "recorded_at":  recorded_at,
            "girls_entered": girls_entered,
            "boys_entered":  boys_entered,
            "denied":        denied,
            "left_count":    left_total,
            "girls_left":    girls_left,
            "boys_left":     boys_left,
        })
        prev = row
    return hourly


async def main():
    print("Инициализация БД...")
    await init_db()

    # Группируем строки по ночам
    nights: dict[int, list] = {}
    for row in RAW_DATA:
        serial = row[0]
        nights.setdefault(serial, []).append(row)

    nights_created = 0
    stats_inserted = 0

    async with AsyncSessionLocal() as session:
        for serial, rows in sorted(nights.items()):
            date_str = EXCEL_DATE_MAP[serial]
            dow = DAY_OF_WEEK_MAP[date_str]

            # Создаём ClubNight если не существует
            res = await session.execute(select(ClubNight).where(ClubNight.date == date_str))
            night = res.scalar_one_or_none()
            if not night:
                night = ClubNight(
                    date=date_str,
                    day_of_week=dow,
                    opened_at=datetime.strptime(date_str, "%Y-%m-%d").replace(hour=23, minute=0),
                    closed_at=datetime.strptime(date_str, "%Y-%m-%d").replace(hour=4, minute=59),
                )
                session.add(night)
                await session.flush()  # получаем night.id
                nights_created += 1
                print(f"  Создана ночь: {date_str} ({dow})")
            else:
                print(f"  Ночь уже существует: {date_str}, id={night.id}")

            hourly = cumulative_to_hourly(rows)

            for h in hourly:
                # Проверяем нет ли уже записи за этот час
                res = await session.execute(
                    select(HourlyStat).where(
                        HourlyStat.night_id == night.id,
                        HourlyStat.recorded_at == h["recorded_at"],
                    )
                )
                if res.scalar_one_or_none():
                    print(f"    Пропускаем {h['recorded_at']} — уже существует")
                    continue

                stat = HourlyStat(
                    night_id      = night.id,
                    recorded_at   = h["recorded_at"],
                    is_manual_time= False,
                    is_historical = True,
                    girls_entered = h["girls_entered"],
                    boys_entered  = h["boys_entered"],
                    denied        = h["denied"],
                    left_count    = h["left_count"],
                    girls_left    = h["girls_left"],
                    boys_left     = h["boys_left"],
                )
                session.add(stat)
                stats_inserted += 1
                print(f"    +{h['recorded_at'].strftime('%H:%M')} "
                      f"Д:{h['girls_entered']} П:{h['boys_entered']} "
                      f"ушло:{h['left_count']} откз:{h['denied']}")

        await session.commit()

    print(f"\n✅ Готово!")
    print(f"   Ночей создано:  {nights_created}")
    print(f"   Записей вставлено: {stats_inserted}")


if __name__ == "__main__":
    asyncio.run(main())
