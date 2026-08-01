"""Joy band qilish oqimi: sana → vaqt → sektor → tarif → kishi → telefon → izoh."""
from __future__ import annotations

import re

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from bot import keyboards as kb
from bot import texts
from bot.catalog import SECTORS_BY_CODE, TARIFFS_BY_CODE
from bot.config import ADMIN_IDS, is_admin
from bot.storage import db, sheets

router = Router(name="booking")

PHONE_RE = re.compile(r"^\+?\d{9,15}$")


class Booking(StatesGroup):
    date = State()
    time = State()
    sector = State()
    tariff = State()
    people = State()
    phone = State()
    comment = State()
    confirm = State()


@router.message(F.text == kb.BTN_BOOK)
async def start_booking(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(Booking.date)
    await message.answer("📅 <b>Qaysi kunga?</b>", reply_markup=kb.dates_kb())


@router.callback_query(F.data == "cancel")
async def cancel(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(
        texts.CANCELLED, reply_markup=kb.main_menu(is_admin(call.from_user.id))
    )
    await call.answer()


@router.callback_query(Booking.date, F.data.startswith("date:"))
async def pick_date(call: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(booking_date=call.data.split(":", 1)[1])
    await state.set_state(Booking.time)
    await call.message.edit_text("🕐 <b>Soat nechada?</b>", reply_markup=kb.times_kb())
    await call.answer()


@router.callback_query(Booking.time, F.data.startswith("time:"))
async def pick_time(call: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(time_slot=call.data.split(":", 1)[1])
    await state.set_state(Booking.sector)
    await call.message.edit_text("🎯 <b>Qaysi sektor?</b>", reply_markup=kb.sectors_kb())
    await call.answer()


@router.callback_query(Booking.sector, F.data.startswith("sector:"))
async def pick_sector(call: CallbackQuery, state: FSMContext) -> None:
    code = call.data.split(":", 1)[1]
    await state.update_data(sector_code=code)
    await state.set_state(Booking.tariff)
    sector = SECTORS_BY_CODE[code]
    await call.message.edit_text(
        f"🎯 <b>{sector.name}</b>\n{sector.desc}\n\n💰 <b>Qaysi tarif?</b>",
        reply_markup=kb.tariffs_kb(),
    )
    await call.answer()


@router.callback_query(Booking.tariff, F.data.startswith("tariff:"))
async def pick_tariff(call: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(tariff_code=call.data.split(":", 1)[1])
    await state.set_state(Booking.people)
    await call.message.edit_text("👥 <b>Necha kishi bo'lasiz?</b>",
                                 reply_markup=kb.people_kb())
    await call.answer()


@router.callback_query(Booking.people, F.data.startswith("people:"))
async def pick_people(call: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(people=int(call.data.split(":", 1)[1]))
    await state.set_state(Booking.phone)
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(texts.ASK_PHONE, reply_markup=kb.phone_kb())
    await call.answer()


# --- orqaga qaytish -------------------------------------------------------


@router.callback_query(F.data.startswith("back:"))
async def go_back(call: CallbackQuery, state: FSMContext) -> None:
    step = call.data.split(":", 1)[1]
    if step == "date":
        await state.set_state(Booking.date)
        await call.message.edit_text("📅 <b>Qaysi kunga?</b>", reply_markup=kb.dates_kb())
    elif step == "time":
        await state.set_state(Booking.time)
        await call.message.edit_text("🕐 <b>Soat nechada?</b>", reply_markup=kb.times_kb())
    elif step == "sector":
        await state.set_state(Booking.sector)
        await call.message.edit_text("🎯 <b>Qaysi sektor?</b>", reply_markup=kb.sectors_kb())
    elif step == "tariff":
        await state.set_state(Booking.tariff)
        await call.message.edit_text("💰 <b>Qaysi tarif?</b>", reply_markup=kb.tariffs_kb())
    await call.answer()


# --- telefon --------------------------------------------------------------


@router.message(Booking.phone, F.contact)
async def phone_from_contact(message: Message, state: FSMContext) -> None:
    await _save_phone(message, state, message.contact.phone_number)


@router.message(Booking.phone, F.text, ~F.text.in_(kb.MENU_BUTTONS))
async def phone_from_text(message: Message, state: FSMContext) -> None:
    raw = message.text.strip().replace(" ", "").replace("-", "")
    if not PHONE_RE.match(raw):
        await message.answer(texts.BAD_PHONE)
        return
    await _save_phone(message, state, raw)


async def _save_phone(message: Message, state: FSMContext, phone: str) -> None:
    if not phone.startswith("+"):
        phone = "+" + phone
    await state.update_data(phone=phone)
    await state.set_state(Booking.comment)
    await message.answer("Rahmat!", reply_markup=ReplyKeyboardRemove())
    await message.answer(texts.ASK_COMMENT, reply_markup=kb.comment_kb())


# --- izoh va tasdiqlash ---------------------------------------------------


@router.callback_query(Booking.comment, F.data == "comment:skip")
async def skip_comment(call: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(comment=None)
    await call.message.edit_reply_markup(reply_markup=None)
    await _ask_confirm(call.message, state)
    await call.answer()


@router.message(Booking.comment, F.text, ~F.text.in_(kb.MENU_BUTTONS))
async def take_comment(message: Message, state: FSMContext) -> None:
    await state.update_data(comment=message.text.strip()[:500])
    await _ask_confirm(message, state)


@router.message(Booking.phone, F.text.in_(kb.MENU_BUTTONS))
@router.message(Booking.comment, F.text.in_(kb.MENU_BUTTONS))
async def menu_pressed_mid_flow(message: Message, state: FSMContext) -> None:
    """Oqim o'rtasida menyu tugmasi bosilsa — band qilishni to'xtatib, bosilgan
    tugmaning o'z ishini bajaramiz. Aks holda tugma javobsiz qolardi."""
    from bot.handlers import admin, common

    await state.clear()
    text = message.text

    if text == kb.BTN_BOOK:
        await start_booking(message, state)
        return

    await message.answer(
        "Band qilish to'xtatildi.",
        reply_markup=kb.main_menu(is_admin(message.from_user.id)),
    )
    actions = {
        kb.BTN_PRICES: common.show_prices,
        kb.BTN_ARENA: common.show_arena,
        kb.BTN_PASS: common.show_pass,
        kb.BTN_CONTACT: common.show_contact,
        kb.BTN_ADMIN: admin.admin_menu,
    }
    handler = actions.get(text)
    if handler is not None:
        await handler(message)


async def _ask_confirm(message: Message, state: FSMContext) -> None:
    await state.set_state(Booking.confirm)
    data = await state.get_data()
    await message.answer(texts.booking_summary(data), reply_markup=kb.confirm_kb())


@router.callback_query(Booking.confirm, F.data == "confirm:yes")
async def save_booking(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    user = call.from_user

    booking_id = await db.create_booking({
        "user_id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "phone": data.get("phone"),
        "booking_date": data["booking_date"],
        "time_slot": data["time_slot"],
        "sector_code": data["sector_code"],
        "tariff_code": data["tariff_code"],
        "people": data.get("people", 1),
        "comment": data.get("comment"),
    })
    await db.upsert_card(user.id, user.username, user.full_name, data.get("phone"))

    await state.clear()
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(
        texts.booking_saved(booking_id), reply_markup=kb.main_menu(is_admin(user.id))
    )
    await call.answer("Buyurtma yuborildi!")

    # Uchinchi qatlam: adminlarga darhol xabar.
    text = texts.admin_new_booking(booking_id, data, user)
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text,
                                   reply_markup=kb.admin_booking_kb(booking_id))
        except Exception:
            # Admin botni bloklagan yoki hali /start bosmagan bo'lishi mumkin.
            pass

    sector = SECTORS_BY_CODE.get(data["sector_code"])
    tariff = TARIFFS_BY_CODE.get(data["tariff_code"])
    await sheets.append_booking([
        booking_id, data["booking_date"], data["time_slot"],
        sector.name if sector else "", tariff.name if tariff else "",
        data.get("people", 1), user.full_name, data.get("phone", ""),
        f"@{user.username}" if user.username else "", data.get("comment") or "",
        "new", "",
    ])
