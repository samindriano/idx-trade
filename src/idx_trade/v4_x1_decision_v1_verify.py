from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .v4_x1_decision_v1_contract import (
    TARGET_POSITIONS, REQUIRED_SCORE_COLUMNS, EXPECTED_ALPHA_MODEL_ID,
    EXPECTED_ALPHA_MODEL_FINGERPRINT, EXPECTED_GENERATION, EXPECTED_FREEZE_BOUNDARY,
    EXPECTED_SCIENTIFIC_BLOBS, _VERIFIED_TOKEN, DecisionV1Error, VerifiedScoreSession,
    _sha256, _normalize_ticker, _read_manifest, _resolve_artifact,
)

def verify_v4_x1_score_artifact(manifest_path: str | Path) -> VerifiedScoreSession:
    manifest_path = Path(manifest_path).expanduser().resolve()
    if not manifest_path.is_file():
        raise DecisionV1Error(f"DECISION_V1_MANIFEST_MISSING:{manifest_path}")
    manifest_sha = _sha256(manifest_path)
    manifest = _read_manifest(manifest_path)

    if manifest.get("schema_version") != "v4_x1_prospective_score_manifest_v2":
        raise DecisionV1Error("DECISION_V1_UPSTREAM_SCHEMA_CHANGED")
    if manifest.get("status") != "DONE":
        raise DecisionV1Error("DECISION_V1_UPSTREAM_NOT_DONE")
    if manifest.get("model_id") != EXPECTED_ALPHA_MODEL_ID:
        raise DecisionV1Error("DECISION_V1_UPSTREAM_MODEL_ID_MISMATCH")
    if manifest.get("generation") != EXPECTED_GENERATION:
        raise DecisionV1Error("DECISION_V1_UPSTREAM_GENERATION_MISMATCH")
    if manifest.get("model_fingerprint") != EXPECTED_ALPHA_MODEL_FINGERPRINT:
        raise DecisionV1Error("DECISION_V1_UPSTREAM_MODEL_FINGERPRINT_MISMATCH")

    guards = manifest.get("guards")
    if not isinstance(guards, dict):
        raise DecisionV1Error("DECISION_V1_UPSTREAM_GUARDS_MISSING")
    for key in (
        "provider_calls",
        "protected_outcome_accessed",
        "realized_forward_outcome_loaded",
        "historical_prediction_generated",
        "model_refit",
        "model_retuned",
        "science_changed",
    ):
        if guards.get(key) is not False:
            raise DecisionV1Error(f"DECISION_V1_UPSTREAM_GUARD_CHANGED:{key}")

    model_bundle = manifest.get("model_bundle")
    if not isinstance(model_bundle, dict) or model_bundle.get("manifest_sha256") != EXPECTED_ALPHA_MODEL_FINGERPRINT:
        raise DecisionV1Error("DECISION_V1_UPSTREAM_MODEL_BUNDLE_CHANGED")

    freshness = manifest.get("freshness")
    if not isinstance(freshness, dict) or freshness.get("model_freeze_observed_by") != EXPECTED_FREEZE_BOUNDARY:
        raise DecisionV1Error("DECISION_V1_UPSTREAM_FREEZE_BOUNDARY_CHANGED")

    science = manifest.get("science")
    if not isinstance(science, dict):
        raise DecisionV1Error("DECISION_V1_UPSTREAM_SCIENCE_MISSING")
    if science.get("consensus_formula") != "0.5*H5_WITHIN_DATE_PERCENTILE_RANK+0.5*H10_WITHIN_DATE_PERCENTILE_RANK":
        raise DecisionV1Error("DECISION_V1_UPSTREAM_CONSENSUS_FORMULA_CHANGED")
    blobs = science.get("frozen_scientific_git_blobs")
    if not isinstance(blobs, dict):
        raise DecisionV1Error("DECISION_V1_UPSTREAM_SCIENTIFIC_BLOBS_MISSING")
    for path, expected_blob in EXPECTED_SCIENTIFIC_BLOBS.items():
        if blobs.get(path) != expected_blob:
            raise DecisionV1Error(f"DECISION_V1_UPSTREAM_SCIENTIFIC_BLOB_CHANGED:{path}")

    session_date = str(manifest.get("session_date") or "")
    parsed_session = pd.to_datetime(session_date, errors="coerce")
    if pd.isna(parsed_session):
        raise DecisionV1Error("DECISION_V1_UPSTREAM_SESSION_DATE_INVALID")
    normalized_session = pd.Timestamp(parsed_session).tz_localize(None).normalize().date().isoformat()
    if normalized_session != session_date:
        raise DecisionV1Error("DECISION_V1_UPSTREAM_SESSION_DATE_NOT_CANONICAL")

    output = manifest.get("output")
    if not isinstance(output, dict):
        raise DecisionV1Error("DECISION_V1_UPSTREAM_OUTPUT_MISSING")
    artifact_path = _resolve_artifact(manifest_path, output.get("artifact_path"))
    if not artifact_path.is_file():
        raise DecisionV1Error(f"DECISION_V1_ARTIFACT_MISSING:{artifact_path}")
    actual_artifact_sha = _sha256(artifact_path)
    declared_artifact_sha = str(output.get("artifact_sha256") or "")
    if actual_artifact_sha != declared_artifact_sha:
        raise DecisionV1Error("DECISION_V1_ARTIFACT_SHA_MISMATCH")

    declared_columns = output.get("columns")
    if not isinstance(declared_columns, list) or not set(REQUIRED_SCORE_COLUMNS).issubset(set(map(str, declared_columns))):
        raise DecisionV1Error("DECISION_V1_REQUIRED_OUTPUT_COLUMNS_NOT_DECLARED")

    try:
        scores = pd.read_parquet(artifact_path)
    except Exception as exc:
        raise DecisionV1Error("DECISION_V1_ARTIFACT_UNREADABLE") from exc
    if list(map(str, scores.columns)) != list(map(str, declared_columns)):
        raise DecisionV1Error("DECISION_V1_ARTIFACT_DECLARED_SCHEMA_MISMATCH")
    missing = set(REQUIRED_SCORE_COLUMNS) - set(scores.columns)
    if missing:
        raise DecisionV1Error(f"DECISION_V1_ARTIFACT_COLUMNS_MISSING:{sorted(missing)}")
    if int(manifest.get("rows", -1)) != len(scores) or len(scores) < TARGET_POSITIONS:
        raise DecisionV1Error("DECISION_V1_ARTIFACT_ROW_COUNT_INVALID")

    frame = scores.loc[:, list(REQUIRED_SCORE_COLUMNS)].copy()
    frame["ticker"] = frame["ticker"].map(_normalize_ticker)
    if frame["ticker"].duplicated().any():
        raise DecisionV1Error("DECISION_V1_ARTIFACT_DUPLICATE_TICKER")
    dates = pd.to_datetime(frame["date"], errors="coerce")
    if dates.isna().any():
        raise DecisionV1Error("DECISION_V1_ARTIFACT_DATE_INVALID")
    dates = dates.dt.tz_localize(None).dt.normalize()
    if not dates.eq(pd.Timestamp(session_date)).all():
        raise DecisionV1Error("DECISION_V1_ARTIFACT_DATE_MISMATCH")

    for column in ("alpha_h5", "alpha_h10", "alpha_consensus"):
        values = pd.to_numeric(frame[column], errors="coerce").astype(float)
        if not np.isfinite(values).all():
            raise DecisionV1Error(f"DECISION_V1_ARTIFACT_NONFINITE:{column}")
        if ((values < 0.0) | (values > 1.0)).any():
            raise DecisionV1Error(f"DECISION_V1_ARTIFACT_ALPHA_OUT_OF_RANGE:{column}")
        frame[column] = values
    expected_consensus = 0.5 * frame["alpha_h5"] + 0.5 * frame["alpha_h10"]
    if not np.allclose(frame["alpha_consensus"], expected_consensus, rtol=0.0, atol=1e-12):
        raise DecisionV1Error("DECISION_V1_ARTIFACT_CONSENSUS_MISMATCH")

    rank_numeric = pd.to_numeric(frame["rank_consensus"], errors="coerce")
    if rank_numeric.isna().any() or not np.equal(rank_numeric, np.floor(rank_numeric)).all():
        raise DecisionV1Error("DECISION_V1_ARTIFACT_RANK_NONINTEGER")
    ranks = rank_numeric.astype(int)
    if set(ranks.tolist()) != set(range(1, len(frame) + 1)):
        raise DecisionV1Error("DECISION_V1_ARTIFACT_RANK_NOT_CONTIGUOUS")
    frame["rank_consensus"] = ranks

    expected_order = frame.sort_values(
        ["alpha_consensus", "ticker"], ascending=[False, True], kind="mergesort"
    )["ticker"].tolist()
    actual_order = frame.sort_values("rank_consensus", kind="mergesort")["ticker"].tolist()
    if actual_order != expected_order:
        raise DecisionV1Error("DECISION_V1_ARTIFACT_RANK_ORDER_MISMATCH")

    tie_rows = int(frame["alpha_consensus"].duplicated(keep=False).sum())
    frame = frame.sort_values("rank_consensus", kind="mergesort").reset_index(drop=True)
    return VerifiedScoreSession(
        session_date=session_date,
        model_id=EXPECTED_ALPHA_MODEL_ID,
        model_fingerprint=EXPECTED_ALPHA_MODEL_FINGERPRINT,
        artifact_path=artifact_path,
        artifact_sha256=actual_artifact_sha,
        manifest_path=manifest_path,
        manifest_sha256=manifest_sha,
        scores=frame,
        alpha_tie_rows=tie_rows,
        _verification_token=_VERIFIED_TOKEN,
    )
