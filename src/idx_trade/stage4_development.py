from __future__ import annotations

import argparse
import json
import platform
from importlib.metadata import version
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from .provenance import sha256_file
from .research_baselines import run_development_fold
from .research_stage4 import (
    CALIBRATOR_ORDER,
    attribution_summary,
    assign_cross_sectional_quintiles,
    calibration_candidates,
    calibration_readiness,
    fit_full_hgb_fold,
    pooled_calibration_metrics,
    quintile_summary,
    regime_diagnostics,
    run_ablation_fold,
    select_calibrator,
)
from .research_validation import FROZEN_FOLDS, normalize_calendar
from .storage import write_parquet_atomic


FROZEN_STAGE3_MODEL_TABLE_SHA256 = "c161911f1330eec12335c6e2711bdca045ad5cfdb1e52f789b1489e987a67189"
FROZEN_STAGE3_FEATURE_TABLE_SHA256 = "f16d77caa6642d0aba8c0a39eda5b2d32e53f17717b149f5f0637eeacac80772"
FROZEN_STAGE3_SUMMARY_SHA256 = "979c56be43e2fdc5c0502e1b1625d74dbcab6ba28f097338575479739baa029f"
LOCKED_HOLDOUT_START_INDEX = 1009


def _read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"unsupported table format: {path}")


def _atomic_json(value: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    temporary.replace(path)


def _dependency_versions() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "numpy": version("numpy"),
        "pandas": version("pandas"),
        "pyarrow": version("pyarrow"),
        "scikit-learn": version("scikit-learn"),
    }


