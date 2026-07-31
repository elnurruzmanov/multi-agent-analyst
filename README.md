# Bank Multi-Agent AI Analyst

[![CI](https://github.com/elnurruzmanov/multi-agent-analyst/actions/workflows/ci.yml/badge.svg)](https://github.com/elnurruzmanov/multi-agent-analyst/actions/workflows/ci.yml)

Multi-agent AI analyst capstone (F1–F14) — **written from scratch**, with a
banking twist: the analyst answers questions about **digital-banking churn**.
The SQL agent queries a synthetic SQB-style customers database and the
retriever searches internal churn/retention documents. The interface is
available in **Uzbek, Russian and English**, and the analyst replies in
whichever language the question was asked in.

Author: Elnur Ruzmanov.

## Architecture

```
frontend/ (Vercel)  ── /api ─►  api.py (Render, FastAPI)
  dashboard + chat                 │
                                   ├─► analytics.py — fixed SQL aggregates
                                   │
                                   └─► graph.py — LangGraph pipeline:
question
   │
supervisor (F7) ── plans 1-3 agents ──► retriever (F3, Qdrant RAG)
   │                                    web       (F4, Tavily, optional)
   │                                    data      (F5, NL→read-only SQL)
   │                                    code      (F6, sandboxed python)
   ▼
critic (F8): draft → review → (revise once) → final answer
memory (F10) feeds past Q&A into drafting; every node logs a trace step.
```

The dashboard and the agent answer the same questions from the same database
on purpose: `analytics.py` runs fixed, deterministic SQL, so its numbers are
the ground truth you can check the agent's generated SQL against.

Key safety choices (defense points):
- **SQL guard** — single SELECT only; INSERT/UPDATE/DROP/PRAGMA etc. rejected
  before execution.
- **Code sandbox** — separate isolated subprocess, 5s timeout, denylist for
  os/net/file/eval imports.
- **API guard** — 500-char question cap and a per-IP rate limit, so a public
  demo cannot run up the model bill.
- **Graceful degradation** — unparseable routing falls back to the retriever;
  the web agent skips politely without a Tavily key; a missing database or
  document index returns an explanation instead of a stack trace.
- **MOCK mode** — runs the entire graph offline with no key at all.

## Mock mode vs live answers

Without `GEMINI_API_KEY` the app runs in **mock mode**. That is a real demo,
not a placeholder: the router, the SQL writer and the calculator all follow
the question, so "qaysi regionda churn eng ko'p?" really does return Farg'ona
at 27.3%. What mock mode cannot do is *write* — it summarises what the agents
retrieved instead of composing an answer, and it only covers the dimensions
the dashboard exposes.

**For fluent answers to arbitrary questions, add a free Gemini key:**

1. Get one at <https://aistudio.google.com/apikey> (free tier, no card).
2. Locally: `cp .env.example .env` and paste it after `GEMINI_API_KEY=`.
3. On Render: dashboard → your service → *Environment* → add `GEMINI_API_KEY`.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # paste your free Gemini key

python db/init_db.py        # sample bank database (1,000 customers)
python ingestion.py         # F2: chunk + embed docs into embedded Qdrant
```

Run the backend and the frontend together:

```bash
python -m uvicorn api:app --reload --port 8000
```

```bash
python -m http.server 5500 --directory frontend
```

Then open `http://localhost:5500/?api=http://localhost:8000`.

> Embedded Qdrant allows only **one** process to hold `qdrant_data/` at a time.
> Stop the backend before running the tests, or they will fail on a storage lock.

## Test each phase (matches the course phases)

```bash
python -m agents.retriever "why are customers churning?"    # F3
python -m agents.web "digital banking churn trends"         # F4
python -m agents.data_sql "how many customers churned?"     # F5
python -m agents.code_agent "what is 17% of 340?"           # F6
python -m agents.supervisor "how many churned last quarter?"# F7
python graph.py "How many customers churned in Q1-2026, and why?"  # F9 end-to-end
python analytics.py                     # dashboard aggregates as JSON

python -m evaluation.eval               # F11 (routing + judge), critic ON
python -m evaluation.eval --no-critic   # ablation table
pip install -r requirements-ui.txt && python app_gradio.py   # F13 Gradio UI
```

## Tests & CI

```bash
pip install pytest
MOCK_LLM=1 pytest -q
```

29 tests cover the SQL guard, the code-sandbox denylist, supervisor routing and
its JSON-failure fallback, the mock-mode answer paths, chunking, memory recall,
the analytics aggregates, the HTTP API (validation, rate limiting, error
handling) and the full graph end-to-end — all offline, no keys needed. GitHub
Actions runs the same suite on every push.

## Deploy

**Backend → Render.** New → *Blueprint*, pick this repo; `render.yaml` defines
the service, rebuilds the database and the Qdrant index at build time (Render's
free filesystem is ephemeral) and health-checks `/api/health`.

**Frontend → Vercel.** Import the repo; `vercel.json` serves `frontend/` and
rewrites `/api/*` to the Render service, so the browser only ever talks to one
origin and there is no CORS to configure. Update the destination host in
`vercel.json` if your Render service gets a different name.

Free-tier Render services sleep when idle, so the first request after a quiet
period takes about 50 seconds — the UI says so while it waits.

## Evaluation snapshot (mock mode)

| run | routing | judge avg |
|---|---|---|
| critic ON | 10/10 | see eval_results.csv |
| critic OFF | 10/10 | see eval_results_no_critic.csv |

Re-run with a real Gemini key for the submission numbers, then do the error
analysis: pick the 3 lowest judge_score rows and trace which agent failed.

## Why this project is mine

The domain is my real work: I run a churn-prediction initiative for a bank
mobile app (SQB Mobile). The sample database mirrors my synthetic churn
dataset, and the retriever documents are my project's churn definition and
retention playbook. The analyst is the natural next layer on top of that work.
