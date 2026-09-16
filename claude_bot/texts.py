"""Botning barcha matnlari — bir joyda, o'zbekcha."""
from __future__ import annotations

WELCOME = (
    "Salom! Men Claude'ga ulangan botman.\n\n"
    "Savolingizni shunchaki yozing — men uni Claude'ga yuborib, javobini shu "
    "yerga qaytaraman. O'zbek, rus yoki ingliz tilida yozishingiz mumkin.\n\n"
    "Suhbat konteksti eslab qolinadi, ya'ni «buni qisqartir» deb davom "
    "ettirsangiz ham tushunaman.\n\n"
    "Kerak bo'lsa internetdan qidirib ham ko'raman — bugungi yangilik yoki "
    "kurs kabi narsalarni so'rayvering.\n\n"
    "Rasm yoki fayl (PDF, Word, Excel, matn) yuborsangiz ham o'qiyman — "
    "izohiga savolingizni yozing.\n\n"
    "<b>Buyruqlar</b>\n"
    "/new — suhbatni noldan boshlash\n"
    "/pdf — oxirgi javobni PDF fayl qilish\n"
    "/cost — qancha pul sarflandi\n"
    "/model — qaysi model ishlayotgani\n"
    "/id — Telegram ID ingiz\n"
    "/help — shu yordam"
)

THINKING = "⏳ O'ylayapman…"

# Qurol ishga tushganda ko'rsatiladigan holat.
TOOL_STATUS = {
    "web_search": "🔎 Internetdan qidiryapman…",
    "web_fetch": "📄 Sahifani o'qiyapman…",
    "code_execution": "🧮 Hisoblayapman…",
    "bash_code_execution": "🧮 Hisoblayapman…",
}

_CODE_TOOLS = ("code_execution", "bash_code_execution")


def tool_status(name: str, mode: str = "") -> str:
    """Qurol nomidan foydalanuvchiga ko'rsatiladigan holat.

    `web` rejimida qidiruv quroli natijalarni saralash uchun ichida kod
    bajaradi. Buni «hisoblayapman» deb ko'rsatsak, foydalanuvchi nima
    bo'layotganini noto'g'ri tushunadi — aslida bu hamon qidiruvning bir
    qismi.
    """
    if mode == "web" and name in _CODE_TOOLS:
        return TOOL_STATUS["web_search"]
    return TOOL_STATUS.get(name, "🛠 Qurol ishlatyapman…")
CLEARED = "🧹 Suhbat tozalandi. Yangi mavzudan boshlayveramiz."
EMPTY_ANSWER = "Claude bo'sh javob qaytardi. Savolni boshqacha yozib ko'ring."
NOT_ALLOWED = (
    "Bu bot yopiq rejimda ishlayapti. Egasidan sizni ro'yxatga qo'shishini "
    "so'rang — /id buyrug'i sizning raqamingizni ko'rsatadi."
)
ONLY_TEXT = (
    "Hozircha matn, rasm va faylni o'qiy olaman. Ovozli xabar, video yoki "
    "stikerni esa yo'q — matn bilan yozib yuboring."
)

DOWNLOADING = "📥 Faylni olyapman…"

MAKING_FILE = "📎 Fayl tayyorlayapman…"
MAKING_PDF = "📄 PDF tayyorlayapman…"
PDF_READY = "Mana, PDF tayyor."
PDF_SENT = "📄 PDF yuborildi."
PDF_FAILED = "❌ PDF yasab bo'lmadi. Javob juda uzun yoki g'alati bo'lishi mumkin."
NOTHING_TO_EXPORT = (
    "Hali PDF qiladigan javob yo'q. Avval savol bering, keyin /pdf yozing."
)
READING_FILE = "📖 Faylni o'qiyapman…"

# Rasm/fayl izohsiz kelganda beriladigan savol.
DEFAULT_IMAGE_PROMPT = "Bu rasmda nima bor? Muhim joylarini tushuntirib ber."
DEFAULT_FILE_PROMPT = "Bu faylni o'qib, asosiy mazmunini qisqacha aytib ber."

UNSUPPORTED_FILE = (
    "Bu turdagi faylni o'qiy olmayman. Men tushunadiganlari: rasm (JPG, PNG), "
    "PDF, Word (.docx), Excel (.xlsx) va oddiy matn (.txt, .csv, .json).\n\n"
    "Boshqa format bo'lsa, PDF ga o'girib yuboring."
)

