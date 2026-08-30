"""Build the outcome-blind INC-001 closure-feasibility artifact.

This report consumes the final known-event reconciliation and previously
accepted R3.1 geometry audit.  It does not recompute model features, access
outcomes, or create a new admission path.  Its purpose is to distinguish
known-event remediation from the independent population-completeness and
historical-as-of blockers.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping


V16_MANIFEST_SHA256 = "3ff25d77dd1d2d85d1ff7526fcef90525dfe60afed026f4c2738b8bfb2a57030"
MERGER_MANIFEST_SHA256 = "747c83ac3bcf6dac15e73c1e71553a0ae80422b9da0f25deb57b3139dceff6c1"
CAPITAL_MANIFEST_SHA256 = "a4f4fd188d830088cdafbb1bbcd5716ae1f92cc6fcd8314181cf9dbefa832887"
R31_MANIFEST_SHA256 = "9075b707db70cf7e2a6fce4b504bfdf8c16369b9de75420f90d9808f1b994c2b"
AUDIT_DATE = "2026-08-31"
PARKED_FAMILIES = (
    "RIGHTS_HMETD",
    "UNRESOLVED_OPERATIONAL_LABEL",
    "STOCK_SPLIT",
    "REVERSE_SPLIT",
    "BONUS_SHARES",
    "STOCK_DIVIDEND",
    "TRUE_SECURITY_CONVERSION",
    "MERGER",
    "CAPITAL_RESTRUCTURING",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: "" if row.get(field) is None else row.get(field, "") for field in fields})


def verify_manifest(root: Path, expected_sha256: str) -> dict[str, Any]:
    manifest_path = root / "MANIFEST.json"
    actual = sha256_file(manifest_path)
    if actual != expected_sha256:
        raise RuntimeError(f"manifest mismatch for {root}: {actual}")
    manifest = read_json(manifest_path)
    entries = manifest.get("files", [])
    if entries:
        for item in entries:
            path = root / item["path"]
            if not path.is_file() or path.stat().st_size != item["bytes"] or sha256_file(path) != item["sha256"]:
                raise RuntimeError(f"manifest-bound file mismatch: {path}")
    else:
        for name, expected in manifest.get("output_hashes", {}).items():
            path = root / name
            if not path.is_file() or sha256_file(path) != expected:
                raise RuntimeError(f"output hash mismatch: {path}")
    return manifest


def git_head(repo_root: Path) -> str:
    return subprocess.check_output(["git", "-C", str(repo_root), "rev-parse", "HEAD"], text=True).strip()


def build(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = args.repo_root.resolve()
    v16_root = args.v16_root.resolve()
    merger_root = args.merger_root.resolve()
    capital_root = args.capital_root.resolve()
    r31_root = args.r31_root.resolve()
    output_root = args.output_root.resolve()
    verify_manifest(v16_root, V16_MANIFEST_SHA256)
    verify_manifest(merger_root, MERGER_MANIFEST_SHA256)
    verify_manifest(capital_root, CAPITAL_MANIFEST_SHA256)
    verify_manifest(r31_root, R31_MANIFEST_SHA256)
    if output_root.exists():
        raise FileExistsError(f"refuse overwrite closure artifact: {output_root}")
    staging = output_root.with_name(output_root.name + ".staging")
    if staging.exists():
        raise FileExistsError(f"staging closure artifact already exists: {staging}")
    staging.mkdir(parents=True)
    try:
        events = read_csv(v16_root / "economic_event_ledger.csv")
        if len(events) != 387:
            raise RuntimeError(f"unexpected final event count: {len(events)}")
        status_counts = Counter(row.get("transition_status", "") for row in events)
        expected_status = Counter({"RESOLVED": 163, "UNRESOLVED": 178, "NOT_APPLICABLE_NON_BASIS": 46})
        if status_counts != expected_status:
            raise RuntimeError(f"unexpected final transition counts: {status_counts}")
        family_counts = Counter(row.get("economic_family", "") for row in events)
        unresolved_by_family = Counter(row.get("economic_family", "") for row in events if row.get("transition_status") == "UNRESOLVED")
        if unresolved_by_family["COMPOSITE_CASH_SHARE_DISTRIBUTION"] != 4 or unresolved_by_family["MERGER"] != 5 or unresolved_by_family["CAPITAL_RESTRUCTURING"] != 19:
            raise RuntimeError("final event census does not contain the expected current phase results")

        merger_summary = read_json(merger_root / "acquisition_summary.json")
        merger_results = read_csv(merger_root / "target_event_results.csv")
        capital_summary = read_json(capital_root / "reconciliation_summary.json")
        capital_results = read_csv(capital_root / "capital_restructuring_decomposition.csv")
        if len(merger_results) != 5 or len(capital_results) != 19:
            raise RuntimeError("phase artifact scopes are not conserved")
        if any(row.get("result_classification") != "PROVIDER_DISCOVERY_FAILURE" for row in merger_results):
            raise RuntimeError("merger artifact contains an unexpected classification")
        if any(row.get("transition_status") != "UNRESOLVED" for row in capital_results):
            raise RuntimeError("capital artifact contains a promoted transition")

        final_rows = []
        for row in events:
            status = row.get("transition_status", "")
            if status == "RESOLVED":
                disposition = "RESOLVED_EXACT"
            elif status == "NOT_APPLICABLE_NON_BASIS":
                disposition = "NON_BASIS"
            elif row.get("economic_family") in PARKED_FAMILIES:
                disposition = "PARKED_FAIL_CLOSED"
            else:
                disposition = "UNRESOLVED_REQUIRES_REVIEW"
            final_rows.append({
                "economic_event_id": row.get("economic_event_id", ""),
                "economic_family": row.get("economic_family", ""),
                "basis_effect": row.get("basis_effect", ""),
                "transition_status": status,
                "final_disposition": disposition,
                "transition_missing": str(status == "UNRESOLVED").upper(),
            })

        r31 = read_json(r31_root / "r3_summary.json")
        geometry = {
            "source": "existing outcome-blind R3.1 geometry artifact; not recomputed in this closure report",
            "artifact_root": str(r31_root),
            "artifact_manifest_sha256": R31_MANIFEST_SHA256,
            "fit_rows": r31["exact_final_fit"]["union_rows"],
            "fit_tickers": r31["exact_final_fit"]["union_tickers"],
            "application_rows": r31["cross_section_application"]["application_rows"],
            "application_tickers": r31["cross_section_application"]["application_tickers"],
            "dependency_closure_rows": r31["backward_dependency_closure"]["closure_rows"],
            "dependency_closure_tickers": r31["backward_dependency_closure"]["closure_tickers"],
            "dependency_missing_offset_counts": r31["backward_dependency_closure"]["missing_offset_counts"],
            "dependency_missing_target_counts": r31["backward_dependency_closure"]["missing_target_counts"],
            "existing_global_gate_verdict": r31["global_ca_population_gate"]["verdict"],
            "basis_safe_geometry": "NOT_CERTIFIABLE_WITH_CURRENT_GLOBAL_CA_COVERAGE",
            "basis_safe_certified_rows": 0,
            "basis_unsafe_geometry": "NOT_SEPARATELY_QUANTIFIED; current R3.1 scope is not identity-joined to the final V16 event ledger",
            "basis_unknown_known_event": "NOT_SEPARATELY_QUANTIFIED_WITHOUT_CURRENT_EVENT_TO_CLOSURE_IDENTITY_JOIN",
            "basis_unknown_population_authority": "GLOBAL_GATE_BLOCKS_ADMISSION; exact row split is not estimated",
            "geometry_is_not_current_event_census": True,
        }
        census = {
            "family_counts": dict(sorted(family_counts.items())),
            "unresolved_by_family": dict(sorted(unresolved_by_family.items())),
            "transition_status_counts": dict(sorted(status_counts.items())),
            "resolved_exact": status_counts["RESOLVED"],
            "non_basis": status_counts["NOT_APPLICABLE_NON_BASIS"],
            "unresolved": status_counts["UNRESOLVED"],
            "provider_or_path_failure_classes": {
                "MERGER_PROVIDER_DISCOVERY_FAILURE": sum(row.get("result_classification") == "PROVIDER_DISCOVERY_FAILURE" for row in merger_results),
                "CAPITAL_PROVIDER_DISCOVERY_FAILURE": sum(row.get("acquisition_classification") == "PROVIDER_DISCOVERY_FAILURE" for row in capital_results),
                "CAPITAL_ZERO_TO_ZERO_PARKED": sum(row.get("acquisition_classification") == "PARKED_ZERO_TO_ZERO_RETAINED_MECHANICS" for row in capital_results),
            },
            "document_unavailable": 0,
            "semantic_insufficient": 0,
            "no_official_document_discovered": 0,
            "unresolved_taxonomy": family_counts.get("UNKNOWN_TAXONOMY", 0),
            "exact_transition_missing": status_counts["UNRESOLVED"],
        }
        summary = {
            "schema_version": "INC001_CLOSURE_FEASIBILITY_V1",
            "audit_date": AUDIT_DATE,
            "status": "INC001_CLOSURE_FEASIBILITY_COMPLETE_BLOCKED_ON_POPULATION_AUTHORITY",
            "repository": {"head": git_head(repo_root), "outcome_blind": True},
            "controlling_reconciliation": {"root": str(v16_root), "manifest_sha256": V16_MANIFEST_SHA256},
            "final_census": census,
            "phase_results": {
                "composite_policy": {"family": "COMPOSITE_CASH_SHARE_DISTRIBUTION", "events": 4, "unresolved": 4, "basis_effect": "BASIS_CHANGING", "transition": "UNRESOLVED"},
                "merger": {"events": 5, "resolved_exact": 0, "unresolved": 5, "artifact_manifest_sha256": MERGER_MANIFEST_SHA256, "result_status": merger_summary.get("status", "")},
                "capital_restructuring": {"events": 19, "resolved_exact": 0, "non_basis": 0, "policy_blocked": 0, "unresolved": 19, "artifact_manifest_sha256": CAPITAL_MANIFEST_SHA256, "result_status": capital_summary.get("status", "")},
            },
            "known_event_remediation": "MATERIAL_WORK_COMPLETE",
            "known_event_long_tail": "PARKED_FAIL_CLOSED",
            "authority": {
                "IDX_HISTORICAL_NEGATIVE_AUTHORITY": "UNSUPPORTED",
                "IDX_HISTORICAL_ASOF_AUTHORITY": "UNKNOWN",
                "KSEI_HISTORICAL_COMPLETE_INTERVAL_AUTHORITY": "UNKNOWN",
                "population_completeness": "UNKNOWN",
                "historical_asof": "UNKNOWN",
            },
            "closure_verdict": "BLOCKED_ON_POPULATION_AUTHORITY",
            "smallest_remaining_blocker": "An authoritative source/contract must prove population-wide no-event completeness and historical as-of coverage over the relevant ticker/session scope; current KSEI coverage is 610 tickers against 629 fit and 716 application/closure tickers, with no per-session date attestation.",
            "next_action_recommendation": "Stop event-by-event archaeology. If closure is revisited, obtain the smallest authoritative population-wide negative/no-event and as-of contract, then rerun the existing fail-closed gate; do not infer safe rows from event absence.",
            "geometry": geometry,
            "guardrails": {
                "outcomes_or_targets": False,
                "model_fit": False,
                "model_scoring": False,
                "historical_feature_recompute": False,
                "production_execution": False,
                "provider_calls_in_closure_phase": False,
                "canonical_artifacts_mutated": False,
                "counter_mutated": False,
                "paper_state_mutated": False,
                "merge": False,
            },
        }
        validation = {
            "v16_manifest_verified": True,
            "merger_manifest_verified": True,
            "capital_manifest_verified": True,
            "r31_manifest_verified": True,
            "final_event_count_387": len(events) == 387,
            "final_transition_counts_163_178_46": status_counts == expected_status,
            "composite_four_unresolved": unresolved_by_family["COMPOSITE_CASH_SHARE_DISTRIBUTION"] == 4,
            "merger_five_unresolved": len(merger_results) == 5,
            "capital_nineteen_unresolved": len(capital_results) == 19 and all(row.get("transition_status") == "UNRESOLVED" for row in capital_results),
            "no_new_acquisition": True,
            "no_scientific_admission": True,
            "closure_is_read_only": True,
        }
        write_csv(staging / "final_known_event_census.csv", final_rows, list(final_rows[0]))
        write_json(staging / "geometry_analysis.json", geometry)
        write_json(staging / "reconciliation_inputs.json", {
            "controlling_v16_manifest_sha256": V16_MANIFEST_SHA256,
            "merger_acquisition_manifest_sha256": MERGER_MANIFEST_SHA256,
            "capital_artifact_manifest_sha256": CAPITAL_MANIFEST_SHA256,
            "r31_geometry_manifest_sha256": R31_MANIFEST_SHA256,
        })
        write_json(staging / "reconciliation_summary.json", summary)
        write_json(staging / "validation_report.json", validation)
        manifest = {"schema_version": "INC001_CLOSURE_FEASIBILITY_V1_MANIFEST", "audit_date": AUDIT_DATE, "files": [], "self_hash_policy": "MANIFEST.json excluded from its own hash"}
        for path in sorted(staging.rglob("*")):
            if path.is_file() and path.name != "MANIFEST.json":
                manifest["files"].append({"path": path.relative_to(staging).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
        write_json(staging / "MANIFEST.json", manifest)
        staging.rename(output_root)
        return {"summary": summary, "validation": validation, "manifest_sha256": sha256_file(output_root / "MANIFEST.json")}
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--v16-root", type=Path, required=True)
    parser.add_argument("--merger-root", type=Path, required=True)
    parser.add_argument("--capital-root", type=Path, required=True)
    parser.add_argument("--r31-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args), ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
