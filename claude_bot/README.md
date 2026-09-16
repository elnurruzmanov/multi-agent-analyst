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

Buyruqlar: `/start`, `/new` (suhbatni tozalash), `/pdf`, `/cost`, `/model`,
`/id`, `/help`.

## Xarajatni ko'rish

Har javob oxirida taxminiy narx turadi (`· ~3 sent`), `/cost` esa yig'indini
ko'rsatadi: so'nggi 24 soat va bot yoqilgandan beri.

Hisob **taxminiy** va faqat matn tokenlarini oladi — internet qidiruvining
o'z narxi bunga kirmaydi. Aniq raqam har doim
[platform.claude.com → Usage](https://platform.claude.com) da. Narxlar
`pricing.py` da qo'lda yozilgan, model narxi o'zgarsa o'sha yerni yangilash
kerak.

Sanoq xotirada turadi: qayta deploy qilinganda nolga qaytadi.

Javob oxiridagi qator keraksiz bo'lsa — `CLAUDE_SHOW_COST=0`.

### Nimadan tejaladi

| Usul | Taxminiy tejov | Nimadan voz kechiladi |
| --- | --- | --- |
| Mavzu tugagach `/new` | 30–50% | hech narsadan |
| `CLAUDE_MODEL=claude-sonnet-5` | ~60% | murakkab masalalarda biroz sifat |
| `CLAUDE_TOOLS=off` | 20–40% | bugungi ma'lumot topilmaydi |
| `CLAUDE_EFFORT=low` | 20–30% | chuqur o'ylashni talab qiladigan savollar |
| `CLAUDE_HISTORY_LIMIT=10` | 15–25% | kamroq eslab qoladi |

Birinchi qatori eng kuchlisi va bepul: suhbat tarixi har savolda boshidan
qayta yuboriladi, ya'ni uzun suhbatning 21-savoli birinchisidan bir necha
barobar qimmat turadi.

## Fayl yasash

Claude foydalanuvchiga **Excel, Word, PDF, CSV va matn** fayllarini yasab
bera oladi. Buning uchun unga `create_file` degan qurol berilgan
(`files.py`): model qanday fayl kerakligini va ichida nima bo'lishini
aytadi, faylni esa bot yig'ib, hujjat sifatida yuboradi.

Ya'ni alohida buyruq o'rganish shart emas — «buni excelga sol» deb
yozaverasiz, model o'zi qurolni chaqiradi.

| So'ralganda | Model nima beradi |
| --- | --- |
| Jadval, ro'yxat, hisob-kitob | `rows` (birinchi qator sarlavha) → `.xlsx` yoki `.csv` |
| Matnli hujjat, bayon, xat | `text` (markdown) → `.docx` yoki `.pdf` |

Bitta javobda ko'pi bilan `MAX_FILES` (5) ta fayl yasaladi. Qurol noto'g'ri
ma'lumot olsa xatolik modelga qaytariladi va u boshqacha urinib ko'radi —
javob butunlay yo'qolmaydi.

Butunlay o'chirish: `CLAUDE_MAKE_FILES=0`.

## /pdf

`/pdf` oxirgi javobni PDF fayl qilib yuboradi. Fayl shu yerda, bot ichida
yig'iladi (`reportlab`) — **Claude fayl yarata olmaydi**, u faqat matn
qaytaradi. Shu sababli tizim ko'rsatmasida unga «fayl tayyor» deb aytish
taqiqlangan: modelning o'zi fayl yasay olmagani holda «mana fayl» deyishi
foydalanuvchini aldash bo'lardi.

Shrift: DejaVu topilsa o'sha ishlatiladi (`oʻ`, `gʻ` to'g'ri chiqadi), aks
holda Helvetica'ga tushib, sig'maydigan belgilar yaqin ko'rinishiga
almashtiriladi — PDF chiqmay qolgandan ko'ra shunisi yaxshi.

## Sozlash

**1. Botni yarating.** Telegram'da [@BotFather](https://t.me/BotFather) ga
`/newbot` yozing, nom va username bering — u token beradi.

**2. Anthropic kalitini oling.**
[platform.claude.com/settings/keys](https://platform.claude.com/settings/keys)
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
| `CLAUDE_MAX_FILE_MB` | `10` | Yuborilgan fayl hajmi chegarasi |
| `CLAUDE_SHOW_COST` | `1` | Javob oxirida taxminiy narxni ko'rsatish |
| `CLAUDE_MAKE_FILES` | `1` | Claude fayl yasab bera olsinmi |
| `CLAUDE_RATE_LIMIT` | `10` | Bir foydalanuvchi uchun daqiqasiga savol; `0` — cheklovsiz |
| `CLAUDE_ALLOWED_USER_IDS` | bo'sh | Ruxsat etilganlar; bo'sh — hammaga ochiq |
| `CLAUDE_SYSTEM_PROMPT` | o'zbekcha ko'rsatma | Botning xarakteri |
| `CLAUDE_FALLBACKS` | `1` | Claude javobdan bosh tortsa, zaxira modelga o'tish |
| `CLAUDE_THINKING` | `1` | Adaptive thinking; eski modellarda `0` qiling |
| `CLAUDE_TOOLS` | `web` | Qurollar: `web`, `code` yoki `off` — pastda |
| `CLAUDE_MAX_TOOL_USES` | `5` | Bitta javobda qurol nechta marta ishlatilsin |
| `CLAUDE_WEBHOOK_URL` | bo'sh | Berilsa webhook rejimi; bo'sh bo'lsa polling |
| `PORT` | `10000` | Webhook rejimida tinglanadigan port (hosting o'zi beradi) |

Tezroq va arzonroq javob kerak bo'lsa: `CLAUDE_EFFORT=low`, yoki
`CLAUDE_MODEL=claude-sonnet-5`. Murakkab masalalar uchun `CLAUDE_EFFORT=xhigh`.

`CLAUDE_MODEL` ni almashtirsangiz, model adaptive thinking'ni qo'llashini
tekshiring (`claude-opus-5`, `claude-sonnet-5`, `claude-opus-4-8` — qo'llaydi).
Eskiroq `claude-haiku-4-5` uni qabul qilmaydi, u bilan `CLAUDE_THINKING=0`
qo'shing.

## Rasm va fayl

Botga rasm yoki fayl yuborsangiz, izohiga yozgan savolingiz bilan birga
Claude'ga boradi. Izoh bo'lmasa bot o'zi «bu nima?» deb so'raydi.

| Nima yuborilsa | Qanday o'qiladi |
| --- | --- |
| Rasm (JPG, PNG, GIF, WebP) | Claude to'g'ridan-to'g'ri ko'radi |
| PDF | Claude to'g'ridan-to'g'ri o'qiydi |
| Word (`.docx`) | matni ajratib olinadi (`python-docx`) |
| Excel (`.xlsx`) | varaqlar matnga aylantiriladi (`openpyxl`) |
| Matnli fayl (`.txt`, `.csv`, `.json`, `.md`) | o'zi matn |
| Qolgani (video, ovoz, arxiv) | o'qilmaydi, bot buni aytadi |

Ikkita chegara bor va ikkalasi ham hisobni himoya qiladi:

- **Fayl hajmi** — `CLAUDE_MAX_FILE_MB` (default 10 MB). Telegram baribir
  botlarga 20 MB dan kattasini bermaydi.
- **Fayl kontekstda abadiy qolmaydi.** Yuborilgan rasm/hujjat haqida bir necha
  savol berish mumkin, lekin ikki holatda u tarixda `[«nom» yuborildi]`
  yozuviga almashadi: yangi fayl yuborilganda, yoki suhbat undan
  `MEDIA_KEEP` (6) ta xabar nariga o'tganda. Aks holda hujjat har bir savolda
  qaytadan yuborilib, hisobni bo'shatib qo'yardi.

Skanerdan o'tgan (rasmga aylangan) PDF ichida matn bo'lmaydi — bunday hujjatni
rasm sifatida yuborgan ma'qul, o'shanda Claude uni ko'rib o'qiydi.

## Qurollar

Claude javob berishdan oldin qurol ishlatishi mumkin — qidiradi, sahifani
o'qiydi, hisoblaydi. Qurollar Anthropic serverida ishlaydi: bizning kodimiz
ularni bajarmaydi, faqat ruxsat beradi.

| `CLAUDE_TOOLS` | Nima beriladi | Qachon |
| --- | --- | --- |
| `web` (default) | qidirish + sahifani o'qish | bugungi ma'lumot kerak bo'lganda |
| `code` | kod bajarish + oddiy qidiruv | hisob, jadval, grafik kerak bo'lganda |
| `off` | hech narsa | eng arzon va eng tez |

`web` va `code` birga berilmaydi: yangi qidiruv quroli natijalarni saralash
uchun ichida kod bajarish muhitini ishlatadi, yoniga ikkinchisini qo'ysak
model qaysi birini tanlashni chalkashtiradi.

Qurol ishlatilgan javob qimmatroq turadi — model bir necha marta chaqiriladi
va qidiruvning o'z narxi bor. `CLAUDE_MAX_TOOL_USES` bitta javobdagi
chaqiruvlar sonini cheklaydi; butunlay kerak bo'lmasa `CLAUDE_TOOLS=off`.

Qurol ishga tushganda bot xabarni «🔎 Internetdan qidiryapman…» ga
o'zgartiradi — qidiruv paytida matn oqmaydi, ekran jim qolmasin uchun.

Qurollar Opus 5, Opus 4.6+ va Sonnet 5 / 4.6 da ishlaydi. Eskiroq modelga
o'tsangiz `CLAUDE_TOOLS=off` qo'ying.

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
| `tools.py` | Qaysi server qurollari berilishi va nega birga emasligi |
| `media.py` | Rasm va fayllarni Claude bloklariga aylantirish |
| `pdf.py` | Javobni PDF fayl qilish |
| `pricing.py` | Token narxlari va taxminiy hisob |
| `files.py` | `create_file` quroli: Excel, Word, PDF, CSV yasash |
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
