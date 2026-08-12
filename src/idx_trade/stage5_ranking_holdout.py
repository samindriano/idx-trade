from __future__ import annotations

import argparse
import json
import platform
from importlib.metadata import version
from pathlib import Path
from typing import Iterable

import joblib
import numpy as np
import pandas as pd

from .provenance import sha256_file
from .research_baselines import logistic_baseline, prepare_primary_model_table, tree_challenger
from .research_features import build_baseline_features
from .research_labels import BarrierLabelConfig, SL_FIRST, TP_FIRST, build_first_touch_labels
from .research_stage5 import (
    FINAL_TRAIN_SIGNAL_INDEX,
    HOLDOUT_H10_LAST_SIGNAL_INDEX,
    HOLDOUT_H20_LAST_SIGNAL_INDEX,
    HOLDOUT_H5_LAST_SIGNAL_INDEX,
    HOLDOUT_START_INDEX,
    assign_within_date_buckets,
    bucket_summary,
    momentum_ranker,
    pipeline_raw_score,
    ranking_metrics,
    stage5_decision,
    temporal_half_metrics,
)
from .research_validation import normalize_calendar
from .signal_research import validate_signal_research_hlcv, verify_signal_research_snapshot_manifest
from .storage import write_parquet_atomic


FROZEN_PANEL_SHA256 = "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
FROZEN_RESEARCH_MANIFEST_SHA256 = "b703f1f80aa062accfb4387e5c457458c88aec77351e7dd19342b9c45873cd1a"
FROZEN_STAGE4B_SUMMARY_SHA256 = "f9cbce089c21debd6420943ebf5cd647fc41942e4f210964ddbb5d165d10ebb7"
FROZEN_CALENDAR_SHA256 = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
GLOBAL_HOLDOUT_MARKER_FILENAME = "STAGE5_RANKING_V1_HOLDOUT_ACCESS_STARTED.json"
EXPECTED_ENVIRONMENT = {
    "python": "3.13.5",
    "numpy": "2.4.2",
    "pandas": "2.3.3",
    "pyarrow": "23.0.1",
    "scikit-learn": "1.8.0",
}


def _atomic_json(value: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    temporary.replace(path)


def _read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"unsupported table format: {path}")


def _calendar(path: Path, column: str) -> pd.DatetimeIndex:
    if sha256_file(path) != FROZEN_CALENDAR_SHA256:
        raise RuntimeError("frozen official calendar hash mismatch")
    frame = _read_table(path)
    if column not in frame.columns:
        raise ValueError(f"calendar column {column!r} absent from {path}")
    calendar = normalize_calendar(frame[column])
    if len(calendar) != 1260:
        raise RuntimeError(f"expected 1260 official sessions, got {len(calendar)}")
    if pd.Timestamp(calendar[0]) != pd.Timestamp("2021-04-29") or pd.Timestamp(calendar[-1]) != pd.Timestamp("2026-07-31"):
        raise RuntimeError("frozen official calendar boundary mismatch")
    return calendar


def _listing_map(path: Path, ticker_column: str, listed_from_column: str) -> dict[str, object]:
    frame = _read_table(path)
    required = {ticker_column, listed_from_column}
    if not required.issubset(frame.columns):
        raise ValueError(f"security master missing columns: {sorted(required - set(frame.columns))}")
    result: dict[str, object] = {}
    for ticker, listed_from in frame[[ticker_column, listed_from_column]].itertuples(index=False, name=None):
        key = str(ticker).upper().replace(".JK", "").strip()
        if key:
            result[key] = listed_from
    return result


def _environment() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "numpy": version("numpy"),
        "pandas": version("pandas"),
        "pyarrow": version("pyarrow"),
        "scikit-learn": version("scikit-learn"),
    }


def _assert_environment() -> dict[str, str]:
    actual = _environment()
    if actual != EXPECTED_ENVIRONMENT:
        raise RuntimeError(f"Stage-5 numerical environment mismatch: expected={EXPECTED_ENVIRONMENT} actual={actual}")
    return actual


