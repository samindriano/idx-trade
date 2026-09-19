"""Outcome-blind structural audit for the local IDX LBRE free-float corpus.

The audit verifies the persisted artifact manifest and normalized lineage
surfaces. It does not call the provider, open targets/outcomes, alter source
files, or construct a feature/universe mask.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
ADMITTED_FIELDS = {
    "record_id",
    "ticker",
    "as_of_date",
    "free_float_pct",
    "free_float_shares",
    "published_at",
    "source_sha256",
    "metadata_source_sha256",
    "revision_kind",
    "source_family",
}
RAW_PARSED_FIELDS = {
    "candidate_id",
    "ticker",
    "as_of_date",
    "free_float_pct",
    "free_float_shares",
    "published_at",
    "source_sha256",
    "metadata_source_sha256",
    "revision_kind",
    "parse_status",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def json_list(path: Path) -> list[dict[str, Any]]:
    payload = load_json(path)
    if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
        raise ValueError(f"expected list of objects: {path}")
    return payload


def check_manifest_file(root: Path, record: dict[str, Any]) -> tuple[str, str]:
    relative = str(record.get("path", ""))
    path = root / Path(relative)
    if not path.is_file():
        return "missing", relative
    if path.stat().st_size != int(record.get("bytes", -1)):
        return "bytes", relative
    if sha256_file(path) != str(record.get("sha256", "")):
        return "hash", relative
    return "ok", relative


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    output = args.output.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")

    manifest_path = root / "artifact_manifest.json"
    manifest_sha_path = root / "artifact_manifest.sha256"
    normalized = root / "normalized"
    reports = root / "reports"
    manifest = load_json(manifest_path)
    manifest_files = manifest.get("files", [])
    if not isinstance(manifest_files, list):
        raise ValueError("manifest files must be a list")

    manifest_results: list[tuple[str, str]] = []
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(check_manifest_file, root, record) for record in manifest_files]
        for future in futures:
            manifest_results.append(future.result())
    manifest_counts = {status: sum(item[0] == status for item in manifest_results) for status in ("ok", "missing", "bytes", "hash")}
    manifest_sha_text = manifest_sha_path.read_text(encoding="utf-8").strip().split()[0]
    manifest_actual_sha = sha256_file(manifest_path)

    canonical = json_list(normalized / "lbre_canonical_observations.json")
    admitted = json_list(normalized / "lbre_admitted_observations.json")
    current = json_list(normalized / "lbre_current_observations.json")
    exact = json_list(normalized / "lbre_exact_observations.json")
    replay = load_json(reports / "lbre_replay_summary.json")
    lineage = load_json(reports / "lbre_lineage_audit.json")
    parse_audit_payload = load_json(reports / "lbre_parse_audit.json")
    parse_audit = parse_audit_payload.get("audit_rows", []) if isinstance(parse_audit_payload, dict) else []
    if not isinstance(parse_audit, list) or any(not isinstance(row, dict) for row in parse_audit):
        raise ValueError("parse audit audit_rows must be a list of objects")
    monthly_census = load_json(reports / "monthly_census.json")

    all_rows = {"canonical": canonical, "admitted": admitted, "current": current, "exact": exact}
    field_failures: dict[str, int] = {}
    invalid_dates: dict[str, int] = {}
    invalid_published_at: dict[str, int] = {}
    invalid_pct: dict[str, int] = {}
    invalid_shares: dict[str, int] = {}
    invalid_hashes: dict[str, int] = {}
    duplicate_record_ids: dict[str, int] = {}
    duplicate_keys: dict[str, int] = {}
    revision_counts: dict[str, dict[str, int]] = {}
    for name, rows in all_rows.items():
        required_fields = ADMITTED_FIELDS if name in {"admitted", "current"} else RAW_PARSED_FIELDS
        field_failures[name] = sum(1 for row in rows if not required_fields.issubset(row))
        invalid_dates[name] = sum(not isinstance(row.get("as_of_date"), str) or not row.get("as_of_date") or _parse_date(row.get("as_of_date")) is None for row in rows)
        invalid_published_at[name] = sum(_parse_datetime(row.get("published_at")) is None for row in rows)
        invalid_pct[name] = sum(not isinstance(row.get("free_float_pct"), (int, float)) or not 0 <= float(row["free_float_pct"]) <= 100 for row in rows)
        invalid_shares[name] = sum(not isinstance(row.get("free_float_shares"), (int, float)) or float(row["free_float_shares"]) < 0 for row in rows)
        invalid_hashes[name] = sum(not SHA256_RE.fullmatch(str(row.get(field, ""))) for row in rows for field in ("source_sha256", "metadata_source_sha256"))
        record_ids = [str(row.get("record_id", "")) for row in rows if "record_id" in row]
        keys = [(str(row.get("ticker", "")), str(row.get("as_of_date", ""))) for row in rows]
        duplicate_record_ids[name] = len(record_ids) - len(set(record_ids)) if record_ids else 0
        duplicate_keys[name] = len(keys) - len(set(keys))
        revisions: dict[str, int] = {}
        for row in rows:
            revision = str(row.get("revision_kind", ""))
            revisions[revision] = revisions.get(revision, 0) + 1
        revision_counts[name] = revisions

    source_key = lambda row: (str(row.get("ticker", "")), str(row.get("as_of_date", "")), str(row.get("source_sha256", "")))
    canonical_keys = {source_key(row) for row in canonical}
    admitted_keys = {source_key(row) for row in admitted}
    current_keys = {source_key(row) for row in current}
    admitted_not_canonical = sorted(admitted_keys - canonical_keys)
    current_not_admitted = sorted(current_keys - admitted_keys)
    current_non_original = sum(str(row.get("revision_kind")) != "ORIGINAL" for row in current)
    publication_before_asof = sum(
        (_parse_datetime(row.get("published_at")) or datetime.max.replace(tzinfo=timezone.utc)).date()
        < (_parse_date(row.get("as_of_date")) or datetime.max.date())
        for row in current
    )

    expected_counts = {
        "canonical": 25262,
        "admitted": 24394,
        "current": 23373,
        "exact": 28254,
        "manifest": 58671,
        "months": 27,
    }
    integrity_checks = {
        "manifest_declared_file_count_exact": int(manifest.get("file_count", -1)) == expected_counts["manifest"],
        "manifest_loaded_file_count_exact": len(manifest_files) == expected_counts["manifest"],
        "manifest_sha_sidecar_matches": manifest_sha_text.lower() == manifest_actual_sha.lower(),
        "all_manifest_files_present": manifest_counts["missing"] == 0,
        "all_manifest_file_bytes_match": manifest_counts["bytes"] == 0,
        "all_manifest_file_hashes_match": manifest_counts["hash"] == 0,
        "canonical_count_exact": len(canonical) == expected_counts["canonical"],
        "admitted_count_exact": len(admitted) == expected_counts["admitted"],
        "current_count_exact": len(current) == expected_counts["current"],
        "exact_count_exact": len(exact) == expected_counts["exact"],
        "all_required_fields_present": all(value == 0 for value in field_failures.values()),
        "all_as_of_dates_parse": all(value == 0 for value in invalid_dates.values()),
        "all_publication_timestamps_parse": all(value == 0 for value in invalid_published_at.values()),
        "all_free_float_percentages_valid": all(value == 0 for value in invalid_pct.values()),
        "all_free_float_shares_valid": all(value == 0 for value in invalid_shares.values()),
        "all_provenance_hash_fields_valid": all(value == 0 for value in invalid_hashes.values()),
        "current_record_ids_are_unique": duplicate_record_ids["current"] == 0,
        "current_ticker_date_keys_are_unique": duplicate_keys["current"] == 0,
        "admitted_source_keys_are_subset_of_canonical": not admitted_not_canonical,
        "current_source_keys_are_subset_of_admitted": not current_not_admitted,
        "monthly_census_count_exact": len(monthly_census.get("months", {})) == expected_counts["months"],
        "replay_summary_counts_match": replay.get("canonical_rows") == 25262 and replay.get("admitted") == 24394 and replay.get("current") == 23373 and replay.get("exact_input") == 28254,
        "lineage_summary_counts_match": lineage.get("admitted_count") == 24394 and lineage.get("current_count") == 23373,
    }

    semantic_findings = {
        "canonical_duplicate_record_ids": duplicate_record_ids["canonical"],
        "canonical_duplicate_ticker_date_rows": duplicate_keys["canonical"],
        "admitted_duplicate_ticker_date_rows": duplicate_keys["admitted"],
        "exact_duplicate_ticker_date_rows": duplicate_keys["exact"],
        "revision_counts": revision_counts,
        "current_non_original_rows": current_non_original,
        "publication_before_as_of_rows": publication_before_asof,
        "lineage_disposition_counts": lineage.get("lineage_disposition_counts", {}),
        "unresolved_lineage_rows": len(lineage.get("unresolved", [])),
        "parse_audit_rows": len(parse_audit),
        "replay_summary": replay,
        "monthly_census_first": min(monthly_census.get("months", {})) if monthly_census.get("months") else None,
        "monthly_census_last": max(monthly_census.get("months", {})) if monthly_census.get("months") else None,
        "daily_population_panel_available": False,
        "issuer_isin_transition_fields_available": False,
        "corporate_action_linkage_available": False,
        "revision_vintage_completeness": False,
        "public_availability_contract": False,
    }

    result = {
        "status": "PASS_STRUCTURAL_ONLY / SOURCE_REMEDIATION_REQUIRED" if all(integrity_checks.values()) else "FAIL_STRUCTURAL_INTEGRITY",
        "stage": "H_DATA_CAPABILITY_LBRE_FREE_FLOAT_SOURCE_AUDIT",
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
            "manifest": str(manifest_path),
            "manifest_sha256": manifest_actual_sha,
            "manifest_sidecar_sha256_text": manifest_sha_text,
            "canonical_sha256": sha256_file(normalized / "lbre_canonical_observations.json"),
            "admitted_sha256": sha256_file(normalized / "lbre_admitted_observations.json"),
            "current_sha256": sha256_file(normalized / "lbre_current_observations.json"),
            "exact_sha256": sha256_file(normalized / "lbre_exact_observations.json"),
            "replay_summary_sha256": sha256_file(reports / "lbre_replay_summary.json"),
            "lineage_audit_sha256": sha256_file(reports / "lbre_lineage_audit.json"),
            "parse_audit_sha256": sha256_file(reports / "lbre_parse_audit.json"),
            "monthly_census_sha256": sha256_file(reports / "monthly_census.json"),
        },
        "manifest_details": {
            "declared_file_count": int(manifest.get("file_count", -1)),
            "loaded_file_count": len(manifest_files),
            "verification_counts": manifest_counts,
            "failed_examples": [item[1] for item in manifest_results if item[0] != "ok"][:20],
            "schema": manifest.get("schema"),
            "target_count": manifest.get("target_count"),
            "target_first": manifest.get("target_first"),
            "target_last": manifest.get("target_last"),
        },
        "integrity_checks": integrity_checks,
        "integrity_details": {
            "field_failures": field_failures,
            "invalid_dates": invalid_dates,
            "invalid_published_at": invalid_published_at,
            "invalid_pct": invalid_pct,
            "invalid_shares": invalid_shares,
            "invalid_hashes": invalid_hashes,
            "admitted_not_canonical_examples": admitted_not_canonical[:20],
            "current_not_admitted_examples": current_not_admitted[:20],
        },
        "semantic_findings": semantic_findings,
        "source_contract": {
            "admission_status": "SOURCE_REMEDIATION_REQUIRED",
            "monthly_issuer_reports_not_daily_population_panel": True,
            "daily_population_panel_available": False,
            "issuer_isin_transition_fields_available": False,
            "corporate_action_linkage_available": False,
            "revision_vintage_completeness": False,
            "public_availability_contract": False,
            "coverage_gap_before_2024": True,
            "unresolved_lineage_rows": len(lineage.get("unresolved", [])),
        },
        "source_hashes": {
            "artifact_manifest": manifest_actual_sha,
            "artifact_manifest_sidecar": sha256_file(manifest_sha_path),
            "canonical_observations": sha256_file(normalized / "lbre_canonical_observations.json"),
            "admitted_observations": sha256_file(normalized / "lbre_admitted_observations.json"),
            "current_observations": sha256_file(normalized / "lbre_current_observations.json"),
            "exact_observations": sha256_file(normalized / "lbre_exact_observations.json"),
            "replay_summary": sha256_file(reports / "lbre_replay_summary.json"),
            "lineage_audit": sha256_file(reports / "lbre_lineage_audit.json"),
            "parse_audit": sha256_file(reports / "lbre_parse_audit.json"),
            "monthly_census": sha256_file(reports / "monthly_census.json"),
        },
        "code_sha256": sha256_file(Path(__file__)),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "manifest_counts": manifest_counts, "output_sha256": sha256_file(output), "code_sha256": result["code_sha256"]}, indent=2))
    if result["status"] != "PASS_STRUCTURAL_ONLY / SOURCE_REMEDIATION_REQUIRED":
        raise SystemExit(1)


def _parse_date(value: Any) -> Any:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


if __name__ == "__main__":
    main()
