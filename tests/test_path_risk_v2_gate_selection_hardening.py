from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from idx_trade import path_risk_v2 as v2
from idx_trade import path_risk_v2_discovery_run as run


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "docs" / "PATH_RISK_V2_SPEC.md"


def _passing_gate_frame(*, candidate: str | None = None) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "fold": ["V2F1", "V2F2", "V2F3", "V2F4"],
            "relative_logloss_improvement_vs_base": [0.02, 0.01, 0.03, 0.01],
            "relative_brier_improvement_vs_base": [0.02, 0.01, 0.03, 0.01],
            "relative_logloss_improvement_vs_alpha": [0.01, 0.005, 0.01, 0.004],
            "roc_auc": [0.58, 0.57, 0.56, 0.59],
            "q5_minus_q1_stop_touch_rate": [0.10, 0.11, 0.09, 0.12],
        }
    )
    if candidate is not None:
        frame["candidate"] = candidate
    return frame


_INDIVIDUAL_GATE_FAILURES = (
    (
        "all_required_metrics_finite",
        "relative_logloss_improvement_vs_base",
        [0.02, np.nan, 0.03, 0.01],
    ),
    (
        "logloss_vs_base_nonnegative_3_of_4",
        "relative_logloss_improvement_vs_base",
        [-0.001, -0.001, 0.02, 0.02],
    ),
    (
        "median_logloss_vs_base_ge_0_005",
        "relative_logloss_improvement_vs_base",
        [0.004, 0.004, 0.004, 0.004],
    ),
    (
        "brier_vs_base_nonnegative_3_of_4",
        "relative_brier_improvement_vs_base",
        [-0.001, -0.001, 0.02, 0.02],
    ),
    (
        "logloss_vs_alpha_nonnegative_3_of_4",
        "relative_logloss_improvement_vs_alpha",
        [-0.001, -0.001, 0.02, 0.02],
    ),
    (
        "median_logloss_vs_alpha_ge_0_002",
        "relative_logloss_improvement_vs_alpha",
        [0.001, 0.001, 0.001, 0.001],
    ),
    (
        "roc_gt_half_3_of_4",
        "roc_auc",
        [0.5, 0.5, 0.7, 0.7],
    ),
    (
        "median_roc_ge_0_55",
        "roc_auc",
        [0.51, 0.52, 0.53, 0.54],
    ),
    (
        "positive_q5_q1_spread_4_of_4",
        "q5_minus_q1_stop_touch_rate",
        [0.0, 0.10, 0.10, 0.10],
    ),
    (
        "median_q5_q1_spread_ge_0_08",
        "q5_minus_q1_stop_touch_rate",
        [0.01, 0.02, 0.03, 0.04],
    ),
)


@pytest.mark.parametrize(
    ("failed_check", "column", "values"),
    _INDIVIDUAL_GATE_FAILURES,
)
def test_each_frozen_gate_condition_fails_independently(
    failed_check: str,
    column: str,
    values: list[float],
) -> None:
    metrics = _passing_gate_frame()
    metrics[column] = values

    eligible, checks, _ = v2.path_risk_v2_candidate_gate(metrics)

    assert not eligible
    assert checks[failed_check] is False


def test_frozen_gate_boundary_counts_and_strict_roc_semantics() -> None:
    boundary = _passing_gate_frame()
    boundary["relative_logloss_improvement_vs_base"] = [0.01, 0.01, 0.01, -0.01]
    boundary["relative_brier_improvement_vs_base"] = [0.01, 0.01, 0.01, -0.01]
    boundary["relative_logloss_improvement_vs_alpha"] = [0.01, 0.01, 0.01, -0.01]
    boundary["roc_auc"] = [0.50, 0.60, 0.60, 0.60]
    boundary["q5_minus_q1_stop_touch_rate"] = [0.01, 0.10, 0.10, 0.10]

    eligible, checks, aggregate = v2.path_risk_v2_candidate_gate(boundary)

    assert eligible
    assert aggregate["nonnegative_logloss_vs_base_folds"] == 3
    assert aggregate["nonnegative_brier_vs_base_folds"] == 3
    assert aggregate["nonnegative_logloss_vs_alpha_folds"] == 3
    assert aggregate["roc_gt_half_folds"] == 3
    assert aggregate["positive_spread_folds"] == 4
    assert checks["roc_gt_half_3_of_4"]

    strict_roc_failure = boundary.copy()
    strict_roc_failure["roc_auc"] = [0.50, 0.50, 0.60, 0.60]
    eligible, checks, aggregate = v2.path_risk_v2_candidate_gate(strict_roc_failure)
    assert not eligible
    assert aggregate["roc_gt_half_folds"] == 2
    assert checks["roc_gt_half_3_of_4"] is False


