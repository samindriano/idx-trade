from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "ranking_v4_x1_final_refit_v1.json"
RUNNER = ROOT / "scripts" / "run_v4_x1_final_refit_freeze.py"
PREREG = ROOT / "config" / "ranking_v4_x1_prospective_preregistration_v1.json"


def test_v4_x1_final_refit_freezes_exactly_four_models() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert config["generation_id"] == "V4_X1_GEOMETRY3_PROSPECTIVE"
    assert config["required_fit_count"] == 4
    assert config["expected_head_eligible_dates"] == {"H5": 986, "H10": 982}
    assert config["model_contract"]["control_features"] == 25
    assert config["model_contract"]["challenger_features"] == 28
    assert config["model_contract"]["heads"] == ["H5", "H10"]
    assert config["model_contract"]["hyperparameter_search"] is False


def test_v4_x1_final_refit_forbids_historical_performance_and_predictions() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert config["historical_prediction_generation_authorized"] is False
    assert config["historical_performance_recomputation_authorized"] is False
    assert config["protected_forward_access_authorized"] is False
    assert config["provider_calls_authorized"] is False
    assert config["model_contract"]["historical_refit_performance_evaluation"] is False
    assert config["post_refit_boundary"]["historical_scores_must_not_be_generated"] is True
    assert config["post_refit_boundary"]["historical_performance_must_not_be_recomputed"] is True


def test_v4_x1_runner_has_fit_but_no_historical_scoring_or_gate_evaluation() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    assert "fit_v4_head(" in text
    assert "score_v4_head(" not in text
    assert "evaluate_head_by_date" not in text
    assert "evaluate_absolute_viability_gates" not in text
    assert "evaluate_incremental_promotion_gates" not in text
    assert "run_models(" not in text
    assert "evaluate_models(" not in text
    assert '"historical_prediction_generated": False' in text
    assert '"historical_performance_computed": False' in text


def test_v4_x1_refit_training_policy_is_all_ca80_eligible_only() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert config["final_training_policy"] == (
        "ALL_CA80_HEAD_ELIGIBLE_DATES_THROUGH_FROZEN_V4_3R_END"
    )
    source = RUNNER.read_text(encoding="utf-8")
    assert 'per_date[eligible_col]' in source
    assert "TARGET_H5_AVAILABLE" in source
    assert "TARGET_H10_AVAILABLE" in source
    assert "V4_X1_ELIGIBLE_DATE_AFTER_FROZEN_END" in source


def test_x1_prereg_and_refit_share_same_fresh_boundary() -> None:
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    refit = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert prereg["prospective_boundary"]["fresh_only"] is True
    assert prereg["prospective_boundary"]["interim_outcome_peeking"] is False
    assert "strictly after" in refit["first_eligible_score_session_rule"]
    assert refit["post_refit_boundary"]["prospective_scores_before_successful_manifest_are_ineligible"] is True
    assert refit["post_refit_boundary"]["once_first_prospective_score_is_captured_model_bytes_are_immutable"] is True


def test_v4_3r_no_survivor_parent_is_preserved() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    assert config["historical_selection_parent"]["status"] == "V4_3R_GENERATION_NO_SURVIVOR"
    assert prereg["scientific_parent"]["historical_verdict"] == "V4_3R_GENERATION_NO_SURVIVOR"
    assert prereg["scientific_parent"]["historical_result_manifest_sha256"] == config["historical_selection_parent"]["manifest_sha256"]
