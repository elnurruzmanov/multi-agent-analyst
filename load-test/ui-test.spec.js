// UI (funksional) test — murojaat.byurokratiyasiz2030.uz
// Vosita: Playwright (https://playwright.dev)
//
// O'rnatish va ishga tushirish (kompyuteringizda):
//   npm init -y
//   npm install -D @playwright/test
//   npx playwright install chromium
//   npx playwright test ui-test.spec.js --headed
//   npx playwright show-report      // natijani chiroyli HTML hisobot bilan ko'rish
//
// Natija: har bir "test" o'tdi (yashil) yoki o'tmadi (qizil) bo'lib chiqadi,
// va screenshots/ papkasida skrinshotlar saqlanadi. Bu REAL natija.

const { test, expect } = require('@playwright/test');

const BASE_URL = process.env.BASE_URL || 'http://murojaat.byurokratiyasiz2030.uz/';

test.describe('Sayt UI testlari', () => {

  test('1. Sahifa muvaffaqiyatli ochiladi (HTTP 200)', async ({ page }) => {
    const res = await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
    expect(res.status(), 'HTTP status 200 bo\'lishi kerak').toBeLessThan(400);
  });

  test('2. Sahifa sarlavhasi (title) bo\'sh emas', async ({ page }) => {
    await page.goto(BASE_URL);
    const title = await page.title();
    console.log('Sahifa sarlavhasi:', title);
    expect(title.trim().length, 'title bo\'sh bo\'lmasligi kerak').toBeGreaterThan(0);
  });

  test('3. Asosiy kontent ko\'rinadi (body matni mavjud)', async ({ page }) => {
    await page.goto(BASE_URL);
    const bodyText = (await page.locator('body').innerText()).trim();
    console.log('Body matn uzunligi:', bodyText.length, 'belgi');
    expect(bodyText.length, 'sahifada matn bo\'lishi kerak').toBeGreaterThan(20);
  });

  test('4. Havolalar (linklar) mavjud va soni hisoblanadi', async ({ page }) => {
    await page.goto(BASE_URL);
    const linkCount = await page.locator('a').count();
    console.log('Havolalar soni:', linkCount);
    expect(linkCount, 'kamida bitta havola bo\'lishi kerak').toBeGreaterThan(0);
  });

  test('5. Murojaat formasi / kiritish maydonlari bor-yo\'qligi', async ({ page }) => {
    await page.goto(BASE_URL);
    const inputs = await page.locator('input, textarea, select').count();
    const forms = await page.locator('form').count();
    console.log('Forma soni:', forms, '| Kiritish maydonlari:', inputs);
    // Bu tekshiruv faqat ma'lumot uchun (fail qilmaydi) — natijani hisobotga yozing
  });

  test('6. Konsolda JavaScript xatolari yo\'q', async ({ page }) => {
    const errors = [];
    page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
    page.on('pageerror', err => errors.push(err.message));
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    if (errors.length) console.log('Konsol xatolari:', errors);
    expect(errors, 'JS xatolari bo\'lmasligi kerak').toHaveLength(0);
  });

  test('7. Desktop skrinshot', async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await page.screenshot({ path: 'screenshots/desktop.png', fullPage: true });
  });

  test('8. Mobil ko\'rinish (responsive) skrinshot', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 }); // iPhone o'lchami
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await page.screenshot({ path: 'screenshots/mobile.png', fullPage: true });
    // Gorizontal skroll (mobilda yomon belgi) bor-yo'qligini tekshirish
    const hasHScroll = await page.evaluate(() =>
      document.documentElement.scrollWidth > document.documentElement.clientWidth + 2);
    console.log('Mobilda gorizontal skroll:', hasHScroll ? 'BOR (kamchilik)' : 'yo\'q (yaxshi)');
  });

  test('9. HTTPS holati (xavfsizlik)', async ({ page }) => {
    const res = await page.goto(BASE_URL);
    const finalUrl = page.url();
    console.log('Yakuniy URL:', finalUrl);
    const isHttps = finalUrl.startsWith('https://');
    console.log('HTTPS:', isHttps ? 'yoqilgan' : 'YO\'Q — kamchilik (davlat sayti uchun muhim)');
    // Ma'lumot uchun — natijani hisobotga qo'shing
  });

});
