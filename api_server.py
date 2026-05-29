from __future__ import annotations
import hmac
import hashlib
import json
import logging
import urllib.parse
from pathlib import Path
from typing import Optional
from aiohttp import web
from models.db import AsyncSessionLocal
from repositories import user_repo, stats_repo
from services import stats_service, report_service
from config import settings

logger = logging.getLogger(__name__)

MINIAPP_DIR = Path(__file__).parent / "miniapp"


# Dev superadmin stub used when initData is absent (local browser testing)
DEV_SUPERADMIN = {"id": settings.SUPERADMIN_ID, "username": "superadmin"}


def validate_init_data(init_data: str) -> dict | None:
    if not init_data:
        return None
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        check_string = parsed.pop("hash", "")
        data_check = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret = hmac.new(b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
        computed = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed, check_string):
            return None
        user_json = parsed.get("user", "{}")
        return json.loads(user_json)
    except Exception as e:
        logger.error("validate_init_data error: %s", e)
        return None


def get_tg_user(request: web.Request) -> dict:
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    user = validate_init_data(init_data)
    # If no valid initData (local dev or browser open), treat as superadmin
    return user if user is not None else DEV_SUPERADMIN


def require_superadmin(handler):
    async def wrapper(request):
        tg_user = get_tg_user(request)
        if tg_user.get("id") != settings.SUPERADMIN_ID:
            return web.json_response({"error": "Forbidden"}, status=403)
        return await handler(request)
    return wrapper


def require_auth(handler):
    async def wrapper(request):
        request["tg_user"] = get_tg_user(request)
        return await handler(request)
    return wrapper


async def index(request: web.Request) -> web.Response:
    return web.FileResponse(MINIAPP_DIR / "index.html")


@require_auth
async def api_me(request: web.Request) -> web.Response:
    tg_user = request["tg_user"]
    async with AsyncSessionLocal() as session:
        user = await user_repo.get_by_telegram_id(session, tg_user["id"])
    if not user:
        return web.json_response({"role": "pending"})
    return web.json_response({"role": user.role, "telegram_id": user.telegram_id})


@require_auth
async def api_live(request: web.Request) -> web.Response:
    async with AsyncSessionLocal() as session:
        night = await stats_service.get_current_night(session)
        if not night:
            return web.json_response({
                "inside": 0, "girls_entered": 0, "boys_entered": 0,
                "girls_inside": 0, "boys_inside": 0,
                "left": 0, "denied": 0, "ratio_girls": 0, "hourly": []
            })

        stats  = await stats_repo.get_night_stats(session, night.id)
        inside = await stats_service.get_live_occupancy(session, night.id)
        split  = await stats_service.get_live_split(session, night.id)

        girls_entered = sum(s.girls_entered for s in stats)
        boys_entered  = sum(s.boys_entered  for s in stats)
        left          = sum(s.left_count    for s in stats)
        denied        = sum(s.denied        for s in stats)
        hourly = [{"time": s.recorded_at.strftime("%H:%M"), "entered": s.girls_entered + s.boys_entered} for s in stats]

        # Benchmark
        from datetime import datetime as _dt
        cur_hour = _dt.utcnow().hour
        bm = await stats_service.get_benchmark(session, night.id, 0, night.day_of_week)

    def delta_pct(cur, avg):
        if not avg:
            return None
        return round((cur / avg - 1) * 100)

    def signal(d):
        if d is None:
            return None
        if d > 15:
            return "green"
        if d < -15:
            return "red"
        return "orange"

    bm_data = None
    if bm:
        total_now = girls_entered + boys_entered
        d_total  = delta_pct(total_now,    bm["avg_total"])
        d_girls  = delta_pct(girls_entered, bm["avg_girls"])
        d_boys   = delta_pct(boys_entered,  bm["avg_boys"])
        bm_data  = {
            "avg_total":      bm["avg_total"],
            "avg_girls":      bm["avg_girls"],
            "avg_boys":       bm["avg_boys"],
            "avg_inside":     bm["avg_inside"],
            "delta_total":    d_total,
            "delta_girls":    d_girls,
            "delta_boys":     d_boys,
            "signal_total":   signal(d_total),
            "signal_girls":   signal(d_girls),
            "signal_boys":    signal(d_boys),
            "sample_count":   bm["sample_count"],
            "day_of_week":    night.day_of_week,
        }

    return web.json_response({
        "inside":        inside,
        "girls_entered": girls_entered,
        "boys_entered":  boys_entered,
        "girls_inside":  split["girls_inside"],
        "boys_inside":   split["boys_inside"],
        "ratio_girls":   split["ratio_girls"],
        "ratio_boys":    split["ratio_boys"],
        "left":          left,
        "denied":        denied,
        "hourly":        hourly,
        "benchmark":     bm_data,
    })


