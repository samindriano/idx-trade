"""Outcome-blind audit for the local statutory free-float snapshot."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def check_declared(root: Path, record: dict[str, Any]) -> tuple[str, str]:
    rel = str(record.get("path", ""))
    path = root / Path(rel)
    if not path.is_file():
        return "missing", rel
    if path.stat().st_size != int(record.get("bytes", -1)):
        return "bytes", rel
    if sha256_file(path) != str(record.get("sha256", "")):
        return "hash", rel
    return "ok", rel


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
    manifest_sidecar = root / "artifact_manifest.sha256"
    manifest = load_json(manifest_path)
    declared = manifest.get("files", [])
    with ThreadPoolExecutor(max_workers=16) as executor:
        results = list(executor.map(lambda row: check_declared(root, row), declared))
    counts = {status: sum(item[0] == status for item in results) for status in ("ok", "missing", "bytes", "hash")}

    reused = manifest.get("reused_parent_sources", [])
    reused_results: list[dict[str, Any]] = []
    for item in reused:
        path = Path(str(item.get("path", "")))
        actual = sha256_file(path) if path.is_file() else None
        reused_results.append({"kind": item.get("kind"), "path": str(path), "declared_sha256": item.get("sha256"), "actual_sha256": actual, "matches": actual == item.get("sha256")})

    csv_path = root / "normalized" / "historical_ff_observations.csv"
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    required = {"record_id", "ticker", "as_of_date", "published_at", "free_float_shares", "free_float_pct", "source_family", "revision_kind", "source_sha256", "metadata_source_sha256"}
    csv_field_failures = sum(1 for row in csv_rows if not required.issubset(row))
    csv_bad_dates = sum(_date(row.get("as_of_date")) is None for row in csv_rows)
    csv_bad_numbers = sum(_number(row.get("free_float_shares")) is None or _number(row.get("free_float_pct")) is None for row in csv_rows)
    csv_key_duplicates = len(csv_rows) - len({(row.get("ticker"), row.get("as_of_date"), row.get("source_family")) for row in csv_rows})
    source_family_counts: dict[str, int] = {}
    for row in csv_rows:
        key = str(row.get("source_family", ""))
        source_family_counts[key] = source_family_counts.get(key, 0) + 1

    anchor_summary = load_json(root / "reports" / "anchor_and_census_summary.json")
    lbre_summary = load_json(root / "reports" / "lbre_census_summary.json")
    lbre_lineage = load_json(root / "reports" / "lbre_lineage.json")
    lbre_parse = load_json(root / "reports" / "lbre_parse_audit.json")
    target_audit = load_json(root / "reports" / "quarterly_anchor_target_audit.json")

    integrity_checks = {
        "manifest_file_count_exact": len(declared) == 2145 and int(manifest.get("new_file_count", -1)) == 2145,
        "manifest_sidecar_matches": manifest_sidecar.read_text(encoding="utf-8").split()[0].lower() == sha256_file(manifest_path),
        "all_manifest_files_present": counts["missing"] == 0,
        "all_manifest_bytes_match": counts["bytes"] == 0,
        "all_manifest_hashes_match": counts["hash"] == 0,
        "all_reused_parent_sources_match": all(item["matches"] for item in reused_results),
        "csv_rows_exact": len(csv_rows) == 1882,
        "csv_required_fields_present": csv_field_failures == 0,
        "csv_dates_parse": csv_bad_dates == 0,
        "csv_numeric_fields_parse": csv_bad_numbers == 0,
        "market_anchor_summary_exact": anchor_summary.get("market_2025_12_31_reported_rows") == 956 and anchor_summary.get("market_2025_12_31_exact_rows") == 923 and anchor_summary.get("market_2026_03_31_reported_rows") == 956 and anchor_summary.get("market_2026_03_31_exact_rows") == 0,
        "lbre_summary_exact": lbre_summary.get("exact_label_line_rows") == 1050 and lbre_summary.get("exact_rows_target") == 1015 and lbre_summary.get("parse_unresolved_rows") == 18,
        "lbre_lineage_summary_exact": lbre_lineage.get("admitted_rows") == 957 and lbre_lineage.get("excluded_rows") == 93,
        "lbre_parse_summary_exact": lbre_parse.get("candidate_count") == 1068 and lbre_parse.get("download_records") == 1064 and lbre_parse.get("parsed_exact_count") == 1050 and lbre_parse.get("failed_or_ambiguous_count") == 18,
    }
    result = {
        "status": "PASS_STRUCTURAL_ONLY / SOURCE_REMEDIATION_REQUIRED" if all(integrity_checks.values()) else "FAIL_STRUCTURAL_INTEGRITY",
        "stage": "H_DATA_CAPABILITY_STATUTORY_FREE_FLOAT_SOURCE_AUDIT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": {"outcome_accessed": False, "target_accessed": False, "provider_accessed": False, "network_used": False, "canonical_mutation": False, "feature_created": False, "candidate_created": False},
        "source": {
            "root": str(root),
            "manifest_sha256": sha256_file(manifest_path),
            "manifest_sidecar_sha256": sha256_file(manifest_sidecar),
            "new_manifest_files": len(declared),
            "reused_parent_sources": len(reused),
            "unified_csv_sha256": sha256_file(csv_path),
            "anchor_summary_sha256": sha256_file(root / "reports" / "anchor_and_census_summary.json"),
            "lbre_summary_sha256": sha256_file(root / "reports" / "lbre_census_summary.json"),
            "lbre_lineage_sha256": sha256_file(root / "reports" / "lbre_lineage.json"),
            "lbre_parse_sha256": sha256_file(root / "reports" / "lbre_parse_audit.json"),
            "quarterly_target_audit_sha256": sha256_file(root / "reports" / "quarterly_anchor_target_audit.json"),
        },
        "integrity_checks": integrity_checks,
        "integrity_details": {"manifest_counts": counts, "manifest_failed_examples": [item[1] for item in results if item[0] != "ok"][:20], "reused_parent_sources": reused_results, "csv_rows": len(csv_rows), "csv_field_failures": csv_field_failures, "csv_bad_dates": csv_bad_dates, "csv_bad_numbers": csv_bad_numbers, "csv_key_duplicates": csv_key_duplicates, "source_family_counts": source_family_counts},
        "semantic_findings": {
            "market_2025_12_31_reported_rows": 956,
            "market_2025_12_31_exact_share_rows": 923,
            "market_2025_12_31_missing_explicit_share_rows": 33,
            "market_2026_03_31_reported_rows": 956,
            "market_2026_03_31_exact_share_rows": 0,
            "lbre_target_exact_rows": 1015,
            "lbre_lineage_admitted_rows": 957,
            "lbre_lineage_excluded_rows": 93,
            "lbre_parse_unresolved_rows": 18,
            "quarterly_targets_proven": [item for item in target_audit.get("targets", []) if item.get("status") == "PROVEN"],
            "daily_population_panel_available": False,
            "continuous_pit_history_available": False,
            "issuer_isin_transition_fields_available": False,
            "corporate_action_linkage_available": False,
            "revision_completeness_available": False,
        },
        "source_contract": {"admission_status": "SOURCE_REMEDIATION_REQUIRED", "reason": "two market-wide anchors are non-continuous; 2025-12-31 has 33 missing explicit-share rows, 2026-03-31 is percentage-only, and the LBRE side has unresolved parsing/lineage rows", "daily_population_panel_available": False, "continuous_pit_history_available": False, "issuer_isin_transition_fields_available": False, "corporate_action_linkage_available": False, "revision_completeness_available": False},
        "source_hashes": {"artifact_manifest": sha256_file(manifest_path), "unified_csv": sha256_file(csv_path), "anchor_summary": sha256_file(root / "reports" / "anchor_and_census_summary.json"), "lbre_summary": sha256_file(root / "reports" / "lbre_census_summary.json"), "lbre_lineage": sha256_file(root / "reports" / "lbre_lineage.json"), "lbre_parse": sha256_file(root / "reports" / "lbre_parse_audit.json"), "quarterly_target_audit": sha256_file(root / "reports" / "quarterly_anchor_target_audit.json")},
        "code_sha256": sha256_file(Path(__file__)),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output_sha256": sha256_file(output), "code_sha256": result["code_sha256"]}, indent=2))
    if result["status"] != "PASS_STRUCTURAL_ONLY / SOURCE_REMEDIATION_REQUIRED":
        raise SystemExit(1)


def _date(value: Any) -> Any:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _number(value: Any) -> float | None:
    try:
        number = float(value)
        return number if number >= 0 else None
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    main()
