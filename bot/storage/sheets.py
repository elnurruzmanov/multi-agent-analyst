"""Google Sheets — ixtiyoriy ko'zgu.

Kalit berilmasa yoki gspread o'rnatilmagan bo'lsa, bu modul jimgina o'chib
qoladi: bot Sheets'siz to'liq ishlaydi va hech qanday xato bermaydi. Sheets
hech qachon asosiy manba emas — u faqat SQLite'dagi yozuvning nusxasi.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from bot.config import SHEET_CREDENTIALS, SHEET_ID

log = logging.getLogger(__name__)

_HEADER = [
    "ID", "Sana", "Vaqt", "Sektor", "Tarif", "Kishi",
    "Ism", "Telefon", "Username", "Izoh", "Holat", "Yaratilgan",
]

_worksheet: Any = None
_checked = False


def enabled() -> bool:
    return bool(SHEET_ID and SHEET_CREDENTIALS)


def _open_sync() -> Any:
    import gspread  # kutubxona faqat Sheets yoqilganda kerak
    from google.oauth2.service_account import Credentials

    creds = Credentials.from_service_account_info(
        json.loads(SHEET_CREDENTIALS),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    sheet = gspread.authorize(creds).open_by_key(SHEET_ID).sheet1
    if not sheet.row_values(1):
        sheet.append_row(_HEADER)
    return sheet


def _worksheet_sync() -> Any:
    global _worksheet, _checked
    if _worksheet is None and not _checked:
        _checked = True
        try:
            _worksheet = _open_sync()
            log.info("Google Sheets ulandi")
        except Exception as exc:  # kalit noto'g'ri, tarmoq yo'q, ruxsat yo'q...
            log.warning("Google Sheets ulanmadi, o'tkazib yuborildi: %s", exc)
            _worksheet = None
    return _worksheet


def _append_sync(row: list[Any]) -> None:
    sheet = _worksheet_sync()
    if sheet is not None:
        sheet.append_row([str(cell) for cell in row])


async def append_booking(row: list[Any]) -> None:
    """Buyurtmani jadvalga qo'shadi. Xatolik bo'lsa ham botni to'xtatmaydi."""
    if not enabled():
        return
    try:
        await asyncio.to_thread(_append_sync, row)
    except Exception as exc:
        log.warning("Sheets'ga yozib bo'lmadi: %s", exc)


def _update_status_sync(booking_id: int, status: str) -> None:
    sheet = _worksheet_sync()
    if sheet is None:
        return
    cell = sheet.find(str(booking_id), in_column=1)
    if cell:
        sheet.update_cell(cell.row, _HEADER.index("Holat") + 1, status)


async def update_status(booking_id: int, status: str) -> None:
    if not enabled():
        return
    try:
        await asyncio.to_thread(_update_status_sync, booking_id, status)
    except Exception as exc:
        log.warning("Sheets'da holatni yangilab bo'lmadi: %s", exc)
