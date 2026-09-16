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

    def __init__(self, text="", chat_id=1, user_id=1, outbox=None, edits=None,
                 photo=None, document=None, caption=None):
        self.text = text
        self.photo = photo
        self.document = document
        self.caption = caption
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
    def __init__(self, payload=b""):
        self.actions = []
        self.payload = payload

    async def send_chat_action(self, chat_id, action):
        self.actions.append((chat_id, action))

    async def get_file(self, file_id):
        return type("Info", (), {"file_path": f"files/{file_id}"})()

    async def download_file(self, path):
        import io
        return io.BytesIO(self.payload)


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


# --- rasm va fayl -----------------------------------------------------------

def test_kind_recognises_what_we_can_read():
    from claude_bot import media

    assert media.kind("image/png", "a.png") == "image"
    assert media.kind("application/pdf", "hisobot.pdf") == "pdf"
    assert media.kind("text/csv", "data.csv") == "text"
    assert media.kind(media.DOCX_TYPE, "shartnoma.docx") == "docx"
    assert media.kind(media.XLSX_TYPE, "byudjet.xlsx") == "xlsx"
    assert media.kind("video/mp4", "klip.mp4") == "unsupported"


def test_kind_falls_back_to_the_file_name():
    from claude_bot import media

    # Telegram mime bermasligi mumkin — kengaytma bo'yicha topamiz.
    assert media.kind(None, "hisobot.docx") == "docx"
    assert media.kind("", "eslatma.txt") == "text"
    assert media.kind("application/octet-stream", "jadval.xlsx") == "xlsx"


def test_image_block_is_base64_with_media_type():
    import base64

    from claude_bot import media

    block = media.image_block(b"\x89PNG-fake", "image/png")
    assert block["type"] == "image"
    assert block["source"]["media_type"] == "image/png"
    assert base64.standard_b64decode(block["source"]["data"]) == b"\x89PNG-fake"


def test_unknown_image_type_falls_back_to_jpeg():
    from claude_bot import media

    block = media.image_block(b"data", "image/heic")
    assert block["source"]["media_type"] == "image/jpeg"


def test_pdf_becomes_a_document_block():
    from claude_bot import media

    block = media.pdf_block(b"%PDF-1.4")
    assert block["type"] == "document"
    assert block["source"]["media_type"] == media.PDF_TYPE


def test_long_text_file_is_clipped_and_says_so():
    from claude_bot import media

    block = media.text_block("x" * (media.MAX_TEXT_CHARS + 500), "katta.txt")
    assert "katta.txt" in block["text"]
    assert "qisqartirildi" in block["text"]
    assert len(block["text"]) < media.MAX_TEXT_CHARS + 500


def test_word_document_text_is_extracted():
    docx = pytest.importorskip("docx")
    import io

    from claude_bot import media

    document = docx.Document()
    document.add_paragraph("Shartnoma raqami 42")
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Summa"
    table.rows[0].cells[1].text = "1000"
    buffer = io.BytesIO()
    document.save(buffer)

    body = media.extract_docx(buffer.getvalue())
    assert "Shartnoma raqami 42" in body
    assert "Summa | 1000" in body


def test_excel_sheet_text_is_extracted():
    openpyxl = pytest.importorskip("openpyxl")
    import io

    from claude_bot import media

    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Byudjet"
    sheet.append(["Oy", "Xarajat"])
    sheet.append(["Yanvar", 1500])
    buffer = io.BytesIO()
    book.save(buffer)

    body = media.extract_xlsx(buffer.getvalue())
    assert "## Varaq: Byudjet" in body
    assert "Yanvar\t1500" in body


def test_only_the_newest_file_stays_in_context():
    history = ChatHistory()
    first = [{"type": "image", "source": {"data": "aaa"}}]
    second = [{"type": "image", "source": {"data": "bbb"}}]

    history.add(1, "user", first, marker="[rasm-1 yuborildi]")
    history.add(1, "assistant", "birinchi javob")
    history.add(1, "user", second, marker="[rasm-2 yuborildi]")

    messages = history.get(1)
    # Eski rasm o'z belgisiga almashdi, yangisi bloklarcha turibdi.
    assert messages[0]["content"] == "[rasm-1 yuborildi]"
    assert messages[2]["content"] == second