def test_median_thresholds_are_inclusive() -> None:
    metrics = _passing_gate_frame()
    metrics["relative_logloss_improvement_vs_base"] = [0.005] * 4
    metrics["relative_logloss_improvement_vs_alpha"] = [0.002] * 4
    metrics["roc_auc"] = [0.55] * 4
    metrics["q5_minus_q1_stop_touch_rate"] = [0.08] * 4

    eligible, checks, aggregate = v2.path_risk_v2_candidate_gate(metrics)

    assert eligible
    assert aggregate["median_logloss_vs_base"] == 0.005
    assert aggregate["median_logloss_vs_alpha"] == 0.002
    assert aggregate["median_roc_auc"] == 0.55
    assert aggregate["median_q5_minus_q1_stop_touch_rate"] == 0.08
    assert checks["median_logloss_vs_base_ge_0_005"]
    assert checks["median_logloss_vs_alpha_ge_0_002"]
    assert checks["median_roc_ge_0_55"]
    assert checks["median_q5_q1_spread_ge_0_08"]


def test_relative_improvement_is_positive_only_when_candidate_loss_is_lower() -> None:
    assert v2.relative_improvement(0.8, 0.6) == pytest.approx(0.25)
    assert v2.relative_improvement(0.8, 0.8) == pytest.approx(0.0)
    assert v2.relative_improvement(0.8, 1.0) == pytest.approx(-0.25)


def _selection_frame(
    *,
    pr002_alpha: float = 0.010,
    pr003_alpha: float = 0.010,
) -> pd.DataFrame:
    pr002 = _passing_gate_frame(candidate=v2.PR002_CANDIDATE)
    pr003 = _passing_gate_frame(candidate=v2.PR003_CANDIDATE)
    pr002["relative_logloss_improvement_vs_alpha"] = pr002_alpha
    pr003["relative_logloss_improvement_vs_alpha"] = pr003_alpha
    return pd.concat([pr002, pr003], ignore_index=True)


def test_neither_eligible_candidate_fails_closed() -> None:
    metrics = _selection_frame(pr002_alpha=-0.010, pr003_alpha=-0.020)

    status, winner, details = v2.select_path_risk_v2_candidate(metrics)

    assert status == v2.PATH_RISK_V2_DISCOVERY_FAIL
    assert winner is None
    assert details[v2.PR002_CANDIDATE]["eligible"] is False
    assert details[v2.PR003_CANDIDATE]["eligible"] is False


def test_exactly_one_eligible_candidate_is_selected() -> None:
    metrics = _selection_frame(pr002_alpha=0.010, pr003_alpha=-0.020)

    status, winner, details = v2.select_path_risk_v2_candidate(metrics)

    assert status == v2.PATH_RISK_V2_DISCOVERY_WINNER
    assert winner == v2.PR002_CANDIDATE
    assert details[v2.PR002_CANDIDATE]["eligible"] is True
    assert details[v2.PR003_CANDIDATE]["eligible"] is False


def test_both_eligible_candidates_choose_higher_alpha_increment_outside_tie() -> None:
    metrics = _selection_frame(pr002_alpha=0.010, pr003_alpha=0.013)

    status, winner, _ = v2.select_path_risk_v2_candidate(metrics)

    assert status == v2.PATH_RISK_V2_DISCOVERY_WINNER
    assert winner == v2.PR003_CANDIDATE


def test_both_eligible_candidates_choose_simpler_pr002_at_exact_tie_tolerance() -> None:
    metrics = _selection_frame(pr002_alpha=0.002, pr003_alpha=0.004)

    status, winner, details = v2.select_path_risk_v2_candidate(metrics)

    assert details[v2.PR003_CANDIDATE]["aggregate"]["median_logloss_vs_alpha"] - details[
        v2.PR002_CANDIDATE
    ]["aggregate"]["median_logloss_vs_alpha"] == pytest.approx(
        v2.PATH_RISK_V2_SELECTION_TIE_TOLERANCE
    )
    assert status == v2.PATH_RISK_V2_DISCOVERY_WINNER
    assert winner == v2.PR002_CANDIDATE


def test_both_eligible_candidates_choose_higher_candidate_just_outside_tie() -> None:
    metrics = _selection_frame(
        pr002_alpha=0.002,
        pr003_alpha=0.002 + v2.PATH_RISK_V2_SELECTION_TIE_TOLERANCE + 1e-6,
    )

    status, winner, _ = v2.select_path_risk_v2_candidate(metrics)

    assert status == v2.PATH_RISK_V2_DISCOVERY_WINNER
    assert winner == v2.PR003_CANDIDATE


