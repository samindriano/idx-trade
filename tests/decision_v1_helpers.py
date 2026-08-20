from __future__ import annotations

import hashlib
import json
from pathlib import Path
import random

import numpy as np
import pandas as pd
import pytest

import idx_trade.v4_x1_decision_v1 as decision_mod
from idx_trade.v4_x1_decision_v1 import (
    DecisionV1Error,
    EXPECTED_ALPHA_MODEL_FINGERPRINT,
    EXPECTED_ALPHA_MODEL_ID,
    EXPECTED_CONFIG_SHA256,
    ShadowPortfolioState,
    TARGET_POSITIONS,
    VerifiedScoreSession,
    plan_decision_v1,
    verify_frozen_config,
    verify_v4_x1_score_artifact,
)


def _scores(n: int = 30, date: str = "2026-08-21") -> pd.DataFrame:
    h5 = np.linspace(1.0, 0.0, n, endpoint=False)
    h10 = np.linspace(0.98, 0.02, n, endpoint=False)
    consensus = 0.5 * h5 + 0.5 * h10
    return pd.DataFrame({
        "ticker": [f"T{i:02d}" for i in range(1, n + 1)],
        "date": pd.Timestamp(date),
        "alpha_h5": h5,
        "alpha_h10": h10,
        "alpha_consensus": consensus,
        "rank_consensus": np.arange(1, n + 1),
    })


def _write_artifact(tmp_path: Path, monkeypatch, frame: pd.DataFrame | None = None, *, manifest_mutator=None):
    frame = _scores() if frame is None else frame.copy()
    artifact = tmp_path / "score_artifact.parquet"
    artifact.write_bytes(b"synthetic-parquet-bytes")
    artifact_sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
    monkeypatch.setattr(pd, "read_parquet", lambda path: frame.copy())
    manifest = {
        "schema_version": "v4_x1_prospective_score_manifest_v2",
        "model_id": EXPECTED_ALPHA_MODEL_ID,
        "generation": "V4-X1-CLEAN",
        "model_fingerprint": EXPECTED_ALPHA_MODEL_FINGERPRINT,
        "session_date": pd.Timestamp(frame["date"].iloc[0]).date().isoformat(),
        "status": "DONE",
        "science": {
            "consensus_formula": "0.5*H5_WITHIN_DATE_PERCENTILE_RANK+0.5*H10_WITHIN_DATE_PERCENTILE_RANK",
            "frozen_scientific_git_blobs": {
                "src/idx_trade/ranking_v4_3_features.py": "59ad05f815870ae00480dc7945fe18371d8eff9c",
                "src/idx_trade/ranking_v4_3_preregistration.py": "cc1308feb51bbed16606bf7bded1ca0111644326",
            },
        },
        "model_bundle": {"manifest_sha256": EXPECTED_ALPHA_MODEL_FINGERPRINT},
        "freshness": {"model_freeze_observed_by": "2026-08-20T12:08:44+00:00"},
        "rows": len(frame),
        "output": {
            "artifact_path": str(artifact),
            "artifact_sha256": artifact_sha,
            "columns": list(frame.columns),
        },
        "guards": {
            "provider_calls": False,
            "protected_outcome_accessed": False,
            "realized_forward_outcome_loaded": False,
            "historical_prediction_generated": False,
            "model_refit": False,
            "model_retuned": False,
            "science_changed": False,
        },
    }
    if manifest_mutator:
        manifest_mutator(manifest)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    return manifest_path, artifact


def _verified(tmp_path: Path, monkeypatch, frame: pd.DataFrame | None = None) -> VerifiedScoreSession:
    manifest, _ = _write_artifact(tmp_path, monkeypatch, frame)
    return verify_v4_x1_score_artifact(manifest)


def _verified_direct(frame: pd.DataFrame | None = None) -> VerifiedScoreSession:
    frame = _scores() if frame is None else frame.copy()
    return VerifiedScoreSession(
        session_date=pd.Timestamp(frame["date"].iloc[0]).date().isoformat(),
        model_id=EXPECTED_ALPHA_MODEL_ID,
        model_fingerprint=EXPECTED_ALPHA_MODEL_FINGERPRINT,
        artifact_path=Path("artifact.parquet"),
        artifact_sha256="test",
        manifest_path=Path("manifest.json"),
        manifest_sha256="test",
        scores=frame.sort_values("rank_consensus", kind="mergesort").reset_index(drop=True),
        alpha_tie_rows=0,
        _verification_token=decision_mod._VERIFIED_TOKEN,
    )


def _state(ranks: list[int], date="2026-08-20") -> ShadowPortfolioState:
    return ShadowPortfolioState(date, tuple(f"T{i:02d}" for i in ranks))


__all__ = [name for name in globals() if not name.startswith("__")]
