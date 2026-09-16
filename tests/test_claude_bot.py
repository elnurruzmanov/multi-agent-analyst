"""Claude Telegram boti: formatlash, tarix va API qatlami testlari.

Telegram'ga ham, Anthropic'ga ham chiqmaydi — hammasi lokal.
"""
import pytest

from claude_bot import formatting
from claude_bot.session import ChatHistory, RateLimiter


# --- formatting ------------------------------------------------------------

def test_html_escapes_dangerous_characters():
    html = formatting.to_html("5 < 7 & <script>alert(1)</script>")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "5 &lt; 7 &amp; " in html


def test_markdown_becomes_telegram_html():
    html = formatting.to_html("## Sarlavha\n**qalin** va *egik*\n- birinchi")
    assert "<b>Sarlavha</b>" in html
    assert "<b>qalin</b>" in html
    assert "<i>egik</i>" in html
    assert "• birinchi" in html


def test_code_block_keeps_content_and_drops_language_tag():
    html = formatting.to_html("Mana:\n```python\nprint('a' < 'b')\n```")
    assert "<pre><code>print(&#x27;a&#x27; &lt; &#x27;b&#x27;)</code></pre>" in html
    assert "python" not in html


def test_stars_inside_code_are_not_formatting():
    html = formatting.to_html("`a ** b` matn")
    assert "<code>a ** b</code>" in html
    assert "<b>" not in html


def test_links_become_anchors():
    html = formatting.to_html("[sayt](https://example.com) ochiladi")
    assert '<a href="https://example.com">sayt</a>' in html


def test_short_answer_is_one_chunk():
    assert formatting.split_markdown("qisqa javob") == ["qisqa javob"]


def test_long_answer_is_split_under_the_limit():
    text = "\n".join(f"{index}-satr" for index in range(2000))
    chunks = formatting.split_markdown(text, limit=500)
    assert len(chunks) > 1
    assert all(len(chunk) <= 500 for chunk in chunks)
    # Hech bir satr yo'qolmasligi kerak.
    assert "1999-satr" in "\n".join(chunks)


def test_split_closes_and_reopens_a_code_fence():
    body = "\n".join(f"line_{index}" for index in range(200))
    chunks = formatting.split_markdown(f"```python\n{body}\n```", limit=400)
    assert len(chunks) > 1
    for chunk in chunks:
        # Har bir bo'lakda ``` juft bo'lsin — aks holda HTML buziladi.
        assert chunk.count("```") % 2 == 0
    for chunk in chunks:
        assert "<pre><code>" in formatting.to_html(chunk)


def test_very_long_single_line_is_cut():
    chunks = formatting.split_markdown("x" * 900, limit=300)
    assert [len(chunk) for chunk in chunks] == [300, 300, 300]


def test_render_produces_html_chunks_aligned_with_plain_chunks():
    text = "\n".join(f"{index}. qator" for index in range(500))
    assert len(formatting.render(text, limit=400)) == len(
        formatting.split_markdown(text, limit=400)
    )


# --- tarix va cheklov -------------------------------------------------------

def test_history_keeps_only_the_last_messages():
    history = ChatHistory(limit=4)
    for index in range(5):
        history.add(1, "user", f"savol {index}")
        history.add(1, "assistant", f"javob {index}")

    messages = history.get(1)
    assert len(messages) <= 4
    # API birinchi xabar `user` bo'lishini talab qiladi.
    assert messages[0]["role"] == "user"
    assert messages[-1]["content"] == "javob 4"


def test_history_is_per_chat_and_clearable():
    history = ChatHistory()
    history.add(1, "user", "birinchi chat")
    history.add(2, "user", "ikkinchi chat")
    history.clear(1)
    assert history.get(1) == []
    assert history.get(2)[0]["content"] == "ikkinchi chat"


def test_rate_limiter_blocks_then_recovers():
    limiter = RateLimiter(per_minute=2)
    assert limiter.allow(7, now=0.0)
    assert limiter.allow(7, now=1.0)
    assert not limiter.allow(7, now=2.0)
    assert limiter.allow(8, now=2.0)  # boshqa foydalanuvchiga ta'sir qilmaydi
    assert limiter.allow(7, now=100.0)  # oyna o'tdi


def test_rate_limiter_can_be_disabled():
    limiter = RateLimiter(per_minute=0)
    assert all(limiter.allow(1, now=float(step)) for step in range(50))


# --- Claude qatlami ---------------------------------------------------------

class _Delta:
    def __init__(self, text):
        self.type = "text_delta"
        self.text = text


