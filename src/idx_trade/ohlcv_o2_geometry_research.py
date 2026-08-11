"""Frozen historical-development experiment for the single O2 geometry challenger."""

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
    EXPECTED_SECURITY_MASTER_SHA256,
    EXPECTED_TRAINING_MANIFEST_SHA256,
    EXPECTED_TRAINING_TABLE_SHA256,
    EXPECTED_V3_B_FEATURE_ORDER_SHA256,
    EXPECTED_PANEL_SHA256,
    HGB_PARAMS,
    RANKING_V2_FOLDS,
    V3_B_FEATURE_COLUMNS,
    _aggregate_metrics,
    _era_metrics,
    _normal_date,
    _stable_key_hash,
    _verify_file,
    evaluate_scores,
    feature_order_hash,
    load_common_support,
    raw_score,
    verify_fold_contract,
    verify_v3_b_feature_order,
)
from .research_features import assert_no_open_dependency


O2_MODEL = "O2_OPEN_GEOMETRY"
BASELINE_MODEL = "V3B_COMMON_SUPPORT_BASELINE"
MODEL_ORDER = (BASELINE_MODEL, O2_MODEL)
O2_GEOMETRY_FEATURES = ("open_position", "open_to_high", "open_to_low")
O2_FEATURE_COLUMNS = (*V3_B_FEATURE_COLUMNS, *O2_GEOMETRY_FEATURES)
EXPECTED_O2_FEATURE_ORDER_SHA256 = feature_order_hash(O2_FEATURE_COLUMNS)
EXPECTED_COMMON_SUPPORT_KEY_SHA256 = "716bed364b5ba0dcb034f335bc7b09b4abac23eb1236a7c718fe6e0f6a78577a"
EXPECTED_O1_ARTIFACT_MANIFEST_SHA256 = "2441f9fcadc9a496ed5d15306bb7bbcb87c9978ecdc26033f5bd7619c2d08714"


def o2_hgb_pipeline(feature_columns: tuple[str, ...]) -> Pipeline:
    if feature_columns not in (V3_B_FEATURE_COLUMNS, O2_FEATURE_COLUMNS):
        raise ValueError("O2 runner received an unfrozen feature order")
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


def _attach_geometry(support: pd.DataFrame, coverage_path: Path) -> tuple[pd.DataFrame, dict[str, float]]:
    coverage = pd.read_csv(coverage_path, parse_dates=["date"])
    coverage["date"] = _normal_date(coverage["date"])
    ready = coverage[coverage["open_feature_ready"].astype(bool)].copy()
    required = {"ticker", "date", "signal_session_index", "high", "low", "open", *O2_GEOMETRY_FEATURES}
    missing = required - set(ready.columns)
    if missing:
        raise RuntimeError(f"coverage artifact is missing O2 geometry columns: {sorted(missing)}")
    geometry = ready[["ticker", "date", "signal_session_index", "high", "low", "open", *O2_GEOMETRY_FEATURES]]
    joined = support.merge(
        geometry,
        on=["ticker", "date"],
        how="inner",
        validate="one_to_one",
        suffixes=("", "_geometry"),
    )
    if len(joined) != EXPECTED_COMMON_SUPPORT_ROWS:
        raise RuntimeError(f"O2 geometry join changed common support: {len(joined)}")
    if not (joined["signal_session_index"].astype(int) == joined["signal_session_index_geometry"].astype(int)).all():
        raise RuntimeError("O2 geometry signal-session identities disagree")
    joined = joined.drop(columns=["signal_session_index_geometry"])
    high = pd.to_numeric(joined["high"], errors="raise").to_numpy(dtype=float)
    low = pd.to_numeric(joined["low"], errors="raise").to_numpy(dtype=float)
    open_values = pd.to_numeric(joined["open"], errors="raise").to_numpy(dtype=float)
    denominator = high - low
    if not np.isfinite(denominator).all() or (denominator <= 0.0).any():
        raise RuntimeError("O2 common support contains a flat/invalid H-L range")
    expected = {
        "open_position": (open_values - low) / denominator,
        "open_to_high": high / open_values - 1.0,
        "open_to_low": low / open_values - 1.0,
    }
    formula_max_abs_error: dict[str, float] = {}
    for name, values in expected.items():
        actual = pd.to_numeric(joined[name], errors="raise").to_numpy(dtype=float)
        if not np.isfinite(actual).all() or not np.allclose(actual, values, rtol=0.0, atol=1e-12):
            raise RuntimeError(f"certified O2 geometry formula mismatch: {name}")
        formula_max_abs_error[name] = float(np.max(np.abs(actual - values)))
    if (open_values <= 0.0).any():
        raise RuntimeError("O2 common support contains non-positive Open")
    joined = joined.drop(columns=["high", "low", "open"])
    return joined, formula_max_abs_error


