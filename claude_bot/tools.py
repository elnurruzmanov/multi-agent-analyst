"""Claude tomonida ishlaydigan qurollar (server tools).

Bu qurollarni biz bajarmaymiz — ular Anthropic serverida ishlaydi. Bizning
ishimiz faqat «shulardan foydalansang bo'ladi» deb aytish; qachon va qanday
chaqirishni Claude o'zi hal qiladi.

`CLAUDE_TOOLS` uchta qiymatni oladi:

| qiymat | nima beriladi | nimaga arziydi |
| --- | --- | --- |
| `web` (default) | internetdan qidirish va sahifani o'qish | yangi ma'lumot, bugungi narx-kurs |
| `code` | kod bajarish + oddiy qidiruv | hisob-kitob, jadval, grafik |
| `off` | hech narsa | eng arzon, eng tez |

Nega `web` va `code` birga emas: yangi qidiruv quroli natijalarni saralash
uchun ichida kod bajarish muhitini ishlatadi. Yoniga ikkinchi muhit qo'shsak,
model qaysi birini ishlatishni chalkashtiradi. Shuning uchun `code` rejimida
qidiruvning oddiyroq, eski varianti beriladi.
"""
from __future__ import annotations

# Bu qurollar Opus 5, Opus 4.6+ va Sonnet 5 / 4.6 da ishlaydi. Eskiroq modelga
# o'tsangiz (masalan haiku), CLAUDE_TOOLS=off qiling.
WEB_SEARCH = "web_search_20260209"
WEB_FETCH = "web_fetch_20260209"
BASIC_WEB_SEARCH = "web_search_20250305"
CODE_EXECUTION = "code_execution_20260521"

MODES = ("web", "code", "off")

# Qurol chaqiruvi pul turadi, shuning uchun bitta javob ichida nechta marta
# ishlatilishini cheklaymiz.
DEFAULT_MAX_USES = 5


def build(mode: str, max_uses: int = DEFAULT_MAX_USES) -> list[dict]:
    """Rejim nomidan API'ga yuboriladigan qurollar ro'yxatini yasaydi."""
    if mode == "web":
        return [
            {"type": WEB_SEARCH, "name": "web_search", "max_uses": max_uses},
            {"type": WEB_FETCH, "name": "web_fetch", "max_uses": max_uses},
        ]
    if mode == "code":
        return [
            {"type": CODE_EXECUTION, "name": "code_execution"},
            {"type": BASIC_WEB_SEARCH, "name": "web_search", "max_uses": max_uses},
        ]
    return []


def describe(mode: str) -> str:
    """Foydalanuvchiga /model buyrug'ida ko'rsatiladigan izoh."""
    if mode == "web":
        return "internetdan qidirish va o'qish"
    if mode == "code":
        return "kod bajarish va qidirish"
    return "yo'q"
