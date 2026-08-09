from __future__ import annotations

import argparse
import json
import platform
from importlib.metadata import version
from pathlib import Path
from typing import Iterable

import pandas as pd

from .provenance import sha256_file
from .research_baselines import run_development_fold
from .research_features import build_baseline_features
from .research_labels import BarrierLabelConfig, build_first_touch_labels
from .research_validation import FROZEN_FOLDS, normalize_calendar
from .signal_research import validate_signal_research_hlcv, verify_signal_research_snapshot_manifest
from .storage import write_parquet_atomic


FROZEN_PANEL_SHA256 = "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
FROZEN_RESEARCH_MANIFEST_SHA256 = "b703f1f80aa062accfb4387e5c457458c88aec77351e7dd19342b9c45873cd1a"
MAX_DEVELOPMENT_SIGNAL_INDEX = 942
MAX_DEVELOPMENT_FUTURE_INDEX = 962  # F3 end + frozen H_max=20


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


def _calendar_from_table(path: Path, column: str) -> pd.DatetimeIndex:
    frame = _read_table(path)
    if column not in frame.columns:
        raise ValueError(f"calendar column {column!r} is absent from {path}")
    return normalize_calendar(frame[column])


def _listing_map(path: Path, ticker_column: str, listed_from_column: str) -> dict[str, object]:
    frame = _read_table(path)
    required = {ticker_column, listed_from_column}
    if not required.issubset(frame.columns):
        raise ValueError(f"security master missing columns: {sorted(required - set(frame.columns))}")
    result: dict[str, object] = {}
    for row in frame[[ticker_column, listed_from_column]].itertuples(index=False, name=None):
        ticker = str(row[0]).upper().replace(".JK", "").strip()
        if ticker:
            result[ticker] = row[1]
    return result


