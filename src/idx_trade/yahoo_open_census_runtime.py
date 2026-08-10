from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .provenance import sha256_file
from .security_master import normalise_ticker
from .tier2_open_audit import _prepare_panel
from .yahoo_open_census import (
    DEFAULT_BACKOFF_SECONDS,
    DEFAULT_END_INCLUSIVE,
    DEFAULT_EXPECTED_PANEL_SHA256,
    DEFAULT_MAX_ATTEMPTS,
    DEFAULT_START,
    _csv_write,
    _json_write,
    _parquet_write,
    apply_verified_split_reconstruction,
    build_cache_manifest,
    build_full_direct_audit,
    fetch_universe_cached,
    summarize_census_rows,
)


def build_full_panel_derivative(
    panel: pd.DataFrame,
    audit: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Fill accepted Open evidence while preserving every original panel column."""

    original = _prepare_panel(panel).copy()
    evidence = audit[
        [
            "ticker",
            "date",
            "panel_open",
            "direct_admissible",
            "direct_candidate_open",
            "split_admissible",
            "split_reconstructed_open",
            "split_factor",
            "direct_diagnostic",
            "split_diagnostic",
            "cache_ref",
            "cache_sha256",
            "retrieved_at_utc",
        ]
    ].copy()
    merged = original.merge(
        evidence,
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )
    known = merged["open"].notna() & merged["open"].gt(0)
    direct = (~known) & merged["direct_admissible"].fillna(False)
    split = (~known) & ~direct & merged["split_admissible"].fillna(False)

    original_known = merged.loc[known, "open"].copy()
    merged.loc[direct, "open"] = merged.loc[direct, "direct_candidate_open"]
    merged.loc[split, "open"] = merged.loc[split, "split_reconstructed_open"]
    if not merged.loc[known, "open"].equals(original_known):
        raise RuntimeError("Existing Open changed while building full-panel derivative")

    provenance = pd.DataFrame(
        {
            "ticker": merged["ticker"],
            "date": merged["date"],
            "open_source": np.select(
                [known, direct, split],
                ["IMMUTABLE_PANEL", "YAHOO_YFINANCE", "YAHOO_YFINANCE"],
                default=None,
            ),
            "open_evidence_class": np.select(
                [known, direct, split],
                [
                    "EXISTING_IMMUTABLE",
                    "DIRECT_RAW_HLC_EXACT",
                    "SPLIT_SCALE_RECONSTRUCTABLE_EVIDENCE",
                ],
                default=None,
            ),
            "validation_status": np.select(
                [known, direct, split],
                ["PRESERVED", "ACCEPTED", "ACCEPTED"],
                default="UNRESOLVED",
            ),
            "source_cache_ref": merged["cache_ref"],
            "source_raw_sha256": merged["cache_sha256"],
            "retrieved_at_utc": merged["retrieved_at_utc"],
            "split_factor": np.where(split, merged["split_factor"], np.nan),
            "direct_diagnostic": merged["direct_diagnostic"],
            "split_diagnostic": merged["split_diagnostic"],
        }
    )
    derivative = merged[list(original.columns)].copy()
    initial_null = int(original["open"].isna().sum())
    final_null = int(derivative["open"].isna().sum())
    summary = {
        "direct_fills": int(direct.sum()),
        "split_fills": int(split.sum()),
        "total_fills": int((direct | split).sum()),
        "initial_null_open": initial_null,
        "final_null_open": final_null,
        "gap_closed": initial_null - final_null,
        "gap_closed_pct": float((initial_null - final_null) / initial_null) if initial_null else None,
        "all_original_columns_preserved": list(derivative.columns) == list(original.columns),
    }
    return derivative, provenance, summary


def run_yahoo_open_census_runtime(
    *,
    panel_path: str | Path,
    official_actions_path: str | Path,
    output_dir: str | Path,
    expected_panel_sha256: str = DEFAULT_EXPECTED_PANEL_SHA256,
    start: str = DEFAULT_START,
    end_inclusive: str = DEFAULT_END_INCLUSIVE,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
) -> dict[str, Any]:
    """Authoritative local runtime wrapper for the full-universe census."""

    panel_file = Path(panel_path)
    actions_file = Path(official_actions_path)
    output = Path(output_dir)
    if not panel_file.is_file() or not actions_file.is_file():
        raise FileNotFoundError("panel and official-actions inputs are required")
    output.mkdir(parents=True, exist_ok=True)
    cache_root = output / "raw_cache"

    panel_sha_before = sha256_file(panel_file)
    if panel_sha_before != expected_panel_sha256:
        raise RuntimeError(f"Immutable panel SHA mismatch before runtime: {panel_sha_before}")
    panel = _prepare_panel(pd.read_parquet(panel_file))
    actions = pd.read_csv(actions_file)
    tickers = sorted(panel["ticker"].dropna().map(normalise_ticker).unique())

    provider, statuses, fetch_summary = fetch_universe_cached(
        tickers,
        start=start,
        end_inclusive=end_inclusive,
        cache_root=cache_root,
        max_attempts=max_attempts,
        backoff_seconds=backoff_seconds,
    )
    _parquet_write(output / "yahoo_provider_rows.parquet", provider)
    _csv_write(output / "provider_ticker_status.csv", statuses)
    cache_manifest = build_cache_manifest(cache_root, statuses)
    _json_write(output / "raw_cache_manifest.json", cache_manifest)

    direct_audit, direct_summary = build_full_direct_audit(panel, provider)
    full_audit, split_summary = apply_verified_split_reconstruction(direct_audit, actions)
    derivative, provenance, derivative_summary = build_full_panel_derivative(panel, full_audit)
    by_year, rejection, temporal = summarize_census_rows(full_audit)

    _parquet_write(output / "yahoo_open_census_row_audit.parquet", full_audit)
    _parquet_write(output / "execution_open_candidate_panel.parquet", derivative)
    _parquet_write(output / "execution_open_candidate_provenance.parquet", provenance)
    _csv_write(output / "missing_open_by_year.csv", by_year)
    _csv_write(output / "missing_open_rejection_histogram.csv", rejection)
    _csv_write(output / "temporal_quality_summary.csv", temporal)

    unsupported = statuses.loc[
        ~statuses["status"].eq("SUCCESS"),
        ["ticker", "status", "provider_errors", "provider_logs"],
    ]
    _csv_write(output / "unsupported_or_error_tickers.csv", unsupported)

    panel_sha_after = sha256_file(panel_file)
    if panel_sha_after != panel_sha_before:
        raise RuntimeError(f"Immutable panel changed during runtime: {panel_sha_after}")

    status_counts = statuses["status"].value_counts().to_dict()
    summary: dict[str, Any] = {
        "status": "YAHOO_FULL_UNIVERSE_OPEN_CENSUS_COMPLETE",
        "decision": "STOP_FOR_INDEPENDENT_REVIEW",
        "panel_sha256_before": panel_sha_before,
        "panel_sha256_after": panel_sha_after,
        "panel_rows": int(len(panel)),
        "panel_tickers": int(len(tickers)),
        "window": {"start": start, "end_inclusive": end_inclusive},
        "fetch": {
            **fetch_summary,
            "status_counts": {str(key): int(value) for key, value in status_counts.items()},
        },
        "direct": direct_summary,
        "split": split_summary,
        "derivative": derivative_summary,
        "named_provider_status": {
            ticker: statuses.loc[statuses["ticker"].eq(ticker)].to_dict(orient="records")
            for ticker in ("FREN", "MASA", "MFIN", "PURE")
        },
        "execution_grade_promoted": False,
    }

    # Avoid circular/stale hashes: the artifact manifest deliberately excludes
    # itself and census_summary.json. The final summary then records its hash.
    artifact_files = sorted(
        path
        for path in output.iterdir()
        if path.is_file() and path.name not in {"artifact_manifest.json", "census_summary.json"}
    )
    artifact_manifest = {
        "runtime": "open_backfill_yahoo_census_v1_20260810",
        "files": {path.name: sha256_file(path) for path in artifact_files},
        "raw_cache_manifest_sha256": sha256_file(output / "raw_cache_manifest.json"),
        "execution_grade_promoted": False,
    }
    _json_write(output / "artifact_manifest.json", artifact_manifest)
    summary["artifact_manifest_sha256"] = sha256_file(output / "artifact_manifest.json")
    summary["derivative_panel_sha256"] = sha256_file(output / "execution_open_candidate_panel.parquet")
    summary["provenance_sha256"] = sha256_file(output / "execution_open_candidate_provenance.parquet")
    _json_write(output / "census_summary.json", summary)
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Authoritative full-universe Yahoo Open census runtime")
    parser.add_argument("--panel", required=True)
    parser.add_argument("--official-actions", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--expected-panel-sha256", default=DEFAULT_EXPECTED_PANEL_SHA256)
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end-inclusive", default=DEFAULT_END_INCLUSIVE)
    parser.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS)
    parser.add_argument("--backoff-seconds", type=float, default=DEFAULT_BACKOFF_SECONDS)
    return parser


def main() -> None:
    args = _parser().parse_args()
    result = run_yahoo_open_census_runtime(
        panel_path=args.panel,
        official_actions_path=args.official_actions,
        output_dir=args.output_dir,
        expected_panel_sha256=args.expected_panel_sha256,
        start=args.start,
        end_inclusive=args.end_inclusive,
        max_attempts=args.max_attempts,
        backoff_seconds=args.backoff_seconds,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