@require_auth
async def api_nights_list(request: web.Request) -> web.Response:
    """Список всех доступных ночей для навигации."""
    from sqlalchemy import select
    from models.db import ClubNight
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ClubNight.date, ClubNight.day_of_week, ClubNight.closed_at)
            .order_by(ClubNight.date.desc())
        )
        rows = result.all()

    MONTHS_SHORT = ['','янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек']
    DAY_RU = {"mon":"Пн","tue":"Вт","wed":"Ср","thu":"Чт","fri":"Пт","sat":"Сб","sun":"Вс"}
    nights = []
    for date_str, dow, closed_at in rows:
        from datetime import datetime
        d = datetime.strptime(date_str, "%Y-%m-%d")
        label = f"{DAY_RU.get(dow,'')} {d.day} {MONTHS_SHORT[d.month]}"
        nights.append({"date": date_str, "label": label, "is_open": closed_at is None})
    return web.json_response({"nights": nights})


@require_auth
async def api_night(request: web.Request) -> web.Response:
    from sqlalchemy import select
    from models.db import ClubNight
    from datetime import datetime

    date_param = request.rel_url.query.get("date")  # ?date=2026-05-29

    async with AsyncSessionLocal() as session:
        if date_param:
            result = await session.execute(
                select(ClubNight).where(ClubNight.date == date_param)
            )
            night = result.scalar_one_or_none()
        else:
            night = await stats_service.get_current_night(session)
            if not night:
                result = await session.execute(
                    select(ClubNight).order_by(ClubNight.opened_at.desc()).limit(1)
                )
                night = result.scalar_one_or_none()

        if not night:
            return web.json_response({"empty": True})

        stats = await stats_repo.get_night_stats(session, night.id)
        total_girls = sum(s.girls_entered for s in stats)
        total_boys  = sum(s.boys_entered  for s in stats)
        total = total_girls + total_boys
        fc = await stats_service.get_fc_conversion(session, night.id)
        ratio = await stats_service.get_ratio(session, night.id)
        peak_time, peak_val = await stats_service.get_peak_hour(session, night.id)
        hourly = [{
            "time":   s.recorded_at.strftime("%H:%M"),
            "entered": s.girls_entered + s.boys_entered,
            "left":   s.left_count,
            "girls":  s.girls_entered,
            "boys":   s.boys_entered,
        } for s in stats]

        MONTHS_SHORT = ['','янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек']
        DAY_RU = {"mon":"Пн","tue":"Вт","wed":"Ср","thu":"Чт","fri":"Пт","sat":"Сб","sun":"Вс"}
        d = datetime.strptime(night.date, "%Y-%m-%d")
        date_label = f"{DAY_RU.get(night.day_of_week,'')} {d.day} {MONTHS_SHORT[d.month]}"

    return web.json_response({
        "date": night.date,
        "date_label": date_label,
        "is_open": night.closed_at is None,
        "total": total,
        "total_girls": total_girls,
        "total_boys": total_boys,
        "fc": fc,
        "ratio": [int(ratio[0]), int(ratio[1])],
        "peak": {"time": peak_time, "val": peak_val},
        "hourly": hourly,
        "empty": len(stats) == 0,
    })


