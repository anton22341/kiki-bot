from __future__ import annotations
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo


def admin_menu(webapp_url: str = "", is_superadmin: bool = False) -> ReplyKeyboardMarkup:
    buttons = [[KeyboardButton(text="📊 Ввести данные")]]
    if webapp_url:
        buttons[0].append(KeyboardButton(text="🌐 Открыть Mini App", web_app=WebAppInfo(url=webapp_url)))
    if is_superadmin:
        buttons.append([KeyboardButton(text="📋 Отчёт")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def owner_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 /live"), KeyboardButton(text="🌙 /night"), KeyboardButton(text="📅 /week")],
            [KeyboardButton(text="📆 /month"), KeyboardButton(text="🎯 /kpi"), KeyboardButton(text="📝 /logs")],
        ],
        resize_keyboard=True,
    )


def confirm_stat_kb(stat_id: str = "pending") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Сохранить", callback_data=f"stat_save:{stat_id}"),
            InlineKeyboardButton(text="🕐 Изменить время", callback_data=f"stat_time:{stat_id}"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="stat_cancel")],
    ])


def after_save_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Получить отчёт", callback_data="live_report")],
    ])


def role_select_kb(username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Owner", callback_data=f"setrole:owner:{username}"),
            InlineKeyboardButton(text="Admin", callback_data=f"setrole:admin:{username}"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="setrole:cancel")],
    ])
