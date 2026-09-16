"""Claude javobini Telegram xabariga aylantirish.

Ikki ish qilinadi:

1. **Bo'lish.** Telegram bitta xabarga 4096 belgidan ko'pini qabul qilmaydi,
   Claude esa bemalol uzunroq yozadi. Matn satrlar bo'yicha bo'linadi va kod
   bloki ikkiga bo'linib qolsa, birinchi bo'lakda yopilib, ikkinchisida qayta
   ochiladi — aks holda HTML buzilib, Telegram xabarni rad etadi.
2. **Markdown → HTML.** Telegram markdown'ni to'liq tushunmaydi, HTML'ni esa
   tushunadi. Avval hamma narsa escape qilinadi, keyin kerakli teglar qo'yiladi:
   escape qilinmagan `<` bitta xabarni butunlay yo'q qiladi.

Bu modul aiogram va anthropic'ga bog'liq emas — shuning uchun uni kutubxonalarsiz
ham test qilish mumkin (`tests/test_claude_bot.py`).
"""
from __future__ import annotations

import html
import re

# Telegram cheklovi 4096. HTML teglari matnni uzaytiradi, shuning uchun xom
# matnni ancha pastroq chegarada bo'lamiz.
TELEGRAM_LIMIT = 4096
CHUNK_LIMIT = 3500

_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_LINK = re.compile(r"\[([^\]\n]+)\]\((https?://[^\s)]+)\)")
_HEADING = re.compile(r"(?m)^\s{0,3}#{1,6}\s+(.+?)\s*$")
_BOLD = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", re.S)
_BOLD_ALT = re.compile(r"__(?=\S)(.+?)(?<=\S)__", re.S)
_ITALIC = re.compile(r"(?<![\w*])\*(?=\S)([^*\n]+?)(?<=\S)\*(?![\w*])")
_BULLET = re.compile(r"(?m)^(\s*)[*+-] (?=\S)")
_PLACEHOLDER = re.compile("\x00(\\d+)\x00")


def to_html(text: str) -> str:
    """Markdown'ga o'xshash matnni Telegram qabul qiladigan HTML'ga aylantiradi."""
    parts = text.split("```")
    rendered = []
    for index, part in enumerate(parts):
        # Toq indeks — ``` juftligi orasidagi kod bloki.
        rendered.append(_code_block(part) if index % 2 else _inline(part))
    return "".join(rendered).strip()


def _code_block(part: str) -> str:
    body = part
    first, separator, rest = part.partition("\n")
    # ```python kabi til belgisi — uni ko'rsatmaymiz.
    if separator and first.strip() and " " not in first.strip():
        body = rest
    return f"<pre><code>{html.escape(body.strip(chr(10)))}</code></pre>"


def _inline(part: str) -> str:
    # Inline kodni oldin olib qo'yamiz: uning ichidagi *yulduzcha* matn emas.
    stashed: list[str] = []

    def stash(match: re.Match[str]) -> str:
        stashed.append(html.escape(match.group(1)))
        return f"\x00{len(stashed) - 1}\x00"

    text = _INLINE_CODE.sub(stash, part)
    text = html.escape(text)
    text = _LINK.sub(r'<a href="\2">\1</a>', text)
    text = _HEADING.sub(r"<b>\1</b>", text)
    text = _BOLD.sub(r"<b>\1</b>", text)
    text = _BOLD_ALT.sub(r"<b>\1</b>", text)
    text = _ITALIC.sub(r"<i>\1</i>", text)
    text = _BULLET.sub(r"\1• ", text)
    return _PLACEHOLDER.sub(lambda m: f"<code>{stashed[int(m.group(1))]}</code>", text)


def split_markdown(text: str, limit: int = CHUNK_LIMIT) -> list[str]:
    """Xom matnni chegaradan oshmaydigan bo'laklarga ajratadi.

    Ochiq qolgan ``` bloki bo'lak oxirida yopiladi va keyingisida qayta ochiladi.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    length = 0
    fence: str | None = None  # None — blokdan tashqarida, aks holda ochiq til

    def flush() -> None:
        nonlocal current, length
        if not current:
            return
        body = "\n".join(current)
        if fence is not None:
            body += "\n```"
        if body.replace("`", "").strip():
            chunks.append(body)
        current = []
        length = 0
        if fence is not None:
            opener = "```" + fence
            current.append(opener)
            length = len(opener) + 1

    for line in text.split("\n"):
        for piece in _hard_wrap(line, limit):
            if current and length + len(piece) + 1 > limit:
                flush()
            current.append(piece)
            length += len(piece) + 1
            stripped = piece.strip()
            if stripped.startswith("```"):
                fence = stripped[3:].strip() if fence is None else None

    flush()
    return chunks


def _hard_wrap(line: str, limit: int) -> list[str]:
    """Bitta satr chegaradan uzun bo'lsa (masalan uzun URL) — majburan kesamiz."""
    if len(line) <= limit:
        return [line]
    return [line[start:start + limit] for start in range(0, len(line), limit)]


def render(text: str, limit: int = CHUNK_LIMIT) -> list[str]:
    """Javobni yuborishga tayyor HTML bo'laklar ro'yxatiga aylantiradi."""
    return [to_html(chunk) for chunk in split_markdown(text, limit)]
