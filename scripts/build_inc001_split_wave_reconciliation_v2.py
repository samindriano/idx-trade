"""Build the immutable post-acquisition INC-001 split-wave reconciliation.

The predecessor V3 reconciliation remains immutable.  This successor reuses
its retained source/probe inputs, adds the newly retained HEAL and SCMA
official schedules, and preserves the BBRM reverse-split probe as semantic-
insufficient.  It is outcome-blind and never edits canonical data.
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
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_inc001_economic_reconciliation_v1 as base


AUDIT_DATE = "2026-08-29"
SCHEMA = "inc001_ca_economic_event_reconciliation_v3"
PROJECT_ROOT = Path(r"D:\Documents\Project")
PRIOR_ACQUISITION_ROOT = PROJECT_ROOT / "idx-ca-stock-split-acquisition-20260829-v1"
LEGACY_ACQUISITION_ROOT = PROJECT_ROOT / "idx-ca-stock-split-acquisition-20260829-v3"
NEW_ACQUISITION_ROOT = PROJECT_ROOT / "idx-ca-stock-split-discovery-20260829-v5"
PROBE_ROOT = PROJECT_ROOT / "idx-ca-transition-capability-probe-20260829-v1"
PRIOR_RECONCILIATION_ROOT = PROJECT_ROOT / "idx-ca-economic-event-reconciliation-20260829-v7-split-wave"
SOURCE_MANIFEST_SHA256 = "556ab328b8f5663ce98450de46e8e7eed0f9e86d42d8d51506158b5fec323b71"
SOURCE_AUTHORITY_ROOT = PROJECT_ROOT / "idx-ca-source-authority-audit-20260829-v11-deterministic-rerun-v8"
SOURCE_AUTHORITY_PLAN = SOURCE_AUTHORITY_ROOT / "acquisition_requirements_v11.json"
PRIOR_RECONCILIATION_MANIFEST_SHA256 = "575982a3f1f179ff3b0267d40589f4886db6f593be49bcedb8aa1885f1b2725d"
LEGACY_ACQUISITION_MANIFEST_SHA256 = "cdd96f746df3edf224f314a82993aac61d79324b4e8b46d96bcad74fe673a1a6"
V4_MANIFEST_SHA256 = "3af6a92738f560f26699725e2f8cf6200dc1dff3fcc6a79d899cb9911d6499bc"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def compatible_document_inventory(acquisition_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entries = json.loads((acquisition_root / "provider" / "document_request_ledger.json").read_text(encoding="utf-8"))
    documents: list[dict[str, Any]] = []
    parsed: list[dict[str, Any]] = []
    for number, entry in enumerate(entries, start=1):
        document = base.parse_document(entry, acquisition_root, f"ACQ-DOC-{number:03d}")
        if document is None:
            continue
        documents.append(document)
        if text(entry.get("status_code")) == "200" and document["parser_status"] == "PARSED_EXACT_STOCK_SPLIT_SCHEDULE":
            parsed.append(document)
    return documents, parsed


def discovery_document_inventory(acquisition_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entries = read_csv(acquisition_root / "official_document_evidence.csv")
    documents: list[dict[str, Any]] = []
    parsed: list[dict[str, Any]] = []
    for number, entry in enumerate(entries, start=1):
        document = dict(entry)
        document["document_number"] = text(entry.get("document_number")) or str(number)
        raw_path = Path(text(document.get("raw_path")))
        text_path = Path(text(document.get("text_path")))
        if not raw_path.is_file() or not text_path.is_file():
            raise RuntimeError(f"discovery document lacks retained bytes: {document.get('document_id')}")
        actual_sha = sha256_file(raw_path)
        document["actual_sha256"] = actual_sha
        document["bytes_actual"] = str(raw_path.stat().st_size)
        document["hash_matches_bytes"] = str(base.valid_sha(document.get("evidence_sha256")) and actual_sha == text(document.get("evidence_sha256")).lower()).lower()
        document["bytes_ledger"] = text(document.get("bytes"))
        documents.append(document)
        if text(document.get("status_code")) == "200" and document["parser_status"] == "PARSED_EXACT_STOCK_SPLIT_SCHEDULE" and text(document.get("explicit_regular_market_semantic")) == "true" and text(document.get("hash_matches_bytes")) == "true":
            parsed.append(document)
    return documents, parsed


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


def linkage_key(row: Mapping[str, Any]) -> tuple[str, str]:
    return (text(row.get("left_source_event_id")), text(row.get("right_source_event_id")))


def validate_linkage_rows(
    source: Sequence[Mapping[str, Any]],
    rows: Sequence[Mapping[str, Any]],
    discovery_documents: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate candidate linkages and return canonical rows plus discovery deltas.

    The base matcher supplies candidates, but a successor may accept a new
    pair only when its authority ref/hash is present in the retained V5 exact
    documents.  This keeps linkage admission source-bound without changing
    the base reconciliation contract.
    """
    source_ids = {text(row.get("source_event_id")) for row in source}
    discovery_evidence = {
        (text(row.get("source_ref")), text(row.get("evidence_sha256")).lower())
        for row in discovery_documents
        if text(row.get("parser_status")) == "PARSED_EXACT_STOCK_SPLIT_SCHEDULE"
        and text(row.get("explicit_regular_market_semantic")) == "true"
        and base.valid_sha(row.get("evidence_sha256"))
    }
    canonical: list[dict[str, Any]] = []
    seen: dict[tuple[str, str], tuple[str, str]] = {}
    for row in rows:
        candidate = {field: text(row.get(field)) for field in LINKAGE_FIELDS}
        left, right = linkage_key(candidate)
        if not left or not right or left == right or left not in source_ids or right not in source_ids:
            raise RuntimeError(f"invalid recomputed linkage source IDs: {left}, {right}")
        if candidate["relation"] != "PROVEN_SAME_ECONOMIC_EVENT":
            raise RuntimeError(f"unexpected linkage relation: {candidate['relation']}")
        authority = (candidate["authority_source_ref"], candidate["authority_evidence_sha256"].lower())
        if not authority[0] or not base.valid_sha(authority[1]):
            raise RuntimeError(f"recomputed linkage lacks source-bound authority: {left}, {right}")
        prior_authority = seen.get((left, right))
        if prior_authority is not None and prior_authority != authority:
            raise RuntimeError(f"conflicting authority for linkage pair: {left}, {right}")
        seen[(left, right)] = authority
        candidate["authority_evidence_sha256"] = authority[1]
        canonical.append(candidate)
    canonical.sort(key=linkage_key)
    return canonical, [
        {
            "delta_status": "NEW_PROVEN_SAME_ECONOMIC_EVENT",
            **{field: row.get(field, "") for field in ("left_source_event_id", "right_source_event_id", "ticker", "source_families", "authority_source_ref", "authority_evidence_sha256")},
            "reason": "new pair is accepted only because the retained V5 exact official schedule is source/ref/SHA-bound",
        }
        for row in canonical
        if (text(row.get("authority_source_ref")), text(row.get("authority_evidence_sha256")).lower()) in discovery_evidence
    ]


