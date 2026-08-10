from __future__ import annotations

import argparse
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
from .ranking_v3_structure_lite import (
    CALENDAR_SHA256,
    MAX_DISCOVERY_SIGNAL_INDEX,
    PANEL_SHA256,
    SECURITY_MASTER_SHA256,
    V2_MANIFEST_SHA256,
    V2_PREPARED_SHA256,
    _feature_order_hash,
    _read_calendar,
    _read_panel_bounded,
    _read_v2_discovery_subset,
)
from .research_baselines import (
    RANDOM_SEED,
    TREE_L2,
    TREE_LEARNING_RATE,
    TREE_MAX_ITER,
    TREE_MAX_LEAF_NODES,
)
from .research_features import assert_no_open_dependency, build_baseline_features
from .research_stage5 import assign_within_date_buckets, ranking_metrics
from .research_v2_features import V2_FULL_FEATURE_COLUMNS, build_v2_feature_table
from .research_v2_models import HGB_XS_MARKET, pointwise_model, pointwise_raw_score
from .research_v2_validation import RANKING_V2_FOLDS, evaluate_v2_scores, split_v2_model_table
from .research_v3_sector import (
    SECTOR_ASSIGNMENT_AUDIT_COLUMNS,
    SECTOR_FEATURE_COLUMNS,
    SECTOR_SOURCE_COLUMNS,
    build_sector_relative_features,
    sector_group_diagnostics,
    sector_history_provenance,
    validate_sector_history,
)
from .stage5_ranking_holdout import _assert_environment


V3_D_HYPOTHESIS_ID = "V3-D-SECTOR-RELATIVE-V1"
V3_D_CONTROL = "V3-D-SECTOR-RELATIVE-V1-CONTROL-008"
V3_D_CANDIDATE = "V3-D-SECTOR-RELATIVE-V1-CANDIDATE-009"
V3_D_CANDIDATES = (V3_D_CONTROL, V3_D_CANDIDATE)
V3_D_FEATURE_COLUMNS = (*V2_FULL_FEATURE_COLUMNS, *SECTOR_FEATURE_COLUMNS)

SECTOR_ASSIGNMENT_MIN = 0.90
SECTOR_FEATURE_FINITE_MIN = 0.80
VALIDATION_DISTINCT_SECTORS_MIN = 8
PER_SECTOR_DIAGNOSTIC_MIN_ROWS = 300
V2_RECOMPUTE_ATOL = 1e-12
SEALED_FOLD_NAMES = frozenset(fold.name for fold in RANKING_V2_FOLDS[4:])

AUTHORIZATION_STATUS = "V3_D_OUTCOME_RUN_AUTHORIZED"


def assert_discovery_fold_allowed(name: str) -> None:
    allowed = {fold.name for fold in DISCOVERY_FOLDS}
    if name in SEALED_FOLD_NAMES or name not in allowed:
        raise PermissionError(f"{name} is sealed for V3-D sector discovery")


def _sector_model() -> Pipeline:
    assert_no_open_dependency(V3_D_FEATURE_COLUMNS)
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
        [("numeric", numeric, list(V3_D_FEATURE_COLUMNS))],
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


def _max_numeric_diff(left: pd.Series, right: pd.Series) -> float:
    a = pd.to_numeric(left, errors="coerce").to_numpy(dtype=float)
    b = pd.to_numeric(right, errors="coerce").to_numpy(dtype=float)
    if not np.allclose(a, b, rtol=0.0, atol=V2_RECOMPUTE_ATOL, equal_nan=True):
        finite = np.isfinite(a) & np.isfinite(b)
        return float(np.max(np.abs(a[finite] - b[finite]))) if finite.any() else float("inf")
    finite = np.isfinite(a) & np.isfinite(b)
    return float(np.max(np.abs(a[finite] - b[finite]))) if finite.any() else 0.0


