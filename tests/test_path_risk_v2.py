from __future__ import annotations

import numpy as np
import pandas as pd

from idx_trade.path_risk_v2 import (
    CR_CONTINUE,
    CR_HORIZON_COLUMN,
    CR_STOP,
    CR_TP,
    PATH_RISK_V2_DISCOVERY_FAIL,
    PATH_RISK_V2_DISCOVERY_WINNER,
    PATH_RISK_V2_FEATURE_COLUMNS,
    PR002_CANDIDATE,
    PR003_CANDIDATE,
    add_competing_risk_event_metadata,
    add_stop_touch_target,
    build_pr002_model,
    build_pr003_model,
    expand_competing_risk_training,
    path_risk_v2_candidate_gate,
    probability_metrics,
    score_pr003_cumulative_risk,
    select_path_risk_v2_candidate,
)


def _features(value: float = 1.0) -> dict[str, float]:
    return {column: value for column in PATH_RISK_V2_FEATURE_COLUMNS}


def test_stop_touch_target_semantics() -> None:
    frame = pd.DataFrame(
        [
            {"label_status": "SL_FIRST", "adverse_excursion_r": 1.2},
            {"label_status": "AMBIGUOUS_SAME_BAR", "adverse_excursion_r": 1.0},
            {"label_status": "TP_FIRST", "adverse_excursion_r": 0.3},
            {"label_status": "NO_BARRIER_HIT", "adverse_excursion_r": 0.8},
        ]
    )
    result = add_stop_touch_target(frame)
    assert result["stop_touch_h10"].tolist() == [1, 1, 0, 0]


def test_event_metadata_and_vectorized_competing_expansion() -> None:
    sessions = pd.date_range("2026-01-02", periods=12, freq="B")
    frame = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "date": sessions[0],
                "label_status": "SL_FIRST",
                "first_barrier_date": sessions[2],
                "adverse_excursion_r": 1.1,
                **_features(1.0),
            },
            {
                "ticker": "BBB",
                "date": sessions[0],
                "label_status": "TP_FIRST",
                "first_barrier_date": sessions[3],
                "adverse_excursion_r": 0.2,
                **_features(2.0),
            },
            {
                "ticker": "CCC",
                "date": sessions[0],
                "label_status": "NO_BARRIER_HIT",
                "first_barrier_date": pd.NaT,
                "adverse_excursion_r": 0.5,
                **_features(3.0),
            },
        ]
    )
    enriched = add_competing_risk_event_metadata(frame, sessions)
    assert enriched["event_day"].tolist()[:2] == [2.0, 3.0]
    assert np.isnan(enriched.iloc[2]["event_day"])
    assert enriched["event_cause"].tolist() == ["STOP", "TP", "NONE"]

    expanded = expand_competing_risk_training(enriched)
    assert len(expanded) == 2 + 3 + 10
    assert expanded[CR_HORIZON_COLUMN].min() == 1
    assert expanded[CR_HORIZON_COLUMN].max() == 10
    assert int((expanded["cr_target"] == CR_STOP).sum()) == 1
    assert int((expanded["cr_target"] == CR_TP).sum()) == 1
    assert int((expanded["cr_target"] == CR_CONTINUE).sum()) == 13


def test_models_use_frozen_columns_and_hgb_config() -> None:
    pr002 = build_pr002_model()
    assert tuple(pr002.named_steps["preprocess"].transformers[0][2]) == PATH_RISK_V2_FEATURE_COLUMNS
    assert pr002.named_steps["model"].get_params()["max_iter"] == 200
    pr003 = build_pr003_model()
    columns = tuple(pr003.named_steps["preprocess"].transformers[0][2])
    assert columns[:-1] == PATH_RISK_V2_FEATURE_COLUMNS
    assert columns[-1] == CR_HORIZON_COLUMN


