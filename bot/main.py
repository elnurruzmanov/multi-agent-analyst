"""Botni ishga tushirish: python -m bot.main"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from bot.config import ADMIN_IDS, require_token
from bot.handlers import build_router
from bot.storage import db, sheets

log = logging.getLogger("gladiator")


async def _set_commands(bot: Bot) -> None:
    await bot.set_my_commands([
        BotCommand(command="start", description="Boshlash / asosiy menyu"),
        BotCommand(command="id", description="Telegram ID ni ko'rsatish"),
        BotCommand(command="help", description="Yordam"),
    ])


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    token = require_token()

    if not ADMIN_IDS:
        log.warning(
            "ADMIN_IDS bo'sh — buyurtmalar hech kimga yuborilmaydi. "
            "Botga /id yozib, chiqqan raqamni ADMIN_IDS ga qo'shing."
        )
    log.info("Google Sheets: %s", "yoqilgan" if sheets.enabled() else "o'chirilgan")

    await db.init()

    bot = Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(build_router())

    await _set_commands(bot)
    # Polling boshlanishidan oldin to'planib qolgan eski xabarlarni tashlab yuboramiz.
    await bot.delete_webhook(drop_pending_updates=True)
    log.info("Bot ishga tushdi")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
