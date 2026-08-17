from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def git_sha256(relative: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"HEAD:{relative}"],
        check=True,
        capture_output=True,
    )
    return hashlib.sha256(completed.stdout).hexdigest()


def test_execution_code_protocol_is_outcome_blind_and_still_blocks_history() -> None:
    protocol = json.loads(
        (ROOT / "config" / "ranking_v4_3_execution_code_protocol.json").read_text(
            encoding="utf-8"
        )
    )
    assert protocol["outcome_blind"] is True
    assert protocol["historical_target_access_authorized"] is False
    assert protocol["status"] == (
        "V4_3_EXECUTION_CODE_FREEZE_PENDING_LOCAL_SYNTHETIC_VALIDATION"
    )
    assert protocol["scientific_preregistration"]["canonical_git_sha256"] == (
        "3a54dcf0266f8a2808b8c1d73dda41a32baea368e6b48aac21e9fa073f6824ed"
    )
    assert git_sha256("config/ranking_v4_3_preregistration.json") == (
        protocol["scientific_preregistration"]["canonical_git_sha256"]
    )


def test_execution_source_list_is_unique_complete_and_currently_present() -> None:
    protocol = json.loads(
        (ROOT / "config" / "ranking_v4_3_execution_code_protocol.json").read_text(
            encoding="utf-8"
        )
    )
    paths = protocol["source_paths_to_freeze"]
    assert len(paths) == len(set(paths))
    required = {
        "src/idx_trade/ranking_v4_3_target_execution.py",
        "src/idx_trade/ranking_v4_3_features.py",
        "src/idx_trade/ranking_v4_3_model_eval.py",
        "scripts/run_v4_3_pit_support_refresh.py",
        "scripts/capture_v4_3_execution_code_manifest.py",
        "tests/test_ranking_v4_3_execution_code_capture.py",
    }
    assert required.issubset(paths)
    for relative in paths:
        assert (ROOT / relative).is_file(), relative


def test_capture_script_never_loads_data_or_runs_model_path() -> None:
    text = (
        ROOT / "scripts" / "capture_v4_3_execution_code_manifest.py"
    ).read_text(encoding="utf-8")
    assert ".fit(" not in text
    assert ".predict(" not in text
    assert "read_parquet" not in text
    assert "read_csv" not in text
    assert "target_rank_h5" not in text
    assert "target_rank_h10" not in text
    assert "provider_calls" in text
    assert '"historical_target_loaded": False' in text
    assert '"historical_model_fit": False' in text


def test_pit_support_refresh_declares_ca_continuity_separate_and_git_fold_hashing() -> None:
    text = (ROOT / "scripts" / "run_v4_3_pit_support_refresh.py").read_text(
        encoding="utf-8"
    )
    assert '"corporate_action_continuity_certified": False' in text
    assert "git_head_bytes" in text
    assert "VALIDATION_FOLD_REPO_PATH" in text
    assert '"validation_fold_hash_semantics"' in text
    assert "R5/R10" in text
