"""Frozen final V3-B refit and outcome-blind fresh-forward runtime.

Historical architecture selection is closed.  This module may build exactly one
final Structure-Lite training table/model from already-consumed development data
and may prepare/score outcome-blind forward features.  It deliberately does not
load fresh-forward labels or consume the real one-shot outcome marker.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import joblib
import numpy as np
import pandas as pd

from .provenance import sha256_file, write_manifest_atomic
from .ranking_v2_forward_runtime import (
    FIRST_VERDICT_MATURE_SESSIONS,
    FRESH_FORWARD_CUTOFF,
    FROZEN_CACHE_FIRST_SESSION,
    FROZEN_CACHE_LAST_SESSION,
    FROZEN_CACHE_ROWS,
    FROZEN_CACHE_TICKERS,
    FROZEN_PREPARED_CACHE_SHA256,
    FROZEN_PREPARED_MANIFEST_SHA256,
    _assert_new_or_empty_directory,
    _canonical_hash,
    _normalize_dates,
    _normalized_date_series,
    _read_table,
    _runtime_environment,
    _timed,
    _verify_prepared_cache,
    assert_forward_outcome_access_not_started,
    assert_outcome_blind_columns,
    build_outcome_blind_forward_features,
    evaluate_frozen_forward_block,
    first_mature_forward_block,
    h10_maturity_diagnostics,
    normalize_final_refit_table,
    write_forward_outcome_access_started,
)
from .ranking_v3_structure_lite import (
    CALENDAR_SHA256,
    PANEL_SHA256,
    SECURITY_MASTER_SHA256,
    V3_B_CANDIDATE,
    V3_B_FEATURE_COLUMNS,
    _feature_order_hash,
    _normalized_git_blob_sha1,
    _read_calendar,
    _structure_model,
)
from .research_v2_models import pointwise_raw_score
from .research_v3_structure_lite import STRUCTURE_LITE_FEATURE_COLUMNS, build_structure_lite_features


V3_FINAL_FORWARD_SPEC_GIT_BLOB = "024f1919de8d5ea4e2e9933a9e4c1a1ef9bbe4f4"
V3_FINAL_FEATURE_ORDER_SHA256 = "100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e"
V3_FINAL_REFIT_STATUS = "RANKING_V3_B_FINAL_REFIT_FROZEN"
V3_PRE_OUTCOME_STATUS = "RANKING_V3_B_PRE_OUTCOME_MANIFEST_READY"


def _assert_forward_spec(spec_path: Path) -> str:
    actual = _normalized_git_blob_sha1(spec_path)
    if actual != V3_FINAL_FORWARD_SPEC_GIT_BLOB:
        raise RuntimeError(
            "final V3-B forward spec Git blob mismatch: "
            f"expected={V3_FINAL_FORWARD_SPEC_GIT_BLOB} actual={actual}"
        )
    return actual


def _assert_source_hashes(
    *,
    panel_path: Path,
    calendar_path: Path,
    security_master_path: Path,
) -> dict[str, str]:
    actual = {
        "panel": sha256_file(panel_path),
        "calendar": sha256_file(calendar_path),
        "security_master": sha256_file(security_master_path),
    }
    expected = {
        "panel": PANEL_SHA256,
        "calendar": CALENDAR_SHA256,
        "security_master": SECURITY_MASTER_SHA256,
    }
    if actual != expected:
        raise RuntimeError(f"final V3-B source hash mismatch: expected={expected} actual={actual}")
    return actual


def _read_structure_panel_bounded(path: Path, *, max_date: pd.Timestamp) -> pd.DataFrame:
    columns = ["ticker", "date", "high", "low", "close", "volume"]
    if path.suffix.lower() not in {".parquet", ".pq"}:
        raise ValueError("final V3-B Structure-Lite source panel must be Parquet")
    try:
        frame = pd.read_parquet(path, columns=columns, filters=[("date", "<=", max_date)])
    except Exception:
        frame = pd.read_parquet(path, columns=columns)
    frame = frame.copy()
    frame["date"] = _normalized_date_series(frame["date"], name="Structure-Lite source date")
    frame = frame[frame["date"] <= pd.Timestamp(max_date)].copy()
    if frame.empty:
        raise RuntimeError("final V3-B Structure-Lite source panel is empty")
    if frame.duplicated(["ticker", "date"]).any():
        raise RuntimeError("final V3-B Structure-Lite source contains duplicate ticker/date rows")
    return frame


def _join_structure_onto_exact_rows(
    base: pd.DataFrame,
    structure: pd.DataFrame,
    *,
    require_frozen_training_facts: bool,
) -> pd.DataFrame:
    base = base.copy().reset_index(drop=True)
    if base.duplicated(["ticker", "date"]).any():
        raise RuntimeError("final V3-B base rows contain duplicate ticker/date keys")
    structure = structure.copy()
    structure["ticker"] = structure["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    structure["date"] = _normalized_date_series(structure["date"], name="Structure-Lite join date")
    if structure.duplicated(["ticker", "date"]).any():
        raise RuntimeError("Structure-Lite feature frame contains duplicate ticker/date keys")

    keyed = structure.set_index(["ticker", "date"])
    keys = pd.MultiIndex.from_frame(base[["ticker", "date"]])
    missing = keys.difference(keyed.index)
    if len(missing):
        raise RuntimeError(f"final V3-B Structure-Lite join has {len(missing)} orphan base rows")

    joined = base.copy()
    aligned = keyed.reindex(keys)
    for column in STRUCTURE_LITE_FEATURE_COLUMNS:
        joined[column] = pd.to_numeric(aligned[column], errors="coerce").to_numpy(dtype=float)

    if len(joined) != len(base):
        raise RuntimeError("final V3-B Structure-Lite join changed row count")
    for column in STRUCTURE_LITE_FEATURE_COLUMNS:
        values = pd.to_numeric(joined[column], errors="coerce").to_numpy(dtype=float)
        if np.isinf(values).any():
            raise RuntimeError(f"final V3-B Structure-Lite column contains infinity: {column}")

    actual_feature_hash = _feature_order_hash(tuple(V3_B_FEATURE_COLUMNS))
    if actual_feature_hash != V3_FINAL_FEATURE_ORDER_SHA256:
        raise RuntimeError(
            "final V3-B feature order mismatch: "
            f"expected={V3_FINAL_FEATURE_ORDER_SHA256} actual={actual_feature_hash}"
        )

    if require_frozen_training_facts:
        facts = {
            "rows": int(len(joined)),
            "tickers": int(joined["ticker"].nunique()),
            "first_signal_session_index": int(joined["signal_session_index"].min()),
            "last_signal_session_index": int(joined["signal_session_index"].max()),
        }
        expected = {
            "rows": FROZEN_CACHE_ROWS,
            "tickers": FROZEN_CACHE_TICKERS,
            "first_signal_session_index": FROZEN_CACHE_FIRST_SESSION,
            "last_signal_session_index": FROZEN_CACHE_LAST_SESSION,
        }
        if facts != expected:
            raise RuntimeError(f"final V3-B training facts mismatch: expected={expected} actual={facts}")

    return joined


def build_final_v3_training_table(
    *,
    panel_path: Path,
    calendar_path: Path,
    security_master_path: Path,
    prepared_table_path: Path,
    prepared_manifest_path: Path,
    spec_path: Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build exact 292,633-row V3-B training table without computing metrics."""

    spec_blob = _assert_forward_spec(spec_path)
    source_hashes = _assert_source_hashes(
        panel_path=panel_path,
        calendar_path=calendar_path,
        security_master_path=security_master_path,
    )
    prepared_manifest = _verify_prepared_cache(
        prepared_table_path=prepared_table_path,
        expected_cache_sha256=FROZEN_PREPARED_CACHE_SHA256,
        prepared_manifest_path=prepared_manifest_path,
        expected_manifest_sha256=FROZEN_PREPARED_MANIFEST_SHA256,
    )
    base = normalize_final_refit_table(_read_table(prepared_table_path))
    base_identity = base[["ticker", "date", "signal_session_index", "binary_target"]].copy()

    sessions = _read_calendar(calendar_path)
    if len(sessions) < FROZEN_CACHE_LAST_SESSION:
        raise RuntimeError("official calendar does not cover final V3-B training session 1250")
    max_date = pd.Timestamp(sessions[FROZEN_CACHE_LAST_SESSION - 1])
    panel = _read_structure_panel_bounded(panel_path, max_date=max_date)
    structure = build_structure_lite_features(
        panel,
        sessions,
        max_signal_session_index=FROZEN_CACHE_LAST_SESSION,
    )
    joined = _join_structure_onto_exact_rows(
        base,
        structure,
        require_frozen_training_facts=True,
    )
    if not joined[["ticker", "date", "signal_session_index", "binary_target"]].equals(base_identity):
        raise RuntimeError("final V3-B join changed frozen V2 training identity/target values")

    metadata = {
        "spec_git_blob": spec_blob,
        "source_sha256": source_hashes,
        "prepared_cache_sha256": FROZEN_PREPARED_CACHE_SHA256,
        "prepared_manifest_sha256": FROZEN_PREPARED_MANIFEST_SHA256,
        "prepared_manifest_status": prepared_manifest.get("status"),
        "feature_columns": list(V3_B_FEATURE_COLUMNS),
        "feature_order_sha256": V3_FINAL_FEATURE_ORDER_SHA256,
        "rows": int(len(joined)),
        "tickers": int(joined["ticker"].nunique()),
        "first_signal_session_index": int(joined["signal_session_index"].min()),
        "last_signal_session_index": int(joined["signal_session_index"].max()),
        "outcome_metrics_computed": False,
        "fresh_forward_outcomes_accessed": False,
    }
    return joined, metadata


