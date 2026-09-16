# Botni telefondan ishga tushirish

Telegram'ga yozasiz — Claude javob beradi. Quyidagi qadamlarni tartib bilan
bajarasiz; **kompyuter kerak emas**, hammasi telefon brauzerida bo'ladi.

Taxminan 40 daqiqa vaqt va bitta bank kartasi kerak bo'ladi.

---

## Avvalo: «pullik» degani nima, «tekin» degani nima

Bu yerda butunlay boshqa ikki narsa uchun pul to'lanadi. Ko'pchilik shu joyda
adashadi, shuning uchun boshidan aniq bo'lsin:

**1. Claude API — botning miyasi. Har doim pullik.**
Bepul varianti umuman yo'q. Har bir savol-javob hisobingizdan bir necha sent
yechadi. Buning evaziga javoblar siz Claude bilan to'g'ridan-to'g'ri
gaplashgandagidek sifatli bo'ladi — hech qanday «arzonlashtirilgan» versiya
emas.

> ⚠️ **claude.ai dagi $20 lik Pro obuna bu yerda ishlamaydi.** Anthropic'da
> ikkita alohida hamyon bor: Pro obunasi saytdagi va ilovadagi suhbat uchun,
> API krediti esa dastur (bizning bot) uchun. Birini ikkinchisiga o'tkazish
> imkoni yo'q — bot uchun alohida kredit sotib olinadi.

**2. Hosting — bot yashaydigan joy. Tanlov shu yerda.**
Bepul tarifda bot 15 daqiqa jimlikdan keyin uxlab qoladi va birinchi xabar
~1 daqiqa kechikadi. $7/oy da umuman uxlamaydi — «qotmaydigan» bot shu.

| | Bepul hosting | $7/oy |
| --- | --- | --- |
| Javob sifati | bir xil | bir xil |
| 15 daq. jimlikdan keyin | uxlaydi, 1-xabar ~1 daq. kechikadi | uxlamaydi |
| Ishda tez javob | yo'q | ha |

**Maslahat:** bepulda boshlang — ishlayotganiga ishonch hosil qiling, keyin bir
tugma bilan $7 lik tarifga o'tasiz. Kod ikkalasida ham bir xil, hech narsani
qaytadan qilish shart emas.

---

## 01 — Telegram'da bot yarating

*Telegram ilovasida, 3 daqiqa*

**1.1. @BotFather'ni oching.**
Telegram qidiruviga `@BotFather` deb yozing. Ko'k tasdiq belgisi ✓ bor
bo'lganini tanlang — qolganlari soxta. **Start** bosing.

**1.2. Yangi bot so'rang.**
`/newbot` deb yuboring. Keyin u ketma-ket ikki narsa so'raydi:

- **Nom** — istalgani, masalan `Mening yordamchim`
- **Username** — `bot` bilan tugashi shart va butun Telegram bo'ylab
  takrorlanmasligi kerak, masalan `elnur_claude_2026_bot`. «Sorry, this
  username is already taken» chiqsa, oxiriga raqam qo'shing.

**1.3. Tokenni saqlang.**
BotFather `8123456789:AAHdq...` ko'rinishidagi uzun qator yuboradi. Uni bosib
nusxalang va o'zingizga — «Saved Messages» ga yuboring.

> 🔒 Bu token — botingizning paroli. Hech kimga yubormang. Tasodifan oshkor
> bo'lsa, BotFather'da `/revoke` bilan yangisini olasiz.

---

## 02 — Claude kalitini oling

*platform.claude.com, 10 daqiqa*

**2.1. Hisob oching.**
Brauzerda `platform.claude.com` ni oching va ro'yxatdan o'ting
(`console.anthropic.com` ham shu yerga olib keladi). Bu **claude.ai dan
alohida xizmat**: u yerdagi obunangiz bu yerda ishlamaydi, chunki bot API
orqali ulanadi.

«How will you use the Claude API?» degan savol chiqsa — **Individual** ni
tanlang.

**2.2. Balansni to'ldiring.**
**Billing** bo'limiga kiring, kartani ulang va hisobni to'ldiring. Sinash
uchun **$5** yetarli — bu taxminan 200–500 ta savol-javob.

Balanssiz kalit ishlamaydi: bot «❌ Anthropic hisobida mablag' yetmayapti» deb
javob beradi.

