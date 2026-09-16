"""Suhbat tarixi va oddiy tezlik chegarasi.

Tarix xotirada turadi: bot qayta ishga tushsa, suhbat noldan boshlanadi. Bu
ataylab shunday — Render'ning bepul tarifida disk vaqtinchalik, va yozishmalarni
diskda saqlamaslik eng xavfsiz standart. Doimiy tarix kerak bo'lsa, `ChatHistory`
ni SQLite bilan almashtirish kifoya: interfeysi shu yerda to'liq.

Modul hech qanday tashqi kutubxonaga bog'liq emas.
"""
from __future__ import annotations

import time

# Yuborilgan rasm/fayl kontekstda nechta xabar davomida qolsin.
MEDIA_KEEP = 6


def _collapse(item: dict) -> None:
    """Media xabarni o'z belgisiga (qisqa matnga) almashtiradi."""
    if item.get("marker"):
        item["content"] = item["marker"]
        item["marker"] = None


class ChatHistory:
    """Har bir chat uchun oxirgi N ta xabar."""

    def __init__(self, limit: int = 20) -> None:
        # limit — xabarlar soni (savol ham, javob ham). Juft son bo'lgani ma'qul.
        self.limit = max(2, limit)
        self._chats: dict[int, list[dict[str, str]]] = {}

    def get(self, chat_id: int) -> list[dict]:
        """Claude'ga yuboriladigan `messages` ro'yxati."""
        return [
            {"role": item["role"], "content": item["content"]}
            for item in self._chats.get(chat_id, [])
        ]

    def add(self, chat_id: int, role: str, content, marker: str | None = None) -> None:
        """Xabarni tarixga qo'shadi.

        `marker` — rasm yoki fayl yuborilganda beriladigan qisqa matn. Fayl
        kontekstda abadiy qololmaydi: har savolda u qaytadan yuborilsa, pul
        behuda ketadi. Shuning uchun ikkita qoida bor:

        * yangi fayl kelsa, avvalgisi darhol belgisiga almashadi;
        * eski fayl `MEDIA_KEEP` ta xabardan nariga o'tsa ham almashadi.

        Ya'ni yuborilgan rasm haqida bir necha savol berish mumkin, lekin u
        suhbat oxirigacha ergashib yurmaydi.
        """
        messages = self._chats.setdefault(chat_id, [])
        if marker is not None:
            for item in messages:
                _collapse(item)
        messages.append({"role": role, "content": content, "marker": marker})
        self._trim(messages)
        for item in messages[:-MEDIA_KEEP]:
            _collapse(item)

    def clear(self, chat_id: int) -> None:
        self._chats.pop(chat_id, None)

    def _trim(self, messages: list[dict[str, str]]) -> None:
        del messages[:max(0, len(messages) - self.limit)]
        # API birinchi xabar `user` bo'lishini talab qiladi — kesishdan keyin
        # boshida javob qolib ketgan bo'lsa, uni tashlaymiz.
        while messages and messages[0]["role"] != "user":
            messages.pop(0)


class UsageTracker:
    """Har bir chat qancha sarflaganini sanab boradi.

    Xotirada turadi — qayta deploy qilinganda nolga qaytadi. Aniq va doimiy
    hisob Anthropic konsolida; bu esa «hozir qancha ketdi?» degan savolga
    darhol javob berish uchun.
    """

    def __init__(self, keep: int = 500) -> None:
        self.keep = keep
        self._calls: dict[int, list[tuple[float, float, int, int]]] = {}

    def record(
        self,
        chat_id: int,
        usd: float,
        input_tokens: int,
        output_tokens: int,
        now: float | None = None,
    ) -> None:
        moment = time.time() if now is None else now
        calls = self._calls.setdefault(chat_id, [])
        calls.append((moment, usd, input_tokens, output_tokens))
        del calls[:max(0, len(calls) - self.keep)]

    def summary(self, chat_id: int, hours: float = 24.0, now: float | None = None) -> dict:
        moment = time.time() if now is None else now
        calls = self._calls.get(chat_id, [])
        recent = [call for call in calls if moment - call[0] <= hours * 3600]
        return {
            "calls": len(calls),
            "usd": sum(call[1] for call in calls),
            "input_tokens": sum(call[2] for call in calls),
            "output_tokens": sum(call[3] for call in calls),
            "recent_calls": len(recent),
            "recent_usd": sum(call[1] for call in recent),
        }


class RateLimiter:
    """Bir foydalanuvchi uchun daqiqasiga nechta so'rov — hisobni himoya qiladi."""

    def __init__(self, per_minute: int = 10, window: float = 60.0) -> None:
        self.per_minute = per_minute
        self.window = window
        self._hits: dict[int, list[float]] = {}

    def allow(self, user_id: int, now: float | None = None) -> bool:
        if self.per_minute <= 0:  # 0 yoki manfiy — cheklov yo'q
            return True
        moment = time.monotonic() if now is None else now
        hits = [stamp for stamp in self._hits.get(user_id, []) if moment - stamp < self.window]
        if len(hits) >= self.per_minute:
            self._hits[user_id] = hits
            return False
        hits.append(moment)
        self._hits[user_id] = hits
        return True
