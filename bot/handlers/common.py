"""Asosiy menyu: /start, narxlar, arena, aloqa, Gladiator Pass."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot import keyboards as kb
from bot import texts
from bot.config import is_admin
from bot.storage import db

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = message.from_user
    await db.upsert_card(user.id, user.username, user.full_name)
    await message.answer(
        texts.WELCOME,
        reply_markup=kb.main_menu(is_admin(user.id)),
    )
    await message.answer("Saytimizni ham ko'rishingiz mumkin:", reply_markup=kb.site_kb())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(texts.WELCOME, reply_markup=kb.main_menu(is_admin(message.from_user.id)))


@router.message(F.text == kb.BTN_PRICES)
async def show_prices(message: Message) -> None:
    await message.answer(texts.prices())


@router.message(F.text == kb.BTN_ARENA)
async def show_arena(message: Message) -> None:
    await message.answer(texts.arena())


@router.message(F.text == kb.BTN_CONTACT)
async def show_contact(message: Message) -> None:
    await message.answer(texts.CONTACT, reply_markup=kb.site_kb(),
                         disable_web_page_preview=True)


@router.message(F.text == kb.BTN_PASS)
async def show_pass(message: Message) -> None:
    user = message.from_user
    card = await db.upsert_card(user.id, user.username, user.full_name)
    await message.answer(texts.pass_card(card, user.full_name))
