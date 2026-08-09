from __future__ import annotations

import argparse
import json
import platform
from importlib.metadata import version
from pathlib import Path

import pandas as pd

from .provenance import sha256_file
from .research_stage4b import build_stage4b_predictions, candidate_metrics, stage4b_readiness
from .research_validation import normalize_calendar
from .storage import write_parquet_atomic


FROZEN_STAGE3_MODEL_TABLE_SHA256 = "c161911f1330eec12335c6e2711bdca045ad5cfdb1e52f789b1489e987a67189"
FROZEN_STAGE4_CALIBRATION_PREDICTIONS_SHA256 = "964d3bdbb39b3069deb8328b981150a634d9c2ba780759e9294baccd2e1869b5"
FROZEN_STAGE4_SUMMARY_SHA256 = "1d904314e01c1a03b1ffce1cdb6ff5cec4be4caa8723ae0b7413927258be3155"
LOCKED_HOLDOUT_START_INDEX = 1009
EXPECTED_ENVIRONMENT = {
    "python": "3.13.5",
    "numpy": "2.4.2",
    "pandas": "2.3.3",
    "pyarrow": "23.0.1",
    "scikit-learn": "1.8.0",
}


def _read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"unsupported table format: {path}")


def _versions() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "numpy": version("numpy"),
        "pandas": version("pandas"),
        "pyarrow": version("pyarrow"),
        "scikit-learn": version("scikit-learn"),
    }


def assert_frozen_environment() -> dict[str, str]:
    actual = _versions()
    mismatches = {name: {"expected": expected, "actual": actual.get(name)} for name, expected in EXPECTED_ENVIRONMENT.items() if actual.get(name) != expected}
    if mismatches:
        raise RuntimeError(f"Stage-4B numerical environment drift: {mismatches}")
    return actual


def _verify_hash(path: Path, expected: str, label: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"{label} hash mismatch: expected={expected} actual={actual}")


def _load_stage4_summary(path: Path) -> dict[str, object]:
    _verify_hash(path, FROZEN_STAGE4_SUMMARY_SHA256, "Stage-4 summary")
    summary = json.loads(path.read_text(encoding="utf-8"))
    if bool(summary.get("holdout_outcome_accessed", True)):
        raise RuntimeError("Stage-4 summary does not prove holdout_outcome_accessed=false")
    if int(summary.get("locked_holdout_start_index", -1)) != LOCKED_HOLDOUT_START_INDEX:
        raise RuntimeError("Stage-4 summary holdout boundary mismatch")
    if str(summary.get("decision")) != "STAGE4_RANKING_GO_CALIBRATION_BLOCKED":
        raise RuntimeError(f"unexpected Stage-4 parent decision: {summary.get('decision')}")
    return summary


def _calendar(path: Path, column: str) -> pd.DatetimeIndex:
    frame = _read_table(path)
    if column not in frame.columns:
        raise ValueError(f"calendar column {column!r} absent")
    return normalize_calendar(frame[column])


