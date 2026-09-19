"""Outcome-blind capability audit for the historical official foreign-flow archive.

The audit reads only the explicitly supplied local archive and its official
session calendar. It verifies persisted hashes, normalized schema/key
integrity, arithmetic, coverage, and acquisition metadata. It does not call
the provider, open targets/outcomes, or construct a feature.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


REQUIRED_COLUMNS = [
    "ticker",
    "session_date",
    "foreign_buy",
    "foreign_sell",
    "foreign_net",
    "unit",
    "label_provenance",
    "acquisition_mode",
    "knowledge_at_utc",
    "source",
    "source_ref",
    "source_sha256",
]
NUMERIC_COLUMNS = ["foreign_buy", "foreign_sell", "foreign_net"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def finite_int_series(series: pd.Series) -> bool:
    numeric = pd.to_numeric(series, errors="coerce")
    return bool(numeric.notna().all() and (numeric.round() == numeric).all())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--archive-manifest", type=Path, required=True)
    parser.add_argument("--coverage-census", type=Path, required=True)
    parser.add_argument("--official-calendar", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    output = args.output.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")

    archive_manifest = json_load(args.archive_manifest)
    coverage = json_load(args.coverage_census)
    calendar = pd.read_csv(args.official_calendar)
    calendar_dates = set(pd.to_datetime(calendar["date"], errors="raise").dt.strftime("%Y-%m-%d"))

    artifact_records = archive_manifest.get("artifacts", [])
    artifact_hash_mismatches: list[str] = []
    artifact_missing: list[str] = []
    artifact_paths: set[str] = set()
    for record in artifact_records:
        relative = str(record.get("path", ""))
        artifact_paths.add(relative.replace("/", "\\"))
        path = root / Path(relative)
        if not path.is_file():
            artifact_missing.append(relative)
            continue
        actual = sha256_file(path)
        if actual != record.get("sha256"):
            artifact_hash_mismatches.append(relative)

    session_dirs = sorted(path for path in (root / "sessions").iterdir() if path.is_dir())
    frames: list[pd.DataFrame] = []
    session_results: list[dict[str, Any]] = []
    schema_set: set[tuple[str, ...]] = set()
    session_dates: list[str] = []
    session_manifest_flags: Counter[str] = Counter()
    row_count_manifest_mismatch: list[str] = []
    session_key_duplicates = 0
    arithmetic_exact = 0
    negative_buy = 0
    negative_sell = 0
    non_integer_numeric = 0
    date_mismatch_rows = 0
    source_sha_mismatch_rows = 0
    knowledge_time_mismatch_sessions = 0

    for session_dir in session_dirs:
        session_name = session_dir.name
        session_path = session_dir / "manifest.json"
        normalized_path = session_dir / "foreign_flow.parquet"
        raw_path = session_dir / "stock_summary.raw.json"
        session = json_load(session_path)
        session_dates.append(session_name)
        session_manifest_flags[str(session.get("publication_time_known"))] += 1
        session_manifest_flags[str(session.get("acquisition_mode"))] += 1
        session_manifest_flags[str(session.get("causality"))] += 1

        frame = pd.read_parquet(normalized_path)
        schema = tuple(str(column) for column in frame.columns)
        schema_set.add(schema)
        if list(schema) != REQUIRED_COLUMNS:
            raise ValueError(f"normalized schema mismatch in {normalized_path}: {schema}")
        frame["session_date"] = pd.to_datetime(frame["session_date"], errors="coerce")
        if frame["session_date"].isna().any():
            raise ValueError(f"invalid normalized session dates in {normalized_path}")
        date_mismatch_rows += int((frame["session_date"].dt.strftime("%Y-%m-%d") != session_name).sum())
        session_key_duplicates += int(frame.duplicated(["ticker", "session_date"]).sum())
        for column in NUMERIC_COLUMNS:
            if not finite_int_series(frame[column]):
                non_integer_numeric += int(frame[column].isna().sum())
        buy = pd.to_numeric(frame["foreign_buy"], errors="coerce")
        sell = pd.to_numeric(frame["foreign_sell"], errors="coerce")
        net = pd.to_numeric(frame["foreign_net"], errors="coerce")
        arithmetic_exact += int((net == buy - sell).sum())
        negative_buy += int((buy < 0).sum())
        negative_sell += int((sell < 0).sum())
        source_sha_mismatch_rows += int((frame["source_sha256"].astype(str) != str(session.get("raw_sha256"))).sum())
        knowledge_values = pd.to_datetime(frame["knowledge_at_utc"], errors="coerce", utc=True)
        expected_knowledge = pd.to_datetime(session.get("observed_available_at_utc"), errors="coerce", utc=True)
        if knowledge_values.isna().any() or expected_knowledge is pd.NaT or not (knowledge_values == expected_knowledge).all():
            knowledge_time_mismatch_sessions += 1
        if len(frame) != int(session.get("row_count", -1)):
            row_count_manifest_mismatch.append(session_name)
        frames.append(frame[["ticker", "session_date", *NUMERIC_COLUMNS]])
        session_results.append(
            {
                "session": session_name,
                "rows": int(len(frame)),
                "tickers": int(frame["ticker"].nunique()),
                "zero_flow_rows": int((net == 0).sum()),
                "publication_time_known": session.get("publication_time_known"),
                "acquisition_mode": session.get("acquisition_mode"),
                "causality": session.get("causality"),
                "knowledge_at_utc": session.get("observed_available_at_utc"),
                "source_sha256": session.get("raw_sha256"),
            }
        )

    full = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["ticker", "session_date", *NUMERIC_COLUMNS])
    full_key_duplicates = int(full.duplicated(["ticker", "session_date"]).sum())
    outside_calendar = sorted(set(session_dates) - calendar_dates)
    calendar_only = sorted(calendar_dates - set(session_dates))
    unique_tickers = int(full["ticker"].nunique()) if not full.empty else 0
    year_summary: dict[str, Any] = {}
    if not full.empty:
        full["year"] = full["session_date"].dt.year
        for year, group in full.groupby("year", sort=True):
            year_summary[str(int(year))] = {
                "rows": int(len(group)),
                "sessions": int(group["session_date"].nunique()),
                "tickers": int(group["ticker"].nunique()),
                "zero_flow_rows": int((group["foreign_net"] == 0).sum()),
            }

    raw_sample = json_load(root / "sessions" / session_dirs[0].name / "stock_summary.raw.json") if session_dirs else {}
    raw_rows = raw_sample.get("data", [])
    raw_fields = sorted(raw_rows[0].keys()) if raw_rows and isinstance(raw_rows[0], dict) else []
    normalized_identity_fields = {"ticker", "session_date"}
    raw_identity_fields = sorted(set(raw_fields) & {"StockCode", "StockName", "IDStockSummary", "ISIN", "Issuer"})

    structural_checks = {
        "archive_artifact_count_matches_manifest": len(artifact_records) == int(archive_manifest.get("artifact_count", -1)),
        "all_declared_artifacts_exist": not artifact_missing,
        "all_declared_artifact_hashes_match": not artifact_hash_mismatches,
        "session_directory_count_matches_manifest": len(session_dirs) == int(archive_manifest.get("session_count", -1)),
        "session_dates_exactly_match_official_calendar": not outside_calendar and not calendar_only,
        "normalized_schema_is_single_and_expected": schema_set == {tuple(REQUIRED_COLUMNS)},
        "no_within_session_duplicate_keys": session_key_duplicates == 0,
        "no_cross_session_duplicate_keys": full_key_duplicates == 0,
        "row_counts_match_session_manifests": not row_count_manifest_mismatch,
        "all_rows_have_exact_net_arithmetic": arithmetic_exact == len(full),
        "buy_sell_non_negative": negative_buy == 0 and negative_sell == 0,
        "normalized_dates_match_session_directory": date_mismatch_rows == 0,
        "normalized_source_sha_matches_raw_manifest": source_sha_mismatch_rows == 0,
        "normalized_knowledge_time_matches_session_observation": knowledge_time_mismatch_sessions == 0,
    }
    source_contract = {
        "acquisition_mode": archive_manifest.get("acquisition_mode"),
        "publication_time_unknown_all_sessions": session_manifest_flags.get("False", 0) == len(session_dirs),
        "declared_causality_rules": sorted({item.get("causality") for item in session_results}),
        "retrieval_time_is_not_publication_time": True,
        "normalized_identity_fields": sorted(normalized_identity_fields),
        "raw_identity_fields_observed": raw_identity_fields,
        "issuer_isin_fields_in_normalized_schema": False,
        "revision_vintage_fields_in_normalized_schema": False,
        "corporate_action_fields_in_normalized_schema": False,
        "admission_status": "SOURCE_ADMISSION_BLOCKED",
    }
    result = {
        "status": "PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED" if all(structural_checks.values()) else "FAIL_STRUCTURAL_INTEGRITY",
        "stage": "H_DATA_CAPABILITY_FOREIGN_FLOW_HISTORICAL_SOURCE_AUDIT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "outcome_accessed": False,
            "target_accessed": False,
            "provider_accessed": False,
            "network_used": False,
            "canonical_mutation": False,
            "feature_created": False,
            "candidate_created": False,
        },
        "source": {
            "archive_manifest": str(args.archive_manifest.resolve()),
            "coverage_census": str(args.coverage_census.resolve()),
            "official_calendar": str(args.official_calendar.resolve()),
            "archive_manifest_sha256": sha256_file(args.archive_manifest),
            "coverage_census_sha256": sha256_file(args.coverage_census),
            "official_calendar_sha256": sha256_file(args.official_calendar),
            "archive_status": archive_manifest.get("status"),
            "source": archive_manifest.get("source"),
            "unit": archive_manifest.get("unit"),
            "row_count": int(len(full)),
            "session_count": int(len(session_dirs)),
            "ticker_count": unique_tickers,
            "first_session": min(session_dates) if session_dates else None,
            "last_session": max(session_dates) if session_dates else None,
        },
        "structural_checks": structural_checks,
        "structural_details": {
            "artifact_count": len(artifact_records),
            "artifact_missing": artifact_missing,
            "artifact_hash_mismatches": artifact_hash_mismatches,
            "session_key_duplicates": session_key_duplicates,
            "cross_session_key_duplicates": full_key_duplicates,
            "row_count_manifest_mismatch": row_count_manifest_mismatch,
            "arithmetic_exact_rows": arithmetic_exact,
            "negative_buy_rows": negative_buy,
            "negative_sell_rows": negative_sell,
            "date_mismatch_rows": date_mismatch_rows,
            "source_sha_mismatch_rows": source_sha_mismatch_rows,
            "knowledge_time_mismatch_sessions": knowledge_time_mismatch_sessions,
            "outside_official_calendar": outside_calendar,
            "calendar_only_sessions": calendar_only,
            "year_summary": year_summary,
            "coverage_zero_flow_rows": coverage.get("zero_flow_rows"),
            "coverage_zero_flow_prevalence": coverage.get("zero_flow_prevalence"),
            "raw_sample_fields": raw_fields,
        },
        "source_contract": source_contract,
        "session_manifest_summary": {
            "publication_time_known_values": dict(session_manifest_flags),
            "session_result_count": len(session_results),
        },
        "source_hashes": {
            "archive_manifest": sha256_file(args.archive_manifest),
            "coverage_census": sha256_file(args.coverage_census),
            "official_calendar": sha256_file(args.official_calendar),
        },
        "code_sha256": sha256_file(Path(__file__)),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output_sha256": sha256_file(output), "code_sha256": result["code_sha256"]}, indent=2))
    if not all(structural_checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
