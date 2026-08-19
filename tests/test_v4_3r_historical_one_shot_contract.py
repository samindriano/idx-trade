from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "ranking_v4_3r_historical_execution_v1.json"
RUNNER = ROOT / "scripts" / "run_v4_3r_historical_one_shot.py"
OVERLAY = ROOT / "src" / "idx_trade" / "ranking_v4_3r_model_eval.py"


def test_historical_execution_is_exact_ca80_one_shot_with_forward_locked() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert cfg["generation_id"] == "V4_3R_CA80"
    assert cfg["one_shot"] is True
    assert cfg["historical_development_only"] is True
    assert cfg["evaluation_date_target_coverage_gate"] == 0.8
    assert cfg["v4_3_reference_date_target_coverage_gate"] == 0.9
    assert cfg["protected_forward_access_authorized"] is False
    assert cfg["execution_freeze"]["manifest_sha256"] == (
        "328713245465e0b5bb434bb4b4fd1bfdce4d8a19b419ac198446de2eb13811be"
    )
    assert cfg["prefit_support"]["manifest_sha256"] == (
        "0c222a10d8c48852f53451f0ce0bdec44b1156b8b9050c536f51b416ff18cfcc"
    )
    assert cfg["parent_combined_replay"]["manifest_sha256"] == (
        "12d60b703d9617db95e89374485abb335a4024c4c6642a5cbee0d72e1eeb2f43"
    )


def test_scientific_contract_has_no_new_model_or_feature_delta() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    unchanged = cfg["unchanged_scientific_contract"]
    assert unchanged["target_h5"] == "Close_(t+5) / Open_(t+1) - 1"
    assert unchanged["target_h10"] == "Close_(t+10) / Open_(t+1) - 1"
    assert unchanged["unsupported_rows_never_receive_target"] is True
    assert unchanged["known_or_unresolved_mechanical_crossing_remains_fail_closed"] is True
    assert unchanged["decision_universe"] == "V4_PRIMARY_LIQUID_CAUSAL_V1"
    assert unchanged["control"] == "V4_CONTROL_CONTEXT25_HGBR"
    assert unchanged["challenger"] == "V4_CHALLENGER_SESSION_GEOMETRY3"
    assert unchanged["validation_folds"] == "6x100"
    assert unchanged["purge_official_sessions"] == 10
    assert unchanged["top_k"] == 30
    assert unchanged["top30_min_observable"] == 27
    assert unchanged["hyperparameter_search"] is False
    assert unchanged["promotion_gates_unchanged"] is True
    for value in cfg["hard_boundaries"].values():
        assert value is False


def test_support_distribution_disclosure_cannot_be_hidden() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    disclosure = cfg["support_distribution_disclosure"]
    assert disclosure["frozen_validation_dates"] == 600
    assert disclosure["below_0.80"] == 0
    assert disclosure["0.80_to_below_0.90"] == 541
    assert disclosure["at_least_0.90"] == 59
    assert "original V4-3 >=90% generation remains failed" in disclosure["statement"]


def test_runner_marks_first_access_before_target_and_checks_parity_before_fit() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    marker = source.index('"HISTORICAL_TARGET_ACCESS_COMMENCED"')
    materialize = source.index("materialize_v4_target_ledger(", marker)
    parity = source.index("assert_target_support_parity(target_ledger, combined)", materialize)
    fit = source.index("run_models(model_frame, target_ledger, training_dates, folds)", parity)
    assert marker < materialize < parity < fit
    assert '"protected_forward_accessed": False' in source
    assert '"provider_calls": False' in source
    assert "REFUSE_OVERWRITE_EXISTING_OUTPUT" in source


def test_runner_uses_exact_frozen_model_core_and_no_network_or_rescue_path() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    overlay = OVERLAY.read_text(encoding="utf-8")
    assert "fit_v4_head" in source
    assert "score_v4_head" in source
    assert "evaluate_absolute_viability_gates" in source
    assert "evaluate_incremental_promotion_gates" in source
    assert "evaluate_head_by_date_ca80" in source
    assert "requests" not in source
    assert "curl_cffi" not in source
    assert "yfinance" not in source
    assert "GridSearchCV" not in source
    assert "RandomizedSearchCV" not in source
    assert "Optuna" not in source
    assert "DATE_TARGET_COVERAGE_GATE = 0.80" not in source
    assert "base.DATE_TARGET_COVERAGE_GATE = V4_3R_DATE_TARGET_COVERAGE_GATE" in overlay
    assert "finally:" in overlay
    assert "base.DATE_TARGET_COVERAGE_GATE = V4_3_REFERENCE_DATE_TARGET_COVERAGE_GATE" in overlay


def test_exact_runtime_and_scientific_blobs_are_pinned() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert cfg["runtime_manifest"]["sha256"] == (
        "cf6f1b0c859dd21b1c0f377f45d62ecdc98165ff6e0975b852a85b11cfbcaac6"
    )
    blobs = cfg["scientific_git_blobs"]
    assert blobs["src/idx_trade/ranking_v4_3_target_execution.py"] == (
        "9b82a0fe8bf06134a06e4a4bfdec15fd10b2bdf4"
    )
    assert blobs["src/idx_trade/ranking_v4_3_features.py"] == (
        "59ad05f815870ae00480dc7945fe18371d8eff9c"
    )
    assert blobs["src/idx_trade/ranking_v4_3_model_eval.py"] == (
        "8aba40c32e6069d1f8bdf5b8b19bf41d2065c422"
    )
    assert blobs["src/idx_trade/ranking_v4_3r_model_eval.py"]
    assert blobs["scripts/run_v4_3r_historical_one_shot.py"]
