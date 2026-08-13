from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from .provenance import sha256_file
from .ranking_v2_candidate import _assert_clean_output_dir, _normalize_candidate_table, _read_table
from .ranking_v3_recency import (
    DISCOVERY_FOLDS,
    _absolute_sanity,
    _aggregate_candidate,
    _paired_metrics,
    _paired_promotion,
    _read_reference_artifacts,
    prove_control_equivalence,
)
from .research_baselines import (
    RANDOM_SEED,
    TREE_L2,
    TREE_LEARNING_RATE,
    TREE_MAX_ITER,
    TREE_MAX_LEAF_NODES,
)
from .research_features import assert_no_open_dependency
from .research_v2_features import V2_FULL_FEATURE_COLUMNS
from .research_v2_models import HGB_XS_MARKET, pointwise_model, pointwise_raw_score
from .research_v2_validation import RANKING_V2_FOLDS, evaluate_v2_scores, split_v2_model_table
from .research_v3_structure_lite import STRUCTURE_LITE_FEATURE_COLUMNS, build_structure_lite_features
from .stage5_ranking_holdout import _assert_environment


V3_B_HYPOTHESIS_ID = "V3-B-STRUCTURE-LITE-V1"
V3_B_CONTROL = "V3-B-STRUCTURE-LITE-V1-CONTROL-004"
V3_B_CANDIDATE = "V3-B-STRUCTURE-LITE-V1-CANDIDATE-005"
V3_B_CANDIDATES = (V3_B_CONTROL, V3_B_CANDIDATE)
V3_B_FEATURE_COLUMNS = (*V2_FULL_FEATURE_COLUMNS, *STRUCTURE_LITE_FEATURE_COLUMNS)

MAX_DISCOVERY_SIGNAL_INDEX = 984
SEALED_FOLD_NAMES = frozenset(fold.name for fold in RANKING_V2_FOLDS[4:])

PANEL_SHA256 = "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
CALENDAR_SHA256 = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
SECURITY_MASTER_SHA256 = "9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9"
V2_PREPARED_SHA256 = "522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5"
V2_MANIFEST_SHA256 = "6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143"
STRUCTURE_SPEC_SHA256 = "1bf046e98f0d0e92c0981ff4120dc5a54e74f2082b84b8c9d8f4ca281cdf1051"
STRUCTURE_SPEC_GIT_BLOB = "0392ab506aa451355697327d416f8f2b2ea21d4f"
STRUCTURE_ADDENDUM_GIT_BLOB = "717871707e833ab9818c249d52aae5b234334fc4"


def assert_discovery_fold_allowed(name: str) -> None:
    allowed = {fold.name for fold in DISCOVERY_FOLDS}
    if name in SEALED_FOLD_NAMES or name not in allowed:
        raise PermissionError(f"{name} is sealed for V3-B Structure-Lite")


def _normalized_text_bytes(path: Path) -> bytes:
    text = path.read_text(encoding="utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _normalized_sha256(path: Path) -> str:
    return hashlib.sha256(_normalized_text_bytes(path)).hexdigest()


def _normalized_git_blob_sha1(path: Path) -> str:
    payload = _normalized_text_bytes(path)
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload, usedforsecurity=False).hexdigest()


def _assert_spec_files(spec_path: Path, addendum_path: Path) -> dict[str, str]:
    identities = {
        "spec_sha256": _normalized_sha256(spec_path),
        "spec_git_blob": _normalized_git_blob_sha1(spec_path),
        "addendum_git_blob": _normalized_git_blob_sha1(addendum_path),
    }
    if identities["spec_sha256"] != STRUCTURE_SPEC_SHA256:
        raise RuntimeError("V3-B Structure-Lite spec SHA-256 mismatch")
    if identities["spec_git_blob"] != STRUCTURE_SPEC_GIT_BLOB:
        raise RuntimeError("V3-B Structure-Lite spec Git blob mismatch")
    if identities["addendum_git_blob"] != STRUCTURE_ADDENDUM_GIT_BLOB:
        raise RuntimeError("V3-B Structure-Lite review addendum Git blob mismatch")
    return identities


