"""F5 — Data agent: natural language -> read-only SQL over bank.db.

Safety: only a single SELECT statement is allowed; any write/DDL keyword or
multiple statements are rejected before execution (defense point: SQL guard).
"""

import os
import re
import sqlite3
import sys

import config

DB = os.path.join(os.path.dirname(__file__), "..", "db", "bank.db")
SCHEMA = """Table customers(client_id TEXT, age_group TEXT, region TEXT,
segment TEXT, platform TEXT, tenure_months INT, avg_monthly_logins REAL,
avg_p2p_count REAL, failed_tx_total INT, support_tickets_total INT,
churned INT (1=left), churn_quarter TEXT e.g. 'Q1-2026')"""

FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|pragma|replace)\b", re.I)


def safe(sql: str) -> bool:
    s = sql.strip().rstrip(";")
    return s.lower().startswith("select") and not FORBIDDEN.search(s) and ";" not in s


def run(question: str) -> str:
    if not os.path.exists(DB):
        return "Database not found. Run `python db/init_db.py` first."
    sql = config.extract_code(config.llm(
        f"Write SQL (SQLite, one SELECT only, no comments) for: {question}\nSchema: {SCHEMA}\nReturn only the SQL."
    )).removeprefix("sql").strip()
    if not safe(sql):
        return f"REJECTED unsafe SQL: {sql}"
    try:
        con = sqlite3.connect(DB)
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchmany(20)
        con.close()
    except Exception as e:
        return f"SQL error: {e} (query: {sql})"
    body = "\n".join(str(dict(zip(cols, r))) for r in rows) or "(empty result)"
    return f"SQL: {sql}\nResult:\n{body}"


if __name__ == "__main__":
    print(run(" ".join(sys.argv[1:]) or "how many customers churned?"))