def _prove_recomputed_v2_equivalence(v2: pd.DataFrame, feature_frame: pd.DataFrame) -> dict[str, float]:
    keyed = feature_frame.set_index(["ticker", "date"])
    if keyed.index.duplicated().any():
        raise RuntimeError("V3-D outcome-independent feature frame contains duplicate ticker/date")
    keys = pd.MultiIndex.from_frame(v2[["ticker", "date"]])
    missing = keys.difference(keyed.index)
    if len(missing):
        raise RuntimeError(f"V3-D recomputed feature frame missing {len(missing)} V2 rows")
    aligned = keyed.reindex(keys)
    diffs: dict[str, float] = {}
    for column in V2_FULL_FEATURE_COLUMNS:
        diff = _max_numeric_diff(v2[column], aligned[column])
        if not np.isfinite(diff) or diff > V2_RECOMPUTE_ATOL:
            raise RuntimeError(f"V3-D recomputed V2 feature mismatch {column}: max_abs_diff={diff}")
        diffs[column] = diff
    return diffs


def _block_coverage(block: pd.DataFrame, *, validation: bool) -> dict[str, Any]:
    assigned = block["sector_code"].notna()
    assignment_rate = float(assigned.mean()) if len(block) else 0.0
    feature_rates: dict[str, float] = {}
    for column in SECTOR_FEATURE_COLUMNS:
        values = pd.to_numeric(block[column], errors="coerce").to_numpy(dtype=float)
        feature_rates[column] = float(np.isfinite(values).mean()) if len(values) else 0.0
    distinct_sectors = int(block.loc[assigned, "sector_code"].nunique())
    gate = bool(
        assignment_rate >= SECTOR_ASSIGNMENT_MIN
        and all(rate >= SECTOR_FEATURE_FINITE_MIN for rate in feature_rates.values())
        and (not validation or distinct_sectors >= VALIDATION_DISTINCT_SECTORS_MIN)
    )
    return {
        "rows": int(len(block)),
        "assigned_rows": int(assigned.sum()),
        "assignment_rate": assignment_rate,
        "feature_finite_rate": feature_rates,
        "distinct_sectors": distinct_sectors,
        "gate_pass": gate,
    }


def _coverage_report(cache: pd.DataFrame) -> dict[str, Any]:
    session = pd.to_numeric(cache["signal_session_index"], errors="raise").astype(int)
    result: dict[str, Any] = {"folds": {}, "gate_pass": True}
    for fold in DISCOVERY_FOLDS:
        assert_discovery_fold_allowed(fold.name)
        train = cache[session.between(fold.train_start, fold.train_end)]
        validation = cache[session.between(fold.validation_start, fold.validation_end)]
        train_report = _block_coverage(train, validation=False)
        validation_report = _block_coverage(validation, validation=True)
        fold_gate = bool(train_report["gate_pass"] and validation_report["gate_pass"])
        result["folds"][fold.name] = {
            "train": train_report,
            "validation": validation_report,
            "gate_pass": fold_gate,
        }
        result["gate_pass"] = bool(result["gate_pass"] and fold_gate)
    return result