EMPTY_FILE = (
    "Faylni ochdim, lekin ichida o'qiydigan matn topmadim. Skanerdan o'tgan "
    "hujjat bo'lsa, uni rasm sifatida yuboring — o'shanda o'qiy olaman."
)

BROKEN_FILE = (
    "Faylni ocholmadim — buzilgan yoki parol bilan yopilgan bo'lishi mumkin."
)


def file_too_big(limit_mb: int) -> str:
    return (
        f"Fayl juda katta — {limit_mb} MB dan oshmasin. Kerakli sahifalarini "
        "alohida yuboring yoki siqib yuboring."
    )


def media_marker(name: str) -> str:
    """Fayl tarixda shu matn bilan qoladi — o'zi emas, nomi."""
    return f"[«{name}» yuborildi]"

def too_long(limit: int) -> str:
    return (
        f"Savol juda uzun — {limit} belgidan oshmasin. "
        "Muhim qismini qoldirib, qayta yuboring."
    )


def rate_limited(per_minute: int) -> str:
    return (
        f"Biroz sekinroq 🙂 Daqiqasiga {per_minute} tagacha savol bera olasiz. "
        "Bir daqiqadan keyin urinib ko'ring."
    )


def cost_line(usd: str) -> str:
    """Javob oxiriga qo'shiladigan kichkina eslatma."""
    return f"\n\n<i>· {usd}</i>"


def cost_report(summary: dict, model: str, money) -> str:
    return (
        "💰 <b>Sarf hisobi</b>\n\n"
        f"<b>So'nggi 24 soat:</b> {money(summary['recent_usd'])}"
        f" ({summary['recent_calls']} ta savol)\n"
        f"<b>Bot yoqilgandan beri:</b> {money(summary['usd'])}"
        f" ({summary['calls']} ta savol)\n"
        f"<b>Model:</b> <code>{model}</code>\n\n"
        "Bu <b>taxminiy</b> hisob — faqat matn tokenlari. Internet "
        "qidiruvining o'z narxi bunga kirmaydi.\n\n"
        "Aniq raqam: platform.claude.com → Usage\n\n"
        "Tejash uchun eng oson yo'l — mavzu tugagach /new yozish: uzun suhbat "
        "har savolda boshidan qayta yuboriladi."
    )


def model_info(model: str, effort: str, history_len: int, tools: str) -> str:
    return (
        f"<b>Model:</b> <code>{model}</code>\n"
        f"<b>Effort:</b> <code>{effort}</code>\n"
        f"<b>Qurollar:</b> {tools}\n"
        f"<b>Eslab turganim:</b> {history_len} ta xabar\n\n"
        "Tozalash uchun /new."
    )


# --- Xatoliklar ------------------------------------------------------------

ERR_AUTH = (
    "❌ ANTHROPIC_API_KEY qabul qilinmadi. Kalit noto'g'ri yoki muddati "
    "tugagan bo'lishi mumkin."
)
ERR_CREDIT = (
    "❌ Anthropic hisobida mablag' yoki ruxsat yetmayapti. "
    "platform.claude.com dagi balansni tekshiring."
)
ERR_RATE = "⏳ Claude hozir band (rate limit). Bir necha soniyadan so'ng qayta yuboring."
ERR_BAD_REQUEST = (
    "❌ So'rovni Claude qabul qilmadi. Model nomi yoki sozlamalarni tekshiring "
    "(/model buyrug'i nimalar ishlayotganini ko'rsatadi)."
)
ERR_SERVER = "❌ Claude tomonida vaqtinchalik nosozlik. Birozdan keyin urinib ko'ring."
ERR_NETWORK = "❌ Claude'ga ulana olmadim. Internet aloqasini tekshiring."
ERR_TIMEOUT = "❌ Javob juda uzoq kutildi. Savolni qisqartirib yuboring."
ERR_UNKNOWN = "❌ Kutilmagan xatolik. Birozdan keyin urinib ko'ring."


def refused(reason: str | None) -> str:
    tail = f"\n\nSabab: {reason}" if reason else ""
    return "⚠️ Claude bu savolga javob berishdan bosh tortdi." + tail
