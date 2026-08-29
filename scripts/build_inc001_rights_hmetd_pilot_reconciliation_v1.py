"""Outcome-blind successor reconciliation for the bounded RIGHTS_HMETD pilot.

The builder consumes the immutable V9 reconciliation and the immutable bounded
pilot root.  It re-runs the existing economic-event reconciler over all 412
source representations, accepts only pilot rows with explicit official
regular-market Ex evidence, and refuses to invent linkages from a single
event-document result.  It never calls providers and never edits canonical
historical data.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import build_inc001_economic_reconciliation_v1 as base
from idx_trade import ca_economic_event_reconciliation_v1 as econ


AUDIT_DATE = "2026-08-30"
SCHEMA = "inc001_rights_hmetd_pilot_reconciliation_v1"
PROJECT_ROOT = Path(r"D:\Documents\Project")
V9_ROOT = PROJECT_ROOT / "idx-ca-economic-event-reconciliation-20260829-v9-stock-split-linkage-correction-final"
V9_MANIFEST_SHA256 = "dcc5e05ca3bc5fe7da148629a26fb913a6e85b92a88cbc88180cfde05eec30cc"
PILOT_ROOT = PROJECT_ROOT / "idx-ca-rights-hmetd-pilot-20260830-v1"

LINKAGE_FIELDS = [
    "left_source_event_id",
    "right_source_event_id",
    "relation",
    "authority_source_ref",
    "authority_evidence_sha256",
    "ticker",
    "source_families",
    "linkage_reason",
]
LINKAGE_DELTA_FIELDS = [
    "delta_status",
    "left_source_event_id",
    "right_source_event_id",
    "ticker",
    "source_families",
    "authority_source_ref",
    "authority_evidence_sha256",
    "reason",
]
EVENT_FIELDS = [
    "economic_event_id",
    "source_event_ids",
    "source_kinds",
    "economic_family",
    "basis_effect",
    "classification_conflict",
    "transition_status",
    "transition_date",
    "transition_semantics",
]


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid_sha(value: Any) -> bool:
    return econ.valid_sha256(value)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def core_adjudications(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    fields = ("source_event_id", "adjudication_status", "economic_family", "basis_effect", "authority_source_ref", "authority_evidence_sha256")
    return [{field: row.get(field, "") for field in fields} for row in rows]


def core_linkages(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    fields = ("left_source_event_id", "right_source_event_id", "relation", "authority_source_ref", "authority_evidence_sha256")
    return [{field: row.get(field, "") for field in fields} for row in rows]


def core_transitions(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    fields = ("source_event_id", "transition_status", "transition_semantic", "transition_date", "authority_source_ref", "authority_evidence_sha256")
    return [{field: row.get(field, "") for field in fields} for row in rows]


def pilot_transitions(
    pilot_results: Sequence[Mapping[str, Any]],
    source_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in pilot_results:
        if text(result.get("result_classification")) != "RESOLVED_EXACT":
            continue
        source_ids = [item for item in text(result.get("source_event_ids")).split("|") if item]
        if not source_ids or any(item not in source_by_id for item in source_ids):
            raise RuntimeError(f"pilot resolved result references unknown source event: {result.get('economic_event_id')}")
        ref = text(result.get("authority_source_ref"))
        sha = text(result.get("authority_evidence_sha256")).lower()
        semantic = text(result.get("transition_semantic"))
        transition_date = text(result.get("transition_date"))[:10]
        if semantic != "REGULAR_MARKET_EX_DATE" or not transition_date or not ref or not valid_sha(sha):
            raise RuntimeError(f"pilot RESOLVED_EXACT lacks accepted source-bound transition evidence: {result.get('economic_event_id')}")
        for source_id in source_ids:
            source = source_by_id[source_id]
            rows.append({"source_event_id": source_id, "transition_status": "RESOLVED", "transition_semantic": semantic, "transition_date": transition_date, "authority_source_ref": ref, "authority_evidence_sha256": sha, "source_kind": source.get("source_kind", ""), "ticker": source.get("ticker", ""), "event_family": source.get("event_family", ""), "candidate_date": source.get("candidate_date", ""), "transition_reason": "pilot official rights schedule explicitly states regular-market Ex date"})
    return sorted(rows, key=lambda row: text(row.get("source_event_id")))


def pilot_linkage_delta(
    pilot_results: Sequence[Mapping[str, Any]],
    prior_linkages: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep V9 linkages unless a future pilot carries explicit pair evidence.

    The current pilot result schema has no official-document-backed pair field;
    therefore a resolved single economic event can never silently collapse a
    second source representation.  This is the required conservative result.
    """
    recomputed = [dict(row) for row in prior_linkages]
    resolved = [row for row in pilot_results if text(row.get("result_classification")) == "RESOLVED_EXACT"]
    delta = [{"delta_status": "NO_NEW_RIGHTS_LINKAGES", "left_source_event_id": "", "right_source_event_id": "", "ticker": "", "source_families": "RIGHTS_HMETD", "authority_source_ref": "", "authority_evidence_sha256": "", "reason": "pilot produced no explicit source-pair evidence; single-event transition evidence cannot collapse source representations"}]
    if resolved:
        delta[0]["reason"] += "; resolved pilot transitions remain one source event unless an independently audited document pair is retained"
    return recomputed, delta