CLUB_DAYS = ("fri", "sat")  # клуб работает только пт и сб
DAY_LABEL = {"fri": "Пт", "sat": "Сб"}


@require_auth
async def api_week(request: web.Request) -> web.Response:
    from datetime import datetime, timedelta
    from sqlalchemy import select
    from models.db import ClubNight
    now = datetime.utcnow()
    two_weeks_ago = (now - timedelta(days=14)).strftime("%Y-%m-%d")
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ClubNight)
            .where(ClubNight.date >= two_weeks_ago)
            .where(ClubNight.day_of_week.in_(CLUB_DAYS))
            .order_by(ClubNight.date)
        )
        nights = list(result.scalars().all())
        data = []
        for n in nights:
            stats = await stats_repo.get_night_stats(session, n.id)
            total = sum(s.girls_entered + s.boys_entered for s in stats)
            d = datetime.strptime(n.date, "%Y-%m-%d")
            label = f"{DAY_LABEL.get(n.day_of_week, n.day_of_week)} {d.day}"
            data.append({"label": label, "total": total, "current": not n.closed_at})
    return web.json_response({"nights": data})


@require_auth
async def api_month(request: web.Request) -> web.Response:
    from datetime import datetime
    from sqlalchemy import select
    from models.db import ClubNight
    now = datetime.utcnow()
    month_start = now.replace(day=1).strftime("%Y-%m-%d")
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ClubNight)
            .where(ClubNight.date >= month_start)
            .where(ClubNight.day_of_week.in_(CLUB_DAYS))
            .order_by(ClubNight.date)
        )
        nights = list(result.scalars().all())
        data = []
        for n in nights:
            stats = await stats_repo.get_night_stats(session, n.id)
            total = sum(s.girls_entered + s.boys_entered for s in stats)
            d = datetime.strptime(n.date, "%Y-%m-%d")
            label = f"{DAY_LABEL.get(n.day_of_week, '')} {d.day}"
            data.append({"label": label, "total": total})
    return web.json_response({"nights": data})


@require_auth
async def api_kpi(request: web.Request) -> web.Response:
    from datetime import datetime
    from sqlalchemy import select
    from models.db import ClubNight
    now = datetime.utcnow()
    month_start = now.replace(day=1).strftime("%Y-%m-%d")
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ClubNight)
            .where(ClubNight.date >= month_start)
            .where(ClubNight.day_of_week.in_(CLUB_DAYS))
        )
        nights = list(result.scalars().all())
        total_g = total_b = total_denied = total_entered = 0
        for n in nights:
            stats = await stats_repo.get_night_stats(session, n.id)
            for s in stats:
                total_entered += s.girls_entered + s.boys_entered
                total_g += s.girls_entered
                total_b += s.boys_entered
                total_denied += s.denied
    fc      = round(total_entered / (total_entered + total_denied) * 100) if (total_entered + total_denied) > 0 else 0
    ratio_g = round(total_g / total_entered * 100) if total_entered > 0 else 0

    # Загружаем цели из настроек
    from sqlalchemy import select
    from models.db import ClubSettings
    async with AsyncSessionLocal() as s2:
        res = await s2.execute(select(ClubSettings))
        cfg = {r.key: r.value for r in res.scalars().all()}

    target_fc    = int(cfg.get("target_fc_pct",    "90"))
    target_ratio = int(cfg.get("target_girls_pct", "55"))
    capacity     = int(cfg.get("max_capacity",      "200"))

    # avg_inside: среднее людей внутри по всем ночам
    avg_inside = None
    if nights:
        all_inside = []
        for n in nights:
            async with AsyncSessionLocal() as s3:
                st = await stats_repo.get_night_stats(s3, n.id)
                if st:
                    ins = sum(s.girls_entered + s.boys_entered for s in st) - sum(s.left_count for s in st)
                    all_inside.append(max(0, ins))
        if all_inside:
            avg_inside = round(sum(all_inside) / len(all_inside))

    items = [
        {"label": "FC %",      "actual": fc,      "target": target_fc},
        {"label": "Девушки %", "actual": ratio_g, "target": target_ratio},
        {"label": "Загрузка %","actual": round(avg_inside / capacity * 100) if avg_inside else 0, "target": 70},
    ]
    return web.json_response({
        "items": items,
        "nights_count": len(nights),
        "avg_inside": avg_inside,
        "capacity": capacity,
    })


