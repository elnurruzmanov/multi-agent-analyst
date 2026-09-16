"""Claude'ga ulangan Telegram bot: python -m claude_bot.main

Foydalanuvchi botga savol yozadi → bot uni Claude API'ga yuboradi → javob
oqim bilan qaytib, xabar yozilib borgani sayin tahrirlanadi.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatAction, ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramUnauthorizedError
from aiogram.filters import Command, CommandStart
from aiogram.types import BotCommand, BufferedInputFile, Message

from claude_bot import (
    config, files, formatting, media, pdf, pricing, scheduler, tasks, texts, tools, webhook,
)
from claude_bot.claude import ClaudeClient, friendly_error
from claude_bot.session import ChatHistory, RateLimiter, UsageTracker

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


@router.message(Command("cost"))
async def cmd_cost(message: Message, usage: UsageTracker) -> None:
    await message.answer(
        texts.cost_report(
            usage.summary(message.chat.id), config.MODEL, pricing.money,
        ),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


@router.message(Command("pdf"))
async def cmd_pdf(message: Message, history: ChatHistory) -> None:
    """Oxirgi javobni PDF fayl qilib yuboradi.

    Claude fayl yarata olmaydi — PDF shu yerda yig'iladi.
    """
    answer = next(
        (
            item["content"]
            for item in reversed(history.get(message.chat.id))
            if item["role"] == "assistant" and isinstance(item["content"], str)
        ),
        None,
    )
    if not answer:
        await message.answer(texts.NOTHING_TO_EXPORT)
        return

    note = await message.answer(texts.MAKING_PDF)
    try:
        title = pdf.title_of(answer)
        data = pdf.build(answer, title)
    except Exception:
        log.exception("PDF yasab bo'lmadi")
        await _safe_edit(note, texts.PDF_FAILED)
        return

    await message.answer_document(
        BufferedInputFile(data, filename=pdf.filename_of(title)),
        caption=texts.PDF_READY,
    )
    await _safe_edit(note, texts.PDF_SENT)


@router.message(Command("tasks"))
async def cmd_tasks(message: Message, schedule: tasks.TaskStore | None = None) -> None:
    items = schedule.for_chat(message.chat.id) if schedule else []
    await message.answer(
        texts.task_list(items) if items else texts.NO_TASKS,
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("model"))
async def cmd_model(message: Message, history: ChatHistory) -> None:
    await message.answer(
        texts.model_info(
            config.MODEL,
            config.EFFORT,
            len(history.get(message.chat.id)),
            tools.describe(config.TOOLS),
        ),
        parse_mode=ParseMode.HTML,
    )


@router.message(F.text)
async def on_question(
    message: Message,
    bot: Bot,
    claude: ClaudeClient,
    history: ChatHistory,
    limiter: RateLimiter,
    usage: UsageTracker,
    schedule: tasks.TaskStore | None = None,
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

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    placeholder = await message.answer(texts.THINKING)
    await _answer(message, placeholder, claude, history, usage, schedule, question, question)


@router.message(F.photo | F.document)
async def on_media(
    message: Message,
    bot: Bot,
    claude: ClaudeClient,
    history: ChatHistory,
    limiter: RateLimiter,
    usage: UsageTracker,
    schedule: tasks.TaskStore | None = None,
) -> None:
    """Rasm yoki fayl: yuklab olamiz, o'qiymiz, savol bilan birga yuboramiz."""
    user_id = message.from_user.id
    if not config.is_allowed(user_id):
        await message.answer(texts.NOT_ALLOWED)
        return
    if not limiter.allow(user_id):
        await message.answer(texts.rate_limited(config.RATE_LIMIT_PER_MINUTE))
        return

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    placeholder = await message.answer(texts.DOWNLOADING)

    try:
        block, name, default_prompt = await _read_attachment(message, bot, placeholder)
    except _MediaError as exc:
        await _safe_edit(placeholder, str(exc))
        return
    except Exception:
        log.exception("Faylni o'qib bo'lmadi")
        await _safe_edit(placeholder, texts.BROKEN_FILE)
        return

    question = (message.caption or "").strip() or default_prompt
    content = [block, {"type": "text", "text": question}]

    await _safe_edit(placeholder, texts.THINKING)
    await _answer(
        message, placeholder, claude, history, usage, schedule,
        content, f"{texts.media_marker(name)} {question}",
    )


@router.message()
async def on_other(message: Message) -> None:
    """Ovoz, video, stiker — hozircha bularni o'qiy olmaymiz."""
    await message.answer(texts.ONLY_TEXT)


_TASK_TOOLS = {tool["name"] for tool in tasks.TOOLS}


