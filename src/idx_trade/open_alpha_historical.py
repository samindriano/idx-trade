"""One-shot historical comparison for the preregistered clean-V2 Open alpha.

This module is intentionally narrower than the outcome-blind audit.  It joins
the already frozen common-support cache to the accepted clean-V2 H10 labels,
then fits exactly CONTROL, V2.1, and V2.2 on the six frozen folds.  It does not
perform feature search, refit a canonical model, touch forward data, or select
anything outside the preregistered survivor rule.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any, Sequence

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline

from .open_alpha_prereg import (
    CONTROL_FEATURE_COLUMNS,
    FROZEN_V2_FOLDS,
    PREVIOUS_RANGE_OPEN_FEATURES,
    SAME_DAY_OPEN_FEATURES,
    V21_FEATURE_COLUMNS,
    V22_FEATURE_COLUMNS,
    evaluate_survivor_gate,
    feature_order_sha256,
    select_historical_winner,
    sha256_file,
    stable_key_sha256,
)


CONTROL_MODEL = "CONTROL_CLEAN_V2_HGB_XS_MARKET"
V21_MODEL = "V2.1_CLEAN_V2_OPEN_GEOMETRY"
V22_MODEL = "V2.2_CLEAN_V2_PREVIOUS_RANGE_OPEN_DISPLACEMENT"
MODEL_ORDER = (CONTROL_MODEL, V21_MODEL, V22_MODEL)
MODEL_FEATURES: dict[str, tuple[str, ...]] = {
    CONTROL_MODEL: tuple(CONTROL_FEATURE_COLUMNS),
    V21_MODEL: tuple(V21_FEATURE_COLUMNS),
    V22_MODEL: tuple(V22_FEATURE_COLUMNS),
}

HGB_PARAMETERS = {
    "learning_rate": 0.05,
    "max_iter": 200,
    "max_leaf_nodes": 31,
    "l2_regularization": 1.0,
    "random_state": 42,
}
HGB_PREPROCESSING = (
    "ColumnTransformer[numeric=Pipeline[SimpleImputer(strategy=median, "
    "add_indicator=True, keep_empty_features=True)], remainder=drop]"
)
EXPECTED_COMMON_SUPPORT_ROWS = 277_244
EXPECTED_COMMON_SUPPORT_TICKERS = 729
EXPECTED_COMMON_SUPPORT_KEY_SHA256 = "e058e5ce4ce650eeab5acd57a7d697c155548e40bbbb8ffe0eab120987d857df"
EXPECTED_COMMON_SUPPORT_SHA256 = "6590686c6790b81abf204b2fc4228e2bb8b3039a7d18c573ec116aee7c117ab6"
EXPECTED_CLEAN_V2_LABEL_SOURCE_SHA256 = "b27a603cea39298f18996629a16f25990d3d04422b12ccb5d9bd1e45dbb34af8"
HISTORICAL_BOUNDARY = pd.Timestamp("2026-07-31")


def _normalise_dates(values: pd.Series) -> pd.Series:
    dates = pd.to_datetime(values, errors="coerce")
    if getattr(dates.dt, "tz", None) is not None:
        dates = dates.dt.tz_localize(None)
    return dates.dt.normalize()


def _numeric_preprocessor(columns: Sequence[str]) -> ColumnTransformer:
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
    return ColumnTransformer(
        [("numeric", numeric, list(columns))],
        remainder="drop",
    )


def frozen_hgb_model(columns: Sequence[str]) -> Pipeline:
    columns = tuple(columns)
    if columns not in MODEL_FEATURES.values():
        raise ValueError("historical runner received an unfrozen feature order")
    return Pipeline(
        [
            ("preprocess", _numeric_preprocessor(columns)),
            ("model", HistGradientBoostingClassifier(**HGB_PARAMETERS)),
        ]
    )


def raw_rank_score(model: Pipeline, frame: pd.DataFrame) -> np.ndarray:
    transformed = model.named_steps["preprocess"].transform(frame)
    estimator = model.named_steps["model"]
    if hasattr(estimator, "decision_function"):
        return np.asarray(estimator.decision_function(transformed), dtype=float)
    probability = np.asarray(estimator.predict_proba(transformed)[:, 1], dtype=float)
    clipped = np.clip(probability, 1e-9, 1.0 - 1e-9)
    return np.log(clipped / (1.0 - clipped))


def _ranking_metrics(frame: pd.DataFrame, score: Sequence[float]) -> dict[str, float]:
    target = pd.to_numeric(frame["binary_target"], errors="raise").to_numpy(dtype=int)
    scores = np.asarray(score, dtype=float)
    if len(target) == 0 or len(target) != len(scores):
        raise ValueError("ranking metrics require aligned non-empty arrays")
    if np.unique(target).size != 2 or not np.isfinite(scores).all():
        raise ValueError("ranking metrics require two classes and finite scores")
    scored = frame[["date", "ticker", "binary_target"]].copy()
    scored["score"] = scores
    pieces: list[pd.DataFrame] = []
    for _, group in scored.groupby("date", sort=True):
        ordered = group.sort_values(["score", "ticker"], kind="mergesort").copy()
        n = len(ordered)
        ordered["quintile"] = np.ceil(5 * np.arange(1, n + 1) / n).astype(int).clip(1, 5)
        ordered["decile"] = np.ceil(10 * np.arange(1, n + 1) / n).astype(int).clip(1, 10)
        pieces.append(ordered)
    bucketed = pd.concat(pieces, ignore_index=True)
    overall = float(target.mean())
    quintile_rates = bucketed.groupby("quintile")["binary_target"].mean()
    decile_rates = bucketed.groupby("decile")["binary_target"].mean()
    return {
        "rows": float(len(target)),
        "positive_rate": overall,
        "pr_auc": float(average_precision_score(target, scores)),
        "pr_auc_minus_prevalence": float(average_precision_score(target, scores) - overall),
        "roc_auc": float(roc_auc_score(target, scores)),
        "q5_minus_q1": float(quintile_rates.loc[5] - quintile_rates.loc[1]),
        "top_decile_lift": float(decile_rates.loc[10] - overall),
    }


def _split_fold(table: pd.DataFrame, fold: Any) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = table[table["signal_session_index"].between(fold.train_start, fold.train_end)].copy()
    validation = table[table["signal_session_index"].between(fold.validation_start, fold.validation_end)].copy()
    if train.empty or validation.empty:
        raise RuntimeError(f"{fold.name} has empty train or validation rows")
    if np.unique(train["binary_target"]).size != 2:
        raise RuntimeError(f"{fold.name} training rows require both target classes")
    if np.unique(validation["binary_target"]).size != 2:
        raise RuntimeError(f"{fold.name} validation rows require both target classes")
    return train, validation


def _load_common_support(common_support_path: Path, label_source_path: Path) -> tuple[pd.DataFrame, dict[str, str]]:
    common_sha = sha256_file(common_support_path)
    label_sha = sha256_file(label_source_path)
    if common_sha != EXPECTED_COMMON_SUPPORT_SHA256:
        raise RuntimeError(f"common-support SHA mismatch: {common_sha}")
    if label_sha != EXPECTED_CLEAN_V2_LABEL_SOURCE_SHA256:
        raise RuntimeError(f"clean-V2 label source SHA mismatch: {label_sha}")
    common = pd.read_parquet(common_support_path)
    labels = pd.read_parquet(
        label_source_path,
        columns=["ticker", "date", "signal_session_index", "binary_target", "label_status"],
    )
    keys = ["ticker", "date", "signal_session_index"]
    for frame in (common, labels):
        frame["ticker"] = frame["ticker"].astype(str).str.upper().str.strip()
        frame["date"] = _normalise_dates(frame["date"])
        frame["signal_session_index"] = pd.to_numeric(frame["signal_session_index"], errors="raise").astype(int)
    if common.duplicated(keys).any() or labels.duplicated(keys).any():
        raise RuntimeError("historical population contains duplicate row identities")
    if len(common) != EXPECTED_COMMON_SUPPORT_ROWS or common["ticker"].nunique() != EXPECTED_COMMON_SUPPORT_TICKERS:
        raise RuntimeError("common-support population changed from the accepted cache")
    if stable_key_sha256(common) != EXPECTED_COMMON_SUPPORT_KEY_SHA256:
        raise RuntimeError("common-support key SHA changed from the accepted cache")
    joined = common.merge(labels, on=keys, how="left", validate="one_to_one", indicator=True)
    if not joined["_merge"].eq("both").all():
        raise RuntimeError("clean-V2 H10 labels do not cover the exact common support")
    joined = joined.drop(columns="_merge")
    joined["binary_target"] = pd.to_numeric(joined["binary_target"], errors="raise").astype(int)
    if not set(joined["binary_target"].unique()).issubset({0, 1}):
        raise RuntimeError("clean-V2 H10 labels are not binary")
    if set(joined["label_status"].astype(str)) != {"TP_FIRST", "SL_FIRST"}:
        raise RuntimeError("clean-V2 H10 label statuses are not frozen")
    mapping = joined.groupby("label_status")["binary_target"].unique().to_dict()
    if set(mapping.get("TP_FIRST", ())) != {1} or set(mapping.get("SL_FIRST", ())) != {0}:
        raise RuntimeError(f"clean-V2 H10 label mapping changed: {mapping}")
    if joined["date"].max() > HISTORICAL_BOUNDARY:
        raise RuntimeError("historical population crosses the 2026-07-31 boundary")
    return joined.sort_values(["signal_session_index", "ticker"], kind="mergesort").reset_index(drop=True), {
        "common_support_sha256": common_sha,
        "clean_v2_label_source_sha256": label_sha,
        "common_support_key_sha256": stable_key_sha256(common),
    }


def _paired(metrics: pd.DataFrame, candidate: str, comparator: str) -> pd.DataFrame:
    left = metrics[metrics["model"].eq(candidate)].copy()
    right = metrics[metrics["model"].eq(comparator)].copy()
    keep = ["fold", "pr_auc", "roc_auc", "q5_minus_q1", "top_decile_lift"]
    joined = left.merge(right[keep], on="fold", suffixes=("", "_comparator"), validate="one_to_one")
    joined["pr_auc_delta"] = joined["pr_auc"] - joined["pr_auc_comparator"]
    joined["roc_auc_delta"] = joined["roc_auc"] - joined["roc_auc_comparator"]
    joined["q5_minus_q1_delta"] = joined["q5_minus_q1"] - joined["q5_minus_q1_comparator"]
    joined["top_decile_lift_delta"] = joined["top_decile_lift"] - joined["top_decile_lift_comparator"]
    return joined.sort_values("fold").reset_index(drop=True)


def _gate_from_pair(pair: pd.DataFrame) -> dict[str, object]:
    result = evaluate_survivor_gate(
        pair["pr_auc_delta"].tolist(),
        pair["roc_auc"].tolist(),
        pair["roc_auc_comparator"].tolist(),
        pair["q5_minus_q1"].tolist(),
        pair["q5_minus_q1_comparator"].tolist(),
    )
    return result


def _artifact_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)).replace("\\", "/"): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name not in {"artifact_manifest.json", "artifact_manifest.sha256"}
    }


def run_historical_comparison(
    *,
    common_support_path: Path,
    label_source_path: Path,
    output_dir: Path,
) -> dict[str, object]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError(f"historical output must be new or empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    table, source_hashes = _load_common_support(common_support_path, label_source_path)
    table.to_parquet(output_dir / "labeled_common_support.parquet", index=False)

    metrics_rows: list[dict[str, object]] = []
    prediction_rows: list[pd.DataFrame] = []
    model_hashes: dict[str, str] = {}
    models_dir = output_dir / "fold_models"
    models_dir.mkdir()
    for fold in FROZEN_V2_FOLDS:
        train, validation = _split_fold(table, fold)
        identity_reference = validation[["ticker", "date", "signal_session_index"]].reset_index(drop=True)
        for model_name in MODEL_ORDER:
            columns = MODEL_FEATURES[model_name]
            fitted = frozen_hgb_model(columns)
            fitted.fit(train.loc[:, columns], train["binary_target"].to_numpy(dtype=int))
            scores = raw_rank_score(fitted, validation.loc[:, columns])
            if not np.isfinite(scores).all():
                raise RuntimeError(f"{model_name} {fold.name} produced non-finite scores")
            metrics_rows.append(
                {
                    "model": model_name,
                    "fold": fold.name,
                    **fold.__dict__,
                    "train_rows": int(len(train)),
                    "validation_rows": int(len(validation)),
                    "feature_count": int(len(columns)),
                    "feature_order_sha256": feature_order_sha256(columns),
                    **_ranking_metrics(validation, scores),
                }
            )
            prediction = identity_reference.copy()
            prediction["model"] = model_name
            prediction["fold"] = fold.name
            prediction["binary_target"] = validation["binary_target"].to_numpy(dtype=int)
            prediction["label_status"] = validation["label_status"].to_numpy()
            prediction["score"] = scores
            prediction_rows.append(prediction)
            model_path = models_dir / f"{model_name.lower()}_{fold.name.lower()}.joblib"
            joblib.dump(fitted, model_path)
            model_hashes[model_path.name] = sha256_file(model_path)
    metrics = pd.DataFrame(metrics_rows).sort_values(["model", "fold"]).reset_index(drop=True)
    predictions = pd.concat(prediction_rows, ignore_index=True).sort_values(
        ["model", "fold", "signal_session_index", "ticker"], kind="mergesort"
    ).reset_index(drop=True)
    for fold in [fold.name for fold in FROZEN_V2_FOLDS]:
        blocks = [
            predictions[(predictions["fold"] == fold) & (predictions["model"] == model)][["ticker", "date", "signal_session_index"]].reset_index(drop=True)
            for model in MODEL_ORDER
        ]
        if not (blocks[0].equals(blocks[1]) and blocks[0].equals(blocks[2])):
            raise RuntimeError(f"same-fold prediction identities differ in {fold}")

    metrics.to_csv(output_dir / "fold_metrics.csv", index=False)
    predictions.to_parquet(output_dir / "predictions.parquet", index=False)
    pair_v21_control = _paired(metrics, V21_MODEL, CONTROL_MODEL)
    pair_v22_control = _paired(metrics, V22_MODEL, CONTROL_MODEL)
    pair_v21_v22 = _paired(metrics, V21_MODEL, V22_MODEL)
    pair_v22_v21 = _paired(metrics, V22_MODEL, V21_MODEL)
    pair_v21_control.to_csv(output_dir / "paired_v21_vs_control.csv", index=False)
    pair_v22_control.to_csv(output_dir / "paired_v22_vs_control.csv", index=False)
    pair_v21_v22.to_csv(output_dir / "paired_v21_vs_v22.csv", index=False)
    pair_v22_v21.to_csv(output_dir / "paired_v22_vs_v21.csv", index=False)

    aggregate = (
        metrics.groupby("model", sort=False)
        .agg(
            folds=("fold", "count"),
            mean_pr_auc=("pr_auc", "mean"),
            median_pr_auc=("pr_auc", "median"),
            mean_pr_auc_minus_prevalence=("pr_auc_minus_prevalence", "mean"),
            median_roc_auc=("roc_auc", "median"),
            median_q5_minus_q1=("q5_minus_q1", "median"),
            median_top_decile_lift=("top_decile_lift", "median"),
        )
        .reset_index()
    )
    aggregate.to_csv(output_dir / "aggregate_metrics.csv", index=False)
    gates = {
        "v21_vs_control": _gate_from_pair(pair_v21_control),
        "v22_vs_control": _gate_from_pair(pair_v22_control),
        "v21_vs_v22": _gate_from_pair(pair_v21_v22),
        "v22_vs_v21": _gate_from_pair(pair_v22_v21),
    }
    winner = select_historical_winner(
        bool(gates["v21_vs_control"]["survives"]),
        bool(gates["v22_vs_control"]["survives"]),
        v21_vs_v22_survives=bool(gates["v21_vs_v22"]["survives"]),
        v22_vs_v21_survives=bool(gates["v22_vs_v21"]["survives"]),
    )
    decision = {
        "gates": gates,
        "winner": winner,
        "selection_rule": "frozen preregistered survivor and head-to-head rule",
    }
    (output_dir / "survivor_decision.json").write_text(json.dumps(decision, indent=2, sort_keys=True), encoding="utf-8")
    summary = {
        "status": "CLEAN_V2_OPEN_ALPHA_HISTORICAL_RUN_COMPLETE",
        "models": list(MODEL_ORDER),
        "feature_order_sha256": {model: feature_order_sha256(columns) for model, columns in MODEL_FEATURES.items()},
        "feature_counts": {model: len(columns) for model, columns in MODEL_FEATURES.items()},
        "combined_31_feature_model": {"authorized": False, "status": "PROHIBITED"},
        "hgb_parameters": HGB_PARAMETERS,
        "hgb_preprocessing": HGB_PREPROCESSING,
        "folds": [fold.__dict__ for fold in FROZEN_V2_FOLDS],
        "common_support_rows": int(len(table)),
        "common_support_tickers": int(table["ticker"].nunique()),
        "common_support_key_sha256": stable_key_sha256(table),
        "source_sha256": source_hashes,
        "gates": gates,
        "winner": winner,
        "model_artifact_sha256": model_hashes,
        "runtime_seconds": float(time.perf_counter() - started),
        "historical_boundary": str(HISTORICAL_BOUNDARY.date()),
        "fresh_forward_outcomes_accessed": False,
        "provider_calls": False,
        "canonical_model_overwritten": False,
        "refit_or_promotion_performed": False,
        "tuning_performed": False,
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True, default=str), encoding="utf-8")
    manifest = {
        "schema": "idx-trade/clean-v2-open-alpha-historical-v1",
        "summary_sha256": sha256_file(summary_path),
        "source_sha256": source_hashes,
        "artifact_sha256": _artifact_hashes(output_dir),
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
    }
    manifest_path = output_dir / "artifact_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str), encoding="utf-8")
    manifest_sha = sha256_file(manifest_path)
    (output_dir / "artifact_manifest.sha256").write_text(f"{manifest_sha}  artifact_manifest.json\n", encoding="utf-8")
    return {
        "summary": summary,
        "decision": decision,
        "summary_sha256": sha256_file(summary_path),
        "artifact_manifest_sha256": manifest_sha,
        "artifact_count": len(manifest["artifact_sha256"]),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--common-support-path", type=Path, required=True)
    parser.add_argument("--label-source-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> int:
    result = run_historical_comparison(**vars(_parser().parse_args()))
    print(json.dumps({"status": result["summary"]["status"], "winner": result["summary"]["winner"], "summary_sha256": result["summary_sha256"], "artifact_manifest_sha256": result["artifact_manifest_sha256"], "artifact_count": result["artifact_count"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