@require_superadmin
async def api_users_list(request: web.Request) -> web.Response:
    async with AsyncSessionLocal() as session:
        users = await user_repo.get_all(session)
    # Главный superadmin всегда скрыт из списка
    filtered = [u for u in users if u.telegram_id != settings.SUPERADMIN_ID]
    return web.json_response({"users": [
        {
            "telegram_id": u.telegram_id,
            "username": u.username,
            "full_name": u.full_name,
            "role": u.role,
            "role_set_at": u.role_set_at.isoformat() if u.role_set_at else None,
        } for u in filtered
    ]})


@require_superadmin
async def api_set_role(request: web.Request) -> web.Response:
    body = await request.json()
    role = body.get("role")
    if role not in ("superadmin", "owner", "admin", "pending"):
        return web.json_response({"error": "Invalid role"}, status=400)
    # Только superadmin может выдать роль superadmin
    tg_user = get_tg_user(request)
    if role == "superadmin" and tg_user.get("id") != settings.SUPERADMIN_ID:
        return web.json_response({"error": "Только главный superadmin может выдавать эту роль"}, status=403)

    tg_id = body.get("telegram_id")
    identifier = body.get("identifier", "")
    async with AsyncSessionLocal() as session:
        if tg_id:
            user = await user_repo.get_by_telegram_id(session, int(tg_id))
        elif identifier:
            clean = str(identifier).lstrip("@")
            if clean.isdigit():
                user = await user_repo.get_by_telegram_id(session, int(clean))
            else:
                user = await user_repo.get_by_username(session, clean)
        else:
            return web.json_response({"error": "No user specified"}, status=400)

        if not user:
            return web.json_response({"error": "Пользователь не найден. Попроси его написать /start боту."}, status=404)

        await user_repo.set_role(session, user.telegram_id, role)

    from bot.messages import format_role_granted
    try:
        from aiogram import Bot
        bot = Bot(token=settings.BOT_TOKEN)
        await bot.send_message(user.telegram_id, format_role_granted(role))
        await bot.session.close()
    except Exception as e:
        logger.warning("Could not notify user: %s", e)

    return web.json_response({"ok": True})


@require_superadmin
async def api_remove_user(request: web.Request) -> web.Response:
    body = await request.json()
    tg_id = body.get("telegram_id")
    if not tg_id:
        return web.json_response({"error": "telegram_id required"}, status=400)
    async with AsyncSessionLocal() as session:
        await user_repo.set_role(session, int(tg_id), "pending")
    return web.json_response({"ok": True})


@require_auth
async def api_input(request: web.Request) -> web.Response:
    """Browser fallback: save stats directly via HTTP (when not sending via tg.sendData)."""
    tg_user = request["tg_user"]
    body = await request.json()
    from datetime import datetime, timedelta

    try:
        girls       = int(body.get("girls", 0))
        boys        = int(body.get("boys", 0))
        girls_left  = int(body.get("girls_left", 0))
        boys_left   = int(body.get("boys_left",  0))
        # Совместимость со старым форматом (одно поле left)
        if "left" in body and not ("girls_left" in body or "boys_left" in body):
            left_total = int(body["left"])
            girls_left = round(left_total * 0.5)
            boys_left  = left_total - girls_left
        denied = int(body.get("denied", 0))
        recorded_at = datetime.fromisoformat(body["recorded_at"].replace("Z", "+00:00")).replace(tzinfo=None)
        is_manual = bool(body.get("is_manual_time", False))
    except Exception as e:
        return web.json_response({"error": f"Bad data: {e}"}, status=400)

    def _night_date(dt: datetime) -> str:
        if dt.hour < 6:
            return (dt - timedelta(days=1)).strftime("%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")

    def _dow(dt: datetime) -> str:
        keys = ["mon","tue","wed","thu","fri","sat","sun"]
        d = dt - timedelta(days=1) if dt.hour < 6 else dt
        return keys[d.weekday()]

    async with AsyncSessionLocal() as session:
        user = await user_repo.get_by_telegram_id(session, tg_user["id"])
        if not user or user.role not in ("superadmin", "admin"):
            return web.json_response({"error": "Forbidden"}, status=403)

        night_date = _night_date(recorded_at)
        dow = _dow(recorded_at)
        from repositories.stats_repo import get_or_create_night, save_stat
        night = await get_or_create_night(session, night_date, dow)
        await save_stat(session, night.id, {
            "recorded_at":   recorded_at,
            "is_manual_time": is_manual,
            "girls_entered":  girls,
            "boys_entered":   boys,
            "denied":         denied,
            "girls_left":     girls_left,
            "boys_left":      boys_left,
            "created_by":     user.id,
        })

    return web.json_response({"ok": True})


