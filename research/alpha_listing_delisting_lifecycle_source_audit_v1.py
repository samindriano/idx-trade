"""Outcome-blind structural audit for the local IDX listing/delisting archive.

This audit reads only the explicitly supplied local acquisition directory and
the already-persisted price-lifecycle summary.  It rehashes the monthly raw
responses, checks normalized CSV parity, and reports lifecycle anomalies.  It
does not call the provider, access targets/outcomes, or construct a feature.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


CURRENT_COLUMNS = [
    "ticker",
    "company_name",
    "listed_from",
    "listed_to",
    "source",
    "source_ref",
    "source_url",
    "evidence_level",
    "source_sha256",
]
DELISTING_COLUMNS = CURRENT_COLUMNS
RAW_REQUIRED = {"code", "issuerName", "ListingDate", "DeListingDate"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def parse_iso(value: str) -> pd.Timestamp | None:
    if not value:
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    return None if pd.isna(parsed) else pd.Timestamp(parsed).normalize()


def parse_human(value: str) -> pd.Timestamp | None:
    if not value:
        return None
    parsed = pd.to_datetime(value, dayfirst=True, errors="coerce")
    return None if pd.isna(parsed) else pd.Timestamp(parsed).normalize()


def canonical_date(value: str, parser: Any) -> str:
    parsed = parser(value)
    return "" if parsed is None else parsed.strftime("%Y-%m-%d")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--price-audit-summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    output = args.output.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")

    summary_path = root / "acquisition_summary.json"
    metadata_path = root / "delisting_month_metadata.json"
    current_path = root / "current_records_raw.csv"
    delisting_path = root / "delisting_records_raw.csv"
    conflict_path = root / "conflicting_lifecycle_rows.csv"
    excluded_path = root / "excluded_nonstandard_codes.csv"
    raw_dir = root / "raw_delisting"

    summary = load_json(summary_path)
    metadata = load_json(metadata_path)
    current_rows = read_csv(current_path)
    delisting_rows = read_csv(delisting_path)
    conflict_rows = read_csv(conflict_path)
    excluded_rows = read_csv(excluded_path)
    price_summary = load_json(args.price_audit_summary)

    metadata_by_ref: dict[str, dict[str, Any]] = {}
    raw_rows: list[dict[str, str]] = []
    raw_month_failures: list[str] = []
    raw_schema_failures: list[str] = []
    raw_row_count_mismatches: list[str] = []
    raw_hash_mismatches: list[str] = []
    raw_byte_mismatches: list[str] = []
    raw_file_missing: list[str] = []
    raw_status_failures: list[str] = []

    for record in metadata:
        year = int(record["year"])
        month = int(record["month"])
        source_ref = f"IDX_DELISTING_{year:04d}_{month:02d}"
        metadata_by_ref[source_ref] = record
        raw_path = raw_dir / f"{year:04d}_{month:02d}.json"
        if not raw_path.is_file():
            raw_file_missing.append(str(raw_path))
            continue
        actual_bytes = raw_path.stat().st_size
        actual_sha = sha256_file(raw_path)
        if actual_bytes != int(record.get("bytes", -1)):
            raw_byte_mismatches.append(source_ref)
        if actual_sha != record.get("sha256"):
            raw_hash_mismatches.append(source_ref)
        if int(record.get("status", -1)) != 200:
            raw_status_failures.append(source_ref)
        try:
            payload = load_json(raw_path)
            month_rows = payload.get("data", [])
            if not isinstance(month_rows, list):
                raise ValueError("data is not a list")
            if len(month_rows) != int(record.get("rows", -1)) or len(month_rows) != int(record.get("totalItems", -1)):
                raw_row_count_mismatches.append(source_ref)
            for item in month_rows:
                if not isinstance(item, dict) or not RAW_REQUIRED.issubset(item):
                    raw_schema_failures.append(source_ref)
                    continue
                raw_rows.append(
                    {
                        "ticker": str(item.get("code", "")).strip(),
                        "company_name": str(item.get("issuerName", "")).strip(),
                        "listed_from": str(item.get("ListingDate", "")).strip(),
                        "listed_to": str(item.get("DeListingDate", "")).strip(),
                        "source_ref": source_ref,
                    }
                )
        except (OSError, ValueError, json.JSONDecodeError):
            raw_month_failures.append(source_ref)

    current_columns = list(current_rows[0].keys()) if current_rows else []
    delisting_columns = list(delisting_rows[0].keys()) if delisting_rows else []
    current_sha = sha256_file(current_path)
    delisting_sha = sha256_file(delisting_path)
    conflict_sha = sha256_file(conflict_path)
    excluded_sha = sha256_file(excluded_path)
    metadata_sha = sha256_file(metadata_path)
    summary_sha = sha256_file(summary_path)

    current_tickers = [row.get("ticker", "").strip() for row in current_rows]
    delisting_tickers = [row.get("ticker", "").strip() for row in delisting_rows]
    current_source_hash_bad = [
        row.get("ticker", "").strip()
        for row in current_rows
        if row.get("source_sha256", "") != summary.get("current_sha256")
    ]
    current_from_invalid = sum(parse_iso(row.get("listed_from", "")) is None for row in current_rows)
    current_to_invalid = sum(bool(row.get("listed_to", "")) and parse_iso(row.get("listed_to", "")) is None for row in current_rows)
    delisting_from_invalid = sum(parse_human(row.get("listed_from", "")) is None for row in delisting_rows)
    delisting_to_invalid = sum(parse_human(row.get("listed_to", "")) is None for row in delisting_rows)

    delisting_date_order_violations: list[str] = []
    interval_records: list[dict[str, Any]] = []
    for row_index, row in enumerate(current_rows):
        start = parse_iso(row.get("listed_from", ""))
        end = parse_iso(row.get("listed_to", ""))
        interval_records.append({"row_id": f"current:{row_index}", "ticker": row.get("ticker", "").strip(), "start": start, "end": end, "source": "current"})
    for row_index, row in enumerate(delisting_rows):
        start = parse_human(row.get("listed_from", ""))
        end = parse_human(row.get("listed_to", ""))
        if start is not None and end is not None and end < start:
            delisting_date_order_violations.append(f"delisting:{row_index}")
        interval_records.append({"row_id": f"delisting:{row_index}", "ticker": row.get("ticker", "").strip(), "start": start, "end": end, "source": "delisting"})

    same_listing_date_conflict_ids: set[str] = set()
    same_listing_date_tickers: set[str] = set()
    grouped_dates: defaultdict[tuple[str, pd.Timestamp | None], list[dict[str, Any]]] = defaultdict(list)
    for record in interval_records:
        grouped_dates[(record["ticker"], record["start"])].append(record)
    for (ticker, _), records in grouped_dates.items():
        if len(records) > 1 and len({record["end"] for record in records}) > 1:
            same_listing_date_tickers.add(ticker)
            same_listing_date_conflict_ids.update(record["row_id"] for record in records)

    overlap_ids: set[str] = set()
    overlap_tickers: set[str] = set()
    by_ticker: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in interval_records:
        by_ticker[record["ticker"]].append(record)
    for ticker, records in by_ticker.items():
        for left_index, left in enumerate(records):
            if left["start"] is None:
                continue
            for right in records[left_index + 1 :]:
                if right["start"] is None:
                    continue
                left_end = left["end"] or pd.Timestamp.max.normalize()
                right_end = right["end"] or pd.Timestamp.max.normalize()
                if max(left["start"], right["start"]) <= min(left_end, right_end):
                    overlap_tickers.add(ticker)
                    overlap_ids.update((left["row_id"], right["row_id"]))

    source_ref_bad: list[str] = []
    source_sha_bad: list[str] = []
    for row in delisting_rows:
        ref = row.get("source_ref", "")
        expected = metadata_by_ref.get(ref)
        if expected is None:
            source_ref_bad.append(ref)
            continue
        raw_path = raw_dir / f"{int(expected['year']):04d}_{int(expected['month']):02d}.json"
        if row.get("source_sha256", "") != expected.get("sha256") or row.get("source_sha256", "") != sha256_file(raw_path):
            source_sha_bad.append(ref)

    raw_counter = Counter(
        (
            item["ticker"],
            item["company_name"],
            item["listed_from"],
            item["listed_to"],
            item["source_ref"],
        )
        for item in raw_rows
    )
    csv_counter = Counter(
        (
            row.get("ticker", "").strip(),
            row.get("company_name", "").strip(),
            row.get("listed_from", "").strip(),
            row.get("listed_to", "").strip(),
            row.get("source_ref", "").strip(),
        )
        for row in delisting_rows
    )

    integrity_checks = {
        "summary_and_metadata_exist": summary_path.is_file() and metadata_path.is_file(),
        "metadata_month_count_is_440": len(metadata) == 440,
        "all_monthly_raw_files_present": not raw_file_missing,
        "all_monthly_status_codes_are_200": not raw_status_failures,
        "all_monthly_bytes_match_metadata": not raw_byte_mismatches,
        "all_monthly_hashes_match_metadata": not raw_hash_mismatches,
        "all_monthly_json_payloads_parse": not raw_month_failures,
        "all_monthly_row_counts_match_metadata": not raw_row_count_mismatches,
        "all_monthly_rows_have_expected_fields": not raw_schema_failures,
        "current_columns_are_expected": current_columns == CURRENT_COLUMNS,
        "delisting_columns_are_expected": delisting_columns == DELISTING_COLUMNS,
        "current_row_count_matches_summary": len(current_rows) == int(summary.get("current_rows", -1)),
        "current_ticker_keys_are_unique": len(current_tickers) == len(set(current_tickers)),
        "current_date_fields_parse": current_from_invalid == 0 and current_to_invalid == 0,
        "current_row_source_hashes_match_summary": not current_source_hash_bad,
        "delisting_row_count_matches_summary": len(delisting_rows) == int(summary.get("delisting_records", -1)),
        "delisting_date_fields_parse": delisting_from_invalid == 0 and delisting_to_invalid == 0,
        "delisting_source_refs_are_known": not source_ref_bad,
        "delisting_source_hashes_match_raw": not source_sha_bad,
        "normalized_delisting_rows_match_raw_payloads": csv_counter == raw_counter,
        "conflict_artifact_is_present": conflict_path.is_file(),
        "excluded_artifact_is_present": excluded_path.is_file(),
        "price_summary_is_present": args.price_audit_summary.is_file(),
    }

    semantic_findings = {
        "delisting_before_listing_rows": len(delisting_date_order_violations),
        "delisting_before_listing_row_ids": delisting_date_order_violations,
        "same_listing_date_conflict_tickers": sorted(same_listing_date_tickers),
        "same_listing_date_conflict_rows": len(same_listing_date_conflict_ids),
        "overlap_tickers": sorted(overlap_tickers),
        "overlap_rows": len(overlap_ids),
        "conflicting_lifecycle_artifact_rows": len(conflict_rows),
        "conflicting_lifecycle_artifact_tickers": sorted({row.get("ticker", "").strip() for row in conflict_rows}),
        "excluded_nonstandard_code_rows": len(excluded_rows),
        "excluded_nonstandard_code_tickers": sorted({row.get("ticker", "").strip() for row in excluded_rows}),
        "price_summary": price_summary,
        "daily_pit_membership_available": False,
        "issuer_isin_transition_fields_available": False,
        "publication_time_available": False,
        "revision_vintage_fields_available": False,
        "corporate_action_fields_available": False,
    }

    result = {
        "status": "PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED" if all(integrity_checks.values()) else "FAIL_STRUCTURAL_INTEGRITY",
        "stage": "H_DATA_CAPABILITY_LISTING_DELISTING_LIFECYCLE_SOURCE_AUDIT",
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
            "root": str(root),
            "acquisition_summary": str(summary_path),
            "delisting_month_metadata": str(metadata_path),
            "current_records": str(current_path),
            "delisting_records": str(delisting_path),
            "raw_month_directory": str(raw_dir),
            "price_audit_summary": str(args.price_audit_summary.resolve()),
            "summary_sha256": summary_sha,
            "metadata_sha256": metadata_sha,
            "current_records_sha256": current_sha,
            "delisting_records_sha256": delisting_sha,
            "conflicting_lifecycle_rows_sha256": conflict_sha,
            "excluded_nonstandard_codes_sha256": excluded_sha,
            "price_audit_summary_sha256": sha256_file(args.price_audit_summary),
            "current_rows": len(current_rows),
            "current_tickers": len(set(current_tickers)),
            "delisting_rows": len(delisting_rows),
            "delisting_tickers": len(set(delisting_tickers)),
            "raw_months": len(metadata),
            "raw_rows": len(raw_rows),
        },
        "source_hashes": {
            "acquisition_summary": summary_sha,
            "metadata": metadata_sha,
            "current_records": current_sha,
            "delisting_records": delisting_sha,
            "conflicting_lifecycle_rows": conflict_sha,
            "excluded_nonstandard_codes": excluded_sha,
            "price_audit_summary": sha256_file(args.price_audit_summary),
        },
        "integrity_checks": integrity_checks,
        "integrity_details": {
            "raw_file_missing": raw_file_missing,
            "raw_status_failures": raw_status_failures,
            "raw_byte_mismatches": raw_byte_mismatches,
            "raw_hash_mismatches": raw_hash_mismatches,
            "raw_month_failures": raw_month_failures,
            "raw_schema_failures": raw_schema_failures,
            "raw_row_count_mismatches": raw_row_count_mismatches,
            "source_ref_bad": source_ref_bad,
            "source_sha_bad": source_sha_bad,
            "current_source_hash_bad": current_source_hash_bad,
            "current_date_invalid_counts": {"listed_from": current_from_invalid, "listed_to": current_to_invalid},
            "delisting_date_invalid_counts": {"listed_from": delisting_from_invalid, "listed_to": delisting_to_invalid},
            "normalized_raw_counter_difference": {
                "only_in_raw": list((raw_counter - csv_counter).elements())[:20],
                "only_in_csv": list((csv_counter - raw_counter).elements())[:20],
            },
        },
        "semantic_findings": semantic_findings,
        "source_contract": {
            "admission_status": "SOURCE_ADMISSION_BLOCKED",
            "reason": "event-level official lifecycle evidence lacks daily PIT membership, issuer/ISIN transition chain, publication-time semantics, revisions/vintages, and corporate-action linkage; six ticker-level lifecycle conflicts remain",
            "event_level_only": True,
            "daily_pit_membership_available": False,
            "issuer_isin_transition_fields_available": False,
            "publication_time_available": False,
            "revision_vintage_fields_available": False,
            "corporate_action_fields_available": False,
        },
        "code_sha256": sha256_file(Path(__file__)),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