def _verify_manifest(path: Path) -> dict[str, object]:
    if sha256_file(path) != FROZEN_RESEARCH_MANIFEST_SHA256:
        raise RuntimeError("frozen SIGNAL_RESEARCH manifest hash mismatch")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    verification = verify_signal_research_snapshot_manifest(manifest)
    if not bool(verification.get("valid", False)):
        raise RuntimeError(f"research manifest verification failed: {verification}")
    return verification


def _verify_stage4b(path: Path) -> dict[str, object]:
    if sha256_file(path) != FROZEN_STAGE4B_SUMMARY_SHA256:
        raise RuntimeError("frozen Stage-4B summary hash mismatch")
    summary = json.loads(path.read_text(encoding="utf-8"))
    if summary.get("decision") != "STAGE4B_CALIBRATION_STILL_BLOCKED":
        raise RuntimeError("Stage-4B parent status is not the frozen blocked calibration result")
    if bool(summary.get("holdout_outcome_accessed", True)):
        raise RuntimeError("Stage-4B parent does not prove holdout_outcome_accessed=false")
    return summary


def global_holdout_marker_path(panel_path: Path) -> Path:
    """Return the durable one-shot marker beside the immutable research panel."""

    return panel_path.parent / GLOBAL_HOLDOUT_MARKER_FILENAME


def _assert_global_holdout_unused(panel_path: Path) -> None:
    marker = global_holdout_marker_path(panel_path)
    if marker.exists():
        raise RuntimeError(
            f"Stage-5 global holdout marker already exists at {marker}; "
            "RANKING_V1 holdout is consumed and must not be read again"
        )


def _assert_clean_output_dir(output_dir: Path) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError("Stage-5 output directory is not clean; use a new directory before holdout access")
    output_dir.mkdir(parents=True, exist_ok=True)


