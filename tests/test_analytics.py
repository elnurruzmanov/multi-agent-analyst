import analytics


def test_overview_totals_are_consistent():
    o = analytics.snapshot()["overview"]
    assert o["customers"] == 1000
    assert 0 < o["churned"] < o["customers"]
    assert round(100 * o["churned"] / o["customers"], 1) == o["churn_rate"]


def test_every_breakdown_sums_back_to_the_portfolio():
    s = analytics.snapshot()
    total = s["overview"]["customers"]
    for key in ("by_region", "by_tenure", "by_failed_tx", "by_segment", "by_platform"):
        rows = s[key]
        assert rows, f"{key} is empty"
        assert sum(r["customers"] for r in rows) == total, key
        assert sum(r["churned"] for r in rows) == s["overview"]["churned"], key


def test_bucket_labels_are_language_neutral_keys():
    s = analytics.snapshot()
    assert {r["tenure"] for r in s["by_tenure"]} <= {"0-5", "6-11", "12-23", "24-35", "36+"}
    assert {r["failed_tx"] for r in s["by_failed_tx"]} <= {"0", "1", "2", "3+"}
    assert {e["status"] for e in s["engagement"]} == {"active", "churned"}


def test_failed_transactions_are_the_strongest_driver():
    """The synthetic data encodes this; the dashboard copy claims it, so pin it."""
    rows = {r["failed_tx"]: r["churn_rate"] for r in analytics.snapshot()["by_failed_tx"]}
    assert rows["2"] > 2 * rows["0"]


def test_snapshot_is_read_only(tmp_path, monkeypatch):
    before = analytics.snapshot()
    analytics.snapshot()
    assert analytics.snapshot() == before
