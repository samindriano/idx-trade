from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from idx_trade.path_risk_v1 import (
    PATH_RISK_DISCOVERY_FAIL,
    PATH_RISK_DISCOVERY_PASS,
    PATH_RISK_FEATURE_COLUMNS,
    _assign_risk_quintiles,
    build_adverse_excursion_targets,
    build_path_risk_model,
    path_risk_discovery_gate,
    path_risk_metrics,
    pinball_loss,
    relative_pinball_improvement,
    training_q75_constant,
)


def _labels_and_path(status: str = "TP_FIRST") -> tuple[pd.DataFrame, pd.DataFrame, pd.DatetimeIndex]:
    sessions = pd.date_range("2026-01-02", periods=12, freq="B")
    closes = [100.0] * 12
    lows = [99.0] * 12
    highs = [101.0] * 12
    if status == "TP_FIRST":
        highs[2] = 104.0
    elif status == "SL_FIRST":
        lows[2] = 98.0
    elif status == "AMBIGUOUS_SAME_BAR":
        highs[2] = 104.0
        lows[2] = 98.0
    elif status == "NO_BARRIER_HIT":
        lows[4] = 99.5
    panel = pd.DataFrame({"ticker": "TEST", "date": sessions, "high": highs, "low": lows, "close": closes})
    first_date = sessions[2] if status != "NO_BARRIER_HIT" else pd.NaT
    labels = pd.DataFrame(
        {
            "ticker": ["TEST"],
            "signal_date": [sessions[0]],
            "signal_session_index": [1],
            "signal_reference_close": [100.0],
            "atr": [2.0],
            "sl_atr_multiple": [1.0],
            "reward_risk": [1.5],
            "tp_level": [103.0],
            "sl_level": [98.0],
            "label_status": [status],
            "first_barrier_date": [first_date],
        }
    )
    return labels, panel, sessions


@pytest.mark.parametrize("status", ["TP_FIRST", "SL_FIRST", "AMBIGUOUS_SAME_BAR", "NO_BARRIER_HIT"])
def test_target_status_semantics(status: str) -> None:
    labels, panel, sessions = _labels_and_path(status)
    result = build_adverse_excursion_targets(labels, panel, sessions)
    assert len(result) == 1
    target = float(result.iloc[0]["adverse_excursion_r"])
    if status in {"SL_FIRST", "AMBIGUOUS_SAME_BAR"}:
        assert target >= 1.0
    else:
        assert target < 1.0


def test_target_rejects_incomplete_future_path() -> None:
    labels, panel, sessions = _labels_and_path("NO_BARRIER_HIT")
    with pytest.raises(ValueError, match="incomplete"):
        build_adverse_excursion_targets(labels, panel.iloc[:10], sessions)


def test_target_rejects_barrier_identity_mismatch() -> None:
    labels, panel, sessions = _labels_and_path("TP_FIRST")
    labels.loc[0, "label_status"] = "SL_FIRST"
    with pytest.raises(ValueError, match="identity mismatch"):
        build_adverse_excursion_targets(labels, panel, sessions)


def test_target_does_not_depend_on_open() -> None:
    labels, panel, sessions = _labels_and_path("TP_FIRST")
    baseline = build_adverse_excursion_targets(labels, panel, sessions)
    panel["open"] = 1_000_000.0
    altered = build_adverse_excursion_targets(labels, panel, sessions)
    assert baseline["adverse_excursion_r"].equals(altered["adverse_excursion_r"])


def test_q75_model_is_frozen_without_fit() -> None:
    model = build_path_risk_model()
    assert model.named_steps["model"].get_params()["loss"] == "quantile"
    assert model.named_steps["model"].get_params()["quantile"] == 0.75
    assert tuple(model.named_steps["preprocess"].transformers[0][2]) == PATH_RISK_FEATURE_COLUMNS


def test_pinball_and_training_q75() -> None:
    assert training_q75_constant([0.0, 1.0, 2.0, 3.0]) == 2.25
    assert pinball_loss([0.0, 1.0], [0.0, 0.0]) == 0.375
    assert relative_pinball_improvement(1.0, 0.75) == 0.25


def test_path_risk_metrics_quintiles_and_finite_diagnostics() -> None:
    rows = []
    for date in pd.date_range("2026-01-02", periods=2, freq="B"):
        for index in range(10):
            rows.append({"date": date, "ticker": f"T{index:03d}", "adverse_excursion_r": float(index) / 10, "prediction": float(index) / 10})
    metrics = path_risk_metrics(pd.DataFrame(rows))
    assert metrics["rows"] == 20
    assert metrics["finite_prediction_rate"] == 1.0
    assert metrics["q5_minus_q1_adverse_excursion"] > 0
    assert len(_assign_risk_quintiles(pd.DataFrame(rows), prediction_column="prediction")) == 20


def test_discovery_gate_pass_and_fail_are_frozen() -> None:
    base = pd.DataFrame(
        {
            "fold": ["V2F1", "V2F2", "V2F3", "V2F4"],
            "relative_pinball_improvement": [0.03, 0.04, 0.02, 0.01],
            "spearman": [0.11, 0.12, 0.10, 0.09],
            "q5_minus_q1_adverse_excursion": [0.11, 0.12, 0.13, 0.14],
        }
    )
    verdict, checks = path_risk_discovery_gate(base)
    assert verdict == PATH_RISK_DISCOVERY_PASS
    assert all(checks.values())
    failed = base.copy()
    failed.loc[0, "relative_pinball_improvement"] = -0.2
    assert path_risk_discovery_gate(failed)[0] == PATH_RISK_DISCOVERY_FAIL