@require_auth
async def api_history(request: web.Request) -> web.Response:
    """История ввода за текущую ночь."""
    async with AsyncSessionLocal() as session:
        night = await stats_service.get_current_night(session)
        if not night:
            # Попробуем последнюю ночь
            from sqlalchemy import select
            from models.db import ClubNight
            result = await session.execute(
                select(ClubNight).order_by(ClubNight.opened_at.desc()).limit(1)
            )
            night = result.scalar_one_or_none()
        if not night:
            return web.json_response({"entries": [], "night": None})

        stats = await stats_repo.get_night_stats(session, night.id)
        entries = []
        for s in stats:
            entries.append({
                "id":            s.id,
                "time":          s.recorded_at.strftime("%H:%M"),
                "recorded_at":   s.recorded_at.isoformat(),
                "is_manual_time": s.is_manual_time,
                "girls":         s.girls_entered,
                "boys":          s.boys_entered,
                "girls_left":    s.girls_left or 0,
                "boys_left":     s.boys_left  or 0,
                "left":          s.left_count,
                "denied":        s.denied,
            })

    return web.json_response({
        "entries": entries,
        "night": {"date": night.date, "day_of_week": night.day_of_week},
    })


@require_auth
async def api_edit_stat(request: web.Request) -> web.Response:
    """Редактирование записи."""
    tg_user = request["tg_user"]
    body = await request.json()

    stat_id = body.get("id")
    if not stat_id:
        return web.json_response({"error": "id required"}, status=400)

    async with AsyncSessionLocal() as session:
        user = await user_repo.get_by_telegram_id(session, tg_user["id"])
        if not user or user.role not in ("superadmin", "admin"):
            return web.json_response({"error": "Forbidden"}, status=403)

        stat = await stats_repo.get_stat_by_id(session, int(stat_id))
        if not stat:
            return web.json_response({"error": "Запись не найдена"}, status=404)

        field_map = {
            "girls":      "girls_entered",
            "boys":       "boys_entered",
            "girls_left": "girls_left",
            "boys_left":  "boys_left",
            "denied":     "denied",
        }

        changes = []
        for field, attr in field_map.items():
            if field in body:
                old = str(getattr(stat, attr) or 0)
                new_val = int(body[field])
                if str(new_val) != old:
                    await stats_repo.save_edit_log(session, stat.id, field, old, str(new_val), user.id)
                    setattr(stat, attr, new_val)
                    changes.append(field)
        # Пересчитываем left_count
        if "girls_left" in changes or "boys_left" in changes:
            stat.left_count = (stat.girls_left or 0) + (stat.boys_left or 0)

        if "time" in body:
            try:
                h, m = map(int, body["time"].split(":"))
                old_time = stat.recorded_at.strftime("%H:%M")
                stat.recorded_at = stat.recorded_at.replace(hour=h, minute=m, second=0)
                stat.is_manual_time = True
                await stats_repo.save_edit_log(session, stat.id, "time", old_time, body["time"], user.id)
                changes.append("time")
            except Exception:
                return web.json_response({"error": "Неверный формат времени"}, status=400)

        if changes:
            await session.commit()

            # Уведомление owner/superadmin
            uname = f"@{user.username}" if user.username else str(user.telegram_id)
            notif = (
                f"⚠️ Правка данных\n\n"
                f"👤 {uname}\n"
                f"📋 Запись #{stat.id} · {stat.recorded_at.strftime('%H:%M')}\n"
                f"📝 Поля: {', '.join(changes)}"
            )
            owners = await user_repo.get_by_role(session, "owner")
            sa_list = await user_repo.get_by_role(session, "superadmin")
            for recipient in owners + sa_list:
                if recipient.telegram_id != tg_user["id"]:
                    try:
                        from aiogram import Bot
                        bot = Bot(token=settings.BOT_TOKEN)
                        await bot.send_message(recipient.telegram_id, notif)
                        await bot.session.close()
                    except Exception:
                        pass

    return web.json_response({"ok": True, "changed": changes})


