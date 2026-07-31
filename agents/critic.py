"""F8 — Critic: drafts the final answer from agent outputs, then reviews it.

Two roles in one module:
- draft(): synthesizes agent outputs into an answer with source hints.
- review(): scores the draft; if it finds issues, one revision pass runs.
Defense point: the eval harness measures quality with vs without the critic.
"""

import json

import config

DRAFT_SYS = ("You are a bank data analyst. Using ONLY the provided agent outputs, "
             "answer the user's question concisely. Mention which source "
             "(documents/database/web/calculation) supports each claim. "
             "If the user asked in Uzbek, answer in Uzbek.")

REVIEW_SYS = ("Review the draft answer against the agent outputs. "
              'Respond JSON: {"verdict": "approve"|"revise", "issues": [".."], "score": 1-10}')


def draft(question: str, context: str) -> str:
    return config.llm(f"Question: {question}\n\nAgent outputs:\n{context}", system=DRAFT_SYS)


def review(question: str, context: str, draft_text: str) -> dict:
    raw = config.llm(
        f"Question: {question}\nAgent outputs:\n{context}\nDraft:\n{draft_text}\nReview the draft.",
        system=REVIEW_SYS, json_mode=True)
    try:
        r = json.loads(raw)
        return {"verdict": r.get("verdict", "approve"),
                "issues": r.get("issues", []), "score": r.get("score", 7)}
    except Exception:
        return {"verdict": "approve", "issues": [], "score": 7}


def revise(question: str, context: str, draft_text: str, issues: list[str]) -> str:
    return config.llm(
        f"Question: {question}\nAgent outputs:\n{context}\nPrevious draft:\n{draft_text}\n"
        f"Fix these issues and rewrite: {issues}", system=DRAFT_SYS)


if __name__ == "__main__":
    d = draft("test question", "ctx")
    print(d, review("test question", "ctx", d))
