"""Independent envelope/hash verifier for the historical foreign-flow audit."""

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
    parser.add_argument("--archive-manifest", type=Path, required=True)
    parser.add_argument("--coverage-census", type=Path, required=True)
    parser.add_argument("--official-calendar", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    artifact: dict[str, Any] = json.loads(args.artifact.read_text(encoding="utf-8"))
    checks: dict[str, bool] = {}
    checks["status_is_structural_only_source_blocked"] = artifact.get("status") == "PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED"
    checks["scope_is_outcome_blind"] = all(
        artifact.get(key) is False
        for key in ("outcome_accessed", "target_accessed", "provider_accessed", "network_used")
    ) if any(key in artifact for key in ("outcome_accessed", "target_accessed", "provider_accessed", "network_used")) else all(
        artifact.get("scope", {}).get(key) is False
        for key in ("outcome_accessed", "target_accessed", "provider_accessed", "network_used")
    )
    structural = artifact.get("structural_checks", {})
    checks["all_structural_checks_true"] = bool(structural) and all(structural.values())
    checks["admission_blocked"] = artifact.get("source_contract", {}).get("admission_status") == "SOURCE_ADMISSION_BLOCKED"
    checks["row_count_exact"] = artifact.get("source", {}).get("row_count") == 1129024
    checks["session_count_exact"] = artifact.get("source", {}).get("session_count") == 1288
    checks["ticker_count_exact"] = artifact.get("source", {}).get("ticker_count") == 983

    files = {
        "archive_manifest": args.archive_manifest,
        "coverage_census": args.coverage_census,
        "official_calendar": args.official_calendar,
    }
    declared = artifact.get("source_hashes", {})
    file_details: dict[str, Any] = {}
    for name, path in files.items():
        actual = sha256_file(path)
        expected = declared.get(name)
        match = actual == expected
        checks[f"{name}_hash_matches"] = match
        file_details[name] = {"path": str(path), "actual_sha256": actual, "declared_sha256": expected, "matches": match}

    code_hash = sha256_file(args.code)
    checks["code_hash_declared"] = bool(artifact.get("code_sha256"))
    checks["code_hash_matches"] = code_hash == artifact.get("code_sha256")
    checks["artifact_is_object"] = isinstance(artifact, dict)
    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "verification_type": "INDEPENDENT_FOREIGN_FLOW_SOURCE_AUDIT_ENVELOPE_V1",
        "artifact_sha256": sha256_file(args.artifact),
        "verifier_code_sha256": sha256_file(Path(__file__)),
        "checks": checks,
        "source_files": file_details,
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