@require_auth
async def api_delete_stat(request: web.Request) -> web.Response:
    """Удаление записи."""
    try:
        tg_user = request["tg_user"]
        body = await request.json()
        stat_id = body.get("id")
        if not stat_id:
            return web.json_response({"error": "id required"}, status=400)

        from sqlalchemy import delete as sa_delete
        from models.db import HourlyStat, EditLog
        async with AsyncSessionLocal() as session:
            sid = int(stat_id)
            # Сначала удаляем связанные edit_logs (foreign key)
            await session.execute(sa_delete(EditLog).where(EditLog.stat_id == sid))
            # Затем удаляем саму запись
            result = await session.execute(
                sa_delete(HourlyStat).where(HourlyStat.id == sid)
            )
            await session.commit()
            if result.rowcount == 0:
                return web.json_response({"error": "Не найдена"}, status=404)

        return web.json_response({"ok": True})
    except Exception as e:
        logger.error("api_delete_stat error: %s", e)
        return web.json_response({"error": str(e)}, status=500)


@require_superadmin
async def api_import_historical(request: web.Request) -> web.Response:
    """Одноразовый импорт исторических данных."""
    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from sqlalchemy import select
        from models.db import ClubNight, HourlyStat
        from datetime import datetime

        EXCEL_DATE_MAP = {46157:"2026-05-15",46158:"2026-05-16",46164:"2026-05-22",46165:"2026-05-23"}
        DAY_MAP = {"2026-05-15":"fri","2026-05-16":"sat","2026-05-22":"fri","2026-05-23":"sat"}
        RAW = [
            (46157,0,81,40,121,32,10,7,3),(46157,1,266,141,407,80,44,29,15),
            (46157,2,365,225,590,113,140,93,47),(46157,3,415,257,672,150,234,156,78),
            (46157,4,442,269,711,157,369,246,123),
            (46158,0,70,39,109,54,5,3,2),(46158,1,216,100,316,104,24,16,8),
            (46158,2,435,225,660,173,165,110,55),(46158,3,465,244,708,190,356,237,119),
            (46158,4,480,250,730,193,437,291,146),
            (46164,0,68,28,96,31,3,2,1),(46164,1,170,115,285,80,21,14,7),
            (46164,2,270,147,417,103,57,38,19),(46164,3,311,173,484,118,113,75,38),
            (46164,4,332,197,529,132,226,151,75),
            (46165,0,58,45,103,37,8,5,3),(46165,1,160,138,298,78,34,23,11),
            (46165,2,233,189,422,114,81,54,27),(46165,3,298,217,515,139,162,108,54),
            (46165,4,326,232,558,157,261,174,87),
        ]
        nights_by_serial = {}
        for row in RAW:
            nights_by_serial.setdefault(row[0], []).append(row)

        nights_created = stats_inserted = 0
        async with AsyncSessionLocal() as session:
            for serial, rows in sorted(nights_by_serial.items()):
                date_str = EXCEL_DATE_MAP[serial]
                dow = DAY_MAP[date_str]
                res = await session.execute(select(ClubNight).where(ClubNight.date == date_str))
                night = res.scalar_one_or_none()
                if not night:
                    night = ClubNight(date=date_str, day_of_week=dow,
                        opened_at=datetime.strptime(date_str,"%Y-%m-%d").replace(hour=23),
                        closed_at=datetime.strptime(date_str,"%Y-%m-%d").replace(hour=4,minute=59))
                    session.add(night); await session.flush(); nights_created += 1

                prev = (0,)*9
                for row in rows:
                    s,h,g,b,_,d,l,lg,lb = row
                    _,_,pg,pb,_,pd,pl,plg,plb = prev
                    rec = datetime.strptime(date_str,"%Y-%m-%d").replace(hour=h,minute=30)
                    ex = await session.execute(select(HourlyStat).where(
                        HourlyStat.night_id==night.id, HourlyStat.recorded_at==rec))
                    if not ex.scalar_one_or_none():
                        session.add(HourlyStat(
                            night_id=night.id, recorded_at=rec, is_manual_time=False, is_historical=True,
                            girls_entered=g-pg, boys_entered=b-pb, denied=d-pd,
                            left_count=l-pl, girls_left=lg-plg, boys_left=lb-plb))
                        stats_inserted += 1
                    prev = row
            await session.commit()
        return web.json_response({"ok":True,"nights_created":nights_created,"stats_inserted":stats_inserted})
    except Exception as e:
        logger.error("import_historical: %s", e)
        return web.json_response({"error": str(e)}, status=500)


