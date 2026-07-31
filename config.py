"""F1 — Configuration: API keys, LLM client, embeddings, vector store client.

Design notes (defense talking points):
- One place for all external services; every agent imports from here.
- MOCK_LLM=1 runs the whole system offline (deterministic fake LLM +
  hash-based embeddings) so the graph, DB and UI can be tested with zero
  keys and zero cost. Set a real GEMINI_API_KEY to go live.
- Gemini free tier is used per the course guide; swapping providers only
  requires changing `llm()` here.
"""

import hashlib
import json
import os
import re

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
MOCK = os.getenv("MOCK_LLM", "0") == "1" or not GEMINI_API_KEY

GEN_MODEL = os.getenv("GEN_MODEL", "gemini-2.0-flash")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-004")
EMBED_DIM = 768
QDRANT_PATH = os.path.join(os.path.dirname(__file__), "qdrant_data")
COLLECTION = "bank_docs"

_client = None
_qdrant = None


def qdrant():
    """Shared embedded-Qdrant client (a local path may only be opened once)."""
    global _qdrant
    if _qdrant is None:
        from qdrant_client import QdrantClient
        _qdrant = QdrantClient(path=QDRANT_PATH)
    return _qdrant


def extract_code(text: str) -> str:
    """Pull code out of an LLM reply, handling ``` fences of any language."""
    m = re.search(r"```(?:\w+)?\s*(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


def _genai():
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def llm(prompt: str, system: str = "", json_mode: bool = False) -> str:
    """Single LLM entrypoint used by every agent."""
    if MOCK:
        return _mock_llm(prompt, system, json_mode)
    cfg = {"system_instruction": system} if system else {}
    if json_mode:
        cfg["response_mime_type"] = "application/json"
    resp = _genai().models.generate_content(
        model=GEN_MODEL, contents=prompt, config=cfg or None
    )
    return resp.text or ""


def embed(texts: list[str]) -> list[list[float]]:
    if MOCK:
        return [_mock_embed(t) for t in texts]
    resp = _genai().models.embed_content(model=EMBED_MODEL, contents=texts)
    return [e.values for e in resp.embeddings]


# ---------------- mock implementations (offline mode) ----------------

def _mock_embed(text: str) -> list[float]:
    """Deterministic pseudo-embedding: token hashes -> fixed dim vector."""
    vec = [0.0] * EMBED_DIM
    for tok in re.findall(r"\w+", text.lower()):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        vec[h % EMBED_DIM] += 1.0
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]


def _mock_llm(prompt: str, system: str, json_mode: bool) -> str:
    """Deterministic canned behaviour so the full graph runs offline."""
    text = (system + "\n" + prompt).lower()
    if "route" in text and json_mode:
        q = text.split("route this question:")[-1]
        if any(w in q for w in ["how many", "count", "average", "sql", "necha", "qancha",
                                "eng ko'p", "сколько", "средн", "больше всего"]):
            agent = "data"
        elif any(w in q for w in ["trend", "news", "internet", "web", "yangilik",
                                  "тренд", "новост"]):
            agent = "web"
        elif any(w in q for w in ["calculate", "percent", "%", "hisobla",
                                  "посчита", "вычисли", "процент"]):
            agent = "code"
        else:
            agent = "retriever"
        return json.dumps({"agents": [agent], "reason": "mock routing"})
    if "review the draft" in text and json_mode:
        return json.dumps({"verdict": "approve", "issues": [], "score": 8})
    if "write sql" in text:
        return _mock_sql(prompt.split("for:", 1)[-1].split("\n", 1)[0].lower())
    if "python code" in text:
        return _mock_code(prompt.split("to answer:", 1)[-1].rsplit(".", 1)[0])
    # Structural check, not a phrase from the prompt: draft() and revise() are
    # the only callers that embed the agent outputs, and review() is handled above.
    if "agent outputs:" in prompt.lower():
        return _mock_draft(prompt)
    return "(mock mode) No live model configured for this step."


MOCK_NOTE = ("[Mock mode — no GEMINI_API_KEY is set, so this is a direct summary of what "
             "the agents retrieved rather than a generated answer. Add a free key from "
             "https://aistudio.google.com/apikey to get real analysis.]")

