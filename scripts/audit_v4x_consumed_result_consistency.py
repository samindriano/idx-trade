"""Read-only consistency audit for the already-consumed V4-3R result.

This script does not fit or score a model, change a gate, call a provider, or
access fresh/protected forward outcomes. It re-derives descriptive summaries
from the immutable V4-3R result files to detect reporting/aggregation mistakes
and to expose the conditioning of IC on target observability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


EXPECTED_MANIFEST_SHA256 = "05c00e5ab42adf34f9bffff4dd5237043d6d281b3e0abe1571f14a59eeb16fef"
MODES = ("control", "challenger")
HEADS = ("h5", "h10", "consensus")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"NOT_JSON_OBJECT:{path}")
    return value


def finite_mean(values: pd.Series) -> float | None:
    numeric = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    numeric = numeric[np.isfinite(numeric)]
    return float(numeric.mean()) if len(numeric) else None


def finite_quantile(values: list[float], q: float) -> float | None:
    array = np.asarray(values, dtype=float)
    array = array[np.isfinite(array)]
    return float(np.quantile(array, q, method="linear")) if len(array) else None


def audit_mode_head(root: Path, mode: str, head: str) -> dict[str, Any]:
    path = root / f"v4_3r_{mode}_{head}_date_metrics.csv"
    frame = pd.read_csv(path)
    if len(frame) != 600:
        raise RuntimeError(f"DATE_METRIC_ROW_COUNT_CHANGED:{mode}:{head}:{len(frame)}")
    required = {
        "date",
        "fold",
        "target_coverage_rate",
        "ic_admitted",
        "daily_ic",
    }
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"DATE_METRIC_COLUMNS_MISSING:{mode}:{head}:{sorted(missing)}")
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    if frame["date"].duplicated().any():
        raise RuntimeError(f"DATE_METRIC_DUPLICATE_DATE:{mode}:{head}")

    fold_rows: list[dict[str, Any]] = []
    for fold, block in frame.groupby("fold", sort=True):
        admitted = block["ic_admitted"].fillna(False).astype(bool)
        ic = pd.to_numeric(block.loc[admitted, "daily_ic"], errors="coerce")
        fold_rows.append(
            {
                "fold": int(fold),
                "ic_admitted_dates": int(admitted.sum()),
                "fold_mean_daily_ic": finite_mean(ic),
                "target_coverage_min": float(pd.to_numeric(block["target_coverage_rate"], errors="raise").min()),
                "target_coverage_mean": float(pd.to_numeric(block["target_coverage_rate"], errors="raise").mean()),
            }
        )
    if [row["fold"] for row in fold_rows] != [1, 2, 3, 4, 5, 6]:
        raise RuntimeError(f"FOLD_IDENTITY_CHANGED:{mode}:{head}")
    fold_means = [float(row["fold_mean_daily_ic"]) for row in fold_rows if row["fold_mean_daily_ic"] is not None]

    coverage = pd.to_numeric(frame["target_coverage_rate"], errors="coerce")
    daily_ic = pd.to_numeric(frame["daily_ic"], errors="coerce")
    buckets: list[dict[str, Any]] = []
    for label, low, high in (
        ("0.80_to_below_0.85", 0.80, 0.85),
        ("0.85_to_below_0.90", 0.85, 0.90),
        ("at_least_0.90", 0.90, 1.0000001),
    ):
        mask = coverage.ge(low) & coverage.lt(high) & daily_ic.notna()
        buckets.append(
            {
                "bucket": label,
                "dates": int(mask.sum()),
                "mean_daily_ic": finite_mean(daily_ic.loc[mask]),
            }
        )

    valid = coverage.notna() & daily_ic.notna()
    coverage_ic_corr = None
    if int(valid.sum()) >= 2 and coverage.loc[valid].nunique() > 1 and daily_ic.loc[valid].nunique() > 1:
        coverage_ic_corr = float(np.corrcoef(coverage.loc[valid], daily_ic.loc[valid])[0, 1])

    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "folds": fold_rows,
        "median_fold_mean_daily_ic": finite_quantile(fold_means, 0.50),
        "q25_fold_mean_daily_ic": finite_quantile(fold_means, 0.25),
        "positive_fold_count": int(sum(value > 0.0 for value in fold_means)),
        "coverage_ic_descriptive_correlation": coverage_ic_corr,
        "coverage_buckets": buckets,
    }


def audit_paired(root: Path, head: str) -> dict[str, Any]:
    path = root / f"v4_3r_paired_{head}_date_deltas.csv"
    frame = pd.read_csv(path)
    if len(frame) != 600:
        raise RuntimeError(f"PAIRED_ROW_COUNT_CHANGED:{head}:{len(frame)}")
    required = {"date", "fold", "delta_daily_ic"}
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"PAIRED_COLUMNS_MISSING:{head}:{sorted(missing)}")
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    fold_rows: list[dict[str, Any]] = []
    for fold, block in frame.groupby("fold", sort=True):
        delta = pd.to_numeric(block["delta_daily_ic"], errors="coerce")
        finite = delta[np.isfinite(delta)]
        fold_rows.append(
            {
                "fold": int(fold),
                "paired_ic_dates": int(len(finite)),
                "fold_mean_ic_delta": float(finite.mean()) if len(finite) else None,
            }
        )
    fold_means = [float(row["fold_mean_ic_delta"]) for row in fold_rows if row["fold_mean_ic_delta"] is not None]
    all_delta = pd.to_numeric(frame["delta_daily_ic"], errors="coerce")
    all_finite = all_delta[np.isfinite(all_delta)]
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "folds": fold_rows,
        "median_fold_mean_ic_delta": finite_quantile(fold_means, 0.50),
        "q25_fold_mean_ic_delta": finite_quantile(fold_means, 0.25),
        "positive_fold_ic_delta_count": int(sum(value > 0.0 for value in fold_means)),
        "mean_paired_daily_ic_delta": float(all_finite.mean()) if len(all_finite) else None,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical-result-root", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.historical_result_root.resolve()
    manifest_path = root / "MANIFEST.json"
    manifest_sha = sha256_file(manifest_path)
    if manifest_sha != EXPECTED_MANIFEST_SHA256:
        raise RuntimeError(f"MANIFEST_SHA_MISMATCH:{manifest_sha}!={EXPECTED_MANIFEST_SHA256}")
    manifest = read_json(manifest_path)
    summary = read_json(root / "summary.json")
    if manifest.get("protected_forward_accessed") is not False or manifest.get("provider_calls") is not False:
        raise RuntimeError("HISTORICAL_GUARD_CHANGED")

    absolute = {
        mode: {head: audit_mode_head(root, mode, head) for head in HEADS}
        for mode in MODES
    }
    paired = {head: audit_paired(root, head) for head in HEADS}

    control_consensus = absolute["control"]["consensus"]["median_fold_mean_daily_ic"]
    challenger_consensus = absolute["challenger"]["consensus"]["median_fold_mean_daily_ic"]
    difference_of_medians = None
    if control_consensus is not None and challenger_consensus is not None:
        difference_of_medians = float(challenger_consensus - control_consensus)

    recorded_control = summary["model_summaries"]["CONTROL"]["CONSENSUS"]["aggregate"]
    recorded_challenger = summary["model_summaries"]["CHALLENGER"]["CONSENSUS"]["aggregate"]
    recorded_paired = summary["decision"]["challenger_incremental_promotion"].get("inputs", {})

    output = {
        "schema_version": "v4x_consumed_result_consistency_audit_v1",
        "status": "V4X_CONSUMED_RESULT_DESCRIPTIVE_AUDIT_COMPLETE",
        "historical_result_root": str(root),
        "manifest_sha256": manifest_sha,
        "protected_forward_accessed": False,
        "provider_calls": False,
        "model_fit": False,
        "model_scored": False,
        "absolute": absolute,
        "paired": paired,
        "consensus_cross_check": {
            "recomputed_control_median_fold_mean_ic": control_consensus,
            "recorded_control_median_fold_mean_ic": recorded_control.get("median_fold_mean_daily_ic"),
            "recomputed_challenger_median_fold_mean_ic": challenger_consensus,
            "recorded_challenger_median_fold_mean_ic": recorded_challenger.get("median_fold_mean_daily_ic"),
            "difference_of_absolute_medians": difference_of_medians,
            "median_of_paired_fold_mean_deltas": paired["consensus"]["median_fold_mean_ic_delta"],
            "note": "Difference of absolute medians and median of paired fold deltas are different estimands and must not be conflated.",
        },
        "recorded_incremental_gate_inputs_if_present": recorded_paired,
        "interpretation_boundary": "Historical V4-3R outcomes were already consumed. This script only re-aggregates existing immutable result files and must not be used to retune V4-X1.",
    }
    print(json.dumps(output, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
