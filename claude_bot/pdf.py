"""Javobni PDF fayl qilib berish.

Claude'ning o'zi fayl yarata olmaydi — u faqat matn qaytaradi. PDF shu
yerda, bot ichida yig'iladi va Telegram'ga hujjat sifatida yuboriladi.

Shrift: imkoni bo'lsa DejaVu (o'zbekcha `oʻ`, `gʻ` va boshqa belgilarni
to'g'ri chizadi). Topilmasa Helvetica'ga tushamiz va sig'maydigan belgilarni
almashtiramiz — PDF chiqmay qolgandan ko'ra, bitta belgi soddalashgani yaxshi.
"""
from __future__ import annotations

import html as html_escape
import io
import os
import re
import unicodedata

FONT_PATHS = (
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
    ("/usr/share/fonts/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
     "/usr/share/fonts/dejavu/DejaVuSansMono.ttf"),
)

# Helvetica'ga tushganda almashtiriladigan belgilar.
FALLBACK_MAP = {
    "ʻ": "'", "ʼ": "'", "‘": "'", "’": "'",
    "“": '"', "”": '"', "–": "-", "—": "-",
    "•": "-", "…": "...", " ": " ",
}

_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*)$")
_BULLET = re.compile(r"^\s*[-*•]\s+(.*)$")
_NUMBERED = re.compile(r"^\s*(\d+)[.)]\s+(.*)$")
_BOLD = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", re.S)
_ITALIC = re.compile(r"(?<![\w*])\*(?=\S)([^*\n]+?)(?<=\S)\*(?![\w*])")
_CODE = re.compile(r"`([^`\n]+)`")


def _fonts() -> tuple[str, str, str, bool]:
    """(oddiy, qalin, monospace, unicode_qo'llab-quvvatlanadimi)."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    for regular, bold, mono in FONT_PATHS:
        if not (os.path.exists(regular) and os.path.exists(bold)):
            continue
        try:
            if "BotSans" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("BotSans", regular))
                pdfmetrics.registerFont(TTFont("BotSans-Bold", bold))
                pdfmetrics.registerFont(
                    TTFont("BotMono", mono if os.path.exists(mono) else regular)
                )
            return "BotSans", "BotSans-Bold", "BotMono", True
        except Exception:  # shrift buzuq bo'lsa ham PDF chiqsin
            break
    return "Helvetica", "Helvetica-Bold", "Courier", False


def _simplify(text: str) -> str:
    """Helvetica chiza olmaydigan belgilarni yaqin ko'rinishiga almashtiradi."""
    for source, target in FALLBACK_MAP.items():
        text = text.replace(source, target)
    text = unicodedata.normalize("NFKD", text)
    return text.encode("latin-1", "replace").decode("latin-1")


def _inline(line: str, mono: str = "Courier") -> str:
    """Bir satrni reportlab tushunadigan mini-HTML ga o'giradi."""
    text = html_escape.escape(line)
    text = _CODE.sub(rf'<font face="{mono}">\1</font>', text)
    text = _BOLD.sub(r"<b>\1</b>", text)
    text = _ITALIC.sub(r"<i>\1</i>", text)
    return text


def title_of(body: str, default: str = "Javob") -> str:
    """Matnning birinchi mazmunli satridan sarlavha yasaydi."""
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        heading = _HEADING.match(line)
        if heading:
            line = heading.group(2)
        line = _BOLD.sub(r"\1", line).strip(" *#:")
        if line:
            return line[:80]
    return default


def filename_of(title: str) -> str:
    """Sarlavhadan xavfsiz fayl nomi."""
    simple = _simplify(title).lower()
    simple = re.sub(r"[^a-z0-9]+", "_", simple).strip("_")
    return (simple[:40] or "javob") + ".pdf"


def build(body: str, title: str | None = None) -> bytes:
    """Markdown'ga o'xshash matndan PDF yasaydi."""
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

    regular, bold, mono, unicode_ok = _fonts()
    if not unicode_ok:
        body = _simplify(body)
        title = _simplify(title) if title else None

    heading_title = title or title_of(body)

    normal = ParagraphStyle(
        "normal", fontName=regular, fontSize=11, leading=16,
        spaceAfter=6, alignment=TA_LEFT,
    )
    head1 = ParagraphStyle(
        "head1", parent=normal, fontName=bold, fontSize=16,
        leading=21, spaceBefore=4, spaceAfter=10,
    )
    head2 = ParagraphStyle(
        "head2", parent=normal, fontName=bold, fontSize=13,
        leading=18, spaceBefore=10, spaceAfter=6,
    )

    story = [Paragraph(_inline(heading_title, mono), head1)]
    bullets: list[ListItem] = []

    def flush_bullets() -> None:
        if bullets:
            story.append(ListFlowable(list(bullets), bulletType="bullet", leftIndent=14))
            story.append(Spacer(1, 4))
            bullets.clear()

    for raw in body.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush_bullets()
            continue

        heading = _HEADING.match(line)
        if heading:
            flush_bullets()
            story.append(Paragraph(_inline(heading.group(2), mono), head2))
            continue

        bullet = _BULLET.match(line)
        if bullet:
            bullets.append(ListItem(Paragraph(_inline(bullet.group(1), mono), normal)))
            continue

        numbered = _NUMBERED.match(line)
        if numbered:
            flush_bullets()
            story.append(Paragraph(
                f"{numbered.group(1)}. " + _inline(numbered.group(2), mono), normal,
            ))
            continue

        flush_bullets()
        story.append(Paragraph(_inline(line, mono), normal))

    flush_bullets()

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=heading_title, author="Claude bot",
    )
    document.build(story)
    return buffer.getvalue()