**2.3. API kalit yarating.**
**Settings → API keys → Create Key**. Kalit `sk-ant-...` bilan boshlanadi va
**faqat bir marta** ko'rsatiladi — darhol nusxalab saqlang.

---

## 03 — Botni hostingga qo'ying

*render.com, 15 daqiqa — eng uzun bosqich*

**3.1. Render'ga GitHub bilan kiring.**
`render.com` → **Get Started** → **GitHub** bilan kirish. Render repolaringizni
ko'rish uchun ruxsat so'raydi — bering.

**3.2. Yangi Web Service yarating.**
Dashboard'da **New +** → **Web Service** → ro'yxatdan `multi-agent-analyst`
repo'sini toping → **Connect**.

> «Web Service» tanlanadi, «Background Worker» emas — bot webhook rejimida
> aynan shunday ishlaydi va bepul tarif ham shu turga beriladi.

**3.3. Maydonlarni to'ldiring** (qolganiga tegmang):

| Maydon | Qiymat |
| --- | --- |
| Name | `claude-bot` |
| Branch | `claude/telegram-bot-claude-integration-2i0bo6` |
| Language | `Python 3` |
| Build Command | `pip install -r requirements-claude-bot.txt` |
| Start Command | `python -m claude_bot.main` |
| Instance Type | `Free` |

**3.4. Uchta maxfiy qiymatni kiriting.**
Xuddi shu sahifadagi **Environment Variables** bo'limida **Add Environment
Variable** bosib, uchtasini qo'shing:

| Nomi | Qiymati |
| --- | --- |
| `CLAUDE_BOT_TOKEN` | BotFather bergan token |
| `ANTHROPIC_API_KEY` | `sk-ant-...` kaliti |
| `PYTHON_VERSION` | `3.12.7` |

**3.5. Deploy qiling va kuting.**
**Create Web Service** bosing. Birinchi build 3–6 daqiqa oladi. Logs oynasida
`Bot ishga tushdi` qatorini ko'rsangiz — hammasi joyida.

**3.6. Webhook o'rnatilganini tekshiring.**
Odatda bu qadam kerak bo'lmaydi: Render web servisga o'z manzilini
avtomatik beradi va bot uni o'zi oladi. Logs'da shunga o'xshash qator
bo'lsa — hammasi joyida:

```
Webhook rejimi: https://claude-bot-xxxx.onrender.com/telegram/… , port 10000
```

Uning o'rniga `Polling rejimi` deb yozilgan bo'lsa, manzilni qo'lda berasiz.
Sahifa tepasidagi manzilni nusxalab, **Environment → Add Environment
Variable**:

| Nomi | Qiymati |
| --- | --- |
| `CLAUDE_WEBHOOK_URL` | `https://claude-bot-xxxx.onrender.com` |

**Save changes** — servis o'zi qayta deploy bo'ladi.

> Manzil `https://` bilan boshlanib, oxirida `/` **bo'lmasligi** kerak.

---

## 04 — Sinab ko'ring va eshikni yoping

*Telegram + Render, 5 daqiqa*

**4.1. Botga yozing.**
Telegram'da o'z botingizni oching → **Start**. Salomlashish xabari kelsa,
bog'lanish ishlayapti. Endi oddiy savol yozing. Birinchi javob 30–60 soniya
kechikishi mumkin — bepul servis uyquda edi.

**4.2. O'z ID raqamingizni oling.**
Botga `/id` yozing — u sizga raqam qaytaradi, nusxalang.

**4.3. Botni faqat o'zingizga qoldiring.**
Render → **Environment → Add Environment Variable**:

| Nomi | Qiymati |
| --- | --- |
| `CLAUDE_ALLOWED_USER_IDS` | `/id` bergan raqam |

> **Bu qadamni o'tkazib yubormang.** Botning username'ini bilgan istalgan odam
> unga yozib, sizning pulingizga savol bera oladi. Hamkasblarga ham kerak
> bo'lsa, ID larni vergul bilan yozing: `111,222,333`.

**4.4. Tekshiring.**
Qayta deploy tugagach botga yana yozing — javob kelishi kerak. Boshqa akkaunt
yozsa, «Bu bot yopiq rejimda ishlayapti» degan javob olishi kerak.

---

## 05 — Qotmaydigan qilib qo'ying

*Ixtiyoriy, 1 daqiqa — $7/oy*

