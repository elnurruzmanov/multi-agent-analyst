"""Claude bot sozlamalari — barchasi environment orqali beriladi.

Gladiator boti (`bot/`) bilan bir repoda yashaydi, shuning uchun token nomi
alohida: `CLAUDE_BOT_TOKEN`. Agar u berilmasa `BOT_TOKEN` ishlatiladi — bitta
botni sinab ko'rayotganda qulay bo'lsin uchun.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = (os.getenv("CLAUDE_BOT_TOKEN") or os.getenv("BOT_TOKEN") or "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()

MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5").strip()

# Effort — javob ustida qancha "o'ylansin". Telegram suhbatida kutish vaqti
# muhim, shuning uchun default `medium`; murakkab savollar uchun `high` yoki
# `xhigh` qo'ying.
_EFFORT_LEVELS = {"low", "medium", "high", "xhigh", "max"}
EFFORT = os.getenv("CLAUDE_EFFORT", "medium").strip().lower()
if EFFORT not in _EFFORT_LEVELS:
    EFFORT = "medium"

MAX_TOKENS = int(os.getenv("CLAUDE_MAX_TOKENS", "16000"))

# Adaptive thinking — hozirgi modellarda (opus-5, sonnet-5, opus-4-8 …) yoqiq.
# Eski modellar (masalan claude-haiku-4-5) uni qabul qilmaydi: o'shanda
# CLAUDE_THINKING=0 qo'ying.
USE_THINKING = os.getenv("CLAUDE_THINKING", "1").strip().lower() not in {
    "0", "false", "no", "off",
}

# Server tomonidagi fallback: Claude javob berishdan bosh tortsa, so'rov o'sha
# chaqiruv ichida boshqa modelga o'tadi. Kerak bo'lmasa CLAUDE_FALLBACKS=0.
USE_FALLBACKS = os.getenv("CLAUDE_FALLBACKS", "1").strip().lower() not in {
    "0", "false", "no", "off",
}

SYSTEM_PROMPT = os.getenv(
    "CLAUDE_SYSTEM_PROMPT",
    "Sen Telegram bot orqali ishlaydigan yordamchisan. Foydalanuvchi qaysi "
    "tilda yozsa (o'zbek, rus, ingliz), o'sha tilda javob ber. Javoblar aniq "
    "va qisqa bo'lsin — Telegram xabari uzun bo'lmagani ma'qul. Jadval o'rniga "
    "oddiy ro'yxat ishlat, kod kerak bo'lsa ``` bilan blokka ol.",
).strip()

# Claude tomonida ishlaydigan qurollar: `web` — internetdan qidirish va
# o'qish, `code` — kod bajarish, `off` — qurolsiz. Batafsil: tools.py.
# Qurollar javobni aniqroq qiladi, lekin har chaqiruv qo'shimcha pul turadi.
TOOLS = os.getenv("CLAUDE_TOOLS", "web").strip().lower()
if TOOLS not in ("web", "code", "off"):
    TOOLS = "web"

# Bitta javob ichida qurol nechta marta ishlatilsin.
MAX_TOOL_USES = int(os.getenv("CLAUDE_MAX_TOOL_USES", "5"))

# Nechta xabar (savol + javob) esda qolsin. /new bu tarixni tozalaydi.
HISTORY_LIMIT = int(os.getenv("CLAUDE_HISTORY_LIMIT", "20"))

# Bitta savol uchun belgilar chegarasi — hisobni himoya qiladi.
MAX_QUESTION_CHARS = int(os.getenv("CLAUDE_MAX_QUESTION_CHARS", "4000"))

# Bir foydalanuvchi bir daqiqada nechta savol bera oladi. 0 — cheklovsiz.
RATE_LIMIT_PER_MINUTE = int(os.getenv("CLAUDE_RATE_LIMIT", "10"))

# Bo'sh qolsa — bot hammaga ochiq. Faqat o'zingiz uchun bo'lsa, /id dan olingan
# raqamni shu yerga yozing (vergul bilan bir nechta bo'lishi mumkin).
ALLOWED_USER_IDS: set[int] = {
    int(part)
    for part in os.getenv("CLAUDE_ALLOWED_USER_IDS", "").replace(" ", "").split(",")
    if part
}


# --- Webhook rejimi (ixtiyoriy) -------------------------------------------
# Berilsa — bot doim ishlaydigan «worker» emas, oddiy web servis sifatida
# yashaydi: Telegram xabar kelganda shu manzilga o'zi murojaat qiladi.
# Manzil to'liq bo'lsin: https://mening-botim.onrender.com
WEBHOOK_URL = (
    os.getenv("CLAUDE_WEBHOOK_URL")
    # Render web servisga o'z manzilini shu nom bilan beradi — qo'lda yozish
    # shart bo'lmasligi uchun uni ham qaraymiz.
    or os.getenv("RENDER_EXTERNAL_URL")
    or ""
).strip().rstrip("/")

# Hosting qaysi portni bersa — o'shani tinglaymiz.
PORT = int(os.getenv("PORT", "10000"))


def is_allowed(user_id: int) -> bool:
    """Ro'yxat bo'sh bo'lsa bot ochiq, aks holda faqat ro'yxatdagilar."""
    return not ALLOWED_USER_IDS or user_id in ALLOWED_USER_IDS


def require_token() -> str:
    if not BOT_TOKEN:
        raise SystemExit(
            "CLAUDE_BOT_TOKEN berilmagan.\n"
            "Telegram'da @BotFather ga /newbot yozib token oling, so'ng uni\n"
            "  .env fayliga CLAUDE_BOT_TOKEN=... deb qo'shing "
            "(yoki Render'da env var qiling)."
        )
    return BOT_TOKEN


def require_api_key() -> str:
    if not ANTHROPIC_API_KEY:
        raise SystemExit(
            "ANTHROPIC_API_KEY berilmagan.\n"
            "Kalitni https://platform.claude.com/settings/keys dan oling, so'ng\n"
            "  .env fayliga ANTHROPIC_API_KEY=sk-ant-... deb qo'shing."
        )
    return ANTHROPIC_API_KEY
