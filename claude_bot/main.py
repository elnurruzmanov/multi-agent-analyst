"""Claude'ga ulangan Telegram bot: python -m claude_bot.main

Foydalanuvchi botga savol yozadi → bot uni Claude API'ga yuboradi → javob
oqim bilan qaytib, xabar yozilib borgani sayin tahrirlanadi.
"""
from __future__ import annotations

import asyncio
import logging
import time

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatAction, ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramUnauthorizedError
from aiogram.filters import Command, CommandStart
from aiogram.types import BotCommand, Message

from claude_bot import config, formatting, texts, webhook
from claude_bot.claude import ClaudeClient, friendly_error
from claude_bot.session import ChatHistory, RateLimiter

log = logging.getLogger("claude-bot")

# Telegram bir chatda sekundiga bir nechta tahrirdan ortig'ini yoqtirmaydi.
EDIT_INTERVAL = 1.5

router = Router(name="claude")


@router.message(CommandStart())
@router.message(Command("help"))
async def cmd_start(message: Message) -> None:
    await message.answer(texts.WELCOME, parse_mode=ParseMode.HTML)


@router.message(Command("new"))
async def cmd_new(message: Message, history: ChatHistory) -> None:
    history.clear(message.chat.id)
    await message.answer(texts.CLEARED)


@router.message(Command("id"))
async def cmd_id(message: Message) -> None:
    await message.answer(
        f"Telegram ID: <code>{message.from_user.id}</code>",
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("model"))
async def cmd_model(message: Message, history: ChatHistory) -> None:
    await message.answer(
        texts.model_info(config.MODEL, config.EFFORT, len(history.get(message.chat.id))),
        parse_mode=ParseMode.HTML,
    )


@router.message(F.text)
async def on_question(
    message: Message,
    bot: Bot,
    claude: ClaudeClient,
    history: ChatHistory,
    limiter: RateLimiter,
) -> None:
    user_id = message.from_user.id
    if not config.is_allowed(user_id):
        await message.answer(texts.NOT_ALLOWED)
        return

    question = message.text.strip()
    if not question:
        return
    if len(question) > config.MAX_QUESTION_CHARS:
        await message.answer(texts.too_long(config.MAX_QUESTION_CHARS))
        return
    if not limiter.allow(user_id):
        await message.answer(texts.rate_limited(config.RATE_LIMIT_PER_MINUTE))
        return

    chat_id = message.chat.id
    await bot.send_chat_action(chat_id, ChatAction.TYPING)
    placeholder = await message.answer(texts.THINKING)

    conversation = history.get(chat_id) + [{"role": "user", "content": question}]

    try:
        reply = await claude.ask(conversation, _progress(placeholder))
    except Exception as exc:  # bitta savol butun botni to'xtatmasligi kerak
        log.exception("Claude so'rovi muvaffaqiyatsiz")
        await _safe_edit(placeholder, friendly_error(exc))
        return

    if reply.stop_reason == "refusal":
        await _safe_edit(placeholder, texts.refused(reply.refusal))
        return
    if not reply.text:
        await _safe_edit(placeholder, texts.EMPTY_ANSWER)
        return

    history.add(chat_id, "user", question)
    history.add(chat_id, "assistant", reply.text)

    answer = reply.text
    if reply.truncated:
        answer += "\n\n…(javob uzunlik chegarasiga yetdi — «davom et» deb yozing)"

    await _deliver(message, placeholder, answer)
    log.info(
        "chat=%s tokens in=%s out=%s model=%s",
        chat_id, reply.input_tokens, reply.output_tokens, reply.model,
    )


@router.message()
async def on_other(message: Message) -> None:
    """Rasm, ovoz, fayl — hozircha matndan boshqasini o'qimaymiz."""
    await message.answer(texts.ONLY_TEXT)


def _progress(placeholder: Message):
    """Oqim davomida xabarni vaqti-vaqti bilan yangilab turadigan callback."""
    state = {"at": 0.0, "text": ""}

    async def update(partial: str) -> None:
        now = time.monotonic()
        if now - state["at"] < EDIT_INTERVAL:
            return
        preview = _preview(partial)
        if preview == state["text"]:
            return
        state["at"], state["text"] = now, preview
        # Oraliq matn oddiy matn sifatida yuboriladi: yarim yozilgan markdown
        # HTML bo'lib qolsa, Telegram xabarni rad etadi.
        await _safe_edit(placeholder, preview)

    return update


