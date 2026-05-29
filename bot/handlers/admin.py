import logging
import json
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from models.db import User, AsyncSessionLocal
from repositories import stats_repo, user_repo
from bot.keyboards import confirm_stat_kb, after_save_kb
from bot.messages import format_stat_card, format_live_report
from services import stats_service

logger = logging.getLogger(__name__)
router = Router()

ALLOWED_ROLES = {"superadmin", "admin"}


class InputStats(StatesGroup):
    girls    = State()
    boys     = State()
    left     = State()
    denied   = State()
    confirm  = State()
    fix_time = State()


def _get_night_date(dt: datetime) -> str:
    if dt.hour < 6:
        return (dt - timedelta(days=1)).strftime("%Y-%m-%d")
    return dt.strftime("%Y-%m-%d")


def _day_of_week(dt: datetime) -> str:
    keys = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    d = dt - timedelta(days=1) if dt.hour < 6 else dt
    return keys[d.weekday()]


async def _save_stat_data(session, data: dict, user_id: int) -> None:
    now = data.get("recorded_at", datetime.utcnow())
    night_date = _get_night_date(now)
    dow = _day_of_week(now)
    night = await stats_repo.get_or_create_night(session, night_date, dow)
    # Поддержка нового формата (girls_left/boys_left) и старого (left)
    girls_left = data.get("girls_left", 0)
    boys_left  = data.get("boys_left", 0)
    if "left" in data and not girls_left and not boys_left:
        left = data["left"]
        girls_left = round(left * 0.5)
        boys_left  = left - girls_left
    await stats_repo.save_stat(session, night.id, {
        "recorded_at":    now,
        "is_manual_time": data.get("is_manual_time", False),
        "girls_entered":  data["girls"],
        "boys_entered":   data["boys"],
        "denied":         data["denied"],
        "girls_left":     girls_left,
        "boys_left":      boys_left,
        "created_by":     user_id,
    })


@router.message(Command("input"))
async def cmd_input(message: Message, role: str, user: User, state: FSMContext) -> None:
    if role not in ALLOWED_ROLES:
        await message.answer("⛔ Только для admin.")
        return

    parts = message.text.split()[1:]
    if len(parts) >= 4:
        try:
            girls, boys, left, denied = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
        except ValueError:
            await message.answer("Неверный формат. Пример: /input 45 32 8 5")
            return

        now = datetime.utcnow()
        await state.set_data({
            "girls": girls, "boys": boys, "left": left, "denied": denied,
            "recorded_at": now.isoformat(), "is_manual_time": False,
        })
        await state.set_state(InputStats.confirm)
        card = format_stat_card(girls, boys, left, denied, now.strftime("%H:%M"), False)
        await message.answer(card, reply_markup=confirm_stat_kb())
    else:
        await state.set_state(InputStats.girls)
        await message.answer("Сколько девушек вошло за этот час?")


@router.message(InputStats.girls)
async def fsm_girls(message: Message, state: FSMContext, role: str) -> None:
    if role not in ALLOWED_ROLES:
        return
    try:
        val = int(message.text.strip())
    except ValueError:
        await message.answer("Введи число.")
        return
    await state.update_data(girls=val)
    await state.set_state(InputStats.boys)
    await message.answer("Сколько парней вошло?")


@router.message(InputStats.boys)
async def fsm_boys(message: Message, state: FSMContext, role: str) -> None:
    if role not in ALLOWED_ROLES:
        return
    try:
        val = int(message.text.strip())
    except ValueError:
        await message.answer("Введи число.")
        return
    await state.update_data(boys=val)
    await state.set_state(InputStats.left)
    await message.answer("Сколько человек ушло?")


@router.message(InputStats.left)
async def fsm_left(message: Message, state: FSMContext, role: str) -> None:
    if role not in ALLOWED_ROLES:
        return
    try:
        val = int(message.text.strip())
    except ValueError:
        await message.answer("Введи число.")
        return
    await state.update_data(left=val)
    await state.set_state(InputStats.denied)
    await message.answer("Сколько отказано на входе?")


