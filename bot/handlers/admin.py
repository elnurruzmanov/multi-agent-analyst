"""Admin panel: buyurtmalarni boshqarish, statistika, Pass belgilari."""
from __future__ import annotations

from datetime import date

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from bot import keyboards as kb
from bot import texts
from bot.config import is_admin
from bot.storage import db, sheets

router = Router(name="admin")


def _guard(user_id: int) -> bool:
    return is_admin(user_id)


@router.message(F.text == kb.BTN_ADMIN)
@router.message(Command("admin"))
async def admin_menu(message: Message) -> None:
    if not _guard(message.from_user.id):
        await message.answer(texts.NOT_ADMIN)
        return
    await message.answer("⚙️ <b>Admin panel</b>", reply_markup=kb.admin_menu_kb())


@router.callback_query(F.data == "adm:list:new")
async def list_new(call: CallbackQuery) -> None:
    if not _guard(call.from_user.id):
        await call.answer(texts.NOT_ADMIN, show_alert=True)
        return
    rows = await db.list_bookings(status="new", limit=15)
    if not rows:
        await call.message.answer("Yangi buyurtmalar yo'q.")
    else:
        body = "\n\n".join(texts.booking_row(row) for row in rows)
        await call.message.answer(f"🆕 <b>Yangi buyurtmalar</b>\n\n{body}")
    await call.answer()


@router.callback_query(F.data == "adm:today")
async def today_schedule(call: CallbackQuery) -> None:
    if not _guard(call.from_user.id):
        await call.answer(texts.NOT_ADMIN, show_alert=True)
        return
    rows = await db.bookings_for_date(date.today().isoformat())
    if not rows:
        await call.message.answer("Bugunga buyurtma yo'q.")
    else:
        body = "\n\n".join(texts.booking_row(row) for row in rows)
        await call.message.answer(f"📅 <b>Bugungi jadval</b>\n\n{body}")
    await call.answer()


@router.callback_query(F.data == "adm:stats")
async def show_stats(call: CallbackQuery) -> None:
    if not _guard(call.from_user.id):
        await call.answer(texts.NOT_ADMIN, show_alert=True)
        return
    await call.message.answer(texts.stats(await db.stats()))
    await call.answer()


@router.callback_query(F.data == "adm:passhelp")
async def pass_help(call: CallbackQuery) -> None:
    if not _guard(call.from_user.id):
        await call.answer(texts.NOT_ADMIN, show_alert=True)
        return
    await call.message.answer(texts.PASS_HELP)
    await call.answer()


# --- buyurtma xabari ostidagi tugmalar ------------------------------------


@router.callback_query(F.data.startswith("adm:ok:"))
async def confirm_booking(call: CallbackQuery, bot: Bot) -> None:
    if not _guard(call.from_user.id):
        await call.answer(texts.NOT_ADMIN, show_alert=True)
        return
    booking_id = int(call.data.rsplit(":", 1)[1])
    row = await db.set_status(booking_id, "confirmed")
    await sheets.update_status(booking_id, "confirmed")
    await call.message.edit_text(
        call.message.html_text + f"\n\n✅ <b>Tasdiqlandi</b> ({call.from_user.full_name})",
        reply_markup=kb.admin_booking_kb(booking_id),
    )
    if row:
        try:
            await bot.send_message(
                row["user_id"],
                f"✅ <b>Buyurtmangiz #{booking_id} tasdiqlandi!</b>\n\n"
                f"Sizni {row['booking_date']} kuni soat {row['time_slot']} da kutamiz.\n"
                "Arenaga xush kelibsiz! ⚔️",
            )
        except Exception:
            pass
    await call.answer("Tasdiqlandi")


@router.callback_query(F.data.startswith("adm:no:"))
async def cancel_booking(call: CallbackQuery, bot: Bot) -> None:
    if not _guard(call.from_user.id):
        await call.answer(texts.NOT_ADMIN, show_alert=True)
        return
    booking_id = int(call.data.rsplit(":", 1)[1])
    row = await db.set_status(booking_id, "cancelled")
    await sheets.update_status(booking_id, "cancelled")
    await call.message.edit_text(
        call.message.html_text + f"\n\n❌ <b>Bekor qilindi</b> ({call.from_user.full_name})",
        reply_markup=kb.admin_booking_kb(booking_id),
    )
    if row:
        try:
            await bot.send_message(
                row["user_id"],
                f"❌ Afsuski, buyurtmangiz <b>#{booking_id}</b> bekor qilindi.\n"
                "Boshqa vaqt tanlash uchun administrator bilan bog'laning.",
            )
        except Exception:
            pass
    await call.answer("Bekor qilindi")


@router.callback_query(F.data.startswith("adm:stamp:"))
async def stamp_from_booking(call: CallbackQuery, bot: Bot) -> None:
    if not _guard(call.from_user.id):
        await call.answer(texts.NOT_ADMIN, show_alert=True)
        return
    booking_id = int(call.data.rsplit(":", 1)[1])
    rows = await db.list_bookings(limit=1000)
    target = next((r for r in rows if r["id"] == booking_id), None)
    if target is None:
        await call.answer("Buyurtma topilmadi", show_alert=True)
        return
    card, earned = await db.add_stamp(target["user_id"], call.from_user.id,
                                      f"buyurtma #{booking_id}")
    try:
        await bot.send_message(target["user_id"], texts.stamp_added(card, earned))
    except Exception:
        pass
    await call.answer(
        "Bepul soat berildi! 🎉" if earned else f"Belgi qo'yildi: {card['stamps']}",
        show_alert=True,
    )


# --- /stamp va /card ------------------------------------------------------


@router.message(Command("stamp"))
async def cmd_stamp(message: Message, command: CommandObject, bot: Bot) -> None:
    if not _guard(message.from_user.id):
        await message.answer(texts.NOT_ADMIN)
        return
    query = (command.args or "").strip()
    if not query:
        await message.answer(texts.PASS_HELP)
        return
    card = await db.find_card(query)
    if card is None:
        await message.answer(
            "Mijoz topilmadi. U avval botga /start bosgan bo'lishi kerak."
        )
        return
    card, earned = await db.add_stamp(card["user_id"], message.from_user.id, "qo'lda")
    try:
        await bot.send_message(card["user_id"], texts.stamp_added(card, earned))
    except Exception:
        pass
    await message.answer(
        texts.pass_card(card, card["full_name"] or str(card["user_id"]))
        + ("\n\n🎉 Bepul soat berildi!" if earned else "")
    )


@router.message(Command("card"))
async def cmd_card(message: Message, command: CommandObject) -> None:
    if not _guard(message.from_user.id):
        await message.answer(texts.NOT_ADMIN)
        return
    query = (command.args or "").strip()
    if not query:
        await message.answer(texts.PASS_HELP)
        return
    card = await db.find_card(query)
    if card is None:
        await message.answer("Mijoz topilmadi.")
        return
    await message.answer(texts.pass_card(card, card["full_name"] or str(card["user_id"])))


@router.message(Command("id"))
async def cmd_id(message: Message) -> None:
    """Admin ID sini bilish uchun — sozlashda kerak bo'ladi."""
    await message.answer(
        f"Sizning Telegram ID: <code>{message.from_user.id}</code>\n\n"
        "Bu raqamni Render'dagi <code>ADMIN_IDS</code> ga qo'shing."
    )
