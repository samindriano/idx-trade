from __future__ import annotations

import importlib.util
import json
from pathlib import Path


RUNNER = Path("scripts/run_v4_3_ca_training_domain_idx_combined_replay.py")
RUNNER_V2 = Path("scripts/run_v4_3_ca_training_domain_idx_combined_replay_v2.py")
CONFIG = Path("config/v4_3_ca_training_domain_idx_combined_replay_v1.json")


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frozen_config_pins_both_adjudications_and_gate() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert config["gate_rate"] == 0.90
    assert config["ksei_schedule80_adjudication"]["resolved_events"] == 21
    assert config["idx_schedule59_adjudication"]["resolved_events"] == 12
    assert config["idx_schedule59_adjudication"]["conflict_events"] == 0
    assert config["idx_schedule59_adjudication"]["residual_events"] == 59
    assert config["idx_schedule59_adjudication"]["residual_event_identity_sha256"] == (
        "f1c587eca59a9e7ec68cb8b1b2fc0980489a8f8a1b608f10403f2cc9f6d85707"
    )
    for value in config["hard_boundaries"].values():
        assert value is False


def test_v2_adds_only_legacy_verifier_metadata() -> None:
    module = _load(RUNNER_V2, "idx_combined_replay_v2_test")
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    compat = module.v1.base_compat_config(config)
    assert compat["schema_version"] == "v4_3_ca_training_domain_schedule_80_replay_v1"
    assert compat["outcome_blind"] is True
    assert compat["parent_replay"] == config["base_replay"]
    assert compat["adjudication_parent"] == config["ksei_schedule80_adjudication"]
    assert compat["gate_rate"] == config["gate_rate"]


def test_runner_remains_outcome_blind_and_provider_free() -> None:
    source = RUNNER.read_text(encoding="utf-8") + RUNNER_V2.read_text(encoding="utf-8")
    forbidden = (
        "requests.get",
        "curl_cffi",
        "materialize_v4_target_ledger",
        "HistGradientBoostingRegressor",
        "fit_v4_head(",
        "score_v4_head(",
        "compute_v4_3_model_eval",
    )
    for token in forbidden:
        assert token not in source
    assert "historical_target_loaded\": False" in source
    assert "model_fit\": False" in source
    assert "performance_computed\": False" in source


def test_idx_overlay_is_applied_only_after_ksei_residual_identity_check() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    ksei_apply = source.index("after_ksei, ksei_overlay = base.apply_adjudication")
    residual_identity = source.index("POST_KSEI_RESIDUAL_IDENTITY_CHANGED")
    idx_apply = source.index("replayed_events, idx_overlay = apply_idx_adjudication")
    assert ksei_apply < residual_identity < idx_apply