def run_final_v3_refit(
    *,
    panel_path: Path,
    calendar_path: Path,
    security_master_path: Path,
    prepared_table_path: Path,
    prepared_manifest_path: Path,
    spec_path: Path,
    output_dir: Path,
    code_commit: str,
) -> dict[str, Any]:
    """Run exactly one frozen V3-B fit; do not evaluate historical performance."""

    _assert_new_or_empty_directory(output_dir, label="final V3-B refit output directory")
    started = time.perf_counter()
    timings: list[dict[str, Any]] = []

    built, timing = _timed(
        "build_final_v3_training_table",
        lambda: build_final_v3_training_table(
            panel_path=panel_path,
            calendar_path=calendar_path,
            security_master_path=security_master_path,
            prepared_table_path=prepared_table_path,
            prepared_manifest_path=prepared_manifest_path,
            spec_path=spec_path,
        ),
    )
    timings.append(timing)
    table, metadata = built

    table_path = output_dir / "ranking_v3_b_structure_lite_final_training_table.parquet"
    _, timing = _timed("training_table_serialization", lambda: table.to_parquet(table_path, index=False))
    timings.append(timing)
    training_table_sha256 = sha256_file(table_path)

    model, timing = _timed(
        "final_model_fit",
        lambda: _structure_model().fit(table, table["binary_target"].to_numpy(dtype=int)),
    )
    timings.append(timing)
    model_path = output_dir / "ranking_v3_b_structure_lite_final.joblib"
    _, timing = _timed("model_serialization", lambda: joblib.dump(model, model_path))
    timings.append(timing)
    model_sha256 = sha256_file(model_path)

    environment = _runtime_environment(
        source_paths=[
            Path(__file__),
            Path(__file__).with_name("ranking_v3_structure_lite.py"),
            Path(__file__).with_name("research_v3_structure_lite.py"),
        ],
        config={"phase": "RANKING_V3_B_FINAL_REFIT", "outcome_access": False},
    )
    manifest: dict[str, Any] = {
        "status": V3_FINAL_REFIT_STATUS,
        "architecture": V3_B_CANDIDATE,
        "code_commit": code_commit,
        **metadata,
        "training_table_path": str(table_path),
        "training_table_sha256": training_table_sha256,
        "model_path": str(model_path),
        "model_sha256": model_sha256,
        "profiling": timings,
        "historical_performance_metrics_computed": False,
        "sessions_1225_1250_used_for_training_only": True,
        "fresh_forward_outcomes_accessed": False,
        "forward_outcome_access_marker_written": False,
        "independent_validation_claim": False,
        "probability_claim": False,
        "environment": environment,
    }
    manifest["manifest_content_sha256"] = _canonical_hash(manifest)
    manifest_path = output_dir / "ranking_v3_b_structure_lite_final_manifest.json"
    write_manifest_atomic(manifest_path, manifest)
    manifest_sha256 = sha256_file(manifest_path)

    summary = {
        "status": V3_FINAL_REFIT_STATUS,
        "architecture": V3_B_CANDIDATE,
        "code_commit": code_commit,
        "model_path": str(model_path),
        "model_sha256": model_sha256,
        "manifest_path": str(manifest_path),
        "manifest_sha256": manifest_sha256,
        "training_table_path": str(table_path),
        "training_table_sha256": training_table_sha256,
        "rows": metadata["rows"],
        "tickers": metadata["tickers"],
        "first_signal_session_index": metadata["first_signal_session_index"],
        "last_signal_session_index": metadata["last_signal_session_index"],
        "feature_order_sha256": V3_FINAL_FEATURE_ORDER_SHA256,
        "historical_performance_metrics_computed": False,
        "fresh_forward_outcomes_accessed": False,
        "forward_outcome_access_marker_written": False,
        "profiling": timings,
        "total_seconds": float(time.perf_counter() - started),
    }
    summary_path = output_dir / "ranking_v3_b_structure_lite_final_summary.json"
    write_manifest_atomic(summary_path, summary)
    summary["summary_sha256"] = sha256_file(summary_path)
    return summary


