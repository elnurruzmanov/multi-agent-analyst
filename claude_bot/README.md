# Claude Telegram bot

Telegram'ga savol yozasiz — bot uni Claude API'ga yuboradi va javobni shu
yerga qaytaradi. Ishda sun'iy intellekt sayti ochilmasa ham, Telegram ochilsa
bot orqali Claude bilan ishlash mumkin bo'ladi.

```
siz → Telegram bot → Anthropic API (Claude) → Telegram bot → siz
```

Bu `bot/` papkasidagi Gladiator botidan **alohida** servis: o'z tokeni, o'z
ishga tushirish buyrug'i. Ikkalasi bir vaqtda ishlayverishi mumkin.

## Nima qila oladi

| Imkoniyat | Izoh |
| --- | --- |
| Savol-javob | Oddiy matn yozasiz, javob keladi |
| Suhbat konteksti | Oxirgi ~20 xabar eslab qolinadi, «buni qisqartir» ishlaydi |
| Jonli yozilish | Javob oqim bilan keladi, xabar yozilgani sayin yangilanadi |
| Uzun javoblar | 4096 belgidan uzun javob bo'laklarga bo'linadi, kod bloki buzilmaydi |
| Formatlash | `**qalin**`, `` `kod` ``, ```` ``` ```` bloklari Telegram HTML'ga aylanadi |
| Himoya | Foydalanuvchi ro'yxati, savol uzunligi va daqiqalik limit — hisob bo'shab qolmasin |

Buyruqlar: `/start`, `/new` (suhbatni tozalash), `/model`, `/id`, `/help`.

## Sozlash

**1. Botni yarating.** Telegram'da [@BotFather](https://t.me/BotFather) ga
`/newbot` yozing, nom va username bering — u token beradi.

**2. Anthropic kalitini oling.**
[console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)
da yangi API key yarating. Bu pullik: har bir savol-javob hisobdan pul yechadi,
shuning uchun 3-qadamni o'tkazib yubormang.

**3. `.env` faylini to'ldiring** (namuna — repo ildizidagi `.env.example`):

```
CLAUDE_BOT_TOKEN=123456:ABC-DEF...
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_ALLOWED_USER_IDS=123456789
```

`CLAUDE_ALLOWED_USER_IDS` — botdan kim foydalana olishi. Bo'sh qoldirsangiz bot
**hammaga ochiq** bo'ladi va begona odam ham sizning hisobingiz hisobidan savol
bera oladi. O'z raqamingizni bilish uchun botni ishga tushirib, unga `/id`
yozing.

**4. Ishga tushiring:**

```bash
pip install -r requirements-claude-bot.txt
python -m claude_bot.main
```

Bot ishga tushdi — Telegram'da unga yozing.

## Sozlamalar

Hammasi environment orqali; ko'rsatilganlari default qiymatlar.

| Env var | Default | Nima qiladi |
| --- | --- | --- |
| `CLAUDE_BOT_TOKEN` | — | @BotFather tokeni (bo'lmasa `BOT_TOKEN` olinadi) |
| `ANTHROPIC_API_KEY` | — | Anthropic kaliti |
| `CLAUDE_MODEL` | `claude-opus-5` | Qaysi model |
| `CLAUDE_EFFORT` | `medium` | Javob ustida qancha o'ylansin: `low`…`max` |
| `CLAUDE_MAX_TOKENS` | `16000` | Bitta javobning eng katta uzunligi |
| `CLAUDE_HISTORY_LIMIT` | `20` | Nechta xabar esda qolsin |
| `CLAUDE_MAX_QUESTION_CHARS` | `4000` | Savol uzunligi chegarasi |
| `CLAUDE_RATE_LIMIT` | `10` | Bir foydalanuvchi uchun daqiqasiga savol; `0` — cheklovsiz |
| `CLAUDE_ALLOWED_USER_IDS` | bo'sh | Ruxsat etilganlar; bo'sh — hammaga ochiq |
| `CLAUDE_SYSTEM_PROMPT` | o'zbekcha ko'rsatma | Botning xarakteri |
| `CLAUDE_FALLBACKS` | `1` | Claude javobdan bosh tortsa, zaxira modelga o'tish |
| `CLAUDE_THINKING` | `1` | Adaptive thinking; eski modellarda `0` qiling |
| `CLAUDE_WEBHOOK_URL` | bo'sh | Berilsa webhook rejimi; bo'sh bo'lsa polling |
| `PORT` | `10000` | Webhook rejimida tinglanadigan port (hosting o'zi beradi) |

Tezroq va arzonroq javob kerak bo'lsa: `CLAUDE_EFFORT=low`, yoki
`CLAUDE_MODEL=claude-sonnet-5`. Murakkab masalalar uchun `CLAUDE_EFFORT=xhigh`.

`CLAUDE_MODEL` ni almashtirsangiz, model adaptive thinking'ni qo'llashini
tekshiring (`claude-opus-5`, `claude-sonnet-5`, `claude-opus-4-8` — qo'llaydi).
Eskiroq `claude-haiku-4-5` uni qabul qilmaydi, u bilan `CLAUDE_THINKING=0`
qo'shing.

## Hostingga qo'yish

Botni ikki xil ishlatish mumkin — kodning o'zi bir xil, farqi
`CLAUDE_WEBHOOK_URL` berilgan-berilmaganida.

| Rejim | Qachon | Sozlash |
| --- | --- | --- |
| **Polling** (default) | lokalda va doim ishlab turadigan worker'da | hech narsa — shunchaki ishga tushiring |
| **Webhook** | web servisda, ayniqsa uxlab qoladigan bepul tarifda | `CLAUDE_WEBHOOK_URL=https://<servis>.onrender.com` |

