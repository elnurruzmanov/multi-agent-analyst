// k6 load test — murojaat.byurokratiyasiz2030.uz
// Ishga tushirish:  k6 run loadtest.js
// O'zgartiruvchi bilan:  k6 run -e BASE_URL=http://murojaat.byurokratiyasiz2030.uz loadtest.js
//
// DIQQAT: Faqat RUXSAT berilgan (o'zingiz boshqaradigan) saytga ishlating.
// Avval smoke bosqichdan o'ting (10 VU), server chidasa keyingi bosqichlarga o'ting.

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://murojaat.byurokratiyasiz2030.uz';

const errorRate = new Rate('errors');
const pageDuration = new Trend('page_duration', true);

export const options = {
  // Bosqichma-bosqich yuklama: warm-up -> ramp -> 500 da ushlab turish -> pasaytirish
  stages: [
    { duration: '1m', target: 20 },   // 1) smoke / isinish
    { duration: '2m', target: 100 },  // 2) o'rtacha
    { duration: '2m', target: 300 },  // 3) yuqori
    { duration: '3m', target: 500 },  // 4) maqsad: 500 concurrent
    { duration: '3m', target: 500 },  // 5) 500 da ushlab turish (barqarorlik)
    { duration: '2m', target: 0 },    // 6) yumshoq pasaytirish
  ],

  // Xavfsizlik chegaralari: buzilsa test "failed" bo'ladi (server yiqilayotgani signali)
  thresholds: {
    http_req_failed: ['rate<0.05'],      // xatolik < 5%
    http_req_duration: ['p(95)<2000'],   // 95% so'rov < 2s
    errors: ['rate<0.05'],
  },
};

export default function () {
  const res = http.get(BASE_URL, {
    headers: { 'User-Agent': 'k6-loadtest (authorized)' },
    tags: { name: 'homepage' },
  });

  const ok = check(res, {
    'status 200': (r) => r.status === 200,
    'javob < 2s': (r) => r.timings.duration < 2000,
  });

  errorRate.add(!ok);
  pageDuration.add(res.timings.duration);

  // "Think time" — real foydalanuvchi darhol qayta bosmaydi (1–3s)
  sleep(Math.random() * 2 + 1);
}
