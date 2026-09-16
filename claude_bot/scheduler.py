"""Vaqti kelgan vazifalarni bajarish.

Ikki yo'l bilan ishga tushadi va ikkalasi ham kerak:

* **ichki soat** — bot uyg'oq bo'lganda har daqiqada tekshiradi;
* **tashqi turtki** — `/tasks/run` manzili. Bepul hostingda servis uxlab
  qoladi va uxlagan servisning ichki soati ham to'xtaydi; tashqi ping
  xizmati (masalan cron-job.org) shu manzilni chaqirsa, servis uyg'onadi
  va o'sha zahoti kechikkan vazifalarni bajaradi.

Shu sababli `is_due` kechikishga chidamli: 8:00 lik vazifa servis 8:40 da
uyg'onsa ham bajariladi.
"""
from __future__ import annotations

import asyncio
import logging

from claude_bot import formatting, tasks as task_lib, texts
from claude_bot.claude import friendly_error

log = logging.getLogger("claude-bot.scheduler")

CHECK_INTERVAL = 60.0


async def run_due(bot, claude, store, *, tz_offset: float, grace_hours: float) -> int:
    """Vaqti kelgan vazifalarni bajaradi va nechtasini bajarganini qaytaradi."""
    now = task_lib.local_now(tz_offset)
    due = store.due(now, grace_hours)
    for task in due:
        # Belgilashni oldin qilamiz: javob berishda xato chiqsa ham vazifa
        # takror-takror ishlab, hisobni bo'shatmasin.
        store.mark_run(task.id, now.date())
        await _run_one(bot, claude, task)
    return len(due)


async def _run_one(bot, claude, task) -> None:
    log.info("Vazifa bajarilyapti: chat=%s id=%s", task.chat_id, task.id)
    try:
        reply = await claude.ask([{"role": "user", "content": task.prompt}])
        body = reply.text or texts.EMPTY_ANSWER
    except Exception as exc:
        log.exception("Vazifa bajarilmadi")
        body = friendly_error(exc)

    header = texts.task_header(task.prompt)
    chunks = formatting.render(body)
    try:
        await bot.send_message(task.chat_id, header, parse_mode="HTML")
        for chunk in chunks:
            await bot.send_message(
                task.chat_id, chunk, parse_mode="HTML", disable_web_page_preview=True
            )
    except Exception:
        log.exception("Vazifa javobini yuborib bo'lmadi")


async def loop(bot, claude, store, *, tz_offset: float, grace_hours: float) -> None:
    """Bot uyg'oq bo'lganda ishlaydigan ichki soat."""
    while True:
        try:
            await run_due(bot, claude, store, tz_offset=tz_offset, grace_hours=grace_hours)
        except Exception:
            # Bitta xato soatni to'xtatib qo'ymasin.
            log.exception("Jadval tekshiruvida xato")
        await asyncio.sleep(CHECK_INTERVAL)
