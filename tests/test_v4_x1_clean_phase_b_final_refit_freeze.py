from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WRAPPER = REPO_ROOT / "scripts" / "run_v4_x1_clean_phase_b_final_refit_freeze.py"
CORE = REPO_ROOT / "scripts" / "run_v4_x1_clean_phase_b_final_refit.py"
CONFIG = REPO_ROOT / "config" / "ranking_v4_x1_clean_phase_b_final_refit_v1.json"


def test_wrapper_enforces_frozen_boundary_before_target_materialization() -> None:
    source = WRAPPER.read_text(encoding="utf-8")
    assert "core.materialize_v4_target_ledger = frozen_materialize" in source
    assert "index.astype(int).le(int(frozen_end_index))" in source
    assert "original_materialize(retained" in source
    assert "post_freeze_numeric_target_accessed\": False" in source
    assert "FROZEN_HISTORICAL_TARGET_BOUNDARY_BEFORE_MATERIALIZATION_V1" in source


def test_wrapper_contains_no_scoring_evaluation_or_provider_path() -> None:
    source = WRAPPER.read_text(encoding="utf-8")
    assert "score_v4_head(" not in source
    assert ".predict(" not in source
    assert "evaluate_models(" not in source
    assert "evaluate_head_by_date_ca80(" not in source
    assert "requests." not in source
    assert "httpx." not in source
    assert "provider_calls\": False" in source
    assert "network_calls\": False" in source
    assert "forward_counter_mutated\": False" in source


def test_wrapper_pins_original_validation_folds_and_core() -> None:
    source = WRAPPER.read_text(encoding="utf-8")
    assert "91fe0e5a1c2489d5397f9f8bef7fc999d3f83a3f0cb94b6cdb5852c1e07cd915" in source
    assert "d18e23375076ca56d4a236217a2481c6f1c62f98" in source
    assert 'len(folds) != 600' in source
    assert 'set(range(1, 7))' in source
    assert '== 100' in source


def test_core_and_config_remain_exact_four_fit_contract() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    source = CORE.read_text(encoding="utf-8")
    assert cfg["required_fit_count"] == 4
    assert 'for mode in (CONTROL, CHALLENGER)' in source
    assert 'for head in ("H5", "H10")' in source
    assert "fit_v4_head(" in source
    assert "len(fit_log) != 4" in source


def test_execution_is_disabled_during_preparation() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert cfg["status"] == "V4_X1_CLEAN_PHASE_B_FINAL_REFIT_PREPARED_EXECUTION_NOT_AUTHORIZED"
    assert cfg["phase_b_refit_execution_authorized"] is False
