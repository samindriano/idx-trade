"""Frozen historical O2-vs-V2 common-support comparator.

This module intentionally consumes already-certified local artifacts.  It does
not fetch data, access forward outcomes, alter canonical models, or write
runtime artifacts into the repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from .ohlcv_o1_research import (
    EXPECTED_ACCEPTED_OPEN_PANEL_SHA256,
    EXPECTED_ACCEPTED_OPEN_PROVENANCE_SHA256,
    EXPECTED_CALENDAR_SHA256,
    EXPECTED_COMMON_SUPPORT_ROWS,
    EXPECTED_PANEL_SHA256,
    EXPECTED_SECURITY_MASTER_SHA256,
    EXPECTED_TRAINING_MANIFEST_SHA256,
    EXPECTED_TRAINING_TABLE_SHA256,
    EXPECTED_V3_B_FEATURE_ORDER_SHA256,
    HGB_PARAMS,
    RANKING_V2_FOLDS,
    V3_B_FEATURE_COLUMNS,
    _aggregate_metrics,
    _normal_date,
    _stable_key_hash,
    _verify_file,
    evaluate_scores,
    feature_order_hash,
    load_common_support,
    raw_score,
    sha256_file,
    verify_fold_contract,
)
from .ohlcv_o2_geometry_research import _attach_geometry
from .research_features import assert_no_open_dependency


V2_MODEL = "V2_HGB_XS_MARKET_COMMON_SUPPORT"
O2_MODEL = "O2_FULL_3_COMMON_SUPPORT"
MODEL_ORDER = (V2_MODEL, O2_MODEL)
V2_FEATURE_COLUMNS = V3_B_FEATURE_COLUMNS[:25]
O2_GEOMETRY_FEATURES = ("open_position", "open_to_high", "open_to_low")
O2_FEATURE_COLUMNS = (*V3_B_FEATURE_COLUMNS, *O2_GEOMETRY_FEATURES)

EXPECTED_V2_FEATURE_ORDER_SHA256 = "1107bf6a65d0b2c86128de7c1123c876ffc9c5e19471b6f32852727f8c5b9a72"
EXPECTED_O2_FEATURE_ORDER_SHA256 = "a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f"
EXPECTED_COMMON_SUPPORT_KEY_SHA256 = "716bed364b5ba0dcb034f335bc7b09b4abac23eb1236a7c718fe6e0f6a78577a"
EXPECTED_V2_CANDIDATE_SUMMARY_SHA256 = "24cd9c6d1a978b35126955802fcf4852e1f3d50a489540b761052a9221a5327d"
EXPECTED_V2_FINAL_MANIFEST_SHA256 = "f483450026a9550f31b7d5873825079a2e307c1b24db87ce06dc500d17c3ace9"
EXPECTED_V2_FINAL_MODEL_SHA256 = "5c9e3d0207baa27310937ff97c92e7561e8e1134152ae011668ad97515cb9ace"
EXPECTED_V2_PREPARED_CACHE_MANIFEST_SHA256 = "6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143"
EXPECTED_V2_PREPARED_CACHE_SHA256 = "522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5"
EXPECTED_O2_MINIMALITY_MANIFEST_SHA256 = "919e35bb8d2fe68588db331e3de25f6c2a490c2727aea9f68e1179c0bcbe5183"
EXPECTED_O2_GEOMETRY_MANIFEST_SHA256 = "cc26bc689dd37bc83cc2c32d348d3201e5c4f41577f4bb8f938ab5cac2c7a97a"


def comparator_hgb_pipeline(feature_columns: Sequence[str]) -> Pipeline:
    """Build the one frozen preprocessing/HGB contract for either model."""

    columns = tuple(feature_columns)
    if columns not in (V2_FEATURE_COLUMNS, O2_FEATURE_COLUMNS):
        raise ValueError("comparator received an unfrozen feature order")
    assert_no_open_dependency(V2_FEATURE_COLUMNS)
    if columns == O2_FEATURE_COLUMNS and O2_FEATURE_COLUMNS[: len(V3_B_FEATURE_COLUMNS)] != V3_B_FEATURE_COLUMNS:
        raise ValueError("O2 feature order does not preserve canonical V3-B prefix")
    numeric = Pipeline(
        [
            (
                "impute",
                SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
            )
        ]
    )
    preprocess = ColumnTransformer([("numeric", numeric, list(columns))], remainder="drop")
    return Pipeline(
        [
            ("preprocess", preprocess),
            ("model", HistGradientBoostingClassifier(**HGB_PARAMS)),
        ]
    )


def comparator_verdict(
    paired: pd.DataFrame,
    aggregate: pd.DataFrame,
) -> tuple[str, dict[str, object]]:
    """Apply only the frozen O2-vs-V2 common-support verdict rule."""

    deltas = paired.loc[paired["level"].eq("fold"), "pr_auc_delta_o2_minus_v2"].to_numpy(dtype=float)
    if len(deltas) != 6:
        raise ValueError("verdict requires six paired fold deltas")
    v2 = aggregate.loc[aggregate["model"].eq(V2_MODEL)].iloc[0]
    o2 = aggregate.loc[aggregate["model"].eq(O2_MODEL)].iloc[0]
    median_delta = float(np.median(deltas))
    lower_quartile_delta = float(np.quantile(deltas, 0.25))
    positive_folds = int(np.sum(deltas > 0.0))
    guardrail_reversal = bool(
        o2["median_roc_auc"] < v2["median_roc_auc"]
        and o2["median_q5_minus_q1"] < v2["median_q5_minus_q1"]
    )
    established = bool(
        median_delta > 0.0
        and lower_quartile_delta > 0.0
        and positive_folds >= 4
        and not guardrail_reversal
    )
    diagnostics = {
        "median_paired_pr_auc_delta": median_delta,
        "lower_quartile_paired_pr_auc_delta": lower_quartile_delta,
        "positive_paired_pr_auc_folds": positive_folds,
        "paired_fold_count": int(len(deltas)),
        "median_roc_auc_guardrail_reversal": guardrail_reversal,
        "median_v2_roc_auc": float(v2["median_roc_auc"]),
        "median_o2_roc_auc": float(o2["median_roc_auc"]),
        "median_v2_q5_minus_q1": float(v2["median_q5_minus_q1"]),
        "median_o2_q5_minus_q1": float(o2["median_q5_minus_q1"]),
        "frozen_rule_pass": established,
    }
    verdict = "O2_DIRECT_V2_COMMON_SUPPORT_BETTER" if established else "O2_DIRECT_V2_COMMON_SUPPORT_NOT_ESTABLISHED"
    return verdict, diagnostics


def _verify_json_file(path: Path, expected_sha: str, label: str) -> dict[str, object]:
    _verify_file(path, expected_sha, label)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} must contain a JSON object")
    return value


def _verify_o2_feature_hash() -> dict[str, object]:
    actual = feature_order_hash(O2_FEATURE_COLUMNS)
    if actual != EXPECTED_O2_FEATURE_ORDER_SHA256:
        raise RuntimeError(
            "accepted O2 feature-order hash mismatch: "
            f"expected {EXPECTED_O2_FEATURE_ORDER_SHA256}, got {actual}"
        )
    return {"expected": EXPECTED_O2_FEATURE_ORDER_SHA256, "actual": actual, "verified": True}


def _verify_manifest_artifacts(path: Path, manifest: dict[str, object], label: str) -> int:
    artifact_hashes = manifest.get("artifact_sha256")
    if not isinstance(artifact_hashes, dict) or not artifact_hashes:
        raise RuntimeError(f"{label} has no artifact hashes")
    for name, expected in sorted(artifact_hashes.items()):
        _verify_file(path.parent / str(name), str(expected), f"{label} artifact {name}")
    return int(len(artifact_hashes))


def _validate_o2_parent_manifest(manifest: dict[str, object], *, parent_kind: str) -> dict[str, object]:
    contract = manifest.get("preflight_contract", {})
    if not isinstance(contract, dict):
        raise RuntimeError(f"O2 {parent_kind} parent has no preflight contract")
    if contract.get("common_support_rows") != EXPECTED_COMMON_SUPPORT_ROWS:
        raise RuntimeError(f"O2 {parent_kind} parent common-support row count mismatch")
    if contract.get("common_support_tickers") != 729:
        raise RuntimeError(f"O2 {parent_kind} parent common-support ticker count mismatch")
    if contract.get("common_support_key_sha256") != EXPECTED_COMMON_SUPPORT_KEY_SHA256:
        raise RuntimeError(f"O2 {parent_kind} parent common-support identity mismatch")
    if contract.get("o2_feature_order_sha256") != EXPECTED_O2_FEATURE_ORDER_SHA256:
        raise RuntimeError(f"O2 {parent_kind} parent feature-order hash mismatch")
    if contract.get("fresh_forward_outcomes_accessed") is not False or (
        "provider_calls" in contract and contract.get("provider_calls") is not False
    ):
        raise RuntimeError(f"O2 {parent_kind} parent is not historical/provider-free")
    if parent_kind == "minimality":
        if manifest.get("schema") != "idx-trade/ohlcv-o2-minimality-artifacts-v1":
            raise RuntimeError("O2 minimality parent schema mismatch")
        if manifest.get("status") != "O2_MINIMALITY_EVIDENCE_COMPLETE":
            raise RuntimeError("O2 minimality parent status mismatch")
        if "O2_FULL_3" not in contract.get("minimality_models", []):
            raise RuntimeError("O2 minimality parent does not contain O2_FULL_3")
        feature_hashes = contract.get("feature_order_sha256", {})
        if not isinstance(feature_hashes, dict) or feature_hashes.get("O2_FULL_3") != EXPECTED_O2_FEATURE_ORDER_SHA256:
            raise RuntimeError("O2 minimality parent O2_FULL_3 feature identity mismatch")
    elif parent_kind == "geometry":
        if manifest.get("schema") != "idx-trade/ohlcv-o2-geometry-research-artifacts-v1":
            raise RuntimeError("O2 geometry parent schema mismatch")
        if manifest.get("status") != "O2_SURVIVOR":
            raise RuntimeError("O2 geometry parent status mismatch")
        if contract.get("o2_model") != "O2_OPEN_GEOMETRY":
            raise RuntimeError("O2 geometry parent model identity mismatch")
    else:
        raise ValueError(f"unknown O2 parent kind: {parent_kind}")
    return {
        "kind": parent_kind,
        "schema": str(manifest["schema"]),
        "status": str(manifest["status"]),
        "common_support_rows": int(contract["common_support_rows"]),
        "common_support_tickers": int(contract["common_support_tickers"]),
        "common_support_key_sha256": str(contract["common_support_key_sha256"]),
        "o2_feature_order_sha256": str(contract["o2_feature_order_sha256"]),
    }


def _verify_accepted_o2_parent_artifacts(
    *,
    minimality_manifest_path: Path,
    geometry_manifest_path: Path,
) -> dict[str, object]:
    feature_hash = _verify_o2_feature_hash()
    parents: list[dict[str, object]] = []
    for kind, path, expected in (
        ("minimality", minimality_manifest_path, EXPECTED_O2_MINIMALITY_MANIFEST_SHA256),
        ("geometry", geometry_manifest_path, EXPECTED_O2_GEOMETRY_MANIFEST_SHA256),
    ):
        manifest = _verify_json_file(path, expected, f"accepted O2 {kind} parent manifest")
        artifact_count = _verify_manifest_artifacts(path, manifest, f"accepted O2 {kind} parent")
        record = _validate_o2_parent_manifest(manifest, parent_kind=kind)
        record.update({"path": str(path), "manifest_sha256": expected, "artifact_count": artifact_count})
        parents.append(record)
    return {"feature_hash": feature_hash, "parents": parents}


def _verify_v2_frozen_artifacts(
    *,
    candidate_summary_path: Path,
    final_manifest_path: Path,
    final_model_path: Path,
    prepared_cache_manifest_path: Path,
    prepared_cache_path: Path,
) -> dict[str, object]:
    candidate = _verify_json_file(candidate_summary_path, EXPECTED_V2_CANDIDATE_SUMMARY_SHA256, "V2 candidate summary")
    final_manifest = _verify_json_file(final_manifest_path, EXPECTED_V2_FINAL_MANIFEST_SHA256, "V2 final manifest")
    prepared_manifest = _verify_json_file(
        prepared_cache_manifest_path,
        EXPECTED_V2_PREPARED_CACHE_MANIFEST_SHA256,
        "V2 prepared-cache manifest",
    )
    model_sha = _verify_file(final_model_path, EXPECTED_V2_FINAL_MODEL_SHA256, "V2 final model")
    cache_sha = _verify_file(prepared_cache_path, EXPECTED_V2_PREPARED_CACHE_SHA256, "V2 prepared cache")

    expected_folds = [asdict(fold) for fold in RANKING_V2_FOLDS]
    for label, value in (
        ("candidate", candidate),
        ("final manifest", final_manifest),
    ):
        columns = tuple(value.get("feature_columns", ()))
        if columns != V2_FEATURE_COLUMNS:
            raise RuntimeError(f"{label} V2 feature order mismatch")
        if label == "candidate" and value.get("fresh_forward_outcomes_accessed") is None:
            pass
        elif value.get("fresh_forward_outcomes_accessed") is not False:
            raise RuntimeError(f"{label} permits fresh-forward access")
    if candidate.get("candidate") != "HGB_XS_MARKET" or candidate.get("status") != "RANKING_V2_CANDIDATE_COMPLETE":
        raise RuntimeError("V2 candidate identity/status mismatch")
    if candidate.get("independent_validation_claim") is not False:
        raise RuntimeError("V2 candidate is not marked development-only")
    if candidate.get("folds") != expected_folds:
        raise RuntimeError("V2 candidate fold contract mismatch")
    if final_manifest.get("status") != "RANKING_V2_FINAL_REFIT_FROZEN":
        raise RuntimeError("V2 final manifest status mismatch")
    if final_manifest.get("model_sha256") != EXPECTED_V2_FINAL_MODEL_SHA256:
        raise RuntimeError("V2 final model hash in manifest mismatch")
    if final_manifest.get("rows") != 292633 or final_manifest.get("tickers") != 737:
        raise RuntimeError("V2 final manifest population mismatch")
    model_config = final_manifest.get("model_config", {})
    preprocessing = model_config.get("preprocessing", {}) if isinstance(model_config, dict) else {}
    estimator = model_config.get("estimator", {}) if isinstance(model_config, dict) else {}
    if tuple(preprocessing.get("selected_columns", ())) != V2_FEATURE_COLUMNS:
        raise RuntimeError("V2 final preprocessing columns mismatch")
    if preprocessing.get("remainder") != "drop" or preprocessing.get("scaler") is not None:
        raise RuntimeError("V2 final preprocessing contract mismatch")
    if preprocessing.get("imputer") != {"add_indicator": True, "keep_empty_features": True, "strategy": "median"}:
        raise RuntimeError("V2 final imputer contract mismatch")
    if estimator != {
        "class": "HistGradientBoostingClassifier",
        "l2_regularization": 1.0,
        "learning_rate": 0.05,
        "max_iter": 200,
        "max_leaf_nodes": 31,
        "random_state": 42,
    }:
        raise RuntimeError("V2 final HGB parameter contract mismatch")
    if tuple(prepared_manifest.get("v2_feature_columns", ())) != V2_FEATURE_COLUMNS:
        raise RuntimeError("V2 prepared-cache feature order mismatch")
    if prepared_manifest.get("cache_sha256") != EXPECTED_V2_PREPARED_CACHE_SHA256:
        raise RuntimeError("V2 prepared-cache hash in manifest mismatch")
    if prepared_manifest.get("rows") != 292633 or prepared_manifest.get("tickers") != 737:
        raise RuntimeError("V2 prepared-cache population mismatch")
    return {
        "candidate_summary_path": str(candidate_summary_path),
        "candidate_summary_sha256": EXPECTED_V2_CANDIDATE_SUMMARY_SHA256,
        "final_manifest_path": str(final_manifest_path),
        "final_manifest_sha256": EXPECTED_V2_FINAL_MANIFEST_SHA256,
        "final_model_path": str(final_model_path),
        "final_model_sha256": model_sha,
        "prepared_cache_manifest_path": str(prepared_cache_manifest_path),
        "prepared_cache_manifest_sha256": EXPECTED_V2_PREPARED_CACHE_MANIFEST_SHA256,
        "prepared_cache_path": str(prepared_cache_path),
        "prepared_cache_sha256": cache_sha,
        "feature_order_sha256": feature_order_hash(V2_FEATURE_COLUMNS),
        "rows": 292633,
        "tickers": 737,
        "folds": expected_folds,
        "h10": {"horizon": 10, "positive_label": "TP_FIRST", "negative_label": "SL_FIRST", "target_mapping": {"TP_FIRST": 1, "SL_FIRST": 0}},
        "hgb_parameters": HGB_PARAMS,
        "fresh_forward_outcomes_accessed": False,
    }


def _paired_comparisons(metrics: pd.DataFrame, aggregate: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for fold in [f.name for f in RANKING_V2_FOLDS]:
        v2 = metrics.loc[(metrics["model"] == V2_MODEL) & (metrics["fold"] == fold)].iloc[0]
        o2 = metrics.loc[(metrics["model"] == O2_MODEL) & (metrics["fold"] == fold)].iloc[0]
        rows.append(
            {
                "level": "fold",
                "fold": fold,
                "v2_model": V2_MODEL,
                "o2_model": O2_MODEL,
                "v2_pr_auc": float(v2["pr_auc"]),
                "o2_pr_auc": float(o2["pr_auc"]),
                "pr_auc_delta_o2_minus_v2": float(o2["pr_auc"] - v2["pr_auc"]),
                "v2_pr_auc_minus_prevalence": float(v2["pr_auc_minus_prevalence"]),
                "o2_pr_auc_minus_prevalence": float(o2["pr_auc_minus_prevalence"]),
                "pr_auc_minus_prevalence_delta_o2_minus_v2": float(o2["pr_auc_minus_prevalence"] - v2["pr_auc_minus_prevalence"]),
                "v2_roc_auc": float(v2["roc_auc"]),
                "o2_roc_auc": float(o2["roc_auc"]),
                "roc_auc_delta_o2_minus_v2": float(o2["roc_auc"] - v2["roc_auc"]),
                "v2_q5_minus_q1": float(v2["q5_minus_q1"]),
                "o2_q5_minus_q1": float(o2["q5_minus_q1"]),
                "q5_minus_q1_delta_o2_minus_v2": float(o2["q5_minus_q1"] - v2["q5_minus_q1"]),
                "v2_top_decile_lift": float(v2["top_decile_lift"]),
                "o2_top_decile_lift": float(o2["top_decile_lift"]),
                "top_decile_lift_delta_o2_minus_v2": float(o2["top_decile_lift"] - v2["top_decile_lift"]),
            }
        )
    v2 = aggregate.loc[aggregate["model"] == V2_MODEL].iloc[0]
    o2 = aggregate.loc[aggregate["model"] == O2_MODEL].iloc[0]
    rows.append(
        {
            "level": "aggregate_mean",
            "fold": "ALL",
            "v2_model": V2_MODEL,
            "o2_model": O2_MODEL,
            "v2_pr_auc": float(v2["mean_pr_auc"]),
            "o2_pr_auc": float(o2["mean_pr_auc"]),
            "pr_auc_delta_o2_minus_v2": float(o2["mean_pr_auc"] - v2["mean_pr_auc"]),
            "v2_pr_auc_minus_prevalence": float(v2["mean_pr_auc_minus_prevalence"]),
            "o2_pr_auc_minus_prevalence": float(o2["mean_pr_auc_minus_prevalence"]),
            "pr_auc_minus_prevalence_delta_o2_minus_v2": float(o2["mean_pr_auc_minus_prevalence"] - v2["mean_pr_auc_minus_prevalence"]),
            "v2_roc_auc": float(v2["mean_roc_auc"]),
            "o2_roc_auc": float(o2["mean_roc_auc"]),
            "roc_auc_delta_o2_minus_v2": float(o2["mean_roc_auc"] - v2["mean_roc_auc"]),
            "v2_q5_minus_q1": float(v2["mean_q5_minus_q1"]),
            "o2_q5_minus_q1": float(o2["mean_q5_minus_q1"]),
            "q5_minus_q1_delta_o2_minus_v2": float(o2["mean_q5_minus_q1"] - v2["mean_q5_minus_q1"]),
            "v2_top_decile_lift": float(v2["mean_top_decile_lift"]),
            "o2_top_decile_lift": float(o2["mean_top_decile_lift"]),
            "top_decile_lift_delta_o2_minus_v2": float(o2["mean_top_decile_lift"] - v2["mean_top_decile_lift"]),
        }
    )
    rows.append(
        {
            **rows[-1],
            "level": "aggregate_median",
            "v2_pr_auc": float(v2["median_pr_auc"]),
            "o2_pr_auc": float(o2["median_pr_auc"]),
            "pr_auc_delta_o2_minus_v2": float(o2["median_pr_auc"] - v2["median_pr_auc"]),
            "v2_pr_auc_minus_prevalence": float(v2["median_pr_auc_minus_prevalence"]),
            "o2_pr_auc_minus_prevalence": float(o2["median_pr_auc_minus_prevalence"]),
            "pr_auc_minus_prevalence_delta_o2_minus_v2": float(o2["median_pr_auc_minus_prevalence"] - v2["median_pr_auc_minus_prevalence"]),
            "v2_roc_auc": float(v2["median_roc_auc"]),
            "o2_roc_auc": float(o2["median_roc_auc"]),
            "roc_auc_delta_o2_minus_v2": float(o2["median_roc_auc"] - v2["median_roc_auc"]),
            "v2_q5_minus_q1": float(v2["median_q5_minus_q1"]),
            "o2_q5_minus_q1": float(o2["median_q5_minus_q1"]),
            "q5_minus_q1_delta_o2_minus_v2": float(o2["median_q5_minus_q1"] - v2["median_q5_minus_q1"]),
            "v2_top_decile_lift": float(v2["median_top_decile_lift"]),
            "o2_top_decile_lift": float(o2["median_top_decile_lift"]),
            "top_decile_lift_delta_o2_minus_v2": float(o2["median_top_decile_lift"] - v2["median_top_decile_lift"]),
        }
    )
    return pd.DataFrame(rows)


def _write_manifest(output_dir: Path, payload: dict[str, object]) -> tuple[Path, str, int]:
    artifact_hashes = {
        path.name: sha256_file(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "artifact_manifest.json"
    }
    manifest = {
        "schema": "idx-trade/o2-v2-common-support-comparator-artifacts-v1",
        "status": payload["verdict"],
        "artifact_sha256": artifact_hashes,
        "contract": payload["contract"],
        "summary": payload["summary"],
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "packages": {"numpy": np.__version__, "pandas": pd.__version__},
        },
    }
    path = output_dir / "artifact_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return path, sha256_file(path), len(artifact_hashes)


def run_comparator(
    *,
    coverage_path: Path,
    training_table_path: Path,
    training_manifest_path: Path,
    v2_candidate_summary_path: Path,
    v2_final_manifest_path: Path,
    v2_final_model_path: Path,
    v2_prepared_cache_manifest_path: Path,
    v2_prepared_cache_path: Path,
    o2_minimality_manifest_path: Path,
    o2_geometry_manifest_path: Path,
    output_dir: Path,
    immutable_panel_path: Path,
    calendar_path: Path,
    security_master_path: Path,
    accepted_open_panel_path: Path,
    accepted_open_provenance_path: Path,
) -> dict[str, object]:
    if output_dir.exists():
        raise RuntimeError(f"refusing to overwrite existing comparator runtime: {output_dir}")
    o2_parent_contract = _verify_accepted_o2_parent_artifacts(
        minimality_manifest_path=o2_minimality_manifest_path,
        geometry_manifest_path=o2_geometry_manifest_path,
    )
    output_dir.mkdir(parents=True)
    contract: dict[str, object] = {
        "models": list(MODEL_ORDER),
        "provider_calls": False,
        "fresh_forward_outcomes_accessed": False,
        "canonical_model_overwrite": False,
        "v2_feature_columns": list(V2_FEATURE_COLUMNS),
        "v2_feature_order_sha256": feature_order_hash(V2_FEATURE_COLUMNS),
        "o2_feature_columns": list(O2_FEATURE_COLUMNS),
        "o2_feature_order_sha256": feature_order_hash(O2_FEATURE_COLUMNS),
        "o2_feature_hash_preflight": o2_parent_contract["feature_hash"],
        "v3_b_feature_order_sha256": EXPECTED_V3_B_FEATURE_ORDER_SHA256,
        "hgb_parameters": HGB_PARAMS,
        "folds": verify_fold_contract(),
        "h10": {"horizon": 10, "positive_label": "TP_FIRST", "negative_label": "SL_FIRST", "target_mapping": {"TP_FIRST": 1, "SL_FIRST": 0}},
    }
    for label, path, expected in (
        ("immutable_panel", immutable_panel_path, EXPECTED_PANEL_SHA256),
        ("official_calendar", calendar_path, EXPECTED_CALENDAR_SHA256),
        ("security_master", security_master_path, EXPECTED_SECURITY_MASTER_SHA256),
        ("accepted_open_panel", accepted_open_panel_path, EXPECTED_ACCEPTED_OPEN_PANEL_SHA256),
        ("accepted_open_provenance", accepted_open_provenance_path, EXPECTED_ACCEPTED_OPEN_PROVENANCE_SHA256),
    ):
        contract[f"{label}_path"] = str(path)
        contract[f"{label}_sha256"] = _verify_file(path, expected, label)
    contract["v2_frozen_artifacts"] = _verify_v2_frozen_artifacts(
        candidate_summary_path=v2_candidate_summary_path,
        final_manifest_path=v2_final_manifest_path,
        final_model_path=v2_final_model_path,
        prepared_cache_manifest_path=v2_prepared_cache_manifest_path,
        prepared_cache_path=v2_prepared_cache_path,
    )
    contract["accepted_o2_parent_artifacts"] = o2_parent_contract["parents"]
    support, support_contract = load_common_support(
        coverage_path=coverage_path,
        training_table_path=training_table_path,
        training_manifest_path=training_manifest_path,
    )
    if support_contract["common_support_key_sha256"] != EXPECTED_COMMON_SUPPORT_KEY_SHA256:
        raise RuntimeError("common-support identity hash differs from the frozen accepted population")
    support, formula_errors = _attach_geometry(support, coverage_path)
    if len(support) != EXPECTED_COMMON_SUPPORT_ROWS or support["ticker"].nunique() != 729 or _stable_key_hash(support) != EXPECTED_COMMON_SUPPORT_KEY_SHA256:
        raise RuntimeError("comparator population is not the exact 278,168-row/729-ticker support set")
    contract.update(support_contract)
    contract["geometry_formula_max_abs_error"] = formula_errors
    contract["common_support_rows"] = int(len(support))
    contract["common_support_tickers"] = int(support["ticker"].nunique())
    support_rows = support[["ticker", "date", "signal_session_index"]].copy()
    support_rows["date"] = _normal_date(support_rows["date"]).dt.strftime("%Y-%m-%d")
    support_rows.sort_values(["ticker", "date"], kind="mergesort").to_csv(output_dir / "common_support_rows.csv", index=False)
    (output_dir / "preflight_contract.json").write_text(json.dumps(contract, indent=2, sort_keys=True, default=str), encoding="utf-8")
    (output_dir / "fold_definitions.json").write_text(json.dumps(contract["folds"], indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "feature_manifest.json").write_text(
        json.dumps(
            {
                "models": {V2_MODEL: list(V2_FEATURE_COLUMNS), O2_MODEL: list(O2_FEATURE_COLUMNS)},
                "feature_order_sha256": {V2_MODEL: feature_order_hash(V2_FEATURE_COLUMNS), O2_MODEL: feature_order_hash(O2_FEATURE_COLUMNS)},
                "hgb_parameters": HGB_PARAMS,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    metric_rows: list[dict[str, object]] = []
    prediction_frames: list[pd.DataFrame] = []
    identity_rows: list[dict[str, object]] = []
    runtime_start = time.perf_counter()
    for fold in RANKING_V2_FOLDS:
        train = support[support["signal_session_index"].between(fold.train_start, fold.train_end)].copy()
        validation = support[support["signal_session_index"].between(fold.validation_start, fold.validation_end)].copy()
        if train.empty or validation.empty or train["binary_target"].nunique() != 2 or validation["binary_target"].nunique() != 2:
            raise RuntimeError(f"{fold.name} does not have a valid common-support train/validation set")
        train_hash = _stable_key_hash(train)
        validation_hash = _stable_key_hash(validation)
        identity_rows.append(
            {
                "fold": fold.name,
                "train_rows": int(len(train)),
                "validation_rows": int(len(validation)),
                "train_identity_sha256": train_hash,
                "validation_identity_sha256": validation_hash,
                "identical_train_validation_identities": True,
            }
        )
        for model_name, columns in ((V2_MODEL, V2_FEATURE_COLUMNS), (O2_MODEL, O2_FEATURE_COLUMNS)):
            model_start = time.perf_counter()
            model = comparator_hgb_pipeline(columns)
            model.fit(train[list(columns)], train["binary_target"].astype(int).to_numpy())
            scores = raw_score(model, validation[list(columns)])
            if not np.isfinite(scores).all():
                raise RuntimeError(f"{model_name} {fold.name} produced non-finite scores")
            evaluated = evaluate_scores(validation, scores)
            metric_rows.append(
                {
                    "model": model_name,
                    "fold": fold.name,
                    **asdict(fold),
                    "train_rows": int(len(train)),
                    "validation_rows": int(len(validation)),
                    "train_identity_sha256": train_hash,
                    "validation_identity_sha256": validation_hash,
                    "feature_count": int(len(columns)),
                    "feature_order_sha256": feature_order_hash(columns),
                    "training_runtime_seconds": float(time.perf_counter() - model_start),
                    **evaluated,
                }
            )
            prediction_frames.append(
                pd.DataFrame(
                    {
                        "model": model_name,
                        "fold": fold.name,
                        "ticker": validation["ticker"].to_numpy(),
                        "date": validation["date"].to_numpy(),
                        "signal_session_index": validation["signal_session_index"].to_numpy(),
                        "binary_target": validation["binary_target"].astype(int).to_numpy(),
                        "score": scores,
                    }
                )
            )
    metrics = pd.DataFrame(metric_rows)
    aggregate = _aggregate_metrics(metrics)
    median_top_decile = metrics.groupby("model", sort=True)["top_decile_lift"].median()
    aggregate["median_top_decile_lift"] = aggregate["model"].map(median_top_decile).astype(float)
    paired = _paired_comparisons(metrics, aggregate)
    verdict, verdict_diagnostics = comparator_verdict(paired, aggregate)
    predictions = pd.concat(prediction_frames, ignore_index=True)
    predictions["year"] = pd.to_datetime(predictions["date"]).dt.year.astype(int)
    identity = pd.DataFrame(identity_rows)
    metrics.to_csv(output_dir / "fold_metrics.csv", index=False)
    aggregate.to_csv(output_dir / "aggregate_metrics.csv", index=False)
    paired.to_csv(output_dir / "paired_comparisons.csv", index=False)
    identity.to_csv(output_dir / "fold_row_identity_checks.csv", index=False)
    predictions.to_parquet(output_dir / "fold_predictions.parquet", index=False)
    summary = {
        "verdict": verdict,
        "models": list(MODEL_ORDER),
        "common_support_rows": int(len(support)),
        "common_support_tickers": int(support["ticker"].nunique()),
        "common_support_key_sha256": EXPECTED_COMMON_SUPPORT_KEY_SHA256,
        "fold_count": len(RANKING_V2_FOLDS),
        "fresh_forward_outcomes_accessed": False,
        "provider_calls": False,
        "training_runtime_seconds": float(time.perf_counter() - runtime_start),
        "verdict_diagnostics": verdict_diagnostics,
    }
    (output_dir / "experiment_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, default=str), encoding="utf-8")
    manifest_path, manifest_sha, artifact_count = _write_manifest(output_dir, {"verdict": verdict, "contract": contract, "summary": summary})
    return {
        **summary,
        "artifact_manifest_path": str(manifest_path),
        "artifact_manifest_sha256": manifest_sha,
        "artifact_count": artifact_count,
        "contract": contract,
        "aggregate": aggregate.to_dict(orient="records"),
        "paired": paired.to_dict(orient="records"),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    names = (
        "coverage_path", "training_table_path", "training_manifest_path", "v2_candidate_summary_path",
        "v2_final_manifest_path", "v2_final_model_path", "v2_prepared_cache_manifest_path",
        "v2_prepared_cache_path", "o2_minimality_manifest_path", "o2_geometry_manifest_path",
        "output_dir", "immutable_panel_path", "calendar_path",
        "security_master_path", "accepted_open_panel_path", "accepted_open_provenance_path",
    )
    for name in names:
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    result = run_comparator(**vars(args))
    print(json.dumps({k: result[k] for k in ("verdict", "common_support_rows", "common_support_tickers", "fold_count", "artifact_manifest_path", "artifact_manifest_sha256", "artifact_count")}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
