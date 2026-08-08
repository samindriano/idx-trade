import pandas as pd
import pytest

from idx_trade.security_master import (
    canonicalize_coverage_windows,
    canonicalize_tradability_intervals,
)
from idx_trade.tradability_reconciliation import (
    assert_snapshot_reconciliation,
    reconcile_tradability_snapshot,
    snapshot_to_tradability_anchors,
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
                "source_ref": f"idx://snapshot/{as_of}",
            }
        ]
    )


def _coverage() -> pd.DataFrame:
    return canonicalize_coverage_windows(
        pd.DataFrame(
            [
                {
                    "market": "REGULAR",
                    "effective_from": "2025-01-01",
                    "effective_to": "2025-12-31",
                    "source": "CLAIMED_COMPLETE",
                    "is_complete": True,
                    "discovery_basis": "TEST_PUBLIC_DISCOVERY_AUDIT",
                    "left_boundary_basis": "TEST_ARCHIVE_START_AUDIT",
                }
            ]
        )
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


def test_complete_discovery_window_does_not_create_false_active_without_anchor():
    report = reconcile_tradability_snapshot(
        _snapshot("SUSPENDED"),
        canonicalize_tradability_intervals(pd.DataFrame()),
        _coverage(),
    )
    assert report["passed"] is False
    assert report["rows"][0]["reconstructed_state"] == "UNKNOWN"


def test_selected_snapshot_can_seed_anchor_while_separate_snapshot_validates():
    anchor_snapshot = _snapshot("ACTIVE", as_of="2025-01-02")
    anchors = snapshot_to_tradability_anchors(anchor_snapshot)
    validation_snapshot = _snapshot("ACTIVE", as_of="2025-02-03")
    report = reconcile_tradability_snapshot(
        validation_snapshot,
        canonicalize_tradability_intervals(pd.DataFrame()),
        _coverage(),
        anchors,
    )
    assert report["passed"] is True
    assert report["matched_rows"] == 1


def test_independent_suspended_snapshot_detects_missing_event_even_with_active_anchor():
    anchors = snapshot_to_tradability_anchors(_snapshot("ACTIVE", as_of="2025-01-02"))
    report = reconcile_tradability_snapshot(
        _snapshot("SUSPENDED", as_of="2025-02-03"),
        canonicalize_tradability_intervals(pd.DataFrame()),
        _coverage(),
        anchors,
    )
    assert report["passed"] is False
    assert report["rows"][0]["reconstructed_state"] == "ACTIVE"
