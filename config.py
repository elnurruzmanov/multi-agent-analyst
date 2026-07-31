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
        if any(w in q for w in ["how many", "count", "average", "sql", "necha", "qancha", "eng ko'p"]):
            agent = "data"
        elif any(w in q for w in ["trend", "news", "internet", "web", "yangilik"]):
            agent = "web"
        elif any(w in q for w in ["calculate", "percent", "%", "hisobla"]):
            agent = "code"
        else:
            agent = "retriever"
        return json.dumps({"agents": [agent], "reason": "mock routing"})
    if "review the draft" in text and json_mode:
        return json.dumps({"verdict": "approve", "issues": [], "score": 8})
    if "write sql" in text:
        return "SELECT COUNT(DISTINCT client_id) AS n FROM customers WHERE churned=1;"
    if "python code" in text:
        return "print(round(0.17*340, 2))"
    return "MOCK ANSWER: based on the provided context, churn is driven by declining activity. [mock]"
