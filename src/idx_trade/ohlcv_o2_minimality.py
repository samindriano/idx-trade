"""Frozen eight-model minimality ablation for the accepted O2 geometry."""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from dataclasses import asdict
from pathlib import Path

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
    _era_metrics,
    _stable_key_hash,
    _verify_file,
    evaluate_scores,
    feature_order_hash,
    load_common_support,
    raw_score,
    verify_fold_contract,
)
from .ohlcv_o2_geometry_research import (
    BASELINE_MODEL,
    EXPECTED_COMMON_SUPPORT_KEY_SHA256,
    EXPECTED_O1_ARTIFACT_MANIFEST_SHA256,
    EXPECTED_O2_FEATURE_ORDER_SHA256,
    O2_FEATURE_COLUMNS,
    O2_GEOMETRY_FEATURES,
    _attach_geometry,
)
from .research_features import assert_no_open_dependency


O2_FULL_3 = "O2_FULL_3"
O2_SINGLE_POSITION = "O2_SINGLE_POSITION"
O2_SINGLE_TO_HIGH = "O2_SINGLE_TO_HIGH"
O2_SINGLE_TO_LOW = "O2_SINGLE_TO_LOW"
O2_PAIR_POSITION_HIGH = "O2_PAIR_POSITION_HIGH"
O2_PAIR_POSITION_LOW = "O2_PAIR_POSITION_LOW"
O2_PAIR_HIGH_LOW = "O2_PAIR_HIGH_LOW"

MODEL_ORDER = (
    BASELINE_MODEL,
    O2_FULL_3,
    O2_SINGLE_POSITION,
    O2_SINGLE_TO_HIGH,
    O2_SINGLE_TO_LOW,
    O2_PAIR_POSITION_HIGH,
    O2_PAIR_POSITION_LOW,
    O2_PAIR_HIGH_LOW,
)
REDUCED_MODELS = MODEL_ORDER[2:]
MODEL_FEATURES = {
    BASELINE_MODEL: V3_B_FEATURE_COLUMNS,
    O2_FULL_3: O2_FEATURE_COLUMNS,
    O2_SINGLE_POSITION: (*V3_B_FEATURE_COLUMNS, "open_position"),
    O2_SINGLE_TO_HIGH: (*V3_B_FEATURE_COLUMNS, "open_to_high"),
    O2_SINGLE_TO_LOW: (*V3_B_FEATURE_COLUMNS, "open_to_low"),
    O2_PAIR_POSITION_HIGH: (*V3_B_FEATURE_COLUMNS, "open_position", "open_to_high"),
    O2_PAIR_POSITION_LOW: (*V3_B_FEATURE_COLUMNS, "open_position", "open_to_low"),
    O2_PAIR_HIGH_LOW: (*V3_B_FEATURE_COLUMNS, "open_to_high", "open_to_low"),
}
EXPECTED_O2_ARTIFACT_MANIFEST_SHA256 = "cc26bc689dd37bc83cc2c32d348d3201e5c4f41577f4bb8f938ab5cac2c7a97a"
EXPECTED_STATUS = "O2_MINIMALITY_EVIDENCE_COMPLETE"


def minimality_hgb_pipeline(feature_columns: tuple[str, ...]) -> Pipeline:
    """Build the exact frozen HGB pipeline for one permitted representation."""

    if feature_columns not in tuple(MODEL_FEATURES.values()):
        raise ValueError("minimality runner received an unfrozen feature order")
    assert_no_open_dependency(V3_B_FEATURE_COLUMNS)
    numeric = Pipeline(
        [
            (
                "impute",
                SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
            )
        ]
    )
    preprocess = ColumnTransformer([("numeric", numeric, list(feature_columns))], remainder="drop")
    return Pipeline(
        [
            ("preprocess", preprocess),
            ("model", HistGradientBoostingClassifier(**HGB_PARAMS)),
        ]
    )


