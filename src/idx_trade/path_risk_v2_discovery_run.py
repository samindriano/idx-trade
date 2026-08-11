"""Frozen Path Risk V2 F1-F4 development runner.

The runner consumes only the immutable PR-001 F1-F4 joined model table (max
signal session 984) plus the official calendar. It evaluates exactly PR-002 and
PR-003 and cannot access Path Risk F5/F6 or fresh-forward outcomes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Sequence

import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.linear_model import LogisticRegression

from .path_risk_v2 import (
    PATH_RISK_V2_CALENDAR_SHA256,
    PATH_RISK_V2_DISCOVERY_FOLDS,
    PATH_RISK_V2_FEATURE_COLUMNS,
    PATH_RISK_V2_FEATURE_ORDER_SHA256,
    PATH_RISK_V2_HORIZON,
    PATH_RISK_V2_MAX_SIGNAL_SESSION,
    PATH_RISK_V2_MODEL_TABLE_ROWS,
    PATH_RISK_V2_SPEC_GIT_BLOB,
    PATH_RISK_V2_STATUSES,
    PATH_RISK_V2_V1_MODEL_TABLE_SHA256,
    PR002_CANDIDATE,
    PR003_CANDIDATE,
    add_competing_risk_event_metadata,
    add_stop_touch_target,
    build_pr002_model,
    build_pr003_model,
    expand_competing_risk_training,
    predict_pr002_probability,
    probability_metrics,
    relative_improvement,
    score_pr003_cumulative_risk,
    select_path_risk_v2_candidate,
)
from .provenance import sha256_file, write_manifest_atomic
from .ranking_v3_structure_lite import _structure_model
from .research_v2_models import pointwise_raw_score
from .research_v2_validation import RANKING_V2_FOLDS, RankingV2Fold


RUN_STATUS = "PATH_RISK_V2_DISCOVERY_F1_F4_COMPLETE"
ALPHA_BASELINE = "FOLD_V3_B_ALPHA_ONLY_LOGIT"
BASE_RATE_BASELINE = "TRAIN_STOP_TOUCH_BASE_RATE"


def _assert_new_or_empty(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise RuntimeError(f"Path Risk V2 output directory must be new or empty: {path}")
    path.mkdir(parents=True, exist_ok=True)


def _normalized_git_blob_sha1(path: Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    payload = text.encode("utf-8")
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload, usedforsecurity=False).hexdigest()


def _assert_spec(path: Path) -> str:
    actual = _normalized_git_blob_sha1(path)
    if actual != PATH_RISK_V2_SPEC_GIT_BLOB:
        raise RuntimeError(
            f"Path Risk V2 spec Git blob mismatch: expected={PATH_RISK_V2_SPEC_GIT_BLOB} actual={actual}"
        )
    return actual


def _read_calendar(path: Path) -> pd.DatetimeIndex:
    if sha256_file(path) != PATH_RISK_V2_CALENDAR_SHA256:
        raise RuntimeError("Path Risk V2 calendar SHA mismatch")
    frame = pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_parquet(path)
    columns = [column for column in ("date", "session_date", "trading_date") if column in frame.columns]
    if len(columns) != 1:
        raise ValueError(f"Path Risk V2 calendar requires one date column, got {columns}")
    dates = pd.to_datetime(frame[columns[0]], errors="coerce")
    sessions = pd.DatetimeIndex(dates).tz_localize(None).normalize().dropna().unique().sort_values()
    if len(sessions) < PATH_RISK_V2_MAX_SIGNAL_SESSION + PATH_RISK_V2_HORIZON:
        raise RuntimeError("Path Risk V2 calendar does not cover discovery H10 endpoint")
    return sessions


def _feature_order_hash(columns: Sequence[str]) -> str:
    payload = json.dumps(list(columns), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _read_v1_model_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() not in {".parquet", ".pq"}:
        raise ValueError("Path Risk V2 requires the frozen V1 Parquet model table")
    if sha256_file(path) != PATH_RISK_V2_V1_MODEL_TABLE_SHA256:
        raise RuntimeError("Path Risk V2 V1-model-table SHA mismatch")
    columns = [
        "ticker",
        "date",
        "signal_session_index",
        "label_status",
        "first_barrier_date",
        "adverse_excursion_r",
        *PATH_RISK_V2_FEATURE_COLUMNS,
    ]
    schema_columns = list(pq.ParquetFile(path).schema.names)
    if schema_columns != columns:
        raise RuntimeError(
            "Path Risk V2 model-table schema mismatch: "
            f"expected exact columns/order={columns} actual={schema_columns}"
        )
    frame = pd.read_parquet(path, columns=columns)
    if len(frame) != PATH_RISK_V2_MODEL_TABLE_ROWS:
        raise RuntimeError(
            f"Path Risk V2 model-table row mismatch: expected={PATH_RISK_V2_MODEL_TABLE_ROWS} actual={len(frame)}"
        )
    if _feature_order_hash(PATH_RISK_V2_FEATURE_COLUMNS) != PATH_RISK_V2_FEATURE_ORDER_SHA256:
        raise RuntimeError("Path Risk V2 frozen feature-order hash mismatch")
    frame = frame.copy()
    frame["ticker"] = frame["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    frame["signal_session_index"] = pd.to_numeric(frame["signal_session_index"], errors="raise").astype(int)
    if frame["date"].isna().any() or frame.duplicated(["ticker", "date"]).any():
        raise RuntimeError("Path Risk V2 model table has invalid/duplicate identities")
    if int(frame["signal_session_index"].max()) > PATH_RISK_V2_MAX_SIGNAL_SESSION:
        raise RuntimeError("Path Risk V2 model table materialized session 985+")
    if set(frame["label_status"].astype(str).unique()) - PATH_RISK_V2_STATUSES:
        raise RuntimeError("Path Risk V2 model table contains unsupported statuses")
    for column in PATH_RISK_V2_FEATURE_COLUMNS:
        values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
        if np.isinf(values).any():
            raise RuntimeError(f"Path Risk V2 feature contains infinity: {column}")
    return frame.sort_values(["signal_session_index", "ticker"], kind="mergesort").reset_index(drop=True)


def _folds() -> tuple[RankingV2Fold, ...]:
    folds = tuple(fold for fold in RANKING_V2_FOLDS if fold.name in PATH_RISK_V2_DISCOVERY_FOLDS)
    if tuple(fold.name for fold in folds) != PATH_RISK_V2_DISCOVERY_FOLDS:
        raise RuntimeError("Path Risk V2 discovery fold identity mismatch")
    if max(fold.validation_end for fold in folds) != PATH_RISK_V2_MAX_SIGNAL_SESSION:
        raise RuntimeError("Path Risk V2 discovery fold escaped session 984")
    return folds


def _split(table: pd.DataFrame, fold: RankingV2Fold) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = table[table["signal_session_index"].between(fold.train_start, fold.train_end)].copy()
    validation = table[
        table["signal_session_index"].between(fold.validation_start, fold.validation_end)
    ].copy()
    if train.empty or validation.empty:
        raise RuntimeError(f"{fold.name} has empty Path Risk V2 train/validation rows")
    if np.unique(train["stop_touch_h10"].to_numpy(dtype=int)).size != 2:
        raise RuntimeError(f"{fold.name} Path Risk V2 training requires both stop-touch classes")
    if np.unique(validation["stop_touch_h10"].to_numpy(dtype=int)).size != 2:
        raise RuntimeError(f"{fold.name} Path Risk V2 validation requires both stop-touch classes")
    return train, validation


def _scored_frame(
    validation: pd.DataFrame,
    probability: np.ndarray,
    *,
    column: str = "prediction",
) -> pd.DataFrame:
    scored = validation[
        [
            "ticker",
            "date",
            "signal_session_index",
            "label_status",
            "adverse_excursion_r",
            "stop_touch_h10",
        ]
    ].copy()
    scored[column] = np.asarray(probability, dtype=float)
    return scored


def _base_rate_predictions(train: pd.DataFrame, validation: pd.DataFrame) -> np.ndarray:
    prevalence = float(train["stop_touch_h10"].mean())
    if not 0.0 < prevalence < 1.0:
        raise RuntimeError("Path Risk V2 training base rate must be strictly between 0 and 1")
    return np.full(len(validation), prevalence, dtype=float)


def _fit_alpha_only_baseline(
    train: pd.DataFrame,
    validation: pd.DataFrame,
) -> tuple[np.ndarray, dict[str, Any]]:
    resolved = train[train["label_status"].isin(["TP_FIRST", "SL_FIRST"])].copy()
    alpha_target = resolved["label_status"].eq("TP_FIRST").astype(int).to_numpy()
    if len(resolved) == 0 or np.unique(alpha_target).size != 2:
        raise RuntimeError("Path Risk V2 alpha baseline requires resolved TP/SL training rows")
    alpha_model = _structure_model()
    alpha_model.fit(resolved, alpha_target)
    train_score = pointwise_raw_score(alpha_model, train)
    validation_score = pointwise_raw_score(alpha_model, validation)
    mapper = LogisticRegression(C=1_000_000.0, solver="lbfgs", max_iter=1000)
    mapper.fit(train_score.reshape(-1, 1), train["stop_touch_h10"].to_numpy(dtype=int))
    probability = mapper.predict_proba(validation_score.reshape(-1, 1))[:, 1]
    if not np.isfinite(probability).all() or (probability <= 0).any() or (probability >= 1).any():
        raise RuntimeError("Path Risk V2 alpha baseline produced invalid probabilities")
    return probability, {"alpha_model": alpha_model, "stop_mapping": mapper}


def _candidate_metric_row(
    *,
    fold: str,
    candidate: str,
    candidate_metrics: dict[str, Any],
    base_metrics: dict[str, Any],
    alpha_metrics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "fold": fold,
        "candidate": candidate,
        **candidate_metrics,
        "relative_logloss_improvement_vs_base": relative_improvement(
            base_metrics["log_loss"], candidate_metrics["log_loss"]
        ),
        "relative_brier_improvement_vs_base": relative_improvement(
            base_metrics["brier"], candidate_metrics["brier"]
        ),
        "relative_logloss_improvement_vs_alpha": relative_improvement(
            alpha_metrics["log_loss"], candidate_metrics["log_loss"]
        ),
        "relative_brier_improvement_vs_alpha": relative_improvement(
            alpha_metrics["brier"], candidate_metrics["brier"]
        ),
    }


def run_discovery(
    *,
    v1_model_table_path: Path,
    calendar_path: Path,
    spec_path: Path,
    output_dir: Path,
    code_commit: str,
) -> dict[str, Any]:
    _assert_new_or_empty(output_dir)
    total_started = time.perf_counter()
    profiling: dict[str, Any] = {}
    spec_blob = _assert_spec(spec_path)

    stage = time.perf_counter()
    table = _read_v1_model_table(v1_model_table_path)
    sessions = _read_calendar(calendar_path)
    table = add_competing_risk_event_metadata(add_stop_touch_target(table), sessions)
    profiling["read_and_validate_seconds"] = float(time.perf_counter() - stage)

    candidate_metric_rows: list[dict[str, Any]] = []
    comparator_metric_rows: list[dict[str, Any]] = []
    prediction_frames: list[pd.DataFrame] = []
    model_hashes: dict[str, str] = {}
    fold_profiles: dict[str, Any] = {}

    for fold in _folds():
        fold_started = time.perf_counter()
        train, validation = _split(table, fold)

        stage = time.perf_counter()
        base_probability = _base_rate_predictions(train, validation)
        base_metrics = probability_metrics(_scored_frame(validation, base_probability))
        alpha_probability, alpha_bundle = _fit_alpha_only_baseline(train, validation)
        alpha_metrics = probability_metrics(_scored_frame(validation, alpha_probability))
        alpha_model_path = output_dir / f"path_risk_v2_{fold.name}_alpha_only.joblib"
        joblib.dump(alpha_bundle, alpha_model_path)
        model_hashes[f"{fold.name}:{ALPHA_BASELINE}"] = sha256_file(alpha_model_path)
        comparator_seconds = float(time.perf_counter() - stage)

        comparator_metric_rows.extend(
            [
                {"fold": fold.name, "comparator": BASE_RATE_BASELINE, **base_metrics},
                {"fold": fold.name, "comparator": ALPHA_BASELINE, **alpha_metrics},
            ]
        )

        stage = time.perf_counter()
        pr002 = build_pr002_model()
        pr002.fit(train, train["stop_touch_h10"].to_numpy(dtype=int))
        pr002_probability = predict_pr002_probability(pr002, validation)
        pr002_metrics = probability_metrics(_scored_frame(validation, pr002_probability))
        candidate_metric_rows.append(
            _candidate_metric_row(
                fold=fold.name,
                candidate=PR002_CANDIDATE,
                candidate_metrics=pr002_metrics,
                base_metrics=base_metrics,
                alpha_metrics=alpha_metrics,
            )
        )
        pr002_path = output_dir / f"path_risk_v2_{fold.name}_pr002.joblib"
        joblib.dump(pr002, pr002_path)
        model_hashes[f"{fold.name}:{PR002_CANDIDATE}"] = sha256_file(pr002_path)
        pr002_seconds = float(time.perf_counter() - stage)

        pr002_scored = _scored_frame(validation, pr002_probability)
        pr002_scored["candidate"] = PR002_CANDIDATE
        pr002_scored["base_rate_probability"] = base_probability
        pr002_scored["alpha_only_probability"] = alpha_probability
        prediction_frames.append(pr002_scored)

        stage = time.perf_counter()
        expanded_train = expand_competing_risk_training(train)
        if set(expanded_train["cr_target"].astype(int).unique()) != {0, 1, 2}:
            raise RuntimeError(f"{fold.name} PR-003 training expansion requires all three classes")
        pr003 = build_pr003_model()
        pr003.fit(expanded_train, expanded_train["cr_target"].to_numpy(dtype=int))
        pr003_profile = score_pr003_cumulative_risk(pr003, validation)
        pr003_probability = pr003_profile["stop_probability_h10"].to_numpy(dtype=float)
        pr003_metrics = probability_metrics(_scored_frame(validation, pr003_probability))
        metric_row = _candidate_metric_row(
            fold=fold.name,
            candidate=PR003_CANDIDATE,
            candidate_metrics=pr003_metrics,
            base_metrics=base_metrics,
            alpha_metrics=alpha_metrics,
        )
        metric_row.update(
            {
                "mean_stop_probability_h3": float(pr003_profile["stop_probability_h3"].mean()),
                "mean_stop_probability_h5": float(pr003_profile["stop_probability_h5"].mean()),
                "mean_tp_probability_h10": float(pr003_profile["tp_probability_h10"].mean()),
                "mean_survival_probability_h10": float(
                    pr003_profile["survival_probability_h10"].mean()
                ),
                "max_probability_mass_error": float(pr003_profile["mass_error_h10"].max()),
                "expanded_train_rows": int(len(expanded_train)),
            }
        )
        candidate_metric_rows.append(metric_row)
        pr003_path = output_dir / f"path_risk_v2_{fold.name}_pr003.joblib"
        joblib.dump(pr003, pr003_path)
        model_hashes[f"{fold.name}:{PR003_CANDIDATE}"] = sha256_file(pr003_path)
        pr003_seconds = float(time.perf_counter() - stage)

        pr003_scored = _scored_frame(validation, pr003_probability)
        pr003_scored["candidate"] = PR003_CANDIDATE
        pr003_scored["base_rate_probability"] = base_probability
        pr003_scored["alpha_only_probability"] = alpha_probability
        for column in (
            "stop_probability_h3",
            "stop_probability_h5",
            "tp_probability_h10",
            "survival_probability_h10",
            "mass_error_h10",
        ):
            pr003_scored[column] = pr003_profile[column].to_numpy()
        prediction_frames.append(pr003_scored)

        fold_profiles[fold.name] = {
            "train_rows": int(len(train)),
            "validation_rows": int(len(validation)),
            "validation_dates": int(validation["date"].nunique()),
            "validation_tickers": int(validation["ticker"].nunique()),
            "comparator_seconds": comparator_seconds,
            "pr002_seconds": pr002_seconds,
            "pr003_seconds": pr003_seconds,
            "fold_total_seconds": float(time.perf_counter() - fold_started),
        }

    candidate_metrics = pd.DataFrame(candidate_metric_rows).sort_values(
        ["candidate", "fold"], kind="mergesort"
    ).reset_index(drop=True)
    comparator_metrics = pd.DataFrame(comparator_metric_rows).sort_values(
        ["comparator", "fold"], kind="mergesort"
    ).reset_index(drop=True)
    predictions = pd.concat(prediction_frames, ignore_index=True).sort_values(
        ["candidate", "signal_session_index", "ticker"], kind="mergesort"
    ).reset_index(drop=True)
    status, winner, selection = select_path_risk_v2_candidate(candidate_metrics)

    metrics_path = output_dir / "path_risk_v2_discovery_candidate_metrics.parquet"
    comparator_path = output_dir / "path_risk_v2_discovery_comparator_metrics.parquet"
    predictions_path = output_dir / "path_risk_v2_discovery_predictions.parquet"
    candidate_metrics.to_parquet(metrics_path, index=False)
    comparator_metrics.to_parquet(comparator_path, index=False)
    predictions.to_parquet(predictions_path, index=False)

    summary: dict[str, Any] = {
        "run_status": RUN_STATUS,
        "verdict": status,
        "winner": winner,
        "code_commit": code_commit,
        "spec_git_blob": spec_blob,
        "v1_model_table_sha256": PATH_RISK_V2_V1_MODEL_TABLE_SHA256,
        "calendar_sha256": PATH_RISK_V2_CALENDAR_SHA256,
        "feature_order_sha256": PATH_RISK_V2_FEATURE_ORDER_SHA256,
        "model_table_rows": int(len(table)),
        "first_signal_session_index": int(table["signal_session_index"].min()),
        "last_signal_session_index": int(table["signal_session_index"].max()),
        "status_composition": {
            str(key): int(value)
            for key, value in table["label_status"].value_counts().sort_index().items()
        },
        "stop_touch_prevalence": float(table["stop_touch_h10"].mean()),
        "candidate_selection": selection,
        "candidate_model_hashes": model_hashes,
        "candidate_metrics_path": str(metrics_path),
        "candidate_metrics_sha256": sha256_file(metrics_path),
        "comparator_metrics_path": str(comparator_path),
        "comparator_metrics_sha256": sha256_file(comparator_path),
        "predictions_path": str(predictions_path),
        "predictions_sha256": sha256_file(predictions_path),
        "fold_profiles": fold_profiles,
        "f5_f6_path_risk_accessed": False,
        "fresh_forward_accessed": False,
        "forward_marker_written": False,
        "final_ranker_modified": False,
        "risk_integration_created": False,
        "total_seconds": float(time.perf_counter() - total_started),
    }
    summary_path = output_dir / "path_risk_v2_discovery_summary.json"
    write_manifest_atomic(summary_path, summary)
    summary["summary_path"] = str(summary_path)
    summary["summary_sha256"] = sha256_file(summary_path)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Frozen Path Risk V2 PR-002/PR-003 F1-F4 runner"
    )
    parser.add_argument("--v1-model-table", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--code-commit", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_discovery(
        v1_model_table_path=args.v1_model_table,
        calendar_path=args.calendar,
        spec_path=args.spec,
        output_dir=args.output_dir,
        code_commit=args.code_commit,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
