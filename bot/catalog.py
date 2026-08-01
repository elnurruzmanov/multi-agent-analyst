"""Arena ma'lumotlari — saytdagi narx va sektorlar bilan bir xil.

Narx yoki sektor o'zgarsa, faqat shu faylni va frontend/gladiator/index.html ni
yangilash kifoya.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Sector:
    code: str
    name: str
    desc: str


@dataclass(frozen=True)
class Tariff:
    code: str
    name: str
    price: int  # so'mda
    desc: str


SECTORS: tuple[Sector, ...] = (
    Sector("s1", "Solo Arena", "Yakka jangchilar uchun 2 ta stansiya"),
    Sector("s2", "Duel Zone", "1v1 musobaqalar uchun mos joy"),
    Sector("s3", "Squad Room", "4 kishilik jamoa xonasi"),
    Sector("s4", "VIP Loji", "Alohida xona, qulay divanlar"),
    Sector("s5", "Racing Pit", "Rul va pedallar bilan jihozlangan"),
    Sector("s6", "Chill Corner", "Kutish va dam olish zonasi"),
)

TARIFFS: tuple[Tariff, ...] = (
    Tariff("t1", "1 soat", 15_000, "Bitta stansiya, bitta soat — tezkor raund uchun."),
    Tariff("t3", "3 soat", 40_000, "Eng ko'p tanlanadigan paket, do'stlar bilan kelish uchun ideal."),
    Tariff("vip", "VIP loji / soat", 35_000, "Alohida xona, katta ekran, shaxsiy muhit."),
    Tariff("night", "Tungi paket", 60_000, "23:00–07:00 — tun bo'yi cheklovsiz o'ynang."),
)

SECTORS_BY_CODE = {s.code: s for s in SECTORS}
TARIFFS_BY_CODE = {t.code: t for t in TARIFFS}

# Band qilish uchun taklif qilinadigan vaqtlar.
TIME_SLOTS: tuple[str, ...] = (
    "10:00", "12:00", "14:00", "16:00",
    "18:00", "20:00", "22:00", "00:00",
)


def money(amount: int) -> str:
    """15000 -> '15 000 so'm'"""
    return f"{amount:,}".replace(",", " ") + " so'm"
