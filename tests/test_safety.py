from agents import code_agent, data_sql


def test_sql_guard_allows_single_select():
    assert data_sql.safe("SELECT COUNT(*) FROM customers")
    assert data_sql.safe("select region from customers where churned=1;")


def test_sql_guard_rejects_writes_and_multi_statements():
    assert not data_sql.safe("DROP TABLE customers")
    assert not data_sql.safe("SELECT 1; DELETE FROM customers")
    assert not data_sql.safe("UPDATE customers SET churned=0")
    assert not data_sql.safe("PRAGMA table_info(customers)")
    assert not data_sql.safe("INSERT INTO customers VALUES (1)")


def test_code_denylist_blocks_dangerous_code(monkeypatch):
    import config
    monkeypatch.setattr(config, "llm",
                        lambda *a, **k: "import os\nprint(os.listdir('.'))")
    assert code_agent.run("list files").startswith("REJECTED")


def test_code_agent_runs_safe_code(monkeypatch):
    import config
    monkeypatch.setattr(config, "llm", lambda *a, **k: "print(2 + 2)")
    assert "4" in code_agent.run("2+2")
