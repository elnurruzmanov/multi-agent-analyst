# Bank Multi-Agent AI Analyst

[![CI](https://github.com/elnurruzmanov/multi-agent-analyst/actions/workflows/ci.yml/badge.svg)](https://github.com/elnurruzmanov/multi-agent-analyst/actions/workflows/ci.yml)

Multi-agent AI Analyst capstone (F1–F14) — **written from scratch**, with a
banking twist: the analyst answers questions about **digital-banking churn**.
The SQL agent queries a synthetic SQB-style customers database and the
retriever searches internal churn/retention documents (in Uzbek). Questions
can be asked in English or Uzbek.

Author: Elnur Ruzmanov.

## Architecture

```
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

Key safety choices (defense points):
- **SQL guard** — single SELECT only; INSERT/UPDATE/DROP/PRAGMA etc. rejected
  before execution.
- **Code sandbox** — separate subprocess, 5s timeout, denylist for os/net/file
  imports.
- **Graceful degradation** — unparseable routing falls back to the retriever;
  web agent skips politely without a Tavily key.
- **MOCK mode** — `MOCK_LLM=1` runs the entire graph offline with a
  deterministic fake LLM: free to test, reproducible in CI.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # paste your free Gemini key (aistudio.google.com/apikey)

python db/init_db.py        # sample bank database (1,000 customers)
python ingestion.py         # F2: chunk + embed docs into embedded Qdrant
```

## Test each phase (matches the course phases)

```bash
python -m agents.retriever "why are customers churning?"    # F3
python -m agents.web "digital banking churn trends"         # F4
python -m agents.data_sql "how many customers churned?"     # F5
python -m agents.code_agent "what is 17% of 340?"           # F6
python -m agents.supervisor "how many churned last quarter?"# F7
python graph.py "How many customers churned in Q1-2026, and why?"  # F9 end-to-end

python -m evaluation.eval               # F11 (routing + judge), critic ON
python -m evaluation.eval --no-critic   # ablation table
python app_gradio.py                    # F13/F14 UI with live trace
```

## Tests & CI

```bash
pip install pytest
MOCK_LLM=1 pytest -q
```

12 tests cover the SQL guard, the code-sandbox denylist, supervisor routing
and its JSON-failure fallback, chunking, memory recall, and the full graph
end-to-end (mock mode, no keys needed). GitHub Actions runs the same suite
on every push (`.github/workflows/ci.yml`).

Offline demo without any keys: prefix commands with `MOCK_LLM=1`.

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