def _preview(partial: str) -> str:
    """Oraliq ko'rsatish uchun oxirgi bo'lak — Telegram chegarasiga sig'sin."""
    limit = formatting.CHUNK_LIMIT
    text = partial if len(partial) <= limit else "…" + partial[-limit:]
    return (text + " ▌").strip()


async def _safe_edit(placeholder: Message, text: str, **kwargs) -> None:
    try:
        await placeholder.edit_text(text, **kwargs)
    except TelegramBadRequest as exc:
        # "message is not modified" va shunga o'xshash mayda xatolar javobni
        # yo'qotishga arzimaydi.
        log.debug("Xabarni tahrirlab bo'lmadi: %s", exc)


async def _deliver(message: Message, placeholder: Message, answer: str) -> None:
    """Javobni bo'laklab yuboradi; HTML o'tmasa — oddiy matn bilan."""
    html_chunks = formatting.render(answer)
    plain_chunks = formatting.split_markdown(answer)

    for index, chunk in enumerate(html_chunks):
        plain = plain_chunks[index] if index < len(plain_chunks) else chunk
        try:
            if index == 0:
                await placeholder.edit_text(
                    chunk, parse_mode=ParseMode.HTML, disable_web_page_preview=True
                )
            else:
                await message.answer(
                    chunk, parse_mode=ParseMode.HTML, disable_web_page_preview=True
                )
        except TelegramBadRequest as exc:
            log.warning("HTML qabul qilinmadi (%s) — oddiy matn yuborildi", exc)
            if index == 0:
                await _safe_edit(placeholder, plain, disable_web_page_preview=True)
            else:
                await message.answer(plain, disable_web_page_preview=True)


async def _set_commands(bot: Bot) -> None:
    await bot.set_my_commands([
        BotCommand(command="start", description="Boshlash"),
        BotCommand(command="new", description="Suhbatni tozalash"),
        BotCommand(command="model", description="Qaysi model ishlayapti"),
        BotCommand(command="id", description="Telegram ID ni ko'rsatish"),
        BotCommand(command="help", description="Yordam"),
    ])


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    token = config.require_token()
    api_key = config.require_api_key()

    if not config.ALLOWED_USER_IDS:
        log.warning(
            "CLAUDE_ALLOWED_USER_IDS bo'sh — bot hammaga ochiq va har bir savol "
            "Anthropic hisobidan pul yechadi. Faqat o'zingiz uchun bo'lsa, "
            "/id dan olingan raqamni shu env var ga yozing."
        )

    claude = ClaudeClient(
        api_key,
        model=config.MODEL,
        system=config.SYSTEM_PROMPT,
        max_tokens=config.MAX_TOKENS,
        effort=config.EFFORT,
        use_fallbacks=config.USE_FALLBACKS,
        use_thinking=config.USE_THINKING,
    )

    bot = Bot(token)
    dp = Dispatcher(
        claude=claude,
        history=ChatHistory(config.HISTORY_LIMIT),
        limiter=RateLimiter(config.RATE_LIMIT_PER_MINUTE),
    )
    dp.include_router(router)

    try:
        await _set_commands(bot)
        log.info("Bot ishga tushdi — model %s, effort %s", config.MODEL, config.EFFORT)

        if config.WEBHOOK_URL:
            await webhook.run(
                bot, dp, base_url=config.WEBHOOK_URL, port=config.PORT, token=token
            )
        else:
            log.info("Polling rejimi (CLAUDE_WEBHOOK_URL berilmagan)")
            # Eski webhook qolib ketgan bo'lsa olib tashlaymiz, to'planib qolgan
            # xabarlarga esa javob bermaymiz.
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot)
    except TelegramUnauthorizedError:
        raise SystemExit(
            "Telegram tokenni qabul qilmadi. CLAUDE_BOT_TOKEN ni tekshiring — "
            "@BotFather dan yangisini olish mumkin."
        )
    finally:
        await claude.aclose()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    # SystemExit ni ushlamaymiz: token yoki kalit berilmaganda sozlash bo'yicha
    # ko'rsatma ekranda ko'rinishi va exit kodi nolga teng bo'lmasligi kerak.
