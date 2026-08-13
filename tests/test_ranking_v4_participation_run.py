from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.ranking_v4_participation_run import (
    FOLD_NAMES,
    _gate,
    prove_v3_b_control_equivalence,
)


def _metrics(*, pr_gain: float = 0.0, spread_gain: float = 0.0, roc_gain: float = 0.0) -> pd.DataFrame:
    rows = []
    for fold in FOLD_NAMES:
        positive_rate = 0.40
        pr_auc = 0.45 + pr_gain
        q1 = 0.35
        q5 = 0.45 + spread_gain
        rows.append(
            {
                "candidate": "X",
                "fold": fold,
                "positive_rate": positive_rate,
                "pr_auc": pr_auc,
                "pr_auc_delta_vs_base": pr_auc - positive_rate,
                "roc_auc": 0.53 + roc_gain,
                "q1_tp_rate": q1,
                "q5_tp_rate": q5,
                "q5_minus_q1": q5 - q1,
                "top_decile_tp_rate": 0.48,
                "top_decile_lift": 0.08,
            }
        )
    return pd.DataFrame(rows)


def _predictions() -> pd.DataFrame:
    rows = []
    for fold_number, fold in enumerate(FOLD_NAMES, start=1):
        for ticker_number, ticker in enumerate(("AAA", "BBB"), start=1):
            rows.append(
                {
                    "candidate": "X",
                    "fold": fold,
                    "ticker": ticker,
                    "date": pd.Timestamp("2025-01-01") + pd.Timedelta(days=fold_number),
                    "signal_session_index": fold_number * 100 + ticker_number,
                    "binary_target": ticker_number % 2,
                    "score": float(fold_number + ticker_number / 10.0),
                }
            )
    return pd.DataFrame(rows)


def test_v4_a_gate_passes_frozen_small_consistent_improvement() -> None:
    control = _metrics()
    candidate = _metrics(pr_gain=0.002, spread_gain=0.005, roc_gain=0.001)
    paired, detail, passed = _gate(candidate, control)
    assert passed is True
    assert detail["paired_pr_nonnegative_folds"] == 6
    assert detail["median_pr_auc_improvement"] == pytest.approx(0.002)
    assert detail["q25_pr_auc_improvement"] == pytest.approx(0.002)
    assert detail["median_q5_minus_q1_change"] == pytest.approx(0.005)
    assert paired["fold"].tolist() == list(FOLD_NAMES)


def test_v4_a_gate_fails_when_median_pr_does_not_reach_frozen_threshold() -> None:
    control = _metrics()
    candidate = _metrics(pr_gain=0.001, spread_gain=0.005)
    _, detail, passed = _gate(candidate, control)
    assert passed is False
    assert detail["median_pr_auc_improvement"] == pytest.approx(0.001)


def test_v4_a_gate_fails_if_only_four_folds_are_nonnegative() -> None:
    control = _metrics()
    candidate = _metrics(pr_gain=0.002, spread_gain=0.005)
    candidate.loc[candidate["fold"].isin(("V2F1", "V2F2")), "pr_auc"] -= 0.004
    candidate["pr_auc_delta_vs_base"] = candidate["pr_auc"] - candidate["positive_rate"]
    _, detail, passed = _gate(candidate, control)
    assert passed is False
    assert detail["paired_pr_nonnegative_folds"] == 4


def test_v4_a_control_equivalence_accepts_exact_reference_and_rejects_score_change() -> None:
    metrics = _metrics()
    predictions = _predictions()
    result = prove_v3_b_control_equivalence(
        control_metrics=metrics,
        control_predictions=predictions,
        reference_metrics=metrics.copy(),
        reference_predictions=predictions.copy(),
        reference_hashes={"x": "y"},
    )
    assert result["status"] == "V4_A_V3_B_CONTROL_EQUIVALENCE_PASS"
    assert result["max_score_abs_diff"] == 0.0

    changed = predictions.copy()
    changed.loc[0, "score"] += 1e-6
    with pytest.raises(RuntimeError, match="score equivalence"):
        prove_v3_b_control_equivalence(
            control_metrics=metrics,
            control_predictions=changed,
            reference_metrics=metrics.copy(),
            reference_predictions=predictions.copy(),
            reference_hashes={"x": "y"},
        )
