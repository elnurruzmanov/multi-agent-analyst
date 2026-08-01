"""Gladiator bot: saqlash qatlami va matn shakllantirish testlari.

Telegram'ga umuman chiqmaydi — faqat mustaqil mantiq tekshiriladi.
"""
import asyncio
import importlib
from datetime import date

import pytest


@pytest.fixture()
def bot_db(tmp_path, monkeypatch):
    """Har bir test uchun toza SQLite bazasi."""
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BOT_TOKEN", "test:token")
    monkeypatch.setenv("ADMIN_IDS", "111,222")

    import bot.config as bot_config
    importlib.reload(bot_config)
    from bot.storage import db
    importlib.reload(db)

    asyncio.run(db.init())
    return db


def test_admin_ids_parsed(bot_db):
    import bot.config as bot_config
    assert bot_config.ADMIN_IDS == {111, 222}
    assert bot_config.is_admin(111)
    assert not bot_config.is_admin(999)


def _sample(user_id=42, day=None):
    return {
        "user_id": user_id,
        "username": "gladiator_fan",
        "full_name": "Test Mijoz",
        "phone": "+998901234567",
        "booking_date": day or date.today().isoformat(),
        "time_slot": "18:00",
        "sector_code": "s3",
        "tariff_code": "t3",
        "people": 4,
        "comment": "Tug'ilgan kun",
    }


def test_booking_is_stored_and_listed(bot_db):
    booking_id = asyncio.run(bot_db.create_booking(_sample()))
    assert booking_id == 1

    rows = asyncio.run(bot_db.list_bookings(status="new"))
    assert len(rows) == 1
    assert rows[0]["phone"] == "+998901234567"
    assert rows[0]["people"] == 4
    assert rows[0]["status"] == "new"


def test_status_change_and_today_filter(bot_db):
    booking_id = asyncio.run(bot_db.create_booking(_sample()))
    asyncio.run(bot_db.create_booking(_sample(user_id=43, day="2030-01-01")))

    row = asyncio.run(bot_db.set_status(booking_id, "confirmed"))
    assert row["status"] == "confirmed"

    today = asyncio.run(bot_db.bookings_for_date(date.today().isoformat()))
    assert [r["id"] for r in today] == [booking_id]

    asyncio.run(bot_db.set_status(booking_id, "cancelled"))
    assert asyncio.run(bot_db.bookings_for_date(date.today().isoformat())) == []


def test_stamp_resets_and_grants_reward_at_ten(bot_db):
    asyncio.run(bot_db.upsert_card(42, "gladiator_fan", "Test Mijoz", "+998901234567"))

    for visit in range(1, 10):
        card, earned = asyncio.run(bot_db.add_stamp(42))
        assert card["stamps"] == visit
        assert not earned

    card, earned = asyncio.run(bot_db.add_stamp(42))
    assert earned, "10-tashrifda bepul soat berilishi kerak"
    assert card["stamps"] == 0, "karta nolga qaytishi kerak"
    assert card["rewards"] == 1
    assert card["total_visits"] == 10


def test_find_card_by_id_username_and_phone(bot_db):
    asyncio.run(bot_db.upsert_card(42, "gladiator_fan", "Test Mijoz", "+998901234567"))

    assert asyncio.run(bot_db.find_card("42"))["user_id"] == 42
    assert asyncio.run(bot_db.find_card("@gladiator_fan"))["user_id"] == 42
    assert asyncio.run(bot_db.find_card("+998901234567"))["user_id"] == 42
    assert asyncio.run(bot_db.find_card("901234567"))["user_id"] == 42
    assert asyncio.run(bot_db.find_card("yo'q-mijoz")) is None


def test_upsert_does_not_wipe_known_phone(bot_db):
    asyncio.run(bot_db.upsert_card(42, "gladiator_fan", "Test Mijoz", "+998901234567"))
    card = asyncio.run(bot_db.upsert_card(42, "gladiator_fan", "Test Mijoz"))
    assert card["phone"] == "+998901234567"


def test_stats_counts_every_status(bot_db):
    first = asyncio.run(bot_db.create_booking(_sample()))
    asyncio.run(bot_db.create_booking(_sample(user_id=43)))
    asyncio.run(bot_db.set_status(first, "confirmed"))

    data = asyncio.run(bot_db.stats())
    assert data["total"] == 2
    assert data["confirmed"] == 1
    assert data["new"] == 1
    assert data["clients"] == 2


def test_texts_render_without_error(bot_db):
    from bot import texts
    from bot.catalog import money

    assert money(15000) == "15 000 so'm"
    assert "3 soat" in texts.prices()
    assert "Squad Room" in texts.arena()

    summary = texts.booking_summary(_sample())
    assert "Squad Room" in summary and "+998901234567" in summary

    card = asyncio.run(bot_db.upsert_card(42, "u", "Test Mijoz"))
    assert "0 / 10" in texts.pass_card(card, "Test Mijoz")


def test_summary_escapes_html_in_user_input(bot_db):
    from bot import texts

    data = _sample()
    data["comment"] = "<b>qalin</b> & <script>"
    summary = texts.booking_summary(data)
    assert "<script>" not in summary
    assert "&lt;script&gt;" in summary


def test_sheets_is_disabled_without_credentials(bot_db):
    from bot.storage import sheets
    importlib.reload(sheets)

    assert not sheets.enabled()
    # Yoqilmagan bo'lsa ham chaqiruvlar xato bermasligi kerak.
    asyncio.run(sheets.append_booking([1, "2026-08-01"]))
    asyncio.run(sheets.update_status(1, "confirmed"))
