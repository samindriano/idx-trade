from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from idx_trade.expected_payoff_v0 import PayoffDataBlocked
from idx_trade.expected_payoff_v1_correction import corrected_mse_skill, validation_baseline_mse


def test_validation_baseline_mse_uses_validation_outcomes_not_training_variance():
    train = np.array([0.0, 2.0])
    validation = np.array([10.0, 10.0])
    train_mean = float(train.mean())
    training_variance = float(np.mean((train - train_mean) ** 2))
    validation_mse = validation_baseline_mse(train_mean, validation)
    assert training_variance == pytest.approx(1.0)
    assert validation_mse == pytest.approx(81.0)
    assert validation_mse != training_variance


def test_corrected_skill_uses_validation_baseline_denominator():
    assert corrected_mse_skill(40.5, 81.0) == pytest.approx(0.5)
    with pytest.raises(PayoffDataBlocked):
        validation_baseline_mse(1.0, pd.Series(dtype=float))
