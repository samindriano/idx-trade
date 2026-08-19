from __future__ import annotations

import json
from pathlib import Path


CONFIG = Path("config/ranking_v4_3r_ca80_preregistration_v1.json")
RUNNER = Path("scripts/run_v4_3r_ca80_prefit_support_gate.py")


def test_v4_3r_is_explicit_new_generation_with_only_two_threshold_changes() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert cfg["generation_id"] == "V4_3R_CA80"
    assert cfg["outcome_blind"] is True
    assert cfg["historical_target_access_authorized"] is False
    changed = cfg["changed_from_v4_3"]
    assert set(changed) == {
        "prefit_date_full_target_support_gate",
        "evaluation_date_target_coverage_gate",
    }
    assert changed["prefit_date_full_target_support_gate"] == {"v4_3": 0.9, "v4_3r": 0.8}
    assert changed["evaluation_date_target_coverage_gate"] == {"v4_3": 0.9, "v4_3r": 0.8}


def test_row_level_fail_closed_and_scientific_model_contract_stay_frozen() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    unchanged = cfg["unchanged_scientific_contract"]
    assert unchanged["unsupported_rows_never_receive_target"] is True
    assert unchanged["known_or_unresolved_mechanical_crossing_never_passes_row_continuity"] is True
    assert unchanged["missing_ca_evidence_fails_closed_at_row_level"] is True
    assert unchanged["decision_universe"] == "V4_PRIMARY_LIQUID_CAUSAL_V1"
    assert unchanged["control"] == "V4_CONTROL_CONTEXT25_HGBR"
    assert unchanged["challenger"] == "V4_CHALLENGER_SESSION_GEOMETRY3"
    assert unchanged["learner_hyperparameter_search"] is False
    assert unchanged["validation_fold_count"] == 6
    assert unchanged["validation_dates_per_fold"] == 100
    assert unchanged["purge_official_sessions"] == 10
    assert unchanged["promotion_gates_unchanged"] is True


def test_runner_is_outcome_blind_and_provider_free() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "--parent-combined-replay-root" in source
    assert '"historical_target_loaded": False' in source
    assert '"model_fit": False' in source
    assert '"performance_computed": False' in source
    assert "curl_cffi" not in source
    assert "requests.get" not in source
    assert "HistGradientBoostingRegressor" not in source


def test_parent_manifest_and_folds_are_pinned() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert cfg["parent_outcome_blind_support"]["manifest_sha256"] == (
        "12d60b703d9617db95e89374485abb335a4024c4c6642a5cbee0d72e1eeb2f43"
    )
    assert cfg["validation_folds"]["sha256"] == (
        "91fe0e5a1c2489d5397f9f8bef7fc999d3f83a3f0cb94b6cdb5852c1e07cd915"
    )
    assert cfg["inherited_v4_3_lineage"]["preregistration_canonical_sha256"] == (
        "3a54dcf0266f8a2808b8c1d73dda41a32baea368e6b48aac21e9fa073f6824ed"
    )
