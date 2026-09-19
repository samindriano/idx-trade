"""Independent envelope verifier for the statutory free-float audit."""

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
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--unified-csv", type=Path, required=True)
    parser.add_argument("--anchor-summary", type=Path, required=True)
    parser.add_argument("--lbre-summary", type=Path, required=True)
    parser.add_argument("--lbre-lineage", type=Path, required=True)
    parser.add_argument("--lbre-parse", type=Path, required=True)
    parser.add_argument("--quarterly-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    artifact: dict[str, Any] = json.loads(args.artifact.read_text(encoding="utf-8"))
    checks: dict[str, bool] = {
        "status_is_structural_only_remediation_required": artifact.get("status") == "PASS_STRUCTURAL_ONLY / SOURCE_REMEDIATION_REQUIRED",
        "scope_is_outcome_blind": all(artifact.get("scope", {}).get(key) is False for key in ("outcome_accessed", "target_accessed", "provider_accessed", "network_used")),
        "all_integrity_checks_true": bool(artifact.get("integrity_checks")) and all(artifact["integrity_checks"].values()),
        "admission_is_remediation_required": artifact.get("source_contract", {}).get("admission_status") == "SOURCE_REMEDIATION_REQUIRED",
        "manifest_files_exact": artifact.get("source", {}).get("new_manifest_files") == 2145,
        "market_exact_rows": artifact.get("semantic_findings", {}).get("market_2025_12_31_exact_share_rows") == 923,
        "market_pct_only_rows": artifact.get("semantic_findings", {}).get("market_2026_03_31_exact_share_rows") == 0,
        "no_feature_or_candidate": artifact.get("scope", {}).get("feature_created") is False and artifact.get("scope", {}).get("candidate_created") is False,
        "daily_panel_not_claimed": artifact.get("source_contract", {}).get("daily_population_panel_available") is False,
    }
    declared = artifact.get("source_hashes", {})
    files = {"artifact_manifest": args.manifest, "unified_csv": args.unified_csv, "anchor_summary": args.anchor_summary, "lbre_summary": args.lbre_summary, "lbre_lineage": args.lbre_lineage, "lbre_parse": args.lbre_parse, "quarterly_target_audit": args.quarterly_audit}
    source_files: dict[str, Any] = {}
    for name, path in files.items():
        actual = sha256_file(path)
        expected = declared.get(name)
        checks[f"{name}_hash_matches"] = actual == expected
        source_files[name] = {"path": str(path), "actual_sha256": actual, "declared_sha256": expected, "matches": actual == expected}
    checks["code_hash_declared"] = bool(artifact.get("code_sha256"))
    checks["code_hash_matches"] = sha256_file(args.code) == artifact.get("code_sha256")
    checks["artifact_is_object"] = isinstance(artifact, dict)
    result = {"status": "PASS" if all(checks.values()) else "FAIL", "verification_type": "INDEPENDENT_STATUTORY_FREE_FLOAT_SOURCE_AUDIT_ENVELOPE_V1", "artifact_sha256": sha256_file(args.artifact), "verifier_code_sha256": sha256_file(Path(__file__)), "checks": checks, "source_files": source_files, "scope": {"outcome_accessed": False, "target_accessed": False, "provider_accessed": False, "network_used": False, "canonical_mutation": False}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