class _Event:
    """Stream hodisasi: matn bo'lagi yoki qurol ishga tushishi."""

    def __init__(self, type_, delta=None, content_block=None):
        self.type = type_
        self.delta = delta
        self.content_block = content_block

    @staticmethod
    def text(piece):
        return _Event("content_block_delta", delta=_Delta(piece))

    @staticmethod
    def tool(name):
        block = type("Block", (), {"type": "server_tool_use", "name": name})()
        return _Event("content_block_start", content_block=block)


class _FakeStream:
    """anthropic'ning stream helper'iga o'xshab qiladigan soxta obyekt."""

    def __init__(self, pieces, final, events=None):
        # `pieces` — qulaylik uchun: matn bo'laklari hodisaga aylantiriladi.
        self._events = events if events is not None else [
            _Event.text(piece) for piece in pieces
        ]
        self._final = final

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    def __aiter__(self):
        async def generator():
            for event in self._events:
                yield event
        return generator()

    async def get_final_message(self):
        return self._final


class _Block:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _Usage:
    input_tokens = 11
    output_tokens = 22


class _Message:
    def __init__(self, text, stop_reason="end_turn", stop_details=None):
        self.content = [_Block(text)]
        self.stop_reason = stop_reason
        self.stop_details = stop_details
        self.usage = _Usage()
        self.model = "claude-opus-5"


def _client(monkeypatch, stream, captured=None, **options):
    pytest.importorskip("anthropic")
    from claude_bot.claude import ClaudeClient

    client = ClaudeClient(
        "sk-test",
        model="claude-opus-5",
        system="test",
        max_tokens=100,
        effort="low",
        use_fallbacks=False,
        **options,
    )

    def fake_stream(**kwargs):
        if captured is not None:
            captured.update(kwargs)
        return stream

    monkeypatch.setattr(client._client.messages, "stream", fake_stream, raising=False)
    return client


def test_ask_collects_streamed_text_and_reports_progress(monkeypatch):
    import asyncio

    stream = _FakeStream(["Sa", "lom", "!"], _Message("Salom!"))
    client = _client(monkeypatch, stream)

    seen = []

    async def on_progress(partial):
        seen.append(partial)

    async def run():
        return await client.ask([{"role": "user", "content": "hi"}], on_progress)

    reply = asyncio.run(run())
    assert reply.text == "Salom!"
    assert seen == ["Sa", "Salom", "Salom!"]
    assert (reply.input_tokens, reply.output_tokens) == (11, 22)
    assert not reply.truncated


def test_ask_surfaces_a_refusal(monkeypatch):
    import asyncio

    class _Details:
        category = "cyber"
        explanation = "not allowed"

    stream = _FakeStream([], _Message("", stop_reason="refusal", stop_details=_Details()))
    client = _client(monkeypatch, stream)

    reply = asyncio.run(client.ask([{"role": "user", "content": "hi"}]))
    assert reply.stop_reason == "refusal"
    assert reply.refusal == "not allowed"


def test_truncated_answer_is_flagged(monkeypatch):
    import asyncio

    stream = _FakeStream(["uzun"], _Message("uzun", stop_reason="max_tokens"))
    client = _client(monkeypatch, stream)

    reply = asyncio.run(client.ask([{"role": "user", "content": "hi"}]))
    assert reply.truncated


# --- handler mantiqi --------------------------------------------------------

class _StubChat:
    def __init__(self, chat_id):
        self.id = chat_id


class _StubUser:
    def __init__(self, user_id):
        self.id = user_id


class _StubMessage:
    """Telegram xabarining eng kerakli qismi — aiogram'siz."""

    def __init__(self, text="", chat_id=1, user_id=1, outbox=None, edits=None):
        self.text = text
        self.chat = _StubChat(chat_id)
        self.from_user = _StubUser(user_id)
        # Ro'yxatlar «chat» bo'ylab umumiy: placeholder alohida obyekt bo'lsa ham
        # uning tahrirlari shu yerda ko'rinadi.
        self.outbox = outbox if outbox is not None else []
        self.edits = edits if edits is not None else []

    async def answer(self, text, **kwargs):
        self.outbox.append(text)
        return _StubMessage(
            text, self.chat.id, self.from_user.id, self.outbox, self.edits
        )

    async def edit_text(self, text, **kwargs):
        self.edits.append(text)
        self.text = text


class _StubBot:
    def __init__(self):
        self.actions = []

    async def send_chat_action(self, chat_id, action):
        self.actions.append((chat_id, action))


class _StubClaude:
    def __init__(self, reply):
        self.reply = reply
        self.seen = None

    async def ask(self, messages, on_progress=None, on_status=None):
        self.seen = list(messages)
        if on_status is not None:
            await on_status("web_search")
        if on_progress is not None:
            await on_progress(self.reply.text)
        return self.reply


