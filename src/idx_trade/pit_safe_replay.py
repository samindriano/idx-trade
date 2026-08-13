"""Fresh PIT-safe historical replay for the frozen V2 -> V3-B -> O2 ladder.

This runner deliberately consumes only the corrected, externally materialized
tables. It does not rebuild features, labels, or provider data, and it never
reads the prospective outcome store.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any, Iterable

import joblib
import numpy as np
import pandas as pd

from .ohlcv_o1_research import (
    V3_B_FEATURE_COLUMNS,
    _aggregate_metrics,
    evaluate_scores,
    feature_order_hash,
    hgb_pipeline,
    raw_score,
    sha256_file,
)
from .ohlcv_o2_geometry_research import (
    BASELINE_MODEL as O2_BASELINE,
    O2_FEATURE_COLUMNS,
    O2_GEOMETRY_FEATURES,
    O2_MODEL,
    _o2_survivor,
    o2_hgb_pipeline,
)
from .ranking_v3_structure_lite import _structure_model
from .research_features import assert_no_open_dependency
from .research_v2_models import (
    ALL_RANKING_V2_MODELS,
    HGB_XS_MARKET,
    PAIRWISE_LOGISTIC_XS,
    PairwiseLogisticRanker,
    candidate_feature_columns,
    pointwise_model,
    pointwise_raw_score,
)
from .research_v2_validation import (
    RANKING_V2_FOLDS,
    candidate_aggregate,
    comparison_to_control,
    evaluate_v2_scores,
    select_v2_champion,
    split_v2_model_table,
)


IMMUTABLE_PANEL_SHA256 = "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
CALENDAR_SHA256 = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
SECURITY_MASTER_SHA256 = "9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9"
FAST_H10_SHA256 = "a447b3f2208cbc320f7ec7cfa16c3dbb51107286891deca130f2fb848895b677"
EQUIVALENCE_REPORT_SHA256 = "8f8865b2f133020a94ab8d2507fbb221f4b7f59bd1775b9da51fba2f4084d554"
CORRECTED_V2_SHA256 = "b27a603cea39298f18996629a16f25990d3d04422b12ccb5d9bd1e45dbb34af8"
CORRECTED_V3_SHA256 = "7faf7f68b78dff336a908a69e8b02f6b0f741434b4ada6e17c6b1ef8d9385753"
CORRECTED_O2_SHA256 = "8b1f6c917c013a6fb9cb5733d8096b45e0b5712dfa318ad49ca7f9ca43321585"
CORRECTED_V2_KEY_SHA256 = "79d33b233f65b282189917c7226e979956da7f0599a5ba484d82a154ed1ea826"
CORRECTED_O2_KEY_SHA256 = "77dbe5aaa32fa7e35779f273bc09501140e1a1363861aa262567f59354dd0644"
V3_B_CANDIDATE = "V3-B-STRUCTURE-LITE-V1-CANDIDATE-005"
V3_B_BASELINE = "V3B_COMMON_SUPPORT_BASELINE"
V3_B_FEATURE_ORDER_SHA256 = feature_order_hash(V3_B_FEATURE_COLUMNS)
O2_FEATURE_ORDER_SHA256 = feature_order_hash(O2_FEATURE_COLUMNS)
REPLAY_BOUNDARY = "2026-07-31"


def _stable_key_hash(frame: pd.DataFrame) -> str:
    keys = frame[["ticker", "date", "signal_session_index"]].copy()
    keys["ticker"] = keys["ticker"].astype(str)
    keys["date"] = pd.to_datetime(keys["date"], errors="raise").dt.strftime("%Y-%m-%d")
    keys["signal_session_index"] = pd.to_numeric(keys["signal_session_index"], errors="raise").astype(int)
    lines = keys.sort_values(["ticker", "date", "signal_session_index"], kind="mergesort").astype(str).agg("|".join, axis=1)
    import hashlib

    return hashlib.sha256(("\n".join(lines.tolist()) + "\n").encode("utf-8")).hexdigest()


def _read_table(path: Path, feature_columns: Iterable[str]) -> pd.DataFrame:
    table = pd.read_parquet(path)
    required = {
        "ticker",
        "date",
        "signal_session_index",
        "binary_target",
        "label_status",
        "universe_primary_liquid",
        *feature_columns,
    }
    missing = required - set(table.columns)
    if missing:
        raise RuntimeError(f"replay table {path.name} missing {sorted(missing)}")
    table = table.copy()
    table["ticker"] = table["ticker"].astype(str).str.upper().str.strip()
    table["date"] = pd.to_datetime(table["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if table["date"].isna().any():
        raise RuntimeError(f"replay table {path.name} has invalid dates")
    table["signal_session_index"] = pd.to_numeric(table["signal_session_index"], errors="raise").astype(int)
    table["binary_target"] = pd.to_numeric(table["binary_target"], errors="raise").astype(int)
    if not set(table["binary_target"].unique()).issubset({0, 1}):
        raise RuntimeError(f"replay table {path.name} contains non-binary labels")
    if set(table["label_status"].astype(str)) != {"TP_FIRST", "SL_FIRST"}:
        raise RuntimeError(f"replay table {path.name} has unexpected H10 label status")
    mapping = table.groupby("label_status")["binary_target"].unique().to_dict()
    if set(mapping.get("TP_FIRST", ())) != {1} or set(mapping.get("SL_FIRST", ())) != {0}:
        raise RuntimeError(f"replay table {path.name} has invalid H10 mapping: {mapping}")
    if not _strict_boolean_series(table["universe_primary_liquid"], "universe_primary_liquid").all():
        raise RuntimeError(f"replay table {path.name} is not primary-liquid only")
    if table.duplicated(["ticker", "date"]).any():
        raise RuntimeError(f"replay table {path.name} contains duplicate ticker/date rows")
    if table["date"].max() > pd.Timestamp(REPLAY_BOUNDARY):
        raise RuntimeError(f"replay table {path.name} crosses the historical boundary")
    return table.sort_values(["signal_session_index", "ticker"], kind="mergesort").reset_index(drop=True)


def _strict_boolean_series(values: pd.Series, label: str) -> pd.Series:
    """Parse only actual booleans; never coerce strings/numbers truthily."""

    if values.isna().any():
        raise RuntimeError(f"{label} contains null boolean values")
    if pd.api.types.is_bool_dtype(values.dtype):
        return values.astype(bool)
    if not values.map(lambda value: isinstance(value, (bool, np.bool_))).all():
        raise RuntimeError(f"{label} must contain strict boolean values")
    return values.map(bool).astype(bool)


def validate_replay_tables(v2: pd.DataFrame, v3: pd.DataFrame, o2: pd.DataFrame) -> dict[str, Any]:
    if len(v2) != 292_631 or v2["ticker"].nunique() != 737:
        raise RuntimeError("corrected V2 population is not 292,631 rows / 737 tickers")
    if len(v3) != len(v2) or v3["ticker"].nunique() != v2["ticker"].nunique():
        raise RuntimeError("corrected V3-B population differs from corrected V2")
    v2_keys = v2[["ticker", "date", "signal_session_index"]].reset_index(drop=True)
    v3_keys = v3[["ticker", "date", "signal_session_index"]].reset_index(drop=True)
    if not v2_keys.equals(v3_keys):
        raise RuntimeError("corrected V2/V3-B row identities differ")
    for column in candidate_feature_columns(HGB_XS_MARKET):
        left = v2[column].to_numpy(dtype=float)
        right = v3[column].to_numpy(dtype=float)
        if not np.array_equal(left, right, equal_nan=True):
            raise RuntimeError(f"corrected V3-B changed V2 feature values: {column}")
    if len(o2) != 278_166 or o2["ticker"].nunique() != 729:
        raise RuntimeError("corrected O2 population is not 278,166 rows / 729 tickers")
    o2_keys = o2[["ticker", "date", "signal_session_index"]]
    v3_key_set = set(map(tuple, v3_keys.itertuples(index=False, name=None)))
    if not set(map(tuple, o2_keys.itertuples(index=False, name=None))).issubset(v3_key_set):
        raise RuntimeError("corrected O2 contains identities outside corrected V3-B")
    if not np.isfinite(o2[list(O2_GEOMETRY_FEATURES)].to_numpy(dtype=float)).all():
        raise RuntimeError("corrected O2 geometry contains non-finite values")
    v2_key = _stable_key_hash(v2)
    o2_key = _stable_key_hash(o2)
    if v2_key != CORRECTED_V2_KEY_SHA256 or o2_key != CORRECTED_O2_KEY_SHA256:
        raise RuntimeError(f"corrected key hash mismatch: V2={v2_key} O2={o2_key}")
    return {
        "v2_rows": int(len(v2)),
        "v2_tickers": int(v2["ticker"].nunique()),
        "v2_key_sha256": v2_key,
        "v3_b_rows": int(len(v3)),
        "v3_b_tickers": int(v3["ticker"].nunique()),
        "o2_rows": int(len(o2)),
        "o2_tickers": int(o2["ticker"].nunique()),
        "o2_key_sha256": o2_key,
    }


def verify_v2_v3_control_equivalence(
    v2_predictions_path: Path,
    v3_predictions_path: Path,
) -> dict[str, Any]:
    """Verify exact V2 HGB_XS_MARKET ↔ V3-B control replay equivalence."""

    v2 = pd.read_parquet(v2_predictions_path)
    v3 = pd.read_parquet(v3_predictions_path)
    left = v2[v2["candidate"].eq(HGB_XS_MARKET)].copy()
    right = v3[v3["model"].eq(V3_B_BASELINE)].copy()
    keys = ["fold", "ticker", "date", "signal_session_index", "binary_target"]
    required_left = set(keys) | {"score"}
    required_right = set(keys) | {"score"}
    if not required_left.issubset(left.columns) or not required_right.issubset(right.columns):
        raise RuntimeError("V2/V3 control predictions are missing equivalence columns")
    left = left.sort_values(keys, kind="mergesort").reset_index(drop=True)
    right = right.sort_values(keys, kind="mergesort").reset_index(drop=True)
    if not left[keys].equals(right[keys]):
        raise RuntimeError("V2 HGB_XS_MARKET and V3-B control identities differ")
    left_score = pd.to_numeric(left["score"], errors="raise").to_numpy(dtype=float)
    right_score = pd.to_numeric(right["score"], errors="raise").to_numpy(dtype=float)
    if len(left_score) != len(right_score):
        raise RuntimeError("V2/V3 control prediction row counts differ")
    max_abs_diff = float(np.max(np.abs(left_score - right_score))) if len(left_score) else 0.0
    if max_abs_diff != 0.0:
        raise RuntimeError(f"V2/V3 control scores differ: max_abs_diff={max_abs_diff}")
    return {
        "status": "V2_V3_CONTROL_EXACT_EQUIVALENCE_PASS",
        "v2_model": HGB_XS_MARKET,
        "v3_model": V3_B_BASELINE,
        "rows": int(len(left)),
        "identity_exact": True,
        "score_exact": True,
        "max_score_abs_diff": max_abs_diff,
        "folds": [str(value) for value in left["fold"].drop_duplicates().tolist()],
        "v2_predictions_sha256": sha256_file(v2_predictions_path),
        "v3_predictions_sha256": sha256_file(v3_predictions_path),
    }


def apply_conditional_ladder(
    v2_summary: dict[str, Any],
    v3_summary: dict[str, Any],
    o2_summary: dict[str, Any],
) -> dict[str, Any]:
    """Keep downstream evidence diagnostic when its parent does not pass."""

    v3_parent_pass = v3_summary.get("decision") == "V3_FINAL_STRUCTURE_LITE_LATE_DEV_PASS"
    diagnostic_decision = str(o2_summary.get("diagnostic_decision", o2_summary.get("decision", "UNKNOWN")))
    clean_lineage_decision = (
        "O2_CLEAN_LINEAGE_SURVIVOR" if v3_parent_pass and diagnostic_decision == "O2_SURVIVOR" else
        "O2_CLEAN_LINEAGE_NO_SURVIVOR" if v3_parent_pass else
        "O2_DIAGNOSTIC_ORPHANED_PARENT"
    )
    o2_summary["diagnostic_decision"] = diagnostic_decision
    o2_summary["clean_lineage_decision"] = clean_lineage_decision
    o2_summary["parent_v3_b_decision"] = v3_summary.get("decision")
    o2_summary["conditional_ladder_policy"] = "downstream_verdict_does_not_automatically_propagate"
    o2_summary["decision"] = clean_lineage_decision
    return {
        "v2": {"status": v2_summary.get("champion_status"), "champion": v2_summary.get("champion")},
        "v3_b": {"status": v3_summary.get("decision"), "parent_pass": v3_parent_pass},
        "o2": {
            "diagnostic_decision": diagnostic_decision,
            "clean_lineage_decision": clean_lineage_decision,
            "parent_v3_b_decision": v3_summary.get("decision"),
        },
        "policy": "downstream_verdict_does_not_automatically_propagate",
    }


def review_existing_replay_artifacts(replay_root: Path, output_dir: Path) -> dict[str, Any]:
    """Audit an already-completed replay without refitting or rewriting it."""

    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError(f"review output must be new or empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = replay_root / "artifact_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_mismatches: list[dict[str, str]] = []
    for relative, expected in manifest.get("artifact_sha256", {}).items():
        path = replay_root / relative
        actual = sha256_file(path) if path.is_file() else "MISSING"
        if actual != expected:
            manifest_mismatches.append({"path": relative, "expected": expected, "actual": actual})
    if manifest_mismatches:
        raise RuntimeError(f"existing replay manifest mismatch: {manifest_mismatches[:3]}")
    v2_summary = json.loads((replay_root / "v2" / "summary.json").read_text(encoding="utf-8"))
    v3_summary = json.loads((replay_root / "v3b" / "summary.json").read_text(encoding="utf-8"))
    o2_summary = json.loads((replay_root / "o2" / "summary.json").read_text(encoding="utf-8"))
    equivalence = verify_v2_v3_control_equivalence(
        replay_root / "v2" / "predictions.parquet",
        replay_root / "v3b" / "predictions.parquet",
    )
    ladder = apply_conditional_ladder(v2_summary, v3_summary, o2_summary)
    sources = {
        "replay_manifest": sha256_file(manifest_path),
        "v2_predictions": sha256_file(replay_root / "v2" / "predictions.parquet"),
        "v3_b_predictions": sha256_file(replay_root / "v3b" / "predictions.parquet"),
        "v3_b_summary": sha256_file(replay_root / "v3b" / "summary.json"),
        "o2_summary": sha256_file(replay_root / "o2" / "summary.json"),
    }
    review = {
        "status": "PIT_SAFE_REPLAY_REVIEW_COMPLETE",
        "replay_root": str(replay_root),
        "existing_manifest_artifacts_valid": True,
        "source_sha256": sources,
        "v2_v3_control_equivalence": equivalence,
        "conditional_ladder": ladder,
        "refit_performed": False,
        "provider_calls": False,
        "fresh_forward_outcomes_accessed": False,
        "canonical_models_overwritten": False,
    }
    review_path = output_dir / "review_summary.json"
    review_path.write_text(json.dumps(review, indent=2, sort_keys=True, default=str), encoding="utf-8")
    artifact_manifest = {
        "schema": "idx-trade/pit-safe-replay-review-v1",
        "review_summary_sha256": sha256_file(review_path),
        "source_sha256": sources,
    }
    artifact_manifest_path = output_dir / "artifact_manifest.json"
    artifact_manifest_path.write_text(json.dumps(artifact_manifest, indent=2, sort_keys=True), encoding="utf-8")
    return {
        **review,
        "review_summary_path": str(review_path),
        "review_summary_sha256": sha256_file(review_path),
        "artifact_manifest_path": str(artifact_manifest_path),
        "artifact_manifest_sha256": sha256_file(artifact_manifest_path),
    }


def _save_model(model: object, path: Path) -> str:
    joblib.dump(model, path)
    return sha256_file(path)


def _run_v2(table: pd.DataFrame, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    metrics_rows: list[dict[str, Any]] = []
    prediction_rows: list[pd.DataFrame] = []
    pairwise_diagnostics: dict[str, dict[str, int]] = {}
    model_hashes: dict[str, str] = {}
    started = time.perf_counter()
    for fold in RANKING_V2_FOLDS:
        train, validation = split_v2_model_table(table, fold)
        fold_scores: dict[str, np.ndarray] = {}
        for candidate in ALL_RANKING_V2_MODELS:
            if candidate == PAIRWISE_LOGISTIC_XS:
                fitted = PairwiseLogisticRanker().fit(train, train["binary_target"].to_numpy(dtype=int))
                scores = fitted.score(validation)
                pairwise_diagnostics[fold.name] = {
                    "pair_days": int(fitted.fitted_pair_days),
                    "unique_pairs": int(fitted.fitted_unique_pairs),
                }
            else:
                fitted = pointwise_model(candidate)
                fitted.fit(train, train["binary_target"].to_numpy(dtype=int))
                scores = pointwise_raw_score(fitted, validation)
            if not np.isfinite(scores).all():
                raise RuntimeError(f"{candidate} {fold.name} produced non-finite scores")
            fold_scores[candidate] = scores
            metrics_rows.append(
                {
                    "candidate": candidate,
                    "fold": fold.name,
                    **fold.__dict__,
                    "train_rows": int(len(train)),
                    "validation_rows": int(len(validation)),
                    "feature_count": int(len(candidate_feature_columns(candidate))),
                    "feature_order_sha256": feature_order_hash(candidate_feature_columns(candidate)),
                    **evaluate_v2_scores(validation, scores),
                }
            )
            prediction_rows.append(
                pd.DataFrame(
                    {
                        "candidate": candidate,
                        "fold": fold.name,
                        "ticker": validation["ticker"].to_numpy(),
                        "date": validation["date"].to_numpy(),
                        "signal_session_index": validation["signal_session_index"].to_numpy(),
                        "binary_target": validation["binary_target"].to_numpy(),
                        "score": scores,
                    }
                )
            )
            model_path = output_dir / f"{candidate.lower()}_{fold.name.lower()}.joblib"
            model_hashes[model_path.name] = _save_model(fitted, model_path)
    metrics = pd.DataFrame(metrics_rows)
    aggregate = candidate_aggregate(metrics)
    champion_status, champion, _ = select_v2_champion(metrics)
    comparison = comparison_to_control(aggregate)
    predictions = pd.concat(prediction_rows, ignore_index=True)
    metrics.to_csv(output_dir / "fold_metrics.csv", index=False)
    aggregate.to_csv(output_dir / "candidate_aggregate.csv", index=False)
    comparison.to_csv(output_dir / "comparison_to_control.csv", index=False)
    predictions.to_parquet(output_dir / "predictions.parquet", index=False)
    summary = {
        "status": "V2_REPLAY_COMPLETE",
        "champion_status": champion_status,
        "champion": champion,
        "models": list(ALL_RANKING_V2_MODELS),
        "fold_count": len(RANKING_V2_FOLDS),
        "row_count": int(len(table)),
        "ticker_count": int(table["ticker"].nunique()),
        "pairwise_diagnostics": pairwise_diagnostics,
        "model_artifact_sha256": model_hashes,
        "runtime_seconds": float(time.perf_counter() - started),
        "fresh_forward_outcomes_accessed": False,
        "provider_calls": False,
        "execution_grade_promoted": False,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def _run_v3b(table: pd.DataFrame, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    models = (V3_B_BASELINE, V3_B_CANDIDATE)
    metrics_rows: list[dict[str, Any]] = []
    prediction_rows: list[pd.DataFrame] = []
    model_hashes: dict[str, str] = {}
    started = time.perf_counter()
    for fold in RANKING_V2_FOLDS:
        train, validation = split_v2_model_table(table, fold)
        fold_scores: dict[str, np.ndarray] = {}
        for model_name in models:
            columns = candidate_feature_columns(HGB_XS_MARKET) if model_name == V3_B_BASELINE else V3_B_FEATURE_COLUMNS
            fitted = pointwise_model(HGB_XS_MARKET) if model_name == V3_B_BASELINE else _structure_model()
            fitted.fit(train, train["binary_target"].to_numpy(dtype=int))
            scores = pointwise_raw_score(fitted, validation)
            if not np.isfinite(scores).all():
                raise RuntimeError(f"{model_name} {fold.name} produced non-finite scores")
            fold_scores[model_name] = scores
            metrics_rows.append(
                {
                    "model": model_name,
                    "fold": fold.name,
                    **fold.__dict__,
                    "train_rows": int(len(train)),
                    "validation_rows": int(len(validation)),
                    "feature_count": int(len(columns)),
                    "feature_order_sha256": feature_order_hash(columns),
                    **evaluate_scores(validation, scores),
                    "paired_pr_auc_vs_baseline": np.nan,
                }
            )
            prediction_rows.append(
                pd.DataFrame(
                    {
                        "model": model_name,
                        "fold": fold.name,
                        "ticker": validation["ticker"].to_numpy(),
                        "date": validation["date"].to_numpy(),
                        "signal_session_index": validation["signal_session_index"].to_numpy(),
                        "binary_target": validation["binary_target"].to_numpy(),
                        "score": scores,
                    }
                )
            )
            model_path = output_dir / f"{model_name.lower()}_{fold.name.lower()}.joblib"
            model_hashes[model_path.name] = _save_model(fitted, model_path)
        baseline_pr = float(evaluate_scores(validation, fold_scores[V3_B_BASELINE])["pr_auc"])
        for row in metrics_rows[-2:]:
            if row["model"] == V3_B_CANDIDATE:
                row["paired_pr_auc_vs_baseline"] = float(row["pr_auc"] - baseline_pr)
    metrics = pd.DataFrame(metrics_rows)
    aggregate = _aggregate_metrics(metrics)
    paired = metrics[metrics["model"].eq(V3_B_CANDIDATE)].merge(
        metrics[metrics["model"].eq(V3_B_BASELINE)][["fold", "pr_auc", "roc_auc", "q5_minus_q1", "top_decile_lift"]],
        on="fold", suffixes=("", "_baseline"), validate="one_to_one",
    )
    paired["pr_auc_change"] = paired["pr_auc"] - paired["pr_auc_baseline"]
    paired["roc_auc_change"] = paired["roc_auc"] - paired["roc_auc_baseline"]
    paired["q5_minus_q1_change"] = paired["q5_minus_q1"] - paired["q5_minus_q1_baseline"]
    paired["top_decile_lift_change"] = paired["top_decile_lift"] - paired["top_decile_lift_baseline"]
    late = paired[paired["fold"].isin(["V2F5", "V2F6"])].sort_values("fold")
    absolute_pass = bool(
        len(late) == 2
        and np.isfinite(late[["pr_auc_minus_prevalence", "roc_auc", "q5_minus_q1"]].to_numpy(dtype=float)).all()
        and (late["pr_auc_minus_prevalence"] > 0).all()
        and (late["roc_auc"] > 0.5).all()
        and (late["q5_minus_q1"] > 0).all()
    )
    paired_pass = bool(
        len(late) == 2
        and (late["pr_auc_change"] >= 0).all()
        and float(late["pr_auc_change"].median()) >= 0.001
        and float(late["roc_auc_change"].median()) >= -0.005
        and (late["q5_minus_q1_change"] >= 0).all()
    )
    decision = "V3_FINAL_STRUCTURE_LITE_LATE_DEV_PASS" if absolute_pass and paired_pass else "V3_FINAL_STRUCTURE_LITE_LATE_DEV_FAIL_RETAIN_V2"
    predictions = pd.concat(prediction_rows, ignore_index=True)
    metrics.to_csv(output_dir / "fold_metrics.csv", index=False)
    aggregate.to_csv(output_dir / "aggregate_metrics.csv", index=False)
    paired.to_csv(output_dir / "paired.csv", index=False)
    predictions.to_parquet(output_dir / "predictions.parquet", index=False)
    verdict = {
        "status": decision,
        "absolute_gate_pass": absolute_pass,
        "paired_gate_pass": paired_pass,
        "final_architecture": V3_B_CANDIDATE if decision.endswith("PASS") else HGB_XS_MARKET,
        "late_fold_rule": "V2F5/V2F6 exact frozen V3-B final late-development gates",
    }
    (output_dir / "verdict.json").write_text(json.dumps(verdict, indent=2, sort_keys=True), encoding="utf-8")
    summary = {
        "status": "V3_B_REPLAY_COMPLETE",
        "decision": decision,
        "models": list(models),
        "fold_count": len(RANKING_V2_FOLDS),
        "row_count": int(len(table)),
        "ticker_count": int(table["ticker"].nunique()),
        "feature_order_sha256": V3_B_FEATURE_ORDER_SHA256,
        "model_artifact_sha256": model_hashes,
        "fresh_forward_outcomes_accessed": False,
        "provider_calls": False,
        "execution_grade_promoted": False,
        "runtime_seconds": float(time.perf_counter() - started),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def _run_o2(table: pd.DataFrame, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    models = (O2_BASELINE, O2_MODEL)
    metrics_rows: list[dict[str, Any]] = []
    prediction_rows: list[pd.DataFrame] = []
    model_hashes: dict[str, str] = {}
    started = time.perf_counter()
    for fold in RANKING_V2_FOLDS:
        train, validation = split_v2_model_table(table, fold)
        fold_scores: dict[str, np.ndarray] = {}
        for model_name in models:
            columns = V3_B_FEATURE_COLUMNS if model_name == O2_BASELINE else O2_FEATURE_COLUMNS
            fitted = o2_hgb_pipeline(tuple(columns))
            fitted.fit(train[list(columns)], train["binary_target"].to_numpy(dtype=int))
            scores = raw_score(fitted, validation)
            if not np.isfinite(scores).all():
                raise RuntimeError(f"{model_name} {fold.name} produced non-finite scores")
            fold_scores[model_name] = scores
            metrics_rows.append(
                {
                    "model": model_name,
                    "fold": fold.name,
                    **fold.__dict__,
                    "train_rows": int(len(train)),
                    "validation_rows": int(len(validation)),
                    "feature_count": int(len(columns)),
                    "feature_order_sha256": feature_order_hash(columns),
                    **evaluate_scores(validation, scores),
                    "paired_pr_auc_vs_baseline": np.nan,
                }
            )
            prediction_rows.append(
                pd.DataFrame(
                    {
                        "model": model_name,
                        "fold": fold.name,
                        "ticker": validation["ticker"].to_numpy(),
                        "date": validation["date"].to_numpy(),
                        "signal_session_index": validation["signal_session_index"].to_numpy(),
                        "binary_target": validation["binary_target"].to_numpy(),
                        "score": scores,
                    }
                )
            )
            model_path = output_dir / f"{model_name.lower()}_{fold.name.lower()}.joblib"
            model_hashes[model_path.name] = _save_model(fitted, model_path)
        baseline_pr = float(evaluate_scores(validation, fold_scores[O2_BASELINE])["pr_auc"])
        for row in metrics_rows[-2:]:
            if row["model"] == O2_MODEL:
                row["paired_pr_auc_vs_baseline"] = float(row["pr_auc"] - baseline_pr)
    metrics = pd.DataFrame(metrics_rows)
    aggregate = _aggregate_metrics(metrics)
    decision, survivor = _o2_survivor(metrics, aggregate)
    predictions = pd.concat(prediction_rows, ignore_index=True)
    metrics.to_csv(output_dir / "fold_metrics.csv", index=False)
    aggregate.to_csv(output_dir / "aggregate_metrics.csv", index=False)
    survivor.to_csv(output_dir / "survivor_decision.csv", index=False)
    predictions.to_parquet(output_dir / "predictions.parquet", index=False)
    summary = {
        "status": "O2_REPLAY_COMPLETE",
        "decision": decision,
        "diagnostic_decision": decision,
        "models": list(models),
        "fold_count": len(RANKING_V2_FOLDS),
        "row_count": int(len(table)),
        "ticker_count": int(table["ticker"].nunique()),
        "feature_order_sha256": O2_FEATURE_ORDER_SHA256,
        "model_artifact_sha256": model_hashes,
        "fresh_forward_outcomes_accessed": False,
        "provider_calls": False,
        "execution_grade_promoted": False,
        "runtime_seconds": float(time.perf_counter() - started),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def _artifact_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)).replace("\\", "/"): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "artifact_manifest.json"
    }


def run_replay(
    *,
    panel_path: Path,
    calendar_path: Path,
    security_master_path: Path,
    fast_h10_path: Path,
    equivalence_report_path: Path,
    corrected_v2_path: Path,
    corrected_v3_path: Path,
    corrected_o2_path: Path,
    corrected_report_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError(f"replay output must be new or empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    expected_files = {
        "immutable_panel": (panel_path, IMMUTABLE_PANEL_SHA256),
        "official_calendar": (calendar_path, CALENDAR_SHA256),
        "security_master": (security_master_path, SECURITY_MASTER_SHA256),
        "fast_h10_labels": (fast_h10_path, FAST_H10_SHA256),
        "equivalence_report": (equivalence_report_path, EQUIVALENCE_REPORT_SHA256),
        "corrected_v2": (corrected_v2_path, CORRECTED_V2_SHA256),
        "corrected_v3_b": (corrected_v3_path, CORRECTED_V3_SHA256),
        "corrected_o2": (corrected_o2_path, CORRECTED_O2_SHA256),
        "corrected_reconstruction_report": (corrected_report_path, ""),
    }
    input_hashes: dict[str, str] = {}
    for label, (path, expected) in expected_files.items():
        actual = sha256_file(path)
        if expected and actual != expected:
            raise RuntimeError(f"{label} SHA mismatch: expected={expected} actual={actual}")
        input_hashes[label] = actual
    equivalence = json.loads(equivalence_report_path.read_text(encoding="utf-8"))
    if equivalence.get("status") != "FULL_PANEL_LEGACY_FAST_EQUIVALENT" or equivalence.get("legacy_fast_equal") is not True:
        raise RuntimeError("fast-H10 equivalence report is not an exact PASS")
    corrected_report = json.loads(corrected_report_path.read_text(encoding="utf-8"))
    if corrected_report.get("status") != "REPRODUCTION_BLOCKED" or corrected_report.get("koci_2023_10_06_removed") is not True:
        raise RuntimeError("corrected input report identity is not the expected PIT-safe reconstruction")
    v2 = _read_table(corrected_v2_path, set(candidate_feature_columns(HGB_XS_MARKET)))
    v3 = _read_table(corrected_v3_path, set(V3_B_FEATURE_COLUMNS))
    o2 = _read_table(corrected_o2_path, set(O2_FEATURE_COLUMNS))
    populations = validate_replay_tables(v2, v3, o2)
    preflight = {
        "status": "PIT_SAFE_REPLAY_PREFLIGHT_PASS",
        "input_sha256": input_hashes,
        "populations": populations,
        "h10_equivalence_status": equivalence.get("status"),
        "h10_equivalence_report_legacy_fast_equal": equivalence.get("legacy_fast_equal"),
        "h10_boundary": REPLAY_BOUNDARY,
        "v2_feature_order_sha256": {name: feature_order_hash(candidate_feature_columns(name)) for name in ALL_RANKING_V2_MODELS},
        "v3_b_feature_order_sha256": V3_B_FEATURE_ORDER_SHA256,
        "o2_feature_order_sha256": O2_FEATURE_ORDER_SHA256,
        "folds": [fold.__dict__ for fold in RANKING_V2_FOLDS],
        "fresh_forward_outcomes_accessed": False,
        "provider_calls": False,
        "execution_grade_promoted": False,
    }
    (output_dir / "preflight_contract.json").write_text(json.dumps(preflight, indent=2, sort_keys=True), encoding="utf-8")
    v2_summary = _run_v2(v2, output_dir / "v2")
    v3_summary = _run_v3b(v3, output_dir / "v3b")
    o2_summary = _run_o2(o2, output_dir / "o2")
    control_equivalence = verify_v2_v3_control_equivalence(
        output_dir / "v2" / "predictions.parquet",
        output_dir / "v3b" / "predictions.parquet",
    )
    ladder = apply_conditional_ladder(v2_summary, v3_summary, o2_summary)
    summary = {
        "status": "PIT_SAFE_HISTORICAL_REPLAY_COMPLETE",
        "lineage": "PIT-SAFE-RECONSTRUCTION-V1",
        "historical_boundary": REPLAY_BOUNDARY,
        "preflight": preflight,
        "v2": v2_summary,
        "v3_b": v3_summary,
        "o2": o2_summary,
        "v2_v3_control_equivalence": control_equivalence,
        "conditional_ladder": ladder,
        "fresh_forward_outcomes_accessed": False,
        "provider_calls": False,
        "execution_grade_promoted": False,
        "canonical_models_overwritten": False,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    manifest = {
        "schema": "idx-trade/pit-safe-historical-replay-v1",
        "summary": summary,
        "input_sha256": input_hashes,
        "artifact_sha256": _artifact_hashes(output_dir),
        "environment": {"python": sys.version, "platform": platform.platform(), "pandas": pd.__version__, "numpy": np.__version__},
    }
    manifest_path = output_dir / "artifact_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str), encoding="utf-8")
    manifest_sha = sha256_file(manifest_path)
    return {"summary": summary, "manifest_sha256": manifest_sha, "artifact_count": len(manifest["artifact_sha256"]), "artifact_manifest_path": str(manifest_path)}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("panel_path", "calendar_path", "security_master_path", "fast_h10_path", "equivalence_report_path", "corrected_v2_path", "corrected_v3_path", "corrected_o2_path", "corrected_report_path", "output_dir"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    return parser


def main() -> int:
    result = run_replay(**vars(_parser().parse_args()))
    print(json.dumps({"status": result["summary"]["status"], "manifest_sha256": result["manifest_sha256"], "artifact_count": result["artifact_count"], "v2": result["summary"]["v2"], "v3_b": result["summary"]["v3_b"], "o2": result["summary"]["o2"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