def verify_final_v3_refit_artifacts(
    *,
    model_path: Path,
    manifest_path: Path,
    expected_model_sha256: str,
    expected_manifest_sha256: str,
) -> dict[str, Any]:
    actual_model = sha256_file(model_path)
    actual_manifest = sha256_file(manifest_path)
    if actual_model != expected_model_sha256:
        raise RuntimeError(f"final V3-B model SHA mismatch: expected={expected_model_sha256} actual={actual_model}")
    if actual_manifest != expected_manifest_sha256:
        raise RuntimeError(
            f"final V3-B manifest SHA mismatch: expected={expected_manifest_sha256} actual={actual_manifest}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = {
        "status": V3_FINAL_REFIT_STATUS,
        "architecture": V3_B_CANDIDATE,
        "model_sha256": expected_model_sha256,
        "feature_order_sha256": V3_FINAL_FEATURE_ORDER_SHA256,
        "rows": FROZEN_CACHE_ROWS,
        "tickers": FROZEN_CACHE_TICKERS,
        "first_signal_session_index": FROZEN_CACHE_FIRST_SESSION,
        "last_signal_session_index": FROZEN_CACHE_LAST_SESSION,
        "historical_performance_metrics_computed": False,
        "fresh_forward_outcomes_accessed": False,
        "forward_outcome_access_marker_written": False,
    }
    for key, value in required.items():
        if manifest.get(key) != value:
            raise RuntimeError(f"final V3-B manifest mismatch {key}: expected={value} actual={manifest.get(key)}")
    return {
        "valid": True,
        "model_sha256": actual_model,
        "manifest_sha256": actual_manifest,
        "training_table_sha256": manifest.get("training_table_sha256"),
        "rows": manifest.get("rows"),
        "tickers": manifest.get("tickers"),
    }


