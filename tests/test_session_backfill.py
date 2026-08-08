import json

import pandas as pd

from idx_trade.session_backfill import run_exchange_session_backfill


def test_session_backfill_writes_calendar_and_source_report(tmp_path):
    def fetch_month(year: int, month: int):
        if (year, month) == (2025, 9):
            return pd.DatetimeIndex(["2025-09-29", "2025-09-30"])
        if (year, month) == (2025, 10):
            return pd.DatetimeIndex(["2025-10-01", "2025-10-02"])
        raise AssertionError((year, month))

    summary = run_exchange_session_backfill(
        "2025-09-30", "2025-10-01", tmp_path, fetch_month=fetch_month
    )

    assert summary["complete"]
    assert summary["exchange_sessions"] == 2
    sessions = pd.read_csv(tmp_path / "exchange_sessions.csv")
    assert sessions["date"].tolist() == ["2025-09-30", "2025-10-01"]
    sources = pd.read_csv(tmp_path / "exchange_session_sources.csv")
    assert sources["status"].eq("PARSED").all()
    stored_summary = json.loads((tmp_path / "exchange_session_summary.json").read_text())
    assert stored_summary["sessions_sha256"] == summary["sessions_sha256"]


def test_session_backfill_fails_summary_if_a_month_cannot_be_parsed(tmp_path):
    def fetch_month(year: int, month: int):
        if month == 9:
            return pd.DatetimeIndex(["2025-09-30"])
        raise ValueError("schema changed")

    summary = run_exchange_session_backfill(
        "2025-09-30", "2025-10-01", tmp_path, fetch_month=fetch_month
    )

    assert not summary["complete"]
    assert summary["error_months"] == 1
    sources = pd.read_csv(tmp_path / "exchange_session_sources.csv")
    assert set(sources["status"]) == {"PARSED", "ERROR"}