def test_competing_risk_cumulative_mass_conservation() -> None:
    class _Estimator:
        classes_ = np.array([CR_CONTINUE, CR_STOP, CR_TP], dtype=int)

    class _FakeModel:
        named_steps = {"model": _Estimator()}

        def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
            return np.tile(np.array([[0.8, 0.1, 0.1]], dtype=float), (len(frame), 1))

    frame = pd.DataFrame(
        [
            {"ticker": "AAA", "date": pd.Timestamp("2026-01-02"), **_features(1.0)},
            {"ticker": "BBB", "date": pd.Timestamp("2026-01-02"), **_features(2.0)},
        ]
    )
    scored = score_pr003_cumulative_risk(_FakeModel(), frame)  # type: ignore[arg-type]
    assert np.all(scored["stop_probability_h3"] <= scored["stop_probability_h5"])
    assert np.all(scored["stop_probability_h5"] <= scored["stop_probability_h10"])
    total = (
        scored["stop_probability_h10"]
        + scored["tp_probability_h10"]
        + scored["survival_probability_h10"]
    )
    assert np.allclose(total, 1.0, rtol=0.0, atol=1e-10)
    assert float(scored["mass_error_h10"].max()) < 1e-10


def test_probability_metrics_and_frozen_gate() -> None:
    rows = []
    for date in pd.date_range("2026-01-02", periods=2, freq="B"):
        for index in range(10):
            target = int(index >= 5)
            rows.append(
                {
                    "date": date,
                    "ticker": f"T{index:03d}",
                    "stop_touch_h10": target,
                    "adverse_excursion_r": 1.1 if target else 0.2,
                    "prediction": 0.8 if target else 0.2,
                }
            )
    metrics = probability_metrics(pd.DataFrame(rows))
    assert metrics["roc_auc"] == 1.0
    assert metrics["q5_minus_q1_stop_touch_rate"] > 0

    passing = pd.DataFrame(
        {
            "fold": ["V2F1", "V2F2", "V2F3", "V2F4"],
            "relative_logloss_improvement_vs_base": [0.02, 0.01, 0.03, 0.01],
            "relative_brier_improvement_vs_base": [0.02, 0.01, 0.03, 0.01],
            "relative_logloss_improvement_vs_alpha": [0.01, 0.005, 0.01, 0.004],
            "roc_auc": [0.58, 0.57, 0.56, 0.59],
            "q5_minus_q1_stop_touch_rate": [0.10, 0.11, 0.09, 0.12],
        }
    )
    eligible, checks, _ = path_risk_v2_candidate_gate(passing)
    assert eligible
    assert all(checks.values())
    failed = passing.copy()
    failed["relative_logloss_improvement_vs_alpha"] = [-0.01, -0.01, 0.001, 0.001]
    assert not path_risk_v2_candidate_gate(failed)[0]


def test_selection_uses_alpha_increment_then_simplicity_tie_break() -> None:
    base = pd.DataFrame(
        {
            "fold": ["V2F1", "V2F2", "V2F3", "V2F4"],
            "relative_logloss_improvement_vs_base": [0.02, 0.01, 0.03, 0.01],
            "relative_brier_improvement_vs_base": [0.02, 0.01, 0.03, 0.01],
            "relative_logloss_improvement_vs_alpha": [0.01, 0.006, 0.009, 0.007],
            "roc_auc": [0.58, 0.57, 0.56, 0.59],
            "q5_minus_q1_stop_touch_rate": [0.10, 0.11, 0.09, 0.12],
        }
    )
    pr002 = base.assign(candidate=PR002_CANDIDATE)
    pr003 = base.assign(candidate=PR003_CANDIDATE)
    status, winner, _ = select_path_risk_v2_candidate(pd.concat([pr002, pr003], ignore_index=True))
    assert status == PATH_RISK_V2_DISCOVERY_WINNER
    assert winner == PR002_CANDIDATE

    pr003 = pr003.copy()
    pr003["relative_logloss_improvement_vs_alpha"] += 0.01
    status, winner, _ = select_path_risk_v2_candidate(pd.concat([pr002, pr003], ignore_index=True))
    assert status == PATH_RISK_V2_DISCOVERY_WINNER
    assert winner == PR003_CANDIDATE

    dead = pr002.copy()
    dead["relative_logloss_improvement_vs_alpha"] = -0.02
    dead2 = pr003.copy()
    dead2["relative_logloss_improvement_vs_alpha"] = -0.02
    status, winner, _ = select_path_risk_v2_candidate(pd.concat([dead, dead2], ignore_index=True))
    assert status == PATH_RISK_V2_DISCOVERY_FAIL
    assert winner is None
