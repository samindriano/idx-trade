import pandas as pd
import pytest

from idx_trade.execution_evidence import merge_tradability_point_evidence
from idx_trade.security_master import (
    canonicalize_coverage_windows,
    canonicalize_tradability_anchors,
    canonicalize_tradability_intervals,
    tradability_state,
)
from idx_trade.states import TradabilityState


def _anchor(state: str, source: str) -> pd.DataFrame:
    return canonicalize_tradability_anchors(
        pd.DataFrame(
            {
                "ticker": ["TEST"],
                "market": ["REGULAR"],
                "as_of_date": ["2025-07-30"],
                "state": [state],
                "source": [source],
                "source_ref": [f"idx://{source}"],
                "evidence_type": [source],
            }
        )
    )


def test_suspended_point_evidence_refines_no_trade_observation():
    merged = merge_tradability_point_evidence(
        _anchor("NO_TRADE", "EXECUTION"),
        _anchor("SUSPENDED", "LEGAL_STATUS"),
    )
    assert len(merged) == 1
    assert merged.iloc[0]["state"] == "SUSPENDED"


def test_active_and_no_trade_point_evidence_is_a_hard_conflict():
    with pytest.raises(ValueError, match="Conflicting tradability point evidence"):
        merge_tradability_point_evidence(
            _anchor("ACTIVE", "EXECUTION_ACTIVE"),
            _anchor("NO_TRADE", "EXECUTION_NONE"),
        )


def test_no_trade_anchor_is_compatible_with_explicit_suspension_interval():
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
    state = tradability_state(
        intervals,
        canonicalize_coverage_windows(pd.DataFrame()),
        "TEST",
        pd.Timestamp("2025-07-30"),
        anchors=_anchor("NO_TRADE", "EXECUTION"),
    )
    assert state is TradabilityState.SUSPENDED