def _read_calendar(path: Path) -> pd.DatetimeIndex:
    frame = _read_table(path)
    candidates = [column for column in ("date", "session_date", "trading_date") if column in frame.columns]
    if len(candidates) != 1:
        raise ValueError(f"official calendar requires one recognized date column, got {candidates}")
    values = pd.to_datetime(frame[candidates[0]], errors="coerce")
    sessions = pd.DatetimeIndex(values).tz_localize(None).normalize().dropna().unique().sort_values()
    if not len(sessions):
        raise ValueError("official calendar is empty")
    if len(sessions) < MAX_DISCOVERY_SIGNAL_INDEX:
        raise ValueError("official calendar does not cover V3-B discovery boundary")
    return sessions


def _read_v2_discovery_subset(path: Path) -> pd.DataFrame:
    if path.suffix.lower() not in {".parquet", ".pq"}:
        raise ValueError("V3-B discovery requires the frozen Parquet prepared cache")
    frame = pd.read_parquet(
        path,
        filters=[("signal_session_index", "<=", MAX_DISCOVERY_SIGNAL_INDEX)],
    )
    if frame.empty:
        raise ValueError("V3-B V2 discovery subset is empty")
    values = pd.to_numeric(frame["signal_session_index"], errors="raise").astype(int)
    if int(values.max()) > MAX_DISCOVERY_SIGNAL_INDEX:
        raise RuntimeError("V3-B prepared predicate materialized a sealed session")
    return frame


def _read_panel_bounded(path: Path, max_date: pd.Timestamp) -> pd.DataFrame:
    if path.suffix.lower() in {".parquet", ".pq"}:
        try:
            frame = pd.read_parquet(path, filters=[("date", "<=", max_date)])
        except Exception:
            frame = pd.read_parquet(path)
    elif path.suffix.lower() == ".csv":
        frame = pd.read_csv(path)
    else:
        raise ValueError(f"unsupported panel format: {path}")
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if frame["date"].isna().any():
        raise ValueError("signal-research panel contains invalid dates")
    frame = frame[frame["date"] <= max_date].copy()
    if (frame["date"] > max_date).any():
        raise RuntimeError("post-discovery HLCV row escaped boundary")
    return frame


