import numpy as np
import pandas as pd

import idx_trade.research_stage4b as stage4b
from idx_trade.research_stage4b import (
    CAUSAL_PRIOR_ONLY_60,
    ISOTONIC_PRIOR_SHIFT_60,
    ISOTONIC_PRIOR_SHIFT_126,
    STATIC_BASE_RATE,
    STATIC_ISOTONIC,
    causal_recent_prior_audit,
    prior_shift_probability,
    stage4b_readiness,
)


def test_prior_shift_is_odds_correction_and_monotonic():
    probability = np.array([0.2, 0.4, 0.7])
    unchanged = prior_shift_probability(probability, 0.4, 0.4)
    np.testing.assert_allclose(unchanged, probability)

    lower_prior = prior_shift_probability(probability, 0.4, 0.2)
    assert np.all(lower_prior < probability)
    assert np.all(np.diff(lower_prior) > 0)

    higher_prior = prior_shift_probability(probability, 0.4, 0.6)
    assert np.all(higher_prior > probability)
    assert np.all(np.diff(higher_prior) > 0)


def _simple_calendar(periods=220):
    return pd.date_range("2024-01-01", periods=periods, freq="D")


def _resolved_table(calendar):
    rows = []
    for date_index, date in enumerate(calendar):
        for security in range(25):
            rows.append(
                {
                    "ticker": f"T{security:02d}",
                    "date": date,
                    "binary_target": int((date_index + security) % 3 == 0),
                }
            )
    return pd.DataFrame(rows)


def test_recent_prior_uses_only_matured_signal_dates(monkeypatch):
    calendar = _simple_calendar()
    monkeypatch.setattr(stage4b, "normalize_calendar", lambda values: pd.DatetimeIndex(values))
    table = _resolved_table(calendar)
    prediction_date = calendar[150]

    audit = causal_recent_prior_audit(
        table,
        [prediction_date],
        calendar,
        window=60,
        horizon=10,
        min_rows=1000,
    ).iloc[0]

    assert audit["prediction_session_index"] == 151
    assert audit["maturity_cutoff_session_index"] == 141
    assert audit["prior_window_start_session_index"] == 82
    assert audit["max_prior_source_signal_date"] <= audit["maturity_cutoff_date"]
    assert bool(audit["causal_audit_pass"])
    assert audit["recent_resolved_rows"] == 60 * 25


def test_recent_prior_is_invariant_to_future_target_changes(monkeypatch):
    calendar = _simple_calendar()
    monkeypatch.setattr(stage4b, "normalize_calendar", lambda values: pd.DatetimeIndex(values))
    table = _resolved_table(calendar)
    prediction_date = calendar[150]

    first = causal_recent_prior_audit(
        table,
        [prediction_date],
        calendar,
        window=60,
        horizon=10,
        min_rows=1000,
    )["recent_prior"].iloc[0]

    mutated = table.copy()
    mutated.loc[mutated["date"] > calendar[140], "binary_target"] = 1 - mutated.loc[
        mutated["date"] > calendar[140], "binary_target"
    ]
    second = causal_recent_prior_audit(
        mutated,
        [prediction_date],
        calendar,
        window=60,
        horizon=10,
        min_rows=1000,
    )["recent_prior"].iloc[0]

    assert first == second


def _metrics_frame(primary_brier=0.19, primary_ece=0.02):
    candidates = [
        STATIC_BASE_RATE,
        STATIC_ISOTONIC,
        CAUSAL_PRIOR_ONLY_60,
        ISOTONIC_PRIOR_SHIFT_60,
        ISOTONIC_PRIOR_SHIFT_126,
    ]
    pooled_values = {
        STATIC_BASE_RATE: (0.22, 0.04),
        STATIC_ISOTONIC: (0.21, 0.035),
        CAUSAL_PRIOR_ONLY_60: (0.20, 0.03),
        ISOTONIC_PRIOR_SHIFT_60: (primary_brier, primary_ece),
        ISOTONIC_PRIOR_SHIFT_126: (0.195, 0.025),
    }
    pooled = []
    fold = []
    for candidate in candidates:
        brier, ece = pooled_values[candidate]
        pooled.append(
            {
                "candidate": candidate,
                "pr_auc": 0.4,
                "roc_auc": 0.53,
                "brier": brier,
                "ece": ece,
                "log_loss": 0.65,
                "positive_rate": 0.35,
                "mean_probability": 0.35,
                "prevalence_gap": 0.01,
            }
        )
        for index, name in enumerate(("F1", "F2", "F3")):
            gap = 0.01 if candidate == ISOTONIC_PRIOR_SHIFT_60 else 0.03
            fold.append(
                {
                    "fold": name,
                    "candidate": candidate,
                    "pr_auc": 0.4,
                    "roc_auc": 0.53,
                    "brier": brier,
                    "ece": ece,
                    "log_loss": 0.65,
                    "positive_rate": 0.35,
                    "mean_probability": 0.35,
                    "prevalence_gap": gap + (0.001 * index),
                }
            )
    return pd.DataFrame(fold), pd.DataFrame(pooled)


def test_readiness_requires_primary_60_to_beat_static_and_dynamic_baselines():
    fold, pooled = _metrics_frame()
    audit = pd.DataFrame({"causal_audit_pass": [True, True, True]})
    decision = stage4b_readiness(fold, pooled, audit, holdout_outcome_accessed=False)
    assert decision["calibration_freeze_ready"]
    assert decision["decision"] == "STAGE4B_CALIBRATION_FREEZE_READY"

    blocked_fold, blocked_pooled = _metrics_frame(primary_brier=0.205, primary_ece=0.02)
    blocked = stage4b_readiness(blocked_fold, blocked_pooled, audit, holdout_outcome_accessed=False)
    assert not blocked["pooled_brier_beats_causal_prior_only"]
    assert not blocked["calibration_freeze_ready"]
    assert blocked["decision"] == "STAGE4B_CALIBRATION_STILL_BLOCKED"


def test_sensitivity_126_cannot_rescue_failed_primary_60():
    fold, pooled = _metrics_frame(primary_brier=0.23, primary_ece=0.05)
    pooled.loc[pooled["candidate"].eq(ISOTONIC_PRIOR_SHIFT_126), ["brier", "ece"]] = [0.10, 0.005]
    audit = pd.DataFrame({"causal_audit_pass": [True]})
    decision = stage4b_readiness(fold, pooled, audit, holdout_outcome_accessed=False)
    assert not decision["calibration_freeze_ready"]


def test_holdout_access_blocks_readiness_even_with_good_metrics():
    fold, pooled = _metrics_frame()
    audit = pd.DataFrame({"causal_audit_pass": [True]})
    decision = stage4b_readiness(fold, pooled, audit, holdout_outcome_accessed=True)
    assert not decision["holdout_outcome_accessed_false"]
    assert not decision["calibration_freeze_ready"]