@router.message(InputStats.denied)
async def fsm_denied(message: Message, state: FSMContext, role: str) -> None:
    if role not in ALLOWED_ROLES:
        return
    try:
        val = int(message.text.strip())
    except ValueError:
        await message.answer("Введи число.")
        return

    now = datetime.utcnow()
    data = await state.get_data()
    data.update({"denied": val, "recorded_at": now.isoformat(), "is_manual_time": False})
    await state.set_data(data)
    await state.set_state(InputStats.confirm)

    card = format_stat_card(data["girls"], data["boys"], data["left"], val, now.strftime("%H:%M"), False)
    await message.answer(card, reply_markup=confirm_stat_kb())


@router.callback_query(F.data == "stat_save:pending")
async def cb_stat_save(callback: CallbackQuery, state: FSMContext, user: User, role: str) -> None:
    if role not in ALLOWED_ROLES:
        await callback.answer("Нет доступа", show_alert=True)
        return

    data = await state.get_data()
    data["recorded_at"] = datetime.fromisoformat(data["recorded_at"])

    async with AsyncSessionLocal() as session:
        await _save_stat_data(session, data, user.id)

    await state.clear()
    await callback.message.edit_text(
        "✅ Данные сохранены!",
        reply_markup=after_save_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "live_report")
async def cb_live_report(callback: CallbackQuery, role: str) -> None:
    async with AsyncSessionLocal() as session:
        night = await stats_service.get_current_night(session)
        if not night:
            await callback.answer("Нет активной ночи", show_alert=True)
            return

        inside  = await stats_service.get_live_occupancy(session, night.id)
        split   = await stats_service.get_live_split(session, night.id)
        fc      = await stats_service.get_fc_conversion(session, night.id)
        peak_t, peak_v = await stats_service.get_peak_hour(session, night.id)

        stats   = await stats_repo.get_night_stats(session, night.id)
        g_ent   = sum(s.girls_entered for s in stats)
        b_ent   = sum(s.boys_entered  for s in stats)
        g_left  = sum(s.girls_left or 0 for s in stats)
        b_left  = sum(s.boys_left  or 0 for s in stats)
        denied  = sum(s.denied for s in stats)

    report = format_live_report(
        inside=inside,
        girls_inside=split["girls_inside"],
        boys_inside=split["boys_inside"],
        girls_entered=g_ent,
        boys_entered=b_ent,
        girls_left=g_left,
        boys_left=b_left,
        denied=denied,
        fc=fc,
        peak_time=peak_t,
        peak_val=peak_v,
    )
    await callback.message.answer(report)
    await callback.answer()


@router.callback_query(F.data == "stat_cancel")
async def cb_stat_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("❌ Отменено.")
    await callback.answer()


