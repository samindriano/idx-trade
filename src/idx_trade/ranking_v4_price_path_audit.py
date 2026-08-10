from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .provenance import sha256_file
from .ranking_v2_candidate import _assert_clean_output_dir
from .ranking_v3_structure_lite import V3_B_FEATURE_COLUMNS
from .ranking_v4_price_path import assert_historical_boundary
from .ranking_v4_price_path_prepare import V4_B_CACHE_STATUS
from .research_v4_price_path import V4_B_FEATURE_COLUMNS


AUDIT_COLUMNS = (
    "ticker",
    "date",
    "signal_session_index",
    *V3_B_FEATURE_COLUMNS,
    *V4_B_FEATURE_COLUMNS,
)


def _summary(values: pd.Series) -> dict[str, Any]:
    numeric = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    finite = numeric[np.isfinite(numeric)]
    if len(finite) == 0:
        return {
            "rows": int(len(numeric)),
            "finite_rows": 0,
            "finite_rate": 0.0,
            "unique_finite": 0,
            "constant": True,
        }
    quantiles = np.quantile(finite, [0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99])
    return {
        "rows": int(len(numeric)),
        "finite_rows": int(len(finite)),
        "finite_rate": float(len(finite) / len(numeric)),
        "unique_finite": int(pd.Series(finite).nunique(dropna=True)),
        "constant": bool(np.nanmin(finite) == np.nanmax(finite)),
        "min": float(np.min(finite)),
        "p01": float(quantiles[0]),
        "p05": float(quantiles[1]),
        "p25": float(quantiles[2]),
        "p50": float(quantiles[3]),
        "p75": float(quantiles[4]),
        "p95": float(quantiles[5]),
        "p99": float(quantiles[6]),
        "max": float(np.max(finite)),
        "mean": float(np.mean(finite)),
        "std": float(np.std(finite)),
    }


def _correlation_records(frame: pd.DataFrame) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    numeric_columns = [*V3_B_FEATURE_COLUMNS, *V4_B_FEATURE_COLUMNS]
    numeric = frame[numeric_columns].apply(pd.to_numeric, errors="coerce")
    correlation = numeric.corr(method="spearman", min_periods=100)
    records: list[dict[str, Any]] = []
    high: list[dict[str, Any]] = []
    columns = list(correlation.columns)
    for i, left in enumerate(columns):
        for right in columns[i + 1 :]:
            value = correlation.loc[left, right]
            if not np.isfinite(value):
                continue
            if left not in V4_B_FEATURE_COLUMNS and right not in V4_B_FEATURE_COLUMNS:
                continue
            record = {
                "left": left,
                "right": right,
                "spearman": float(value),
                "abs_spearman": float(abs(value)),
            }
            records.append(record)
            if abs(float(value)) >= 0.95:
                high.append(record)
    records.sort(key=lambda item: (-item["abs_spearman"], item["left"], item["right"]))
    high.sort(key=lambda item: (-item["abs_spearman"], item["left"], item["right"]))
    return records, high


def audit_v4b_cache(
    *,
    cache_path: Path,
    manifest_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Outcome-blind audit: binary_target and outcome columns are never loaded."""

    started = time.perf_counter()
    _assert_clean_output_dir(output_dir)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != V4_B_CACHE_STATUS:
        raise RuntimeError("V4-B audit requires frozen pre-outcome cache manifest")
    actual_cache_sha = sha256_file(cache_path)
    if actual_cache_sha != manifest.get("cache_sha256"):
        raise RuntimeError("V4-B audit cache hash mismatch")
    if bool(manifest.get("outcome_metrics_computed", True)):
        raise RuntimeError("V4-B audit manifest claims outcome metrics were already computed")
    if bool(manifest.get("fresh_forward_accessed", True)):
        raise RuntimeError("V4-B audit manifest claims fresh-forward access")
    if bool(manifest.get("integration_candidate_materialized", True)):
        raise RuntimeError("V4-B audit manifest claims integration candidate materialization")

    frame = pd.read_parquet(cache_path, columns=list(AUDIT_COLUMNS))
    if frame.empty:
        raise RuntimeError("V4-B audit cache is empty")
    assert_historical_boundary(frame)
    if frame.duplicated(["ticker", "date"]).any():
        raise RuntimeError("V4-B audit found duplicate ticker/date rows")

    summaries = {column: _summary(frame[column]) for column in V4_B_FEATURE_COLUMNS}
    correlations, high_correlations = _correlation_records(frame)
    constant_features = [
        column for column, summary in summaries.items() if bool(summary.get("constant", False))
    ]
    low_coverage_features = [
        column
        for column, summary in summaries.items()
        if float(summary.get("finite_rate", 0.0)) < 0.80
    ]

    audit = {
        "status": "RANKING_V4_B_PRICE_PATH_OUTCOME_BLIND_AUDIT_COMPLETE",
        "cache_sha256": actual_cache_sha,
        "cache_manifest_sha256": sha256_file(manifest_path),
        "columns_loaded": list(AUDIT_COLUMNS),
        "binary_target_loaded": False,
        "outcome_columns_loaded": False,
        "rows": int(len(frame)),
        "tickers": int(frame["ticker"].nunique()),
        "first_signal_session_index": int(frame["signal_session_index"].min()),
        "last_signal_session_index": int(frame["signal_session_index"].max()),
        "feature_summary": summaries,
        "spearman_correlations_involving_v4b": correlations,
        "abs_spearman_ge_095": high_correlations,
        "constant_features": constant_features,
        "finite_rate_lt_080": low_coverage_features,
        "mechanical_review_required": bool(
            constant_features or low_coverage_features or high_correlations
        ),
        "outcome_metrics_computed": False,
        "fresh_forward_accessed": False,
        "post_1224_materialized": False,
        "elapsed_seconds": float(time.perf_counter() - started),
    }
    output_path = output_dir / "ranking_v4_b_price_path_outcome_blind_audit.json"
    output_path.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    audit["audit_sha256"] = sha256_file(output_path)
    return audit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Outcome-blind V4-B price-path cache audit")
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--cache-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = audit_v4b_cache(
        cache_path=args.cache,
        manifest_path=args.cache_manifest,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
