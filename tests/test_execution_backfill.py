from dataclasses import dataclass

import pandas as pd

from idx_trade.execution_backfill import backfill_stock_summary_execution_evidence


@dataclass
class _Meta:
    source_ref: str

    def to_dict(self):
        return {"source_ref": self.source_ref}


def _frame(date: pd.Timestamp) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAAA", "BBBB"],
            "as_of_date": [date, date],
            "volume": [1000, 0],
            "frequency": [10, 0],
            "nonregular_volume": [2000, 200],
            "nonregular_frequency": [20, 2],
            "source": ["IDX_PUBLIC_STOCK_SUMMARY"] * 2,
            "source_ref": [f"idx://{date.date()}"] * 2,
        }
    )


def test_execution_backfill_writes_active_and_no_trade_evidence(tmp_path):
    sessions = pd.to_datetime(["2025-01-02", "2025-01-03"])

    def fetcher(day):
        return _frame(day), _Meta(f"idx://{day.date()}")

    summary = backfill_stock_summary_execution_evidence(
        pd.DatetimeIndex(sessions), tmp_path, fetcher=fetcher
    )
    assert summary["session_source_complete"] is True
    assert summary["anchor_rows"] == 4
    assert summary["active_anchor_rows"] == 2
    assert summary["no_trade_anchor_rows"] == 2
    anchors = pd.read_csv(tmp_path / "idx_execution_anchors.csv")
    assert set(anchors["state"]) == {"ACTIVE", "NO_TRADE"}


def test_execution_backfill_records_failed_session_without_filling_it(tmp_path):
    sessions = pd.to_datetime(["2025-01-02", "2025-01-03"])

    def fetcher(day):
        if day == pd.Timestamp("2025-01-03"):
            raise RuntimeError("IDX unavailable")
        return _frame(day), _Meta(f"idx://{day.date()}")

    summary = backfill_stock_summary_execution_evidence(
        pd.DatetimeIndex(sessions), tmp_path, fetcher=fetcher
    )
    assert summary["session_source_complete"] is False
    assert summary["failed_sessions"] == 1
    report = pd.read_csv(tmp_path / "idx_execution_session_report.csv")
    failed = report.loc[report["status"].eq("ERROR")]
    assert len(failed) == 1
    assert "IDX unavailable" in failed.iloc[0]["error"]
