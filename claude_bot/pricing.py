"""Sarflangan pulni taxminlash.

API javobda nechta token ishlatilganini aytadi, narxni esa o'zimiz bilamiz.
Shu ikkisidan taxminiy summa chiqadi.

**Taxminiy** so'zi muhim: bu hisobga faqat matn tokenlari kiradi. Internet
qidiruvining o'z narxi bor va u bu yerda ko'rinmaydi. Aniq raqam har doim
platform.claude.com → Usage sahifasida.
"""
from __future__ import annotations

# 1 million token uchun dollarda: (kirish, chiqish).
PRICES: dict[str, tuple[float, float]] = {
    "claude-fable-5-1": (10.0, 50.0),
    "claude-fable-5": (10.0, 50.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-opus-4-6": (5.0, 25.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}

# Notanish model uchun — eng qimmatidan kelib chiqamiz, ya'ni taxmin
# kam emas, ko'proq chiqadi. Kutilmagan hisob kutilmagan kamdan yaxshi.
FALLBACK = (5.0, 25.0)


def rates(model: str) -> tuple[float, float]:
    """Model nomidan narxni topadi; nom to'liq mos kelmasa — eng uzun mosi."""
    if model in PRICES:
        return PRICES[model]
    matches = [name for name in PRICES if model.startswith(name)]
    if matches:
        return PRICES[max(matches, key=len)]
    return FALLBACK


def cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Bitta javobning taxminiy narxi — dollarda."""
    per_input, per_output = rates(model)
    return (input_tokens * per_input + output_tokens * per_output) / 1_000_000


def money(usd: float) -> str:
    """Summani o'zbekcha, o'qishga qulay ko'rinishda beradi."""
    if usd <= 0:
        return "0"
    if usd < 0.01:
        return "1 sentdan kam"
    if usd < 1:
        return f"~{round(usd * 100)} sent"
    return f"~${usd:.2f}"