def _repo_spec_hashes() -> dict[str, str]:
    root = Path(__file__).resolve().parents[2]
    paths = {
        "research_specification_v1": root / "docs" / "RESEARCH_SPECIFICATION_V1.md",
        "validation_plan_v1": root / "docs" / "VALIDATION_PLAN_V1.md",
        "stage3_implementation_plan_v1": root / "docs" / "STAGE3_IMPLEMENTATION_PLAN_V1.md",
        "stage4_research_plan_v1": root / "docs" / "STAGE4_RESEARCH_PLAN_V1.md",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing frozen research documents: {missing}")
    return {name: sha256_file(path) for name, path in paths.items()}


def _calendar(path: Path, column: str) -> pd.DatetimeIndex:
    frame = _read_table(path)
    if column not in frame.columns:
        raise ValueError(f"calendar column {column!r} absent from {path}")
    return normalize_calendar(frame[column])


def _verify_input_hash(path: Path, expected: str, label: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"{label} hash mismatch: expected={expected} actual={actual}")


def _load_stage3_summary(path: Path) -> dict[str, object]:
    _verify_input_hash(path, FROZEN_STAGE3_SUMMARY_SHA256, "Stage-3 summary")
    summary = json.loads(path.read_text(encoding="utf-8"))
    if bool(summary.get("holdout_outcome_accessed", True)):
        raise RuntimeError("Stage-3 summary does not prove holdout_outcome_accessed=false")
    if int(summary.get("locked_holdout_start_index", -1)) != LOCKED_HOLDOUT_START_INDEX:
        raise RuntimeError("Stage-3 summary locked-holdout boundary mismatch")
    return summary


def _assert_development_only(frame: pd.DataFrame, calendar: pd.DatetimeIndex, label: str) -> pd.DataFrame:
    if "date" not in frame.columns:
        raise ValueError(f"{label} missing date")
    result = frame.copy()
    result["date"] = pd.to_datetime(result["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if result["date"].isna().any():
        raise ValueError(f"{label} contains invalid dates")
    holdout_start = pd.Timestamp(calendar[LOCKED_HOLDOUT_START_INDEX - 1])
    if (result["date"] >= holdout_start).any():
        first = result.loc[result["date"] >= holdout_start, "date"].min()
        raise RuntimeError(f"{label} contains locked-holdout row: {first}")
    return result


def _reference_stage3_metrics(model_table: pd.DataFrame, calendar: pd.DatetimeIndex) -> tuple[pd.DataFrame, pd.DataFrame]:
    metric_rows: list[dict[str, object]] = []
    predictions: list[pd.DataFrame] = []
    for fold in FROZEN_FOLDS:
        for result in run_development_fold(model_table, calendar, fold_name=fold.name, include_tree=True):
            metrics = dict(result.metrics)
            metrics["prevalence_gap"] = abs(float(metrics["prediction_mean"]) - float(metrics["positive_rate"]))
            metric_rows.append({"fold": fold.name, "model": result.model_name, **metrics})
            pred = result.predictions.copy()
            pred["fold"] = fold.name
            pred["model"] = result.model_name
            predictions.append(pred)
    return pd.DataFrame(metric_rows), pd.concat(predictions, ignore_index=True)


def _pooled_reference_metrics(metrics: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for model, block in predictions.groupby("model", sort=True):
        y = block["target"].to_numpy(dtype=int)
        p = block["probability"].to_numpy(dtype=float)
        fold_metrics = metrics[metrics["model"].eq(model)]
        rows.append(
            {
                "model": model,
                "rows": int(len(block)),
                "positive_rate": float(y.mean()),
                "mean_probability": float(p.mean()),
                "prevalence_gap": abs(float(p.mean()) - float(y.mean())),
                "pr_auc": float(average_precision_score(y, p)),
                "roc_auc": float(roc_auc_score(y, p)),
                "brier": float(brier_score_loss(y, p)),
                "weighted_fold_ece": float(np.average(fold_metrics["ece"], weights=fold_metrics["rows"])),
            }
        )
    return pd.DataFrame(rows)


def _ranking_advancement(reference_metrics: pd.DataFrame) -> dict[str, object]:
    folds: list[str] = []
    for fold in ("F1", "F2", "F3"):
        block = reference_metrics[reference_metrics["fold"].eq(fold)].set_index("model")
        hgb = float(block.loc["hist_gradient_boosting", "pr_auc"])
        if hgb > float(block.loc["base_rate", "pr_auc"]) and hgb > float(block.loc["momentum_20", "pr_auc"]):
            folds.append(fold)
    return {"hgb_beats_base_and_momentum_folds": folds, "stage3_rule_reproduced": len(folds) >= 2}


def _quintile_gate(summary: pd.DataFrame) -> dict[str, object]:
    fold_rows = summary[(summary["fold"].isin(["F1", "F2", "F3"])) & summary["quintile"].eq(5)]
    passing = [str(row.fold) for row in fold_rows.itertuples() if bool(row.q5_gt_q1)]
    return {"q5_gt_q1_folds": passing, "directional_quintile_gate": len(passing) >= 2}


def _runtime_decision(ranking: dict[str, object], quintile: dict[str, object], calibration: dict[str, object]) -> str:
    ranking_ok = bool(ranking["stage3_rule_reproduced"]) and bool(quintile["directional_quintile_gate"])
    if not ranking_ok:
        return "STAGE4_RANKING_REVIEW_REQUIRED"
    if bool(calibration["calibration_ready"]):
        return "STAGE4_RANKING_AND_CALIBRATION_FREEZE_READY"
    return "STAGE4_RANKING_GO_CALIBRATION_BLOCKED"


def run_stage4_development(
    *,
    model_table_path: Path,
    feature_table_path: Path,
    stage3_summary_path: Path,
    calendar_path: Path,
    output_dir: Path,
    code_commit: str,
    calendar_column: str = "date",
) -> dict[str, object]:
    _verify_input_hash(model_table_path, FROZEN_STAGE3_MODEL_TABLE_SHA256, "Stage-3 model table")
    _verify_input_hash(feature_table_path, FROZEN_STAGE3_FEATURE_TABLE_SHA256, "Stage-3 feature table")
    stage3_summary = _load_stage3_summary(stage3_summary_path)
    calendar = _calendar(calendar_path, calendar_column)
    model_table = _assert_development_only(_read_table(model_table_path), calendar, "Stage-3 model table")
    feature_table = _assert_development_only(_read_table(feature_table_path), calendar, "Stage-3 feature table")

    reference_metrics, reference_predictions = _reference_stage3_metrics(model_table, calendar)
    pooled_reference = _pooled_reference_metrics(reference_metrics, reference_predictions)
    ranking_gate = _ranking_advancement(reference_metrics)

    ablation_metrics_frames: list[pd.DataFrame] = []
    ablation_prediction_frames: list[pd.DataFrame] = []
    calibration_metric_frames: list[pd.DataFrame] = []
    calibration_prediction_frames: list[pd.DataFrame] = []
    platt_predictions: list[pd.DataFrame] = []
    platt_edges: dict[str, tuple[float, ...]] = {}

    for fold in FROZEN_FOLDS:
        metrics, predictions = run_ablation_fold(model_table, calendar, fold.name)
        ablation_metrics_frames.append(metrics)
        ablation_prediction_frames.append(predictions)

        bundle = fit_full_hgb_fold(model_table, calendar, fold.name)
        cal_metrics, cal_predictions, edges = calibration_candidates(bundle)
        calibration_metric_frames.append(cal_metrics)
        calibration_prediction_frames.append(cal_predictions)
        platt_predictions.append(cal_predictions[cal_predictions["calibrator"].eq("PLATT")].copy())
        platt_edges[fold.name] = edges["PLATT"]

    ablation_metrics = pd.concat(ablation_metrics_frames, ignore_index=True)
    ablation_predictions = pd.concat(ablation_prediction_frames, ignore_index=True)
    attribution = attribution_summary(ablation_metrics)

    full_predictions = ablation_predictions[ablation_predictions["variant"].eq("HGB_FULL")].copy()
    quintiled = assign_cross_sectional_quintiles(full_predictions)
    quintiles = quintile_summary(quintiled)
    quintile_gate = _quintile_gate(quintiles)

    calibration_fold_metrics = pd.concat(calibration_metric_frames, ignore_index=True)
    calibration_predictions = pd.concat(calibration_prediction_frames, ignore_index=True)
    pooled_calibration = pooled_calibration_metrics(calibration_fold_metrics, calibration_predictions)
    selected_calibrator = select_calibrator(pooled_calibration)

    base_fold = reference_metrics[reference_metrics["model"].eq("base_rate")][
        ["fold", "brier", "ece", "prevalence_gap", "rows"]
    ].copy()
    base_pooled = pooled_reference[pooled_reference["model"].eq("base_rate")].iloc[0]
    calibration_gate = calibration_readiness(
        selected_calibrator,
        calibration_fold_metrics,
        pooled_calibration,
        base_fold,
        base_pooled_brier=float(base_pooled["brier"]),
        base_weighted_ece=float(base_pooled["weighted_fold_ece"]),
    )

    regime_thresholds, regime_metrics = regime_diagnostics(
        feature_table,
        pd.concat(platt_predictions, ignore_index=True),
        platt_edges,
        calendar,
    )

    decision = _runtime_decision(ranking_gate, quintile_gate, calibration_gate)
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs: dict[str, Path] = {
        "reference_fold_metrics": output_dir / "stage4_reference_fold_metrics.csv",
        "reference_pooled_metrics": output_dir / "stage4_reference_pooled_metrics.csv",
        "ablation_fold_metrics": output_dir / "stage4_ablation_fold_metrics.csv",
        "ablation_predictions": output_dir / "stage4_ablation_oof_predictions.parquet",
        "feature_attribution": output_dir / "stage4_feature_attribution.csv",
        "quintile_rows": output_dir / "stage4_cross_sectional_quintile_rows.parquet",
        "quintile_summary": output_dir / "stage4_cross_sectional_quintile_summary.csv",
        "calibration_fold_metrics": output_dir / "stage4_calibration_fold_metrics.csv",
        "calibration_pooled_metrics": output_dir / "stage4_calibration_pooled_metrics.csv",
        "calibration_predictions": output_dir / "stage4_calibration_oof_predictions.parquet",
        "regime_thresholds": output_dir / "stage4_regime_thresholds.csv",
        "regime_metrics": output_dir / "stage4_regime_metrics.csv",
    }

    reference_metrics.to_csv(outputs["reference_fold_metrics"], index=False)
    pooled_reference.to_csv(outputs["reference_pooled_metrics"], index=False)
    ablation_metrics.to_csv(outputs["ablation_fold_metrics"], index=False)
    write_parquet_atomic(ablation_predictions, outputs["ablation_predictions"])
    attribution.to_csv(outputs["feature_attribution"], index=False)
    write_parquet_atomic(quintiled, outputs["quintile_rows"])
    quintiles.to_csv(outputs["quintile_summary"], index=False)
    calibration_fold_metrics.to_csv(outputs["calibration_fold_metrics"], index=False)
    pooled_calibration.to_csv(outputs["calibration_pooled_metrics"], index=False)
    write_parquet_atomic(calibration_predictions, outputs["calibration_predictions"])
    regime_thresholds.to_csv(outputs["regime_thresholds"], index=False)
    regime_metrics.to_csv(outputs["regime_metrics"], index=False)

    summary: dict[str, object] = {
        "stage": "STAGE4_DEVELOPMENT",
        "decision": decision,
        "code_commit": code_commit,
        "input_hashes": {
            "stage3_model_table": FROZEN_STAGE3_MODEL_TABLE_SHA256,
            "stage3_feature_table": FROZEN_STAGE3_FEATURE_TABLE_SHA256,
            "stage3_summary": FROZEN_STAGE3_SUMMARY_SHA256,
        },
        "stage3_holdout_outcome_accessed": stage3_summary.get("holdout_outcome_accessed"),
        "holdout_outcome_accessed": False,
        "locked_holdout_start_index": LOCKED_HOLDOUT_START_INDEX,
        "locked_holdout_start_date": pd.Timestamp(calendar[1008]).date().isoformat(),
        "specification_hashes": _repo_spec_hashes(),
        "dependency_versions": _dependency_versions(),
        "random_seed": 42,
        "calibrator_family": list(CALIBRATOR_ORDER),
        "selected_calibrator": selected_calibrator,
        "ranking_gate": ranking_gate,
        "quintile_gate": quintile_gate,
        "calibration_gate": calibration_gate,
        "feature_attribution": attribution.to_dict(orient="records"),
        "artifact_hashes": {name: sha256_file(path) for name, path in outputs.items()},
    }
    summary_path = output_dir / "stage4_development_summary.json"
    _atomic_json(summary, summary_path)
    summary["summary_path"] = str(summary_path)
    summary["summary_sha256"] = sha256_file(summary_path)
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run frozen Stage-4 development diagnostics without holdout access")
    parser.add_argument("--model-table", required=True, type=Path)
    parser.add_argument("--feature-table", required=True, type=Path)
    parser.add_argument("--stage3-summary", required=True, type=Path)
    parser.add_argument("--calendar", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--code-commit", required=True)
    parser.add_argument("--calendar-column", default="date")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    summary = run_stage4_development(
        model_table_path=args.model_table,
        feature_table_path=args.feature_table,
        stage3_summary_path=args.stage3_summary,
        calendar_path=args.calendar,
        output_dir=args.output_dir,
        code_commit=args.code_commit,
        calendar_column=args.calendar_column,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
