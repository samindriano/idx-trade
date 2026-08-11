"""Frozen historical-development experiment for the OHLCV O1 challenger family.

The runner deliberately consumes the already-certified V3-B training table and
the Open coverage-gate artifact. It does not build features, fetch data, or
touch any forward outcome store.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from .research_features import assert_no_open_dependency
from .research_stage5 import assign_within_date_buckets, bucket_summary, ranking_metrics


V3_B_HYPOTHESIS_ID = "V3-B-STRUCTURE-LITE-V1"
V3_B_CANDIDATE = "V3-B-STRUCTURE-LITE-V1-CANDIDATE-005"

V3_B_FEATURE_COLUMNS = (
    "xs_rank_close_return_5",
    "xs_rank_close_return_20",
    "xs_rank_atr14_over_close",
    "xs_rank_close_position_20",
    "xs_rank_distance_high_20_atr",
    "xs_rank_distance_low_20_atr",
    "xs_rank_distance_high_60_atr",
    "xs_rank_distance_low_60_atr",
    "xs_rank_relative_volume_20",
    "xs_rank_log_regular_value_relative_20",
    "market_primary_liquid_count",
    "market_breadth_return_5_positive",
    "market_breadth_return_20_positive",
    "market_median_close_return_5",
    "market_median_close_return_20",
    "market_median_atr14_over_close",
    "market_median_close_position_20",
    "market_median_relative_volume_20",
    "market_median_log_regular_value_relative_20",
    "market_relative_close_return_5",
    "market_relative_close_return_20",
    "market_relative_atr14_over_close",
    "market_relative_close_position_20",
    "market_relative_relative_volume_20",
    "market_relative_log_regular_value_relative_20",
    "structure_support_distance_atr",
    "structure_resistance_distance_atr",
    "structure_support_touch_count_60",
    "structure_resistance_touch_count_60",
    "structure_nearest_level_age_sessions",
    "structure_role_reversal_count_120",
    "structure_breakout_retest_state",
    "structure_breakout_volume_confirmed",
)

OPEN_FEATURES = ("overnight_gap", "intraday_return")
MODEL_FEATURES = {
    "V3B_COMMON_SUPPORT_BASELINE": V3_B_FEATURE_COLUMNS,
    "O1A_OVERNIGHT": (*V3_B_FEATURE_COLUMNS, "overnight_gap"),
    "O1B_INTRADAY": (*V3_B_FEATURE_COLUMNS, "intraday_return"),
    "O1C_DECOMPOSITION": (*V3_B_FEATURE_COLUMNS, *OPEN_FEATURES),
}
MODEL_ORDER = tuple(MODEL_FEATURES)

RANDOM_SEED = 42
TREE_LEARNING_RATE = 0.05
TREE_MAX_ITER = 200
TREE_MAX_LEAF_NODES = 31
TREE_L2 = 1.0
HGB_PARAMS = {
    "learning_rate": TREE_LEARNING_RATE,
    "max_iter": TREE_MAX_ITER,
    "max_leaf_nodes": TREE_MAX_LEAF_NODES,
    "l2_regularization": TREE_L2,
    "random_state": RANDOM_SEED,
}

EXPECTED_V3_B_FEATURE_ORDER_SHA256 = "100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e"
EXPECTED_COMMON_SUPPORT_ROWS = 278_168
EXPECTED_COMMON_SUPPORT_SOURCE_ROWS = 292_633
EXPECTED_TRAINING_TABLE_SHA256 = "5893c9f2872aae0f33acd4104d82ee8c1d4474aae7d54e9d01879724b86dffbe"
EXPECTED_TRAINING_MANIFEST_SHA256 = "4e84ce02c6ee856c0f260dd6099b2a479723c53da82131ae669e0bf7e4d384f9"
EXPECTED_PANEL_SHA256 = "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
EXPECTED_CALENDAR_SHA256 = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
EXPECTED_SECURITY_MASTER_SHA256 = "9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9"
EXPECTED_ACCEPTED_OPEN_PANEL_SHA256 = "a1dae0714971904b266a380be6bb96a2a4976068c9d60c54c8c43746826f7cab"
EXPECTED_ACCEPTED_OPEN_PROVENANCE_SHA256 = "90deaad64ff3330921859eb222df556794c345bb3d440df89edab8ef6d342687"


@dataclass(frozen=True)
class RankingV2Fold:
    name: str
    train_start: int
    train_end: int
    gap_start: int
    gap_end: int
    validation_start: int
    validation_end: int


RANKING_V2_FOLDS = (
    RankingV2Fold("V2F1", 1, 504, 505, 524, 525, 624),
    RankingV2Fold("V2F2", 1, 624, 625, 644, 645, 744),
    RankingV2Fold("V2F3", 1, 744, 745, 764, 765, 864),
    RankingV2Fold("V2F4", 1, 864, 865, 884, 885, 984),
    RankingV2Fold("V2F5", 1, 984, 985, 1004, 1005, 1104),
    RankingV2Fold("V2F6", 1, 1104, 1105, 1124, 1125, 1224),
)


def feature_order_hash(columns: Sequence[str]) -> str:
    payload = json.dumps(list(columns), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normal_date(values: pd.Series) -> pd.Series:
    dates = pd.to_datetime(values, errors="coerce")
    if getattr(dates.dt, "tz", None) is not None:
        dates = dates.dt.tz_localize(None)
    return dates.dt.normalize()


def _stable_key_hash(frame: pd.DataFrame) -> str:
    keys = frame[["ticker", "date", "signal_session_index"]].copy()
    keys["ticker"] = keys["ticker"].astype(str)
    keys["date"] = _normal_date(keys["date"]).dt.strftime("%Y-%m-%d")
    keys["signal_session_index"] = pd.to_numeric(keys["signal_session_index"], errors="raise").astype(int)
    lines = keys.sort_values(["ticker", "date", "signal_session_index"], kind="mergesort").astype(str).agg("|".join, axis=1)
    return hashlib.sha256(("\n".join(lines.tolist()) + "\n").encode("utf-8")).hexdigest()


def _verify_file(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"{label} missing: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"{label} SHA-256 mismatch: expected {expected}, got {actual}")
    return actual


def verify_v3_b_feature_order(manifest: dict[str, object]) -> None:
    manifest_columns = tuple(manifest.get("feature_columns", ()))
    if manifest_columns != V3_B_FEATURE_COLUMNS:
        raise RuntimeError("V3-B feature order differs from the frozen final manifest")
    actual = feature_order_hash(V3_B_FEATURE_COLUMNS)
    if actual != EXPECTED_V3_B_FEATURE_ORDER_SHA256 or manifest.get("feature_order_sha256") != actual:
        raise RuntimeError("V3-B feature-order hash mismatch")
    assert_no_open_dependency(V3_B_FEATURE_COLUMNS)


def verify_h10_labels(training: pd.DataFrame) -> dict[str, object]:
    required = {"label_status", "binary_target"}
    if not required.issubset(training.columns):
        raise RuntimeError(f"H10 training table missing {sorted(required - set(training.columns))}")
    statuses = set(training["label_status"].dropna().astype(str))
    if statuses != {"TP_FIRST", "SL_FIRST"}:
        raise RuntimeError(f"unexpected H10 statuses: {sorted(statuses)}")
    mapping = training.groupby("label_status")["binary_target"].unique().to_dict()
    if set(mapping.get("TP_FIRST", ())) != {1} or set(mapping.get("SL_FIRST", ())) != {0}:
        raise RuntimeError(f"H10 target mapping mismatch: {mapping}")
    return {
        "horizon": 10,
        "positive_label": "TP_FIRST",
        "negative_label": "SL_FIRST",
        "target_mapping": {"TP_FIRST": 1, "SL_FIRST": 0},
        "rows": int(len(training)),
        "status_counts": {str(k): int(v) for k, v in training["label_status"].value_counts().sort_index().items()},
    }


def verify_fold_contract() -> list[dict[str, int | str]]:
    previous_validation_end = 0
    output: list[dict[str, int | str]] = []
    for fold in RANKING_V2_FOLDS:
        if fold.train_start != 1 or fold.gap_start != fold.train_end + 1:
            raise RuntimeError(f"{fold.name} expanding/purge boundary mismatch")
        if fold.gap_end - fold.gap_start + 1 != 20:
            raise RuntimeError(f"{fold.name} purge is not H20")
        if fold.validation_start != fold.gap_end + 1 or fold.validation_end - fold.validation_start + 1 != 100:
            raise RuntimeError(f"{fold.name} validation window mismatch")
        if fold.train_end + 20 >= fold.validation_start:
            raise RuntimeError(f"{fold.name} H20 label path overlaps validation")
        if previous_validation_end and fold.validation_start <= previous_validation_end:
            raise RuntimeError("six validation windows overlap")
        previous_validation_end = fold.validation_end
        output.append(asdict(fold))
    return output


def hgb_pipeline(feature_columns: Sequence[str]) -> Pipeline:
    columns = tuple(feature_columns)
    if columns not in MODEL_FEATURES.values():
        raise ValueError("unknown frozen O1 feature set")
    assert_no_open_dependency(columns[: len(V3_B_FEATURE_COLUMNS)])
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


def raw_score(model: Pipeline, frame: pd.DataFrame) -> np.ndarray:
    transformed = model.named_steps["preprocess"].transform(frame)
    estimator = model.named_steps["model"]
    if hasattr(estimator, "decision_function"):
        scores = estimator.decision_function(transformed)
        return np.asarray(scores, dtype=float)
    probability = np.asarray(estimator.predict_proba(transformed)[:, 1], dtype=float)
    clipped = np.clip(probability, 1e-9, 1.0 - 1e-9)
    return np.log(clipped / (1.0 - clipped))


def evaluate_scores(validation: pd.DataFrame, scores: np.ndarray) -> dict[str, float]:
    metrics = ranking_metrics(validation["binary_target"].astype(int), scores)
    scored = validation[["ticker", "date", "binary_target"]].copy()
    scored["score"] = np.asarray(scores, dtype=float)
    quintiled = assign_within_date_buckets(scored, score_column="score", buckets=5, output_column="quintile")
    q = bucket_summary(quintiled, bucket_column="quintile").set_index("bucket")
    deciled = assign_within_date_buckets(scored, score_column="score", buckets=10, output_column="decile")
    d = bucket_summary(deciled, bucket_column="decile").set_index("bucket")
    return {
        **metrics,
        "pr_auc_minus_prevalence": float(metrics["pr_auc"] - metrics["positive_rate"]),
        "q1_tp_rate": float(q.loc[1, "tp_rate"]),
        "q5_tp_rate": float(q.loc[5, "tp_rate"]),
        "q5_minus_q1": float(q.loc[5, "tp_rate"] - q.loc[1, "tp_rate"]),
        "top_decile_tp_rate": float(d.loc[10, "tp_rate"]),
        "top_decile_lift": float(d.loc[10, "tp_rate"] - metrics["positive_rate"]),
    }


def load_common_support(
    *,
    coverage_path: Path,
    training_table_path: Path,
    training_manifest_path: Path,
) -> tuple[pd.DataFrame, dict[str, object]]:
    _verify_file(training_table_path, EXPECTED_TRAINING_TABLE_SHA256, "V3-B training table")
    _verify_file(training_manifest_path, EXPECTED_TRAINING_MANIFEST_SHA256, "V3-B final manifest")
    manifest = json.loads(training_manifest_path.read_text(encoding="utf-8"))
    verify_v3_b_feature_order(manifest)
    if manifest.get("architecture") != f"{V3_B_HYPOTHESIS_ID}-CANDIDATE-005":
        raise RuntimeError("unexpected V3-B architecture identity")
    if manifest.get("fresh_forward_outcomes_accessed") is not False or manifest.get("forward_outcome_access_marker_written") is not False:
        raise RuntimeError("V3-B manifest permits fresh-forward access")
    training = pd.read_parquet(training_table_path)
    if len(training) != EXPECTED_COMMON_SUPPORT_SOURCE_ROWS:
        raise RuntimeError(f"unexpected V3-B training rows: {len(training)}")
    if training.duplicated(["ticker", "date"]).any():
        raise RuntimeError("V3-B training table has duplicate ticker/date rows")
    training["date"] = _normal_date(training["date"])
    label_contract = verify_h10_labels(training)

    coverage = pd.read_csv(coverage_path, parse_dates=["date"])
    if len(coverage) != EXPECTED_COMMON_SUPPORT_SOURCE_ROWS:
        raise RuntimeError(f"unexpected coverage-gate rows: {len(coverage)}")
    if coverage.duplicated(["ticker", "date"]).any():
        raise RuntimeError("coverage-gate rows have duplicate ticker/date keys")
    ready = coverage[coverage["open_feature_ready"].astype(bool)].copy()
    if len(ready) != EXPECTED_COMMON_SUPPORT_ROWS:
        raise RuntimeError(f"unexpected common-support rows: {len(ready)}")
    if ready[["overnight_gap", "intraday_return"]].isna().any().any():
        raise RuntimeError("common-support Open decomposition contains missing features")
    ready["date"] = _normal_date(ready["date"])
    merged = training.merge(
        ready[["ticker", "date", "signal_session_index", "overnight_gap", "intraday_return"]],
        on=["ticker", "date"],
        how="inner",
        validate="one_to_one",
        suffixes=("", "_coverage"),
    )
    if len(merged) != len(ready):
        raise RuntimeError(f"common-support join lost rows: {len(merged)} vs {len(ready)}")
    if not (merged["signal_session_index"].astype(int) == merged["signal_session_index_coverage"].astype(int)).all():
        raise RuntimeError("common-support signal-session identities disagree")
    merged = merged.drop(columns=["signal_session_index_coverage"])
    merged["signal_session_index"] = pd.to_numeric(merged["signal_session_index"], errors="raise").astype(int)
    if merged["date"].max() > pd.Timestamp("2026-07-31"):
        raise RuntimeError("historical-development table contains post-2026-07-31 rows")
    support_sha = _stable_key_hash(merged)
    contract = {
        "v3_b_hypothesis_id": V3_B_HYPOTHESIS_ID,
        "v3_b_candidate": V3_B_CANDIDATE,
        "training_table_sha256": EXPECTED_TRAINING_TABLE_SHA256,
        "training_manifest_sha256": EXPECTED_TRAINING_MANIFEST_SHA256,
        "coverage_gate_sha256": sha256_file(coverage_path),
        "common_support_rows": int(len(merged)),
        "common_support_tickers": int(merged["ticker"].nunique()),
        "common_support_key_sha256": support_sha,
        "h10_labels": label_contract,
        "v3_b_feature_columns": list(V3_B_FEATURE_COLUMNS),
        "v3_b_feature_order_sha256": feature_order_hash(V3_B_FEATURE_COLUMNS),
        "hgb_parameters": HGB_PARAMS,
        "folds": verify_fold_contract(),
        "training_date_max": merged["date"].max().date().isoformat(),
        "fresh_forward_outcomes_accessed": False,
    }
    return merged.sort_values(["signal_session_index", "ticker"], kind="mergesort").reset_index(drop=True), contract


def _aggregate_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for model_name, block in metrics.groupby("model", sort=True):
        rows.append(
            {
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
            }
        )
    return pd.DataFrame(rows).sort_values("model").reset_index(drop=True)


def _survivor_decision(metrics: pd.DataFrame, aggregate: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    baseline = aggregate[aggregate["model"].eq("V3B_COMMON_SUPPORT_BASELINE")].iloc[0]
    rows: list[dict[str, object]] = []
    for model_name in MODEL_ORDER[1:]:
        block = metrics[metrics["model"].eq(model_name)].sort_values("fold")
        deltas = block["paired_pr_auc_vs_baseline"].to_numpy(dtype=float)
        candidate = aggregate[aggregate["model"].eq(model_name)].iloc[0]
        median = float(np.median(deltas))
        q25 = float(np.quantile(deltas, 0.25))
        positive_folds = int(np.sum(deltas > 0.0))
        guardrail_reversal = bool(
            candidate["median_roc_auc"] < baseline["median_roc_auc"]
            and candidate["median_q5_minus_q1"] < baseline["median_q5_minus_q1"]
        )
        rows.append(
            {
                "model": model_name,
                "median_paired_pr_auc": median,
                "q25_paired_pr_auc": q25,
                "positive_paired_folds": positive_folds,
                "not_one_isolated_fold_spike": positive_folds >= 2,
                "aggregate_ranking_guardrail_reversal": guardrail_reversal,
                "survivor": bool(median > 0.0 and q25 > 0.0 and positive_folds >= 2 and not guardrail_reversal),
            }
        )
    decision = pd.DataFrame(rows).sort_values("model").reset_index(drop=True)
    return ("O1_SURVIVOR" if decision["survivor"].any() else "O1_NO_SURVIVOR"), decision


def _era_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (model, year), block in predictions.groupby(["model", "year"], sort=True):
        if block["binary_target"].nunique() < 2:
            rows.append({"model": model, "year": int(year), "rows": int(len(block)), "positive_rate": float(block["binary_target"].mean()), "pr_auc": np.nan, "roc_auc": np.nan})
            continue
        m = ranking_metrics(block["binary_target"], block["score"])
        rows.append({"model": model, "year": int(year), "rows": int(len(block)), "positive_rate": float(m["positive_rate"]), "pr_auc": float(m["pr_auc"]), "roc_auc": float(m["roc_auc"])})
    return pd.DataFrame(rows)


def run_experiment(
    *,
    coverage_path: Path,
    training_table_path: Path,
    training_manifest_path: Path,
    output_dir: Path,
    immutable_panel_path: Path,
    calendar_path: Path,
    security_master_path: Path,
    accepted_open_panel_path: Path,
    accepted_open_provenance_path: Path,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    contract = {}
    for label, path, expected in (
        ("immutable_panel", immutable_panel_path, EXPECTED_PANEL_SHA256),
        ("official_calendar", calendar_path, EXPECTED_CALENDAR_SHA256),
        ("security_master", security_master_path, EXPECTED_SECURITY_MASTER_SHA256),
        ("accepted_open_panel", accepted_open_panel_path, EXPECTED_ACCEPTED_OPEN_PANEL_SHA256),
        ("accepted_open_provenance", accepted_open_provenance_path, EXPECTED_ACCEPTED_OPEN_PROVENANCE_SHA256),
    ):
        contract[f"{label}_path"] = str(path)
        contract[f"{label}_sha256"] = _verify_file(path, expected, label)
    support, support_contract = load_common_support(
        coverage_path=coverage_path,
        training_table_path=training_table_path,
        training_manifest_path=training_manifest_path,
    )
    contract.update(support_contract)
    if contract["common_support_rows"] != EXPECTED_COMMON_SUPPORT_ROWS:
        raise RuntimeError("frozen common-support population is not exactly 278,168 rows")
    pd.DataFrame(
        {
            "ticker": support["ticker"],
            "date": support["date"].dt.strftime("%Y-%m-%d"),
            "signal_session_index": support["signal_session_index"],
        }
    ).sort_values(["ticker", "date"], kind="mergesort").to_csv(output_dir / "common_support_rows.csv", index=False)
    (output_dir / "preflight_contract.json").write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "fold_definitions.json").write_text(json.dumps(contract["folds"], indent=2), encoding="utf-8")
    (output_dir / "feature_manifest.json").write_text(json.dumps({"models": {k: list(v) for k, v in MODEL_FEATURES.items()}, "hashes": {k: feature_order_hash(v) for k, v in MODEL_FEATURES.items()}, "hgb_parameters": HGB_PARAMS}, indent=2, sort_keys=True), encoding="utf-8")

    metric_rows: list[dict[str, object]] = []
    prediction_frames: list[pd.DataFrame] = []
    start = time.perf_counter()
    for fold in RANKING_V2_FOLDS:
        train = support[support["signal_session_index"].between(fold.train_start, fold.train_end)].copy()
        validation = support[support["signal_session_index"].between(fold.validation_start, fold.validation_end)].copy()
        if train.empty or validation.empty or train["binary_target"].nunique() != 2 or validation["binary_target"].nunique() != 2:
            raise RuntimeError(f"{fold.name} does not have a valid common-support train/validation set")
        fold_scores: dict[str, np.ndarray] = {}
        for model_name in MODEL_ORDER:
            model_start = time.perf_counter()
            columns = MODEL_FEATURES[model_name]
            model = hgb_pipeline(columns)
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
            prediction_frames.append(pd.DataFrame({"model": model_name, "fold": fold.name, "ticker": validation["ticker"].to_numpy(), "date": validation["date"].to_numpy(), "signal_session_index": validation["signal_session_index"].to_numpy(), "binary_target": validation["binary_target"].to_numpy(), "score": scores}))
        baseline_pr = float(evaluate_scores(validation, fold_scores["V3B_COMMON_SUPPORT_BASELINE"])["pr_auc"])
        for row in metric_rows[-len(MODEL_ORDER):]:
            if row["model"] != "V3B_COMMON_SUPPORT_BASELINE":
                row["paired_pr_auc_vs_baseline"] = float(row["pr_auc"] - baseline_pr)
    metrics = pd.DataFrame(metric_rows)
    aggregate = _aggregate_metrics(metrics)
    decision, survivor_table = _survivor_decision(metrics, aggregate)
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
    for path in sorted(output_dir.iterdir()):
        if path.name != "artifact_manifest.json" and path.is_file():
            artifacts[path.name] = sha256_file(path)
    manifest = {
        "schema": "idx-trade/ohlcv-o1-research-artifacts-v1",
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
    parser.add_argument("--coverage-path", type=Path, required=True)
    parser.add_argument("--training-table-path", type=Path, required=True)
    parser.add_argument("--training-manifest-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--immutable-panel-path", type=Path, required=True)
    parser.add_argument("--calendar-path", type=Path, required=True)
    parser.add_argument("--security-master-path", type=Path, required=True)
    parser.add_argument("--accepted-open-panel-path", type=Path, required=True)
    parser.add_argument("--accepted-open-provenance-path", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    result = run_experiment(**vars(args))
    print(json.dumps({k: result[k] for k in ("status", "common_support_rows", "fold_count", "training_runtime_seconds", "artifact_manifest_sha256", "artifact_count")}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