def _read_development_panel(panel_path: Path, max_date: pd.Timestamp) -> pd.DataFrame:
    """Read only the pre-holdout parquet partition needed for Stage-3 development."""

    if panel_path.suffix.lower() not in {".parquet", ".pq"}:
        raise ValueError("Stage-3 development requires the frozen parquet panel so row filters can enforce access bounds")
    try:
        panel = pd.read_parquet(panel_path, filters=[("date", "<=", max_date.to_pydatetime())])
    except Exception as error:
        raise RuntimeError(
            "failed to read the frozen panel with a pre-holdout parquet filter; refusing an unfiltered fallback"
        ) from error
    if panel.empty:
        raise ValueError("filtered development panel is empty")
    panel["date"] = pd.to_datetime(panel["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if panel["date"].max() > max_date:
        raise RuntimeError("parquet filter admitted data beyond the configured development future boundary")
    if not validate_signal_research_hlcv(panel):
        raise ValueError("filtered development panel violates SIGNAL_RESEARCH_HLCV")
    return panel


def _verify_research_manifest(path: Path) -> dict[str, object]:
    if sha256_file(path) != FROZEN_RESEARCH_MANIFEST_SHA256:
        raise RuntimeError("frozen SIGNAL_RESEARCH_1260 manifest hash mismatch")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    verification = verify_signal_research_snapshot_manifest(manifest)
    if not bool(verification.get("valid", False)):
        raise RuntimeError(f"frozen research manifest verification failed: {verification}")
    return verification


def _frozen_spec_hashes() -> dict[str, str]:
    repo_root = Path(__file__).resolve().parents[2]
    paths = {
        "research_specification_v1": repo_root / "docs" / "RESEARCH_SPECIFICATION_V1.md",
        "validation_plan_v1": repo_root / "docs" / "VALIDATION_PLAN_V1.md",
        "validation_threat_model_v1": repo_root / "docs" / "VALIDATION_THREAT_MODEL_V1.md",
        "stage3_implementation_plan_v1": repo_root / "docs" / "STAGE3_IMPLEMENTATION_PLAN_V1.md",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"required frozen specification files are missing: {missing}")
    return {name: sha256_file(path) for name, path in paths.items()}


def _dependency_versions() -> dict[str, str]:
    packages = ["numpy", "pandas", "pyarrow", "scikit-learn"]
    return {name: version(name) for name in packages} | {"python": platform.python_version()}


def _label_outcome_summary(labels: pd.DataFrame, horizon: int) -> list[dict[str, object]]:
    counts = labels["label_status"].value_counts(dropna=False).sort_index()
    total = int(len(labels))
    return [
        {
            "horizon": horizon,
            "label_status": str(status),
            "rows": int(count),
            "share": float(count / total) if total else 0.0,
        }
        for status, count in counts.items()
    ]


def _advancement_summary(metrics: pd.DataFrame) -> dict[str, object]:
    decisions: dict[str, object] = {}
    for challenger in ("logistic_compact", "hist_gradient_boosting"):
        better_folds: list[str] = []
        for fold in [item.name for item in FROZEN_FOLDS]:
            block = metrics[metrics["fold"].eq(fold)].set_index("model_name")
            if challenger not in block.index or "base_rate" not in block.index or "momentum_20" not in block.index:
                continue
            candidate = float(block.loc[challenger, "pr_auc"])
            if candidate > float(block.loc["base_rate", "pr_auc"]) and candidate > float(block.loc["momentum_20", "pr_auc"]):
                better_folds.append(fold)
        decisions[challenger] = {
            "better_than_base_rate_and_momentum_folds": better_folds,
            "directional_advancement_rule_met": len(better_folds) >= 2,
        }
    return decisions


def run_stage3_development(
    *,
    panel_path: Path,
    research_manifest_path: Path,
    calendar_path: Path,
    security_master_path: Path,
    output_dir: Path,
    code_commit: str,
    calendar_column: str = "date",
    ticker_column: str = "ticker",
    listed_from_column: str = "listed_from",
) -> dict[str, object]:
    if sha256_file(panel_path) != FROZEN_PANEL_SHA256:
        raise RuntimeError("frozen SIGNAL_RESEARCH_HLCV panel hash mismatch")
    manifest_verification = _verify_research_manifest(research_manifest_path)
    spec_hashes = _frozen_spec_hashes()
    dependencies = _dependency_versions()
    calendar = _calendar_from_table(calendar_path, calendar_column)
    listing_map = _listing_map(security_master_path, ticker_column, listed_from_column)
    max_future_date = pd.Timestamp(calendar[MAX_DEVELOPMENT_FUTURE_INDEX - 1])
    max_signal_date = pd.Timestamp(calendar[MAX_DEVELOPMENT_SIGNAL_INDEX - 1])
    source_panel = _read_development_panel(panel_path, max_future_date)

    feature_source = source_panel[source_panel["date"] <= max_signal_date].copy()
    features = build_baseline_features(feature_source, calendar, listed_from=listing_map)

    label_tables: dict[int, pd.DataFrame] = {}
    outcome_summary: list[dict[str, object]] = []
    for horizon in (5, 10, 20):
        labels = build_first_touch_labels(
            source_panel,
            calendar,
            config=BarrierLabelConfig(horizon=horizon),
            max_signal_session_index=MAX_DEVELOPMENT_SIGNAL_INDEX,
            max_future_session_index=MAX_DEVELOPMENT_FUTURE_INDEX,
        )
        label_tables[horizon] = labels
        outcome_summary.extend(_label_outcome_summary(labels, horizon))

    from .research_baselines import prepare_primary_model_table

    model_table = prepare_primary_model_table(features, label_tables[10])
    if model_table["date"].max() > max_signal_date:
        raise RuntimeError("model table crosses the pre-registered development signal boundary")

    metrics_rows: list[dict[str, object]] = []
    prediction_frames: list[pd.DataFrame] = []
    for fold in FROZEN_FOLDS:
        results = run_development_fold(model_table, calendar, fold_name=fold.name, include_tree=True)
        for result in results:
            metrics_rows.append({"fold": result.fold, "model_name": result.model_name, **result.metrics})
            prediction = result.predictions.copy()
            prediction["fold"] = result.fold
            prediction["model_name"] = result.model_name
            prediction_frames.append(prediction)

    metrics = pd.DataFrame(metrics_rows).sort_values(["fold", "model_name"]).reset_index(drop=True)
    predictions = pd.concat(prediction_frames, ignore_index=True, sort=False).sort_values(
        ["model_name", "date", "ticker"]
    ).reset_index(drop=True)
    advancement = _advancement_summary(metrics)

    output_dir.mkdir(parents=True, exist_ok=True)
    feature_path = output_dir / "stage3_baseline_features_development.parquet"
    model_table_path = output_dir / "stage3_primary_model_table_development.parquet"
    prediction_path = output_dir / "stage3_oof_predictions_development.parquet"
    metrics_path = output_dir / "stage3_fold_metrics.csv"
    label_paths: dict[int, Path] = {}

    write_parquet_atomic(features, feature_path)
    write_parquet_atomic(model_table, model_table_path)
    write_parquet_atomic(predictions, prediction_path)
    metrics.to_csv(metrics_path, index=False)
    for horizon, labels in label_tables.items():
        path = output_dir / f"stage3_labels_h{horizon}_development.parquet"
        write_parquet_atomic(labels, path)
        label_paths[horizon] = path

    summary = {
        "stage": "STAGE3_DEVELOPMENT",
        "code_commit": code_commit,
        "input_panel_sha256": FROZEN_PANEL_SHA256,
        "research_manifest_sha256": FROZEN_RESEARCH_MANIFEST_SHA256,
        "research_manifest_verification": manifest_verification,
        "specification_hashes": spec_hashes,
        "dependency_versions": dependencies,
        "random_seed": 42,
        "calendar_first": pd.Timestamp(calendar[0]).date().isoformat(),
        "calendar_last": pd.Timestamp(calendar[-1]).date().isoformat(),
        "max_signal_session_index_read": MAX_DEVELOPMENT_SIGNAL_INDEX,
        "max_signal_date": max_signal_date.date().isoformat(),
        "max_future_session_index_read": MAX_DEVELOPMENT_FUTURE_INDEX,
        "max_future_date": max_future_date.date().isoformat(),
        "locked_holdout_start_index": 1009,
        "locked_holdout_start_date": pd.Timestamp(calendar[1008]).date().isoformat(),
        "holdout_outcome_accessed": False,
        "primary_label": {"horizon": 10, "atr_window": 14, "sl_atr_multiple": 1.0, "reward_risk": 1.5},
        "secondary_label_horizons": [5, 20],
        "feature_rows": int(len(features)),
        "primary_model_rows": int(len(model_table)),
        "outcome_summary": outcome_summary,
        "advancement": advancement,
        "artifacts": {},
    }
    artifact_paths = {
        "features": feature_path,
        "primary_model_table": model_table_path,
        "oof_predictions": prediction_path,
        "fold_metrics": metrics_path,
        **{f"labels_h{horizon}": path for horizon, path in label_paths.items()},
    }
    summary["artifacts"] = {
        name: {"path": str(path), "sha256": sha256_file(path)} for name, path in artifact_paths.items()
    }
    summary_path = output_dir / "stage3_development_summary.json"
    _atomic_json(summary, summary_path)
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run frozen Stage-3 development only; locked holdout is inaccessible")
    parser.add_argument("--panel", required=True, type=Path)
    parser.add_argument("--research-manifest", required=True, type=Path)
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
    summary = run_stage3_development(
        panel_path=args.panel,
        research_manifest_path=args.research_manifest,
        calendar_path=args.calendar,
        security_master_path=args.security_master,
        output_dir=args.output_dir,
        code_commit=args.code_commit,
        calendar_column=args.calendar_column,
        ticker_column=args.ticker_column,
        listed_from_column=args.listed_from_column,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