def _run_task_tool(name: str, payload, store, chat_id: int) -> str:
    """Jadval qurollari — sof, tez ishlar, shuning uchun async emas."""
    payload = payload if isinstance(payload, dict) else {}

    if name == tasks.LIST_TOOL["name"]:
        items = store.for_chat(chat_id)
        if not items:
            return "Rejalashtirilgan vazifa yo'q."
        return "\n".join(f"#{task.id} — {task.when} — {task.prompt}" for task in items)

    if name == tasks.CANCEL_TOOL["name"]:
        try:
            task_id = int(payload.get("id"))
        except (TypeError, ValueError):
            raise files.BadInput("`id` butun son bo'lishi kerak.") from None
        if store.remove(chat_id, task_id):
            return f"#{task_id} vazifasi o'chirildi."
        return f"#{task_id} topilmadi — ro'yxatni list_tasks bilan tekshir."

    # schedule_task
    prompt = str(payload.get("prompt") or "").strip()
    if not prompt:
        raise files.BadInput("`prompt` bo'sh bo'lmasin.")
    try:
        hour, minute = tasks.parse_time(payload.get("time"))
        task = store.add(chat_id, prompt, hour, minute, tasks.parse_days(payload.get("days")))
    except ValueError as exc:
        raise files.BadInput(str(exc)) from None
    return f"Qo'shildi: #{task.id} — {task.when}."


class _MediaError(Exception):
    """Foydalanuvchiga aytiladigan, kutilgan xatolik."""


async def _read_attachment(message: Message, bot: Bot, placeholder: Message):
    """Telegram faylini Claude bloki qilib qaytaradi: (blok, nom, savol)."""
    document = message.document
    if message.photo:
        # Telegram bir rasmning bir necha o'lchamini beradi — eng kattasi oxirida.
        photo = message.photo[-1]
        _check_size(photo.file_size)
        data = await _download(bot, photo.file_id)
        return media.image_block(data, "image/jpeg"), "rasm", texts.DEFAULT_IMAGE_PROMPT

    name = document.file_name or "fayl"
    flavour = media.kind(document.mime_type, name)
    if flavour == "unsupported":
        raise _MediaError(texts.UNSUPPORTED_FILE)

    _check_size(document.file_size)
    data = await _download(bot, document.file_id)

    if flavour == "image":
        return media.image_block(data, document.mime_type or ""), name, texts.DEFAULT_IMAGE_PROMPT
    if flavour == "pdf":
        return media.pdf_block(data), name, texts.DEFAULT_FILE_PROMPT

    await _safe_edit(placeholder, texts.READING_FILE)
    if flavour == "text":
        body = data.decode("utf-8", errors="replace")
    elif flavour == "docx":
        body = media.extract_docx(data)
    else:
        body = media.extract_xlsx(data)

    if not body.strip():
        raise _MediaError(texts.EMPTY_FILE)
    return media.text_block(body, name), name, texts.DEFAULT_FILE_PROMPT


def _check_size(size: int | None) -> None:
    if size and size > config.MAX_FILE_MB * 1024 * 1024:
        raise _MediaError(texts.file_too_big(config.MAX_FILE_MB))


async def _download(bot: Bot, file_id: str) -> bytes:
    info = await bot.get_file(file_id)
    buffer = await bot.download_file(info.file_path)
    return buffer.read()


async def _answer(
    message: Message,
    placeholder: Message,
    claude: ClaudeClient,
    history: ChatHistory,
    usage: UsageTracker,
    schedule: tasks.TaskStore | None,
    content,
    marker: str,
) -> None:
    """Savolni Claude'ga yuborib, javobni chatga yetkazadi.

    `content` matn ham, rasm/fayl bloklari ro'yxati ham bo'lishi mumkin;
    `marker` esa tarixda qoladigan qisqa yozuv.
    """
    chat_id = message.chat.id
    conversation = history.get(chat_id) + [{"role": "user", "content": content}]
    progress, status = _progress(placeholder)
    made: list[files.Artifact] = []

    async def on_tool(name: str, payload) -> str:
        """Model so'ragan ishni bajaramiz: fayl yasash yoki jadval bilan ishlash."""
        if name == files.TOOL["name"]:
            if len(made) >= files.MAX_FILES:
                raise files.BadInput("Bitta javobda bunchadan ko'p fayl yasalmaydi.")
            await _safe_edit(placeholder, texts.MAKING_FILE)
            note, artifact = files.run(payload)
            made.append(artifact)
            return note
        if schedule is not None and name in _TASK_TOOLS:
            return _run_task_tool(name, payload, schedule, chat_id)
        raise files.BadInput(f"«{name}» degan qurol yo'q.")

    try:
        reply = await claude.ask(conversation, progress, status, on_tool)
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

    history.add(chat_id, "user", content, marker=marker)
    history.add(chat_id, "assistant", reply.text)

    spent = pricing.cost(reply.model or config.MODEL, reply.input_tokens, reply.output_tokens)
    usage.record(chat_id, spent, reply.input_tokens, reply.output_tokens)

    answer = reply.text
    if reply.truncated:
        answer += "\n\n…(javob uzunlik chegarasiga yetdi — «davom et» deb yozing)"

    await _deliver(
        message, placeholder, answer,
        footer=texts.cost_line(pricing.money(spent)) if config.SHOW_COST and spent else "",
    )
    for artifact in made:
        await message.answer_document(
            BufferedInputFile(artifact.data, filename=artifact.filename)
        )
    log.info(
        "chat=%s tokens in=%s out=%s model=%s narx=%.4f$",
        chat_id, reply.input_tokens, reply.output_tokens, reply.model, spent,
    )


