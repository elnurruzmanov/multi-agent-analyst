"""F9 — Graph: LangGraph wiring of supervisor -> specialists -> critic.

Flow: supervisor plans -> chosen specialist nodes run in plan order ->
critic drafts + reviews (one revision max) -> final answer. Every node
appends to `steps` so the UI can show a live trace. F10: a small long-term
memory stores past Q&A and is injected into drafting context.
"""

import sys

from langgraph.graph import END, StateGraph

import memory
from agents import code_agent, critic, data_sql, retriever, supervisor, web
from state import AgentState


def node_supervisor(s: AgentState) -> AgentState:
    plan = supervisor.run(s["question"])
    steps = s.get("steps", []) + [f"supervisor -> {plan['agents']} ({plan['reason']})"]
    return {**s, "plan": plan["agents"], "route_reason": plan["reason"], "steps": steps}


def _specialist(name, fn, key):
    def node(s: AgentState) -> AgentState:
        out = fn(s["question"])
        return {**s, key: out, "steps": s["steps"] + [f"{name}: done ({len(out)} chars)"]}
    return node


def node_critic(s: AgentState) -> AgentState:
    ctx_parts = [f"[{k.removesuffix('_out')}]\n{v}" for k, v in s.items()
                 if k.endswith("_out") and v]
    mem = memory.recall(s["question"])
    if mem:
        ctx_parts.append(f"[memory]\n{mem}")
    ctx = "\n\n".join(ctx_parts) or "(no agent output)"
    d = critic.draft(s["question"], ctx)
    r = critic.review(s["question"], ctx, d)
    steps = s["steps"] + [f"critic: draft -> {r['verdict']} (score {r['score']})"]
    if r["verdict"] == "revise" and r["issues"]:
        d = critic.revise(s["question"], ctx, d, r["issues"])
        steps.append("critic: revised once")
    memory.remember(s["question"], d)
    return {**s, "draft": d, "critic_verdict": r["verdict"],
            "critic_issues": r["issues"], "answer": d, "steps": steps}


def build_graph(use_critic: bool = True):
    g = StateGraph(AgentState)
    g.add_node("supervisor", node_supervisor)
    g.add_node("retriever", _specialist("retriever", retriever.run, "retriever_out"))
    g.add_node("web", _specialist("web", web.run, "web_out"))
    g.add_node("data", _specialist("data", data_sql.run, "data_out"))
    g.add_node("code", _specialist("code", code_agent.run, "code_out"))

    if use_critic:
        g.add_node("critic", node_critic)

    g.set_entry_point("supervisor")

    def route(s: AgentState):
        # run agents sequentially in plan order via conditional hops
        done = [st.split(":")[0] for st in s["steps"]]
        for a in s["plan"]:
            if a not in done:
                return a
        return "critic" if use_critic else END

    for src in ["supervisor", "retriever", "web", "data", "code"]:
        g.add_conditional_edges(src, route)
    if use_critic:
        g.add_edge("critic", END)
    return g.compile()


def ask(question: str, use_critic: bool = True) -> AgentState:
    app = build_graph(use_critic)
    if not use_critic:
        # simple draft without review for the eval ablation
        s = app.invoke({"question": question, "steps": []})
        ctx = "\n\n".join(v for k, v in s.items() if k.endswith("_out") and v)
        s["answer"] = critic.draft(question, ctx or "(no agent output)")
        return s
    return app.invoke({"question": question, "steps": []})


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "How many customers churned in Q1-2026, and why?"
    result = ask(q)
    print("\n".join(result["steps"]))
    print("\n=== ANSWER ===\n" + result["answer"])