**Worker (polling).** `render.yaml` da `claude-telegram-bot` nomli worker
tayyor: `CLAUDE_BOT_TOKEN`, `ANTHROPIC_API_KEY`, `CLAUDE_ALLOWED_USER_IDS` ni
Render panelida kiritasiz. Eng sodda yo'l, lekin servis to'xtovsiz ishlab
turishi kerak.

**Web servis (webhook).** Render'da *Web Service* yaratasiz:

| Maydon | Qiymat |
| --- | --- |
| Build command | `pip install -r requirements-claude-bot.txt` |
| Start command | `python -m claude_bot.main` |
| Health check path | `/` |

Env var'larga yuqoridagi uchtasi ustiga `CLAUDE_WEBHOOK_URL` ni qo'shasiz —
servisning to'liq manzili (`https://...onrender.com`). Bot o'zi Telegram'ga
webhook o'rnatadi, `/` manzilida esa «ok» qaytaradigan tekshiruv sahifasi
turadi.

Webhook manzilining maxfiy qismi tokenning sha256 yig'indisidan olinadi va
Telegram har bir so'rovda maxfiy sarlavha yuboradi — begona POST so'rov 401
bilan qaytariladi. Token na manzilda, na logda ko'rinmaydi.

Servis harakatsizlikdan uxlab qoladigan tarifda bo'lsa, birinchi xabardan
keyin uyg'onish bir daqiqagacha cho'zilishi mumkin. Buni yo'qotish uchun
tashqi ping xizmati (masalan cron-job.org) har 10 daqiqada `/` manzilini
so'rab tursa, servis uyg'oq qoladi.

Har ikki holatda ham suhbat tarixi xotirada: qayta deploy qilinganda u
tozalanadi.

## Nima qayerda

| Fayl | Roli |
| --- | --- |
| `main.py` | aiogram handler'lari: buyruqlar, savol → javob oqimi |
| `webhook.py` | Webhook rejimi: maxfiy manzil, health sahifa, aiohttp servisi |
| `claude.py` | Anthropic API bilan ishlash, xatoliklarni odam tiliga o'girish |
| `formatting.py` | Markdown → Telegram HTML, uzun javobni bo'lish |
| `session.py` | Suhbat tarixi va daqiqalik limit |
| `config.py` | Barcha env var'lar |
| `texts.py` | Botning matnlari |

## Testlar

```bash
python -m pytest tests/test_claude_bot.py -q
```

Testlar na Telegram'ga, na Anthropic'ga chiqadi: formatlash, tarix, limit va
handler mantiqi soxta obyektlar bilan tekshiriladi. `aiogram`/`anthropic`
o'rnatilmagan bo'lsa, o'sha testlar avtomatik o'tkazib yuboriladi — CI shu
sababli bu kutubxonalarsiz ham yashil turadi.

## Xavfsizlik eslatmasi

- Kalitlar hech qachon repoga tushmaydi: `.env` `.gitignore` da.
- Bot xabarlarni diskka yozmaydi.
- Ro'yxatni bo'sh qoldirmang: ochiq bot = ochiq hisob.
