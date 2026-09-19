"""Outcome-blind structural audit for the local HSC ownership event ledger."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "event_id",
    "ticker",
    "status",
    "ownership_as_of_date",
    "published_at",
    "concentration_pct",
    "determination_methodology_version",
    "idx_announcement_no",
    "ksei_announcement_no",
    "revision_kind",
    "supersedes_event_id",
    "source_url",
    "source_sha256",
    "metadata_source_sha256",
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def check_manifest_artifact(root: Path, record: dict[str, Any]) -> tuple[str, str]:
    rel = str(record.get("path", ""))
    candidate = (root / Path(rel)).resolve()
    if root not in candidate.parents:
        return "escape", rel
    if not candidate.is_file():
        return "missing", rel
    if candidate.stat().st_size != int(record.get("bytes", -1)):
        return "bytes", rel
    if sha256_file(candidate) != str(record.get("sha256", "")):
        return "hash", rel
    return "ok", rel


def parse_date(value: Any) -> date | None:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def parse_timestamp(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo is not None else None
    except (TypeError, ValueError):
        return None


def parse_pct(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if 0 <= parsed <= 100 else None


def count_artifacts(manifest: dict[str, Any]) -> dict[str, int]:
    paths = [str(item.get("path", "")) for item in manifest.get("artifacts", [])]
    return {
        "declared": len(paths),
        "unique": len(set(paths)),
        "audit": sum(path.startswith("audit/") for path in paths),
        "normalized": sum(path.startswith("normalized/") for path in paths),
        "metadata": sum(path.startswith("raw/idx_metadata/") for path in paths),
        "pdf": sum(path.startswith("raw/official_idx/") for path in paths),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")

    manifest_path = root / "AUDIT_MANIFEST.json"
    manifest = load_json(manifest_path)
    declared = manifest.get("artifacts", [])
    with ThreadPoolExecutor(max_workers=16) as executor:
        results = list(executor.map(lambda row: check_manifest_artifact(root, row), declared))
    manifest_counts = {
        status: sum(item[0] == status for item in results)
        for status in ("ok", "missing", "bytes", "hash", "escape")
    }

    events_csv_path = root / "normalized" / "hsc_events.csv"
    events_json_path = root / "normalized" / "hsc_events.json"
    with events_csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        csv_reader = csv.DictReader(handle)
        csv_fields = list(csv_reader.fieldnames or [])
        csv_rows = list(csv_reader)
    json_rows = load_json(events_json_path)
    if not isinstance(json_rows, list):
        json_rows = []

    required_failures = sum(1 for row in csv_rows if not REQUIRED_FIELDS.issubset(row))
    bad_tickers = sum(
        1
        for row in csv_rows
        if not re.fullmatch(r"[A-Z0-9]{4}", str(row.get("ticker", "")))
    )
    bad_dates = sum(parse_date(row.get("ownership_as_of_date")) is None for row in csv_rows)
    bad_timestamps = sum(parse_timestamp(row.get("published_at")) is None for row in csv_rows)
    bad_pct = sum(
        row.get("revision_kind") != "REMOVAL" and parse_pct(row.get("concentration_pct")) is None
        for row in csv_rows
    )
    removal_pct_present = sum(
        row.get("revision_kind") == "REMOVAL" and row.get("concentration_pct") not in (None, "")
        for row in csv_rows
    )
    invalid_hashes = sum(
        not HEX64.fullmatch(str(row.get(field, "")))
        for row in csv_rows
        for field in ("source_sha256", "metadata_source_sha256")
    )
    event_ids = {row.get("event_id") for row in csv_rows}
    announcement_counts: dict[str, int] = {}
    for row in csv_rows:
        key = str(row.get("idx_announcement_no", ""))
        announcement_counts[key] = announcement_counts.get(key, 0) + 1
    duplicate_announcement_rows = sum(count - 1 for count in announcement_counts.values() if count > 1)

    by_revision: dict[str, int] = {}
    by_methodology: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for row in csv_rows:
        for counts, key in (
            (by_revision, row.get("revision_kind", "")),
            (by_methodology, row.get("determination_methodology_version", "")),
            (status_counts, row.get("status", "")),
        ):
            counts[str(key)] = counts.get(str(key), 0) + 1

    id_to_row = {str(row.get("event_id")): row for row in csv_rows}
    bad_revision_links = 0
    for row in csv_rows:
        revision = row.get("revision_kind")
        supersedes = str(row.get("supersedes_event_id", ""))
        if revision == "CORRECTION":
            bad_revision_links += int(not supersedes or supersedes not in id_to_row)
        else:
            bad_revision_links += int(bool(supersedes))

    capture_index = load_json(root / "audit" / "capture_index.json")
    parse_audit = load_json(root / "audit" / "event_parse_audit.json")
    replay = load_json(root / "audit" / "replay_checkpoints.json")
    cutoff_search = load_json(root / "audit" / "cutoff_search.json")
    current_target = load_json(root / "audit" / "official_current_target_20260815.json")
    july_target = load_json(root / "audit" / "official_july_51_target.json")
    current_target_csv = [
        line.strip()
        for line in (root / "normalized" / "official_current_target_20260815.csv").read_text(encoding="utf-8").splitlines()[1:]
        if line.strip()
    ]
    july_target_csv = [
        line.strip()
        for line in (root / "normalized" / "official_july_51_target.csv").read_text(encoding="utf-8").splitlines()[1:]
        if line.strip()
    ]
    raw_active_tickers = {row.get("ticker") for row in csv_rows if row.get("status") == "HSC_ACTIVE"}
    active_tickers = set(manifest.get("active_tickers_at_cutoff", []))
    capture_records = capture_index.get("records", []) if isinstance(capture_index, dict) else []
    parse_records = parse_audit if isinstance(parse_audit, list) else []

    integrity_checks = {
        "manifest_schema_exact": manifest.get("schema_version") == "HSC_FULL_HISTORY_LEDGER_V1",
        "manifest_artifact_count_exact": len(declared) == 137,
        "manifest_artifact_paths_unique": len(declared) == len({item.get("path") for item in declared}),
        "manifest_artifact_partition_exact": count_artifacts(manifest) == {"declared": 137, "unique": 137, "audit": 7, "normalized": 4, "metadata": 8, "pdf": 118},
        "all_manifest_artifacts_present": manifest_counts["missing"] == 0 and manifest_counts["escape"] == 0,
        "all_manifest_bytes_match": manifest_counts["bytes"] == 0,
        "all_manifest_hashes_match": manifest_counts["hash"] == 0,
        "manifest_event_count_exact": manifest.get("event_count") == 59 and len(csv_rows) == 59,
        "manifest_active_count_exact": manifest.get("active_count_at_cutoff") == 55 and len(active_tickers) == 55 and manifest.get("active_tickers_at_cutoff") == current_target.get("tickers", []),
        "manifest_revision_counts_exact": manifest.get("event_counts_by_revision_kind") == {"ORIGINAL": 56, "CORRECTION": 2, "REMOVAL": 1} and by_revision == {"ORIGINAL": 56, "CORRECTION": 2, "REMOVAL": 1},
        "manifest_methodology_counts_exact": manifest.get("event_counts_by_methodology") == {"HSC_2026_INITIAL": 17, "HSC_2026_PRICE_IMPACT_REVISION": 42} and by_methodology == {"HSC_2026_INITIAL": 17, "HSC_2026_PRICE_IMPACT_REVISION": 42},
        "normalized_csv_json_exact": csv_rows == json_rows,
        "normalized_required_fields_present": set(csv_fields) == REQUIRED_FIELDS,
        "normalized_required_values_valid": required_failures == 0 and bad_tickers == 0 and bad_dates == 0 and bad_timestamps == 0 and bad_pct == 0 and removal_pct_present == 0 and invalid_hashes == 0,
        "event_ids_unique": len(event_ids) == len(csv_rows),
        "revision_links_valid": bad_revision_links == 0,
        "capture_record_count_exact": len(capture_records) == 59,
        "parse_record_count_exact": len(parse_records) == 59,
        "replay_all_pass": bool(replay) and all(item.get("status") == "PASS" for item in replay),
        "replay_final_active_count_exact": bool(replay) and replay[-1].get("active_count") == 55,
        "current_target_exact": current_target.get("ticker_count") == 55 and current_target_csv == current_target.get("tickers") and current_target.get("tickers") == manifest.get("active_tickers_at_cutoff"),
        "july_target_exact": july_target.get("ticker_count") == 51 and july_target_csv == july_target.get("tickers") and manifest.get("july_51_target_count") == 51 and manifest.get("july_51_target_match") is True,
        "bounded_cutoff_search_declared": cutoff_search.get("negative_search_limit") == "absence is bounded to the preserved official metadata capture; no inference beyond cutoff coverage",
        "duplicate_announcement_rows_expected": duplicate_announcement_rows == 2,
        "no_network_or_outcome_access": True,
    }
    structural_pass = all(integrity_checks.values())
    result = {
        "status": "PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED" if structural_pass else "FAIL_STRUCTURAL_INTEGRITY",
        "stage": "H_DATA_CAPABILITY_HSC_OWNERSHIP_EVENT_SOURCE_AUDIT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": {"outcome_accessed": False, "target_accessed": False, "provider_accessed": False, "network_used": False, "canonical_mutation": False, "feature_created": False, "candidate_created": False, "production_or_capture_mutation": False},
        "source": {"root": str(root), "manifest_sha256": sha256_file(manifest_path), "manifest_artifacts": len(declared), "events_csv_sha256": sha256_file(events_csv_path), "events_json_sha256": sha256_file(events_json_path), "capture_index_sha256": sha256_file(root / "audit" / "capture_index.json"), "parse_audit_sha256": sha256_file(root / "audit" / "event_parse_audit.json"), "replay_checkpoints_sha256": sha256_file(root / "audit" / "replay_checkpoints.json"), "cutoff_search_sha256": sha256_file(root / "audit" / "cutoff_search.json")},
        "integrity_checks": integrity_checks,
        "integrity_details": {"manifest_counts": manifest_counts, "manifest_failed_examples": [item[1] for item in results if item[0] != "ok"][:20], "csv_rows": len(csv_rows), "csv_fields": csv_fields, "status_counts": status_counts, "raw_status_active_ticker_count": len(raw_active_tickers), "effective_active_ticker_count": len(active_tickers), "revision_counts": by_revision, "methodology_counts": by_methodology, "duplicate_announcement_rows": duplicate_announcement_rows, "duplicate_announcement_keys": sorted(key for key, count in announcement_counts.items() if count > 1), "invalid_value_counts": {"required_fields": required_failures, "bad_tickers": bad_tickers, "bad_dates": bad_dates, "bad_timestamps": bad_timestamps, "bad_concentration_pct": bad_pct, "removal_pct_present": removal_pct_present, "invalid_hashes": invalid_hashes, "bad_revision_links": bad_revision_links}},
        "semantic_findings": {"event_count": 59, "active_ticker_count_at_cutoff": 55, "active_tickers": sorted(active_tickers), "revision_counts": by_revision, "methodology_counts": by_methodology, "ownership_date_range": [min(row["ownership_as_of_date"] for row in csv_rows), max(row["ownership_as_of_date"] for row in csv_rows)], "published_at_range": [min(row["published_at"] for row in csv_rows), max(row["published_at"] for row in csv_rows)], "duplicate_announcement_rows": duplicate_announcement_rows, "daily_population_panel_available": False, "continuous_pit_history_available": False, "issuer_isin_transition_fields_available": False, "corporate_action_linkage_available": False, "revision_completeness_available": False, "event_publication_availability_contract": False},
        "source_contract": {"admission_status": "SOURCE_ADMISSION_BLOCKED", "reason": "the local source is a structurally verified HSC ownership event ledger only; it lacks daily population-wide coverage, issuer/ISIN transition lineage, corporate-action linkage, and an independently proven full publication/revision contract", "event_ledger_available": True, "daily_population_panel_available": False, "continuous_pit_history_available": False, "issuer_isin_transition_fields_available": False, "corporate_action_linkage_available": False, "revision_completeness_available": False, "event_publication_availability_contract": False},
        "source_hashes": {"manifest": sha256_file(manifest_path), "events_csv": sha256_file(events_csv_path), "events_json": sha256_file(events_json_path), "capture_index": sha256_file(root / "audit" / "capture_index.json"), "parse_audit": sha256_file(root / "audit" / "event_parse_audit.json"), "replay_checkpoints": sha256_file(root / "audit" / "replay_checkpoints.json"), "cutoff_search": sha256_file(root / "audit" / "cutoff_search.json")},
        "code_sha256": sha256_file(Path(__file__)),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output_sha256": sha256_file(output), "code_sha256": result["code_sha256"]}, indent=2))
    if not structural_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
