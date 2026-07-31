"""Builds the sample SQLite database the data_sql agent queries.

Banking twist: instead of a generic demo table, this mirrors the author's
SQB-style churn work — 1,000 synthetic customers with monthly activity
aggregates and a churn flag (90 days without login).
"""

import os
import random
import sqlite3

random.seed(42)
DB = os.path.join(os.path.dirname(__file__), "bank.db")


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.executescript("""
    DROP TABLE IF EXISTS customers;
    CREATE TABLE customers (
        client_id TEXT PRIMARY KEY,
        age_group TEXT, region TEXT, segment TEXT, platform TEXT,
        tenure_months INTEGER,
        avg_monthly_logins REAL, avg_p2p_count REAL,
        failed_tx_total INTEGER, support_tickets_total INTEGER,
        churned INTEGER, churn_quarter TEXT
    );
    """)
    regions = ["Toshkent", "Samarqand", "Qashqadaryo", "Farg'ona", "Boshqa"]
    rows = []
    for i in range(1000):
        base = random.choice([4, 12, 26])
        churned = random.random() < (0.35 if base == 4 else 0.18 if base == 12 else 0.08)
        failed = random.choices([0, 1, 2, 5], weights=[60, 25, 10, 5])[0]
        if failed >= 2 and random.random() < 0.5:
            churned = 1
        rows.append((
            f"C{100000+i}",
            random.choice(["18-24", "25-34", "35-44", "45-54", "55+"]),
            random.choice(regions),
            "premium" if random.random() < 0.1 else "retail",
            random.choice(["Android", "Android", "iOS"]),
            random.randint(1, 60),
            round(base * random.uniform(0.6, 1.3), 1),
            round(base * 0.45 * random.uniform(0.5, 1.4), 1),
            failed,
            random.choices([0, 1, 2, 4], weights=[70, 18, 8, 4])[0],
            int(churned),
            random.choice(["Q1-2026", "Q2-2026", "Q4-2025", ""]) if churned else "",
        ))
    cur.executemany("INSERT INTO customers VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    con.commit()
    n = cur.execute("SELECT COUNT(*), SUM(churned) FROM customers").fetchone()
    print(f"bank.db yaratildi: {n[0]} mijoz, {n[1]} churned")
    con.close()


if __name__ == "__main__":
    main()