def _progress(placeholder: Message):
    """Oqim davomida xabarni yangilab turadigan ikkita callback.

    Birinchisi yozilayotgan matnni ko'rsatadi, ikkinchisi qurol ishga
    tushganini aytadi — qidiruv paytida matn oqmaydi, ekran esa jim turmasin.
    """
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

    async def status(tool_name: str) -> None:
        note = texts.tool_status(tool_name, config.TOOLS)
        if note == state["text"]:
            return
        state["at"], state["text"] = time.monotonic(), note
        await _safe_edit(placeholder, note)

    return update, status


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


async def _deliver(
    message: Message, placeholder: Message, answer: str, footer: str = "",
) -> None:
    """Javobni bo'laklab yuboradi; HTML o'tmasa — oddiy matn bilan.

    `footer` — tayyor HTML (masalan narx eslatmasi). U faqat oxirgi bo'lakka
    qo'shiladi, shuning uchun uzun javobda ham bir marta ko'rinadi.
    """
    html_chunks = formatting.render(answer)
    plain_chunks = formatting.split_markdown(answer)
    if footer and html_chunks:
        html_chunks[-1] += footer
        plain_chunks[-1] += _strip_tags(footer)

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


def _tick(bot: Bot, claude: ClaudeClient, schedule: tasks.TaskStore):
    """Tashqi ping kelganda kechikkan vazifalarni bajaradigan funksiya."""
    async def tick() -> int:
        return await scheduler.run_due(
            bot, claude, schedule,
            tz_offset=config.TZ_OFFSET, grace_hours=config.TASK_GRACE_HOURS,
        )
    return tick


def _strip_tags(html: str) -> str:
    """HTML o'tmagan holat uchun teglarni olib tashlaydi."""
    return re.sub(r"<[^>]+>", "", html)


async def _set_commands(bot: Bot) -> None:
    """Telegram menyusidagi buyruqlar ro'yxati.

    Fon rejimida chaqiriladi, shuning uchun xatolikni shu yerda yutamiz:
    menyu yozilmagani bot ishlamasligi degani emas.
    """
    try:
        await _send_commands(bot)
    except Exception:
        log.warning("Buyruqlar ro'yxatini yozib bo'lmadi", exc_info=True)


async def _send_commands(bot: Bot) -> None:
    await bot.set_my_commands([
        BotCommand(command="start", description="Boshlash"),
        BotCommand(command="new", description="Suhbatni tozalash"),
        BotCommand(command="pdf", description="Oxirgi javobni PDF qilish"),
        BotCommand(command="cost", description="Qancha sarflandi"),
        BotCommand(command="tasks", description="Rejalashtirilgan vazifalar"),
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
        tool_mode=config.TOOLS,
        max_tool_uses=config.MAX_TOOL_USES,
        client_tools=(
            ([files.TOOL] if config.MAKE_FILES else [])
            + (list(tasks.TOOLS) if config.SCHEDULE_ENABLED else [])
        ),
    )

    schedule = None
    if config.SCHEDULE_ENABLED:
        try:
            schedule = tasks.TaskStore(config.TASKS_DB)
            log.info("Jadval yoqilgan: %s ta vazifa", len(schedule.all()))
        except Exception:
            # Disk yozishga ruxsat bermasligi mumkin. Bu jadvalni o'chiradi,
            # lekin botning o'zini yiqitmasligi kerak — savol-javob muhimroq.
            log.exception("Jadval bazasi ochilmadi — jadvalsiz davom etamiz")

    bot = Bot(token)
    dp = Dispatcher(
        claude=claude,
        history=ChatHistory(config.HISTORY_LIMIT),
        limiter=RateLimiter(config.RATE_LIMIT_PER_MINUTE),
        usage=UsageTracker(),
        schedule=schedule,
    )
    dp.include_router(router)

    clock = None
    if schedule:
        clock = asyncio.create_task(scheduler.loop(
            bot, claude, schedule,
            tz_offset=config.TZ_OFFSET, grace_hours=config.TASK_GRACE_HOURS,
        ))

    try:
        # Buyruqlar ro'yxati — Telegram'ga qilinadigan tarmoq chaqiruvi. U
        # sekinlashsa, port ochilishini kutdirib qo'ymasligi kerak: hosting
        # portni ko'rmasa, deploy «timed out» bo'lib yiqiladi.
        asyncio.create_task(_set_commands(bot))
        log.info(
            "Bot ishga tushdi — model %s, effort %s, qurollar %s",
            config.MODEL, config.EFFORT, config.TOOLS,
        )

        if config.WEBHOOK_URL:
            await webhook.run(
                bot, dp, base_url=config.WEBHOOK_URL, port=config.PORT, token=token,
                on_tick=_tick(bot, claude, schedule) if schedule else None,
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
        if clock:
            clock.cancel()
        if schedule:
            schedule.close()
        await claude.aclose()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    # SystemExit ni ushlamaymiz: token yoki kalit berilmaganda sozlash bo'yicha
    # ko'rsatma ekranda ko'rinishi va exit kodi nolga teng bo'lmasligi kerak.
