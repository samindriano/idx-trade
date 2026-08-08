import pandas as pd
import pytest

from idx_trade.security_master import canonicalize_coverage_windows, canonicalize_tradability_intervals
from idx_trade.tradability_reconciliation import (
    assert_snapshot_reconciliation,
    reconcile_tradability_snapshot,
)


def _snapshot(state: str, as_of: str = "2025-01-03") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "TEST",
                "market": "REGULAR",
                "state": state,
                "as_of_date": as_of,
                "source": "IDX_STATUS_SNAPSHOT",
                "source_ref": "idx://snapshot",
            }
        ]
    )


def _suspension() -> pd.DataFrame:
    return canonicalize_tradability_intervals(
        pd.DataFrame(
            [
                {
                    "ticker": "TEST",
                    "market": "REGULAR",
                    "state": "SUSPENDED",
                    "effective_from": "2025-01-02",
                    "effective_to": "2025-01-05",
                    "announced_at": "2025-01-01",
                    "source": "IDX_EXCHANGE_ANNOUNCEMENT",
                    "source_ref": "idx://suspend|idx://resume",
                }
            ]
        )
    )


def test_snapshot_matches_reconstructed_suspension():
    report = reconcile_tradability_snapshot(
        _snapshot("SUSPENDED"),
        _suspension(),
        canonicalize_coverage_windows(pd.DataFrame()),
    )
    assert report["passed"] is True
    assert report["mismatch_rows"] == 0
    assert_snapshot_reconciliation(report)


def test_snapshot_exposes_missing_event_history_even_without_complete_coverage_window():
    report = reconcile_tradability_snapshot(
        _snapshot("SUSPENDED"),
        canonicalize_tradability_intervals(pd.DataFrame()),
        canonicalize_coverage_windows(pd.DataFrame()),
    )
    assert report["passed"] is False
    assert report["rows"][0]["reconstructed_state"] == "UNKNOWN"
    assert report["mismatch_tickers"] == ["TEST"]
    with pytest.raises(RuntimeError, match="do not declare a complete coverage window"):
        assert_snapshot_reconciliation(report)


def test_snapshot_exposes_false_active_complement_inside_claimed_complete_window():
    coverage = canonicalize_coverage_windows(
        pd.DataFrame(
            [
                {
                    "market": "REGULAR",
                    "effective_from": "2025-01-01",
                        "effective_to": "2025-12-31",
                        "source": "CLAIMED_COMPLETE",
                        "is_complete": True,
                        "discovery_basis": "TEST_PUBLIC_DISCOVERY_AUDIT",
                        "left_boundary_basis": "TEST_INITIAL_ACTIVE_SNAPSHOT",
                        "initial_state": "ACTIVE",
                    }
            ]
        )
    )
    report = reconcile_tradability_snapshot(
        _snapshot("SUSPENDED"),
        canonicalize_tradability_intervals(pd.DataFrame()),
        coverage,
    )
    assert report["passed"] is False
    assert report["rows"][0]["reconstructed_state"] == "ACTIVE"
