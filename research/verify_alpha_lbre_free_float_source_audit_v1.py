"""Independent envelope verifier for the LBRE free-float source audit."""

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
    parser.add_argument("--canonical", type=Path, required=True)
    parser.add_argument("--admitted", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--exact", type=Path, required=True)
    parser.add_argument("--replay-summary", type=Path, required=True)
    parser.add_argument("--lineage-audit", type=Path, required=True)
    parser.add_argument("--parse-audit", type=Path, required=True)
    parser.add_argument("--monthly-census", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    artifact: dict[str, Any] = json.loads(args.artifact.read_text(encoding="utf-8"))
    checks: dict[str, bool] = {
        "status_is_structural_only_remediation_required": artifact.get("status") == "PASS_STRUCTURAL_ONLY / SOURCE_REMEDIATION_REQUIRED",
        "scope_is_outcome_blind": all(artifact.get("scope", {}).get(key) is False for key in ("outcome_accessed", "target_accessed", "provider_accessed", "network_used")),
        "all_integrity_checks_true": bool(artifact.get("integrity_checks")) and all(artifact["integrity_checks"].values()),
        "admission_is_remediation_required": artifact.get("source_contract", {}).get("admission_status") == "SOURCE_REMEDIATION_REQUIRED",
        "manifest_count_exact": artifact.get("manifest_details", {}).get("loaded_file_count") == 58671,
        "manifest_hashes_all_pass": artifact.get("manifest_details", {}).get("verification_counts", {}).get("hash") == 0,
        "canonical_count_exact": artifact.get("semantic_findings", {}).get("replay_summary", {}).get("canonical_rows") == 25262,
        "admitted_count_exact": artifact.get("semantic_findings", {}).get("replay_summary", {}).get("admitted") == 24394,
        "current_count_exact": artifact.get("semantic_findings", {}).get("replay_summary", {}).get("current") == 23373,
        "unresolved_lineage_exact": artifact.get("semantic_findings", {}).get("unresolved_lineage_rows") == 868,
        "daily_panel_not_claimed": artifact.get("source_contract", {}).get("daily_population_panel_available") is False,
        "no_feature_or_candidate": artifact.get("scope", {}).get("feature_created") is False and artifact.get("scope", {}).get("candidate_created") is False,
    }

    declared = artifact.get("source_hashes", {})
    files = {
        "artifact_manifest": args.manifest,
        "canonical_observations": args.canonical,
        "admitted_observations": args.admitted,
        "current_observations": args.current,
        "exact_observations": args.exact,
        "replay_summary": args.replay_summary,
        "lineage_audit": args.lineage_audit,
        "parse_audit": args.parse_audit,
        "monthly_census": args.monthly_census,
    }
    source_files: dict[str, Any] = {}
    for name, path in files.items():
        actual = sha256_file(path)
        expected = declared.get(name)
        matches = actual == expected
        checks[f"{name}_hash_matches"] = matches
        source_files[name] = {"path": str(path), "actual_sha256": actual, "declared_sha256": expected, "matches": matches}

    code_hash = sha256_file(args.code)
    checks["code_hash_declared"] = bool(artifact.get("code_sha256"))
    checks["code_hash_matches"] = code_hash == artifact.get("code_sha256")
    checks["artifact_is_object"] = isinstance(artifact, dict)
    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "verification_type": "INDEPENDENT_LBRE_FREE_FLOAT_SOURCE_AUDIT_ENVELOPE_V1",
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
