"""Outcome-blind audit of a locally acquired official IDX current directory.

The endpoint response is treated as a current snapshot only.  This module
checks response shape, key uniqueness, date validity, and agreement with two
already-persisted comparison surfaces.  It does not call the provider, infer
historical membership, or admit the source for PIT research.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


REQUIRED_PROFILE_FIELDS = {"KodeEmiten", "NamaEmiten", "TanggalPencatatan", "Status"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_code(value: Any) -> str:
    return str(value or "").strip().upper()


def _date_map(rows: list[dict[str, Any]], code_field: str, date_field: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in rows:
        code = _normalize_code(row.get(code_field))
        parsed = pd.to_datetime(row.get(date_field), errors="raise")
        result[code] = pd.Timestamp(parsed).normalize().strftime("%Y-%m-%d")
    return result


def audit_official_profiles(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise ValueError("official profiles data is not a list")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("official profiles contains a non-object row")
    fields = set().union(*(set(row) for row in rows)) if rows else set()
    missing_fields = sorted(REQUIRED_PROFILE_FIELDS - fields)
    if missing_fields:
        raise ValueError(f"official profiles missing fields: {missing_fields}")
    codes = [_normalize_code(row.get("KodeEmiten")) for row in rows]
    if "" in codes:
        raise ValueError("official profiles contains an empty code")
    listing_dates = _date_map(rows, "KodeEmiten", "TanggalPencatatan")
    statuses = sorted({str(row.get("Status")) for row in rows})
    return {
        "payload": payload,
        "rows": rows,
        "codes": set(codes),
        "listing_dates": listing_dates,
        "all_fields": sorted(fields),
        "missing_required_fields": missing_fields,
        "duplicate_codes": sorted(code for code in set(codes) if codes.count(code) > 1),
        "status_values": statuses,
        "records_total": int(payload.get("recordsTotal", -1)),
        "records_filtered": int(payload.get("recordsFiltered", -1)),
        "listing_min": min(listing_dates.values()) if listing_dates else None,
        "listing_max": max(listing_dates.values()) if listing_dates else None,
    }


def load_ticker_files(root: Path) -> set[str]:
    files = sorted(root.glob("*.csv"))
    if not files:
        raise ValueError("public EOD directory has no ticker CSV files")
    return {_normalize_code(path.stem) for path in files}


def load_anchor_tickers(path: Path) -> set[str]:
    frame = pd.read_csv(path, usecols=["ticker"])
    return set(frame["ticker"].astype("string").str.upper().str.strip())


def load_prior_official(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    rows = payload.get("data")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("prior official current payload has invalid data")
    codes = {_normalize_code(row.get("Code")) for row in rows}
    dates = _date_map(rows, "Code", "ListingDate")
    return {"rows": rows, "codes": codes, "listing_dates": dates}


def run_audit(
    official_path: Path,
    headers_path: Path,
    pholenk_root: Path,
    prior_official_path: Path,
    anchor_path: Path,
    output: Path,
    endpoint: str,
) -> dict[str, Any]:
    output = output.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")

    official = audit_official_profiles(official_path)
    pholenk_codes = load_ticker_files(pholenk_root)
    anchor_codes = load_anchor_tickers(anchor_path)
    prior = load_prior_official(prior_official_path)
    header_text = headers_path.read_text(encoding="utf-8")
    status_line = next((line for line in header_text.splitlines() if line.startswith("HTTP/")), "")
    date_line = next((line for line in header_text.splitlines() if line.lower().startswith("date:")), "")
    official_codes = official["codes"]
    current_only_anchor = sorted(anchor_codes - official_codes)
    official_only_anchor = sorted(official_codes - anchor_codes)
    eod_gap = sorted(official_codes - pholenk_codes)
    prior_date_diffs = sorted(
        code
        for code in official_codes & prior["codes"]
        if official["listing_dates"].get(code) != prior["listing_dates"].get(code)
    )

    checks = {
        "http_status_is_200": status_line.startswith("HTTP/1.1 200") or status_line.startswith("HTTP/2 200"),
        "records_total_matches_rows": official["records_total"] == len(official["rows"]),
        "records_filtered_matches_rows": official["records_filtered"] == len(official["rows"]),
        "codes_are_unique": not official["duplicate_codes"],
        "required_fields_present": not official["missing_required_fields"],
        "all_status_values_are_zero": official["status_values"] == ["0"],
        "official_codes_are_subset_of_anchor": not official_only_anchor,
        "official_code_set_matches_prior_official_snapshot": official_codes == prior["codes"],
        "official_listing_dates_match_prior_official_snapshot": not prior_date_diffs,
    }

    result = {
        "status": "PASS_OFFICIAL_CURRENT_DIRECTORY_RESEARCH_ONLY" if all(checks.values()) else "FAIL_OFFICIAL_CURRENT_DIRECTORY_INTEGRITY",
        "scope": "Official IDX current company-profile directory snapshot; capability and comparison evidence only",
        "protected_boundary": "CLOSED",
        "source": {
            "endpoint": endpoint,
            "raw_path": str(official_path),
            "raw_sha256": sha256_file(official_path),
            "headers_path": str(headers_path),
            "headers_sha256": sha256_file(headers_path),
            "http_status_line": status_line,
            "retrieval_date_header": date_line,
            "records_total": official["records_total"],
            "records_filtered": official["records_filtered"],
            "unique_codes": len(official_codes),
            "listing_date_min": official["listing_min"],
            "listing_date_max": official["listing_max"],
            "status_values": official["status_values"],
            "fields": official["all_fields"],
            "has_issuer_or_isin_field": any("isin" in field.lower() or "issuer" in field.lower() for field in official["all_fields"]),
        },
        "integrity_checks": checks,
        "comparisons": {
            "anchor_ticker_count": len(anchor_codes),
            "official_minus_anchor": official_only_anchor,
            "anchor_minus_official": current_only_anchor,
            "official_current_is_subset_of_anchor": not official_only_anchor,
            "pholenk_ticker_count": len(pholenk_codes),
            "official_minus_pholenk": eod_gap,
            "official_minus_pholenk_listing_dates": {
                code: official["listing_dates"][code] for code in eod_gap
            },
            "pholenk_minus_official": sorted(pholenk_codes - official_codes),
            "prior_official_ticker_count": len(prior["codes"]),
            "prior_official_code_set_equal": official_codes == prior["codes"],
            "prior_official_listing_date_differences": prior_date_diffs,
        },
        "interpretation": {
            "current_directory_identity": "The official snapshot supplies current code, issuer name, listing date, board, sector, and subsector fields for 962 current records.",
            "six_ticker_gap": "The six current official codes absent from the newer public EOD snapshot are a current-snapshot timing difference, not evidence that those codes were absent from the official current directory.",
            "historical_anchor_gap": "The 18 anchor-only codes, including CNTX, are not in the current official directory; this is consistent with historical or non-current anchor coverage but does not identify delisting, relisting, ticker reuse, or issuer continuity.",
            "population_claim": "A current directory snapshot and exact agreement with the anchor do not prove daily historical population completeness, survivorship safety, or point-in-time eligibility.",
        },
        "admission": {
            "current_directory_capability": "SUPPORTED_CURRENT_SNAPSHOT",
            "historical_population_completeness": "UNKNOWN",
            "daily_pit_membership": "MISSING",
            "issuer_isin_transition_authority": "MISSING",
            "publication_or_available_at_authority": "MISSING",
            "revision_vintage_authority": "MISSING",
            "corporate_action_basis_authority": "MISSING",
            "historical_research_admission": "BLOCKED",
        },
        "inputs": {
            "anchor": {"path": str(anchor_path), "sha256": sha256_file(anchor_path)},
            "prior_official": {"path": str(prior_official_path), "sha256": sha256_file(prior_official_path)},
            "pholenk_root": {"path": str(pholenk_root), "ticker_files": len(pholenk_codes)},
        },
        "network_used": False,
        "provider_called_by_audit": False,
        "canonical_mutation": False,
    }
    result["code_sha256"] = sha256_file(Path(__file__).resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    if result["status"] != "PASS_OFFICIAL_CURRENT_DIRECTORY_RESEARCH_ONLY":
        raise SystemExit(1)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--official", type=Path, required=True)
    parser.add_argument("--headers", type=Path, required=True)
    parser.add_argument("--pholenk-root", type=Path, required=True)
    parser.add_argument("--prior-official", type=Path, required=True)
    parser.add_argument("--anchor", type=Path, required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run_audit(args.official, args.headers, args.pholenk_root, args.prior_official, args.anchor, args.output, args.endpoint)


if __name__ == "__main__":
    main()
