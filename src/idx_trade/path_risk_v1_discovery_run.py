"""Frozen Path Risk V1 F1-F4 discovery runner.

This module is intentionally separate from cache preparation. It is only for the
separately authorized historical Path Risk outcome run. It physically bounds
loaded label rows to signal sessions <=984 and price-path evidence to the latest
H10 endpoint needed by that discovery window. It never reads Path Risk F5/F6 or
post-2026-07-31 forward rows into model/evaluation frames.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .path_risk_v1 import (
    PATH_RISK_CANDIDATE,
    PATH_RISK_DISCOVERY_FOLDS,
    PATH_RISK_DISCOVERY_PASS,
    PATH_RISK_FEATURE_COLUMNS,
    PATH_RISK_FEATURE_ORDER_SHA256,
    PATH_RISK_H10_LABEL_SHA256,
    PATH_RISK_HORIZON,
    PATH_RISK_REWARD_RISK,
    PATH_RISK_STOP_ATR_MULTIPLE,
    build_adverse_excursion_targets,
    build_path_risk_model,
    path_risk_discovery_gate,
    path_risk_metrics,
    relative_pinball_improvement,
    training_q75_constant,
)
from .provenance import sha256_file, write_manifest_atomic
from .research_v2_validation import RANKING_V2_FOLDS, RankingV2Fold


DISCOVERY_MAX_SIGNAL_SESSION = 984
DISCOVERY_MAX_FUTURE_SESSION = DISCOVERY_MAX_SIGNAL_SESSION + PATH_RISK_HORIZON

FROZEN_FEATURE_CACHE_SHA256 = "74c300390dce542dad95ae204dd7663f5f780b09dd33c3514c5dd264f15cca08"
FROZEN_FEATURE_MANIFEST_SHA256 = "054ccff7676a744871b1f82a5b263898f9fa53c2d1ae1ac20a5659485466bed0"
FROZEN_PANEL_SHA256 = "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
FROZEN_CALENDAR_SHA256 = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
FROZEN_SPEC_GIT_BLOB = "a0d9f23844d9f7f2c311e27a471a86d7f7f48395"

RUN_STATUS = "PATH_RISK_A_DISCOVERY_F1_F4_COMPLETE"

_LABEL_COLUMNS = (
    "ticker",
    "signal_date",
    "signal_session_index",
    "signal_reference_close",
    "atr",
    "horizon",
    "sl_atr_multiple",
    "reward_risk",
    "tp_level",
    "sl_level",
    "label_status",
    "first_barrier_date",
)


def _assert_new_or_empty(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise RuntimeError(f"Path Risk discovery output directory must be new or empty: {path}")
    path.mkdir(parents=True, exist_ok=True)


def _read_calendar(path: Path) -> pd.DatetimeIndex:
    if sha256_file(path) != FROZEN_CALENDAR_SHA256:
        raise RuntimeError("Path Risk discovery calendar SHA mismatch")
    frame = pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_parquet(path)
    candidates = [column for column in ("date", "session_date", "trading_date") if column in frame.columns]
    if len(candidates) != 1:
        raise ValueError(f"Path Risk discovery calendar requires one date column, got {candidates}")
    dates = pd.to_datetime(frame[candidates[0]], errors="coerce")
    sessions = pd.DatetimeIndex(dates).tz_localize(None).normalize().dropna().unique().sort_values()
    if len(sessions) < DISCOVERY_MAX_FUTURE_SESSION:
        raise RuntimeError("Path Risk discovery calendar does not cover the H10 endpoint through session 994")
    return sessions


def _read_feature_cache(cache_path: Path, manifest_path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    if sha256_file(cache_path) != FROZEN_FEATURE_CACHE_SHA256:
        raise RuntimeError("Path Risk frozen feature-cache SHA mismatch")
    if sha256_file(manifest_path) != FROZEN_FEATURE_MANIFEST_SHA256:
        raise RuntimeError("Path Risk frozen feature-cache manifest SHA mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required_manifest = {
        "status": "PATH_RISK_V1_DISCOVERY_FEATURE_CACHE_FROZEN_PRE_OUTCOME",
        "cache_sha256": FROZEN_FEATURE_CACHE_SHA256,
        "last_signal_session_index": DISCOVERY_MAX_SIGNAL_SESSION,
        "feature_order_sha256": PATH_RISK_FEATURE_ORDER_SHA256,
        "real_h10_labels_loaded": False,
        "real_path_risk_target_computed": False,
        "pr001_model_fitted": False,
        "path_risk_performance_metrics_computed": False,
        "f5_f6_path_risk_accessed": False,
        "fresh_forward_accessed": False,
        "forward_marker_written": False,
    }
    for key, expected in required_manifest.items():
        if manifest.get(key) != expected:
            raise RuntimeError(f"Path Risk feature-cache manifest mismatch {key}: expected={expected!r} actual={manifest.get(key)!r}")

    frame = pd.read_parquet(cache_path)
    required = {"ticker", "date", "signal_session_index", "universe_primary_liquid", *PATH_RISK_FEATURE_COLUMNS}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Path Risk feature cache missing {sorted(missing)}")
    frame = frame.copy()
    frame["ticker"] = frame["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    frame["signal_session_index"] = pd.to_numeric(frame["signal_session_index"], errors="raise").astype(int)
    if frame["date"].isna().any() or frame.duplicated(["ticker", "date"]).any():
        raise ValueError("Path Risk feature cache has invalid/duplicate identity rows")
    if not frame["universe_primary_liquid"].astype(bool).all():
        raise RuntimeError("Path Risk feature cache contains non-primary-liquid rows")
    if int(frame["signal_session_index"].max()) > DISCOVERY_MAX_SIGNAL_SESSION:
        raise RuntimeError("Path Risk feature cache escaped session 984")
    if list(frame.columns[-len(PATH_RISK_FEATURE_COLUMNS):]) != list(PATH_RISK_FEATURE_COLUMNS):
        raise RuntimeError("Path Risk feature-cache feature order differs from frozen 33-feature order")
    return frame.sort_values(["signal_session_index", "ticker"], kind="mergesort").reset_index(drop=True), manifest


def _read_discovery_labels(path: Path) -> pd.DataFrame:
    if path.suffix.lower() not in {".parquet", ".pq"}:
        raise ValueError("Path Risk H10 labels must be Parquet for physical discovery filtering")
    if sha256_file(path) != PATH_RISK_H10_LABEL_SHA256:
        raise RuntimeError("Path Risk frozen H10 label SHA mismatch")
    labels = pd.read_parquet(
        path,
        columns=list(_LABEL_COLUMNS),
        filters=[("signal_session_index", "<=", DISCOVERY_MAX_SIGNAL_SESSION)],
    )
    if labels.empty:
        raise RuntimeError("Path Risk discovery H10 label subset is empty")
    labels = labels.copy()
    labels["ticker"] = labels["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    labels["signal_date"] = pd.to_datetime(labels["signal_date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    labels["signal_session_index"] = pd.to_numeric(labels["signal_session_index"], errors="raise").astype(int)
    if labels["signal_date"].isna().any() or labels.duplicated(["ticker", "signal_date"]).any():
        raise ValueError("Path Risk discovery labels have invalid/duplicate identities")
    if int(labels["signal_session_index"].max()) > DISCOVERY_MAX_SIGNAL_SESSION:
        raise RuntimeError("Path Risk discovery label read materialized session 985+")

    horizon = pd.to_numeric(labels["horizon"], errors="raise").astype(int)
    sl_multiple = pd.to_numeric(labels["sl_atr_multiple"], errors="raise").to_numpy(dtype=float)
    reward_risk = pd.to_numeric(labels["reward_risk"], errors="raise").to_numpy(dtype=float)
    if not horizon.eq(PATH_RISK_HORIZON).all():
        raise RuntimeError("Path Risk labels violate frozen H10 horizon=10")
    if not np.isclose(sl_multiple, PATH_RISK_STOP_ATR_MULTIPLE, rtol=0.0, atol=1e-12).all():
        raise RuntimeError("Path Risk labels violate frozen stop ATR multiple=1.0")
    if not np.isclose(reward_risk, PATH_RISK_REWARD_RISK, rtol=0.0, atol=1e-12).all():
        raise RuntimeError("Path Risk labels violate frozen reward:risk=1.5")
    return labels.sort_values(["signal_session_index", "ticker"], kind="mergesort").reset_index(drop=True)


def _read_path_panel(path: Path, sessions: pd.DatetimeIndex) -> pd.DataFrame:
    if path.suffix.lower() not in {".parquet", ".pq"}:
        raise ValueError("Path Risk signal panel must be Parquet")
    if sha256_file(path) != FROZEN_PANEL_SHA256:
        raise RuntimeError("Path Risk frozen signal-panel SHA mismatch")
    max_future_date = pd.Timestamp(sessions[DISCOVERY_MAX_FUTURE_SESSION - 1])
    columns = ["ticker", "date", "high", "low", "close"]
    panel = pd.read_parquet(path, columns=columns, filters=[("date", "<=", max_future_date)])
    panel = panel.copy()
    panel["date"] = pd.to_datetime(panel["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if panel.empty or panel["date"].isna().any() or (panel["date"] > max_future_date).any():
        raise RuntimeError("Path Risk discovery panel read escaped required future endpoint")
    return panel


def _build_target_table(
    *,
    labels: pd.DataFrame,
    panel: pd.DataFrame,
    sessions: pd.DatetimeIndex,
) -> pd.DataFrame:
    targets = build_adverse_excursion_targets(labels, panel, sessions)
    if targets.empty:
        raise RuntimeError("Path Risk target builder produced no eligible targets")
    targets = targets.rename(columns={"signal_date": "date"}).copy()
    targets["date"] = pd.to_datetime(targets["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    targets["signal_session_index"] = pd.to_numeric(targets["signal_session_index"], errors="raise").astype(int)
    if targets.duplicated(["ticker", "date"]).any():
        raise RuntimeError("Path Risk target table contains duplicate identities")
    if int(targets["signal_session_index"].max()) > DISCOVERY_MAX_SIGNAL_SESSION:
        raise RuntimeError("Path Risk target table escaped session 984")
    values = pd.to_numeric(targets["adverse_excursion_r"], errors="coerce").to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise RuntimeError("Path Risk target table contains invalid adverse-excursion targets")
    return targets.sort_values(["signal_session_index", "ticker"], kind="mergesort").reset_index(drop=True)


def _join_features_targets(features: pd.DataFrame, targets: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    target_columns = [
        "ticker",
        "date",
        "signal_session_index",
        "label_status",
        "first_barrier_date",
        "target_tau_date",
        "adverse_excursion_r",
    ]
    merged = features.merge(
        targets[target_columns],
        on=["ticker", "date", "signal_session_index"],
        how="inner",
        validate="one_to_one",
    )
    if merged.empty:
        raise RuntimeError("Path Risk feature/target join produced no rows")
    coverage = {
        "feature_rows": int(len(features)),
        "target_eligible_rows": int(len(targets)),
        "joined_rows": int(len(merged)),
        "joined_fraction_of_feature_rows": float(len(merged) / len(features)),
        "feature_rows_without_eligible_target": int(len(features) - len(merged)),
    }
    return merged.sort_values(["signal_session_index", "ticker"], kind="mergesort").reset_index(drop=True), coverage


def _folds() -> tuple[RankingV2Fold, ...]:
    selected = tuple(fold for fold in RANKING_V2_FOLDS if fold.name in PATH_RISK_DISCOVERY_FOLDS)
    if tuple(fold.name for fold in selected) != PATH_RISK_DISCOVERY_FOLDS:
        raise RuntimeError("Path Risk discovery fold identity mismatch")
    return selected


def _status_composition(frame: pd.DataFrame) -> dict[str, int]:
    return {str(key): int(value) for key, value in frame["label_status"].value_counts(dropna=False).sort_index().items()}


def run_discovery(
    *,
    feature_cache_path: Path,
    feature_manifest_path: Path,
    h10_labels_path: Path,
    panel_path: Path,
    calendar_path: Path,
    output_dir: Path,
    code_commit: str,
) -> dict[str, Any]:
    _assert_new_or_empty(output_dir)
    started = time.perf_counter()

    features, feature_manifest = _read_feature_cache(feature_cache_path, feature_manifest_path)
    sessions = _read_calendar(calendar_path)
    labels = _read_discovery_labels(h10_labels_path)
    panel = _read_path_panel(panel_path, sessions)
    targets = _build_target_table(labels=labels, panel=panel, sessions=sessions)
    model_table, join_coverage = _join_features_targets(features, targets)

    target_path = output_dir / "path_risk_v1_discovery_targets.parquet"
    targets.to_parquet(target_path, index=False)
    model_table_path = output_dir / "path_risk_v1_discovery_model_table.parquet"
    model_table.to_parquet(model_table_path, index=False)

    metric_rows: list[dict[str, Any]] = []
    prediction_frames: list[pd.DataFrame] = []
    model_hashes: dict[str, str] = {}
    fold_runtime: dict[str, float] = {}

    for fold in _folds():
        fold_started = time.perf_counter()
        train = model_table[model_table["signal_session_index"].between(fold.train_start, fold.train_end)].copy()
        validation = model_table[model_table["signal_session_index"].between(fold.validation_start, fold.validation_end)].copy()
        if train.empty or validation.empty:
            raise RuntimeError(f"{fold.name} has empty Path Risk train/validation rows")

        train_target = pd.to_numeric(train["adverse_excursion_r"], errors="raise").to_numpy(dtype=float)
        validation_target = pd.to_numeric(validation["adverse_excursion_r"], errors="raise").to_numpy(dtype=float)
        if not np.isfinite(train_target).all() or not np.isfinite(validation_target).all():
            raise RuntimeError(f"{fold.name} contains non-finite Path Risk targets")

        baseline_q75 = training_q75_constant(train_target)
        baseline_prediction = np.full(len(validation), baseline_q75, dtype=float)

        model = build_path_risk_model()
        model.fit(train, train_target)
        prediction = np.asarray(model.predict(validation), dtype=float)
        if not np.isfinite(prediction).all():
            raise RuntimeError(f"{fold.name} PR-001 produced non-finite predictions")

        scored = validation[["ticker", "date", "signal_session_index", "label_status", "adverse_excursion_r"]].copy()
        scored["prediction"] = prediction
        scored["baseline_prediction"] = baseline_prediction
        model_metrics = path_risk_metrics(scored, prediction_column="prediction")
        baseline_metrics = path_risk_metrics(scored, prediction_column="baseline_prediction")
        relative_improvement = relative_pinball_improvement(
            baseline_metrics["pinball_loss"], model_metrics["pinball_loss"]
        )

        model_path = output_dir / f"path_risk_v1_pr001_{fold.name}.joblib"
        joblib.dump(model, model_path)
        model_hashes[fold.name] = sha256_file(model_path)

        metric_rows.append(
            {
                "fold": fold.name,
                "train_rows": int(len(train)),
                "validation_rows": int(len(validation)),
                "validation_dates": int(validation["date"].nunique()),
                "validation_tickers": int(validation["ticker"].nunique()),
                "training_q75_baseline": float(baseline_q75),
                "baseline_pinball_loss": float(baseline_metrics["pinball_loss"]),
                "model_pinball_loss": float(model_metrics["pinball_loss"]),
                "relative_pinball_improvement": float(relative_improvement),
                "model_mae": float(model_metrics["mae"]),
                "spearman": float(model_metrics["spearman"]),
                "empirical_q75_coverage": float(model_metrics["empirical_q75_coverage"]),
                "absolute_coverage_error": float(model_metrics["absolute_coverage_error"]),
                "q1_mean_adverse_excursion": float(model_metrics["q1_mean_adverse_excursion"]),
                "q5_mean_adverse_excursion": float(model_metrics["q5_mean_adverse_excursion"]),
                "q5_minus_q1_adverse_excursion": float(model_metrics["q5_minus_q1_adverse_excursion"]),
                "q1_stop_touch_rate": float(model_metrics["q1_stop_touch_rate"]),
                "q5_stop_touch_rate": float(model_metrics["q5_stop_touch_rate"]),
                "finite_prediction_rate": float(model_metrics["finite_prediction_rate"]),
                "unique_prediction_count": int(model_metrics["unique_prediction_count"]),
                "train_status_composition": json.dumps(_status_composition(train), sort_keys=True),
                "validation_status_composition": json.dumps(_status_composition(validation), sort_keys=True),
                "model_sha256": model_hashes[fold.name],
            }
        )
        scored.insert(0, "candidate", PATH_RISK_CANDIDATE)
        scored.insert(1, "fold", fold.name)
        prediction_frames.append(scored)
        fold_runtime[fold.name] = float(time.perf_counter() - fold_started)

    metrics = pd.DataFrame(metric_rows).sort_values("fold").reset_index(drop=True)
    verdict, gate_checks = path_risk_discovery_gate(metrics)
    predictions = pd.concat(prediction_frames, ignore_index=True).sort_values(["fold", "date", "ticker"]).reset_index(drop=True)

    if int(predictions["signal_session_index"].max()) > DISCOVERY_MAX_SIGNAL_SESSION:
        raise RuntimeError("Path Risk discovery predictions escaped session 984")

    metrics_path = output_dir / "path_risk_v1_discovery_fold_metrics.parquet"
    metrics.to_parquet(metrics_path, index=False)
    predictions_path = output_dir / "path_risk_v1_discovery_predictions.parquet"
    predictions.to_parquet(predictions_path, index=False)

    summary: dict[str, Any] = {
        "status": RUN_STATUS,
        "candidate": PATH_RISK_CANDIDATE,
        "verdict": verdict,
        "candidate_viewed": True,
        "candidate_ordinal": "PR-001",
        "code_commit": code_commit,
        "discovery_folds": list(PATH_RISK_DISCOVERY_FOLDS),
        "feature_cache_sha256": FROZEN_FEATURE_CACHE_SHA256,
        "feature_manifest_sha256": FROZEN_FEATURE_MANIFEST_SHA256,
        "h10_labels_sha256": PATH_RISK_H10_LABEL_SHA256,
        "panel_sha256": FROZEN_PANEL_SHA256,
        "calendar_sha256": FROZEN_CALENDAR_SHA256,
        "spec_git_blob": FROZEN_SPEC_GIT_BLOB,
        "feature_order_sha256": PATH_RISK_FEATURE_ORDER_SHA256,
        "join_coverage": join_coverage,
        "target_rows": int(len(targets)),
        "target_status_composition": _status_composition(targets),
        "model_table_rows": int(len(model_table)),
        "model_hashes": model_hashes,
        "gate_checks": gate_checks,
        "artifacts": {
            "targets_sha256": sha256_file(target_path),
            "model_table_sha256": sha256_file(model_table_path),
            "metrics_sha256": sha256_file(metrics_path),
            "predictions_sha256": sha256_file(predictions_path),
        },
        "fold_runtime_seconds": fold_runtime,
        "runtime_seconds": float(time.perf_counter() - started),
        "f5_f6_path_risk_accessed": False,
        "fresh_forward_accessed": False,
        "forward_marker_written": False,
        "ranker_changed": False,
        "risk_veto_or_integration_created": False,
    }
    summary_path = output_dir / "path_risk_v1_discovery_summary.json"
    write_manifest_atomic(summary_path, summary)
    summary["summary_sha256"] = sha256_file(summary_path)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Frozen Path Risk V1 PR-001 F1-F4 discovery runner")
    parser.add_argument("--feature-cache", type=Path, required=True)
    parser.add_argument("--feature-manifest", type=Path, required=True)
    parser.add_argument("--h10-labels", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--code-commit", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_discovery(
        feature_cache_path=args.feature_cache,
        feature_manifest_path=args.feature_manifest,
        h10_labels_path=args.h10_labels,
        panel_path=args.panel,
        calendar_path=args.calendar,
        output_dir=args.output_dir,
        code_commit=args.code_commit,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