def _assert_no_holdout_rows(frame: pd.DataFrame, calendar: pd.DatetimeIndex, label: str) -> pd.DataFrame:
    if "date" not in frame.columns:
        raise ValueError(f"{label} missing date")
    result = frame.copy()
    result["date"] = pd.to_datetime(result["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if result["date"].isna().any():
        raise ValueError(f"{label} contains invalid date")
    holdout_start = pd.Timestamp(calendar[LOCKED_HOLDOUT_START_INDEX - 1])
    if (result["date"] >= holdout_start).any():
        first = result.loc[result["date"] >= holdout_start, "date"].min()
        raise RuntimeError(f"{label} contains locked holdout row: {first}")
    return result


def _repo_spec_hashes() -> dict[str, str]:
    root = Path(__file__).resolve().parents[2]
    files = {
        "research_specification_v1": root / "docs" / "RESEARCH_SPECIFICATION_V1.md",
        "stage4_research_plan_v1": root / "docs" / "STAGE4_RESEARCH_PLAN_V1.md",
        "stage4b_calibration_plan_v1": root / "docs" / "STAGE4B_CALIBRATION_PLAN_V1.md",
    }
    missing = [str(path) for path in files.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing frozen specification files: {missing}")
    return {name: sha256_file(path) for name, path in files.items()}


def _atomic_json(value: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    temp.replace(path)


def run_stage4b_development(
    *,
    model_table_path: Path,
    stage4_calibration_predictions_path: Path,
    stage4_summary_path: Path,
    calendar_path: Path,
    output_dir: Path,
    code_commit: str,
    calendar_column: str = "date",
) -> dict[str, object]:
    environment = assert_frozen_environment()
    _verify_hash(model_table_path, FROZEN_STAGE3_MODEL_TABLE_SHA256, "Stage-3 model table")
    _verify_hash(
        stage4_calibration_predictions_path,
        FROZEN_STAGE4_CALIBRATION_PREDICTIONS_SHA256,
        "Stage-4 calibration predictions",
    )
    parent_summary = _load_stage4_summary(stage4_summary_path)
    calendar = _calendar(calendar_path, calendar_column)
    model_table = _assert_no_holdout_rows(_read_table(model_table_path), calendar, "Stage-3 model table")
    predictions = _assert_no_holdout_rows(
        _read_table(stage4_calibration_predictions_path), calendar, "Stage-4 calibration predictions"
    )

    candidate_predictions, priors, audit = build_stage4b_predictions(model_table, predictions, calendar)
    fold_metrics, pooled_metrics = candidate_metrics(candidate_predictions)
    readiness = stage4b_readiness(
        fold_metrics,
        pooled_metrics,
        audit,
        holdout_outcome_accessed=False,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "candidate_predictions": output_dir / "stage4b_candidate_oof_predictions.parquet",
        "fold_priors": output_dir / "stage4b_fold_reference_priors.csv",
        "causal_prior_audit": output_dir / "stage4b_causal_prior_audit.csv",
        "fold_metrics": output_dir / "stage4b_fold_metrics.csv",
        "pooled_metrics": output_dir / "stage4b_pooled_metrics.csv",
    }
    write_parquet_atomic(candidate_predictions, outputs["candidate_predictions"])
    priors.to_csv(outputs["fold_priors"], index=False)
    audit.to_csv(outputs["causal_prior_audit"], index=False)
    fold_metrics.to_csv(outputs["fold_metrics"], index=False)
    pooled_metrics.to_csv(outputs["pooled_metrics"], index=False)

    summary: dict[str, object] = {
        "stage": "STAGE4B_CAUSAL_CALIBRATION",
        "decision": readiness["decision"],
        "code_commit": code_commit,
        "environment": environment,
        "input_hashes": {
            "stage3_model_table": FROZEN_STAGE3_MODEL_TABLE_SHA256,
            "stage4_calibration_predictions": FROZEN_STAGE4_CALIBRATION_PREDICTIONS_SHA256,
            "stage4_summary": FROZEN_STAGE4_SUMMARY_SHA256,
        },
        "specification_hashes": _repo_spec_hashes(),
        "parent_stage4_decision": parent_summary.get("decision"),
        "holdout_outcome_accessed": False,
        "locked_holdout_start_index": LOCKED_HOLDOUT_START_INDEX,
        "locked_holdout_start_date": pd.Timestamp(calendar[LOCKED_HOLDOUT_START_INDEX - 1]).date().isoformat(),
        "readiness": readiness,
        "artifact_hashes": {name: sha256_file(path) for name, path in outputs.items()},
    }
    summary_path = output_dir / "stage4b_development_summary.json"
    _atomic_json(summary, summary_path)
    summary["summary_path"] = str(summary_path)
    summary["summary_sha256"] = sha256_file(summary_path)
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run frozen Stage-4B causal prior-shift calibration research")
    parser.add_argument("--model-table", required=True, type=Path)
    parser.add_argument("--stage4-calibration-predictions", required=True, type=Path)
    parser.add_argument("--stage4-summary", required=True, type=Path)
    parser.add_argument("--calendar", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--code-commit", required=True)
    parser.add_argument("--calendar-column", default="date")
    return parser


def main() -> int:
    args = _parser().parse_args()
    summary = run_stage4b_development(
        model_table_path=args.model_table,
        stage4_calibration_predictions_path=args.stage4_calibration_predictions,
        stage4_summary_path=args.stage4_summary,
        calendar_path=args.calendar,
        output_dir=args.output_dir,
        code_commit=args.code_commit,
        calendar_column=args.calendar_column,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