def _read_panel_until(panel_path: Path, max_date: pd.Timestamp) -> pd.DataFrame:
    if panel_path.suffix.lower() not in {".parquet", ".pq"}:
        raise ValueError("Stage-5 requires the immutable parquet panel")
    try:
        panel = pd.read_parquet(panel_path, filters=[("date", "<=", max_date.to_pydatetime())])
    except Exception as error:
        raise RuntimeError("failed filtered development-panel read; refusing unfiltered fallback before model freeze") from error
    panel["date"] = pd.to_datetime(panel["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if panel.empty or panel["date"].max() > max_date:
        raise RuntimeError("development-panel filter boundary failed")
    if not validate_signal_research_hlcv(panel):
        raise RuntimeError("development panel violates SIGNAL_RESEARCH_HLCV")
    return panel


def _read_full_panel_after_freeze(panel_path: Path) -> pd.DataFrame:
    panel = pd.read_parquet(panel_path)
    panel["date"] = pd.to_datetime(panel["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if not validate_signal_research_hlcv(panel):
        raise RuntimeError("full frozen panel violates SIGNAL_RESEARCH_HLCV")
    return panel


def _fit_final_rankers(train: pd.DataFrame) -> dict[str, object]:
    if train.empty or np.unique(train["binary_target"]).size != 2:
        raise ValueError("final development model table requires both binary classes")
    momentum = momentum_ranker()
    momentum.fit(train[["close_return_20"]], train["binary_target"].to_numpy(dtype=int))
    logistic = logistic_baseline()
    logistic.fit(train, train["binary_target"].to_numpy(dtype=int))
    hgb = tree_challenger()
    hgb.fit(train, train["binary_target"].to_numpy(dtype=int))
    return {
        "momentum_20": momentum,
        "logistic_compact": logistic,
        "hist_gradient_boosting": hgb,
    }


def _freeze_models(
    models: dict[str, object],
    train: pd.DataFrame,
    output_dir: Path,
    *,
    code_commit: str,
    calendar: pd.DatetimeIndex,
) -> tuple[dict[str, str], Path]:
    training_path = output_dir / "stage5_final_training_model_table.parquet"
    write_parquet_atomic(train, training_path)
    hashes: dict[str, str] = {"training_model_table": sha256_file(training_path)}
    model_paths: dict[str, str] = {}
    for name, model in models.items():
        path = output_dir / f"stage5_frozen_{name}.joblib"
        joblib.dump(model, path)
        hashes[f"model_{name}"] = sha256_file(path)
        model_paths[name] = str(path)
    freeze_record = {
        "code_commit": code_commit,
        "final_train_signal_index": FINAL_TRAIN_SIGNAL_INDEX,
        "final_train_signal_date": pd.Timestamp(calendar[FINAL_TRAIN_SIGNAL_INDEX - 1]).date().isoformat(),
        "holdout_start_index": HOLDOUT_START_INDEX,
        "holdout_start_date": pd.Timestamp(calendar[HOLDOUT_START_INDEX - 1]).date().isoformat(),
        "training_rows": int(len(train)),
        "training_positive_rate": float(train["binary_target"].mean()),
        "training_max_date": pd.Timestamp(train["date"].max()).date().isoformat(),
        "model_paths": model_paths,
        "artifact_hashes": hashes,
        "models_frozen_before_holdout_labels": True,
    }
    freeze_path = output_dir / "stage5_preholdout_model_freeze.json"
    _atomic_json(freeze_record, freeze_path)
    hashes["preholdout_model_freeze"] = sha256_file(freeze_path)
    return hashes, freeze_path


def _write_holdout_access_markers(
    output_dir: Path,
    panel_path: Path,
    freeze_path: Path,
    calendar: pd.DatetimeIndex,
) -> tuple[Path, str, Path, str]:
    global_marker = global_holdout_marker_path(panel_path)
    local_marker = output_dir / GLOBAL_HOLDOUT_MARKER_FILENAME
    if global_marker.exists() or local_marker.exists():
        raise RuntimeError("Stage-5 holdout-access marker already exists; refusing a second holdout read")
    marker = {
        "holdout_consumed": True,
        "holdout_consumed_for": "RANKING_V1_ONLY",
        "holdout_start_index": HOLDOUT_START_INDEX,
        "holdout_start_date": pd.Timestamp(calendar[HOLDOUT_START_INDEX - 1]).date().isoformat(),
        "models_frozen_before_holdout_labels": True,
        "preholdout_model_freeze_sha256": sha256_file(freeze_path),
        "rerun_policy": "STOP_FOR_INDEPENDENT_REVIEW_IF_PROCESS_FAILS_AFTER_THIS_MARKER",
    }
    # The durable marker is written first. From this point onward the holdout is
    # conservatively treated as consumed even if a later I/O/runtime failure occurs.
    _atomic_json(marker, global_marker)
    global_sha = sha256_file(global_marker)
    local_payload = dict(marker)
    local_payload["global_marker_path"] = str(global_marker)
    local_payload["global_marker_sha256"] = global_sha
    _atomic_json(local_payload, local_marker)
    return global_marker, global_sha, local_marker, sha256_file(local_marker)


def _label_summary(labels: pd.DataFrame, features: pd.DataFrame, horizon: int) -> pd.DataFrame:
    eligible = features[features["universe_primary_liquid"].astype(bool)][["ticker", "date"]].copy()
    block = labels.merge(eligible, left_on=["ticker", "signal_date"], right_on=["ticker", "date"], how="inner")
    counts = block["label_status"].value_counts(dropna=False).sort_index()
    total = int(len(block))
    return pd.DataFrame(
        [
            {
                "horizon": horizon,
                "label_status": str(status),
                "rows": int(count),
                "share": float(count / total) if total else 0.0,
            }
            for status, count in counts.items()
        ]
    )


def _resolved_holdout_table(features: pd.DataFrame, labels: pd.DataFrame, first_index: int, last_index: int) -> pd.DataFrame:
    primary = features[features["universe_primary_liquid"].astype(bool)].copy()
    primary = primary[primary["session_index_zero"].between(first_index - 1, last_index - 1)].copy()
    resolved = labels[
        labels["signal_session_index"].between(first_index, last_index)
        & labels["label_status"].isin([TP_FIRST, SL_FIRST])
    ].copy()
    joined = primary.merge(
        resolved[["ticker", "signal_date", "signal_session_index", "binary_target", "label_status"]],
        left_on=["ticker", "date"],
        right_on=["ticker", "signal_date"],
        how="inner",
        validate="one_to_one",
    )
    if joined.empty:
        raise ValueError("holdout resolved primary table is empty")
    joined["binary_target"] = joined["binary_target"].astype(int)
    return joined.sort_values(["date", "ticker"]).reset_index(drop=True)


def _score_models(table: pd.DataFrame, models: dict[str, object], train_prevalence: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    scored = table.copy()
    scored["score_base_rate"] = float(train_prevalence)
    scored["score_momentum_20"] = pipeline_raw_score(models["momentum_20"], scored)
    scored["score_logistic_compact"] = pipeline_raw_score(models["logistic_compact"], scored)
    scored["score_hist_gradient_boosting"] = pipeline_raw_score(models["hist_gradient_boosting"], scored)
    metric_rows: list[dict[str, object]] = []
    for name, column in (
        ("base_rate", "score_base_rate"),
        ("momentum_20", "score_momentum_20"),
        ("logistic_compact", "score_logistic_compact"),
        ("hist_gradient_boosting", "score_hist_gradient_boosting"),
    ):
        metrics = ranking_metrics(scored["binary_target"], scored[column])
        metric_rows.append({"model": name, **metrics})
    return scored, pd.DataFrame(metric_rows)


def _sensitivity_metrics(features: pd.DataFrame, labels: pd.DataFrame, model: object, horizon: int, last_index: int) -> dict[str, object]:
    table = _resolved_holdout_table(features, labels, HOLDOUT_START_INDEX, last_index)
    score = pipeline_raw_score(model, table)
    metrics = ranking_metrics(table["binary_target"], score)
    return {"horizon": horizon, **metrics, "pr_auc_delta_vs_base": float(metrics["pr_auc"] - metrics["positive_rate"])}


def run_stage5_ranking_holdout(
    *,
    panel_path: Path,
    research_manifest_path: Path,
    stage4b_summary_path: Path,
    calendar_path: Path,
    security_master_path: Path,
    output_dir: Path,
    code_commit: str,
    calendar_column: str = "date",
    ticker_column: str = "ticker",
    listed_from_column: str = "listed_from",
) -> dict[str, object]:
    if sha256_file(panel_path) != FROZEN_PANEL_SHA256:
        raise RuntimeError("frozen SIGNAL_RESEARCH panel hash mismatch")
    environment = _assert_environment()
    manifest_verification = _verify_manifest(research_manifest_path)
    parent = _verify_stage4b(stage4b_summary_path)
    calendar = _calendar(calendar_path, calendar_column)
    listing_map = _listing_map(security_master_path, ticker_column, listed_from_column)
    _assert_global_holdout_unused(panel_path)
    _assert_clean_output_dir(output_dir)

    # PRE-HOLDOUT PHASE. Only development data through session 1008 is readable.
    development_end = pd.Timestamp(calendar[1007])
    development_panel = _read_panel_until(panel_path, development_end)
    train_feature_end = pd.Timestamp(calendar[FINAL_TRAIN_SIGNAL_INDEX - 1])
    train_features = build_baseline_features(
        development_panel[development_panel["date"] <= train_feature_end].copy(),
        calendar,
        listed_from=listing_map,
    )
    train_labels = build_first_touch_labels(
        development_panel,
        calendar,
        config=BarrierLabelConfig(horizon=10),
        max_signal_session_index=FINAL_TRAIN_SIGNAL_INDEX,
        max_future_session_index=1008,
    )
    train_table = prepare_primary_model_table(train_features, train_labels)
    if train_table["date"].max() > train_feature_end:
        raise RuntimeError("final training table crosses frozen signal boundary")
    models = _fit_final_rankers(train_table)
    preholdout_hashes, freeze_path = _freeze_models(models, train_table, output_dir, code_commit=code_commit, calendar=calendar)
    freeze_record = json.loads(freeze_path.read_text(encoding="utf-8"))
    if not bool(freeze_record.get("models_frozen_before_holdout_labels", False)):
        raise RuntimeError("model freeze record failed before holdout outcome access")

    # HOLDOUT IS IRREVOCABLY CONSUMED FOR RANKING_V1_ONLY AFTER THESE MARKERS.
    global_marker, global_marker_sha, local_marker, local_marker_sha = _write_holdout_access_markers(
        output_dir, panel_path, freeze_path, calendar
    )

    full_panel = _read_full_panel_after_freeze(panel_path)
    features = build_baseline_features(full_panel, calendar, listed_from=listing_map)
    label_configs = {
        5: HOLDOUT_H5_LAST_SIGNAL_INDEX,
        10: HOLDOUT_H10_LAST_SIGNAL_INDEX,
        20: HOLDOUT_H20_LAST_SIGNAL_INDEX,
    }
    labels: dict[int, pd.DataFrame] = {}
    label_summaries: list[pd.DataFrame] = []
    for horizon, last_signal in label_configs.items():
        built = build_first_touch_labels(
            full_panel,
            calendar,
            config=BarrierLabelConfig(horizon=horizon),
            max_signal_session_index=last_signal,
            max_future_session_index=1260,
        )
        built = built[built["signal_session_index"] >= HOLDOUT_START_INDEX].copy()
        labels[horizon] = built
        label_summaries.append(_label_summary(built, features, horizon))

    h10_table = _resolved_holdout_table(features, labels[10], HOLDOUT_START_INDEX, HOLDOUT_H10_LAST_SIGNAL_INDEX)
    scored, model_metrics = _score_models(h10_table, models, float(train_table["binary_target"].mean()))
    metric_map = model_metrics.set_index("model").to_dict(orient="index")

    quintiled = assign_within_date_buckets(
        scored,
        score_column="score_hist_gradient_boosting",
        buckets=5,
        output_column="quintile",
    )
    quintile_summary = bucket_summary(quintiled, bucket_column="quintile")
    deciled = assign_within_date_buckets(
        scored,
        score_column="score_hist_gradient_boosting",
        buckets=10,
        output_column="decile",
    )
    decile_summary = bucket_summary(deciled, bucket_column="decile")
    q = quintile_summary.set_index("bucket")
    q1_rate = float(q.loc[1, "tp_rate"])
    q5_rate = float(q.loc[5, "tp_rate"])
    half = temporal_half_metrics(scored, score_column="score_hist_gradient_boosting")

    decision, decision_checks = stage5_decision(
        hgb_metrics=metric_map["hist_gradient_boosting"],
        momentum_metrics=metric_map["momentum_20"],
        q5_rate=q5_rate,
        q1_rate=q1_rate,
        half_metrics=half,
        models_frozen_before_holdout_labels=True,
    )

    sensitivity = pd.DataFrame(
        [
            _sensitivity_metrics(features, labels[5], models["hist_gradient_boosting"], 5, HOLDOUT_H5_LAST_SIGNAL_INDEX),
            _sensitivity_metrics(features, labels[20], models["hist_gradient_boosting"], 20, HOLDOUT_H20_LAST_SIGNAL_INDEX),
        ]
    )
    outcome_summary = pd.concat(label_summaries, ignore_index=True)

    predictions_path = output_dir / "stage5_h10_ranking_holdout_predictions.parquet"
    metrics_path = output_dir / "stage5_h10_ranking_metrics.csv"
    quintile_path = output_dir / "stage5_h10_quintile_summary.csv"
    decile_path = output_dir / "stage5_h10_decile_summary.csv"
    half_path = output_dir / "stage5_h10_temporal_half_metrics.csv"
    sensitivity_path = output_dir / "stage5_h5_h20_sensitivity_metrics.csv"
    outcome_path = output_dir / "stage5_holdout_outcome_status_summary.csv"
    write_parquet_atomic(
        scored[
            [
                "ticker",
                "date",
                "signal_session_index",
                "binary_target",
                "label_status",
                "score_base_rate",
                "score_momentum_20",
                "score_logistic_compact",
                "score_hist_gradient_boosting",
            ]
        ],
        predictions_path,
    )
    model_metrics.to_csv(metrics_path, index=False)
    quintile_summary.to_csv(quintile_path, index=False)
    decile_summary.to_csv(decile_path, index=False)
    half.to_csv(half_path, index=False)
    sensitivity.to_csv(sensitivity_path, index=False)
    outcome_summary.to_csv(outcome_path, index=False)

    runtime_artifacts = {
        "h10_predictions": predictions_path,
        "h10_metrics": metrics_path,
        "h10_quintiles": quintile_path,
        "h10_deciles": decile_path,
        "h10_temporal_halves": half_path,
        "h5_h20_sensitivity": sensitivity_path,
        "outcome_status_summary": outcome_path,
    }
    runtime_hashes = {name: sha256_file(path) for name, path in runtime_artifacts.items()}

    summary: dict[str, object] = {
        "stage": "STAGE5_RANKING_HOLDOUT_V1",
        "decision": decision,
        "code_commit": code_commit,
        "environment": environment,
        "input_hashes": {
            "panel": FROZEN_PANEL_SHA256,
            "research_manifest": FROZEN_RESEARCH_MANIFEST_SHA256,
            "calendar": FROZEN_CALENDAR_SHA256,
            "stage4b_summary": FROZEN_STAGE4B_SUMMARY_SHA256,
            "security_master": sha256_file(security_master_path),
        },
        "research_manifest_verification": manifest_verification,
        "parent_stage4b_decision": parent.get("decision"),
        "final_train_signal_index": FINAL_TRAIN_SIGNAL_INDEX,
        "final_train_signal_date": train_feature_end.date().isoformat(),
        "training_rows": int(len(train_table)),
        "training_positive_rate": float(train_table["binary_target"].mean()),
        "preholdout_artifact_hashes": preholdout_hashes,
        "models_frozen_before_holdout_labels": True,
        "global_holdout_access_marker": str(global_marker),
        "global_holdout_access_marker_sha256": global_marker_sha,
        "local_holdout_access_marker": str(local_marker),
        "local_holdout_access_marker_sha256": local_marker_sha,
        "holdout_start_index": HOLDOUT_START_INDEX,
        "holdout_start_date": pd.Timestamp(calendar[HOLDOUT_START_INDEX - 1]).date().isoformat(),
        "h10_last_evaluable_signal_index": HOLDOUT_H10_LAST_SIGNAL_INDEX,
        "h10_last_evaluable_signal_date": pd.Timestamp(calendar[HOLDOUT_H10_LAST_SIGNAL_INDEX - 1]).date().isoformat(),
        "holdout_consumed": True,
        "holdout_consumed_for": "RANKING_V1_ONLY",
        "holdout_outcome_accessed": True,
        "probability_v1_status": "PROBABILITY_V1_NOT_READY_DEFERRED",
        "probability_v2_validation_policy": "FRESH_FORWARD_DATA_STRICTLY_AFTER_2026_07_31",
        "h10_model_metrics": model_metrics.to_dict(orient="records"),
        "h10_q5_minus_q1": q5_rate - q1_rate,
        "h10_q5_lift_vs_overall": q5_rate - float(scored["binary_target"].mean()),
        "h10_top_decile_rate": float(decile_summary.set_index("bucket").loc[10, "tp_rate"]),
        "h10_top_decile_lift_vs_overall": float(decile_summary.set_index("bucket").loc[10, "lift_vs_overall"]),
        "temporal_half_metrics": half.to_dict(orient="records"),
        "decision_checks": decision_checks,
        "sensitivity_metrics": sensitivity.to_dict(orient="records"),
        "outcome_status_summary": outcome_summary.to_dict(orient="records"),
        "runtime_artifact_hashes": runtime_hashes,
    }
    summary_path = output_dir / "stage5_ranking_holdout_summary.json"
    _atomic_json(summary, summary_path)
    summary["summary_path"] = str(summary_path)
    summary["summary_sha256"] = sha256_file(summary_path)
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Consume the frozen holdout once for Stage-5 ranking V1 only")
    parser.add_argument("--panel", required=True, type=Path)
    parser.add_argument("--research-manifest", required=True, type=Path)
    parser.add_argument("--stage4b-summary", required=True, type=Path)
    parser.add_argument("--calendar", required=True, type=Path)
    parser.add_argument("--security-master", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--code-commit", required=True)
    parser.add_argument("--calendar-column", default="date")
    parser.add_argument("--ticker-column", default="ticker")
    parser.add_argument("--listed-from-column", default="listed_from")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    summary = run_stage5_ranking_holdout(
        panel_path=args.panel,
        research_manifest_path=args.research_manifest,
        stage4b_summary_path=args.stage4b_summary,
        calendar_path=args.calendar,
        security_master_path=args.security_master,
        output_dir=args.output_dir,
        code_commit=args.code_commit,
        calendar_column=args.calendar_column,
        ticker_column=args.ticker_column,
        listed_from_column=args.listed_from_column,
    )
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