def build_outcome_blind_v3_forward_features(
    panel: pd.DataFrame,
    official_sessions: Iterable[object],
    *,
    listed_from: Mapping[str, object] | None = None,
    cutoff_date: object = FRESH_FORWARD_CUTOFF,
) -> pd.DataFrame:
    """Build exact V3-B primary-liquid forward features without outcomes."""

    assert_outcome_blind_columns(panel.columns)
    if "tradability_state" in panel.columns:
        state = panel["tradability_state"].astype(str).str.upper()
        if not state.eq("ACTIVE").all():
            raise ValueError("V3-B forward panel must be signal-safe ACTIVE-only")

    v2 = build_outcome_blind_forward_features(
        panel,
        official_sessions,
        listed_from=listed_from,
        cutoff_date=cutoff_date,
    )
    if "universe_primary_liquid" not in v2.columns:
        raise RuntimeError("V2 forward feature table lacks universe_primary_liquid")
    primary = v2[v2["universe_primary_liquid"].astype(bool)].copy().reset_index(drop=True)
    if primary.empty:
        raise RuntimeError("V3-B forward feature table has no primary-liquid rows")

    required_structure = {"ticker", "date", "high", "low", "close", "volume"}
    missing = required_structure - set(panel.columns)
    if missing:
        raise ValueError(f"V3-B forward Structure-Lite input missing {sorted(missing)}")
    structure_input_columns = ["ticker", "date", "high", "low", "close", "volume"]
    if "tradability_state" in panel.columns:
        structure_input_columns.append("tradability_state")
    structure_input = panel.loc[:, structure_input_columns].copy()
    structure_input["date"] = _normalized_date_series(structure_input["date"], name="V3-B forward structure date")

    sessions = _normalize_dates(official_sessions)
    structure = build_structure_lite_features(
        structure_input,
        sessions,
        max_signal_session_index=len(sessions),
    )
    cutoff = pd.Timestamp(cutoff_date).tz_localize(None).normalize()
    structure = structure[structure["date"] > cutoff].copy()
    joined = _join_structure_onto_exact_rows(
        primary,
        structure,
        require_frozen_training_facts=False,
    )
    if not joined["universe_primary_liquid"].astype(bool).all():
        raise RuntimeError("V3-B forward output contains a non-primary row")
    return joined.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)