**5.1. Starter tarifga o'ting.**
Render → servis → **Settings → Instance Type → Starter**. Servis endi hech
qachon uxlamaydi: har bir xabarga darhol javob keladi.

> Pul sarflamay turishning yo'li ham bor: `cron-job.org` kabi bepul xizmat har
> 10 daqiqada servis manzilini so'rab tursa, u uyg'oq qoladi. Lekin bu
> ishonchsizroq — muhim ish uchun $7 ni to'lagan ma'qul.

**5.2. Xarajatga ko'z-quloq bo'ling.**
Birinchi hafta `platform.claude.com → Usage` ni kuzating. Ko'p ketayotgan
bo'lsa, Render'da `CLAUDE_MODEL` ni `claude-sonnet-5` ga o'zgartirasiz.

---

## Qancha turadi

Taxminiy, kuniga 30 ta savol hisobida:

| Model | 1 savol-javob | Oyiga (~900 ta) | Qanday |
| --- | --- | --- | --- |
| `claude-opus-5` | ~2–4 sent | ~$20–35 | eng kuchli — default |
| `claude-sonnet-5` | ~1 sent | ~$9 | kundalik ish uchun |
| `claude-haiku-4-5` | ~0.5 sent | ~$4 | eng arzon, soddaroq |

Bu raqamlar **taxminiy**: aniq summa savol uzunligiga va suhbat tarixiga
bog'liq. Uzun suhbat har safar boshidan yuboriladi, shuning uchun mavzu
tugagach `/new` yozib tarixni tozalash — eng oson tejash usuli.

Hosting alohida hisoblanadi: bepul $0, Starter $7/oy.

---

## Nimadir ishlamasa

**Bot umuman javob bermayapti.**
Render → servis → **Logs** ni oching. Oxirgi qatorlarda `Bot ishga tushdi`
bormi? Yo'q bo'lsa — build yiqilgan. Bor bo'lsa, lekin javob yo'q —
`CLAUDE_WEBHOOK_URL` noto'g'ri bo'lishi mumkin.

**«❌ ANTHROPIC_API_KEY qabul qilinmadi».**
Kalit noto'g'ri nusxalangan (boshida yoki oxirida bo'sh joy qolgan) yoki
o'chirilgan. Yangi kalit yarating va Render'dagi qiymatni almashtiring.

**«❌ Anthropic hisobida mablag' yetmayapti».**
Balans tugagan. **Billing** ga kirib to'ldiring — bir necha daqiqada ishlay
boshlaydi.

**Birinchi xabar juda kech keladi.**
Bepul tarif 15 daqiqa jimlikdan keyin uxlaydi, uyg'onish ~1 daqiqa. Bu
nosozlik emas. Yoqmasa — 05-bosqich.

**Deploy «failed» bo'ldi.**
**Logs** dagi qizil xatolikni to'liq nusxalang — odatda Build Command yoki
branch nomi xato yozilgan bo'ladi.

---

## Kompyuter olganingizda

Hech narsani boshidan qilish shart emas. Kod GitHub'da, sozlamalar Render'da
turadi — kompyuterda faqat nusxa olasiz:

```bash
git clone https://github.com/elnurruzmanov/multi-agent-analyst.git
cd multi-agent-analyst
git checkout claude/telegram-bot-claude-integration-2i0bo6
pip install -r requirements-claude-bot.txt
python -m claude_bot.main
```

`.env` faylini yaratib, `CLAUDE_BOT_TOKEN` va `ANTHROPIC_API_KEY` ni yozasiz
(namuna: repo ildizidagi `.env.example`).

> ⚠️ Bitta shart: **bitta tokenni ikki joyda bir vaqtda ishlatmang**.
> Kompyuterda sinamoqchi bo'lsangiz, Render'dagi servisni vaqtincha to'xtating
> (Settings → Suspend) yoki BotFather'dan alohida «test bot» oling.

---

## Botning buyruqlari

| Buyruq | Nima qiladi |
| --- | --- |
| `/start` | boshlash va yordam |
| `/new` | suhbatni tozalash (tejash uchun ham foydali) |
| `/model` | qaysi model ishlayapti |
| `/id` | Telegram ID ingizni ko'rsatadi |
| `/help` | yordam |

Texnik tafsilotlar va barcha sozlamalar: [`README.md`](README.md).
