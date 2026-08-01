import pytest
from fastapi.testclient import TestClient

import api


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(api, "_hits", {})
    return TestClient(api.app)


def test_root_explains_the_service_instead_of_404(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "GET /api/health" in r.json()["endpoints"]


def test_health_reports_mock_mode(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "mock_mode": True}


def test_ask_returns_answer_and_trace(client):
    r = client.post("/api/ask", json={"question": "How many customers churned?"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"]
    assert body["plan"] == ["data"]
    assert any(s.startswith("supervisor") for s in body["steps"])


def test_ask_rejects_empty_and_oversized_questions(client):
    assert client.post("/api/ask", json={"question": ""}).status_code == 422
    assert client.post("/api/ask", json={"question": "x" * 501}).status_code == 422


def test_ask_reports_agent_failure_as_500(client, monkeypatch):
    monkeypatch.setattr(api.graph, "ask", lambda *a, **k: 1 / 0)
    r = client.post("/api/ask", json={"question": "boom"})
    assert r.status_code == 500
    assert "ZeroDivisionError" in r.json()["detail"]


def test_rate_limit_returns_429(client, monkeypatch):
    monkeypatch.setattr(api, "RATE_LIMIT", 2)
    for _ in range(2):
        assert client.post("/api/ask", json={"question": "churn?"}).status_code == 200
    assert client.post("/api/ask", json={"question": "churn?"}).status_code == 429
