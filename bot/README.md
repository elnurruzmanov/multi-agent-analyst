# Gladiator Gaming Arena — Telegram bot

Klub uchun bot: joy band qilish, narxlar, arena ma'lumoti, Gladiator Pass
sodiqlik kartasi va admin panel. Sayt bilan bir xil narx/sektor ma'lumotidan
foydalanadi (`bot/catalog.py` ↔ `frontend/gladiator/index.html`).

## Buyurtma qayerda saqlanadi

Uchta qatlam birga ishlaydi — biri ikkinchisini almashtirmaydi:

| Qatlam | Roli | Ishlashi uchun nima kerak |
| --- | --- | --- |
| SQLite (`bot/data/gladiator.db`) | asosiy manba, ro'yxat va statistika shu yerdan | hech narsa |
| Telegram xabari | admin darhol ko'radi, tugma bilan tasdiqlaydi | `ADMIN_IDS` |
| Google Sheets | jadval ko'rinishida ko'rish uchun ko'zgu | `GOOGLE_SHEET_ID` + kalit |

Sheets kalitisiz bot to'liq ishlayveradi — u qatlam jimgina o'chib qoladi.

## Sozlash

**1. Botni yarating.** Telegram'da [@BotFather](https://t.me/BotFather) ga
`/newbot` yozing, nom va username bering. U bergan tokenni saqlang.

**2. Admin ID ingizni bilib oling.** Botni ishga tushirgach unga `/id` yozing —
u sizning raqamli ID ingizni qaytaradi.

**3. Lokal ishga tushirish:**

```bash
pip install -r requirements-bot.txt
```

`.env` fayliga qo'shing (namuna `.env.example` da):

```
BOT_TOKEN=123456:ABC-DEF...
ADMIN_IDS=123456789
```

```bash
python -m bot.main
```

**4. Render'ga deploy.** `render.yaml` da `gladiator-bot` nomli worker servisi
tayyor. Render dashboard'ida `BOT_TOKEN` va `ADMIN_IDS` ni kiriting.

> Bepul tarifda Render diski vaqtinchalik: qayta deploy qilinganda SQLite
> bazasi nolga qaytadi. Buyurtmalar shu sababli darhol Telegram xabari
> sifatida ham yuboriladi. Tarix doimiy turishi kerak bo'lsa, pullik disk
> ulab `DB_PATH` ni `/var/data/gladiator.db` ga o'zgartiring.

## Google Sheets (ixtiyoriy)

1. Google Cloud'da service account yarating, JSON kalitini yuklab oling.
2. Yangi Google Sheet oching, uni service account emailiga tahrirlash huquqi
   bilan ulashing.
3. Env var qo'shing:
   - `GOOGLE_SHEET_ID` — jadval URL'idagi uzun ID.
   - `GOOGLE_CREDENTIALS_JSON` — JSON kalitning **butun matni** bir qatorda.

## Admin buyruqlari

| Buyruq | Nima qiladi |
| --- | --- |
| `/admin` | panel: yangi buyurtmalar, bugungi jadval, statistika |
| `/stamp <ID yoki telefon>` | mijozga Pass belgisi qo'yadi |
| `/card <ID yoki telefon>` | mijoz kartasini ko'rsatadi |
| `/id` | o'z Telegram ID ingizni ko'rsatadi |

Har bir yangi buyurtma xabari ostida «✅ Tasdiqlash», «❌ Bekor qilish» va
«🎟 Belgi qo'shish» tugmalari bo'ladi — mijoz javobni avtomatik oladi.

## Testlar

```bash
python -m pytest tests/test_bot.py -q
```

Testlar Telegram'ga chiqmaydi — faqat baza va matn mantiqini tekshiradi.
