"""Build the bounded INC-001 Mixed Dividend policy successor artifact.

This script consumes the retained V15 ledgers and the previously retained,
hash-matched KSEI evidence for exactly four composite cash+share rows.  It is
local-only: no provider calls, outcome access, canonical-data rewrite, or
production mutation is permitted.
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
from typing import Any, Iterable, Mapping


V15_MANIFEST_SHA256 = "d5a4a21beb2f065502fef3899b3a4f4f7204e0fbbed6f05ae7f4a0119fed6025"
PREVIOUS_COMPOSITE_MANIFEST_SHA256 = "ee7ac86764f7edda8a5886e5697b128085b32eaf1b487a9d5eac1132413a88ca"
EXPECTED_REPO_HEAD = "c6972f2a3b75a7d7884c958baeaddb247c1eac96"
AUDIT_DATE = "2026-08-31"
COMPOSITE_FAMILY = "COMPOSITE_CASH_SHARE_DISTRIBUTION"
BASIS_CONTRACT_FAMILY = "STOCK_DIVIDEND"

TARGETS: tuple[dict[str, str], ...] = (
    {
        "economic_event_id": "DERIVED-4e2db5111bc0b70d5bd6b9e77cda6703dea8ff60d18a033787e75e04999e4d60",
        "source_event_id": "aad3d51ec0e1cbbfc4637b47a64fd5a9ac98c2ec6ea61b387998b44e66be8cc4",
        "ticker": "CNMA",
        "source_ref": "https://web.ksei.co.id/services/registered-securities/shares/lc/CNMA?setLocale=en-US",
        "raw_capture_path": "D:\\Documents\\Project\\idx-v4-ksei-ca-history-census-20260817-v1\\raw\\CNMA\\attempt_01.html",
        "evidence_sha256": "e7656e6126b5be6091a805621de843b7f8bd2e72f500ecea5dac98ca86efc5d9",
        "cash_ratio": "(50 CNMA : 7 IDR)",
        "share_ratio": "(50 CNMA : 1 CNMA )",
        "cash_units": "7",
        "share_units": "1",
        "paired_stock_source_event_id": "3ac75071cfbca806f0e133579111cfefcfe30c4d76a86fb8c334d74a550ec196",
    },
    {
        "economic_event_id": "DERIVED-893338349f1dc1ac85f83e9a5476f2a5967f5c28b0c4bdf26a20c28ae0264c92",
        "source_event_id": "389ab4a10c6df68b58979afdf86ee369174c6637a2418a22a8bfaa926de04d26",
        "ticker": "KKGI",
        "source_ref": "https://web.ksei.co.id/services/registered-securities/shares/lc/KKGI?setLocale=en-US",
        "raw_capture_path": "D:\\Documents\\Project\\idx-v4-ksei-ca-history-census-20260817-v1\\raw\\KKGI\\attempt_01.html",
        "evidence_sha256": "c674ef6469147656a057c09a617e5d95c9ea8e6761e4c75c4638f4d26ab55e78",
        "cash_ratio": "(10000 KKGI : 15 IDR)",
        "share_ratio": "(10000 KKGI : 53 KKGI )",
        "cash_units": "15",
        "share_units": "53",
        "paired_stock_source_event_id": "474512eee014cece469973a6ce29fa2e90a53557be3d0ae807e7bd36722d1960",
    },
    {
        "economic_event_id": "DERIVED-7d3d4fb644bfac02abc1ff6f2aac5cb20c895eb1e0a571d42291759ea62a1ea8",
        "source_event_id": "0b4dd5c52fcf6dc2f12710099bb77a5d16c842f1a51ac584a9929532ecac5732",
        "ticker": "WINS",
        "source_ref": "https://web.ksei.co.id/services/registered-securities/shares/lc/WINS?setLocale=en-US",
        "raw_capture_path": "D:\\Documents\\Project\\idx-v4-ksei-ca-history-census-20260817-v1\\raw\\WINS\\attempt_01.html",
        "evidence_sha256": "d2269bfed3d9f14ba06160641904a75d4753db706a8946793359fbcc5302280f",
        "cash_ratio": "(46 WINS : 2 IDR)",
        "share_ratio": "(46 WINS : 1 WINS )",
        "cash_units": "2",
        "share_units": "1",
        "paired_stock_source_event_id": "278e2ec1e086b7153b700b0d88e8c3d0fc83a1bb8f9c63a2e7fa3fd32d347ebd",
    },
    {
        "economic_event_id": "DERIVED-ff06b7cd6b57d1c4d7a0b5b21a8d6e44bd0b493fc5e18aebc3960b26f3b6022f",
        "source_event_id": "6f449d4210b1ae38dcfdd8e1084165729cd7d07fb7dc74640a698673de0ef49a",
        "ticker": "WINS",
        "source_ref": "https://web.ksei.co.id/services/registered-securities/shares/lc/WINS?setLocale=en-US",
        "raw_capture_path": "D:\\Documents\\Project\\idx-v4-ksei-ca-history-census-20260817-v1\\raw\\WINS\\attempt_01.html",
        "evidence_sha256": "d2269bfed3d9f14ba06160641904a75d4753db706a8946793359fbcc5302280f",
        "cash_ratio": "(71 WINS : 2 IDR)",
        "share_ratio": "(71 WINS : 1 WINS )",
        "cash_units": "2",
        "share_units": "1",
        "paired_stock_source_event_id": "273d8d75c833a6bed57313b1d8eafd4bc2e3c73f33c738c798436419f6067870",
    },
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: "" if row.get(field) is None else row.get(field, "") for field in fields})


def git_head(repo_root: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"], text=True
    ).strip()


def event_row(event: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(event)
    row["source_event_ids"] = "|".join(event["source_event_ids"])
    row["source_kinds"] = "|".join(event["source_kinds"])
    row["transition_semantics"] = "|".join(event["transition_semantics"])
    return row


def canonical_result(result: Mapping[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = args.repo_root.resolve()
    input_root = args.input_root.resolve()
    prior_root = args.prior_root.resolve()
    output_root = args.output_root.resolve()
    manifest_path = input_root / "MANIFEST.json"
    if sha256_file(manifest_path) != V15_MANIFEST_SHA256:
        raise RuntimeError("controlling V15 manifest hash mismatch")
    prior_manifest_path = prior_root / "MANIFEST.json"
    if sha256_file(prior_manifest_path) != PREVIOUS_COMPOSITE_MANIFEST_SHA256:
        raise RuntimeError("prior composite artifact manifest hash mismatch")
    actual_head = git_head(repo_root)
    expected_head = args.expected_repo_head or EXPECTED_REPO_HEAD
    if actual_head != expected_head:
        raise RuntimeError(f"unexpected repository HEAD: {actual_head}; expected {expected_head}")
    if output_root.exists():
        raise FileExistsError(f"immutable output root already exists: {output_root}")
    staging = output_root.with_name(output_root.name + ".staging")
    if staging.exists():
        raise FileExistsError(f"staging output root already exists: {staging}")
    staging.mkdir(parents=True)

    try:
        source = read_csv(input_root / "source_evidence_ledger.csv")
        baseline_events = read_csv(input_root / "economic_event_ledger.csv")
        adjudications = read_csv(input_root / "economic_adjudication_ledger.csv")
        linkages = read_csv(input_root / "proven_same_event_linkage_ledger.csv")
        transitions = read_csv(input_root / "transition_attestation_ledger.csv")
        source_by_id = {row["source_event_id"]: row for row in source}
        if len(source_by_id) != len(source) or len(source) != 412:
            raise RuntimeError("V15 source ledger is not the expected unique 412-row population")
        source_hash_failures = []
        for row in source:
            raw_path = Path(row.get("raw_capture_path", ""))
            if (
                not raw_path.is_file()
                or sha256_file(raw_path) != row.get("evidence_sha256", "").lower()
                or row.get("source_hash_matches_bytes", "").lower() != "true"
            ):
                source_hash_failures.append(row.get("source_event_id", ""))
        if source_hash_failures:
            raise RuntimeError(f"V15 source evidence hash failures: {len(source_hash_failures)}")

        target_by_source = {target["source_event_id"]: target for target in TARGETS}
        if set(target_by_source) - set(source_by_id):
            raise RuntimeError("composite target is absent from controlling source ledger")
        if any(target["source_event_id"] in {row["source_event_id"] for row in adjudications} for target in TARGETS):
            raise RuntimeError("composite target already has a V15 adjudication")

        for target in TARGETS:
            raw_path = Path(target["raw_capture_path"])
            if not raw_path.is_file() or sha256_file(raw_path) != target["evidence_sha256"]:
                raise RuntimeError(f"retained composite evidence hash mismatch: {raw_path}")
            source_row = source_by_id[target["source_event_id"]]
            if source_row["ticker"] != target["ticker"] or source_row["source_ref"] != target["source_ref"]:
                raise RuntimeError(f"composite source identity mismatch: {target['source_event_id']}")
            if source_row["source_native_label"] != "Mixed Dividend":
                raise RuntimeError(f"composite source label mismatch: {target['source_event_id']}")
            if source_row["ratio_raw"] != target["cash_ratio"]:
                raise RuntimeError(f"composite cash ratio mismatch: {target['source_event_id']}")
            paired = source_by_id.get(target["paired_stock_source_event_id"])
            if paired is None:
                raise RuntimeError(f"paired share source is absent: {target['source_event_id']}")
            if (
                paired["ticker"] != target["ticker"]
                or paired["source_ref"] != target["source_ref"]
                or paired["source_native_label"] != "Mixed Dividend"
                or paired["ratio_raw"] != target["share_ratio"]
                or paired["candidate_date"] != source_row["candidate_date"]
                or paired["cum_date"] != source_row["cum_date"]
                or paired["record_date"] != source_row["record_date"]
                or paired["distribution_date"] != source_row["distribution_date"]
                or paired["status"] != source_row["status"]
            ):
                raise RuntimeError(f"paired share evidence is not same-date and active: {target['source_event_id']}")
            if (
                source_row["ratio_right_security"] != "IDR"
                or int(source_row["ratio_right_value"]) <= 0
                or source_row["ratio_right_value"] != target["cash_units"]
                or paired["ratio_right_security"] != target["ticker"]
                or int(paired["ratio_right_value"]) <= 0
                or paired["ratio_right_value"] != target["share_units"]
            ):
                raise RuntimeError(f"composite positive cash/share legs are not proven: {target['source_event_id']}")

        added_adjudications = [
            {
                **target,
                "adjudication_status": "PROVEN",
                "economic_family": COMPOSITE_FAMILY,
                "basis_effect": "BASIS_CHANGING",
                "authority_source_ref": target["source_ref"],
                "authority_evidence_sha256": target["evidence_sha256"],
                "source_native_label": "Mixed Dividend",
                "candidate_date": source_by_id[target["source_event_id"]]["candidate_date"],
                "ratio_raw": source_by_id[target["source_event_id"]]["ratio_raw"],
                "adjudication_reason": (
                    "retained KSEI evidence proves same-date active cash and positive share legs; "
                    "share leg is basis-changing while exact regular-market transition remains unresolved"
                ),
            }
            for target in TARGETS
        ]
        all_adjudications = [*adjudications, *added_adjudications]
        core_adjudications = [
            {
                key: row[key]
                for key in (
                    "source_event_id",
                    "adjudication_status",
                    "economic_family",
                    "basis_effect",
                    "authority_source_ref",
                    "authority_evidence_sha256",
                )
            }
            for row in all_adjudications
        ]
        core_linkages = [
            {
                key: row[key]
                for key in (
                    "left_source_event_id",
                    "right_source_event_id",
                    "relation",
                    "authority_source_ref",
                    "authority_evidence_sha256",
                )
            }
            for row in linkages
        ]
        core_transitions = [
            {
                key: row[key]
                for key in (
                    "source_event_id",
                    "transition_status",
                    "transition_semantic",
                    "transition_date",
                    "authority_source_ref",
                    "authority_evidence_sha256",
                )
            }
            for row in transitions
        ]
        sys.path.insert(0, str(repo_root / "src"))
        from idx_trade import ca_economic_event_reconciliation_v1 as econ

        result = econ.reconcile_economic_events(
            source,
            adjudications=core_adjudications,
            linkages=core_linkages,
            transition_attestations=core_transitions,
        )
        replay = econ.reconcile_economic_events(
            source,
            adjudications=core_adjudications,
            linkages=core_linkages,
            transition_attestations=core_transitions,
        )
        result_bytes = canonical_result(result)
        replay_bytes = canonical_result(replay)
        if result_bytes != replay_bytes:
            raise RuntimeError("deterministic frozen replay diverged")

        expected_counts = {
            "source_evidence_rows": 412,
            "cross_source_collapses": 22,
            "same_source_collapses": 3,
            "economic_event_count": 387,
            "resolved_transitions": 163,
            "unresolved_transitions": 178,
            "non_basis_excluded": 46,
        }
        actual_counts = {key: result[key] for key in expected_counts}
        if actual_counts != expected_counts:
            raise RuntimeError(f"successor counts diverge: {actual_counts}")
        events = result["economic_events"]
        events_by_source = {
            member: event for event in events for member in event["source_event_ids"]
        }
        for target in TARGETS:
            event = events_by_source[target["source_event_id"]]
            if (
                event["economic_event_id"] != target["economic_event_id"]
                or event["economic_family"] != COMPOSITE_FAMILY
                or event["basis_effect"] != "BASIS_CHANGING"
                or event["transition_status"] != "UNRESOLVED"
            ):
                raise RuntimeError(f"composite successor state mismatch: {target['source_event_id']}")

        old_family_counts = Counter(row["economic_family"] for row in baseline_events)
        new_family_counts = Counter(event["economic_family"] for event in events)
        if old_family_counts["UNKNOWN_TAXONOMY"] != 4 or new_family_counts["UNKNOWN_TAXONOMY"] != 0:
            raise RuntimeError("UNKNOWN_TAXONOMY composite delta is not exactly 4 -> 0")
        if old_family_counts[COMPOSITE_FAMILY] != 0 or new_family_counts[COMPOSITE_FAMILY] != 4:
            raise RuntimeError("composite family delta is not exactly 0 -> 4")
        changed_families = (set(old_family_counts) | set(new_family_counts)) - {
            "UNKNOWN_TAXONOMY",
            COMPOSITE_FAMILY,
        }
        for family in sorted(changed_families):
            if old_family_counts[family] != new_family_counts[family]:
                raise RuntimeError(f"unrelated family changed: {family}")

        baseline_pairs = sorted(
            (row["left_source_event_id"], row["right_source_event_id"])
            for row in linkages
            if row.get("relation", "").upper() == "PROVEN_SAME_ECONOMIC_EVENT"
        )
        successor_pairs = sorted(
            (row["left_source_event_id"], row["right_source_event_id"])
            for row in result["proven_linkages"]
        )
        if baseline_pairs != successor_pairs:
            raise RuntimeError("proven linkage set changed during composite policy")

        event_rows = [event_row(event) for event in events]
        unresolved_rows = [row for row in event_rows if row["transition_status"] == "UNRESOLVED"]
        non_basis_rows = [row for row in event_rows if row["transition_status"] == "NOT_APPLICABLE_NON_BASIS"]
        source_mapping = [
            {
                "economic_event_id": event["economic_event_id"],
                "economic_family": event["economic_family"],
                "source_event_id": member,
                "ticker": source_by_id[member]["ticker"],
                "transition_status": event["transition_status"],
                "transition_date": event["transition_date"],
                "transition_semantics": "|".join(event["transition_semantics"]),
            }
            for event in events
            for member in event["source_event_ids"]
        ]
        component_rows = [
            {
                "economic_event_id": target["economic_event_id"],
                "source_event_id": target["source_event_id"],
                "ticker": target["ticker"],
                "source_native_label": "Mixed Dividend",
                "cash_component": "CASH_DIVIDEND",
                "cash_ratio": target["cash_ratio"],
                "share_component": "STOCK_DIVIDEND",
                "share_ratio": target["share_ratio"],
                "paired_stock_source_event_id": target["paired_stock_source_event_id"],
                "basis_effect": "BASIS_CHANGING",
                "basis_contract_family": BASIS_CONTRACT_FAMILY,
                "transition_status": "UNRESOLVED",
                "source_ref": target["source_ref"],
                "raw_capture_path": target["raw_capture_path"],
                "evidence_sha256": target["evidence_sha256"],
                "same_dates_and_active_status": "True",
                "positive_share_leg_proven": "True",
                "cash_leg_neutralizes_share_basis": "False",
                "label_alone_sufficient": "False",
            }
            for target in TARGETS
        ]
        family_gap_rows = [
            {
                "economic_family": family,
                "economic_event_count": count,
                "ticker_count": len({source_by_id[member]["ticker"] for event in events if event["economic_family"] == family for member in event["source_event_ids"]}),
                "tickers": "|".join(sorted({source_by_id[member]["ticker"] for event in events if event["economic_family"] == family for member in event["source_event_ids"]})),
                "economic_event_ids": "|".join(sorted(event["economic_event_id"] for event in events if event["economic_family"] == family)),
                "source_kinds": "|".join(sorted({kind for event in events if event["economic_family"] == family for kind in event["source_kinds"]})),
                "missing_semantic": "exact regular-market transition session remains unresolved" if family == COMPOSITE_FAMILY else "",
            }
            for family, count in sorted(new_family_counts.items())
        ]
        summary = {
            "schema_version": "inc001_ca_composite_policy_reconciliation_v1",
            "audit_date": AUDIT_DATE,
            "status": "LOCAL_PHASE_A_COMPOSITE_POLICY_RECONCILIATION_COMPLETE_NO_SCIENTIFIC_ADMISSION",
            "controlling_predecessor": {
                "root": str(input_root),
                "manifest_sha256": V15_MANIFEST_SHA256,
                "economic_event_count": 387,
            },
            "previous_composite_policy_artifact": {
                "root": str(prior_root),
                "manifest_sha256": PREVIOUS_COMPOSITE_MANIFEST_SHA256,
            },
            "repository": {"head": actual_head, "script": "scripts/build_inc001_composite_policy_reconciliation_v1.py"},
            "policy": {
                "source_native_label": "Mixed Dividend",
                "economic_family": COMPOSITE_FAMILY,
                "basis_effect": "BASIS_CHANGING",
                "basis_contract_family": BASIS_CONTRACT_FAMILY,
                "cash_leg_is_retained": True,
                "positive_share_leg_is_required": True,
                "exact_transition_required": True,
                "unresolved_transition_state": "UNRESOLVED",
                "label_alone_is_insufficient": True,
            },
            "counts": actual_counts,
            "classification_delta": {
                "UNKNOWN_TAXONOMY": {"before": 4, "after": 0},
                COMPOSITE_FAMILY: {"before": 0, "after": 4},
                "all_other_families_unchanged": True,
            },
            "target_events": component_rows,
            "source_to_economic_mapping_recomputed": True,
            "proven_linkages_recomputed_from_scratch": True,
            "proven_linkage_count": len(successor_pairs),
            "scientific_verdict": {
                "DATA_ADMISSION": "FAIL",
                "RESEARCH_ADMISSION": "FAIL",
                "MODEL_PROMOTION": "NOT_EVALUATED",
                "HISTORICAL_APPLICATION": "BLOCKED_PHASE_E_NOT_RUN",
                "REFIT_AUTHORIZED": False,
                "COUNTER_ACTION": "NONE",
            },
            "guardrails": {
                "provider_calls": False,
                "outcomes_or_targets": False,
                "fit_refit_score": False,
                "canonical_historical_rewrite": False,
                "production_execution": False,
                "merge": False,
            },
        }
        validation = {
            "controlling_v15_manifest_verified": True,
            "prior_composite_manifest_verified": True,
            "source_rows_preserved": len(source) == 412,
            "target_count": len(component_rows),
            "target_raw_bytes_hash_matched": True,
            "target_identity_and_dates_verified": True,
            "composite_basis_changing": all(row["basis_effect"] == "BASIS_CHANGING" for row in component_rows),
            "transition_remains_unresolved": all(row["transition_status"] == "UNRESOLVED" for row in component_rows),
            "cash_and_share_components_retained": all(row["cash_component"] and row["share_component"] for row in component_rows),
            "no_new_linkages": baseline_pairs == successor_pairs,
            "classification_conservation": sum(new_family_counts.values()) == len(events),
            "collapse_arithmetic": result["source_evidence_rows"] - result["cross_source_collapses"] - result["same_source_collapses"] == result["economic_event_count"],
            "transition_arithmetic": result["resolved_transitions"] + result["unresolved_transitions"] + result["non_basis_excluded"] == result["economic_event_count"],
            "deterministic_frozen_replay": True,
            "no_scientific_admission": True,
        }

        event_fields = [
            "economic_event_id", "source_event_ids", "source_kinds", "economic_family", "basis_effect",
            "classification_conflict", "transition_status", "transition_date", "transition_semantics",
        ]
        write_csv(staging / "source_evidence_ledger.csv", source, list(source[0]))
        write_csv(staging / "economic_adjudication_ledger.csv", all_adjudications, list(adjudications[0]))
        write_csv(staging / "proven_same_event_linkage_ledger.csv", linkages, list(linkages[0]))
        write_csv(staging / "transition_attestation_ledger.csv", transitions, list(transitions[0]))
        write_csv(staging / "economic_event_ledger.csv", event_rows, event_fields)
        write_csv(staging / "unresolved_economic_event_ledger.csv", unresolved_rows, event_fields)
        write_csv(staging / "non_basis_exclusion_ledger.csv", non_basis_rows, event_fields)
        write_csv(staging / "source_to_economic_mapping.csv", source_mapping, list(source_mapping[0]))
        write_csv(staging / "composite_component_ledger.csv", component_rows, list(component_rows[0]))
        write_csv(staging / "remaining_gap_geometry.csv", family_gap_rows, list(family_gap_rows[0]))
        write_json(staging / "reconciliation_summary.json", summary)
        write_json(staging / "validation_report.json", validation)
        write_json(staging / "deterministic_replay.json", {
            "input_manifest_sha256": V15_MANIFEST_SHA256,
            "repo_head": actual_head,
            "result_sha256": hashlib.sha256(result_bytes.encode()).hexdigest(),
            "replay_sha256": hashlib.sha256(replay_bytes.encode()).hexdigest(),
            "byte_identical": result_bytes == replay_bytes,
        })
        write_json(staging / "selection_manifest.json", {
            "schema_version": "inc001_ca_composite_policy_selection_v1",
            "audit_date": AUDIT_DATE,
            "policy_decision": "positive share leg makes composite distribution basis-changing",
            "source_label": "Mixed Dividend",
            "selected_count": len(component_rows),
            "selected_source_event_ids": sorted(row["source_event_id"] for row in component_rows),
            "not_selected_by_label_alone": True,
            "transition_not_inferred": True,
        })
        manifest = {
            "schema_version": "inc001_ca_composite_policy_reconciliation_manifest_v1",
            "audit_date": AUDIT_DATE,
            "predecessor_manifest_sha256": V15_MANIFEST_SHA256,
            "repository_head": actual_head,
            "files": [],
        }
        for path in sorted(staging.iterdir()):
            if path.name == "MANIFEST.json":
                continue
            manifest["files"].append({"path": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
        write_json(staging / "MANIFEST.json", manifest)
        staging.rename(output_root)
        return {"summary": summary, "validation": validation, "manifest_sha256": sha256_file(output_root / "MANIFEST.json")}
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--prior-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--expected-repo-head")
    args = parser.parse_args()
    result = build(args)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
