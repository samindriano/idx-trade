"""Outcome-blind Reliability V1 score-margin sidecar for the O2 archive.

This module consumes an already-written, hash-pinned O2 score artifact.  It
does not read OHLCV, labels, outcomes, the O2 model, or the O2 counter.  The
sidecar is subordinate metadata and is deliberately kept outside the
``model_runs`` table and the official O2 counter.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from .forward_model_runtime import (
    O2_FEATURE_ORDER_SHA256,
    O2_MODEL_ID,
    O2_MODEL_MANIFEST_SHA256,
    O2_MODEL_SHA256,
    _connection,
    _paths,
)
from .provenance import sha256_file, write_manifest_atomic
from .storage import write_parquet_atomic


RELIABILITY_MODEL_ID = "RELIABILITY-V1-SCORE-MARGIN-SHADOW"
RELIABILITY_GENERATION = "RELIABILITY-V1-SHADOW"
RELIABILITY_FORMULA_VERSION = "score_margin_reliability_v1"
RELIABILITY_SHADOW_ROOT = "reliability_v1_shadow/score_margin"
EXPECTED_FIRST_SESSION_DATE = "2026-08-12"
EXPECTED_FIRST_O2_SCORE_SHA256 = "b7fc6f22230500d65c1a24c4333b5601c0102da5bb99c3cae77a85bdb112c42d"
EXPECTED_FIRST_O2_MANIFEST_SHA256 = "4f3d7814333b867316092758b8530270a14d2e741bc8cca2c12c1dffbc99b5e2"

PROTECTED_FLAGS = {
    "provider_calls": False,
    "source_recapture_or_repair": False,
    "o2_refit": False,
    "o2_rescore": False,
    "reliability_model_fit": False,
    "composite_reliability_score_created": False,
    "tier_or_threshold_optimization": False,
    "trade_filtering": False,
    "independent_reliability_counter_registration": False,
    "fresh_forward_outcomes_accessed": False,
    "forward_outcome_access_marker_written": False,
}


def _normal_date(value: object) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_localize(None)
    return timestamp.normalize()


def _implementation_commit() -> str:
    """Resolve the checkout identity without making a network or data call."""

    try:
        repo_root = Path(__file__).resolve().parents[2]
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return "UNAVAILABLE_CHECKOUT_ID"


def _sidecar_paths(paths: Any, session_key: str) -> dict[str, Path]:
    root = paths.monitor_root / RELIABILITY_SHADOW_ROOT / session_key
    return {
        "root": root,
        "artifact": root / "reliability_artifact.parquet",
        "manifest": root / "manifest.json",
    }


def _find_o2_source(paths: Any, session_key: str) -> tuple[Path, Path, dict[str, Any]]:
    root = paths.monitor_root / "model_runs" / session_key
    candidates: list[tuple[Path, dict[str, Any]]] = []
    for manifest_path in sorted(root.glob("*/*manifest.json")):
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            continue
        if payload.get("model_id") == O2_MODEL_ID:
            candidates.append((manifest_path, payload))
    if not candidates:
        raise FileNotFoundError(f"accepted O2 score manifest not found for {session_key}")
    if len(candidates) != 1:
        raise RuntimeError(f"ambiguous O2 score manifests for {session_key}")

    manifest_path, payload = candidates[0]
    artifact_value = payload.get("score_artifact_path")
    if not artifact_value:
        raise RuntimeError(f"O2 score manifest has no score artifact path for {session_key}")
    artifact_path = Path(str(artifact_value))
    if not artifact_path.is_file() or not manifest_path.is_file():
        raise FileNotFoundError(f"O2 score artifact bundle is incomplete for {session_key}")
    if sha256_file(artifact_path) != str(payload.get("score_artifact_sha256")):
        raise RuntimeError(f"O2 score artifact hash mismatch for {session_key}")
    if payload.get("status") != "DONE":
        raise RuntimeError(f"O2 score manifest is not DONE for {session_key}")
    if payload.get("session_date") != session_key:
        raise RuntimeError(f"O2 score manifest date mismatch for {session_key}")
    if payload.get("model_sha256") != O2_MODEL_SHA256:
        raise RuntimeError(f"O2 model hash mismatch for {session_key}")
    if payload.get("model_manifest_sha256") != O2_MODEL_MANIFEST_SHA256:
        raise RuntimeError(f"O2 model-manifest hash mismatch for {session_key}")
    if payload.get("feature_order_sha256") != O2_FEATURE_ORDER_SHA256:
        raise RuntimeError(f"O2 feature-order hash mismatch for {session_key}")
    if payload.get("outcome_blind") is not True:
        raise RuntimeError(f"O2 score manifest is not outcome-blind for {session_key}")
    if payload.get("fresh_forward_outcomes_accessed") is not False:
        raise RuntimeError(f"O2 score manifest has invalid outcome flag for {session_key}")
    if payload.get("forward_outcome_access_marker_written") is not False:
        raise RuntimeError(f"O2 score manifest has invalid marker flag for {session_key}")
    if payload.get("official_session_index") is None:
        raise RuntimeError(f"O2 score manifest has no official session index for {session_key}")

    actual_manifest_sha = sha256_file(manifest_path)
    if session_key == EXPECTED_FIRST_SESSION_DATE:
        if str(payload.get("score_artifact_sha256")) != EXPECTED_FIRST_O2_SCORE_SHA256:
            raise RuntimeError("first accepted O2 score artifact does not match frozen pin")
        if actual_manifest_sha != EXPECTED_FIRST_O2_MANIFEST_SHA256:
            raise RuntimeError("first accepted O2 session manifest does not match frozen pin")
    payload = dict(payload)
    payload["_manifest_sha256"] = actual_manifest_sha
    return artifact_path, manifest_path, payload


def _validate_o2_frame(frame: pd.DataFrame, session_key: str) -> pd.DataFrame:
    required = {"ticker", "session_date", "score", "o2_eligible", "o2_exclusion_reason"}
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"O2 score artifact missing columns: {sorted(missing)}")
    result = frame.copy()
    result["ticker"] = result["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    result["session_date"] = pd.to_datetime(result["session_date"], errors="coerce").dt.normalize()
    session = _normal_date(session_key)
    if result["session_date"].isna().any() or not result["session_date"].eq(session).all():
        raise RuntimeError(f"O2 score artifact contains a wrong or invalid date for {session_key}")
    if result["ticker"].eq("").any() or result.duplicated("ticker").any():
        raise RuntimeError(f"O2 score artifact ticker identity is invalid for {session_key}")
    eligible = result["o2_eligible"].astype(bool)
    scores = pd.to_numeric(result["score"], errors="coerce")
    if scores.loc[eligible].isna().any() or not np.isfinite(scores.loc[eligible].to_numpy(dtype=float)).all():
        raise RuntimeError(f"O2 scored rows contain invalid scores for {session_key}")
    if scores.loc[~eligible].notna().any():
        raise RuntimeError(f"O2-ineligible rows unexpectedly contain scores for {session_key}")
    result["score"] = scores
    result["o2_eligible"] = eligible
    return result


def _compute_margin(scored: pd.DataFrame) -> tuple[pd.Series, float]:
    n = len(scored)
    raw = pd.Series(np.nan, index=scored.index, dtype=float)
    if n < 2:
        return raw, float("nan")
    ordered = scored.sort_values(["score", "ticker"], kind="mergesort")
    values = ordered["score"].to_numpy(dtype=float)
    gaps = np.diff(values)
    nearest = np.empty(n, dtype=float)
    nearest[0] = gaps[0]
    nearest[-1] = gaps[-1]
    if n > 2:
        nearest[1:-1] = np.minimum(gaps[:-1], gaps[1:])
    iqr = float(scored["score"].quantile(0.75) - scored["score"].quantile(0.25))
    if not np.isfinite(iqr) or iqr <= 0:
        return raw, iqr
    raw.loc[ordered.index] = nearest / iqr
    return raw, iqr


def _percentiles(raw: pd.Series) -> pd.Series:
    result = pd.Series(np.nan, index=raw.index, dtype=float)
    finite = raw.notna() & np.isfinite(raw.to_numpy(dtype=float))
    n = int(finite.sum())
    if n >= 2:
        ranks = raw.loc[finite].rank(method="average", ascending=True)
        result.loc[finite] = 100.0 * (ranks - 1.0) / float(n - 1)
    return result


def _existing_sidecar(paths: Any, session_key: str) -> dict[str, Any] | None:
    output = _sidecar_paths(paths, session_key)
    exists = [output["artifact"].exists(), output["manifest"].exists()]
    if not any(exists):
        return None
    if not all(exists):
        raise RuntimeError(f"Reliability sidecar bundle is incomplete for {session_key}")
    payload = json.loads(output["manifest"].read_text(encoding="utf-8"))
    if sha256_file(output["artifact"]) != payload.get("reliability_artifact_sha256"):
        raise RuntimeError(f"Reliability sidecar artifact hash mismatch for {session_key}")
    return payload


def score_reliability_v1_session(paths: Any, session_key: str) -> dict[str, Any]:
    """Create or verify one outcome-blind Reliability V1 sidecar."""

    session_key = _normal_date(session_key).date().isoformat()
    prior = _existing_sidecar(paths, session_key)
    if prior is not None:
        return prior
    o2_artifact, o2_manifest_path, o2_manifest = _find_o2_source(paths, session_key)
    o2 = _validate_o2_frame(pd.read_parquet(o2_artifact), session_key)
    scored = o2.loc[o2["o2_eligible"]].copy()
    raw = pd.Series(np.nan, index=o2.index, dtype=float)
    iqr = float("nan")
    if len(scored):
        computed, iqr = _compute_margin(scored)
        raw.loc[computed.index] = computed
    percentile = _percentiles(raw)

    output = pd.DataFrame(
        {
            "date": o2["session_date"].dt.strftime("%Y-%m-%d"),
            "session_index": int(o2_manifest["official_session_index"]),
            "ticker": o2["ticker"],
            "o2_eligible": o2["o2_eligible"],
            "o2_score": o2["score"],
            "score_margin_reliability": raw,
            "reliability_percentile": percentile,
            "reliability_status": np.where(
                ~o2["o2_eligible"], "NOT_APPLICABLE_O2_UNSCORED",
                np.where(raw.notna(), "AVAILABLE", "UNAVAILABLE_SESSION_GEOMETRY"),
            ),
            "reliability_reason": np.where(
                ~o2["o2_eligible"], o2["o2_exclusion_reason"].fillna("O2_UNSCORED"),
                np.where(raw.notna(), "", "ZERO_OR_NONFINITE_SCORE_IQR"),
            ),
            "formula_version": RELIABILITY_FORMULA_VERSION,
            "model_id": RELIABILITY_MODEL_ID,
            "generation": RELIABILITY_GENERATION,
        }
    )
    output = output.sort_values(["o2_eligible", "o2_score", "ticker"], ascending=[False, False, True], kind="mergesort").reset_index(drop=True)
    output_paths = _sidecar_paths(paths, session_key)
    output_paths["root"].mkdir(parents=True, exist_ok=True)
    write_parquet_atomic(output, output_paths["artifact"])
    artifact_sha = sha256_file(output_paths["artifact"])
    payload: dict[str, Any] = {
        "schema": "idx-trade/reliability-v1-forward-shadow-artifacts-v1",
        "status": "READY",
        "session_date": session_key,
        "official_session_index": int(o2_manifest["official_session_index"]),
        "model_id": RELIABILITY_MODEL_ID,
        "generation": RELIABILITY_GENERATION,
        "formula_version": RELIABILITY_FORMULA_VERSION,
        "o2_source_score_artifact_path": str(o2_artifact),
        "o2_source_score_artifact_sha256": str(o2_manifest["score_artifact_sha256"]),
        "o2_source_session_manifest_path": str(o2_manifest_path),
        "o2_source_session_manifest_sha256": str(o2_manifest["_manifest_sha256"]),
        "o2_model_sha256": O2_MODEL_SHA256,
        "o2_feature_order_sha256": O2_FEATURE_ORDER_SHA256,
        "spec_commit": "3239a319fbd4ff492b16a74d899a20edc9affa7f",
        "implementation_commit": _implementation_commit(),
        "score_rows": int(len(output)),
        "o2_scored_rows": int(o2["o2_eligible"].sum()),
        "reliability_finite_rows": int(output["score_margin_reliability"].notna().sum()),
        "o2_unscored_not_applicable_rows": int((~o2["o2_eligible"]).sum()),
        "score_iqr": iqr,
        "reliability_artifact_path": str(output_paths["artifact"]),
        "reliability_artifact_sha256": artifact_sha,
        "runtime_flags": dict(PROTECTED_FLAGS),
        "outcome_access": "LOCKED",
    }
    write_manifest_atomic(output_paths["manifest"], payload)
    return payload


def align_reliability_v1_sessions(
    runtime_root: str | Path, session_dates: Iterable[object] | None = None
) -> dict[str, Any]:
    """Align only stored DATA_READY O2 sessions; never capture or rescore."""

    paths = _paths(runtime_root)
    requested = None if session_dates is None else {_normal_date(value).date().isoformat() for value in session_dates}
    connection = _connection(paths)
    try:
        available = [
            str(row["session_date"])
            for row in connection.execute(
                "SELECT session_date FROM session_snapshots WHERE state='DATA_READY' ORDER BY session_date"
            ).fetchall()
        ]
    finally:
        connection.close()
    sessions = [value for value in available if requested is None or value in requested]
    results = [score_reliability_v1_session(paths, session) for session in sessions]
    return {
        "status": "RELIABILITY_V1_SHADOW_ALIGNED",
        "sessions": results,
        "independent_counter": False,
        "outcome_access": "LOCKED",
        "runtime_flags": dict(PROTECTED_FLAGS),
    }


def reliability_v1_status(runtime_root: str | Path) -> dict[str, Any]:
    root = Path(runtime_root)
    run_root = root / "forward_monitoring" / RELIABILITY_SHADOW_ROOT
    manifests = sorted(run_root.glob("*/manifest.json")) if run_root.exists() else []
    valid: list[dict[str, Any]] = []
    for manifest_path in manifests:
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            artifact = Path(payload["reliability_artifact_path"])
            if artifact.is_file() and sha256_file(artifact) == payload.get("reliability_artifact_sha256"):
                valid.append(payload)
        except (OSError, ValueError, KeyError, TypeError):
            continue
    latest = sorted(valid, key=lambda value: str(value.get("session_date", "")))[-1] if valid else None
    return {
        "status": "READY" if valid else "NOT_ALIGNED",
        "model_id": RELIABILITY_MODEL_ID,
        "generation": RELIABILITY_GENERATION,
        "formula_version": RELIABILITY_FORMULA_VERSION,
        "shadow_sessions_aligned": len(valid),
        "latest_session_date": None if latest is None else latest.get("session_date"),
        "independent_counter": False,
        "outcome_access": "LOCKED",
        "runtime_flags": dict(PROTECTED_FLAGS),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="IDX Trade Reliability V1 forward shadow")
    parser.add_argument("command", choices=("align", "status"))
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--date", default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "align":
        dates = [args.date] if args.date else None
        result = align_reliability_v1_sessions(args.runtime_root, dates)
    else:
        result = reliability_v1_status(args.runtime_root)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
