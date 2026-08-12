from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from idx_trade.expected_payoff_v1 import (
    FEATURES_33,
    FEATURES_36,
    FEATURE_HASH,
    PayoffDataBlocked,
    evaluate_survivor_gate,
    feature_order_sha256,
    fit_fold_model,
    train_mean_baseline,
    validate_feature_order,
)


def _metrics(values: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "fold": [f"V2F{i}" for i in range(1, 7)],
            "mse_skill": values,
            "median_session_ic_atr": [0.01] * 6,
            "mean_d10_minus_d1_mean_payoff_atr": [0.01] * 6,
        }
    )


def test_frozen_feature_order_and_hash_are_exact():
    assert len(FEATURES_33) == 33
    assert FEATURES_36[-3:] == ["open_position", "open_to_high", "open_to_low"]
    assert feature_order_sha256(FEATURES_36) == FEATURE_HASH
    validate_feature_order(FEATURES_36)


@pytest.mark.parametrize("columns", [FEATURES_36[:-1], FEATURES_36 + ["extra"], FEATURES_36[1:] + FEATURES_36[:1]])
def test_feature_contract_rejects_missing_extra_or_reordered(columns):
    with pytest.raises(PayoffDataBlocked):
        validate_feature_order(columns)


def test_training_mean_baseline_and_zero_variance_fail_closed():
    mean, mse = train_mean_baseline(pd.Series([1.0, 2.0, 3.0]))
    assert mean == 2.0
    assert mse == pytest.approx(2 / 3)
    with pytest.raises(PayoffDataBlocked):
        train_mean_baseline(pd.Series([1.0, 1.0]))


def test_fold_model_uses_frozen_imputer_and_returns_finite_predictions():
    frame = pd.DataFrame({column: [float(i), np.nan, float(i + 2), float(i + 3)] for i, column in enumerate(FEATURES_36)})
    y = pd.Series([0.1, -0.1, 0.2, -0.2])
    imputer, model, mean, baseline = fit_fold_model(frame, y)
    pred = model.predict(imputer.transform(frame))
    assert np.isfinite(pred).all()
    assert mean == pytest.approx(0.0)
    assert baseline > 0
    assert model.get_params()["random_state"] == 42


def test_survivor_gate_requires_four_positive_skill_folds_and_strict_medians():
    result = evaluate_survivor_gate(_metrics([0.1, 0.1, 0.1, 0.1, -0.1, -0.1]), True)
    assert result["verdict"] == "EXPECTED_PAYOFF_V1_SURVIVOR"
    result = evaluate_survivor_gate(_metrics([0.1, 0.1, 0.1, -0.1, -0.1, -0.1]), True)
    assert result["verdict"] == "EXPECTED_PAYOFF_V1_NO_SURVIVOR"


def test_data_ready_gate_is_fail_closed():
    assert evaluate_survivor_gate(_metrics([0.1] * 6), False)["verdict"] == "EXPECTED_PAYOFF_V1_DATA_BLOCKED"
