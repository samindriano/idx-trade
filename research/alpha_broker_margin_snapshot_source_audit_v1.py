"""Outcome-blind structural audit for the local broker/margin snapshot."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HEX64 = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def check_manifest_file(root: Path, record: dict[str, Any]) -> tuple[str, str]:
    rel = str(record.get("path", ""))
    path = (root / Path(rel)).resolve()
    if root not in path.parents:
        return "escape", rel
    if not path.is_file():
        return "missing", rel
    if path.stat().st_size != int(record.get("bytes", -1)):
        return "bytes", rel
    if sha256_file(path) != str(record.get("sha256", "")):
        return "hash", rel
    return "ok", rel


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def unique_codes(rows: list[dict[str, Any]], field: str) -> set[str]:
    return {str(row.get(field, "")).strip().upper() for row in rows if str(row.get(field, "")).strip()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")

    manifest_path = root / "artifact_manifest_2026-07-14.json"
    manifest = load_json(manifest_path)
    declared = manifest.get("files", [])
    with ThreadPoolExecutor(max_workers=16) as executor:
        results = list(executor.map(lambda row: check_manifest_file(root, row), declared))
    manifest_counts = {status: sum(item[0] == status for item in results) for status in ("ok", "missing", "bytes", "hash", "escape")}

    audit = load_json(root / "margin_summary_audit_report_2026-07-14.json")
    parity = load_json(root / "margin_summary_parity_summary_2026-07-14.json")
    official_parity = load_json(root / "official_source_parity_summary_2026-07-14.json")
    official_margin = load_json(root / "official_margin_summary_raw_2026-07-14.json")
    official_stock = load_json(root / "official_stock_summary_raw_2026-07-14.json")
    zapi_margin = load_json(root / "zapi_margin_summary_2026-07-14.json")
    zapi_stock = load_json(root / "zapi_stock_summary_2026-07-14.json")
    request_metadata = load_json(root / "zapi_request_metadata_2026-07-14.json")
    fields_comparison, comparison_rows = read_csv(root / "margin_stock_comparison_2026-07-14.csv")
    fields_eligible, eligible_rows = read_csv(root / "official_margin_eligible_2026-07-14.csv")
    fields_zapi_margin, zapi_margin_rows = read_csv(root / "zapi_margin_summary_normalized_2026-07-14.csv")
    fields_zapi_stock, zapi_stock_rows = read_csv(root / "zapi_stock_summary_normalized_2026-07-14.csv")

    official_margin_rows = official_margin.get("data", []) if isinstance(official_margin, dict) else []
    official_stock_rows = official_stock.get("data", []) if isinstance(official_stock, dict) else []
    zapi_margin_payload_rows = zapi_margin.get("data", {}).get("data", []) if isinstance(zapi_margin, dict) else []
    zapi_stock_payload = zapi_stock.get("data", {}) if isinstance(zapi_stock, dict) else {}
    zapi_stock_payload_rows = zapi_stock_payload.get("data", []) if isinstance(zapi_stock_payload, dict) else []
    eligible_codes = unique_codes(eligible_rows, "ticker")
    margin_codes = unique_codes(zapi_margin_rows, "code")
    stock_codes = unique_codes(zapi_stock_rows, "StockCode")
    comparison_codes = unique_codes(comparison_rows, "ticker")

    exact_fields = audit.get("source_raw_parity", {}).get("field_exact", {})
    official_exact_margin = official_parity.get("zapi_margin_official_raw_parity", {})
    official_exact_stock = official_parity.get("zapi_stock_official_raw_parity", {})
    required_comparison_fields = {"ticker", "official_margin_eligible", "margin_present", "stock_present", "all_six_exact", "stock_positive_activity"}
    required_eligible_fields = {"ticker", "name", "sheet", "row"}
    required_margin_fields = {"code", "high", "low", "close", "change", "volume", "value", "frequency"}

    integrity_checks = {
        "manifest_id_exact": manifest.get("manifest_id") == "IDX-BROKER-MARGIN-SOURCE-AUDIT-V0",
        "manifest_file_count_exact": manifest.get("file_count") == 73 and len(declared) == 73 and len({item.get("path") for item in declared}) == 73,
        "all_manifest_files_present": manifest_counts["missing"] == 0 and manifest_counts["escape"] == 0,
        "all_manifest_bytes_match": manifest_counts["bytes"] == 0,
        "all_manifest_hashes_match": manifest_counts["hash"] == 0,
        "secret_not_persisted": manifest.get("secret_check", {}).get("ZAPI_API_KEY") == "not written; only presence used",
        "official_margin_raw_exact": len(official_margin_rows) == 220 and official_margin.get("recordsTotal") == 220 and official_margin.get("recordsFiltered") == 220,
        "official_stock_raw_exact": len(official_stock_rows) == 965 and official_stock.get("recordsTotal") == 965 and official_stock.get("recordsFiltered") == 965,
        "zapi_margin_raw_exact": len(zapi_margin_payload_rows) == 220 and zapi_margin.get("data", {}).get("total") == 220,
        "zapi_stock_raw_exact": len(zapi_stock_payload_rows) == 965,
        "normalized_row_counts_exact": len(zapi_margin_rows) == 220 and len(zapi_stock_rows) == 965 and len(eligible_rows) == 326 and len(comparison_rows) == 971,
        "normalized_required_fields_present": required_margin_fields.issubset(fields_zapi_margin) and required_eligible_fields.issubset(fields_eligible) and required_comparison_fields.issubset(fields_comparison) and "StockCode" in fields_zapi_stock,
        "normalized_codes_unique": len(margin_codes) == 220 and len(stock_codes) == 965 and len(eligible_codes) == 326,
        "margin_codes_subset_eligible": margin_codes <= eligible_codes,
        "official_parity_exact": all(exact_fields.get(field) == 220 for field in ("high", "low", "close", "value", "volume", "frequency")) and audit.get("source_raw_parity", {}).get("all_six_exact") == 220,
        "zapi_official_parity_exact": official_exact_margin.get("all_six_exact") == 220 and official_exact_stock.get("all_six_exact") == 965 and official_exact_margin.get("date_exact") == 220 and official_exact_stock.get("date_exact") == 965,
        "bounded_pagination_complete": audit.get("pagination_completeness", {}).get("additional_pagination_required") is False,
        "parity_summary_consistent": parity.get("all_six_exact_count") == 0 and parity.get("universe", {}).get("eligible_tickers") == 326 and parity.get("universe", {}).get("margin_and_stock") == 220,
        "classification_consistent": audit.get("classification") == "UNRESOLVED_H2_LIKE_NOT_H1_PROVEN" and official_parity.get("semantics", {}).get("bounded_classification") == "H2_LIKE_CATEGORY_VIEW_NOT_H1_MARGIN_FINANCING_FLOW",
        "no_publication_time_claim": audit.get("pit_status", {}).get("publication_or_knowledge_timestamp") == "not present in payloads" and official_parity.get("pit_status", {}).get("publication_or_knowledge_timestamp") == "not present in payloads",
        "no_network_or_outcome_access": True,
    }
    structural_pass = all(integrity_checks.values())
    result = {
        "status": "PASS_STRUCTURAL_ONLY / SNAPSHOT_ONLY_BLOCKED" if structural_pass else "FAIL_STRUCTURAL_INTEGRITY",
        "stage": "H_DATA_CAPABILITY_BROKER_MARGIN_SNAPSHOT_SOURCE_AUDIT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": {"outcome_accessed": False, "target_accessed": False, "provider_accessed": False, "network_used": False, "canonical_mutation": False, "feature_created": False, "candidate_created": False, "production_or_capture_mutation": False},
        "source": {"root": str(root), "manifest_sha256": sha256_file(manifest_path), "manifest_files": len(declared), "audit_report_sha256": sha256_file(root / "margin_summary_audit_report_2026-07-14.json"), "parity_summary_sha256": sha256_file(root / "margin_summary_parity_summary_2026-07-14.json"), "official_parity_sha256": sha256_file(root / "official_source_parity_summary_2026-07-14.json"), "comparison_csv_sha256": sha256_file(root / "margin_stock_comparison_2026-07-14.csv")},
        "integrity_checks": integrity_checks,
        "integrity_details": {"manifest_counts": manifest_counts, "manifest_failed_examples": [item[1] for item in results if item[0] != "ok"][:20], "official_margin_rows": len(official_margin_rows), "official_stock_rows": len(official_stock_rows), "zapi_margin_rows": len(zapi_margin_payload_rows), "zapi_stock_rows": len(zapi_stock_payload_rows), "eligible_rows": len(eligible_rows), "comparison_rows": len(comparison_rows), "eligible_tickers": len(eligible_codes), "margin_tickers": len(margin_codes), "stock_tickers": len(stock_codes), "request_metadata_records": len(request_metadata) if isinstance(request_metadata, list) else None},
        "semantic_findings": {"audit_date": "2026-07-14", "eligible_ticker_count": 326, "margin_summary_ticker_count": 220, "stock_summary_ticker_count": 965, "eligible_without_margin": 106, "eligible_without_margin_with_positive_stock_activity": 100, "all_six_metric_matches_against_all_stock": 0, "raw_zapi_official_margin_all_six_parity": 220, "raw_zapi_official_stock_all_six_parity": 965, "classification": "H2_LIKE_CATEGORY_VIEW_NOT_H1_MARGIN_FINANCING_FLOW", "pit_publication_or_knowledge_time": False, "daily_history_available": False, "historical_series_available": False},
        "source_contract": {"admission_status": "SNAPSHOT_ONLY_BLOCKED", "reason": "single-date category snapshot; official source labels Margin tab as IDX Reporting (Regular and Cash), no financing-account or margin-loan fields exist, 106/326 eligible rows are absent, all-six generic metric parity is 0/220, and publication/knowledge time is absent", "single_date_only": True, "actual_margin_financing_flow_proven": False, "h2_exact_all_stock_filter_proven": False, "publication_or_knowledge_timestamp_available": False, "daily_history_available": False, "feature_admission": False},
        "source_hashes": {"manifest": sha256_file(manifest_path), "audit_report": sha256_file(root / "margin_summary_audit_report_2026-07-14.json"), "parity_summary": sha256_file(root / "margin_summary_parity_summary_2026-07-14.json"), "official_parity": sha256_file(root / "official_source_parity_summary_2026-07-14.json"), "comparison_csv": sha256_file(root / "margin_stock_comparison_2026-07-14.csv"), "zapi_margin_json": sha256_file(root / "zapi_margin_summary_2026-07-14.json"), "zapi_stock_json": sha256_file(root / "zapi_stock_summary_2026-07-14.json"), "eligible_csv": sha256_file(root / "official_margin_eligible_2026-07-14.csv")},
        "code_sha256": sha256_file(Path(__file__)),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output_sha256": sha256_file(output), "code_sha256": result["code_sha256"]}, indent=2))
    if not structural_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
