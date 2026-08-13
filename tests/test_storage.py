import pandas as pd
import pytest

from idx_trade.storage import DataRevisionConflict, merge_daily_history


def _frame(close: float, *, vendor_adj_close: float | None = None) -> pd.DataFrame:
    if vendor_adj_close is None:
        vendor_adj_close = close
    return pd.DataFrame(
        {
            "date": [pd.Timestamp("2025-01-02")],
            "raw_open": [100.0],
            "raw_high": [105.0],
            "raw_low": [95.0],
            "raw_close": [close],
            "raw_volume": [1_000.0],
            "vendor_adj_close": [vendor_adj_close],
            "explicit_split_event": [False],
            "explicit_dividend_event": [False],
        }
    )


def test_existing_history_revision_fails_closed_by_default():
    with pytest.raises(DataRevisionConflict):
        merge_daily_history(_frame(102.0), _frame(103.0), "TEST")


def test_identical_overlap_is_idempotent():
    merged, conflicts = merge_daily_history(_frame(102.0), _frame(102.0), "TEST")
    assert conflicts == []
    assert len(merged) == 1


def test_explicit_revision_mode_returns_audit_conflicts():
    merged, conflicts = merge_daily_history(
        _frame(102.0), _frame(103.0, vendor_adj_close=102.0), "TEST", allow_revisions=True
    )
    assert {conflict.column for conflict in conflicts} == {"raw_close"}
    assert merged.iloc[0]["raw_close"] == 103.0


def test_explicit_revision_mode_surfaces_vendor_adjusted_close_revision():
    _, conflicts = merge_daily_history(
        _frame(102.0), _frame(102.0, vendor_adj_close=103.0), "TEST", allow_revisions=True
    )
    assert {conflict.column for conflict in conflicts} == {"vendor_adj_close"}
