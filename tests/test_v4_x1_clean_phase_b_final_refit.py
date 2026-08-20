from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pandas as pd
import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "scripts" / "run_v4_x1_clean_phase_b_final_refit.py"
CONFIG = REPO_ROOT / "config" / "ranking_v4_x1_clean_phase_b_final_refit_v1.json"
PARENT_CONFIG = REPO_ROOT / "config" / "ranking_v4_x1_final_refit_v1.json"


def _load_runner():
    spec = importlib.util.spec_from_file_location("v4_x1_clean_phase_b_test", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_source_has_fit_only_no_scoring_or_historical_evaluation_path() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "fit_v4_head(" in source
    assert "score_v4_head(" not in source
    assert ".predict(" not in source
    assert "evaluate_models(" not in source
    assert "run_models(" not in source
    assert "evaluate_head_by_date_ca80(" not in source
    assert "historical_result_root" not in source
    assert "prospective_scoring_authorized\": False" in source


def test_clean_representation_uses_phase_a_primary_and_open_lineage() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "phase_a.build_primary_model_frame(" in source
    assert "open_fix.apply_clean_open_lineage(" in source
    assert "phase_a.build_old_price_evidence(" in source
    assert "hist.prepare_model_frame(" not in source
    assert "phase_a_result[\"h5_support\"]" in source
    assert "phase_a_result[\"h10_support\"]" in source


def test_config_preserves_parent_model_contract_and_four_fit_policy() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    parent = json.loads(PARENT_CONFIG.read_text(encoding="utf-8"))
    assert cfg["required_fit_count"] == 4
    assert cfg["final_training_policy"] == parent["final_training_policy"]
    assert cfg["model_contract"] == parent["model_contract"]
    assert cfg["parent_generation_id"] == parent["generation_id"]
    assert cfg["ca80_gate_rate"] == 0.80


def test_config_hard_guards_allow_training_only() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    guards = cfg["hard_guards"]
    assert guards["historical_training_target_access_authorized"] is True
    assert guards["model_fit_authorized"] is True
    for key in (
        "provider_calls_authorized",
        "network_calls_authorized",
        "historical_prediction_generation_authorized",
        "historical_performance_recomputation_authorized",
        "model_scoring_authorized",
        "protected_forward_access_authorized",
        "fresh_forward_access_authorized",
        "forward_counter_mutation_authorized",
        "prospective_scoring_authorized",
        "v4_x2_session_semantics_authorized",
        "ca80_threshold_change_authorized",
        "hyperparameter_search_authorized",
        "data_repair_or_rescue_authorized",
    ):
        assert guards[key] is False


def test_target_support_identity_obeys_clean_eligible_dates() -> None:
    runner = _load_runner()
    target = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "AAA", "BBB"],
            "date": pd.to_datetime(["2026-01-02", "2026-01-02", "2026-01-05", "2026-01-05"]),
            "target_state_h5": ["TARGET_H5_AVAILABLE", "NO", "TARGET_H5_AVAILABLE", "TARGET_H5_AVAILABLE"],
            "target_state_h10": ["TARGET_H10_AVAILABLE", "TARGET_H10_AVAILABLE", "NO", "TARGET_H10_AVAILABLE"],
        }
    )
    per_date = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-02", "2026-01-05"]),
            "h5_eligible": [True, False],
            "h10_eligible": [True, True],
        }
    )
    h5 = runner.target_support_identity(target, per_date, head="H5")
    h10 = runner.target_support_identity(target, per_date, head="H10")
    assert list(zip(h5["ticker"], h5["date"].dt.strftime("%Y-%m-%d"))) == [("AAA", "2026-01-02")]
    assert list(zip(h10["ticker"], h10["date"].dt.strftime("%Y-%m-%d"))) == [
        ("AAA", "2026-01-02"),
        ("BBB", "2026-01-02"),
        ("BBB", "2026-01-05"),
    ]


def test_support_identity_mismatch_fails_closed() -> None:
    runner = _load_runner()
    actual = pd.DataFrame({"ticker": ["AAA"], "date": ["2026-01-02"]})
    expected = pd.DataFrame({"ticker": ["BBB"], "date": ["2026-01-02"]})
    with pytest.raises(RuntimeError, match="SUPPORT_IDENTITY_MISMATCH"):
        runner._assert_same_identity(actual, expected, label="H5")


def test_accepted_phase_a_counts_are_frozen() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert cfg["accepted_clean_support_rows"] == {"H5": 239648, "H10": 237976}
    assert cfg["accepted_clean_primary_rows"] == 348762
    assert cfg["accepted_clean_training_date_counts"] == {
        "F1_H5": 368,
        "F1_H10": 364,
        "F2_H5": 468,
        "F2_H10": 464,
        "F3_H5": 568,
        "F3_H10": 564,
        "F4_H5": 668,
        "F4_H10": 664,
        "F5_H5": 768,
        "F5_H10": 764,
        "F6_H5": 868,
        "F6_H10": 864,
    }