def validate_sector_history_artifact(
    *,
    sector_history_path: Path,
    security_master_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    _assert_clean_output_dir(output_dir)
    security_master = _read_table(security_master_path)
    history = validate_sector_history(_read_table(sector_history_path), security_master)
    normalized_path = output_dir / "ranking_v3_d_validated_sector_history.parquet"
    history.to_parquet(normalized_path, index=False)
    report = {
        "status": "RANKING_V3_D_PIT_SECTOR_HISTORY_VALIDATED",
        "sector_history_source_sha256": sha256_file(sector_history_path),
        "security_master_sha256": sha256_file(security_master_path),
        "normalized_history_sha256": sha256_file(normalized_path),
        "provenance": sector_history_provenance(history),
        "outcome_metrics_computed": False,
    }
    report_path = output_dir / "ranking_v3_d_sector_history_validation.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    report["report_sha256"] = sha256_file(report_path)
    return report


def prepare_sector_cache(
    *,
    panel_path: Path,
    calendar_path: Path,
    security_master_path: Path,
    v2_prepared_path: Path,
    v2_manifest_path: Path,
    sector_history_path: Path,
    spec_path: Path,
    output_dir: Path,
    code_commit: str,
) -> dict[str, Any]:
    _assert_clean_output_dir(output_dir)
    source_sha256 = {
        "panel": sha256_file(panel_path),
        "calendar": sha256_file(calendar_path),
        "security_master": sha256_file(security_master_path),
        "v2_prepared": sha256_file(v2_prepared_path),
        "v2_manifest": sha256_file(v2_manifest_path),
        "sector_history": sha256_file(sector_history_path),
        "provisional_spec": sha256_file(spec_path),
    }
    expected = {
        "panel": PANEL_SHA256,
        "calendar": CALENDAR_SHA256,
        "security_master": SECURITY_MASTER_SHA256,
        "v2_prepared": V2_PREPARED_SHA256,
        "v2_manifest": V2_MANIFEST_SHA256,
    }
    for key, value in expected.items():
        if source_sha256[key] != value:
            raise RuntimeError(f"V3-D source hash mismatch {key}: expected={value} actual={source_sha256[key]}")

    sessions = _read_calendar(calendar_path)
    max_date = pd.Timestamp(sessions[MAX_DISCOVERY_SIGNAL_INDEX - 1])
    panel = _read_panel_bounded(panel_path, max_date)
    security_master = _read_table(security_master_path)
    validated_history = validate_sector_history(_read_table(sector_history_path), security_master)

    baseline = build_baseline_features(panel, sessions)
    if any(column in baseline.columns for column in ("binary_target", "label_status")):
        raise RuntimeError("V3-D outcome-independent baseline unexpectedly contains labels")
    v2_feature_frame = build_v2_feature_table(baseline)
    sector_feature_frame = build_sector_relative_features(v2_feature_frame, validated_history)
    sector_feature_frame = sector_feature_frame[sector_feature_frame["date"] <= max_date].copy()

    v2_raw = _read_v2_discovery_subset(v2_prepared_path)
    v2 = _normalize_candidate_table(v2_raw, HGB_XS_MARKET)
    if int(v2["signal_session_index"].max()) > MAX_DISCOVERY_SIGNAL_INDEX:
        raise RuntimeError("V3-D V2 discovery subset contains sealed sessions")
    v2_diffs = _prove_recomputed_v2_equivalence(v2, sector_feature_frame)

    keyed = sector_feature_frame.set_index(["ticker", "date"])
    keys = pd.MultiIndex.from_frame(v2[["ticker", "date"]])
    aligned = keyed.reindex(keys)
    joined = v2.copy()
    join_columns = [*SECTOR_ASSIGNMENT_AUDIT_COLUMNS, *SECTOR_FEATURE_COLUMNS]
    for source in SECTOR_SOURCE_COLUMNS:
        join_columns.append(f"sector_group_finite_count_{source}")
    for column in join_columns:
        joined[column] = aligned[column].to_numpy()

    original_columns = list(v2.columns)
    if not joined.loc[:, original_columns].equals(v2.loc[:, original_columns]):
        raise RuntimeError("V3-D cache changed an existing V2 prepared column")
    if joined.duplicated(["ticker", "date"]).any():
        raise RuntimeError("V3-D discovery cache contains duplicate ticker/date rows")
    if int(joined["signal_session_index"].max()) > MAX_DISCOVERY_SIGNAL_INDEX:
        raise RuntimeError("V3-D cache includes sealed sessions")
    for column in SECTOR_FEATURE_COLUMNS:
        values = pd.to_numeric(joined[column], errors="coerce").to_numpy(dtype=float)
        if np.isinf(values).any():
            raise RuntimeError(f"V3-D cache contains infinite feature values: {column}")

    coverage = _coverage_report(joined)
    group_diagnostics = sector_group_diagnostics(sector_feature_frame)
    history_provenance = sector_history_provenance(validated_history)

    cache_path = output_dir / "ranking_v3_d_sector_relative_discovery_cache.parquet"
    joined.to_parquet(cache_path, index=False)
    cache_sha = sha256_file(cache_path)
    status = (
        "RANKING_V3_D_SECTOR_DISCOVERY_CACHE_FROZEN_DATA_GATE_PASS"
        if coverage["gate_pass"]
        else "RANKING_V3_D_SECTOR_DISCOVERY_CACHE_BLOCKED_COVERAGE"
    )
    manifest = {
        "status": status,
        "code_commit": code_commit,
        "source_sha256": source_sha256,
        "cache_path": str(cache_path),
        "cache_sha256": cache_sha,
        "rows": int(len(joined)),
        "tickers": int(joined["ticker"].nunique()),
        "first_signal_session_index": int(joined["signal_session_index"].min()),
        "last_signal_session_index": int(joined["signal_session_index"].max()),
        "v2_feature_columns": list(V2_FULL_FEATURE_COLUMNS),
        "sector_feature_columns": list(SECTOR_FEATURE_COLUMNS),
        "candidate_feature_columns": list(V3_D_FEATURE_COLUMNS),
        "v2_feature_order_sha256": _feature_order_hash(tuple(V2_FULL_FEATURE_COLUMNS)),
        "candidate_feature_order_sha256": _feature_order_hash(tuple(V3_D_FEATURE_COLUMNS)),
        "v2_recompute_max_abs_diff": v2_diffs,
        "sector_history_provenance": history_provenance,
        "sector_group_diagnostics": group_diagnostics,
        "coverage": coverage,
        "coverage_gate_pass": bool(coverage["gate_pass"]),
        "v2f5_v2f6_materialized": False,
        "outcome_metrics_computed": False,
        "v3_c_result_consumed": False,
        "outcome_run_authorized": False,
        "independent_validation_claim": False,
    }
    manifest_path = output_dir / "ranking_v3_d_sector_relative_discovery_cache_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    manifest["manifest_sha256"] = sha256_file(manifest_path)
    return manifest


def _assert_run_authorization(
    *,
    authorization_path: Path,
    spec_path: Path,
    cache_path: Path,
    cache_manifest_path: Path,
    code_commit: str,
) -> dict[str, Any]:
    auth = json.loads(authorization_path.read_text(encoding="utf-8"))
    if auth.get("status") != AUTHORIZATION_STATUS:
        raise PermissionError("V3-D outcome run is not authorized")
    if not bool(auth.get("v3_c_reviewed", False)):
        raise PermissionError("V3-D authorization requires completed independent V3-C review")
    expected = {
        "spec_sha256": sha256_file(spec_path),
        "cache_sha256": sha256_file(cache_path),
        "cache_manifest_sha256": sha256_file(cache_manifest_path),
        "implementation_commit": code_commit,
    }
    for key, value in expected.items():
        if auth.get(key) != value:
            raise PermissionError(f"V3-D authorization identity mismatch for {key}")
    return auth


def _assert_discovery_cache(cache_path: Path, manifest_path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "RANKING_V3_D_SECTOR_DISCOVERY_CACHE_FROZEN_DATA_GATE_PASS":
        raise RuntimeError("V3-D discovery cache did not pass PIT sector/coverage gate")
    if not bool(manifest.get("coverage_gate_pass", False)):
        raise RuntimeError("V3-D coverage gate failed")
    if bool(manifest.get("v2f5_v2f6_materialized", True)):
        raise RuntimeError("V3-D cache claims F5/F6 materialization")
    if bool(manifest.get("outcome_metrics_computed", True)):
        raise RuntimeError("V3-D prepare unexpectedly computed outcome metrics")
    if manifest.get("cache_sha256") != sha256_file(cache_path):
        raise RuntimeError("V3-D cache hash mismatch")
    table = pd.read_parquet(cache_path)
    if int(pd.to_numeric(table["signal_session_index"], errors="raise").max()) > MAX_DISCOVERY_SIGNAL_INDEX:
        raise RuntimeError("V3-D cache contains sealed sessions")
    table = _normalize_candidate_table(table, HGB_XS_MARKET)
    required = {"sector_code", *SECTOR_FEATURE_COLUMNS}
    if not required.issubset(table.columns):
        raise RuntimeError(f"V3-D cache missing columns: {sorted(required-set(table.columns))}")
    return table, manifest


def _score_candidate(
    table: pd.DataFrame,
    candidate: str,
    *,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    if candidate not in V3_D_CANDIDATES:
        raise ValueError(f"unknown V3-D candidate: {candidate}")
    metrics_rows: list[dict[str, Any]] = []
    prediction_rows: list[pd.DataFrame] = []
    model_hashes: dict[str, str] = {}
    for fold in DISCOVERY_FOLDS:
        assert_discovery_fold_allowed(fold.name)
        train, validation = split_v2_model_table(table, fold)
        model = pointwise_model(HGB_XS_MARKET) if candidate == V3_D_CONTROL else _sector_model()
        model.fit(train, train["binary_target"].to_numpy(dtype=int))
        score = pointwise_raw_score(model, validation)
        if not np.isfinite(score).all():
            raise RuntimeError(f"V3-D {candidate} {fold.name} produced non-finite score")
        metrics_rows.append(
            {
                "candidate": candidate,
                "fold": fold.name,
                "train_rows": int(len(train)),
                "validation_rows": int(len(validation)),
                **evaluate_v2_scores(validation, score),
            }
        )
        scored = validation[
            ["ticker", "date", "signal_session_index", "binary_target", "sector_code"]
        ].copy()
        scored.insert(0, "fold", fold.name)
        scored.insert(0, "candidate", candidate)
        scored["score"] = score
        prediction_rows.append(scored)
        model_path = output_dir / f"ranking_v3_d_{candidate.lower()}_{fold.name.lower()}.joblib"
        joblib.dump(model, model_path)
        model_hashes[model_path.name] = sha256_file(model_path)
    return pd.DataFrame(metrics_rows), pd.concat(prediction_rows, ignore_index=True), model_hashes


def _sector_diagnostics(
    control_predictions: pd.DataFrame,
    candidate_predictions: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_rows: list[dict[str, Any]] = []
    sector_rows: list[dict[str, Any]] = []
    for fold in [item.name for item in DISCOVERY_FOLDS]:
        control = control_predictions[control_predictions["fold"].eq(fold)].copy().reset_index(drop=True)
        candidate = candidate_predictions[candidate_predictions["fold"].eq(fold)].copy().reset_index(drop=True)
        identity = ["ticker", "date", "signal_session_index", "binary_target", "sector_code"]
        if not control[identity].equals(candidate[identity]):
            raise RuntimeError(f"V3-D diagnostic prediction identity mismatch for {fold}")

        control_bucketed = assign_within_date_buckets(
            control, score_column="score", buckets=10, output_column="decile"
        )
        candidate_bucketed = assign_within_date_buckets(
            candidate, score_column="score", buckets=10, output_column="decile"
        )
        control_top = control_bucketed[control_bucketed["decile"].eq(10)].copy()
        candidate_top = candidate_bucketed[candidate_bucketed["decile"].eq(10)].copy()
        control_keys = set(zip(control_top["ticker"], control_top["date"], strict=False))
        candidate_keys = set(zip(candidate_top["ticker"], candidate_top["date"], strict=False))
        union = control_keys | candidate_keys
        overlap = control_keys & candidate_keys
        composition = candidate_top["sector_code"].fillna("MISSING").value_counts(dropna=False)
        largest_share = float(composition.max() / composition.sum()) if len(composition) else 0.0
        summary_rows.append(
            {
                "fold": fold,
                "rows": int(len(candidate)),
                "assigned_sector_rate": float(candidate["sector_code"].notna().mean()),
                "distinct_sectors": int(candidate["sector_code"].nunique(dropna=True)),
                "control_top_decile_rows": int(len(control_top)),
                "candidate_top_decile_rows": int(len(candidate_top)),
                "top_decile_jaccard": float(len(overlap) / len(union)) if union else 1.0,
                "candidate_top_decile_largest_sector_share": largest_share,
                "candidate_top_decile_sector_composition": composition.to_dict(),
            }
        )

        for sector, positions in candidate.groupby("sector_code", dropna=True, sort=True).groups.items():
            if len(positions) < PER_SECTOR_DIAGNOSTIC_MIN_ROWS:
                continue
            positions = list(positions)
            target = candidate.loc[positions, "binary_target"].astype(int)
            row: dict[str, Any] = {
                "fold": fold,
                "sector_code": str(sector),
                "rows": int(len(positions)),
                "dates": int(candidate.loc[positions, "date"].nunique()),
                "positive_rate": float(target.mean()),
            }
            if target.nunique() != 2:
                row.update(
                    {
                        "control_pr_auc": np.nan,
                        "candidate_pr_auc": np.nan,
                        "control_pr_delta": np.nan,
                        "candidate_pr_delta": np.nan,
                        "candidate_minus_control_pr_delta": np.nan,
                    }
                )
            else:
                control_metric = ranking_metrics(
                    target,
                    control.loc[positions, "score"].to_numpy(dtype=float),
                )
                candidate_metric = ranking_metrics(
                    target,
                    candidate.loc[positions, "score"].to_numpy(dtype=float),
                )
                control_delta = float(control_metric["pr_auc"] - control_metric["positive_rate"])
                candidate_delta = float(candidate_metric["pr_auc"] - candidate_metric["positive_rate"])
                row.update(
                    {
                        "control_pr_auc": float(control_metric["pr_auc"]),
                        "candidate_pr_auc": float(candidate_metric["pr_auc"]),
                        "control_pr_delta": control_delta,
                        "candidate_pr_delta": candidate_delta,
                        "candidate_minus_control_pr_delta": candidate_delta - control_delta,
                    }
                )
            sector_rows.append(row)
    return pd.DataFrame(summary_rows), pd.DataFrame(sector_rows)


def run_sector_discovery(
    *,
    cache_path: Path,
    cache_manifest_path: Path,
    reference_v2_dir: Path,
    spec_path: Path,
    authorization_path: Path,
    output_dir: Path,
    code_commit: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    environment = _assert_environment()
    _assert_clean_output_dir(output_dir)
    table, cache_manifest = _assert_discovery_cache(cache_path, cache_manifest_path)
    authorization = _assert_run_authorization(
        authorization_path=authorization_path,
        spec_path=spec_path,
        cache_path=cache_path,
        cache_manifest_path=cache_manifest_path,
        code_commit=code_commit,
    )

    reference_summary, reference_metrics, reference_predictions, reference_hashes = _read_reference_artifacts(
        reference_v2_dir
    )

    control_dir = output_dir / "control"
    control_dir.mkdir(parents=True, exist_ok=False)
    control_started = time.perf_counter()
    control_metrics, control_predictions, control_models = _score_candidate(
        table, V3_D_CONTROL, output_dir=control_dir
    )
    control_seconds = time.perf_counter() - control_started
    equivalence = prove_control_equivalence(
        control_metrics=control_metrics,
        control_predictions=control_predictions,
        reference_metrics=reference_metrics,
        reference_predictions=reference_predictions,
        reference_hashes=reference_hashes,
    )
    equivalence["status"] = "V3_D_CONTROL_EQUIVALENCE_PASS"
    equivalence["reference_summary_identity"] = {
        "sha256": reference_hashes["summary"],
        "code_commit": reference_summary.get("code_commit"),
    }
    equivalence_path = output_dir / "ranking_v3_d_control_equivalence.json"
    equivalence_path.write_text(json.dumps(equivalence, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    candidate_dir = output_dir / "sector_relative"
    candidate_dir.mkdir(parents=True, exist_ok=False)
    candidate_started = time.perf_counter()
    candidate_metrics, candidate_predictions, candidate_models = _score_candidate(
        table, V3_D_CANDIDATE, output_dir=candidate_dir
    )
    candidate_seconds = time.perf_counter() - candidate_started

    control_aggregate = _aggregate_candidate(control_metrics)
    sector_aggregate = _aggregate_candidate(candidate_metrics)
    paired_frame, paired_aggregate = _paired_metrics(candidate_metrics, control_metrics)
    absolute_pass = _absolute_sanity(sector_aggregate)
    paired_pass = _paired_promotion(paired_aggregate)
    if absolute_pass and paired_pass:
        candidate_verdict = "PROMOTE_FOR_NEXT_RESEARCH_STEP"
        decision = "V3_D_SECTOR_PROMOTE_RELATIVE6"
    else:
        candidate_verdict = "KEEP_DIAGNOSTIC"
        decision = "V3_D_SECTOR_KILL_KEEP_V2_CONTROL"

    diagnostic_summary, diagnostic_sectors = _sector_diagnostics(control_predictions, candidate_predictions)

    metrics_path = output_dir / "ranking_v3_d_sector_relative_f1_f4_metrics.csv"
    predictions_path = output_dir / "ranking_v3_d_sector_relative_f1_f4_predictions.parquet"
    paired_path = output_dir / "ranking_v3_d_sector_relative_paired.csv"
    diagnostics_path = output_dir / "ranking_v3_d_sector_diagnostics.csv"
    sector_metrics_path = output_dir / "ranking_v3_d_per_sector_metrics.csv"
    pd.concat([control_metrics, candidate_metrics], ignore_index=True).to_csv(metrics_path, index=False)
    pd.concat([control_predictions, candidate_predictions], ignore_index=True).to_parquet(predictions_path, index=False)
    paired_frame.insert(0, "candidate", V3_D_CANDIDATE)
    paired_frame.to_csv(paired_path, index=False)
    diagnostic_summary.to_csv(diagnostics_path, index=False)
    diagnostic_sectors.to_csv(sector_metrics_path, index=False)

    aggregate = {
        V3_D_CONTROL: control_aggregate,
        V3_D_CANDIDATE: sector_aggregate,
        "paired": paired_aggregate,
        "candidate_absolute_sanity_pass": bool(absolute_pass),
        "candidate_paired_promotion_pass": bool(paired_pass),
    }
    aggregate_path = output_dir / "ranking_v3_d_sector_relative_aggregate.json"
    aggregate_path.write_text(json.dumps(aggregate, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    verdict = {
        "status": decision,
        "control_verdict": "CONTROL_REFERENCE",
        "sector_candidate_verdict": candidate_verdict,
        "selected_component": V3_D_CANDIDATE if candidate_verdict == "PROMOTE_FOR_NEXT_RESEARCH_STEP" else None,
        "authorization_status": authorization.get("status"),
        "v2f5_v2f6_accessed": False,
        "fresh_forward_accessed": False,
    }
    verdict_path = output_dir / "ranking_v3_d_sector_relative_verdict.json"
    verdict_path.write_text(json.dumps(verdict, indent=2, ensure_ascii=False), encoding="utf-8")

    ledger_rows = [
        {
            "hypothesis_id": V3_D_HYPOTHESIS_ID,
            "candidate_id": V3_D_CONTROL,
            "candidate_ordinal": 8,
            "result_status": "COMPLETE",
            "result_viewed": True,
            "verdict": "CONTROL_REFERENCE",
        },
        {
            "hypothesis_id": V3_D_HYPOTHESIS_ID,
            "candidate_id": V3_D_CANDIDATE,
            "candidate_ordinal": 9,
            "result_status": "COMPLETE",
            "result_viewed": True,
            "verdict": candidate_verdict,
        },
    ]
    ledger_path = output_dir / "ranking_v3_d_sector_relative_ledger_rows.json"
    ledger_path.write_text(json.dumps(ledger_rows, indent=2, ensure_ascii=False), encoding="utf-8")

    runtime = {
        "mode": "sequential_reference",
        "control_seconds": control_seconds,
        "sector_candidate_seconds": candidate_seconds,
        "total_seconds": time.perf_counter() - started,
        "python": sys.version,
        "platform": platform.platform(),
        "environment": environment,
    }
    runtime_path = output_dir / "ranking_v3_d_sector_relative_runtime.json"
    runtime_path.write_text(json.dumps(runtime, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    model_hashes = {**control_models, **candidate_models}
    artifact_paths = [
        equivalence_path,
        metrics_path,
        predictions_path,
        paired_path,
        diagnostics_path,
        sector_metrics_path,
        aggregate_path,
        verdict_path,
        ledger_path,
        runtime_path,
    ]
    artifacts = {path.name: sha256_file(path) for path in artifact_paths}
    artifacts.update(model_hashes)
    summary = {
        "status": decision,
        "code_commit": code_commit,
        "hypothesis_id": V3_D_HYPOTHESIS_ID,
        "candidates": list(V3_D_CANDIDATES),
        "folds": [fold.name for fold in DISCOVERY_FOLDS],
        "cache_sha256": sha256_file(cache_path),
        "cache_manifest_sha256": sha256_file(cache_manifest_path),
        "spec_sha256": sha256_file(spec_path),
        "authorization_sha256": sha256_file(authorization_path),
        "control_equivalence_status": equivalence["status"],
        "candidate_feature_columns": list(V3_D_FEATURE_COLUMNS),
        "candidate_feature_order_sha256": _feature_order_hash(tuple(V3_D_FEATURE_COLUMNS)),
        "candidate_verdict": candidate_verdict,
        "cache_coverage": cache_manifest.get("coverage", {}),
        "artifact_sha256": artifacts,
        "independent_validation_claim": False,
        "probability_claim": False,
        "v2f5_v2f6_accessed": False,
        "fresh_forward_accessed": False,
    }
    summary_path = output_dir / "ranking_v3_d_sector_relative_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    summary["summary_sha256"] = sha256_file(summary_path)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate, prepare, or run provisional Ranking V3-D sector research")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate-history", help="validate PIT sector-history provenance without outcomes")
    validate.add_argument("--sector-history", type=Path, required=True)
    validate.add_argument("--security-master", type=Path, required=True)
    validate.add_argument("--output-dir", type=Path, required=True)

    prepare = sub.add_parser("prepare", help="build outcome-independent F1-F4-only sector cache")
    prepare.add_argument("--panel", type=Path, required=True)
    prepare.add_argument("--calendar", type=Path, required=True)
    prepare.add_argument("--security-master", type=Path, required=True)
    prepare.add_argument("--v2-prepared", type=Path, required=True)
    prepare.add_argument("--v2-manifest", type=Path, required=True)
    prepare.add_argument("--sector-history", type=Path, required=True)
    prepare.add_argument("--spec", type=Path, required=True)
    prepare.add_argument("--output-dir", type=Path, required=True)
    prepare.add_argument("--code-commit", required=True)

    run = sub.add_parser("run", help="run V3-D only with a separately frozen authorization JSON")
    run.add_argument("--cache", type=Path, required=True)
    run.add_argument("--cache-manifest", type=Path, required=True)
    run.add_argument("--reference-v2-dir", type=Path, required=True)
    run.add_argument("--spec", type=Path, required=True)
    run.add_argument("--authorization", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--code-commit", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "validate-history":
        result = validate_sector_history_artifact(
            sector_history_path=args.sector_history,
            security_master_path=args.security_master,
            output_dir=args.output_dir,
        )
    elif args.command == "prepare":
        result = prepare_sector_cache(
            panel_path=args.panel,
            calendar_path=args.calendar,
            security_master_path=args.security_master,
            v2_prepared_path=args.v2_prepared,
            v2_manifest_path=args.v2_manifest,
            sector_history_path=args.sector_history,
            spec_path=args.spec,
            output_dir=args.output_dir,
            code_commit=args.code_commit,
        )
    else:
        result = run_sector_discovery(
            cache_path=args.cache,
            cache_manifest_path=args.cache_manifest,
            reference_v2_dir=args.reference_v2_dir,
            spec_path=args.spec,
            authorization_path=args.authorization,
            output_dir=args.output_dir,
            code_commit=args.code_commit,
        )
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
