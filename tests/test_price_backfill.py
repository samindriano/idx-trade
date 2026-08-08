import json

import pandas as pd

from idx_trade.data import canonicalize_ohlcv
from idx_trade.price_backfill import run_price_backfill


def _frame(dates, close=100.0):
    return canonicalize_ohlcv(
        pd.DataFrame(
            {
                "date": dates,
                "open": close,
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": 1_000_000,
            }
        ),
        ticker="TEST",
    )


def test_backfill_persists_new_history_and_reports_range(tmp_path):
    dates = pd.bdate_range("2025-01-01", periods=5)

    def downloader(tickers, start, end):
        assert tickers == ["TEST"]
        return {"TEST": _frame(dates)}

    summary = run_price_backfill(
        ["TEST"], "2025-01-01", "2025-02-01", tmp_path / "raw", tmp_path / "reports",
        downloader=downloader,
    )
    assert summary["complete"] is True
    stored = pd.read_parquet(tmp_path / "raw" / "TEST.parquet")
    assert len(stored) == 5
    report = pd.read_csv(tmp_path / "reports" / "price_backfill_report.csv")
    assert report.loc[0, "status"] == "UPDATED"
    assert report.loc[0, "first_date"] == "2025-01-01"


def test_provider_empty_is_unresolved_and_does_not_create_fake_price_file(tmp_path):
    def downloader(tickers, start, end):
        return {"TEST": pd.DataFrame()}

    summary = run_price_backfill(
        ["TEST"], "2025-01-01", None, tmp_path / "raw", tmp_path / "reports",
        downloader=downloader,
    )
    assert summary["complete"] is False
    assert summary["no_provider_rows"] == 1
    assert not (tmp_path / "raw" / "TEST.parquet").exists()
    saved = json.loads((tmp_path / "reports" / "price_backfill_summary.json").read_text())
    assert "not proof of suspension" in saved["note"]


def test_provider_revision_is_reported_and_existing_history_remains_unchanged(tmp_path):
    dates = pd.bdate_range("2025-01-01", periods=3)
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    original = _frame(dates, close=100.0)
    original.to_parquet(raw_dir / "TEST.parquet", index=False)

    revised = original.copy()
    revised.loc[1, "raw_close"] = 80.0

    def downloader(tickers, start, end):
        return {"TEST": revised}

    summary = run_price_backfill(
        ["TEST"], "2025-01-01", None, raw_dir, tmp_path / "reports",
        downloader=downloader,
    )
    assert summary["complete"] is False
    assert summary["revision_conflicts"] == 1
    after = pd.read_parquet(raw_dir / "TEST.parquet")
    pd.testing.assert_frame_equal(after, original)