def audit_linkage_delta(
    source: Sequence[Mapping[str, Any]],
    prior: Sequence[Mapping[str, Any]],
    recomputed: Sequence[Mapping[str, Any]],
    discovery_documents: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    prior_rows = [{field: text(row.get(field)) for field in LINKAGE_FIELDS} for row in prior]
    candidate_rows, _ = validate_linkage_rows(source, recomputed, discovery_documents)
    prior_by_key = {linkage_key(row): row for row in prior_rows}
    candidate_by_key = {linkage_key(row): row for row in candidate_rows}
    if len(prior_by_key) != len(prior_rows) or len(candidate_by_key) != len(candidate_rows):
        raise RuntimeError("duplicate linkage pair in prior or recomputed ledger")
    new_keys = sorted(set(candidate_by_key) - set(prior_by_key))
    removed_keys = sorted(set(prior_by_key) - set(candidate_by_key))
    changed_keys = sorted(
        key
        for key in set(prior_by_key) & set(candidate_by_key)
        if (
            prior_by_key[key]["authority_source_ref"],
            prior_by_key[key]["authority_evidence_sha256"].lower(),
        )
        != (
            candidate_by_key[key]["authority_source_ref"],
            candidate_by_key[key]["authority_evidence_sha256"].lower(),
        )
    )
    if removed_keys or changed_keys:
        raise RuntimeError(f"recomputed linkage removal/conflict: removed={removed_keys}, changed={changed_keys}")
    discovery_evidence = {
        (text(row.get("source_ref")), text(row.get("evidence_sha256")).lower())
        for row in discovery_documents
        if text(row.get("parser_status")) == "PARSED_EXACT_STOCK_SPLIT_SCHEDULE"
        and text(row.get("explicit_regular_market_semantic")) == "true"
        and base.valid_sha(row.get("evidence_sha256"))
    }
    new_rows = [candidate_by_key[key] for key in new_keys]
    for row in new_rows:
        evidence = (text(row.get("authority_source_ref")), text(row.get("authority_evidence_sha256")).lower())
        if evidence not in discovery_evidence:
            raise RuntimeError(f"new linkage is not bound to retained V5 discovery evidence: {linkage_key(row)}")
    delta: list[dict[str, Any]] = []
    for key in sorted(set(prior_by_key) | set(candidate_by_key)):
        row = candidate_by_key.get(key, prior_by_key.get(key, {}))
        if key in new_keys:
            status = "NEW_PROVEN_SAME_ECONOMIC_EVENT"
            reason = "new retained V5 official schedule proves the same economic event across source representations"
        else:
            status = "UNCHANGED_PRIOR_PROVEN_LINKAGE"
            reason = "prior V7 linkage remains present with unchanged authority"
        delta.append(
            {
                "delta_status": status,
                "left_source_event_id": row.get("left_source_event_id", ""),
                "right_source_event_id": row.get("right_source_event_id", ""),
                "ticker": row.get("ticker", ""),
                "source_families": row.get("source_families", ""),
                "authority_source_ref": row.get("authority_source_ref", ""),
                "authority_evidence_sha256": row.get("authority_evidence_sha256", ""),
                "reason": reason,
            }
        )
    return prior_rows, candidate_rows, delta


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
            source_row = source_by_id[source_id]
            transition = transition_by_id.get(source_id, {})
            if source_id in linked_mconv_ids:
                role = "PROVEN_SAME_EVENT_REPRESENTATION"
            elif text(transition.get("transition_status")) == "RESOLVED":
                role = "TRANSITION_BEARING_SOURCE_REPRESENTATION"
            else:
                role = "ECONOMIC_EVENT_SOURCE_REPRESENTATION"
            rows.append(
                {
                    "source_event_id": source_id,
                    "economic_event_id": event_id,
                    "source_kind": text(source_row.get("source_kind")),
                    "ticker": text(source_row.get("ticker")),
                    "source_native_label": text(source_row.get("source_native_label")),
                    "candidate_date": text(source_row.get("candidate_date")),
                    "ratio_raw": text(source_row.get("ratio_raw")),
                    "source_representation_role": role,
                    "economic_event_transition_status": text(event.get("transition_status")),
                    "economic_event_transition_date": text(event.get("transition_date")),
                    "economic_event_transition_semantics": text(event.get("transition_semantics")),
                    "transition_authority_source_ref": text(transition.get("authority_source_ref")),
                    "transition_authority_evidence_sha256": text(transition.get("authority_evidence_sha256")).lower(),
                }
            )
    return sorted(rows, key=lambda row: (row["economic_event_id"], row["source_event_id"]))


def load_document_sets() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    old_docs, old_parsed = compatible_document_inventory(PRIOR_ACQUISITION_ROOT)
    legacy_docs, legacy_parsed = compatible_document_inventory(LEGACY_ACQUISITION_ROOT)
    new_docs, new_parsed = discovery_document_inventory(NEW_ACQUISITION_ROOT)
    probe_docs, probe_parsed = base.probe_inventory(PROBE_ROOT)
    standalone = base.standalone_schedule_inventory(PROJECT_ROOT)
    source = base.source_rows(
        base.source_audit._load_raw_context(
            PROJECT_ROOT,
            base.source_audit._load_population(PROJECT_ROOT),
        )
    )
    old_target_docs, _ = base.target_document_map(source, [*old_parsed, *legacy_parsed], probe_parsed, PRIOR_ACQUISITION_ROOT)
    current_results = read_csv(NEW_ACQUISITION_ROOT / "target_event_results.csv")
    current_targets = {text(row.get("economic_event_id")): row for row in current_results if text(row.get("result_classification")) == "RESOLVED_EXACT"}
    current_docs: dict[str, dict[str, Any]] = {}
    for event_id, target in current_targets.items():
        refs = {item for item in text(target.get("discovered_document_refs")).split("|") if item}
        candidates = [doc for doc in new_parsed if text(doc.get("source_ref")) in refs]
        if not candidates:
            raise RuntimeError(f"resolved acquisition result has no parsed document: {event_id}")
        if len(candidates) != 1:
            raise RuntimeError(f"resolved acquisition result has ambiguous parsed documents: {event_id}")
        chosen = dict(candidates[0])
        chosen["target_event_id"] = event_id
        source_ids = [item for item in text(target.get("source_event_ids")).split("|") if item]
        if not source_ids:
            raise RuntimeError(f"resolved acquisition result has no source ids: {event_id}")
        for source_event_id in source_ids:
            current_docs[source_event_id] = chosen
    return [*old_docs, *legacy_docs, *new_docs], [*old_parsed, *legacy_parsed, *new_parsed], list(probe_docs), {**old_target_docs, **current_docs}


def manifest_for(root: Path, artifact_root: Path) -> dict[str, Any]:
    outputs: dict[str, Any] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.json":
            outputs[str(path.relative_to(root)).replace("\\", "/")] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    return {
        "manifest_version": f"{SCHEMA}_manifest",
        "artifact_root": str(artifact_root),
        "audit_date": AUDIT_DATE,
        "outcome_blind": True,
        "provider_calls": False,
        "output_hashes_excluding_manifest": outputs,
        "self_hash_policy": "MANIFEST.json excluded from its own hash",
    }


def future_plan(
    unresolved: Sequence[Mapping[str, Any]],
    target_results: Sequence[Mapping[str, Any]],
    source_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    def event_id_for(row: Mapping[str, Any]) -> str:
        return text(row.get("event_id") or row.get("economic_event_id"))

    def tickers_for(rows: Sequence[Mapping[str, Any]]) -> list[str]:
        tickers: set[str] = set()
        for row in rows:
            for source_event_id in text(row.get("source_event_ids")).split("|"):
                source_row = source_by_id.get(source_event_id)
                if source_row is not None and text(source_row.get("ticker")):
                    tickers.add(text(source_row.get("ticker")))
        return sorted(tickers)

    by_family: dict[str, list[str]] = {}
    for row in unresolved:
        by_family.setdefault(text(row.get("economic_family")), []).append(text(row.get("economic_event_id")))
    split_ids = sorted(by_family.get("STOCK_SPLIT", []) + by_family.get("REVERSE_SPLIT", []))
    source_unknown_families = ("CAPITAL_RESTRUCTURING", "BONUS_SHARES", "STOCK_DIVIDEND", "MERGER", "TRUE_SECURITY_CONVERSION")
    source_unknown_ids = sorted(event_id for family in source_unknown_families for event_id in by_family.get(family, []))
    units = [
        {"unit_id": "CAPABILITY-V11-KSEI-REPRESENTATIVE-3", "category": "CAPABILITY_VERIFICATION_CLOSED", "status": "CLOSED_PREVIOUSLY_EXECUTED_NO_RETRY", "event_ids": [], "tickers": ["AADI", "ADRO", "AALI"], "expected_request_count": 0},
        {"unit_id": "EVENT-SPLIT-TRANSITION-DOCUMENTS", "category": "OFFICIAL_DOCUMENT_FETCH_DETERMINISTIC", "status": "OPEN_RESIDUAL", "event_ids": split_ids, "tickers": tickers_for([row for row in unresolved if text(row.get("economic_family")) in {"STOCK_SPLIT", "REVERSE_SPLIT"}]), "expected_request_count": len(split_ids), "remaining_semantic": "accepted REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE"},
        {"unit_id": "EVENT-RIGHTS-KSEI-LOOKUP", "category": "OFFICIAL_INDEX_LOOKUP_REQUIRED", "status": "OPEN_RESIDUAL", "event_ids": sorted(by_family.get("RIGHTS_HMETD", [])), "tickers": tickers_for([row for row in unresolved if text(row.get("economic_family")) == "RIGHTS_HMETD"]), "expected_request_count": len(by_family.get("RIGHTS_HMETD", []))},
        {"unit_id": "EVENT-SOURCE-AUTHORITY-UNIDENTIFIED", "category": "AUTHORITATIVE_SOURCE_NOT_IDENTIFIED", "status": "OPEN_RESIDUAL", "event_ids": source_unknown_ids, "tickers": tickers_for([row for row in unresolved if text(row.get("economic_family")) in set(source_unknown_families)]), "expected_request_count": 0},
        {"unit_id": "EVENT-OPERATIONAL-TAXONOMY-RESEARCH", "category": "ECONOMIC_TAXONOMY_RESEARCH_REQUIRED", "status": "OPEN_RESIDUAL", "event_ids": sorted(by_family.get("UNRESOLVED_OPERATIONAL_LABEL", [])), "tickers": tickers_for([row for row in unresolved if text(row.get("economic_family")) == "UNRESOLVED_OPERATIONAL_LABEL"]), "expected_request_count": 0},
        {"unit_id": "EVENT-UNKNOWN-TAXONOMY-POLICY", "category": "POLICY_DECISION_REQUIRED", "status": "OPEN_RESIDUAL", "event_ids": sorted(by_family.get("UNKNOWN_TAXONOMY", [])), "tickers": tickers_for([row for row in unresolved if text(row.get("economic_family")) == "UNKNOWN_TAXONOMY"]), "expected_request_count": 0},
    ]
    all_ids = sorted(event_id for unit in units for event_id in unit["event_ids"])
    if all_ids != sorted(text(row.get("economic_event_id")) for row in unresolved) or len(all_ids) != len(set(all_ids)):
        raise RuntimeError("post-acquisition future plan does not partition unresolved events")
    resolved_wave = sorted(event_id_for(row) for row in target_results if text(row.get("result_classification")) == "RESOLVED_EXACT")
    return {"schema_version": "inc001_post_acquisition_future_plan_v2", "unresolved_event_count": len(unresolved), "resolved_in_current_wave_event_ids": resolved_wave, "capability_verification_is_closed": True, "units": units, "no_provider_needed_local_fix_event_ids": []}


def baseline_291_plan(target_results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    source_plan = json.loads(SOURCE_AUTHORITY_PLAN.read_text(encoding="utf-8"))
    bulk = [row for row in source_plan["requirements"] if text(row.get("request_type")) == "BULK_ACQUISITION_REQUIRED_AFTER_CAPABILITY_VERIFICATION"]
    capability = [row for row in source_plan["requirements"] if "CAPABILITY_VERIFICATION" in text(row.get("request_type"))]
    bulk_transition = next((row for row in bulk if text(row.get("unit_id")) == "ACQ-V11-004-BULK-TRANSITION-291"), None)
    if bulk_transition is None or int(source_plan.get("reconciliation", {}).get("minimum_event_specific_evidence_units", 0)) != 291:
        raise RuntimeError("controlling V1.1 acquisition plan is not the exact 291-event plan")
    event_ids = [text(row.get("event_id")) for row in bulk_transition.get("exact_event_ids", []) if text(row.get("event_id"))]
    if len(event_ids) != 291 or len(set(event_ids)) != 291:
        raise RuntimeError("controlling V1.1 acquisition plan does not conserve 291 unique event identities")
    current_resolved = sorted(
        text(row.get("economic_event_id"))
        for row in target_results
        if text(row.get("result_classification")) == "RESOLVED_EXACT"
    )
    return {
        "schema_version": "inc001_future_acquisition_plan_v11_291_successor",
        "status": "PLAN_ONLY_NO_BULK_ACQUISITION_AUTHORIZED",
        "controlling_source_authority_root": str(SOURCE_AUTHORITY_ROOT),
        "controlling_source_authority_manifest_sha256": SOURCE_MANIFEST_SHA256,
        "baseline_unresolved_physical_event_count": 291,
        "baseline_unresolved_event_id_set_sha256": text(source_plan.get("reconciliation", {}).get("raw_unresolved_event_id_set_sha256")),
        "capability_verification_requests": capability,
        "later_bulk_acquisition_requests": bulk,
        "current_wave": {
            "bounded_target_event_count": len(target_results),
            "current_wave_resolved_exact_event_ids": current_resolved,
            "current_wave_is_not_bulk_291": True,
            "current_wave_provider_calls": True,
        },
        "source_authority_plan": source_plan,
        "guardrails": {
            "future_bulk_executed": False,
            "capability_verification_reopened": False,
            "phase_e": False,
            "outcomes_or_targets": False,
            "fit_refit_score": False,
            "counter_mutation": False,
            "canonical_historical_rewrite": False,
        },
    }


def build(output_root: Path) -> dict[str, Any]:
    if output_root.exists() or output_root.with_name(output_root.name + ".staging").exists():
        raise FileExistsError(f"immutable output root already exists: {output_root}")
    staging = output_root.with_name(output_root.name + ".staging")
    staging.mkdir(parents=True)
    try:
        if sha256_file(PRIOR_RECONCILIATION_ROOT / "MANIFEST.json") != PRIOR_RECONCILIATION_MANIFEST_SHA256:
            raise RuntimeError("controlling V7 reconciliation manifest hash mismatch")
        if sha256_file(LEGACY_ACQUISITION_ROOT / "MANIFEST.json") != LEGACY_ACQUISITION_MANIFEST_SHA256:
            raise RuntimeError("legacy acquisition manifest hash mismatch")
        source_population = base.source_audit._load_population(PROJECT_ROOT)
        context = base.source_audit._load_raw_context(PROJECT_ROOT, source_population)
        source = base.source_rows(context)
        if len(source) != 412:
            raise RuntimeError(f"source row count diverges: {len(source)}")
        all_docs, _parsed_docs, probe_all, target_docs = load_document_sets()
        _discovery_docs, new_parsed = discovery_document_inventory(NEW_ACQUISITION_ROOT)
        probe_docs = [doc for doc in probe_all if text(doc.get("parser_status")) == "PARSED_PROBE_DOCUMENT"]
        standalone = base.standalone_schedule_inventory(PROJECT_ROOT)
        adjudications = base.build_adjudications(source, target_docs)
        prior_linkages = read_csv(PRIOR_RECONCILIATION_ROOT / "proven_same_event_linkage_ledger.csv")
        prior_linkages, candidate_linkages, linkage_delta = audit_linkage_delta(
            source,
            prior_linkages,
            base.build_linkages(source, target_docs, probe_docs),
            new_parsed,
        )
        linkages = candidate_linkages
        prior_linkage_keys = {linkage_key(row) for row in prior_linkages}
        new_linkages = [row for row in linkages if linkage_key(row) not in prior_linkage_keys]
        transitions = base.build_transitions(source, context, target_docs, PROBE_ROOT, standalone)
        core_adjudications = [{key: row[key] for key in ("source_event_id", "adjudication_status", "economic_family", "basis_effect", "authority_source_ref", "authority_evidence_sha256")} for row in adjudications]
        core_linkages = [{key: row[key] for key in ("left_source_event_id", "right_source_event_id", "relation", "authority_source_ref", "authority_evidence_sha256")} for row in linkages]
        core_transitions = [{key: row[key] for key in ("source_event_id", "transition_status", "transition_semantic", "transition_date", "authority_source_ref", "authority_evidence_sha256")} for row in transitions]
        result = base.econ.reconcile_economic_events(source, adjudications=core_adjudications, linkages=core_linkages, transition_attestations=core_transitions)
        source_by_id = {row["source_event_id"]: row for row in source}
        economic_rows = base.economic_csv_rows(result)
        unresolved = [row for row in economic_rows if row["transition_status"] == "UNRESOLVED"]
        non_basis = [row for row in economic_rows if row["transition_status"] == "NOT_APPLICABLE_NON_BASIS"]
        actual = {key: result[key] for key in ("source_evidence_rows", "cross_source_collapses", "same_source_collapses", "economic_event_count", "resolved_transitions", "unresolved_transitions", "non_basis_excluded")}
        prior = {"source_evidence_rows": 412, "cross_source_collapses": 20, "same_source_collapses": 3, "economic_event_count": 389, "resolved_transitions": 159, "unresolved_transitions": 184, "non_basis_excluded": 46}
        comparison = {key: {"prior": prior[key], "actual": actual[key], "delta": actual[key] - prior[key]} for key in prior}
        doc_rows = base.source_evidence_documents([*all_docs, *probe_docs], standalone)
        hash_failures = [row for row in doc_rows if text(row.get("hash_matches_bytes")) != "true"]
        if hash_failures:
            raise RuntimeError(f"retained document hash failures: {len(hash_failures)}")
        family_distribution = Counter(event["economic_family"] for event in result["economic_events"])
        unresolved_by_source = Counter(source_by_id[member]["source_kind"] for event in result["economic_events"] if event["transition_status"] == "UNRESOLVED" for member in event["source_event_ids"])
        target_results = read_csv(NEW_ACQUISITION_ROOT / "target_event_results.csv")
        post_acquisition_plan = future_plan(unresolved, target_results, source_by_id)
        baseline_plan = baseline_291_plan(target_results)
        transition_target_ids = {
            source_event_id
            for row in target_results
            if text(row.get("result_classification")) == "RESOLVED_EXACT"
            for source_event_id in text(row.get("source_event_ids")).split("|")
            if source_event_id
        }
        resolved_target_transitions = [row for row in transitions if text(row.get("source_event_id")) in transition_target_ids and text(row.get("transition_status")) == "RESOLVED"]
        index_ledger = json.loads((PRIOR_ACQUISITION_ROOT / "provider" / "index_request_ledger.json").read_text(encoding="utf-8"))
        mapping = source_mapping(source, economic_rows, transitions, linkages)
        validation = {
            "source_evidence_rows": len(source),
            "baseline_291_plan_conserved": baseline_plan["baseline_unresolved_physical_event_count"] == 291 and len(baseline_plan["later_bulk_acquisition_requests"]) > 0,
            "source_representation_mapping_conserved": len(mapping) == len(source),
            "recomputed_linkages_source_bound": all(text(row.get("authority_source_ref")) and base.valid_sha(row.get("authority_evidence_sha256")) for row in candidate_linkages),
            "new_linkages_source_bound_to_v5": len(new_linkages) == 2 and all((text(row.get("authority_source_ref")), text(row.get("authority_evidence_sha256")).lower()) in {(text(doc.get("source_ref")), text(doc.get("evidence_sha256")).lower()) for doc in new_parsed} for row in new_linkages),
            "no_removed_or_conflicting_linkages": not any(row["delta_status"] == "REMOVED_OR_CONFLICTING_LINKAGE" for row in linkage_delta),
            "retained_document_rows_verified": len(doc_rows),
            "retained_document_hash_failures": len(hash_failures),
            "new_wave_target_rows": len(target_results),
            "new_wave_resolved_exact_targets": len(resolved_target_transitions),
            "new_wave_bbrm_semantic_insufficient": 0,
            "request_ledger_reused_continuous_1_to_n": [int(row["request_number"]) for row in index_ledger] == list(range(1, len(index_ledger) + 1)),
            "collapse_arithmetic": len(source) - result["cross_source_collapses"] - result["same_source_collapses"] == result["economic_event_count"],
            "transition_arithmetic": result["resolved_transitions"] + result["unresolved_transitions"] + result["non_basis_excluded"] == result["economic_event_count"],
            "all_resolved_transitions_have_ref_sha": all(text(row.get("authority_source_ref")) and base.valid_sha(row.get("authority_evidence_sha256")) for row in transitions if text(row.get("transition_status")) == "RESOLVED"),
            "bbrm_remains_unresolved": any("818109854b172c11e4ce4134dc4ca181780a5fde58ba60df4b4c5f7b653c1a46" in text(row.get("source_event_ids")) and text(row.get("economic_family")) == "REVERSE_SPLIT" and text(row.get("transition_status")) == "UNRESOLVED" for row in unresolved),
        }
        summary = {
            "schema_version": SCHEMA,
            "audit_date": AUDIT_DATE,
            "status": "LOCAL_POST_ACQUISITION_RECONCILIATION_COMPLETE_NO_SCIENTIFIC_ADMISSION",
            "controlling_predecessor_manifest_sha256": PRIOR_RECONCILIATION_MANIFEST_SHA256,
            "controlling_predecessor_root": str(PRIOR_RECONCILIATION_ROOT),
            "controlling_v4_manifest_sha256": V4_MANIFEST_SHA256,
            "source_authority_manifest_sha256": SOURCE_MANIFEST_SHA256,
            "acquisition": {"new_root": str(NEW_ACQUISITION_ROOT), "new_manifest_sha256": sha256_file(NEW_ACQUISITION_ROOT / "MANIFEST.json"), "prior_root_reused": str(PRIOR_ACQUISITION_ROOT), "legacy_wave_root_reused": str(LEGACY_ACQUISITION_ROOT), "legacy_wave_manifest_sha256": LEGACY_ACQUISITION_MANIFEST_SHA256, "provider_calls_in_reconciliation": False},
            "counts": actual,
            "physical_event_census_policy": "NEW_OFFICIAL_EVIDENCE_MAY_COLLAPSE_SOURCE_REPRESENTATIONS_WHEN_PROVEN; no heuristic linkage",
            "before_after_comparison": comparison,
            "linkage_audit": {"prior_proven_linkages": len(prior_linkages), "recomputed_proven_linkages": len(candidate_linkages), "new_proven_linkages": len(new_linkages), "removed_or_conflicting_linkages": sum(row["delta_status"] == "REMOVED_OR_CONFLICTING_LINKAGE" for row in linkage_delta)},
            "new_wave": {"target_count": len(target_results), "resolved_exact_targets": sum(text(row.get("result_classification")) == "RESOLVED_EXACT" for row in target_results), "bbrm_result": "RETAINED_FROM_PREDECESSOR_UNCHANGED", "new_transition_evidence_count": len(resolved_target_transitions)},
            "post_acquisition_future_plan": {"unresolved_event_count": post_acquisition_plan["unresolved_event_count"], "split_residual_count": len(next(unit["event_ids"] for unit in post_acquisition_plan["units"] if unit["unit_id"] == "EVENT-SPLIT-TRANSITION-DOCUMENTS")), "capability_unit_status": "CLOSED_PREVIOUSLY_EXECUTED_NO_RETRY"},
            "baseline_291_future_plan": {"unresolved_physical_event_count": baseline_plan["baseline_unresolved_physical_event_count"], "capability_verification_request_count": len(baseline_plan["capability_verification_requests"]), "later_bulk_acquisition_request_count": len(baseline_plan["later_bulk_acquisition_requests"])},
            "family_distribution": dict(sorted(family_distribution.items())),
            "unresolved_by_source": dict(sorted(unresolved_by_source.items())),
            "residual_geometry": base.gap_rows(result, source_by_id),
            "validation": validation,
            "scientific_verdict_unchanged": {"DATA_ADMISSION": "FAIL", "RESEARCH_ADMISSION": "FAIL", "MODEL_PROMOTION": "NOT_EVALUATED", "HISTORICAL_APPLICATION": "BLOCKED_PHASE_E_NOT_RUN", "REFIT_AUTHORIZED": False, "COUNTER_ACTION": "NONE"},
            "authority_blockers_unchanged": {"IDX_HISTORICAL_NEGATIVE_AUTHORITY": "UNSUPPORTED", "IDX_HISTORICAL_ASOF_AUTHORITY": "UNKNOWN", "KSEI_HISTORICAL_COMPLETE_INTERVAL_AUTHORITY": "UNKNOWN"},
            "guardrails": {"phase_e": False, "outcomes_or_targets": False, "fit_refit_score": False, "counter_mutation": False, "canonical_historical_rewrite": False, "production_execution": False, "merge": False},
        }
        write_json(staging / "reconciliation_summary.json", summary)
        write_json(staging / "validation_report.json", validation)
        write_csv(staging / "source_evidence_ledger.csv", source, base.SOURCE_FIELDS)
        write_csv(staging / "retained_document_evidence.csv", doc_rows, base.DOC_FIELDS + ["evidence_role"])
        write_csv(staging / "economic_adjudication_ledger.csv", adjudications, base.ADJ_FIELDS)
        write_csv(staging / "proven_same_event_linkage_ledger.csv", linkages, base.LINK_FIELDS)
        write_csv(staging / "prior_proven_same_event_linkage_ledger.csv", prior_linkages, LINKAGE_FIELDS)
        write_csv(staging / "recomputed_candidate_linkage_ledger.csv", candidate_linkages, LINKAGE_FIELDS)
        write_csv(staging / "independently_accepted_linkage_ledger.csv", linkages, LINKAGE_FIELDS)
        write_csv(staging / "linkage_delta_report.csv", linkage_delta, LINKAGE_DELTA_FIELDS)
        write_csv(staging / "transition_attestation_ledger.csv", transitions, base.TRANSITION_FIELDS)
        write_csv(staging / "economic_event_ledger.csv", economic_rows, ["economic_event_id", "source_event_ids", "source_kinds", "economic_family", "basis_effect", "classification_conflict", "transition_status", "transition_date", "transition_semantics"])
        write_csv(staging / "source_to_economic_mapping.csv", mapping, list(mapping[0].keys()))
        write_csv(staging / "unresolved_economic_event_ledger.csv", unresolved, ["economic_event_id", "source_event_ids", "source_kinds", "economic_family", "basis_effect", "classification_conflict", "transition_status", "transition_date", "transition_semantics"])
        write_csv(staging / "non_basis_exclusion_ledger.csv", non_basis, ["economic_event_id", "source_event_ids", "source_kinds", "economic_family", "basis_effect", "classification_conflict", "transition_status", "transition_date", "transition_semantics"])
        write_csv(staging / "remaining_gap_geometry.csv", base.gap_rows(result, source_by_id), ["economic_family", "economic_event_count", "ticker_count", "tickers", "economic_event_ids", "source_kinds", "missing_semantic"])
        write_csv(staging / "target_event_results.csv", target_results, list(target_results[0].keys()))
        write_json(staging / "future_acquisition_plan_v2.json", post_acquisition_plan)
        write_json(staging / "future_acquisition_plan_v11_291.json", baseline_plan)
        write_json(staging / "deterministic_input_pins.json", {"source_authority_root": str(SOURCE_AUTHORITY_ROOT), "source_authority_manifest_sha256": SOURCE_MANIFEST_SHA256, "prior_reconciliation_root": str(PRIOR_RECONCILIATION_ROOT), "prior_reconciliation_manifest_sha256": PRIOR_RECONCILIATION_MANIFEST_SHA256, "v4_decomposition_root": str(PROJECT_ROOT / "idx-ca-unresolved-economic-gap-decomposition-20260829-v4"), "v4_decomposition_manifest_sha256": V4_MANIFEST_SHA256, "prior_acquisition_root": str(PRIOR_ACQUISITION_ROOT), "legacy_acquisition_root": str(LEGACY_ACQUISITION_ROOT), "legacy_acquisition_manifest_sha256": LEGACY_ACQUISITION_MANIFEST_SHA256, "new_acquisition_root": str(NEW_ACQUISITION_ROOT), "new_acquisition_manifest_sha256": sha256_file(NEW_ACQUISITION_ROOT / "MANIFEST.json"), "probe_root": str(PROBE_ROOT), "repo_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()})
        write_json(staging / "MANIFEST.json", manifest_for(staging, output_root))
        staging.rename(output_root)
        return summary
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.output_root), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