def _feature_order_hash(columns: tuple[str, ...]) -> str:
    payload = json.dumps(list(columns), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _structure_model() -> Pipeline:
    assert_no_open_dependency(V3_B_FEATURE_COLUMNS)
    numeric = Pipeline(
        [
            (
                "impute",
                SimpleImputer(
                    strategy="median",
                    add_indicator=True,
                    keep_empty_features=True,
                ),
            )
        ]
    )
    preprocess = ColumnTransformer(
        [("numeric", numeric, list(V3_B_FEATURE_COLUMNS))],
        remainder="drop",
    )
    return Pipeline(
        [
            ("preprocess", preprocess),
            (
                "model",
                HistGradientBoostingClassifier(
                    learning_rate=TREE_LEARNING_RATE,
                    max_iter=TREE_MAX_ITER,
                    max_leaf_nodes=TREE_MAX_LEAF_NODES,
                    l2_regularization=TREE_L2,
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    )


def _coverage_report(cache: pd.DataFrame) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for column in STRUCTURE_LITE_FEATURE_COLUMNS:
        values = pd.to_numeric(cache[column], errors="coerce")
        finite = np.isfinite(values.to_numpy(dtype=float))
        observed = values[finite]
        rows[column] = {
            "rows": int(len(values)),
            "finite_rows": int(finite.sum()),
            "finite_rate": float(finite.mean()) if len(values) else 0.0,
            "missing_rate": float(1.0 - finite.mean()) if len(values) else 1.0,
            "unique_finite_values": int(observed.nunique(dropna=True)),
        }
    per_fold: dict[str, dict[str, float]] = {}
    for fold in DISCOVERY_FOLDS:
        block = cache[
            pd.to_numeric(cache["signal_session_index"], errors="raise")
            .astype(int)
            .between(fold.validation_start, fold.validation_end)
        ]
        per_fold[fold.name] = {
            column: float(
                np.isfinite(pd.to_numeric(block[column], errors="coerce").to_numpy(dtype=float)).mean()
            )
            for column in STRUCTURE_LITE_FEATURE_COLUMNS
        }
    return {"overall": rows, "validation_finite_rate": per_fold}


def prepare_structure_cache(
    *,
    panel_path: Path,
    calendar_path: Path,
    security_master_path: Path,
    v2_prepared_path: Path,
    v2_manifest_path: Path,
    spec_path: Path,
    addendum_path: Path,
    output_dir: Path,
    code_commit: str,
) -> dict[str, Any]:
    _assert_clean_output_dir(output_dir)
    identities = _assert_spec_files(spec_path, addendum_path)
    source_hashes = {
        "panel": sha256_file(panel_path),
        "calendar": sha256_file(calendar_path),
        "security_master": sha256_file(security_master_path),
        "v2_prepared": sha256_file(v2_prepared_path),
        "v2_manifest": sha256_file(v2_manifest_path),
    }
    expected = {
        "panel": PANEL_SHA256,
        "calendar": CALENDAR_SHA256,
        "security_master": SECURITY_MASTER_SHA256,
        "v2_prepared": V2_PREPARED_SHA256,
        "v2_manifest": V2_MANIFEST_SHA256,
    }
    if source_hashes != expected:
        raise RuntimeError(f"V3-B source hash mismatch: expected={expected} actual={source_hashes}")

    sessions = _read_calendar(calendar_path)
    max_date = pd.Timestamp(sessions[MAX_DISCOVERY_SIGNAL_INDEX - 1])
    panel = _read_panel_bounded(panel_path, max_date)
    structure = build_structure_lite_features(
        panel,
        sessions,
        max_signal_session_index=MAX_DISCOVERY_SIGNAL_INDEX,
    )
    if int(structure["signal_session_index"].max()) > MAX_DISCOVERY_SIGNAL_INDEX:
        raise RuntimeError("Structure-Lite feature frame includes sealed sessions")

    v2_raw = _read_v2_discovery_subset(v2_prepared_path)
    v2 = _normalize_candidate_table(v2_raw, HGB_XS_MARKET)
    if int(v2["signal_session_index"].max()) > MAX_DISCOVERY_SIGNAL_INDEX:
        raise RuntimeError("V2 discovery subset includes sealed sessions")

    structure_keyed = structure.set_index(["ticker", "date"])
    keys = pd.MultiIndex.from_frame(v2[["ticker", "date"]])
    if not keys.is_unique:
        raise RuntimeError("V2 discovery keys are not unique")
    missing_keys = keys.difference(structure_keyed.index)
    if len(missing_keys):
        raise RuntimeError(f"Structure-Lite join has {len(missing_keys)} orphan V2 rows")

    joined = v2.copy()
    aligned = structure_keyed.reindex(keys)
    for column in STRUCTURE_LITE_FEATURE_COLUMNS:
        joined[column] = aligned[column].to_numpy()

    original_columns = list(v2.columns)
    if not joined.loc[:, original_columns].equals(v2.loc[:, original_columns]):
        raise RuntimeError("V3-B cache changed an existing V2 prepared column")
    if tuple(V3_B_FEATURE_COLUMNS[: len(V2_FULL_FEATURE_COLUMNS)]) != tuple(V2_FULL_FEATURE_COLUMNS):
        raise RuntimeError("V3-B feature order does not preserve exact V2 prefix")
    if joined.duplicated(["ticker", "date"]).any():
        raise RuntimeError("V3-B discovery cache contains duplicate ticker/date rows")

    coverage = _coverage_report(joined)
    cache_path = output_dir / "ranking_v3_b_structure_lite_discovery_cache.parquet"
    joined.to_parquet(cache_path, index=False)
    cache_sha = sha256_file(cache_path)

    manifest = {
        "status": "RANKING_V3_B_STRUCTURE_LITE_DISCOVERY_CACHE_FROZEN",
        "code_commit": code_commit,
        "source_sha256": source_hashes,
        "contract_identity": identities,
        "cache_path": str(cache_path),
        "cache_sha256": cache_sha,
        "rows": int(len(joined)),
        "tickers": int(joined["ticker"].nunique()),
        "first_signal_session_index": int(joined["signal_session_index"].min()),
        "last_signal_session_index": int(joined["signal_session_index"].max()),
        "v2_feature_columns": list(V2_FULL_FEATURE_COLUMNS),
        "structure_feature_columns": list(STRUCTURE_LITE_FEATURE_COLUMNS),
        "candidate_feature_columns": list(V3_B_FEATURE_COLUMNS),
        "v2_feature_order_sha256": _feature_order_hash(tuple(V2_FULL_FEATURE_COLUMNS)),
        "candidate_feature_order_sha256": _feature_order_hash(tuple(V3_B_FEATURE_COLUMNS)),
        "coverage": coverage,
        "v2f5_v2f6_materialized": False,
        "outcome_metrics_computed": False,
        "independent_validation_claim": False,
    }
    manifest_path = output_dir / "ranking_v3_b_structure_lite_discovery_cache_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    manifest["manifest_sha256"] = sha256_file(manifest_path)
    return manifest


def _assert_discovery_cache(
    *,
    cache_path: Path,
    manifest_path: Path,
    spec_path: Path,
    addendum_path: Path,
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, str]]:
    identities = _assert_spec_files(spec_path, addendum_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "RANKING_V3_B_STRUCTURE_LITE_DISCOVERY_CACHE_FROZEN":
        raise RuntimeError("V3-B discovery cache manifest status is not frozen")
    actual_cache_sha = sha256_file(cache_path)
    if manifest.get("cache_sha256") != actual_cache_sha:
        raise RuntimeError("V3-B discovery cache hash mismatch")
    if bool(manifest.get("v2f5_v2f6_materialized", True)):
        raise RuntimeError("V3-B discovery cache claims sealed folds were materialized")
    if bool(manifest.get("outcome_metrics_computed", True)):
        raise RuntimeError("V3-B prepared cache manifest unexpectedly contains outcome metrics")

    table = pd.read_parquet(cache_path)
    if int(pd.to_numeric(table["signal_session_index"], errors="raise").max()) > MAX_DISCOVERY_SIGNAL_INDEX:
        raise RuntimeError("V3-B discovery cache contains sealed sessions")
    table = _normalize_candidate_table(table, HGB_XS_MARKET)
    required = set(STRUCTURE_LITE_FEATURE_COLUMNS)
    if not required.issubset(table.columns):
        raise RuntimeError(f"V3-B discovery cache missing structure columns: {sorted(required-set(table.columns))}")
    return table, manifest, {"cache": actual_cache_sha, "manifest": sha256_file(manifest_path), **identities}


def _score_candidate(
    table: pd.DataFrame,
    candidate: str,
    *,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    if candidate not in V3_B_CANDIDATES:
        raise ValueError(f"unknown V3-B candidate: {candidate}")
    metrics_rows: list[dict[str, Any]] = []
    prediction_rows: list[pd.DataFrame] = []
    model_hashes: dict[str, str] = {}

    for fold in DISCOVERY_FOLDS:
        assert_discovery_fold_allowed(fold.name)
        train, validation = split_v2_model_table(table, fold)
        y_train = train["binary_target"].to_numpy(dtype=int)
        model = pointwise_model(HGB_XS_MARKET) if candidate == V3_B_CONTROL else _structure_model()
        model.fit(train, y_train)
        score = pointwise_raw_score(model, validation)
        if not np.isfinite(score).all():
            raise RuntimeError(f"{candidate} {fold.name} produced non-finite scores")
        metric = evaluate_v2_scores(validation, score)
        metrics_rows.append(
            {
                "candidate": candidate,
                "fold": fold.name,
                "train_start": fold.train_start,
                "train_end": fold.train_end,
                "gap_start": fold.gap_start,
                "gap_end": fold.gap_end,
                "validation_start": fold.validation_start,
                "validation_end": fold.validation_end,
                "train_rows": int(len(train)),
                "validation_rows": int(len(validation)),
                **metric,
            }
        )
        scored = validation[["ticker", "date", "signal_session_index", "binary_target"]].copy()
        scored.insert(0, "fold", fold.name)
        scored.insert(0, "candidate", candidate)
        scored["score"] = score
        prediction_rows.append(scored)

        model_path = output_dir / f"ranking_v3_b_{candidate.lower()}_{fold.name.lower()}.joblib"
        joblib.dump(model, model_path)
        model_hashes[model_path.name] = sha256_file(model_path)

    return pd.DataFrame(metrics_rows), pd.concat(prediction_rows, ignore_index=True), model_hashes


def run_structure_discovery(
    *,
    cache_path: Path,
    cache_manifest_path: Path,
    reference_v2_dir: Path,
    spec_path: Path,
    addendum_path: Path,
    output_dir: Path,
    code_commit: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    environment = _assert_environment()
    _assert_clean_output_dir(output_dir)
    table, cache_manifest, contract_hashes = _assert_discovery_cache(
        cache_path=cache_path,
        manifest_path=cache_manifest_path,
        spec_path=spec_path,
        addendum_path=addendum_path,
    )

    reference_summary, reference_metrics, reference_predictions, reference_hashes = _read_reference_artifacts(
        reference_v2_dir
    )

    control_started = time.perf_counter()
    control_dir = output_dir / "control"
    control_dir.mkdir(parents=True, exist_ok=False)
    control_metrics, control_predictions, control_models = _score_candidate(
        table, V3_B_CONTROL, output_dir=control_dir
    )
    control_seconds = time.perf_counter() - control_started

    equivalence = prove_control_equivalence(
        control_metrics=control_metrics,
        control_predictions=control_predictions,
        reference_metrics=reference_metrics,
        reference_predictions=reference_predictions,
        reference_hashes=reference_hashes,
    )
    equivalence["status"] = "V3_B_CONTROL_EQUIVALENCE_PASS"
    equivalence["reference_summary_identity"] = {
        "sha256": reference_hashes["summary"],
        "code_commit": reference_summary.get("code_commit"),
    }
    equivalence_path = output_dir / "ranking_v3_b_control_equivalence.json"
    equivalence_path.write_text(json.dumps(equivalence, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    candidate_started = time.perf_counter()
    candidate_dir = output_dir / "structure_lite"
    candidate_dir.mkdir(parents=True, exist_ok=False)
    candidate_metrics, candidate_predictions, candidate_models = _score_candidate(
        table, V3_B_CANDIDATE, output_dir=candidate_dir
    )
    candidate_seconds = time.perf_counter() - candidate_started

    control_aggregate = _aggregate_candidate(control_metrics)
    structure_aggregate = _aggregate_candidate(candidate_metrics)
    paired_frame, paired_aggregate = _paired_metrics(candidate_metrics, control_metrics)
    absolute_pass = _absolute_sanity(structure_aggregate)
    paired_pass = _paired_promotion(paired_aggregate)
    if not absolute_pass:
        candidate_verdict = "KILL"
        decision = "V3_B_STRUCTURE_LITE_KILL_KEEP_V2_CONTROL"
    elif not paired_pass:
        candidate_verdict = "KEEP_DIAGNOSTIC"
        decision = "V3_B_STRUCTURE_LITE_KILL_KEEP_V2_CONTROL"
    else:
        candidate_verdict = "PROMOTE_FOR_NEXT_RESEARCH_STEP"
        decision = "V3_B_STRUCTURE_LITE_PROMOTE_GEOMETRY8"

    all_metrics = pd.concat([control_metrics, candidate_metrics], ignore_index=True)
    all_predictions = pd.concat([control_predictions, candidate_predictions], ignore_index=True)
    metrics_path = output_dir / "ranking_v3_b_structure_lite_f1_f4_metrics.csv"
    predictions_path = output_dir / "ranking_v3_b_structure_lite_f1_f4_predictions.parquet"
    paired_path = output_dir / "ranking_v3_b_structure_lite_paired_comparison.csv"
    all_metrics.to_csv(metrics_path, index=False)
    all_predictions.to_parquet(predictions_path, index=False)
    paired_frame.insert(0, "candidate", V3_B_CANDIDATE)
    paired_frame.to_csv(paired_path, index=False)

    aggregate = {
        V3_B_CONTROL: control_aggregate,
        V3_B_CANDIDATE: structure_aggregate,
        "paired": paired_aggregate,
        "candidate_absolute_sanity_pass": bool(absolute_pass),
        "candidate_paired_promotion_pass": bool(paired_pass),
    }
    aggregate_path = output_dir / "ranking_v3_b_structure_lite_aggregate.json"
    aggregate_path.write_text(json.dumps(aggregate, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    verdict = {
        "status": decision,
        "control_verdict": "CONTROL_REFERENCE",
        "structure_candidate_verdict": candidate_verdict,
        "selected_component": V3_B_CANDIDATE if candidate_verdict == "PROMOTE_FOR_NEXT_RESEARCH_STEP" else None,
        "v2f5_v2f6_accessed": False,
        "fresh_forward_accessed": False,
    }
    verdict_path = output_dir / "ranking_v3_b_structure_lite_verdict.json"
    verdict_path.write_text(json.dumps(verdict, indent=2, ensure_ascii=False), encoding="utf-8")

    coverage_path = output_dir / "ranking_v3_b_structure_lite_coverage.json"
    coverage_path.write_text(
        json.dumps(cache_manifest.get("coverage", {}), indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    ledger_rows = [
        {
            "hypothesis_id": V3_B_HYPOTHESIS_ID,
            "candidate_id": V3_B_CONTROL,
            "candidate_ordinal": 4,
            "result_status": "COMPLETE",
            "result_viewed": True,
            "verdict": "CONTROL_REFERENCE",
            "cumulative_candidate_count": 4,
        },
        {
            "hypothesis_id": V3_B_HYPOTHESIS_ID,
            "candidate_id": V3_B_CANDIDATE,
            "candidate_ordinal": 5,
            "result_status": "COMPLETE",
            "result_viewed": True,
            "verdict": candidate_verdict,
            "cumulative_candidate_count": 5,
        },
    ]
    ledger_path = output_dir / "ranking_v3_b_structure_lite_ledger_rows.json"
    ledger_path.write_text(json.dumps(ledger_rows, indent=2, ensure_ascii=False), encoding="utf-8")

    runtime = {
        "mode": "sequential_reference",
        "control_seconds": control_seconds,
        "structure_candidate_seconds": candidate_seconds,
        "total_seconds": time.perf_counter() - started,
        "python": sys.version,
        "platform": platform.platform(),
        "environment": environment,
    }
    runtime_path = output_dir / "ranking_v3_b_structure_lite_runtime.json"
    runtime_path.write_text(json.dumps(runtime, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    model_hashes = {**control_models, **candidate_models}
    artifacts = {
        metrics_path.name: sha256_file(metrics_path),
        predictions_path.name: sha256_file(predictions_path),
        paired_path.name: sha256_file(paired_path),
        aggregate_path.name: sha256_file(aggregate_path),
        verdict_path.name: sha256_file(verdict_path),
        coverage_path.name: sha256_file(coverage_path),
        ledger_path.name: sha256_file(ledger_path),
        runtime_path.name: sha256_file(runtime_path),
        equivalence_path.name: sha256_file(equivalence_path),
        **model_hashes,
    }
    summary = {
        "status": decision,
        "code_commit": code_commit,
        "hypothesis_id": V3_B_HYPOTHESIS_ID,
        "candidates": list(V3_B_CANDIDATES),
        "folds": [fold.name for fold in DISCOVERY_FOLDS],
        "cache_sha256": contract_hashes["cache"],
        "cache_manifest_sha256": contract_hashes["manifest"],
        "contract_identity": contract_hashes,
        "control_equivalence_status": equivalence["status"],
        "candidate_feature_columns": list(V3_B_FEATURE_COLUMNS),
        "candidate_feature_order_sha256": _feature_order_hash(tuple(V3_B_FEATURE_COLUMNS)),
        "candidate_verdict": candidate_verdict,
        "artifact_sha256": artifacts,
        "independent_validation_claim": False,
        "probability_claim": False,
        "v2f5_v2f6_accessed": False,
        "fresh_forward_accessed": False,
    }
    summary_path = output_dir / "ranking_v3_b_structure_lite_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    summary["summary_sha256"] = sha256_file(summary_path)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare or run frozen Ranking V3-B Structure-Lite discovery")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="build outcome-independent F1-F4-only Structure-Lite cache")
    prepare.add_argument("--panel", type=Path, required=True)
    prepare.add_argument("--calendar", type=Path, required=True)
    prepare.add_argument("--security-master", type=Path, required=True)
    prepare.add_argument("--v2-prepared", type=Path, required=True)
    prepare.add_argument("--v2-manifest", type=Path, required=True)
    prepare.add_argument("--spec", type=Path, required=True)
    prepare.add_argument("--addendum", type=Path, required=True)
    prepare.add_argument("--output-dir", type=Path, required=True)
    prepare.add_argument("--code-commit", required=True)

    run = sub.add_parser("run", help="run exact control then one Structure-Lite candidate on F1-F4")
    run.add_argument("--cache", type=Path, required=True)
    run.add_argument("--cache-manifest", type=Path, required=True)
    run.add_argument("--reference-v2-dir", type=Path, required=True)
    run.add_argument("--spec", type=Path, required=True)
    run.add_argument("--addendum", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--code-commit", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "prepare":
        result = prepare_structure_cache(
            panel_path=args.panel,
            calendar_path=args.calendar,
            security_master_path=args.security_master,
            v2_prepared_path=args.v2_prepared,
            v2_manifest_path=args.v2_manifest,
            spec_path=args.spec,
            addendum_path=args.addendum,
            output_dir=args.output_dir,
            code_commit=args.code_commit,
        )
    else:
        result = run_structure_discovery(
            cache_path=args.cache,
            cache_manifest_path=args.cache_manifest,
            reference_v2_dir=args.reference_v2_dir,
            spec_path=args.spec,
            addendum_path=args.addendum,
            output_dir=args.output_dir,
            code_commit=args.code_commit,
        )
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