def _run_question(monkeypatch, reply, *, text="Salom", history=None, limiter=None):
    import asyncio

    pytest.importorskip("aiogram")
    from claude_bot import main

    message = _StubMessage(text)
    claude = _StubClaude(reply)
    history = history or ChatHistory()
    asyncio.run(
        main.on_question(
            message,
            bot=_StubBot(),
            claude=claude,
            history=history,
            limiter=limiter or RateLimiter(per_minute=0),
        )
    )
    return message, claude, history


def _reply(text, **kwargs):
    pytest.importorskip("anthropic")
    from claude_bot.claude import Reply

    return Reply(text=text, **kwargs)


def test_question_reaches_claude_and_answer_reaches_the_chat(monkeypatch):
    message, claude, history = _run_question(
        monkeypatch, _reply("**Javob** bu yerda"), text="Savolim"
    )

    assert claude.seen == [{"role": "user", "content": "Savolim"}]
    # Birinchi xabar «o'ylayapman», keyin u javob bilan tahrirlanadi.
    assert message.outbox and message.outbox[0]
    assert "<b>Javob</b> bu yerda" in message.edits[-1]
    assert [item["content"] for item in history.get(1)] == [
        "Savolim",
        "**Javob** bu yerda",
    ]


def test_long_answer_is_delivered_in_several_messages(monkeypatch):
    long_answer = "\n".join(f"{index}-qator" for index in range(2000))
    message, _, _ = _run_question(monkeypatch, _reply(long_answer))

    expected = len(formatting.split_markdown(long_answer))
    assert expected > 1
    # Bittasi «o'ylayapman» xabari, qolganlari — javob bo'laklari.
    assert len(message.outbox) == 1 + (expected - 1)


def test_refusal_is_explained_and_not_remembered(monkeypatch):
    message, _, history = _run_question(
        monkeypatch, _reply("", stop_reason="refusal", refusal="cyber")
    )
    assert "bosh tortdi" in message.edits[-1]
    assert history.get(1) == []


def test_rate_limited_user_is_not_sent_to_claude(monkeypatch):
    limiter = RateLimiter(per_minute=1)
    limiter.allow(1)
    message, claude, _ = _run_question(
        monkeypatch, _reply("javob"), limiter=limiter
    )
    assert claude.seen is None
    assert "sekinroq" in message.outbox[0]


def test_overlong_question_is_rejected(monkeypatch):
    from claude_bot import config

    message, claude, _ = _run_question(
        monkeypatch, _reply("javob"), text="x" * (config.MAX_QUESTION_CHARS + 1)
    )
    assert claude.seen is None
    assert "uzun" in message.outbox[0]


def test_request_carries_thinking_and_effort(monkeypatch):
    import asyncio

    captured = {}
    client = _client(monkeypatch, _FakeStream(["ok"], _Message("ok")), captured)
    asyncio.run(client.ask([{"role": "user", "content": "hi"}]))

    assert captured["thinking"] == {"type": "adaptive"}
    assert captured["output_config"] == {"effort": "low"}
    assert captured["messages"] == [{"role": "user", "content": "hi"}]


def test_thinking_can_be_turned_off_for_older_models(monkeypatch):
    import asyncio

    captured = {}
    client = _client(
        monkeypatch, _FakeStream(["ok"], _Message("ok")), captured, use_thinking=False
    )
    asyncio.run(client.ask([{"role": "user", "content": "hi"}]))

    assert "thinking" not in captured


# --- qurollar ---------------------------------------------------------------

def test_web_mode_offers_search_and_fetch():
    from claude_bot import tools

    kinds = {tool["type"] for tool in tools.build("web", max_uses=3)}
    assert kinds == {tools.WEB_SEARCH, tools.WEB_FETCH}
    assert all(tool["max_uses"] == 3 for tool in tools.build("web", max_uses=3))


def test_code_mode_avoids_two_execution_environments():
    from claude_bot import tools

    kinds = {tool["type"] for tool in tools.build("code")}
    # Yangi qidiruv quroli ichida kod bajarish muhiti bor — kod rejimida
    # qidiruvning oddiy varianti olinadi, aks holda muhit ikkita bo'lib qoladi.
    assert tools.CODE_EXECUTION in kinds
    assert tools.WEB_SEARCH not in kinds
    assert tools.BASIC_WEB_SEARCH in kinds


def test_tools_can_be_turned_off():
    from claude_bot import tools

    assert tools.build("off") == []


