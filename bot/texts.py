"""Xabar matnlari. HTML parse mode ishlatiladi."""
from __future__ import annotations

from datetime import date
from html import escape
from typing import Any, Mapping

from bot.catalog import SECTORS, SECTORS_BY_CODE, TARIFFS, TARIFFS_BY_CODE, money
from bot.config import CLUB_ADDRESS, CLUB_PHONE, CLUB_SITE, STAMPS_PER_REWARD

WELCOME = (
    "⚔️ <b>GLADIATOR GAMING ARENA</b>\n\n"
    "Yakkabog', Qashqadaryo — PS5 gaming arena.\n"
    "6 ta stansiya, 4K HDR ekranlar, 24/7 ish vaqti.\n\n"
    "Quyidagi tugmalardan birini tanlang 👇"
)

PRICES_HEAD = "💰 <b>Tariflar</b>\n\n"
ARENA_HEAD = "🗺 <b>Arena xaritasi</b>\n\nHar bir sektor o'ziga xos:\n\n"

CONTACT = (
    "📞 <b>Aloqa</b>\n\n"
    f"Telefon: <a href='tel:{CLUB_PHONE}'>{CLUB_PHONE}</a>\n"
    f"Manzil: {CLUB_ADDRESS}\n"
    "Ish vaqti: har kuni, 24/7\n"
    "Telegram: @gladiator_gaming\n"
    "Instagram: @gladiator.gaming\n\n"
    f"Sayt: {CLUB_SITE}"
)


def prices() -> str:
    lines = [PRICES_HEAD]
    for tariff in TARIFFS:
        lines.append(f"▫️ <b>{tariff.name}</b> — {money(tariff.price)}\n{tariff.desc}\n")
    return "\n".join(lines)


def arena() -> str:
    lines = [ARENA_HEAD]
    for i, sector in enumerate(SECTORS, start=1):
        lines.append(f"<b>Sektor {i:02d} — {sector.name}</b>\n{sector.desc}\n")
    return "\n".join(lines)


def _fmt_date(iso: str) -> str:
    try:
        d = date.fromisoformat(iso)
    except ValueError:
        return iso
    if d == date.today():
        return f"bugun, {d.strftime('%d.%m.%Y')}"
    return d.strftime("%d.%m.%Y")


def booking_summary(data: Mapping[str, Any]) -> str:
    sector = SECTORS_BY_CODE.get(data.get("sector_code", ""))
    tariff = TARIFFS_BY_CODE.get(data.get("tariff_code", ""))
    comment = data.get("comment")
    lines = [
        "📋 <b>Buyurtmangizni tasdiqlang</b>\n",
        f"📅 Sana: <b>{_fmt_date(str(data.get('booking_date', '')))}</b>",
        f"🕐 Vaqt: <b>{escape(str(data.get('time_slot', '')))}</b>",
        f"🎯 Sektor: <b>{escape(sector.name if sector else '—')}</b>",
        f"💰 Tarif: <b>{escape(tariff.name if tariff else '—')}</b>"
        + (f" ({money(tariff.price)})" if tariff else ""),
        f"👥 Kishi: <b>{data.get('people', 1)}</b>",
        f"📱 Telefon: <b>{escape(str(data.get('phone', '—')))}</b>",
    ]
    if comment:
        lines.append(f"💬 Izoh: {escape(str(comment))}")
    lines.append("\nHammasi to'g'rimi?")
    return "\n".join(lines)


def booking_saved(booking_id: int) -> str:
    return (
        f"✅ <b>Buyurtma qabul qilindi!</b>\n\n"
        f"Buyurtma raqami: <b>#{booking_id}</b>\n\n"
        "Administrator tez orada siz bilan bog'lanadi va joyingizni tasdiqlaydi.\n"
        f"Shoshilinch bo'lsa: <a href='tel:{CLUB_PHONE}'>{CLUB_PHONE}</a>"
    )


def admin_new_booking(booking_id: int, data: Mapping[str, Any], user) -> str:
    sector = SECTORS_BY_CODE.get(data.get("sector_code", ""))
    tariff = TARIFFS_BY_CODE.get(data.get("tariff_code", ""))
    handle = f"@{user.username}" if user.username else "—"
    comment = data.get("comment")
    lines = [
        f"🆕 <b>Yangi buyurtma #{booking_id}</b>\n",
        f"👤 {escape(user.full_name)} ({handle})",
        f"🆔 <code>{user.id}</code>",
        f"📱 {escape(str(data.get('phone', '—')))}",
        "",
        f"📅 {_fmt_date(str(data.get('booking_date', '')))} — 🕐 {escape(str(data.get('time_slot', '')))}",
        f"🎯 {escape(sector.name if sector else '—')}",
        f"💰 {escape(tariff.name if tariff else '—')}"
        + (f" ({money(tariff.price)})" if tariff else ""),
        f"👥 {data.get('people', 1)} kishi",
    ]
    if comment:
        lines.append(f"💬 {escape(str(comment))}")
    return "\n".join(lines)


