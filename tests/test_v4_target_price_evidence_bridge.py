from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from idx_trade.ranking_v4_3_target_execution import prepare_price_evidence
from idx_trade.v4_target_price_evidence_bridge import (
    build_market_state_map,
    build_v4_price_evidence,
)


def _panel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAAA", "AAAA", "BBBB", "BBBB"],
            "date": ["2026-01-05", "2026-01-06", "2026-01-05", "2026-01-06"],
            "high": [110.0, 111.0, 210.0, 211.0],
            "low": [90.0, 91.0, 190.0, 191.0],
            "close": [105.0, 106.0, 205.0, 206.0],
        }
    )


def _derivative() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAAA", "AAAA", "BBBB", "BBBB"],
            "date": ["2026-01-05", "2026-01-06", "2026-01-05", "2026-01-06"],
            "open": [100.0, 101.0, 200.0, np.nan],
        }
    )


def _overlay() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["BBBB"],
            "date": ["2026-01-06"],
            "recovered_open": [201.0],
            "panel_high": [211.0],
            "panel_low": [191.0],
            "panel_close": [206.0],
        }
    )


def _anchors() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAAA", "AAAA", "BBBB", "BBBB"],
            "market": ["REGULAR"] * 4,
            "as_of_date": ["2026-01-05", "2026-01-06", "2026-01-05", "2026-01-06"],
            "state": ["ACTIVE", "ACTIVE", "ACTIVE", "ACTIVE"],
        }
    )


def _intervals() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["BBBB"],
            "market": ["REGULAR"],
            "state": ["SUSPENDED"],
            "effective_from": ["2026-01-06"],
            "effective_to": ["2026-01-06"],
        }
    )


def test_price_bridge_materializes_exact_accepted_open_lineage():
    evidence = build_v4_price_evidence(
        _panel(),
        _derivative(),
        _overlay(),
        _anchors(),
        _intervals(),
        ["2026-01-05", "2026-01-06"],
    )
    assert len(evidence) == 4
    bbbb = evidence[(evidence["ticker"] == "BBBB") & (evidence["date"] == pd.Timestamp("2026-01-06"))].iloc[0]
    assert bbbb["accepted_open"] == 201.0
    assert bool(bbbb["open_admitted"])
    assert bbbb["close"] == 206.0
    assert bool(bbbb["close_admitted"])
    # Preserve target-support census precedence: exact anchor wins over an
    # overlapping interval fill.
    assert bbbb["market_state"] == "ACTIVE"
    pd.testing.assert_frame_equal(evidence, prepare_price_evidence(evidence))


def test_overlay_cannot_overlap_positive_derivative_open():
    derivative = _derivative()
    derivative.loc[(derivative["ticker"] == "BBBB") & (derivative["date"] == "2026-01-06"), "open"] = 202.0
    with pytest.raises(RuntimeError, match="OPEN_OVERLAY_OVERLAPS_ADMITTED_DERIVATIVE"):
        build_v4_price_evidence(
            _panel(), derivative, _overlay(), _anchors(), _intervals(), ["2026-01-05", "2026-01-06"]
        )


def test_overlay_reattestation_fails_on_canonical_hlc_mismatch():
    overlay = _overlay()
    overlay.loc[0, "panel_close"] = 999.0
    with pytest.raises(RuntimeError, match="OPEN_OVERLAY_CANONICAL_HLC_MISMATCH"):
        build_v4_price_evidence(
            _panel(), _derivative(), overlay, _anchors(), _intervals(), ["2026-01-05", "2026-01-06"]
        )


def test_missing_market_anchor_fails_closed_to_unknown():
    anchors = _anchors()
    anchors = anchors[~((anchors["ticker"] == "AAAA") & (anchors["as_of_date"] == "2026-01-06"))]
    states = build_market_state_map(
        anchors,
        _intervals(),
        ["2026-01-05", "2026-01-06"],
    )
    assert ("AAAA", pd.Timestamp("2026-01-06")) not in states
    evidence = build_v4_price_evidence(
        _panel(), _derivative(), _overlay(), anchors, _intervals(), ["2026-01-05", "2026-01-06"]
    )
    row = evidence[(evidence["ticker"] == "AAAA") & (evidence["date"] == pd.Timestamp("2026-01-06"))].iloc[0]
    assert row["market_state"] == "UNKNOWN"


def test_derivative_identity_must_match_panel_exactly():
    derivative = _derivative().iloc[:-1].copy()
    with pytest.raises(RuntimeError, match="OPEN_DERIVATIVE_IDENTITY_MISMATCH"):
        build_v4_price_evidence(
            _panel(), derivative, _overlay(), _anchors(), _intervals(), ["2026-01-05", "2026-01-06"]
        )
