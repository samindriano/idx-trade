import json

import pandas as pd

from idx_trade.session_backfill import run_exchange_session_backfill


def _july_2026_daily_statistics_rows() -> list[dict[str, object]]:
    dates = [
        "2026-07-01", "2026-07-02", "2026-07-03", "2026-07-06", "2026-07-07",
        "2026-07-08", "2026-07-09", "2026-07-10", "2026-07-13", "2026-07-14",
        "2026-07-15", "2026-07-16", "2026-07-17", "2026-07-20", "2026-07-21",
        "2026-07-22", "2026-07-23", "2026-07-24", "2026-07-27", "2026-07-28",
        "2026-07-29", "2026-07-30", "2026-07-31",
    ]
    return [{"date": date} for date in dates]


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


def test_session_backfill_records_selected_daily_listing_identity(tmp_path):
    daily_rows = _july_2026_daily_statistics_rows()

    def monthly_fetcher(url: str) -> dict[str, object]:
        return {"data": []}

    def daily_fetcher(url: str) -> dict[str, object]:
        return {"value": daily_rows}

    summary = run_exchange_session_backfill(
        "2026-07-01",
        "2026-07-31",
        tmp_path,
        fetch_json=monthly_fetcher,
        fetch_daily_statistics_json=daily_fetcher,
    )

    assert summary["complete"]
    assert summary["exchange_sessions"] == 23
    assert summary["source_identity"] == "IDX_DAILY_STATISTICS_PUBLICATION_LISTING"
    assert summary["fallback_months"] == 1
    source = pd.read_csv(tmp_path / "exchange_session_sources.csv").iloc[0]
    assert source["source_identity"] == "IDX_DAILY_STATISTICS_PUBLICATION_LISTING"
    assert "primary/Statistic/GetStatistic" in source["source_ref"]
