"""Independent envelope verifier for the listing/delisting source audit."""

from __future__ import annotations

import argparse
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
    parser.add_argument("--acquisition-summary", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--current-records", type=Path, required=True)
    parser.add_argument("--delisting-records", type=Path, required=True)
    parser.add_argument("--price-audit-summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    artifact: dict[str, Any] = json.loads(args.artifact.read_text(encoding="utf-8"))
    checks: dict[str, bool] = {
        "status_is_structural_only_source_blocked": artifact.get("status") == "PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED",
        "scope_is_outcome_blind": all(artifact.get("scope", {}).get(key) is False for key in ("outcome_accessed", "target_accessed", "provider_accessed", "network_used")),
        "all_integrity_checks_true": bool(artifact.get("integrity_checks")) and all(artifact["integrity_checks"].values()),
        "admission_is_blocked": artifact.get("source_contract", {}).get("admission_status") == "SOURCE_ADMISSION_BLOCKED",
        "current_rows_exact": artifact.get("source", {}).get("current_rows") == 962,
        "delisting_rows_exact": artifact.get("source", {}).get("delisting_rows") == 163,
        "raw_months_exact": artifact.get("source", {}).get("raw_months") == 440,
        "raw_rows_exact": artifact.get("source", {}).get("raw_rows") == 163,
        "conflict_ticker_count_exact": len(artifact.get("semantic_findings", {}).get("conflicting_lifecycle_artifact_tickers", [])) == 6,
        "daily_pit_is_not_claimed": artifact.get("source_contract", {}).get("daily_pit_membership_available") is False,
        "no_feature_or_candidate": artifact.get("scope", {}).get("feature_created") is False and artifact.get("scope", {}).get("candidate_created") is False,
    }

    declared_hashes = {
        "acquisition_summary": artifact.get("source", {}).get("summary_sha256"),
        "metadata": artifact.get("source", {}).get("metadata_sha256"),
        "current_records": artifact.get("source", {}).get("current_records_sha256"),
        "delisting_records": artifact.get("source", {}).get("delisting_records_sha256"),
        "price_audit_summary": artifact.get("source", {}).get("price_audit_summary_sha256"),
    }
    files = {
        "acquisition_summary": args.acquisition_summary,
        "metadata": args.metadata,
        "current_records": args.current_records,
        "delisting_records": args.delisting_records,
        "price_audit_summary": args.price_audit_summary,
    }
    source_files: dict[str, Any] = {}
    for name, path in files.items():
        actual = sha256_file(path)
        expected = declared_hashes[name]
        matches = actual == expected
        checks[f"{name}_hash_matches"] = matches
        source_files[name] = {"path": str(path), "actual_sha256": actual, "declared_sha256": expected, "matches": matches}

    code_hash = sha256_file(args.code)
    checks["code_hash_declared"] = bool(artifact.get("code_sha256"))
    checks["code_hash_matches"] = code_hash == artifact.get("code_sha256")
    checks["artifact_is_object"] = isinstance(artifact, dict)
    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "verification_type": "INDEPENDENT_LISTING_DELISTING_SOURCE_AUDIT_ENVELOPE_V1",
        "artifact_sha256": sha256_file(args.artifact),
        "verifier_code_sha256": sha256_file(Path(__file__)),
        "checks": checks,
        "source_files": source_files,
        "scope": {
            "outcome_accessed": False,
            "target_accessed": False,
            "provider_accessed": False,
            "network_used": False,
            "canonical_mutation": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
