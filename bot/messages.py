from __future__ import annotations
from datetime import datetime
from models.db import User


def progress_bar(value: int, max_value: int, width: int = 10) -> str:
    filled = round(value / max_value * width) if max_value > 0 else 0
    return "█" * filled + "░" * (width - filled)


def format_start(user: User) -> str:
    role = user.role
    name = user.username and f"@{user.username}" or user.full_name or "незнакомец"

    if role == "superadmin":
        return (
            f"Привет, {name} 👋  [👑 Superadmin]\n\n"
            "— Admin команды —\n"
            "📊 /input   /status\n\n"
            "— Owner команды —\n"
            "📊 /live    🌙 /night    📅 /week\n"
            "📆 /month   🎯 /kpi      📝 /logs\n\n"
            "— Управление —\n"
            "👥 /users   /addowner   /addadmin   /removeuser"
        )
    elif role == "owner":
        return (
            f"Привет, {name} 👋\n\n"
            "📊 /live    🌙 /night    📅 /week\n"
            "📆 /month   🎯 /kpi      📝 /logs"
        )
    elif role == "admin":
        return (
            f"Привет, {name} 👋\n\n"
            "📊 Ввести данные — /input\n"
            "🌐 Открыть Mini App — кнопка ниже\n"
            "/status — статус текущей ночи"
        )
    return "Нет доступа."


def format_users_list(users: list[User]) -> str:
    groups: dict[str, list[User]] = {"superadmin": [], "owner": [], "admin": [], "pending": []}
    for u in users:
        groups.setdefault(u.role, []).append(u)

    lines = ["👥 Пользователи KIKI Bot\n"]
    icons = {"superadmin": "👑 Superadmin", "owner": "🏠 Owner", "admin": "👔 Admin", "pending": "⏳ Ожидают"}

    for role_key in ["superadmin", "owner", "admin", "pending"]:
        role_users = groups[role_key]
        if not role_users:
            continue
        count = f" ({len(role_users)})" if len(role_users) > 1 else ""
        lines.append(f"{icons[role_key]}{count}")
        for u in role_users:
            uname = f"@{u.username}" if u.username else str(u.telegram_id)
            since = u.role_set_at.strftime("%-d %b") if u.role_set_at else ""
            suffix = f" — с {since}" if since and role_key != "superadmin" else ""
            lines.append(f"• {uname} (ID: {u.telegram_id}){suffix}")
        lines.append("")

    return "\n".join(lines).strip()


def format_role_granted(role: str) -> str:
    role_name = {"owner": "Owner", "admin": "Admin"}.get(role, role)
    return (
        f"✅ Тебе выдан доступ\n\n"
        f"Роль: {role_name}\n"
        f"Бот: KIKI Analytics\n\n"
        f"Напиши /start чтобы начать."
    )


def format_live_report(
    inside: int,
    girls_inside: int,
    boys_inside: int,
    girls_entered: int,
    boys_entered: int,
    girls_left: int,
    boys_left: int,
    denied: int,
    fc: float,
    peak_time: str,
    peak_val: int,
) -> str:
    total_inside = girls_inside + boys_inside
    ratio_g = round(girls_inside / total_inside * 100) if total_inside > 0 else 0
    ratio_b = 100 - ratio_g
    bar = progress_bar(inside, 200, 12)
    pct = round(inside / 200 * 100)
    now = datetime.utcnow().strftime("%H:%M")

    fc_icon = "✅" if fc >= 90 else "⚠️"
    ratio_icon = "✅" if ratio_g >= 55 else "⚠️"

    lines = [
        f"📊 Live · KIKI · {now}",
        "",
        f"👥 Внутри: {inside} чел",
        f"📊 {bar} {pct}%",
        "",
        f"👧 Девушек: {girls_inside}  ({ratio_g}%) {ratio_icon}",
        f"👦 Парней:  {boys_inside}  ({ratio_b}%)",
        "",
        f"➡️  Вошло: {girls_entered + boys_entered}  (👧{girls_entered} / 👦{boys_entered})",
        f"⬅️  Ушло:  {girls_left + boys_left}  (👧{girls_left} / 👦{boys_left})",
        f"🚫 Отказано: {denied}",
        "",
        f"🎯 FC конверсия: {fc}% {fc_icon}",
    ]
    if peak_val > 0:
        lines.append(f"🔥 Пик: {peak_time} — {peak_val} чел")

    return "\n".join(lines)


def format_stat_card(girls: int, boys: int, left: int, denied: int, time_str: str, is_manual: bool) -> str:
    total_entered = girls + boys
    inside = total_entered - left
    ratio_g = round(girls / total_entered * 100) if total_entered > 0 else 0
    ratio_b = 100 - ratio_g
    fc = round(total_entered / (total_entered + denied) * 100) if (total_entered + denied) > 0 else 0
    time_label = "ручное" if is_manual else "авто"

    return (
        f"📊 Проверь данные\n\n"
        f"🕐 Время: {time_str} ({time_label})\n"
        f"👧 Девушки: {girls}\n"
        f"👦 Парни: {boys}\n"
        f"🚪 Ушло: {left}\n"
        f"🚫 Отказано: {denied}\n\n"
        f"📍 Внутри сейчас: {inside}\n"
        f"⚖️ Соотношение: {ratio_g}% / {ratio_b}%\n"
        f"🎯 FC конверсия: {fc}%"
    )
