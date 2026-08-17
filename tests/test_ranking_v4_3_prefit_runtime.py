from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_head_sha256(relative: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"HEAD:{relative}"],
        check=True,
        capture_output=True,
    )
    return sha256_bytes(completed.stdout)


def test_prefit_protocol_pins_support_and_preregistration_canonical_git_bytes() -> None:
    protocol = json.loads(
        (ROOT / "config" / "ranking_v4_3_prefit_runtime_protocol.json").read_text(
            encoding="utf-8"
        )
    )
    assert protocol["outcome_blind"] is True
    assert (
        protocol["status"]
        == "V4_3_PREFIT_RUNTIME_CAPTURE_PROTOCOL_LOCKED_NO_TARGET_OR_MODEL_RUN"
    )
    assert "canonical tracked bytes at Git HEAD" in protocol[
        "required_repo_artifact_hash_semantics"
    ]
    required = protocol["required_repo_artifacts"]
    for relative, expected in required.items():
        assert (ROOT / relative).is_file()
        assert git_head_sha256(relative) == expected


def test_prefit_protocol_matches_frozen_learner_and_imputers() -> None:
    pytest.importorskip("sklearn")
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.impute import SimpleImputer

    protocol = json.loads(
        (ROOT / "config" / "ranking_v4_3_prefit_runtime_protocol.json").read_text(
            encoding="utf-8"
        )
    )
    learner = protocol["learner"]
    estimator = HistGradientBoostingRegressor(
        loss=learner["loss"], **learner["parameters"]
    )
    effective = estimator.get_params(deep=False)
    for key, expected in {"loss": learner["loss"], **learner["parameters"]}.items():
        assert effective[key] == expected

    for name in ("control", "geometry"):
        cfg = protocol["imputers"][name]
        imputer = SimpleImputer(
            strategy=cfg["strategy"],
            add_indicator=cfg["add_indicator"],
            keep_empty_features=cfg["keep_empty_features"],
        )
        params = imputer.get_params(deep=False)
        assert params["strategy"] == cfg["strategy"]
        assert params["add_indicator"] == cfg["add_indicator"]
        assert params["keep_empty_features"] == cfg["keep_empty_features"]


def test_prefit_capture_script_uses_git_head_bytes_and_records_checkout_bytes() -> None:
    text = (ROOT / "scripts" / "capture_v4_3_prefit_environment.py").read_text(
        encoding="utf-8"
    )
    assert '"show", f"HEAD:{relative}"' in text
    assert "repo_git_head_sha256" in text
    assert "repo_worktree_sha256" in text
    assert "required_artifact_actual_git_sha256" in text
    assert "required_artifact_worktree_sha256" in text


def test_prefit_capture_script_contains_no_fit_or_prediction_call() -> None:
    text = (ROOT / "scripts" / "capture_v4_3_prefit_environment.py").read_text(
        encoding="utf-8"
    )
    # Construction and get_params are allowed; executing model fit/predict is not.
    assert ".fit(" not in text
    assert ".predict(" not in text
    assert "target_rank_h5" not in text
    assert "target_rank_h10" not in text
