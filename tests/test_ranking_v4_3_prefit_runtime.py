from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_prefit_protocol_pins_support_and_preregistration_bytes() -> None:
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
    required = protocol["required_repo_artifacts"]
    for relative, expected in required.items():
        assert sha256(ROOT / relative) == expected


def test_prefit_protocol_matches_frozen_learner_and_imputers() -> None:
    sklearn = pytest.importorskip("sklearn")
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


def test_prefit_capture_script_contains_no_fit_or_prediction_call() -> None:
    text = (ROOT / "scripts" / "capture_v4_3_prefit_environment.py").read_text(
        encoding="utf-8"
    )
    # Construction and get_params are allowed; executing model fit/predict is not.
    assert ".fit(" not in text
    assert ".predict(" not in text
    assert "target_rank_h5" not in text
    assert "target_rank_h10" not in text