def booking_row(row: Any) -> str:
    """Adminlar ro'yxati uchun bir qatorli ko'rinish."""
    sector = SECTORS_BY_CODE.get(row["sector_code"])
    status_icon = {"new": "🆕", "confirmed": "✅", "cancelled": "❌"}.get(row["status"], "•")
    return (
        f"{status_icon} <b>#{row['id']}</b> — {_fmt_date(row['booking_date'])} "
        f"{row['time_slot']}\n"
        f"    {escape(sector.name if sector else '—')}, {row['people']} kishi, "
        f"{escape(row['phone'] or '—')}"
    )


def pass_card(card: Any, full_name: str) -> str:
    stamps = card["stamps"] if card else 0
    total = card["total_visits"] if card else 0
    rewards = card["rewards"] if card else 0
    filled = "🟠" * stamps
    empty = "⚪️" * max(0, STAMPS_PER_REWARD - stamps)
    left = max(0, STAMPS_PER_REWARD - stamps)
    lines = [
        "🎟 <b>Gladiator Pass</b>\n",
        f"👤 {escape(full_name)}\n",
        f"{filled}{empty}",
        f"<b>{stamps} / {STAMPS_PER_REWARD}</b> belgi\n",
        f"Jami tashriflar: <b>{total}</b>",
        f"Olingan bepul soatlar: <b>{rewards}</b>\n",
    ]
    if left == 0:
        lines.append("🎉 Kartangiz to'ldi — keyingi soat <b>bepul</b>!")
    else:
        lines.append(
            f"Yana <b>{left}</b> ta tashrif — va 1 soat <b>bepul</b> o'ynaysiz."
        )
    lines.append(
        "\n<i>Belgi administrator tomonidan har tashrifda qo'yiladi. "
        "Kelganingizda shu kartani ko'rsating.</i>"
    )
    return "\n".join(lines)


def stamp_added(card: Any, earned: bool) -> str:
    if earned:
        return (
            "🎉 <b>Tabriklaymiz!</b>\n\n"
            f"Kartangiz to'ldi — sizga <b>1 soat bepul o'yin</b> berildi!\n"
            f"Yangi karta boshlandi: {card['stamps']} / {STAMPS_PER_REWARD}"
        )
    left = STAMPS_PER_REWARD - card["stamps"]
    return (
        f"🎟 <b>Yangi belgi qo'yildi!</b>\n\n"
        f"Holat: <b>{card['stamps']} / {STAMPS_PER_REWARD}</b>\n"
        f"Bepul soatgacha yana <b>{left}</b> ta tashrif."
    )


def stats(data: Mapping[str, int]) -> str:
    return (
        "📊 <b>Statistika</b>\n\n"
        f"Jami buyurtmalar: <b>{data['total']}</b>\n"
        f"  🆕 yangi: {data['new']}\n"
        f"  ✅ tasdiqlangan: {data['confirmed']}\n"
        f"  ❌ bekor qilingan: {data['cancelled']}\n\n"
        f"Mijozlar: <b>{data['clients']}</b>\n"
        f"Pass kartalari: <b>{data['cards']}</b>\n"
        f"Berilgan bepul soatlar: <b>{data['rewards']}</b>"
    )


PASS_HELP = (
    "🎟 <b>Pass boshqaruvi</b>\n\n"
    "Mijozga belgi qo'yish uchun:\n"
    "<code>/stamp &lt;ID yoki telefon&gt;</code>\n\n"
    "Masalan:\n"
    "<code>/stamp 123456789</code>\n"
    "<code>/stamp +998901234567</code>\n\n"
    "Kartani ko'rish uchun:\n"
    "<code>/card &lt;ID yoki telefon&gt;</code>\n\n"
    "Buyurtma xabari ostidagi «🎟 Belgi qo'shish» tugmasi ham shu ishni bajaradi."
)

CANCELLED = "Bekor qilindi. Asosiy menyuga qaytdingiz."
NOT_ADMIN = "Bu bo'lim faqat administratorlar uchun."
ASK_PHONE = (
    "📱 <b>Telefon raqamingiz</b>\n\n"
    "Pastdagi tugma orqali yuboring yoki raqamni qo'lda yozing.\n"
    "Masalan: <code>+998901234567</code>"
)
BAD_PHONE = "Raqam tushunarsiz. Iltimos, <code>+998901234567</code> ko'rinishida yozing."
ASK_COMMENT = (
    "💬 <b>Qo'shimcha izoh</b>\n\n"
    "Maxsus so'rovingiz bo'lsa yozing (masalan: tug'ilgan kun, qaysi o'yin).\n"
    "Bo'lmasa — «Izohsiz davom etish» tugmasini bosing."
)
