"""F7 — Supervisor: decides which specialist agents a question needs.

Returns an ordered plan (1-3 agents). LLM answers in strict JSON; on parse
failure we fall back to the retriever (defense point: graceful degradation).
"""

import json
import sys

import config

SYSTEM = """You route bank-analyst questions to agents. Available:
- retriever: internal documents (definitions, playbooks, product info)
- web: fresh external/internet info, news, trends
- data: SQL over the customers database (counts, averages, segments, churn stats)
- code: pure calculations
Respond in JSON: {"agents": ["..."], "reason": "..."} (1-3 agents, order matters)."""


def run(question: str) -> dict:
    raw = config.llm(f"Route this question: {question}", system=SYSTEM, json_mode=True)
    try:
        plan = json.loads(raw)
        agents = [a for a in plan.get("agents", []) if a in ("retriever", "web", "data", "code")]
        if not agents:
            raise ValueError
        return {"agents": agents[:3], "reason": plan.get("reason", "")}
    except Exception:
        return {"agents": ["retriever"], "reason": "fallback: unparseable routing"}


if __name__ == "__main__":
    print(run(" ".join(sys.argv[1:]) or "how many customers churned last quarter?"))
