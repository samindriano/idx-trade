import pandas as pd

from idx_trade.open_alpha_historical import (
    CONTROL_MODEL,
    MODEL_FEATURES,
    V21_MODEL,
    V22_MODEL,
    _ranking_metrics,
    frozen_hgb_model,
)
from idx_trade.open_alpha_prereg import (
    CONTROL_FEATURE_COLUMNS,
    V21_FEATURE_COLUMNS,
    V22_FEATURE_COLUMNS,
)


def test_historical_runner_has_only_three_separate_feature_identities():
    assert tuple(MODEL_FEATURES[CONTROL_MODEL]) == tuple(CONTROL_FEATURE_COLUMNS)
    assert tuple(MODEL_FEATURES[V21_MODEL]) == tuple(V21_FEATURE_COLUMNS)
    assert tuple(MODEL_FEATURES[V22_MODEL]) == tuple(V22_FEATURE_COLUMNS)
    assert [len(MODEL_FEATURES[name]) for name in (CONTROL_MODEL, V21_MODEL, V22_MODEL)] == [25, 28, 28]
    assert all(len(columns) != 31 for columns in MODEL_FEATURES.values())


def test_frozen_hgb_model_rejects_combined_diagnostic_feature_order():
    combined = tuple(CONTROL_FEATURE_COLUMNS) + (
        "open_position",
        "open_to_high",
        "open_to_low",
        "open_position_prev_active_range",
        "open_to_prev_high",
        "open_to_prev_low",
    )
    try:
        frozen_hgb_model(combined)
    except ValueError as error:
        assert "unfrozen feature order" in str(error)
    else:
        raise AssertionError("31-feature diagnostic order must not be a fitted candidate")


def test_metric_evaluator_matches_frozen_bucket_semantics():
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-01"] * 10),
            "ticker": list("ABCDEFGHIJ"),
            "binary_target": [0, 0, 0, 0, 0, 1, 1, 1, 1, 1],
        }
    )
    metrics = _ranking_metrics(frame, list(range(10)))
    assert metrics["pr_auc"] > metrics["positive_rate"]
    assert metrics["q5_minus_q1"] > 0
    assert metrics["top_decile_lift"] > 0