def doc_rows(v9_root: Path, pilot_root: Path) -> list[dict[str, Any]]:
    rows = read_csv(v9_root / "retained_document_evidence.csv")
    for row in read_csv(pilot_root / "official_document_evidence.csv"):
        item = dict(row)
        item["evidence_role"] = "OFFICIAL_RIGHTS_HMETD_PILOT_DOCUMENT"
        rows.append(item)
    return rows


def source_mapping(
    source: Sequence[Mapping[str, Any]],
    economic_rows: Sequence[Mapping[str, Any]],
    transitions: Sequence[Mapping[str, Any]],
    accepted_linkages: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    source_by_id = {text(row.get("source_event_id")): row for row in source}
    transition_by_id = {text(row.get("source_event_id")): row for row in transitions}
    linked_mconv_ids = {
        source_id
        for row in accepted_linkages
        if "MANDATORY_CONVERSION" in text(row.get("source_families"))
        for source_id in (text(row.get("left_source_event_id")), text(row.get("right_source_event_id")))
        if source_by_id.get(source_id, {}).get("source_kind") == "KSEI_REGISTERED_SECURITY_HISTORY"
    }
    rows: list[dict[str, Any]] = []
    for event in economic_rows:
        event_id = text(event.get("economic_event_id"))
        for source_id in text(event.get("source_event_ids")).split("|"):
            if not source_id:
                continue
            source_row = source_by_id[source_id]
            transition = transition_by_id.get(source_id, {})
            role = "PROVEN_SAME_EVENT_REPRESENTATION" if source_id in linked_mconv_ids else ("TRANSITION_BEARING_SOURCE_REPRESENTATION" if text(transition.get("transition_status")) == "RESOLVED" else "ECONOMIC_EVENT_SOURCE_REPRESENTATION")
            rows.append({"source_event_id": source_id, "economic_event_id": event_id, "source_kind": text(source_row.get("source_kind")), "ticker": text(source_row.get("ticker")), "source_native_label": text(source_row.get("source_native_label")), "candidate_date": text(source_row.get("candidate_date")), "ratio_raw": text(source_row.get("ratio_raw")), "source_representation_role": role, "economic_event_transition_status": text(event.get("transition_status")), "economic_event_transition_date": text(event.get("transition_date")), "economic_event_transition_semantics": text(event.get("transition_semantics")), "transition_authority_source_ref": text(transition.get("authority_source_ref")), "transition_authority_evidence_sha256": text(transition.get("authority_evidence_sha256")).lower()})
    return sorted(rows, key=lambda row: (row["economic_event_id"], row["source_event_id"]))


def post_pilot_plan(result: Mapping[str, Any], source_by_id: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    economic_rows = base.economic_csv_rows(result)
    unresolved = [row for row in economic_rows if text(row.get("transition_status")) == "UNRESOLVED"]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in unresolved:
        grouped.setdefault(text(row.get("economic_family")), []).append(row)
    units = []
    for family, rows in sorted(grouped.items()):
        members = [member for row in rows for member in text(row.get("source_event_ids")).split("|") if member]
        units.append({"unit_id": f"EVENT-{family}-RESIDUAL", "family": family, "status": "OPEN_RESIDUAL", "event_ids": sorted(text(row.get("economic_event_id")) for row in rows), "tickers": sorted({text(source_by_id[member].get("ticker")) for member in members}), "event_count": len(rows), "remaining_semantic": base.gap_rows(result, source_by_id)[next(index for index, gap in enumerate(base.gap_rows(result, source_by_id)) if gap["economic_family"] == family)]["missing_semantic"]})
    return {"schema_version": f"{SCHEMA}_future_plan", "status": "PLAN_ONLY_NO_BULK_ACQUISITION_AUTHORIZED", "unresolved_event_count": len(unresolved), "pilot_resolved_event_ids": sorted(text(row.get("economic_event_id")) for row in read_csv(PILOT_ROOT / "target_event_results.csv") if text(row.get("result_classification")) == "RESOLVED_EXACT"), "units": units, "rights_pilot_is_not_bulk_71": True, "capability_verification_requests": "separate bounded pilot only", "later_bulk_acquisition": "not executed", "guardrails": {"full_71_acquisition": False, "phase_e": False, "outcomes_or_targets": False, "fit_refit_score": False, "counter_mutation": False, "canonical_historical_rewrite": False, "production_execution": False, "merge": False}}


def manifest_for(root: Path) -> dict[str, Any]:
    outputs = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.json":
            outputs[str(path.relative_to(root)).replace("\\", "/")] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    return {"manifest_version": f"{SCHEMA}_manifest", "artifact_root": str(root), "audit_date": AUDIT_DATE, "outcome_blind": True, "provider_calls": False, "output_hashes_excluding_manifest": outputs, "self_hash_policy": "MANIFEST.json excluded from its own hash"}


def git_head(repo_root: Path) -> str:
    return subprocess.check_output(["git", "-C", str(repo_root), "rev-parse", "HEAD"], text=True).strip()


def build(output_root: Path, repo_root: Path = REPO_ROOT, v9_root: Path = V9_ROOT, pilot_root: Path = PILOT_ROOT) -> dict[str, Any]:
    if output_root.exists() or output_root.with_name(output_root.name + ".staging").exists():
        raise FileExistsError(f"immutable reconciliation root already exists: {output_root}")
    staging = output_root.with_name(output_root.name + ".staging")
    staging.mkdir(parents=True)
    try:
        if sha256_file(v9_root / "MANIFEST.json").lower() != V9_MANIFEST_SHA256.lower():
            raise RuntimeError("controlling V9 manifest hash mismatch")
        pilot_manifest = read_json(pilot_root / "MANIFEST.json")
        if not pilot_manifest.get("provider_calls") or pilot_manifest.get("controlling_v9_manifest_sha256", "") not in {"", V9_MANIFEST_SHA256}:
            raise RuntimeError("pilot root provider/provenance pin is invalid")
        source = read_csv(v9_root / "source_evidence_ledger.csv")
        source_by_id = {text(row.get("source_event_id")): row for row in source}
        if len(source) != 412 or len(source_by_id) != 412:
            raise RuntimeError("V9 source evidence is not exactly 412 unique rows")
        adjudications = read_csv(v9_root / "economic_adjudication_ledger.csv")
        prior_linkages = read_csv(v9_root / "proven_same_event_linkage_ledger.csv")
        transitions = read_csv(v9_root / "transition_attestation_ledger.csv")
        pilot_results = read_csv(pilot_root / "target_event_results.csv")
        if len(pilot_results) != 12:
            raise RuntimeError(f"pilot target conservation failed: {len(pilot_results)}")
        rights_scope = [row for row in read_csv(pilot_root / "rights_event_scope.csv")]
        if len(rights_scope) != 71 or len({text(row.get("economic_event_id")) for row in rights_scope}) != 71:
            raise RuntimeError("pilot did not preserve exactly 71 current rights events")
        transitions = transitions + pilot_transitions(pilot_results, source_by_id)
        recomputed_linkages, linkage_delta = pilot_linkage_delta(pilot_results, prior_linkages)
        result = econ.reconcile_economic_events(source, adjudications=core_adjudications(adjudications), linkages=core_linkages(recomputed_linkages), transition_attestations=core_transitions(transitions))
        economic_rows = base.economic_csv_rows(result)
        unresolved = [row for row in economic_rows if text(row.get("transition_status")) == "UNRESOLVED"]
        non_basis = [row for row in economic_rows if text(row.get("transition_status")) == "NOT_APPLICABLE_NON_BASIS"]
        actual = {key: result[key] for key in ("source_evidence_rows", "cross_source_collapses", "same_source_collapses", "economic_event_count", "resolved_transitions", "unresolved_transitions", "non_basis_excluded")}
        prior = {"source_evidence_rows": 412, "cross_source_collapses": 22, "same_source_collapses": 3, "economic_event_count": 387, "resolved_transitions": 157, "unresolved_transitions": 184, "non_basis_excluded": 46}
        comparison = {key: {"prior": prior[key], "actual": actual[key], "delta": actual[key] - prior[key]} for key in prior}
        pilot_resolved = [row for row in pilot_results if text(row.get("result_classification")) == "RESOLVED_EXACT"]
        classification_counts = {key: sum(text(row.get("result_classification")) == key for row in pilot_results) for key in sorted({text(row.get("result_classification")) for row in pilot_results})}
        source_docs = doc_rows(v9_root, pilot_root)
        hash_failures = [row for row in source_docs if text(row.get("evidence_role")) == "OFFICIAL_RIGHTS_HMETD_PILOT_DOCUMENT" and (not valid_sha(row.get("evidence_sha256")) or text(row.get("hash_matches_bytes")) != "true")]
        mapping = source_mapping(source, economic_rows, transitions, recomputed_linkages)
        baseline_plan = read_json(v9_root / "future_acquisition_plan_v11_291.json")
        validation = {"controlling_v9_manifest_verified": True, "pilot_manifest_provider_calls": bool(pilot_manifest.get("provider_calls")), "source_evidence_rows": len(source), "source_representation_mapping_conserved": len(mapping) == len(source), "rights_total_current": len(rights_scope), "pilot_tested": len(pilot_results), "pilot_resolved": len(pilot_resolved), "pilot_result_classifications_conserved": sum(classification_counts.values()) == len(pilot_results), "resolved_pilot_transitions_source_bound": all(text(row.get("authority_source_ref")) and valid_sha(row.get("authority_evidence_sha256")) and text(row.get("transition_semantic")) == "REGULAR_MARKET_EX_DATE" for row in pilot_transitions(pilot_results, source_by_id)), "retained_pilot_document_hash_failures": len(hash_failures), "prior_linkages": len(prior_linkages), "recomputed_linkages": len(recomputed_linkages), "new_linkages": len(recomputed_linkages) - len(prior_linkages), "removed_or_conflicting_linkages": 0, "no_heuristic_rights_linkage": len(recomputed_linkages) == len(prior_linkages), "all_resolved_transitions_have_ref_sha": all(text(row.get("authority_source_ref")) and valid_sha(row.get("authority_evidence_sha256")) for row in transitions if text(row.get("transition_status")) == "RESOLVED"), "collapse_arithmetic": len(source) - result["cross_source_collapses"] - result["same_source_collapses"] == result["economic_event_count"], "transition_arithmetic": result["resolved_transitions"] + result["unresolved_transitions"] + result["non_basis_excluded"] == result["economic_event_count"], "baseline_291_plan_conserved": baseline_plan.get("baseline_unresolved_physical_event_count") == 291, "no_provider_calls_in_reconciliation": True, "scientific_verdict_unchanged": True}
        if not all(value for value in validation.values() if isinstance(value, bool)):
            raise RuntimeError(f"post-pilot validation failed: {validation}")
        summary = {"schema_version": SCHEMA, "audit_date": AUDIT_DATE, "status": "LOCAL_POST_PILOT_RECONCILIATION_COMPLETE_NO_SCIENTIFIC_ADMISSION", "controlling_predecessor_root": str(v9_root), "controlling_predecessor_manifest_sha256": V9_MANIFEST_SHA256, "pilot_root": str(pilot_root), "pilot_manifest_sha256": sha256_file(pilot_root / "MANIFEST.json"), "counts": actual, "before_after_comparison": comparison, "rights_pilot": {"rights_total_current": len(rights_scope), "pilot_tested": len(pilot_results), "pilot_resolved": len(pilot_resolved), "classification_counts": classification_counts, "new_linkages": len(recomputed_linkages) - len(prior_linkages), "remaining_unresolved_pilot_events": len(pilot_results) - len(pilot_resolved), "source_capability_after_pilot": read_json(pilot_root / "source_path_capability_assessment.json").get("verdict"), "proven_path_count": sum(text(row.get("result_classification")) == "RESOLVED_EXACT" for row in pilot_results), "without_proven_path_count": sum(text(row.get("result_classification")) != "RESOLVED_EXACT" for row in pilot_results)}, "linkage_audit": {"prior_proven_linkages": len(prior_linkages), "recomputed_proven_linkages": len(recomputed_linkages), "new_proven_linkages": len(recomputed_linkages) - len(prior_linkages), "removed_or_conflicting_linkages": 0}, "post_pilot_future_plan": {"unresolved_event_count": len(unresolved), "rights_unresolved_event_count": sum(text(row.get("economic_family")) == "RIGHTS_HMETD" for row in unresolved), "plan_is_not_bulk_71": True}, "family_distribution": dict(sorted(Counter(text(row.get("economic_family")) for row in economic_rows).items())), "unresolved_by_source": dict(sorted(Counter(source_by_id[member]["source_kind"] for event in result["economic_events"] if event["transition_status"] == "UNRESOLVED" for member in event["source_event_ids"]).items())), "residual_geometry": base.gap_rows(result, source_by_id), "validation": validation, "scientific_verdict_unchanged": {"DATA_ADMISSION": "FAIL", "RESEARCH_ADMISSION": "FAIL", "MODEL_PROMOTION": "NOT_EVALUATED", "HISTORICAL_APPLICATION": "BLOCKED_PHASE_E_NOT_RUN", "REFIT_AUTHORIZED": False, "COUNTER_ACTION": "NONE"}, "guardrails": {"full_71_acquisition": False, "phase_e": False, "outcomes_or_targets": False, "fit_refit_score": False, "counter_mutation": False, "canonical_historical_rewrite": False, "production_execution": False, "merge": False}}
        shutil.copytree(pilot_root, staging / "pilot_acquisition", dirs_exist_ok=False)
        copy_file(pilot_root / "rights_event_scope.csv", staging / "rights_event_scope.csv")
        copy_file(pilot_root / "candidate_linkage_audit.csv", staging / "candidate_linkage_audit.csv")
        copy_file(pilot_root / "pilot_selection.csv", staging / "pilot_selection.csv")
        write_csv(staging / "source_evidence_ledger.csv", source, base.SOURCE_FIELDS)
        write_csv(staging / "retained_document_evidence.csv", source_docs, sorted({field for row in source_docs for field in row}))
        write_csv(staging / "economic_adjudication_ledger.csv", adjudications, base.ADJ_FIELDS)
        write_csv(staging / "prior_proven_same_event_linkage_ledger.csv", prior_linkages, LINKAGE_FIELDS)
        write_csv(staging / "recomputed_candidate_linkage_ledger.csv", recomputed_linkages, LINKAGE_FIELDS)
        write_csv(staging / "proven_same_event_linkage_ledger.csv", recomputed_linkages, LINKAGE_FIELDS)
        write_csv(staging / "independently_accepted_linkage_ledger.csv", recomputed_linkages, LINKAGE_FIELDS)
        write_csv(staging / "linkage_delta_report.csv", linkage_delta, LINKAGE_DELTA_FIELDS)
        write_csv(staging / "transition_attestation_ledger.csv", transitions, base.TRANSITION_FIELDS)
        write_csv(staging / "economic_event_ledger.csv", economic_rows, EVENT_FIELDS)
        write_csv(staging / "unresolved_economic_event_ledger.csv", unresolved, EVENT_FIELDS)
        write_csv(staging / "non_basis_exclusion_ledger.csv", non_basis, EVENT_FIELDS)
        write_csv(staging / "source_to_economic_mapping.csv", mapping, list(mapping[0].keys()))
        write_csv(staging / "remaining_gap_geometry.csv", base.gap_rows(result, source_by_id), ["economic_family", "economic_event_count", "ticker_count", "tickers", "economic_event_ids", "source_kinds", "missing_semantic"])
        write_csv(staging / "target_event_results.csv", pilot_results, list(pilot_results[0].keys()))
        write_json(staging / "reconciliation_summary.json", summary)
        write_json(staging / "validation_report.json", validation)
        write_json(staging / "post_pilot_future_acquisition_plan.json", post_pilot_plan(result, source_by_id))
        copy_file(v9_root / "future_acquisition_plan_v11_291.json", staging / "future_acquisition_plan_v11_291.json")
        copy_file(v9_root / "future_acquisition_plan_v2.json", staging / "future_acquisition_plan_v2.json")
        write_json(staging / "deterministic_input_pins.json", {"controlling_v9_root": str(v9_root), "controlling_v9_manifest_sha256": V9_MANIFEST_SHA256, "pilot_root": str(pilot_root), "pilot_manifest_sha256": sha256_file(pilot_root / "MANIFEST.json"), "repo_head": git_head(repo_root), "provider_calls_in_reconciliation": False})
        write_json(staging / "MANIFEST.json", manifest_for(staging))
        staging.rename(output_root)
        return summary
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def compare_non_manifest(first: Path, second: Path) -> dict[str, Any]:
    first_files = {str(path.relative_to(first)).replace("\\", "/") for path in first.rglob("*") if path.is_file() and path.name != "MANIFEST.json"}
    second_files = {str(path.relative_to(second)).replace("\\", "/") for path in second.rglob("*") if path.is_file() and path.name != "MANIFEST.json"}
    differences = []
    for name in sorted(first_files | second_files):
        left, right = first / name, second / name
        if not left.is_file() or not right.is_file() or left.read_bytes() != right.read_bytes():
            differences.append(name)
    return {"first_root": str(first), "second_root": str(second), "compared_file_count": len(first_files | second_files), "differences": differences, "verdict": "PASS" if first_files == second_files and not differences else "FAIL"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--rerun-root", type=Path)
    args = parser.parse_args()
    first = build(args.output_root)
    payload: dict[str, Any] = {"summary": first}
    if args.rerun_root:
        build(args.rerun_root)
        comparison = compare_non_manifest(args.output_root, args.rerun_root)
        write_json(args.output_root / "deterministic_non_manifest_comparison.json", comparison)
        write_json(args.rerun_root / "deterministic_non_manifest_comparison.json", comparison)
        write_json(args.output_root / "MANIFEST.json", manifest_for(args.output_root))
        write_json(args.rerun_root / "MANIFEST.json", manifest_for(args.rerun_root))
        payload["comparison"] = comparison
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload.get("comparison", {}).get("verdict", "PASS") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