@router.callback_query(F.data == "stat_time:pending")
async def cb_stat_time(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    cur = datetime.fromisoformat(data["recorded_at"]).strftime("%H:%M")
    await state.set_state(InputStats.fix_time)
    await callback.message.answer(
        f"Введи время в формате ЧЧ:ММ\nНапример: 01:47\n\n(текущее авто-время: {cur})"
    )
    await callback.answer()


@router.message(InputStats.fix_time)
async def fsm_fix_time(message: Message, state: FSMContext, role: str) -> None:
    if role not in ALLOWED_ROLES:
        return
    try:
        h, m = map(int, message.text.strip().split(":"))
        assert 0 <= h <= 23 and 0 <= m <= 59
    except Exception:
        await message.answer("Неверный формат. Введи ЧЧ:ММ, например 02:15")
        return

    data = await state.get_data()
    old_dt = datetime.fromisoformat(data["recorded_at"])
    new_dt = old_dt.replace(hour=h, minute=m, second=0)
    data["recorded_at"] = new_dt.isoformat()
    data["is_manual_time"] = True
    await state.set_data(data)
    await state.set_state(InputStats.confirm)

    card = format_stat_card(data["girls"], data["boys"], data["left"], data["denied"], new_dt.strftime("%H:%M"), True)
    await message.answer(card, reply_markup=confirm_stat_kb())


@router.message(F.web_app_data)
async def handle_webapp_data(message: Message, user: User, role: str, state: FSMContext) -> None:
    if role not in ALLOWED_ROLES:
        return
    try:
        payload = json.loads(message.web_app_data.data)
        if payload.get("action") != "save_stats":
            return
        girls      = int(payload["girls"])
        boys       = int(payload["boys"])
        girls_left = int(payload.get("girls_left", 0))
        boys_left  = int(payload.get("boys_left",  0))
        denied     = int(payload.get("denied", 0))
        recorded_at = datetime.fromisoformat(payload["recorded_at"])
        is_manual   = payload.get("is_manual_time", False)
    except Exception as e:
        logger.error("webapp data parse error: %s", e)
        await message.answer("Ошибка при получении данных из Mini App.")
        return

    async with AsyncSessionLocal() as session:
        await _save_stat_data(session, {
            "girls":      girls,
            "boys":       boys,
            "girls_left": girls_left,
            "boys_left":  boys_left,
            "denied":     denied,
            "recorded_at": recorded_at,
            "is_manual_time": is_manual,
        }, user.id)

    await message.answer(
        f"✅ Данные сохранены · {recorded_at.strftime('%H:%M')}",
        reply_markup=after_save_kb(),
    )


@router.message(Command("edit"))
async def cmd_edit(message: Message, role: str, user: User) -> None:
    if role not in ALLOWED_ROLES:
        await message.answer("⛔ Только для admin.")
        return

    parts = message.text.split()
    if len(parts) < 4:
        await message.answer("Использование: /edit <stat_id> <field> <value>\nПоля: girls, boys, left, denied, time")
        return

    try:
        stat_id = int(parts[1])
    except ValueError:
        await message.answer("stat_id должен быть числом.")
        return

    field = parts[2].lower()
    value = parts[3]
    allowed_fields = {"girls", "boys", "left", "denied", "time"}
    if field not in allowed_fields:
        await message.answer(f"Поле должно быть одним из: {', '.join(allowed_fields)}")
        return

    async with AsyncSessionLocal() as session:
        stat = await stats_repo.get_stat_by_id(session, stat_id)
        if not stat:
            await message.answer(f"Запись #{stat_id} не найдена.")
            return

        old_val: str
        if field == "girls":
            old_val = str(stat.girls_entered)
            stat.girls_entered = int(value)
        elif field == "boys":
            old_val = str(stat.boys_entered)
            stat.boys_entered = int(value)
        elif field == "left":
            old_val = str(stat.left_count)
            stat.left_count = int(value)
        elif field == "denied":
            old_val = str(stat.denied)
            stat.denied = int(value)
        elif field == "time":
            old_val = stat.recorded_at.strftime("%H:%M")
            h, m = map(int, value.split(":"))
            stat.recorded_at = stat.recorded_at.replace(hour=h, minute=m, second=0)
            stat.is_manual_time = True

        await stats_repo.save_edit_log(session, stat_id, field, old_val, value, user.id)
        await session.commit()

    uname = f"@{user.username}" if user.username else str(user.telegram_id)
    notif = (
        f"⚠️ Изменение данных\n\n"
        f"👤 Admin: {uname}\n"
        f"📋 Запись #{stat_id}\n"
        f"📝 Поле: {field}\n"
        f"🔄 Было: {old_val} → Стало: {value}"
    )
    await message.answer(f"✅ Запись #{stat_id} обновлена.")

    async with AsyncSessionLocal() as session:
        owners = await user_repo.get_by_role(session, "owner")
        sa_list = await user_repo.get_by_role(session, "superadmin")

    for recipient in owners + sa_list:
        if recipient.telegram_id != user.telegram_id:
            try:
                await message.bot.send_message(recipient.telegram_id, notif)
            except Exception:
                pass


@router.message(Command("status"))
async def cmd_status(message: Message, role: str) -> None:
    if role not in ALLOWED_ROLES:
        await message.answer("⛔ Только для admin.")
        return
    async with AsyncSessionLocal() as session:
        night = await stats_repo.get_current_night(session)
    if not night:
        await message.answer("🔴 Активной ночи нет.")
    else:
        await message.answer(f"🟢 Ночь открыта: {night.date} ({night.day_of_week})")