# Offline SQL: map the question to a real aggregate instead of one canned query,
# so the keyless demo answers the common churn questions correctly. A live model
# writes SQL for anything; this covers the dimensions the dashboard exposes.
_RATE = "ROUND(100.0*SUM(churned)/COUNT(*),1) AS churn_rate, COUNT(*) AS customers"
_MOCK_SQL_RULES = [
    (("region", "regionda", "регион", "hudud"),
     f"SELECT region, {_RATE} FROM customers GROUP BY region ORDER BY churn_rate DESC"),
    (("segment", "premium", "retail", "сегмент"),
     f"SELECT segment, {_RATE} FROM customers GROUP BY segment ORDER BY churn_rate DESC"),
    (("platform", "android", "ios", "платформ"),
     f"SELECT platform, {_RATE} FROM customers GROUP BY platform ORDER BY churn_rate DESC"),
    (("age", "yosh", "возраст"),
     f"SELECT age_group, {_RATE} FROM customers GROUP BY age_group ORDER BY churn_rate DESC"),
    (("tenure", "staj", "стаж", "how long"),
     "SELECT CASE WHEN tenure_months<6 THEN '0-5' WHEN tenure_months<12 THEN '6-11' "
     "WHEN tenure_months<24 THEN '12-23' ELSE '24+' END AS tenure, "
     f"{_RATE} FROM customers GROUP BY tenure ORDER BY MIN(tenure_months)"),
    (("failed", "xato", "muvaffaqiyatsiz", "сбой", "неуспеш"),
     f"SELECT failed_tx_total, {_RATE} FROM customers "
     "GROUP BY failed_tx_total ORDER BY failed_tx_total"),
    (("login", "activity", "faollik", "актив", "вход"),
     "SELECT churned, ROUND(AVG(avg_monthly_logins),1) AS avg_logins, "
     "ROUND(AVG(avg_p2p_count),1) AS avg_p2p FROM customers GROUP BY churned"),
    (("ticket", "support", "murojaat", "обращен", "поддержк"),
     "SELECT churned, ROUND(AVG(support_tickets_total),2) AS avg_tickets "
     "FROM customers GROUP BY churned"),
]


_PERCENT_WORDS = ("%", "percent", "foiz", "процент")


def _mock_code(question: str) -> str:
    """Offline stand-in for generated Python: handle percentages and plain arithmetic."""
    nums = [n.replace(",", "") for n in re.findall(r"\d+(?:[.,]\d+)?", question)]
    if len(nums) >= 2 and any(w in question.lower() for w in _PERCENT_WORDS):
        return f"print(round({nums[0]} / 100 * {nums[1]}, 2))"
    expr = re.search(r"\d+(?:\.\d+)?(?:\s*[-+*/]\s*\d+(?:\.\d+)?)+", question)
    if expr:
        return f"print(round({expr.group()}, 4))"
    return f"print({nums[0] if nums else 0})"


def _mock_sql(question: str) -> str:
    for quarter in ("q1-2026", "q2-2026", "q4-2025"):
        if quarter in question:
            return ("SELECT churn_quarter, COUNT(*) AS churned FROM customers "
                    f"WHERE churn_quarter='{quarter.upper()}' GROUP BY churn_quarter")
    if "quarter" in question or "chorak" in question or "квартал" in question:
        return ("SELECT churn_quarter, COUNT(*) AS churned FROM customers "
                "WHERE churned=1 AND churn_quarter<>'' GROUP BY churn_quarter "
                "ORDER BY churned DESC")
    for keywords, sql in _MOCK_SQL_RULES:
        if any(k in question for k in keywords):
            return sql
    return ("SELECT COUNT(*) AS customers, SUM(churned) AS churned, "
            "ROUND(100.0*SUM(churned)/COUNT(*),1) AS churn_rate FROM customers")


def _mock_draft(prompt: str) -> str:
    """Ground the offline answer in the real agent outputs instead of a canned string.

    The draft prompt embeds every agent's output under an "[agent]" heading;
    we re-present the useful part of each so the offline demo still shows the
    database rows and document snippets the agents actually found.
    """
    context = prompt.split("Agent outputs:", 1)[-1].strip()
    parts = []
    for block in context.split("\n\n["):
        block = block.lstrip("[")
        name, _, body = block.partition("]\n")
        body = body.strip()
        if not body:
            continue
        if name == "data":
            sql, _, result = body.partition("Result:")
            parts.append(f"Database — {sql.removeprefix('SQL:').strip()}\n{result.strip()}")
        elif name == "retriever":
            top = body.split("\n---\n")[0]
            head, _, snippet = top.partition("]\n")
            source = head.lstrip("[").split("|")[0].strip()
            parts.append(f"Documents ({source}):\n{snippet.strip()[:400]}")
        elif name == "code":
            _, _, out = body.partition("Output:")
            parts.append(f"Calculation result: {out.strip()}")
        elif name == "memory":
            continue
        else:
            parts.append(f"{name.capitalize()}:\n{body[:400]}")
    return "\n\n".join(parts + [MOCK_NOTE]) if parts else MOCK_NOTE
