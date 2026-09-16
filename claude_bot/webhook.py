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


def _make_tick_handler(on_tick, secret: str):
    """Tashqi cron xizmati uchun: `/tasks/run?key=…`.

    Bepul tarifda servis uxlab qoladi va ichki soat ham to'xtaydi. Tashqi
    ping shu manzilni chaqirsa, servis uyg'onadi va kechikkan vazifalar
    o'sha zahoti bajariladi.
    """
    async def handler(request: web.Request) -> web.Response:
        if request.query.get("key") != secret:
            return web.Response(status=403, text="forbidden")
        count = await on_tick()
        return web.Response(text=f"ran {count}")

    return handler


def build_app(
    bot: Bot,
    dispatcher: Dispatcher,
    *,
    path: str,
    secret: str,
    on_tick=None,
) -> web.Application:
    app = web.Application()
    app.router.add_get("/", _health)
    app.router.add_get("/healthz", _health)
    if on_tick is not None:
        app.router.add_get("/tasks/run", _make_tick_handler(on_tick, secret))
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
    on_tick=None,
) -> None:
    path = secret_path(token)
    secret = secret_token(token)
    app = build_app(bot, dispatcher, path=path, secret=secret, on_tick=on_tick)

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
    if on_tick is not None:
        # Bu manzilni tashqi cron xizmatiga berish kerak, shuning uchun
        # to'liq ko'rsatamiz — u faylni emas, faqat jadvalni ishga tushiradi.
        log.info("Jadval turtkisi: %s/tasks/run?key=%s", base_url, secret)

    try:
        await asyncio.Event().wait()  # Telegram murojaatlarini kutamiz
    finally:
        await runner.cleanup()
