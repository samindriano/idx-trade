from pathlib import Path

import pandas as pd
import pytest

from idx_trade.stage3_development import (
    MAX_DEVELOPMENT_FUTURE_INDEX,
    MAX_DEVELOPMENT_SIGNAL_INDEX,
    _advancement_summary,
    _read_development_panel,
)


def test_stage3_access_bound_stays_before_locked_holdout():
    assert MAX_DEVELOPMENT_SIGNAL_INDEX == 942
    assert MAX_DEVELOPMENT_FUTURE_INDEX == 962
    assert MAX_DEVELOPMENT_FUTURE_INDEX < 1009


def test_advancement_rule_requires_two_folds_beating_both_baselines():
    rows = []
    for fold, candidate in (("F1", 0.60), ("F2", 0.58), ("F3", 0.49)):
        rows.extend(
            [
                {"fold": fold, "model_name": "base_rate", "pr_auc": 0.50},
                {"fold": fold, "model_name": "momentum_20", "pr_auc": 0.52},
                {"fold": fold, "model_name": "logistic_compact", "pr_auc": candidate},
                {"fold": fold, "model_name": "hist_gradient_boosting", "pr_auc": 0.51},
            ]
        )
    decision = _advancement_summary(pd.DataFrame(rows))
    assert decision["logistic_compact"]["directional_advancement_rule_met"]
    assert decision["logistic_compact"]["better_than_base_rate_and_momentum_folds"] == ["F1", "F2"]
    assert not decision["hist_gradient_boosting"]["directional_advancement_rule_met"]


def test_development_panel_reader_refuses_unfilterable_nonparquet_source(tmp_path: Path):
    path = tmp_path / "panel.csv"
    path.write_text("ticker,date\nAAA,2025-01-01\n", encoding="utf-8")
    with pytest.raises(ValueError, match="requires the frozen parquet panel"):
        _read_development_panel(path, pd.Timestamp("2025-03-20"))
