"""Webhook rejimi — bot bepul «web service» sifatida ham yashay olsin.

Long polling doim ishlab turadigan servisni talab qiladi. Bepul hostinglarda
(masalan Render) bunday servis pullik bo'lishi yoki harakatsizlikdan keyin
uxlab qolishi mumkin. Webhook'da esa aksincha: Telegram xabar kelganda bizning
manzilimizga o'zi murojaat qiladi — shu murojaat servisni uyg'otadi ham.

`CLAUDE_WEBHOOK_URL` berilsa shu rejim, berilmasa oddiy polling ishlaydi.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging

from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

log = logging.getLogger("claude-bot.webhook")


def secret_path(token: str) -> str:
    """Tokendan kelib chiqadigan, tashqaridan topib bo'lmaydigan manzil.

    Tokenning o'zi emas, uning sha256 yig'indisi ishlatiladi: manzil logga
    tushib qolsa ham tokenni tiklab bo'lmaydi.
    """
    return "/telegram/" + hashlib.sha256(token.encode()).hexdigest()[:32]


def secret_token(token: str) -> str:
    """Telegram har bir so'rovda qaytaradigan maxfiy sarlavha qiymati."""
    return hashlib.sha256(("aiogram-secret:" + token).encode()).hexdigest()[:48]


async def _health(_request: web.Request) -> web.Response:
    """Hosting «tirikmi?» deb so'raganda va uyg'otish ping'lari uchun."""
    return web.Response(text="ok")


def build_app(bot: Bot, dispatcher: Dispatcher, *, path: str, secret: str) -> web.Application:
    app = web.Application()
    app.router.add_get("/", _health)
    app.router.add_get("/healthz", _health)
    SimpleRequestHandler(
        dispatcher=dispatcher, bot=bot, secret_token=secret
    ).register(app, path=path)
    setup_application(app, dispatcher, bot=bot)
    return app


async def run(
    bot: Bot,
    dispatcher: Dispatcher,
    *,
    base_url: str,
    port: int,
    token: str,
) -> None:
    path = secret_path(token)
    secret = secret_token(token)
    app = build_app(bot, dispatcher, path=path, secret=secret)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    await bot.set_webhook(
        base_url + path,
        secret_token=secret,
        drop_pending_updates=True,
    )
    # Manzilning maxfiy qismini logga chiqarmaymiz.
    log.info("Webhook rejimi: %s/telegram/… , port %s", base_url, port)

    try:
        await asyncio.Event().wait()  # Telegram murojaatlarini kutamiz
    finally:
        await runner.cleanup()
