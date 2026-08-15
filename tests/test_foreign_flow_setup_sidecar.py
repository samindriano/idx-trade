from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.foreign_flow_setup_sidecar import build_foreign_flow_setup_sidecar


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "feature_session": "2026-08-14",
                "flow_through_session": "2026-08-13",
                "foreign_participation_1": 0.50,
                "foreign_flow_shock_1": 0.20,
                "foreign_flow_shock_mean_5": 0.15,
                "foreign_flow_shock_mean_20": 0.10,
                "foreign_flow_shock_percentile_120": 0.65,
                "xs_rank_foreign_flow_shock_mean_5": 0.55,
                "xs_rank_foreign_flow_shock_mean_20": 0.60,
                "foreign_weighted_persistence_5": 0.10,
                "foreign_weighted_persistence_20": 0.15,
                "foreign_flow_acceleration_5_20": 0.0,
                "foreign_flow_price_divergence_5": 0.0,
                "foreign_flow_price_divergence_20": 0.0,
            },
            {
                "ticker": "BBB",
                "feature_session": "2026-08-14",
                "flow_through_session": "2026-08-13",
                "foreign_participation_1": 0.05,
                "foreign_flow_shock_1": 3.20,
                "foreign_flow_shock_mean_5": 2.40,
                "foreign_flow_shock_mean_20": 1.60,
                "foreign_flow_shock_percentile_120": 0.99,
                "xs_rank_foreign_flow_shock_mean_5": 0.95,
                "xs_rank_foreign_flow_shock_mean_20": 0.93,
                "foreign_weighted_persistence_5": 0.80,
                "foreign_weighted_persistence_20": 0.75,
                "foreign_flow_acceleration_5_20": 0.12,
                "foreign_flow_price_divergence_5": 0.30,
                "foreign_flow_price_divergence_20": 0.25,
            },
        ]
    )


def test_sidecar_preserves_separate_participation_and_abnormality_axes() -> None:
    out = build_foreign_flow_setup_sidecar(_frame())
    aaa = out.loc[out["ticker"].eq("AAA")].iloc[0]
    bbb = out.loc[out["ticker"].eq("BBB")].iloc[0]

    assert aaa["participation_intensity"] == "HIGH"
    assert aaa["historical_abnormality"] == "NORMAL"
    assert aaa["setup_label"] == "HIGH_PARTICIPATION_ROUTINE_FLOW"

    assert bbb["participation_intensity"] == "NORMAL"
    assert bbb["foreign_flow_shock_1"] == pytest.approx(3.20)
    assert bbb["historical_abnormality"] == "EXTREME_ACCUMULATION"
    assert bbb["setup_label"] == "STEALTH_ACCUMULATION_CANDIDATE"

    # The lower current-volume participation row retains the much larger
    # own-history abnormality evidence instead of being ranked below AAA by
    # participation alone.
    assert bbb["foreign_participation_1"] < aaa["foreign_participation_1"]
    assert bbb["foreign_flow_shock_1"] > aaa["foreign_flow_shock_1"]


def test_sidecar_rejects_duplicate_keys() -> None:
    frame = _frame()
    duplicate = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate ticker/feature_session"):
        build_foreign_flow_setup_sidecar(duplicate)


def test_sidecar_rejects_outcome_columns() -> None:
    frame = _frame()
    frame["TP_FIRST"] = 1
    with pytest.raises(ValueError, match="outcome-blind"):
        build_foreign_flow_setup_sidecar(frame)


def test_sidecar_requires_all_v2_evidence_fields() -> None:
    frame = _frame().drop(columns=["foreign_flow_shock_mean_20"])
    with pytest.raises(ValueError, match="missing columns"):
        build_foreign_flow_setup_sidecar(frame)