def test_plain_text_history_is_untouched_by_markers():
    history = ChatHistory()
    history.add(1, "user", "oddiy savol")
    history.add(1, "assistant", "javob")
    history.add(1, "user", "yana savol")

    assert [item["content"] for item in history.get(1)] == [
        "oddiy savol", "javob", "yana savol",
    ]


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


# --- rasm/fayl handler'i ----------------------------------------------------

def _run_media(reply, message, payload=b"", history=None):
    import asyncio

    pytest.importorskip("aiogram")
    from claude_bot import main

    claude = _StubClaude(reply)
    history = history or ChatHistory()
    asyncio.run(
        main.on_media(
            message,
            bot=_StubBot(payload),
            claude=claude,
            history=history,
            limiter=RateLimiter(per_minute=0),
        )
    )
    return claude, history


def test_photo_reaches_claude_as_an_image_with_the_caption():
    photo = [type("Size", (), {"file_id": "abc", "file_size": 1024})()]
    message = _StubMessage(photo=photo, caption="Bu jadvalda xato bormi?")

    claude, history = _run_media(_reply("Xato yo'q"), message, payload=b"jpeg-bytes")

    content = claude.seen[-1]["content"]
    assert content[0]["type"] == "image"
    assert content[1]["text"] == "Bu jadvalda xato bormi?"
    # Tarixda rasm emas, uning belgisi qoladi — keyingi savollar arzon bo'lsin.
    assert "yuborildi" in history.get(1)[0]["content"]


def test_photo_without_a_caption_gets_a_default_question():
    from claude_bot import texts

    photo = [type("Size", (), {"file_id": "abc", "file_size": 10})()]
    message = _StubMessage(photo=photo)

    claude, _ = _run_media(_reply("javob"), message, payload=b"x")

    assert claude.seen[-1]["content"][1]["text"] == texts.DEFAULT_IMAGE_PROMPT


def test_pdf_document_becomes_a_document_block():
    document = type("Doc", (), {
        "file_id": "f1", "file_size": 2048,
        "file_name": "hisobot.pdf", "mime_type": "application/pdf",
    })()
    message = _StubMessage(document=document, caption="Xulosa qil")

    claude, _ = _run_media(_reply("xulosa"), message, payload=b"%PDF-1.4")

    assert claude.seen[-1]["content"][0]["type"] == "document"


def test_unsupported_file_is_refused_before_any_download():
    from claude_bot import texts

    document = type("Doc", (), {
        "file_id": "f2", "file_size": 100,
        "file_name": "klip.mp4", "mime_type": "video/mp4",
    })()
    message = _StubMessage(document=document)

    claude, _ = _run_media(_reply("javob"), message)

    assert claude.seen is None
    assert texts.UNSUPPORTED_FILE in message.edits[-1]


def test_oversized_file_is_refused():
    from claude_bot import config

    document = type("Doc", (), {
        "file_id": "f3", "file_size": (config.MAX_FILE_MB + 1) * 1024 * 1024,
        "file_name": "katta.pdf", "mime_type": "application/pdf",
    })()
    message = _StubMessage(document=document)

    claude, _ = _run_media(_reply("javob"), message)

    assert claude.seen is None
    assert "katta" in message.edits[-1]


def test_empty_text_file_is_explained():
    from claude_bot import texts

    document = type("Doc", (), {
        "file_id": "f4", "file_size": 3,
        "file_name": "bosh.txt", "mime_type": "text/plain",
    })()
    message = _StubMessage(document=document)

    claude, _ = _run_media(_reply("javob"), message, payload=b"   ")

    assert claude.seen is None
    assert message.edits[-1] == texts.EMPTY_FILE


def test_friendly_error_maps_known_failures():
    anthropic = pytest.importorskip("anthropic")
    from claude_bot import texts
    from claude_bot.claude import friendly_error

    assert friendly_error(
        anthropic.APIConnectionError(request=None)
    ) == texts.ERR_NETWORK
    assert friendly_error(RuntimeError("?")) == texts.ERR_UNKNOWN
