"""SQLite — buyurtmalar va sodiqlik kartasi uchun asosiy manba.

sqlite3 sinxron, shuning uchun har bir chaqiruv asyncio.to_thread ichida
bajariladi: klub hajmidagi yuk uchun bu yetarli va hech qanday qo'shimchа
kutubxona talab qilmaydi.
"""
from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime, timezone
from typing import Any

from bot.config import DB_PATH, STAMPS_PER_REWARD

_SCHEMA = """
CREATE TABLE IF NOT EXISTS bookings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    username    TEXT,
    full_name   TEXT,
    phone       TEXT,
    booking_date TEXT NOT NULL,
    time_slot   TEXT NOT NULL,
    sector_code TEXT NOT NULL,
    tariff_code TEXT NOT NULL,
    people      INTEGER NOT NULL DEFAULT 1,
    comment     TEXT,
    status      TEXT NOT NULL DEFAULT 'new',
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(booking_date);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);

CREATE TABLE IF NOT EXISTS pass_cards (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    full_name   TEXT,
    phone       TEXT,
    stamps      INTEGER NOT NULL DEFAULT 0,
    total_visits INTEGER NOT NULL DEFAULT 0,
    rewards     INTEGER NOT NULL DEFAULT 0,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pass_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    delta      INTEGER NOT NULL,
    reason     TEXT,
    admin_id   INTEGER,
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _init_sync() -> None:
    with _connect() as conn:
        conn.executescript(_SCHEMA)


async def init() -> None:
    await asyncio.to_thread(_init_sync)


# --- buyurtmalar ----------------------------------------------------------


def _create_booking_sync(data: dict[str, Any]) -> int:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO bookings (user_id, username, full_name, phone, booking_date,
                                  time_slot, sector_code, tariff_code, people, comment,
                                  status, created_at)
            VALUES (:user_id, :username, :full_name, :phone, :booking_date,
                    :time_slot, :sector_code, :tariff_code, :people, :comment,
                    'new', :created_at)
            """,
            {**data, "created_at": _now()},
        )
        return int(cur.lastrowid)


async def create_booking(data: dict[str, Any]) -> int:
    return await asyncio.to_thread(_create_booking_sync, data)


def _set_status_sync(booking_id: int, status: str) -> sqlite3.Row | None:
    with _connect() as conn:
        conn.execute("UPDATE bookings SET status = ? WHERE id = ?", (status, booking_id))
        return conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()


async def set_status(booking_id: int, status: str) -> sqlite3.Row | None:
    return await asyncio.to_thread(_set_status_sync, booking_id, status)


def _list_bookings_sync(status: str | None, limit: int) -> list[sqlite3.Row]:
    with _connect() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM bookings WHERE status = ? ORDER BY id DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM bookings ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return list(rows)


async def list_bookings(status: str | None = None, limit: int = 10) -> list[sqlite3.Row]:
    return await asyncio.to_thread(_list_bookings_sync, status, limit)


def _bookings_for_date_sync(date_str: str) -> list[sqlite3.Row]:
    with _connect() as conn:
        return list(
            conn.execute(
                """
                SELECT * FROM bookings
                WHERE booking_date = ? AND status != 'cancelled'
                ORDER BY time_slot
                """,
                (date_str,),
            ).fetchall()
        )


async def bookings_for_date(date_str: str) -> list[sqlite3.Row]:
    return await asyncio.to_thread(_bookings_for_date_sync, date_str)


def _stats_sync() -> dict[str, int]:
    with _connect() as conn:
        def one(sql: str, *args: Any) -> int:
            return int(conn.execute(sql, args).fetchone()[0])

        return {
            "total": one("SELECT COUNT(*) FROM bookings"),
            "new": one("SELECT COUNT(*) FROM bookings WHERE status = 'new'"),
            "confirmed": one("SELECT COUNT(*) FROM bookings WHERE status = 'confirmed'"),
            "cancelled": one("SELECT COUNT(*) FROM bookings WHERE status = 'cancelled'"),
            "clients": one("SELECT COUNT(DISTINCT user_id) FROM bookings"),
            "cards": one("SELECT COUNT(*) FROM pass_cards"),
            "rewards": one("SELECT COALESCE(SUM(rewards), 0) FROM pass_cards"),
        }


