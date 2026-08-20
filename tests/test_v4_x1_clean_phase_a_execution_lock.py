from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "capture_v4_x1_clean_phase_a_execution_lock.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("v4_x1_clean_phase_a_execution_lock", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


lock = _load_module()


def _valid_config() -> dict[str, object]:
    return {
        "schema_version": "ranking_v4_x1_clean_phase_a_execution_lock_v1",
        "generation_id": "V4_X1_CLEAN_REMEDIATED_PROSPECTIVE_V1",
        "phase": "PHASE_A_OUTCOME_BLIND_STRUCTURAL_REPLAY",
        "hard_guards": {
            "provider_calls_authorized": False,
            "network_calls_authorized": False,
            "numeric_target_access_authorized": False,
            "model_fit_authorized": False,
            "model_scoring_authorized": False,
            "historical_prediction_authorized": False,
            "historical_performance_authorized": False,
            "protected_forward_outcome_access_authorized": False,
            "forward_counter_mutation_authorized": False,
            "session_semantics_change_authorized": False,
            "data_repair_authorized": False,
        },
    }


def test_verify_config_accepts_frozen_guard_set(tmp_path: Path) -> None:
    repo = tmp_path
    config_dir = repo / "config"
    config_dir.mkdir()
    config = config_dir / "ranking_v4_x1_clean_phase_a_execution_lock_v1.json"
    config.write_text("{}", encoding="utf-8")
    lock.verify_config(repo, config, _valid_config())


@pytest.mark.parametrize(
    "guard",
    [
        "provider_calls_authorized",
        "network_calls_authorized",
        "numeric_target_access_authorized",
        "model_fit_authorized",
        "model_scoring_authorized",
        "historical_prediction_authorized",
        "historical_performance_authorized",
        "protected_forward_outcome_access_authorized",
        "forward_counter_mutation_authorized",
        "session_semantics_change_authorized",
        "data_repair_authorized",
    ],
)
def test_verify_config_rejects_any_relaxed_guard(tmp_path: Path, guard: str) -> None:
    repo = tmp_path
    config_dir = repo / "config"
    config_dir.mkdir()
    config = config_dir / "ranking_v4_x1_clean_phase_a_execution_lock_v1.json"
    config.write_text("{}", encoding="utf-8")
    cfg = _valid_config()
    cfg["hard_guards"][guard] = True  # type: ignore[index]
    with pytest.raises(RuntimeError, match="V4_X1_CLEAN_LOCK_GUARD_CHANGED"):
        lock.verify_config(repo, config, cfg)


def test_sha256_file_is_deterministic(tmp_path: Path) -> None:
    path = tmp_path / "sample.bin"
    path.write_bytes(b"idx-trade-clean-lock")
    assert lock.sha256_file(path) == lock.sha256_file(path)


def test_sha256_file_fails_closed_on_missing_input(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="V4_X1_CLEAN_LOCK_INPUT_MISSING"):
        lock.sha256_file(tmp_path / "missing.bin")