def _verify_accepted_o2_manifest(path: Path) -> dict[str, object]:
    manifest_sha = _verify_file(path, EXPECTED_O2_ARTIFACT_MANIFEST_SHA256, "accepted O2 artifact manifest")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "idx-trade/ohlcv-o2-geometry-research-artifacts-v1":
        raise RuntimeError("accepted O2 artifact manifest schema mismatch")
    if manifest.get("status") != "O2_SURVIVOR":
        raise RuntimeError("accepted O2 artifact manifest is not the accepted survivor runtime")
    contract = manifest.get("preflight_contract", {})
    if contract.get("common_support_rows") != EXPECTED_COMMON_SUPPORT_ROWS:
        raise RuntimeError("accepted O2 manifest common-support row count mismatch")
    if contract.get("common_support_key_sha256") != EXPECTED_COMMON_SUPPORT_KEY_SHA256:
        raise RuntimeError("accepted O2 manifest common-support key mismatch")
    if contract.get("o2_feature_order_sha256") != EXPECTED_O2_FEATURE_ORDER_SHA256:
        raise RuntimeError("accepted O2 feature-order hash mismatch")
    if contract.get("fresh_forward_outcomes_accessed") is not False:
        raise RuntimeError("accepted O2 manifest permits fresh-forward access")
    artifact_hashes = manifest.get("artifact_sha256", {})
    if not isinstance(artifact_hashes, dict) or not artifact_hashes:
        raise RuntimeError("accepted O2 manifest has no artifact hashes")
    for name, expected in sorted(artifact_hashes.items()):
        _verify_file(path.parent / str(name), str(expected), f"accepted O2 artifact {name}")
    return {
        "path": str(path),
        "sha256": manifest_sha,
        "artifact_count": int(len(artifact_hashes)),
        "artifact_hashes_verified": True,
        "status": str(manifest["status"]),
        "fold_metrics_path": str(path.parent / "fold_metrics.csv"),
        "aggregate_metrics_path": str(path.parent / "aggregate_metrics.csv"),
    }


def _metric_reproduction(
    current_metrics: pd.DataFrame,
    current_aggregate: pd.DataFrame,
    accepted_o2_dir: Path,
) -> dict[str, object]:
    """Prove that the rerun baseline/full-O2 metrics match accepted O2."""

    accepted_metrics = pd.read_csv(accepted_o2_dir / "fold_metrics.csv")
    accepted_aggregate = pd.read_csv(accepted_o2_dir / "aggregate_metrics.csv")
    models = [BASELINE_MODEL, O2_FULL_3]
    current = current_metrics[current_metrics["model"].isin(models)].copy()
    accepted = accepted_metrics[accepted_metrics["model"].isin([BASELINE_MODEL, "O2_OPEN_GEOMETRY"])].copy()
    accepted["model"] = accepted["model"].replace({"O2_OPEN_GEOMETRY": O2_FULL_3})
    joined = current.merge(accepted, on=["model", "fold"], suffixes=("_current", "_accepted"), how="outer", indicator=True)
    if len(joined) != 12 or not (joined["_merge"] == "both").all():
        raise RuntimeError("accepted O2 fold metric identities do not match the rerun")
    fold_numeric = ["pr_auc", "pr_auc_minus_prevalence", "roc_auc", "q5_minus_q1", "top_decile_lift", "train_rows", "validation_rows"]
    fold_diffs: dict[str, float] = {}
    for column in fold_numeric:
        left = pd.to_numeric(joined[f"{column}_current"], errors="raise").to_numpy(dtype=float)
        right = pd.to_numeric(joined[f"{column}_accepted"], errors="raise").to_numpy(dtype=float)
        if not np.allclose(left, right, rtol=0.0, atol=1e-12):
            raise RuntimeError(f"accepted O2 fold metric mismatch: {column}")
        fold_diffs[column] = float(np.max(np.abs(left - right)))
    for column in ("feature_order_sha256",):
        if not (joined[f"{column}_current"].astype(str).to_numpy() == joined[f"{column}_accepted"].astype(str).to_numpy()).all():
            raise RuntimeError(f"accepted O2 fold contract mismatch: {column}")

    accepted_aggregate = accepted_aggregate[accepted_aggregate["model"].isin([BASELINE_MODEL, "O2_OPEN_GEOMETRY"])].copy()
    accepted_aggregate["model"] = accepted_aggregate["model"].replace({"O2_OPEN_GEOMETRY": O2_FULL_3})
    aggregate_joined = current_aggregate[current_aggregate["model"].isin(models)].merge(
        accepted_aggregate,
        on="model",
        suffixes=("_current", "_accepted"),
        how="outer",
        indicator=True,
    )
    if len(aggregate_joined) != 2 or not (aggregate_joined["_merge"] == "both").all():
        raise RuntimeError("accepted O2 aggregate metric identities do not match the rerun")
    aggregate_numeric = [
        "mean_pr_auc",
        "median_pr_auc",
        "mean_pr_auc_minus_prevalence",
        "median_pr_auc_minus_prevalence",
        "mean_roc_auc",
        "median_roc_auc",
        "mean_q5_minus_q1",
        "median_q5_minus_q1",
        "mean_top_decile_lift",
    ]
    aggregate_diffs: dict[str, float] = {}
    for column in aggregate_numeric:
        left = pd.to_numeric(aggregate_joined[f"{column}_current"], errors="raise").to_numpy(dtype=float)
        right = pd.to_numeric(aggregate_joined[f"{column}_accepted"], errors="raise").to_numpy(dtype=float)
        if not np.allclose(left, right, rtol=0.0, atol=1e-12):
            raise RuntimeError(f"accepted O2 aggregate metric mismatch: {column}")
        aggregate_diffs[column] = float(np.max(np.abs(left - right)))
    return {
        "accepted_models": models,
        "fold_metric_rows_compared": int(len(joined)),
        "aggregate_rows_compared": int(len(aggregate_joined)),
        "fold_max_abs_diffs": fold_diffs,
        "aggregate_max_abs_diffs": aggregate_diffs,
        "within_tolerance": True,
    }