async def stats() -> dict[str, int]:
    return await asyncio.to_thread(_stats_sync)


# --- Gladiator Pass -------------------------------------------------------


def _upsert_card_sync(user_id: int, username: str | None, full_name: str | None,
                      phone: str | None) -> sqlite3.Row:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO pass_cards (user_id, username, full_name, phone, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username  = COALESCE(excluded.username, pass_cards.username),
                full_name = COALESCE(excluded.full_name, pass_cards.full_name),
                phone     = COALESCE(excluded.phone, pass_cards.phone),
                updated_at = excluded.updated_at
            """,
            (user_id, username, full_name, phone, _now()),
        )
        return conn.execute("SELECT * FROM pass_cards WHERE user_id = ?", (user_id,)).fetchone()


async def upsert_card(user_id: int, username: str | None = None,
                      full_name: str | None = None, phone: str | None = None) -> sqlite3.Row:
    return await asyncio.to_thread(_upsert_card_sync, user_id, username, full_name, phone)


def _add_stamp_sync(user_id: int, admin_id: int | None, reason: str) -> tuple[sqlite3.Row, bool]:
    """Belgi qo'shadi. Karta to'lganda nolga qaytadi va (karta, True) qaytariladi."""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO pass_cards (user_id, stamps, total_visits, updated_at)
            VALUES (?, 0, 0, ?)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (user_id, _now()),
        )
        conn.execute(
            """
            UPDATE pass_cards
            SET stamps = stamps + 1, total_visits = total_visits + 1, updated_at = ?
            WHERE user_id = ?
            """,
            (_now(), user_id),
        )
        conn.execute(
            "INSERT INTO pass_events (user_id, delta, reason, admin_id, created_at) "
            "VALUES (?, 1, ?, ?, ?)",
            (user_id, reason, admin_id, _now()),
        )

        card = conn.execute("SELECT * FROM pass_cards WHERE user_id = ?", (user_id,)).fetchone()
        earned = card["stamps"] >= STAMPS_PER_REWARD
        if earned:
            conn.execute(
                """
                UPDATE pass_cards
                SET stamps = stamps - ?, rewards = rewards + 1, updated_at = ?
                WHERE user_id = ?
                """,
                (STAMPS_PER_REWARD, _now(), user_id),
            )
            card = conn.execute(
                "SELECT * FROM pass_cards WHERE user_id = ?", (user_id,)
            ).fetchone()
        return card, earned


async def add_stamp(user_id: int, admin_id: int | None = None,
                    reason: str = "tashrif") -> tuple[sqlite3.Row, bool]:
    return await asyncio.to_thread(_add_stamp_sync, user_id, admin_id, reason)


def _get_card_sync(user_id: int) -> sqlite3.Row | None:
    with _connect() as conn:
        return conn.execute("SELECT * FROM pass_cards WHERE user_id = ?", (user_id,)).fetchone()


async def get_card(user_id: int) -> sqlite3.Row | None:
    return await asyncio.to_thread(_get_card_sync, user_id)


def _find_card_sync(query: str) -> sqlite3.Row | None:
    """Telegram ID, @username yoki telefon raqami bo'yicha qidiradi."""
    digits = "".join(ch for ch in query if ch.isdigit())
    handle = query.lstrip("@").lower()
    with _connect() as conn:
        if query.isdigit():
            row = conn.execute(
                "SELECT * FROM pass_cards WHERE user_id = ?", (int(query),)
            ).fetchone()
            if row:
                return row
        row = conn.execute(
            "SELECT * FROM pass_cards WHERE LOWER(username) = ?", (handle,)
        ).fetchone()
        if row:
            return row
        if digits:
            return conn.execute(
                "SELECT * FROM pass_cards WHERE REPLACE(REPLACE(phone,'+',''),' ','') LIKE ?",
                (f"%{digits[-9:]}",),
            ).fetchone()
        return None


async def find_card(query: str) -> sqlite3.Row | None:
    return await asyncio.to_thread(_find_card_sync, query)
