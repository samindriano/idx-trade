"""Independent envelope verifier for the broker/margin snapshot audit."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--code", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--audit-report", type=Path, required=True)
    parser.add_argument("--parity-summary", type=Path, required=True)
    parser.add_argument("--official-parity", type=Path, required=True)
    parser.add_argument("--comparison-csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    artifact: dict[str, Any] = json.loads(args.artifact.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    audit = json.loads(args.audit_report.read_text(encoding="utf-8"))
    parity = json.loads(args.parity_summary.read_text(encoding="utf-8"))
    official_parity = json.loads(args.official_parity.read_text(encoding="utf-8"))
    with args.comparison_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        comparison_rows = list(csv.DictReader(handle))
    checks: dict[str, bool] = {
        "status_is_snapshot_only_blocked": artifact.get("status") == "PASS_STRUCTURAL_ONLY / SNAPSHOT_ONLY_BLOCKED",
        "scope_is_outcome_blind": all(artifact.get("scope", {}).get(key) is False for key in ("outcome_accessed", "target_accessed", "provider_accessed", "network_used")),
        "all_integrity_checks_true": bool(artifact.get("integrity_checks")) and all(artifact["integrity_checks"].values()),
        "manifest_count_exact": manifest.get("file_count") == 73 and len(manifest.get("files", [])) == 73,
        "comparison_count_exact": len(comparison_rows) == 971,
        "audit_classification_exact": audit.get("classification") == "UNRESOLVED_H2_LIKE_NOT_H1_PROVEN",
        "audit_single_date_exact": audit.get("same_date", {}).get("date") == "2026-07-14" and audit.get("same_date", {}).get("margin_rows") == 220 and audit.get("same_date", {}).get("stock_rows") == 965,
        "parity_not_decisive": parity.get("parity_decision") == "NOT_H2_DECISIVE",
        "official_bounded_classification": official_parity.get("semantics", {}).get("bounded_classification") == "H2_LIKE_CATEGORY_VIEW_NOT_H1_MARGIN_FINANCING_FLOW",
        "publication_time_absent": artifact.get("source_contract", {}).get("publication_or_knowledge_timestamp_available") is False,
        "no_feature_or_candidate": artifact.get("scope", {}).get("feature_created") is False and artifact.get("scope", {}).get("candidate_created") is False,
    }
    declared = artifact.get("source_hashes", {})
    files = {"manifest": args.manifest, "audit_report": args.audit_report, "parity_summary": args.parity_summary, "official_parity": args.official_parity, "comparison_csv": args.comparison_csv}
    source_files: dict[str, Any] = {}
    for name, path in files.items():
        actual = sha256_file(path)
        expected = declared.get(name)
        checks[f"{name}_hash_matches"] = actual == expected
        source_files[name] = {"path": str(path), "actual_sha256": actual, "declared_sha256": expected, "matches": actual == expected}
    checks["code_hash_matches"] = sha256_file(args.code) == artifact.get("code_sha256")
    result = {"status": "PASS" if all(checks.values()) else "FAIL", "verification_type": "INDEPENDENT_BROKER_MARGIN_SNAPSHOT_SOURCE_AUDIT_ENVELOPE_V1", "artifact_sha256": sha256_file(args.artifact), "verifier_code_sha256": sha256_file(Path(__file__)), "checks": checks, "source_files": source_files, "scope": {"outcome_accessed": False, "target_accessed": False, "provider_accessed": False, "network_used": False, "canonical_mutation": False}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