def test_probability_bounds_and_nonfinite_gate_metrics_fail_closed() -> None:
    dates = pd.date_range("2026-01-02", periods=2, freq="B")
    rows = [
        {
            "date": date,
            "ticker": f"T{index:02d}",
            "stop_touch_h10": int(index >= 5),
            "adverse_excursion_r": 1.1 if index >= 5 else 0.2,
            "prediction": 0.8 if index >= 5 else 0.2,
        }
        for date in dates
        for index in range(10)
    ]
    scored = pd.DataFrame(rows)

    for invalid in (np.nan, np.inf, -0.01, 1.01):
        invalid_scored = scored.copy()
        invalid_scored.loc[0, "prediction"] = invalid
        with pytest.raises(ValueError, match="finite probabilities"):
            v2.probability_metrics(invalid_scored)

    nonfinite_gate = _passing_gate_frame()
    nonfinite_gate.loc[0, "roc_auc"] = np.inf
    eligible, checks, _ = v2.path_risk_v2_candidate_gate(nonfinite_gate)
    assert not eligible
    assert checks["all_required_metrics_finite"] is False


def test_candidate_universe_is_fixed_and_f5_f6_rows_are_rejected() -> None:
    with pytest.raises(ValueError, match="exactly"):
        v2.select_path_risk_v2_candidate(
            pd.concat(
                [
                    _passing_gate_frame(candidate=v2.PR002_CANDIDATE),
                    _passing_gate_frame(candidate=v2.PR003_CANDIDATE),
                    _passing_gate_frame(candidate="PATH-RISK-V2-PR-004"),
                ],
                ignore_index=True,
            )
        )

    f5_row = _passing_gate_frame(candidate=v2.PR002_CANDIDATE).iloc[[0]].copy()
    f5_row["fold"] = "V2F5"
    with pytest.raises(ValueError, match="exact F1-F4"):
        v2.select_path_risk_v2_candidate(
            pd.concat([_selection_frame(), f5_row], ignore_index=True)
        )

    assert tuple(run._folds())
    assert tuple(fold.name for fold in run._folds()) == v2.PATH_RISK_V2_DISCOVERY_FOLDS
    assert max(fold.validation_end for fold in run._folds()) == v2.PATH_RISK_V2_MAX_SIGNAL_SESSION


def test_ece_and_spearman_are_diagnostics_not_selection_gates() -> None:
    metrics = _selection_frame(pr002_alpha=0.010, pr003_alpha=0.013)
    metrics["ece_10_equal_width"] = 0.0
    metrics["spearman_vs_adverse_excursion"] = 1.0
    status, winner, _ = v2.select_path_risk_v2_candidate(metrics)

    diagnostics_changed = metrics.copy()
    diagnostics_changed["ece_10_equal_width"] = 1.0
    diagnostics_changed["spearman_vs_adverse_excursion"] = -1.0
    changed_status, changed_winner, _ = v2.select_path_risk_v2_candidate(diagnostics_changed)

    assert (status, winner) == (v2.PATH_RISK_V2_DISCOVERY_WINNER, v2.PR003_CANDIDATE)
    assert (changed_status, changed_winner) == (status, winner)


def test_frozen_spec_constants_and_candidate_boundary_match_code() -> None:
    spec_text = SPEC_PATH.read_text(encoding="utf-8")
    source_text = (ROOT / "src" / "idx_trade" / "path_risk_v2.py").read_text(encoding="utf-8")

    assert run._normalized_git_blob_sha1(SPEC_PATH) == v2.PATH_RISK_V2_SPEC_GIT_BLOB
    assert v2.PATH_RISK_V2_CANDIDATES == (v2.PR002_CANDIDATE, v2.PR003_CANDIDATE)
    assert v2.PATH_RISK_V2_DISCOVERY_FOLDS == ("V2F1", "V2F2", "V2F3", "V2F4")
    assert v2.PATH_RISK_V2_HORIZON == 10
    assert v2.PATH_RISK_V2_MAX_SIGNAL_SESSION == 984
    assert v2.PATH_RISK_V2_SELECTION_TIE_TOLERANCE == 0.002
    assert v2.PATH_RISK_V2_FEATURE_ORDER_SHA256 in spec_text
    assert v2.PR002_CANDIDATE in spec_text
    assert v2.PR003_CANDIDATE in spec_text
    assert "PR-004" not in source_text
    assert not re.search(r"PR001(?:_CANDIDATE|_HYPOTHESIS)?", source_text)

    for phrase in (
        "relative log-loss improvement vs base rate is `>=0` on at least `3/4` folds",
        "median relative log-loss improvement vs base rate is `>= +0.005`",
        "relative Brier improvement vs base rate is `>=0` on at least `3/4` folds",
        "relative log-loss improvement vs alpha-only is `>=0` on at least `3/4` folds",
        "median relative log-loss improvement vs alpha-only is `>= +0.002`",
        "ROC-AUC is `>0.5` on at least `3/4` folds and median ROC-AUC is `>=0.55`",
        "Q5-Q1 stop-touch-rate spread is positive on `4/4` folds",
        "median Q5-Q1 stop-touch-rate spread is `>= +0.08`",
        "If the two medians differ by `<=0.002`, choose simpler PR-002.",
    ):
        assert phrase in spec_text
