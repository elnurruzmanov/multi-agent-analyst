"""HTTP backend: exposes the multi-agent graph as a JSON API.

Deployed on Render; the static frontend (Vercel) talks to it over /api.
The graph is run under a lock because embedded Qdrant and SQLite are not
safe to use from several threads at once, and FastAPI runs sync routes in
a threadpool.
"""

import os
import threading
import time
from collections import deque
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import analytics
import config
import graph

MAX_QUESTION_CHARS = 500
RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))

app = FastAPI(title="Bank Multi-Agent AI Analyst", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_graph_lock = threading.Lock()
_hits: dict[str, deque] = {}
_hits_lock = threading.Lock()


def _rate_limited(client: str) -> bool:
    """Allow RATE_LIMIT questions per client per minute (public demo guard)."""
    now = time.monotonic()
    with _hits_lock:
        q = _hits.setdefault(client, deque())
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= RATE_LIMIT:
            return True
        q.append(now)
        return False


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)
    use_critic: bool = True


class AskResponse(BaseModel):
    answer: str
    plan: list[str]
    route_reason: str
    steps: list[str]
    critic_verdict: str


@app.get("/")
def root() -> dict:
    """Opening the bare host in a browser should explain itself, not 404."""
    return {
        "service": "Bank Multi-Agent AI Analyst API",
        "frontend": "https://multi-agent-analyst-nine.vercel.app",
        "endpoints": ["GET /api/health", "GET /api/stats", "POST /api/ask", "GET /docs"],
    }


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "mock_mode": config.MOCK}


@app.get("/api/stats")
def stats() -> dict:
    """Deterministic churn aggregates for the dashboard (cached — data is static)."""
    try:
        return _cached_stats()
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))


@lru_cache(maxsize=1)
def _cached_stats() -> dict:
    return analytics.snapshot()


@app.post("/api/ask", response_model=AskResponse)
def ask(req: AskRequest, request: Request) -> AskResponse:
    client = request.client.host if request.client else "unknown"
    if _rate_limited(client):
        raise HTTPException(429, f"Rate limit reached ({RATE_LIMIT}/min). Try again shortly.")
    with _graph_lock:
        try:
            s = graph.ask(req.question, use_critic=req.use_critic)
        except Exception as e:
            raise HTTPException(500, f"Agent run failed: {type(e).__name__}: {e}")
    return AskResponse(
        answer=s.get("answer", ""),
        plan=s.get("plan", []),
        route_reason=s.get("route_reason", ""),
        steps=s.get("steps", []),
        critic_verdict=s.get("critic_verdict", ""),
    )
