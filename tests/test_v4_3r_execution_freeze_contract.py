from __future__ import annotations

import json
from pathlib import Path


CONFIG = Path("config/ranking_v4_3r_execution_freeze_v1.json")
RUNNER = Path("scripts/capture_v4_3r_execution_freeze.py")


def test_execution_freeze_pins_exact_passed_prefit_manifest() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert cfg["schema_version"] == "ranking_v4_3r_execution_freeze_v1"
    assert cfg["generation_id"] == "V4_3R_CA80"
    assert cfg["outcome_blind"] is True
    assert cfg["historical_target_access_authorized_before_capture"] is False
    prefit = cfg["prefit_support_result"]
    assert prefit["manifest_sha256"] == (
        "0c222a10d8c48852f53451f0ce0bdec44b1156b8b9050c536f51b416ff18cfcc"
    )
    assert prefit["expected_status"] == (
        "V4_3R_CA80_PREFIT_SUPPORT_PASS_READY_TO_FREEZE_EXECUTION"
    )
    assert prefit["support_gate"] == 0.8
    assert prefit["historical_execution_authorized"] is True
    assert prefit["frozen_consensus_support_buckets"] == {
        "below_0.80": 0,
        "0.80_to_below_0.90": 541,
        "at_least_0.90": 59,
    }


def test_execution_freeze_preserves_scientific_core() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    science = cfg["scientific_contract"]
    assert science["only_generation_delta"] == (
        "date-level target-support/evaluation coverage threshold 0.90 -> 0.80"
    )
    assert science["unsupported_rows_never_receive_target"] is True
    assert science["known_or_unresolved_mechanical_crossing_remains_fail_closed"] is True
    assert science["control"] == "V4_CONTROL_CONTEXT25_HGBR"
    assert science["challenger"] == "V4_CHALLENGER_SESSION_GEOMETRY3"
    assert science["folds"] == "6x100"
    assert science["purge_official_sessions"] == 10
    assert science["top_k"] == 30
    assert science["top30_min_observable"] == 27
    assert science["learner_or_hyperparameter_change"] is False
    assert science["feature_change"] is False
    assert science["promotion_gate_change"] is False


def test_inherited_v4_3_scientific_blobs_are_explicitly_frozen() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    blobs = cfg["inherited_v4_3_scientific_git_blobs"]
    assert blobs == {
        "config/ranking_v4_3_target_execution_protocol.json": "c3fab424c49022c8d6e223f3d722a3b3b55637f8",
        "src/idx_trade/ranking_v4_3_preregistration.py": "cc1308feb51bbed16606bf7bded1ca0111644326",
        "src/idx_trade/ranking_v4_3_target_execution.py": "9b82a0fe8bf06134a06e4a4bfdec15fd10b2bdf4",
        "src/idx_trade/ranking_v4_3_features.py": "59ad05f815870ae00480dc7945fe18371d8eff9c",
        "src/idx_trade/ranking_v4_3_model_eval.py": "8aba40c32e6069d1f8bdf5b8b19bf41d2065c422",
    }


def test_capture_is_target_blind_provider_free_and_requires_clean_exact_runtime() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "--prefit-root" in source
    assert "GIT_WORKTREE_NOT_CLEAN" in source
    assert "PYTHON_VERSION_MISMATCH" in source
    assert "RUNTIME_PACKAGE_VERSION_MISMATCH" in source
    assert "PREFIT_MANIFEST_SHA_MISMATCH" in source
    assert '"historical_target_loaded": False' in source
    assert '"model_fit": False' in source
    assert '"performance_computed": False' in source
    assert '"provider_calls": False' in source
    assert "requests.get" not in source
    assert "curl_cffi" not in source
    assert "HistGradientBoostingRegressor" not in source


def test_post_capture_authorization_excludes_protected_forward() -> None:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    auth = cfg["post_capture_authorization"]
    assert auth["historical_target_materialization"] is True
    assert auth["historical_model_fit"] is True
    assert auth["historical_prediction_generation"] is True
    assert auth["historical_performance_computation"] is True
    assert auth["protected_forward_access"] is False
