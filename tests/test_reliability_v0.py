from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from idx_trade.reliability_v0 import (
    EXPECTED_O2_FEATURE_ORDER_SHA256,
    FOLDS,
    O2_FEATURES,
    PRIMARY_PROXIES,
    RUNTIME_FLAGS,
    ReliabilityDataBlocked,
    empirical_centrality,
    evaluate_proxy_gate,
    feature_order_sha256,
    local_pairwise_quality,
    score_margin_reliability,
    session_proxy_metrics,
    validate_fold_windows,
)


def test_frozen_feature_order_hash_is_exact():
    assert len(O2_FEATURES) == 36
    assert O2_FEATURES[-3:] == ("open_position", "open_to_high", "open_to_low")
    assert feature_order_sha256(O2_FEATURES) == EXPECTED_O2_FEATURE_ORDER_SHA256


def test_score_margin_handles_edges_and_ties_deterministically():
    frame = pd.DataFrame(
        {
            "ticker": ["A", "B", "C", "D"],
            "score": [0.0, 1.0, 1.0, 4.0],
        }
    )
    margin = score_margin_reliability(frame)
    assert margin.loc[1] == pytest.approx(0.0)
    assert margin.loc[2] == pytest.approx(0.0)
    assert margin.loc[0] > 0.0
    assert margin.loc[3] > 0.0


def test_empirical_support_uses_training_only_and_preserves_missingness():
    training = np.array([0.0, 1.0, 2.0, 3.0])
    validation = np.array([1.5, 10.0, np.nan])
    support = empirical_centrality(training, validation)
    assert support[0] > support[1]
    assert support[1] == pytest.approx(1e-6)
    assert np.isnan(support[2])
    changed_training = np.array([0.0, 1.0, 2.0, 3.0, 10.0, 10.0])
    changed = empirical_centrality(changed_training, validation)
    assert changed[1] > support[1]


def test_local_pairwise_quality_handles_both_classes_and_ties():
    frame = pd.DataFrame(
        {
            "score": [3.0, 2.0, 2.0, 1.0],
            "binary_target": [1, 1, 0, 0],
        }
    )
    quality = local_pairwise_quality(frame)
    assert quality.iloc[0] == pytest.approx(1.0)
    assert quality.iloc[1] == pytest.approx(0.75)
    assert quality.iloc[2] == pytest.approx(0.75)
    assert quality.iloc[3] == pytest.approx(1.0)


def _session_frame() -> pd.DataFrame:
    rows = 40
    score = np.linspace(-2.0, 2.0, rows)
    quality = np.linspace(0.0, 1.0, rows)
    return pd.DataFrame(
        {
            "ticker": [f"T{i:02d}" for i in range(rows)],
            "score": score,
            "binary_target": [0, 1] * (rows // 2),
            "local_pairwise_quality": quality,
            "proxy": quality,
        }
    )


def test_session_metrics_use_deterministic_quartiles_top40_and_conditional_lift():
    metrics = session_proxy_metrics(_session_frame(), "proxy")
    assert metrics["eligible"] is True
    assert metrics["spearman"] == pytest.approx(1.0)
    assert metrics["q4_minus_q1_quality_lift"] > 0.0
    assert metrics["selective_quality_lift_at_40pct"] > 0.0
    assert metrics["conditional_quality_lift"] > 0.0


def test_exact_fold_windows_reject_out_of_window_rows():
    rows = []
    for fold in FOLDS:
        for idx in range(fold.validation_start, fold.validation_end + 1):
            rows.append({"fold": fold.name, "signal_session_index": idx})
    frame = pd.DataFrame(rows)
    validate_fold_windows(frame)
    broken = frame.copy()
    broken.loc[broken["fold"].eq("V2F1") & broken["signal_session_index"].eq(525), "signal_session_index"] = 524
    with pytest.raises(ReliabilityDataBlocked):
        validate_fold_windows(broken)


def _fold_metrics(proxy: str, spearman: list[float], lift: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "fold": [fold.name for fold in FOLDS],
            "proxy": [proxy] * 6,
            "median_session_spearman": spearman,
            "mean_q4_minus_q1_quality_lift": lift,
            "mean_selective_quality_lift_at_40pct": lift,
            "mean_conditional_quality_lift": lift,
        }
    )


def test_gate_requires_strict_positive_q25_and_four_positive_folds():
    proxy = PRIMARY_PROXIES[0]
    passing = _fold_metrics(proxy, [0.1] * 6, [0.1] * 6)
    assert evaluate_proxy_gate(passing, proxy)["qualified"] is True
    only_three_positive = _fold_metrics(proxy, [0.1, 0.1, 0.1, -0.1, -0.1, -0.1], [0.1] * 6)
    assert evaluate_proxy_gate(only_three_positive, proxy)["qualified"] is False
    q25_not_positive = _fold_metrics(proxy, [0.0, 0.0, 0.1, 0.1, 0.1, 0.1], [0.1] * 6)
    assert evaluate_proxy_gate(q25_not_positive, proxy)["qualified"] is False


def test_protected_runtime_flags_are_all_false():
    assert RUNTIME_FLAGS
    assert all(value is False for value in RUNTIME_FLAGS.values())