def test_request_carries_tools_when_enabled(monkeypatch):
    import asyncio

    captured = {}
    client = _client(
        monkeypatch,
        _FakeStream(["ok"], _Message("ok")),
        captured,
        tool_mode="web",
    )
    asyncio.run(client.ask([{"role": "user", "content": "hi"}]))

    assert [tool["name"] for tool in captured["tools"]] == ["web_search", "web_fetch"]


def test_no_tools_key_when_mode_is_off(monkeypatch):
    import asyncio

    captured = {}
    client = _client(monkeypatch, _FakeStream(["ok"], _Message("ok")), captured)
    asyncio.run(client.ask([{"role": "user", "content": "hi"}]))

    assert "tools" not in captured


def test_search_that_runs_code_still_reads_as_searching():
    from claude_bot import texts

    # Qidiruv quroli natijalarni saralash uchun ichida kod bajaradi — bu
    # foydalanuvchiga «hisoblayapman» bo'lib ko'rinmasligi kerak.
    assert texts.tool_status("code_execution", "web") == texts.TOOL_STATUS["web_search"]
    # `code` rejimida esa hisoblash haqiqatan hisoblash.
    assert texts.tool_status("code_execution", "code") == texts.TOOL_STATUS["code_execution"]
    assert texts.tool_status("web_fetch", "web") == texts.TOOL_STATUS["web_fetch"]


def test_status_callback_fires_when_a_tool_starts(monkeypatch):
    import asyncio

    stream = _FakeStream(
        None,
        _Message("javob"),
        events=[_Event.tool("web_search"), _Event.text("javob")],
    )
    client = _client(monkeypatch, stream, tool_mode="web")

    seen = []

    async def on_status(name):
        seen.append(name)

    asyncio.run(
        client.ask([{"role": "user", "content": "hi"}], None, on_status)
    )
    assert seen == ["web_search"]


def test_paused_turn_is_resumed(monkeypatch):
    import asyncio

    pytest.importorskip("anthropic")
    from claude_bot.claude import ClaudeClient

    client = ClaudeClient(
        "sk-test",
        model="claude-opus-5",
        system="test",
        max_tokens=100,
        effort="low",
        use_fallbacks=False,
        tool_mode="web",
    )

    sent = []
    replies = [
        _FakeStream(["qidiryapman"], _Message("qism", stop_reason="pause_turn")),
        _FakeStream([" va javob"], _Message("to'liq javob")),
    ]

    def fake_stream(**kwargs):
        sent.append(kwargs["messages"])
        return replies[len(sent) - 1]

    monkeypatch.setattr(client._client.messages, "stream", fake_stream, raising=False)

    reply = asyncio.run(client.ask([{"role": "user", "content": "hi"}]))

    assert reply.text == "to'liq javob"
    assert len(sent) == 2
    # Ikkinchi so'rovda birinchi javob assistant xabari sifatida qaytadi.
    assert sent[1][-1]["role"] == "assistant"


# --- webhook rejimi ---------------------------------------------------------

def test_webhook_path_hides_the_token():
    pytest.importorskip("aiogram")
    from claude_bot import webhook

    token = "123456:AAHsupersecret"
    path = webhook.secret_path(token)

    assert path.startswith("/telegram/")
    assert token not in path
    assert "AAHsupersecret" not in path
    # Bir xil token — bir xil manzil (qayta deploy'da o'zgarib ketmasin).
    assert webhook.secret_path(token) == path
    assert webhook.secret_path("boshqa:token") != path


def test_webhook_secret_differs_from_the_path():
    pytest.importorskip("aiogram")
    from claude_bot import webhook

    token = "123456:AAHsupersecret"
    assert token not in webhook.secret_token(token)
    assert webhook.secret_token(token) not in webhook.secret_path(token)


def test_webhook_app_serves_health_and_telegram_routes():
    pytest.importorskip("aiogram")
    from aiogram import Bot, Dispatcher

    from claude_bot import webhook

    bot = Bot("123456:AAHfake-token-for-tests")
    app = webhook.build_app(
        bot, Dispatcher(), path="/telegram/abc", secret="s3cret"
    )
    routes = {
        (route.method, route.resource.canonical) for route in app.router.routes()
    }

    assert ("GET", "/") in routes
    assert ("POST", "/telegram/abc") in routes


def test_friendly_error_maps_known_failures():
    anthropic = pytest.importorskip("anthropic")
    from claude_bot import texts
    from claude_bot.claude import friendly_error

    assert friendly_error(
        anthropic.APIConnectionError(request=None)
    ) == texts.ERR_NETWORK
    assert friendly_error(RuntimeError("?")) == texts.ERR_UNKNOWN
