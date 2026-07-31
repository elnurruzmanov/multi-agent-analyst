"""Deterministic churn aggregates for the dashboard.

Separate from the data agent on purpose: the agent writes SQL with an LLM and
is therefore non-deterministic, while these numbers are fixed queries the
dashboard can trust and the agent's answers can be checked against.
"""

import os
import sqlite3

DB = os.path.join(os.path.dirname(__file__), "db", "bank.db")

# Buckets are emitted as language-neutral keys; the frontend localises them.
TENURE_BUCKET = """CASE
    WHEN tenure_months < 6 THEN '0-5'
    WHEN tenure_months < 12 THEN '6-11'
    WHEN tenure_months < 24 THEN '12-23'
    WHEN tenure_months < 36 THEN '24-35'
    ELSE '36+' END"""

FAILED_BUCKET = """CASE
    WHEN failed_tx_total = 0 THEN '0'
    WHEN failed_tx_total = 1 THEN '1'
    WHEN failed_tx_total <= 2 THEN '2'
    ELSE '3+' END"""


def _rows(con: sqlite3.Connection, sql: str) -> list[dict]:
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _breakdown(con: sqlite3.Connection, expr: str, label: str, order: str) -> list[dict]:
    return _rows(con, f"""
        SELECT {expr} AS {label},
               COUNT(*) AS customers,
               SUM(churned) AS churned,
               ROUND(100.0 * SUM(churned) / COUNT(*), 1) AS churn_rate
        FROM customers
        GROUP BY {label}
        ORDER BY {order}
    """)


def snapshot() -> dict:
    """Every number the dashboard renders, in one read-only pass."""
    if not os.path.exists(DB):
        raise FileNotFoundError("bank.db not found — run `python db/init_db.py`")
    con = sqlite3.connect(DB)
    con.execute("PRAGMA query_only = ON")
    try:
        overview = _rows(con, """
            SELECT COUNT(*) AS customers,
                   SUM(churned) AS churned,
                   ROUND(100.0 * SUM(churned) / COUNT(*), 1) AS churn_rate,
                   ROUND(AVG(tenure_months), 1) AS avg_tenure_months,
                   ROUND(100.0 * SUM(segment = 'premium') / COUNT(*), 1) AS premium_share
            FROM customers
        """)[0]

        engagement = _rows(con, """
            SELECT CASE churned WHEN 1 THEN 'churned' ELSE 'active' END AS status,
                   ROUND(AVG(avg_monthly_logins), 1) AS avg_monthly_logins,
                   ROUND(AVG(avg_p2p_count), 1) AS avg_p2p_count,
                   ROUND(AVG(support_tickets_total), 2) AS avg_support_tickets
            FROM customers GROUP BY churned ORDER BY churned
        """)

        return {
            "overview": overview,
            "by_region": _breakdown(con, "region", "region", "churn_rate DESC"),
            "by_tenure": _breakdown(con, TENURE_BUCKET, "tenure", "MIN(tenure_months)"),
            "by_failed_tx": _breakdown(con, FAILED_BUCKET, "failed_tx", "MIN(failed_tx_total)"),
            "by_segment": _breakdown(con, "segment", "segment", "churn_rate DESC"),
            "by_platform": _breakdown(con, "platform", "platform", "churn_rate DESC"),
            "by_quarter": _rows(con, """
                SELECT churn_quarter AS quarter, COUNT(*) AS churned
                FROM customers WHERE churned = 1 AND churn_quarter <> ''
                GROUP BY quarter ORDER BY substr(quarter, 4) , substr(quarter, 1, 2)
            """),
            "engagement": engagement,
        }
    finally:
        con.close()


if __name__ == "__main__":
    import json
    print(json.dumps(snapshot(), indent=2, ensure_ascii=False))
