"""F1 — Shared state passed between graph nodes."""

from typing import TypedDict


class AgentState(TypedDict, total=False):
    question: str
    plan: list[str]          # agents chosen by the supervisor, in order
    route_reason: str
    retriever_out: str
    web_out: str
    data_out: str
    code_out: str
    draft: str
    critic_verdict: str
    critic_issues: list[str]
    answer: str
    steps: list[str]         # human-readable trace for the UI
    memory_context: str