def _aggregate_minimality(metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for model_name in MODEL_ORDER:
        block = metrics[metrics["model"].eq(model_name)]
        base = block["paired_pr_auc_vs_baseline"].dropna().to_numpy(dtype=float)
        full = block["paired_pr_auc_vs_o2_full_3"].dropna().to_numpy(dtype=float)
        row: dict[str, object] = {
            "model": model_name,
            "folds": int(len(block)),
            "mean_pr_auc": float(block["pr_auc"].mean()),
            "median_pr_auc": float(block["pr_auc"].median()),
            "mean_pr_auc_minus_prevalence": float(block["pr_auc_minus_prevalence"].mean()),
            "median_pr_auc_minus_prevalence": float(block["pr_auc_minus_prevalence"].median()),
            "mean_roc_auc": float(block["roc_auc"].mean()),
            "median_roc_auc": float(block["roc_auc"].median()),
            "mean_q5_minus_q1": float(block["q5_minus_q1"].mean()),
            "median_q5_minus_q1": float(block["q5_minus_q1"].median()),
            "mean_top_decile_lift": float(block["top_decile_lift"].mean()),
            "median_top_decile_lift": float(block["top_decile_lift"].median()),
        }
        for label, values in (("vs_baseline", base), ("vs_o2_full_3", full)):
            if values.size:
                row[f"mean_paired_pr_auc_{label}"] = float(np.mean(values))
                row[f"median_paired_pr_auc_{label}"] = float(np.median(values))
                row[f"lower_quartile_paired_pr_auc_{label}"] = float(np.quantile(values, 0.25))
                row[f"min_paired_pr_auc_{label}"] = float(np.min(values))
                row[f"positive_folds_{label}"] = int(np.sum(values > 0.0))
            else:
                row[f"mean_paired_pr_auc_{label}"] = np.nan
                row[f"median_paired_pr_auc_{label}"] = np.nan
                row[f"lower_quartile_paired_pr_auc_{label}"] = np.nan
                row[f"min_paired_pr_auc_{label}"] = np.nan
                row[f"positive_folds_{label}"] = np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def _minimality_diagnostics(metrics: pd.DataFrame, aggregate: pd.DataFrame) -> pd.DataFrame:
    baseline = aggregate[aggregate["model"].eq(BASELINE_MODEL)].iloc[0]
    rows: list[dict[str, object]] = []
    for model_name in MODEL_ORDER[1:]:
        block = metrics[metrics["model"].eq(model_name)].sort_values("fold")
        deltas = block["paired_pr_auc_vs_baseline"].to_numpy(dtype=float)
        candidate = aggregate[aggregate["model"].eq(model_name)].iloc[0]
        median = float(np.median(deltas))
        q25 = float(np.quantile(deltas, 0.25))
        positive = int(np.sum(deltas > 0.0))
        guardrail_reversal = bool(
            candidate["median_roc_auc"] < baseline["median_roc_auc"]
            and candidate["median_q5_minus_q1"] < baseline["median_q5_minus_q1"]
        )
        rows.append(
            {
                "model": model_name,
                "median_paired_pr_auc_vs_baseline": median,
                "lower_quartile_paired_pr_auc_vs_baseline": q25,
                "min_paired_pr_auc_vs_baseline": float(np.min(deltas)),
                "positive_folds_vs_baseline": positive,
                "not_one_isolated_fold_spike": positive >= 2,
                "aggregate_ranking_guardrail_reversal": guardrail_reversal,
                "passes_original_o2_survivor_diagnostics": bool(median > 0.0 and q25 > 0.0 and positive >= 2 and not guardrail_reversal),
            }
        )
    return pd.DataFrame(rows)


def _paired_comparison(metrics: pd.DataFrame, aggregate: pd.DataFrame) -> pd.DataFrame:
    fold_rows: list[dict[str, object]] = []
    for _, row in metrics.iterrows():
        if row["model"] != BASELINE_MODEL:
            fold_rows.append(
                {
                    "level": "fold",
                    "fold": row["fold"],
                    "model": row["model"],
                    "reference": BASELINE_MODEL,
                    "candidate_pr_auc": row["pr_auc"],
                    "reference_pr_auc": float(metrics[(metrics["model"] == BASELINE_MODEL) & (metrics["fold"] == row["fold"])]["pr_auc"].iloc[0]),
                    "paired_pr_auc_delta": row["paired_pr_auc_vs_baseline"],
                }
            )
        if row["model"] in REDUCED_MODELS:
            fold_rows.append(
                {
                    "level": "fold",
                    "fold": row["fold"],
                    "model": row["model"],
                    "reference": O2_FULL_3,
                    "candidate_pr_auc": row["pr_auc"],
                    "reference_pr_auc": float(metrics[(metrics["model"] == O2_FULL_3) & (metrics["fold"] == row["fold"])]["pr_auc"].iloc[0]),
                    "paired_pr_auc_delta": row["paired_pr_auc_vs_o2_full_3"],
                }
            )
    aggregate_rows: list[dict[str, object]] = []
    for _, row in aggregate.iterrows():
        if row["model"] != BASELINE_MODEL:
            aggregate_rows.append(
                {
                    "level": "aggregate",
                    "fold": "ALL",
                    "model": row["model"],
                    "reference": BASELINE_MODEL,
                    "candidate_pr_auc": row["mean_pr_auc"],
                    "reference_pr_auc": float(aggregate[aggregate["model"] == BASELINE_MODEL]["mean_pr_auc"].iloc[0]),
                    "paired_pr_auc_delta": row["mean_paired_pr_auc_vs_baseline"],
                }
            )
        if row["model"] in REDUCED_MODELS:
            aggregate_rows.append(
                {
                    "level": "aggregate",
                    "fold": "ALL",
                    "model": row["model"],
                    "reference": O2_FULL_3,
                    "candidate_pr_auc": row["mean_pr_auc"],
                    "reference_pr_auc": float(aggregate[aggregate["model"] == O2_FULL_3]["mean_pr_auc"].iloc[0]),
                    "paired_pr_auc_delta": row["mean_paired_pr_auc_vs_o2_full_3"],
                }
            )
    return pd.DataFrame(fold_rows + aggregate_rows)


def run_experiment(
    *,
    coverage_path: Path,
    training_table_path: Path,
    training_manifest_path: Path,
    o1_artifact_manifest_path: Path,
    o2_artifact_manifest_path: Path,
    output_dir: Path,
    immutable_panel_path: Path,
    calendar_path: Path,
    security_master_path: Path,
    accepted_open_panel_path: Path,
    accepted_open_provenance_path: Path,
) -> dict[str, object]:
    if (output_dir / "artifact_manifest.json").exists():
        raise RuntimeError(f"refusing to overwrite existing minimality runtime: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    contract: dict[str, object] = {}
    for label, path, expected in (
        ("immutable_panel", immutable_panel_path, EXPECTED_PANEL_SHA256),
        ("official_calendar", calendar_path, EXPECTED_CALENDAR_SHA256),
        ("security_master", security_master_path, EXPECTED_SECURITY_MASTER_SHA256),
        ("accepted_open_panel", accepted_open_panel_path, EXPECTED_ACCEPTED_OPEN_PANEL_SHA256),
        ("accepted_open_provenance", accepted_open_provenance_path, EXPECTED_ACCEPTED_OPEN_PROVENANCE_SHA256),
        ("o1_artifact_manifest", o1_artifact_manifest_path, EXPECTED_O1_ARTIFACT_MANIFEST_SHA256),
    ):
        contract[f"{label}_path"] = str(path)
        contract[f"{label}_sha256"] = _verify_file(path, expected, label)
    accepted_o2 = _verify_accepted_o2_manifest(o2_artifact_manifest_path)
    contract["accepted_o2_artifact_manifest"] = accepted_o2

    support, support_contract = load_common_support(
        coverage_path=coverage_path,
        training_table_path=training_table_path,
        training_manifest_path=training_manifest_path,
    )
    if support_contract["common_support_key_sha256"] != EXPECTED_COMMON_SUPPORT_KEY_SHA256:
        raise RuntimeError("common-support identity hash differs from the accepted O2 population")
    support, formula_errors = _attach_geometry(support, coverage_path)
    if len(support) != EXPECTED_COMMON_SUPPORT_ROWS or _stable_key_hash(support) != EXPECTED_COMMON_SUPPORT_KEY_SHA256:
        raise RuntimeError("minimality population is not the exact frozen O2 common-support set")
    contract.update(support_contract)
    contract.update(
        {
            "minimality_models": list(MODEL_ORDER),
            "reduced_models": list(REDUCED_MODELS),
            "feature_order_sha256": {name: feature_order_hash(columns) for name, columns in MODEL_FEATURES.items()},
            "v3_b_feature_order_sha256": EXPECTED_V3_B_FEATURE_ORDER_SHA256,
            "o2_geometry_features": list(O2_GEOMETRY_FEATURES),
            "o2_feature_order_sha256": EXPECTED_O2_FEATURE_ORDER_SHA256,
            "geometry_formula_max_abs_error": formula_errors,
            "folds": verify_fold_contract(),
            "hgb_parameters": HGB_PARAMS,
            "fresh_forward_outcomes_accessed": False,
            "provider_calls": False,
            "final_representation_selected": False,
        }
    )

    pd.DataFrame(
        {
            "ticker": support["ticker"],
            "date": support["date"].dt.strftime("%Y-%m-%d"),
            "signal_session_index": support["signal_session_index"],
        }
    ).sort_values(["ticker", "date"], kind="mergesort").to_csv(output_dir / "common_support_rows.csv", index=False)
    (output_dir / "preflight_contract.json").write_text(json.dumps(contract, indent=2, sort_keys=True, default=str), encoding="utf-8")
    (output_dir / "fold_definitions.json").write_text(json.dumps(contract["folds"], indent=2), encoding="utf-8")
    (output_dir / "feature_manifest.json").write_text(
        json.dumps(
            {"models": {name: list(columns) for name, columns in MODEL_FEATURES.items()}, "feature_order_sha256": contract["feature_order_sha256"], "hgb_parameters": HGB_PARAMS},
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    metric_rows: list[dict[str, object]] = []
    prediction_frames: list[pd.DataFrame] = []
    start = time.perf_counter()
    for fold in RANKING_V2_FOLDS:
        train = support[support["signal_session_index"].between(fold.train_start, fold.train_end)].copy()
        validation = support[support["signal_session_index"].between(fold.validation_start, fold.validation_end)].copy()
        if train.empty or validation.empty or train["binary_target"].nunique() != 2 or validation["binary_target"].nunique() != 2:
            raise RuntimeError(f"{fold.name} does not have a valid common-support train/validation set")
        fold_scores: dict[str, np.ndarray] = {}
        fold_metric_start = len(metric_rows)
        for model_name in MODEL_ORDER:
            model_start = time.perf_counter()
            columns = MODEL_FEATURES[model_name]
            model = minimality_hgb_pipeline(columns)
            model.fit(train[list(columns)], train["binary_target"].astype(int).to_numpy())
            scores = raw_score(model, validation[list(columns)])
            if not np.isfinite(scores).all():
                raise RuntimeError(f"{model_name} {fold.name} produced non-finite scores")
            fold_scores[model_name] = scores
            evaluated = evaluate_scores(validation, scores)
            metric_rows.append(
                {
                    "model": model_name,
                    "fold": fold.name,
                    **asdict(fold),
                    "train_rows": int(len(train)),
                    "validation_rows": int(len(validation)),
                    "train_identity_sha256": _stable_key_hash(train),
                    "validation_identity_sha256": _stable_key_hash(validation),
                    "feature_count": int(len(columns)),
                    "feature_order_sha256": feature_order_hash(columns),
                    "training_runtime_seconds": float(time.perf_counter() - model_start),
                    **evaluated,
                    "paired_pr_auc_vs_baseline": np.nan,
                    "paired_pr_auc_vs_o2_full_3": np.nan,
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
                        "binary_target": validation["binary_target"].to_numpy(),
                        "score": scores,
                    }
                )
            )
        baseline_pr = float(evaluate_scores(validation, fold_scores[BASELINE_MODEL])["pr_auc"])
        full_pr = float(evaluate_scores(validation, fold_scores[O2_FULL_3])["pr_auc"])
        for row in metric_rows[fold_metric_start:]:
            if row["model"] != BASELINE_MODEL:
                row["paired_pr_auc_vs_baseline"] = float(row["pr_auc"] - baseline_pr)
            if row["model"] != O2_FULL_3:
                row["paired_pr_auc_vs_o2_full_3"] = float(row["pr_auc"] - full_pr)

    metrics = pd.DataFrame(metric_rows)
    aggregate = _aggregate_minimality(metrics)
    diagnostics = _minimality_diagnostics(metrics, aggregate)
    predictions = pd.concat(prediction_frames, ignore_index=True)
    predictions["year"] = pd.to_datetime(predictions["date"]).dt.year.astype(int)
    era = _era_metrics(predictions)
    paired = _paired_comparison(metrics, aggregate)
    accepted_reproduction = _metric_reproduction(metrics, aggregate, o2_artifact_manifest_path.parent)

    metrics.to_csv(output_dir / "fold_metrics.csv", index=False)
    aggregate.to_csv(output_dir / "aggregate_metrics.csv", index=False)
    diagnostics.to_csv(output_dir / "minimality_diagnostics.csv", index=False)
    paired.to_csv(output_dir / "paired_comparisons.csv", index=False)
    era.to_csv(output_dir / "era_metrics.csv", index=False)
    predictions.to_parquet(output_dir / "fold_predictions.parquet", index=False)
    summary = {
        "status": EXPECTED_STATUS,
        "models": list(MODEL_ORDER),
        "common_support_rows": EXPECTED_COMMON_SUPPORT_ROWS,
        "common_support_tickers": int(support["ticker"].nunique()),
        "common_support_key_sha256": contract["common_support_key_sha256"],
        "fold_count": len(RANKING_V2_FOLDS),
        "fresh_forward_outcomes_accessed": False,
        "provider_calls": False,
        "final_representation_selected": False,
        "accepted_o2_reproduction": accepted_reproduction,
        "training_runtime_seconds": float(time.perf_counter() - start),
    }
    (output_dir / "experiment_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, default=str), encoding="utf-8")
    artifacts: dict[str, str] = {}
    for path in sorted(output_dir.iterdir()):
        if path.name != "artifact_manifest.json" and path.is_file():
            from .ohlcv_o1_research import sha256_file

            artifacts[path.name] = sha256_file(path)
    manifest = {
        "schema": "idx-trade/ohlcv-o2-minimality-artifacts-v1",
        "status": EXPECTED_STATUS,
        "artifact_sha256": artifacts,
        "preflight_contract": contract,
        "summary": summary,
        "environment": {"python": sys.version, "platform": platform.platform(), "packages": {"numpy": np.__version__, "pandas": pd.__version__}},
    }
    manifest_path = output_dir / "artifact_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str), encoding="utf-8")
    from .ohlcv_o1_research import sha256_file

    manifest_sha = sha256_file(manifest_path)
    return {
        **summary,
        "artifact_manifest_sha256": manifest_sha,
        "artifact_count": len(artifacts),
        "aggregate": aggregate.to_dict(orient="records"),
        "diagnostics": diagnostics.to_dict(orient="records"),
        "contract": contract,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "coverage_path",
        "training_table_path",
        "training_manifest_path",
        "o1_artifact_manifest_path",
        "o2_artifact_manifest_path",
        "output_dir",
        "immutable_panel_path",
        "calendar_path",
        "security_master_path",
        "accepted_open_panel_path",
        "accepted_open_provenance_path",
    ):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    result = run_experiment(**vars(args))
    print(
        json.dumps(
            {k: result[k] for k in ("status", "common_support_rows", "common_support_tickers", "fold_count", "training_runtime_seconds", "artifact_manifest_sha256", "artifact_count")},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
