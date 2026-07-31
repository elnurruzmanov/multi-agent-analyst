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
SCHEMA = """Table customers (1000 rows, one per retail-banking customer):
  client_id            TEXT   'C100000'…'C100999'
  age_group            TEXT   '18-24' | '25-34' | '35-44' | '45-54' | '55+'
  region               TEXT   'Toshkent' | 'Samarqand' | 'Qashqadaryo' | "Farg'ona" | 'Boshqa'
  segment              TEXT   'retail' | 'premium'
  platform             TEXT   'Android' | 'iOS'
  tenure_months        INT    1..60, months since the customer joined
  avg_monthly_logins   REAL   average logins per month
  avg_p2p_count        REAL   average person-to-person transfers per month
  failed_tx_total      INT    0..5, lifetime failed transactions
  support_tickets_total INT   0..4, lifetime support tickets
  churned              INT    1 = left (no login for 90+ days), 0 = active
  churn_quarter        TEXT   'Q4-2025' | 'Q1-2026' | 'Q2-2026', empty '' when still active

Guidance:
- "churn rate" means 100.0 * SUM(churned) / COUNT(*) — always ROUND(…, 1).
- Group and compare rather than returning raw rows; add ORDER BY so the top result is first.
- Region names are Uzbek; match them exactly as spelled above."""

FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|pragma|replace)\b", re.I)


def safe(sql: str) -> bool:
    s = sql.strip().rstrip(";")
    return s.lower().startswith("select") and not FORBIDDEN.search(s) and ";" not in s


def run(question: str) -> str:
    if not os.path.exists(DB):
        return "Database not found. Run `python db/init_db.py` first."
    sql = config.extract_code(config.llm(
        f"Write SQL (SQLite, one SELECT only, no comments, no semicolon) for: {question}\n\n"
        f"{SCHEMA}\n\nReturn only the SQL."
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
