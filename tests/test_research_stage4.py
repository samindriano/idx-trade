import numpy as np
import pandas as pd

from idx_trade.research_features import BASELINE_FEATURE_COLUMNS
from idx_trade.research_stage4 import (
    ABLATION_VARIANTS,
    CALIBRATOR_ORDER,
    FEATURE_FAMILIES,
    assign_cross_sectional_quintiles,
    attribution_summary,
    calibration_readiness,
    daily_regime_metrics,
    probability_bin_edges,
    quintile_summary,
    select_calibrator,
    stage4_hgb_pipeline,
)


def test_feature_families_partition_frozen_registry_exactly_once():
    flattened = [column for columns in FEATURE_FAMILIES.values() for column in columns]
    assert sorted(flattened) == sorted(BASELINE_FEATURE_COLUMNS)
    assert len(flattened) == len(set(flattened)) == len(BASELINE_FEATURE_COLUMNS)
    assert ABLATION_VARIANTS["HGB_FULL"] == tuple(BASELINE_FEATURE_COLUMNS)
    for family, columns in FEATURE_FAMILIES.items():
        variant = ABLATION_VARIANTS[f"HGB_NO_{family}"]
        assert set(variant) == set(BASELINE_FEATURE_COLUMNS) - set(columns)


def test_stage4_hgb_rejects_features_outside_frozen_registry():
    try:
        stage4_hgb_pipeline(["close_return_20", "future_return"])
    except ValueError as error:
        assert "outside frozen registry" in str(error)
    else:
        raise AssertionError("unexpected Stage-4 feature should fail closed")


def test_probability_bins_are_training_defined_and_cover_unit_interval():
    edges = probability_bin_edges([0.1, 0.2, 0.3, 0.7, 0.9])
    assert edges[0] == 0.0
    assert edges[-1] == 1.0
    assert np.all(np.diff(edges) >= 0)


def test_cross_sectional_quintiles_are_date_local_and_deterministic():
    rows = []
    for fold in ("F1", "F2"):
        for date in pd.to_datetime(["2024-01-02", "2024-01-03"]):
            for i in range(10):
                rows.append(
                    {
                        "fold": fold,
                        "date": date,
                        "ticker": f"T{i:02d}",
                        "target": int(i >= 6),
                        "raw_score": float(i),
                    }
                )
    frame = pd.DataFrame(rows)
    first = assign_cross_sectional_quintiles(frame.sample(frac=1.0, random_state=1))
    second = assign_cross_sectional_quintiles(frame.sample(frac=1.0, random_state=2))
    pd.testing.assert_frame_equal(first, second)
    counts = first.groupby(["fold", "date", "score_quintile"]).size()
    assert counts.eq(2).all()
    summary = quintile_summary(first)
    q5 = summary[(summary["fold"].eq("F1")) & summary["quintile"].eq(5)].iloc[0]
    assert bool(q5["q5_gt_q1"])
    assert q5["q5_minus_q1"] > 0


def test_daily_regime_metrics_uses_primary_liquid_rows_only():
    frame = pd.DataFrame(
        {
            "ticker": ["A", "B", "C", "A", "B", "C"],
            "date": pd.to_datetime(["2024-01-02"] * 3 + ["2024-01-03"] * 3),
            "universe_primary_liquid": [True, True, False, True, True, False],
            "close_return_20": [0.1, 0.3, 99.0, -0.2, 0.0, -99.0],
            "atr14_over_close": [0.02, 0.04, 9.0, 0.03, 0.05, 9.0],
        }
    )
    result = daily_regime_metrics(frame).set_index("date")
    assert result.loc[pd.Timestamp("2024-01-02"), "trend_metric"] == 0.2
    assert result.loc[pd.Timestamp("2024-01-03"), "trend_metric"] == -0.1
    assert result["regime_source_rows"].eq(2).all()


def test_attribution_rule_is_directional_and_does_not_search_subsets():
    rows = []
    full = {"F1": 0.40, "F2": 0.41, "F3": 0.42}
    for fold, value in full.items():
        rows.append({"fold": fold, "variant": "HGB_FULL", "pr_auc": value})
    for family in FEATURE_FAMILIES:
        variant = f"HGB_NO_{family}"
        for fold, value in full.items():
            delta = -0.01 if family == "STRUCTURE" else 0.001
            rows.append({"fold": fold, "variant": variant, "pr_auc": value + delta})
    summary = attribution_summary(pd.DataFrame(rows)).set_index("family")
    assert summary.loc["STRUCTURE", "attribution_status"] == "CONTRIBUTES_DIRECTIONALLY"
    assert summary.loc["MOMENTUM", "attribution_status"] == "CONSISTENTLY_HARMFUL"


def test_calibrator_selection_is_brier_then_ece_then_simplicity():
    pooled = pd.DataFrame(
        {
            "calibrator": list(CALIBRATOR_ORDER),
            "brier": [0.220000001, 0.220000002, 0.23],
            "weighted_fold_ece": [0.04, 0.03, 0.01],
        }
    )
    assert select_calibrator(pooled) == "PLATT"


def test_calibration_readiness_requires_probability_quality_not_ranking_only():
    fold_metrics = pd.DataFrame(
        {
            "fold": ["F1", "F2", "F3"],
            "calibrator": ["PLATT"] * 3,
            "brier": [0.21, 0.22, 0.23],
            "ece": [0.02, 0.02, 0.02],
            "prevalence_gap": [0.01, 0.01, 0.01],
        }
    )
    pooled = pd.DataFrame(
        {
            "calibrator": ["PLATT"],
            "brier": [0.22],
            "weighted_fold_ece": [0.02],
        }
    )
    base = pd.DataFrame(
        {
            "fold": ["F1", "F2", "F3"],
            "brier": [0.23, 0.23, 0.23],
            "ece": [0.03, 0.03, 0.03],
            "prevalence_gap": [0.02, 0.02, 0.02],
            "rows": [100, 100, 100],
        }
    )
    decision = calibration_readiness(
        "PLATT",
        fold_metrics,
        pooled,
        base,
        base_pooled_brier=0.23,
        base_weighted_ece=0.03,
    )
    assert decision["calibration_ready"]

    blocked = calibration_readiness(
        "PLATT",
        fold_metrics,
        pooled.assign(weighted_fold_ece=0.04),
        base,
        base_pooled_brier=0.23,
        base_weighted_ece=0.03,
    )
    assert not blocked["calibration_ready"]
