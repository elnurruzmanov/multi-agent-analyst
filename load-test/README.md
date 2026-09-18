# Sayt tahlili va test materiallari

Sayt: `https://murojaat.byurokratiyasiz2030.uz/`

Ushbu papkada saytni tahlil qilish va test qilish uchun tayyorlangan hujjat va skriptlar bor.

## Fayllar

| Fayl | Tavsif | Holat |
|------|--------|-------|
| `Tahlil-natijalari.docx` | PageSpeed (web.dev) **real natijalari** — qisqa | ✅ Tayyor |
| `Sayt-tahlili-hisoboti.docx` | To'liq tahlil hisoboti, tavsiyalar bilan | ✅ Tayyor |
| `natijalar.html` | Natijalarni brauzerda ko'rish (ochib qo'ying) | ✅ Tayyor |
| `Stress-test-rejasi.docx` | Yuklama (stress) test rejasi | ✅ Reja tayyor |
| `loadtest.js` | k6 yuklama test skripti | ✅ Tayyor (ruxsat kutmoqda) |
| `ui-test.spec.js` | Playwright UI test skripti | ✅ Tayyor |
| `UAT-tekshiruv-royxati.docx` | UAT tekshiruv ro'yxati (qo'lda to'ldiriladi) | ⏳ Bajarilishi kerak |
| `Telegram-matni.txt` | Direktorga yuborish uchun tayyor matn | ✅ Tayyor |

## PageSpeed natijalari (qisqacha, real)

- **Tezlik (Performance): 61/100** — o'rtacha (LCP 16.7s, sahifa ~3.2 MB og'ir)
- **Accessibility: 95/100** ✅
- **Best Practices: 100/100** ✅
- **SEO: 83/100** — meta-tavsif yo'q, robots.txt'da 21 xato

## Muhim eslatma

- **Front-end tahlil (PageSpeed)** — bajarildi, real natija bor.
- **To'liq stress test (400–500 foydalanuvchi)** — HALI o'tkazilmadi. Reja va skript tayyor, lekin
  jonli saytga ishga tushirish uchun: (1) rasmiy ruxsat, (2) test muhiti/vaqti, (3) server monitoringi kerak.
- **UAT** — qo'lda bosib bajariladi (`UAT-tekshiruv-royxati.docx` bo'yicha).
