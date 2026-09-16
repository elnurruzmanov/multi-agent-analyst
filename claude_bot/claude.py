"""Claude API bilan ishlaydigan yupqa qatlam.

Javob oqim (streaming) bilan olinadi: uzun javoblarda HTTP timeout'ga
tushmaslik uchun va foydalanuvchiga yozilayotgan matnni jonli ko'rsata olish
uchun.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, Sequence

import anthropic

from claude_bot import texts, tools as tool_defs

log = logging.getLogger("claude-bot.api")

# Claude javob berishdan bosh tortsa, so'rov o'sha chaqiruv ichida boshqa
# modelga o'tadi. Beta bayrog'i eskirsa ham bot ishlab turishi kerak, shuning
# uchun quyida birinchi 400 xatoligida undan voz kechamiz.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

# Qurol ishlatganda Claude javobni «pauza» qilib qo'yishi mumkin — davom
# ettirish bizning zimmamizda. Cheksiz aylanmaslik uchun chegara.
MAX_TURNS = 8

Progress = Callable[[str], Awaitable[None]]
# Qurol ishga tushganda chaqiriladi: «qidiryapman», «hisoblayapman».
Status = Callable[[str], Awaitable[None]]


@dataclass
class Reply:
    """Claude javobi — botga kerakli holatda."""

    text: str
    stop_reason: str | None = None
    refusal: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""

    @property
    def truncated(self) -> bool:
        return self.stop_reason == "max_tokens"


class ClaudeClient:
    def __init__(
        self,
        api_key: str,
        *,
        model: str,
        system: str,
        max_tokens: int,
        effort: str,
        use_fallbacks: bool = True,
        use_thinking: bool = True,
        tool_mode: str = "off",
        max_tool_uses: int = tool_defs.DEFAULT_MAX_USES,
    ) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model
        self.system = system
        self.max_tokens = max_tokens
        self.effort = effort
        self.use_thinking = use_thinking
        self.tool_mode = tool_mode
        self.tools = tool_defs.build(tool_mode, max_tool_uses)
        self._use_fallbacks = use_fallbacks

    async def ask(
        self,
        messages: Sequence[dict[str, str]],
        on_progress: Progress | None = None,
        on_status: Status | None = None,
    ) -> Reply:
        """Suhbat tarixini yuborib, to'liq javobni qaytaradi.

        Qurol ishlatilganda Claude `pause_turn` bilan to'xtashi mumkin — bu
        «men hali tugatmadim» degani, javobni davom ettirish uchun turgan
        joyidan qayta so'raymiz.
        """
        conversation = list(messages)
        final = await self._stream(conversation, on_progress, on_status)

        for _ in range(MAX_TURNS - 1):
            if final.stop_reason != "pause_turn":
                break
            conversation.append({"role": "assistant", "content": final.content})
            final = await self._stream(conversation, on_progress, on_status)

        text = "".join(
            block.text for block in final.content if block.type == "text"
        ).strip()

        refusal = None
        if final.stop_reason == "refusal":
            details = getattr(final, "stop_details", None)
            refusal = getattr(details, "explanation", None) or getattr(
                details, "category", None
            )

        return Reply(
            text=text,
            stop_reason=final.stop_reason,
            refusal=refusal,
            input_tokens=final.usage.input_tokens,
            output_tokens=final.usage.output_tokens,
            model=final.model,
        )

    async def aclose(self) -> None:
        await self._client.close()

    async def _stream(
        self,
        messages: list[dict],
        on_progress: Progress | None,
        on_status: Status | None = None,
    ):
        kwargs = dict(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system,
            messages=messages,
            output_config={"effort": self.effort},
        )
        if self.use_thinking:
            kwargs["thinking"] = {"type": "adaptive"}
        if self.tools:
            kwargs["tools"] = self.tools

        if self._use_fallbacks:
            try:
                return await self._consume(
                    self._client.beta.messages.stream(
                        betas=[FALLBACK_BETA], fallbacks="default", **kwargs
                    ),
                    on_progress,
                    on_status,
                )
            except (anthropic.BadRequestError, TypeError) as exc:
                # Beta bayrog'i yoki SDK versiyasi mos kelmadi — bu javobni
                # yo'qotish uchun sabab emas, oddiy so'rov bilan davom etamiz.
                self._use_fallbacks = False
                log.warning("Server fallback o'chirildi: %s", exc)

        return await self._consume(
            self._client.messages.stream(**kwargs), on_progress, on_status
        )

    @staticmethod
    async def _consume(
        stream_context,
        on_progress: Progress | None,
        on_status: Status | None = None,
    ):
        buffer: list[str] = []
        async with stream_context as stream:
            async for event in stream:
                if event.type == "content_block_start":
                    block = event.content_block
                    # Qurol ishga tushdi — foydalanuvchi kutib turganini
                    # bilsin, chunki qidiruv paytida matn oqmaydi.
                    if block.type in ("server_tool_use", "mcp_tool_use") and on_status:
                        await on_status(getattr(block, "name", ""))
                elif event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        buffer.append(event.delta.text)
                        if on_progress is not None:
                            await on_progress("".join(buffer))
            return await stream.get_final_message()


def friendly_error(exc: Exception) -> str:
    """Istisnoni foydalanuvchi tushunadigan bitta jumlaga aylantiradi."""
    if isinstance(exc, anthropic.AuthenticationError):
        return texts.ERR_AUTH
    if isinstance(exc, anthropic.PermissionDeniedError):
        return texts.ERR_CREDIT
    if isinstance(exc, anthropic.RateLimitError):
        return texts.ERR_RATE
    if isinstance(exc, anthropic.APITimeoutError):
        return texts.ERR_TIMEOUT
    if isinstance(exc, anthropic.BadRequestError):
        return texts.ERR_BAD_REQUEST
    if isinstance(exc, anthropic.APIStatusError):
        return texts.ERR_SERVER if exc.status_code >= 500 else texts.ERR_UNKNOWN
    if isinstance(exc, anthropic.APIConnectionError):
        return texts.ERR_NETWORK
    return texts.ERR_UNKNOWN