def score_outcome_blind_v3_forward_features(
    features: pd.DataFrame,
    *,
    model_path: Path,
    manifest_path: Path,
    expected_model_sha256: str,
    expected_manifest_sha256: str,
) -> pd.DataFrame:
    """Score outcome-free V3-B features with the exact frozen final model."""

    assert_outcome_blind_columns(features.columns)
    verify_final_v3_refit_artifacts(
        model_path=model_path,
        manifest_path=manifest_path,
        expected_model_sha256=expected_model_sha256,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    missing = set(V3_B_FEATURE_COLUMNS) - set(features.columns)
    if missing:
        raise ValueError(f"V3-B forward scoring table missing {sorted(missing)}")
    model = joblib.load(model_path)
    score = pointwise_raw_score(model, features)
    if not np.isfinite(score).all():
        raise RuntimeError("V3-B forward model produced non-finite scores")
    output = features[["ticker", "date"]].copy()
    if "signal_session_index" in features.columns:
        output["signal_session_index"] = features["signal_session_index"].to_numpy()
    output["score"] = score
    return output


def write_v3_pre_outcome_manifest(
    *,
    output_dir: Path,
    model_manifest_path: Path,
    expected_model_manifest_sha256: str,
    code_commit: str,
    forward_snapshot_paths: Mapping[str, Path],
    intended_block: pd.DataFrame,
    spec_path: Path,
) -> dict[str, Any]:
    """Freeze V3-B forward provenance without reading labels or writing marker."""

    _assert_new_or_empty_directory(output_dir, label="V3-B pre-outcome manifest directory")
    spec_blob = _assert_forward_spec(spec_path)
    actual_model_manifest = sha256_file(model_manifest_path)
    if actual_model_manifest != expected_model_manifest_sha256:
        raise RuntimeError(
            "V3-B pre-outcome model manifest SHA mismatch: "
            f"expected={expected_model_manifest_sha256} actual={actual_model_manifest}"
        )
    model_manifest = json.loads(model_manifest_path.read_text(encoding="utf-8"))
    if model_manifest.get("status") != V3_FINAL_REFIT_STATUS:
        raise RuntimeError("V3-B pre-outcome model manifest is not a frozen final refit")
    if model_manifest.get("feature_order_sha256") != V3_FINAL_FEATURE_ORDER_SHA256:
        raise RuntimeError("V3-B pre-outcome model feature order mismatch")

    required_block = {"signal_date", "signal_session_index"}
    if not required_block.issubset(intended_block.columns):
        raise ValueError(f"V3-B intended block missing {sorted(required_block - set(intended_block.columns))}")
    if len(intended_block) != FIRST_VERDICT_MATURE_SESSIONS:
        raise ValueError("V3-B intended forward block must contain exactly 100 sessions")
    block = intended_block.copy()
    block["signal_date"] = _normalized_date_series(block["signal_date"], name="V3-B intended block date")
    indices = pd.to_numeric(block["signal_session_index"], errors="raise").astype(int)
    if not indices.diff().dropna().eq(1).all():
        raise ValueError("V3-B intended forward block must be consecutive official sessions")
    if not (block["signal_date"] > FRESH_FORWARD_CUTOFF).all():
        raise ValueError("V3-B intended forward block must be strictly post-2026-07-31")

    snapshot_hashes = {name: sha256_file(path) for name, path in forward_snapshot_paths.items()}
    payload: dict[str, Any] = {
        "status": V3_PRE_OUTCOME_STATUS,
        "architecture": V3_B_CANDIDATE,
        "code_commit": code_commit,
        "spec_git_blob": spec_blob,
        "feature_columns": list(V3_B_FEATURE_COLUMNS),
        "feature_order_sha256": V3_FINAL_FEATURE_ORDER_SHA256,
        "model_manifest_path": str(model_manifest_path),
        "model_manifest_sha256": actual_model_manifest,
        "model_sha256": model_manifest.get("model_sha256"),
        "forward_snapshot_sha256": snapshot_hashes,
        "intended_block": {
            "sessions": int(len(block)),
            "first_signal_date": str(block["signal_date"].min().date()),
            "last_signal_date": str(block["signal_date"].max().date()),
            "first_signal_session_index": int(indices.min()),
            "last_signal_session_index": int(indices.max()),
        },
        "outcome_access_marker_written": False,
        "fresh_forward_outcomes_accessed": False,
        "environment": _runtime_environment(
            source_paths=[Path(__file__), model_manifest_path, spec_path],
            config={"phase": "RANKING_V3_B_PRE_OUTCOME_MANIFEST", "outcome_access": False},
        ),
    }
    payload["manifest_content_sha256"] = _canonical_hash(payload)
    manifest_path = output_dir / "ranking_v3_b_pre_outcome_manifest.json"
    write_manifest_atomic(manifest_path, payload)
    return {
        "path": str(manifest_path),
        "sha256": sha256_file(manifest_path),
        "outcome_access_marker_written": False,
        "fresh_forward_outcomes_accessed": False,
    }


# Explicit re-exports of the already-frozen shared one-shot primitives.
V3_H10_MATURITY_DIAGNOSTICS = h10_maturity_diagnostics
V3_FIRST_MATURE_FORWARD_BLOCK = first_mature_forward_block
V3_EVALUATE_FROZEN_FORWARD_BLOCK = evaluate_frozen_forward_block
V3_ASSERT_FORWARD_OUTCOME_ACCESS_NOT_STARTED = assert_forward_outcome_access_not_started
V3_WRITE_FORWARD_OUTCOME_ACCESS_STARTED = write_forward_outcome_access_started


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Frozen V3-B final-refit and outcome-blind forward runtime")
    subparsers = parser.add_subparsers(dest="command", required=True)
    refit = subparsers.add_parser("final-refit", help="fit the one frozen final V3-B Structure-Lite model")
    refit.add_argument("--panel", type=Path, required=True)
    refit.add_argument("--calendar", type=Path, required=True)
    refit.add_argument("--security-master", type=Path, required=True)
    refit.add_argument("--prepared-table", type=Path, required=True)
    refit.add_argument("--prepared-manifest", type=Path, required=True)
    refit.add_argument("--spec", type=Path, required=True)
    refit.add_argument("--output-dir", type=Path, required=True)
    refit.add_argument("--code-commit", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "final-refit":
        summary = run_final_v3_refit(
            panel_path=args.panel,
            calendar_path=args.calendar,
            security_master_path=args.security_master,
            prepared_table_path=args.prepared_table,
            prepared_manifest_path=args.prepared_manifest,
            spec_path=args.spec,
            output_dir=args.output_dir,
            code_commit=args.code_commit,
        )
        print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
        return 0
    raise AssertionError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
