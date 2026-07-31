from agents import data_sql, retriever, supervisor


def test_supervisor_routes_count_question_to_data():
    plan = supervisor.run("How many customers churned?")
    assert plan["agents"] == ["data"]


def test_supervisor_falls_back_on_bad_json(monkeypatch):
    import config
    monkeypatch.setattr(config, "llm", lambda *a, **k: "not json at all")
    plan = supervisor.run("anything")
    assert plan["agents"] == ["retriever"]
    assert "fallback" in plan["reason"]


def test_data_agent_answers_count_question():
    out = data_sql.run("How many customers churned?")
    assert out.startswith("SQL:")
    assert "Result:" in out


def test_retriever_returns_scored_documents():
    out = retriever.run("churn ta'rifi nima?")
    assert "score=" in out and ".md" in out
