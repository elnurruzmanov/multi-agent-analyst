"""Klaviaturalar."""
from __future__ import annotations

from datetime import date, timedelta

from aiogram.types import (
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.catalog import SECTORS, TARIFFS, TIME_SLOTS, money

BTN_BOOK = "🎮 Joy band qilish"
BTN_PRICES = "💰 Narxlar"
BTN_ARENA = "🗺 Arena"
BTN_PASS = "🎟 Gladiator Pass"
BTN_CONTACT = "📞 Aloqa"
BTN_ADMIN = "⚙️ Admin panel"

# Band qilish oqimi bu tugmalarni matn sifatida qabul qilmasligi kerak —
# aks holda «Narxlar» bosilsa u izoh bo'lib yozilib qolardi.
MENU_BUTTONS = frozenset(
    {BTN_BOOK, BTN_PRICES, BTN_ARENA, BTN_PASS, BTN_CONTACT, BTN_ADMIN}
)


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=BTN_BOOK)],
        [KeyboardButton(text=BTN_PRICES), KeyboardButton(text=BTN_ARENA)],
        [KeyboardButton(text=BTN_PASS), KeyboardButton(text=BTN_CONTACT)],
    ]
    if is_admin:
        rows.append([KeyboardButton(text=BTN_ADMIN)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def dates_kb() -> InlineKeyboardMarkup:
    """Bugundan boshlab 7 kun."""
    kb = InlineKeyboardBuilder()
    today = date.today()
    names = ("Dushanba", "Seshanba", "Chorshanba", "Payshanba",
             "Juma", "Shanba", "Yakshanba")
    for offset in range(7):
        day = today + timedelta(days=offset)
        if offset == 0:
            label = f"Bugun, {day.strftime('%d.%m')}"
        elif offset == 1:
            label = f"Ertaga, {day.strftime('%d.%m')}"
        else:
            label = f"{names[day.weekday()]}, {day.strftime('%d.%m')}"
        kb.button(text=label, callback_data=f"date:{day.isoformat()}")
    kb.button(text="❌ Bekor qilish", callback_data="cancel")
    kb.adjust(1, 2, 2, 2, 1)
    return kb.as_markup()


def times_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for slot in TIME_SLOTS:
        kb.button(text=slot, callback_data=f"time:{slot}")
    kb.button(text="⬅️ Orqaga", callback_data="back:date")
    kb.button(text="❌ Bekor qilish", callback_data="cancel")
    kb.adjust(4, 4, 2)
    return kb.as_markup()


def sectors_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for sector in SECTORS:
        kb.button(text=sector.name, callback_data=f"sector:{sector.code}")
    kb.button(text="⬅️ Orqaga", callback_data="back:time")
    kb.button(text="❌ Bekor qilish", callback_data="cancel")
    kb.adjust(2, 2, 2, 2)
    return kb.as_markup()


def tariffs_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for tariff in TARIFFS:
        kb.button(text=f"{tariff.name} — {money(tariff.price)}",
                  callback_data=f"tariff:{tariff.code}")
    kb.button(text="⬅️ Orqaga", callback_data="back:sector")
    kb.button(text="❌ Bekor qilish", callback_data="cancel")
    kb.adjust(1, 1, 1, 1, 2)
    return kb.as_markup()


def people_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for n in range(1, 9):
        kb.button(text=str(n), callback_data=f"people:{n}")
    kb.button(text="⬅️ Orqaga", callback_data="back:tariff")
    kb.button(text="❌ Bekor qilish", callback_data="cancel")
    kb.adjust(4, 4, 2)
    return kb.as_markup()


def phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Raqamimni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def comment_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Izohsiz davom etish", callback_data="comment:skip")
    kb.button(text="❌ Bekor qilish", callback_data="cancel")
    kb.adjust(1)
    return kb.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tasdiqlash", callback_data="confirm:yes")
    kb.button(text="❌ Bekor qilish", callback_data="cancel")
    kb.adjust(1)
    return kb.as_markup()


def admin_booking_kb(booking_id: int) -> InlineKeyboardMarkup:
    """Adminga keladigan xabar ostidagi tugmalar."""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tasdiqlash", callback_data=f"adm:ok:{booking_id}")
    kb.button(text="❌ Bekor qilish", callback_data=f"adm:no:{booking_id}")
    kb.button(text="🎟 Belgi qo'shish", callback_data=f"adm:stamp:{booking_id}")
    kb.adjust(2, 1)
    return kb.as_markup()


def admin_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🆕 Yangi buyurtmalar", callback_data="adm:list:new")
    kb.button(text="📅 Bugungi jadval", callback_data="adm:today")
    kb.button(text="📊 Statistika", callback_data="adm:stats")
    kb.button(text="🎟 Pass boshqaruvi", callback_data="adm:passhelp")
    kb.adjust(1)
    return kb.as_markup()


def site_kb() -> InlineKeyboardMarkup:
    from bot.config import CLUB_SITE

    kb = InlineKeyboardBuilder()
    kb.button(text="🌐 Saytni ochish", url=CLUB_SITE)
    return kb.as_markup()
