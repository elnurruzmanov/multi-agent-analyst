"""Bot sozlamalari — barchasi environment orqali beriladi."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Kim admin — @userinfobot dan olingan raqamli ID lar, vergul bilan.
ADMIN_IDS: set[int] = {
    int(part) for part in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if part
}

# Render'ning bepul tarifida disk vaqtinchalik, shuning uchun yo'l sozlanadigan:
# doimiy disk ulaganda DB_PATH ni /var/data/gladiator.db ga o'zgartiring.
DB_PATH = Path(os.getenv("DB_PATH", Path(__file__).parent / "data" / "gladiator.db"))

# Google Sheets — ixtiyoriy. Kalit berilmasa bot Sheets'siz to'liq ishlayveradi.
SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "").strip()
SHEET_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS_JSON", "").strip()

CLUB_PHONE = os.getenv("CLUB_PHONE", "+998914556235")
CLUB_ADDRESS = os.getenv("CLUB_ADDRESS", "Yakkabog', Qashqadaryo")
CLUB_SITE = os.getenv("CLUB_SITE", "https://multi-agent-analyst-nine.vercel.app/gladiator/")

# Sodiqlik kartasi: nechta belgidan keyin bepul soat beriladi.
STAMPS_PER_REWARD = int(os.getenv("STAMPS_PER_REWARD", "10"))


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def require_token() -> str:
    if not BOT_TOKEN:
        raise SystemExit(
            "BOT_TOKEN berilmagan.\n"
            "Telegram'da @BotFather ga /newbot yozib token oling, so'ng:\n"
            "  .env fayliga BOT_TOKEN=... deb qo'shing (yoki Render'da env var qiling)."
        )
    return BOT_TOKEN
