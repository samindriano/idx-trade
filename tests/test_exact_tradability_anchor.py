import pandas as pd
import pytest

from idx_trade.security_master import (
    canonicalize_coverage_windows,
    canonicalize_tradability_anchors,
    canonicalize_tradability_intervals,
    tradability_state,
)
from idx_trade.states import TradabilityState


def _anchor(state: str, date: str = "2025-07-30") -> pd.DataFrame:
    return canonicalize_tradability_anchors(
        pd.DataFrame(
            {
                "ticker": ["TEST"],
                "market": ["REGULAR"],
                "as_of_date": [date],
                "state": [state],
                "source": ["IDX_OFFICIAL_POINT_EVIDENCE"],
                "source_ref": ["idx://point-evidence"],
                "evidence_type": ["OFFICIAL_POINT_STATE"],
            }
        )
    )


def test_exact_active_anchor_is_authoritative_without_discovery_window():
    state = tradability_state(
        canonicalize_tradability_intervals(pd.DataFrame()),
        canonicalize_coverage_windows(pd.DataFrame()),
        "TEST",
        pd.Timestamp("2025-07-30"),
        anchors=_anchor("ACTIVE"),
    )
    assert state is TradabilityState.ACTIVE


def test_exact_suspended_anchor_is_authoritative_without_discovery_window():
    state = tradability_state(
        canonicalize_tradability_intervals(pd.DataFrame()),
        canonicalize_coverage_windows(pd.DataFrame()),
        "TEST",
        pd.Timestamp("2025-07-30"),
        anchors=_anchor("SUSPENDED"),
    )
    assert state is TradabilityState.SUSPENDED


def test_exact_anchor_does_not_propagate_without_complete_discovery_window():
    anchors = _anchor("ACTIVE")
    state = tradability_state(
        canonicalize_tradability_intervals(pd.DataFrame()),
        canonicalize_coverage_windows(pd.DataFrame()),
        "TEST",
        pd.Timestamp("2025-07-31"),
        anchors=anchors,
    )
    assert state is TradabilityState.UNKNOWN


def test_exact_anchor_conflicting_with_explicit_interval_fails_hard():
    intervals = canonicalize_tradability_intervals(
        pd.DataFrame(
            {
                "ticker": ["TEST"],
                "market": ["REGULAR"],
                "state": ["SUSPENDED"],
                "effective_from": ["2025-07-30"],
                "effective_to": ["2025-07-30"],
                "source": ["IDX_EXCHANGE_ANNOUNCEMENT"],
            }
        )
    )
    with pytest.raises(ValueError, match="conflicts with reconstructed"):
        tradability_state(
            intervals,
            canonicalize_coverage_windows(pd.DataFrame()),
            "TEST",
            pd.Timestamp("2025-07-30"),
            anchors=_anchor("ACTIVE"),
        )