def _o2_survivor(metrics: pd.DataFrame, aggregate: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    baseline = aggregate[aggregate["model"].eq(BASELINE_MODEL)].iloc[0]
    candidate = aggregate[aggregate["model"].eq(O2_MODEL)].iloc[0]
    block = metrics[metrics["model"].eq(O2_MODEL)].sort_values("fold")
    deltas = block["paired_pr_auc_vs_baseline"].to_numpy(dtype=float)
    median = float(np.median(deltas))
    q25 = float(np.quantile(deltas, 0.25))
    positive_folds = int(np.sum(deltas > 0.0))
    guardrail_reversal = bool(
        candidate["median_roc_auc"] < baseline["median_roc_auc"]
        and candidate["median_q5_minus_q1"] < baseline["median_q5_minus_q1"]
    )
    decision = bool(median > 0.0 and q25 > 0.0 and positive_folds >= 2 and not guardrail_reversal)
    table = pd.DataFrame(
        [
            {
                "model": O2_MODEL,
                "median_paired_pr_auc": median,
                "q25_paired_pr_auc": q25,
                "positive_paired_folds": positive_folds,
                "not_one_isolated_fold_spike": positive_folds >= 2,
                "aggregate_ranking_guardrail_reversal": guardrail_reversal,
                "survivor": decision,
            }
        ]
    )
    return ("O2_SURVIVOR" if decision else "O2_NO_SURVIVOR"), table


def run_experiment(
    *,
    coverage_path: Path,
    training_table_path: Path,
    training_manifest_path: Path,
    o1_artifact_manifest_path: Path,
    output_dir: Path,
    immutable_panel_path: Path,
    calendar_path: Path,
    security_master_path: Path,
    accepted_open_panel_path: Path,
    accepted_open_provenance_path: Path,
) -> dict[str, object]:
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
    support, support_contract = load_common_support(
        coverage_path=coverage_path,
        training_table_path=training_table_path,
        training_manifest_path=training_manifest_path,
    )
    if support_contract["common_support_key_sha256"] != EXPECTED_COMMON_SUPPORT_KEY_SHA256:
        raise RuntimeError("common-support identity hash differs from the accepted O1 population")
    support, formula_errors = _attach_geometry(support, coverage_path)
    contract.update(support_contract)
    contract.update(
        {
            "parent_o1_artifact_manifest_sha256": EXPECTED_O1_ARTIFACT_MANIFEST_SHA256,
            "o2_model": O2_MODEL,
            "o2_geometry_features": list(O2_GEOMETRY_FEATURES),
            "o2_feature_order_sha256": EXPECTED_O2_FEATURE_ORDER_SHA256,
            "geometry_formula_max_abs_error": formula_errors,
            "folds": verify_fold_contract(),
            "fresh_forward_outcomes_accessed": False,
        }
    )
    if len(support) != EXPECTED_COMMON_SUPPORT_ROWS or _stable_key_hash(support) != EXPECTED_COMMON_SUPPORT_KEY_SHA256:
        raise RuntimeError("O2 population is not the exact frozen O1 common-support set")
    pd.DataFrame(
        {
            "ticker": support["ticker"],
            "date": support["date"].dt.strftime("%Y-%m-%d"),
            "signal_session_index": support["signal_session_index"],
        }
    ).sort_values(["ticker", "date"], kind="mergesort").to_csv(output_dir / "common_support_rows.csv", index=False)
    (output_dir / "preflight_contract.json").write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "fold_definitions.json").write_text(json.dumps(contract["folds"], indent=2), encoding="utf-8")
    (output_dir / "feature_manifest.json").write_text(
        json.dumps(
            {
                "baseline_model": BASELINE_MODEL,
                "challenger_model": O2_MODEL,
                "baseline_feature_columns": list(V3_B_FEATURE_COLUMNS),
                "challenger_feature_columns": list(O2_FEATURE_COLUMNS),
                "baseline_feature_order_sha256": EXPECTED_V3_B_FEATURE_ORDER_SHA256,
                "challenger_feature_order_sha256": EXPECTED_O2_FEATURE_ORDER_SHA256,
                "hgb_parameters": HGB_PARAMS,
            },
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
        for model_name, columns in ((BASELINE_MODEL, V3_B_FEATURE_COLUMNS), (O2_MODEL, O2_FEATURE_COLUMNS)):
            model_start = time.perf_counter()
            model = o2_hgb_pipeline(columns)
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
                    "feature_count": int(len(columns)),
                    "feature_order_sha256": feature_order_hash(columns),
                    "training_runtime_seconds": float(time.perf_counter() - model_start),
                    **evaluated,
                    "paired_pr_auc_vs_baseline": np.nan,
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
        for row in metric_rows[-2:]:
            if row["model"] == O2_MODEL:
                row["paired_pr_auc_vs_baseline"] = float(row["pr_auc"] - baseline_pr)
    metrics = pd.DataFrame(metric_rows)
    aggregate = _aggregate_metrics(metrics)
    decision, survivor_table = _o2_survivor(metrics, aggregate)
    predictions = pd.concat(prediction_frames, ignore_index=True)
    predictions["year"] = pd.to_datetime(predictions["date"]).dt.year.astype(int)
    era = _era_metrics(predictions)
    metrics.to_csv(output_dir / "fold_metrics.csv", index=False)
    aggregate.to_csv(output_dir / "aggregate_metrics.csv", index=False)
    survivor_table.to_csv(output_dir / "survivor_decision.csv", index=False)
    era.to_csv(output_dir / "era_metrics.csv", index=False)
    predictions.to_parquet(output_dir / "fold_predictions.parquet", index=False)
    summary = {
        "status": decision,
        "models": list(MODEL_ORDER),
        "common_support_rows": EXPECTED_COMMON_SUPPORT_ROWS,
        "common_support_key_sha256": contract["common_support_key_sha256"],
        "fold_count": len(RANKING_V2_FOLDS),
        "fresh_forward_outcomes_accessed": False,
        "training_runtime_seconds": float(time.perf_counter() - start),
        "aggregate_metrics_path": str(output_dir / "aggregate_metrics.csv"),
        "survivor_decision_path": str(output_dir / "survivor_decision.csv"),
    }
    (output_dir / "experiment_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    artifacts: dict[str, str] = {}
    from .ohlcv_o1_research import sha256_file

    for path in sorted(output_dir.iterdir()):
        if path.name != "artifact_manifest.json" and path.is_file():
            artifacts[path.name] = sha256_file(path)
    manifest = {
        "schema": "idx-trade/ohlcv-o2-geometry-research-artifacts-v1",
        "status": decision,
        "artifact_sha256": artifacts,
        "preflight_contract": contract,
        "summary": summary,
        "environment": {"python": sys.version, "platform": platform.platform(), "packages": {"numpy": np.__version__, "pandas": pd.__version__}},
    }
    manifest_path = output_dir / "artifact_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str), encoding="utf-8")
    manifest_sha = sha256_file(manifest_path)
    return {**summary, "artifact_manifest_sha256": manifest_sha, "artifact_count": len(artifacts), "aggregate": aggregate.to_dict(orient="records"), "survivor_decision": survivor_table.to_dict(orient="records"), "contract": contract}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("coverage_path", "training_table_path", "training_manifest_path", "o1_artifact_manifest_path", "output_dir", "immutable_panel_path", "calendar_path", "security_master_path", "accepted_open_panel_path", "accepted_open_provenance_path"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    result = run_experiment(**vars(args))
    print(json.dumps({k: result[k] for k in ("status", "common_support_rows", "fold_count", "training_runtime_seconds", "artifact_manifest_sha256", "artifact_count")}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
