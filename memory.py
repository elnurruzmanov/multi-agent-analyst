"""F10 - Long-term memory: JSON store of past Q&A, keyword recall."""

import json
import os
import re

PATH = os.path.join(os.path.dirname(__file__), "memory.json")


def _load() -> list[dict]:
    if os.path.exists(PATH):
        return json.load(open(PATH, encoding="utf-8"))
    return []


def remember(question: str, answer: str) -> None:
    items = _load()
    items.append({"q": question, "a": answer[:500]})
    json.dump(items[-50:], open(PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def recall(question: str, k: int = 2) -> str:
    words = set(re.findall(r"\w+", question.lower()))
    scored = []
    for it in _load():
        overlap = len(words & set(re.findall(r"\w+", it["q"].lower())))
        if overlap >= 2:
            scored.append((overlap, it))
    scored.sort(key=lambda x: -x[0])
    return "\n".join(f"Q: {it['q']}\nA: {it['a']}" for _, it in scored[:k])