@require_auth
async def api_get_settings(request: web.Request) -> web.Response:
    """Настройки клуба (цели)."""
    from sqlalchemy import select
    from models.db import ClubSettings
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ClubSettings))
        rows = result.scalars().all()
    return web.json_response({r.key: r.value for r in rows})


@require_superadmin
async def api_save_settings(request: web.Request) -> web.Response:
    """Сохранить настройки клуба."""
    from sqlalchemy import select
    from models.db import ClubSettings
    from datetime import datetime
    body = await request.json()
    allowed = {"max_capacity", "target_girls_pct", "target_fc_pct", "club_name"}
    async with AsyncSessionLocal() as session:
        for key, val in body.items():
            if key not in allowed:
                continue
            res = await session.execute(select(ClubSettings).where(ClubSettings.key == key))
            setting = res.scalar_one_or_none()
            if setting:
                setting.value = str(val)
                setting.updated_at = datetime.utcnow()
            else:
                session.add(ClubSettings(key=key, value=str(val)))
        await session.commit()
    return web.json_response({"ok": True})


@web.middleware
async def cors_middleware(request: web.Request, handler) -> web.Response:
    if request.method == "OPTIONS":
        return web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type, X-Telegram-Init-Data",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        })
    response = await handler(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


def create_app() -> web.Application:
    app = web.Application(middlewares=[cors_middleware])

    app.router.add_get("/", index)
    app.router.add_get("/api/me", api_me)
    app.router.add_get("/api/live", api_live)
    app.router.add_get("/api/nights", api_nights_list)
    app.router.add_get("/api/night", api_night)
    app.router.add_get("/api/week", api_week)
    app.router.add_get("/api/month", api_month)
    app.router.add_get("/api/kpi", api_kpi)
    app.router.add_get("/api/users", api_users_list)
    app.router.add_post("/api/input", api_input)
    app.router.add_get("/api/history", api_history)
    app.router.add_post("/api/stats/edit", api_edit_stat)
    app.router.add_post("/api/stats/delete", api_delete_stat)
    app.router.add_post("/api/users/role", api_set_role)
    app.router.add_post("/api/users/remove", api_remove_user)
    app.router.add_get("/api/settings", api_get_settings)
    app.router.add_post("/api/admin/import-historical", api_import_historical)
    app.router.add_post("/api/settings", api_save_settings)
    app.router.add_static("/miniapp", MINIAPP_DIR)
    return app
