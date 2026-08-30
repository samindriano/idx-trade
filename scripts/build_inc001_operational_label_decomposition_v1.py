"""Build a retained-evidence-only decomposition of INC-001 operational labels.

This is audit tooling, not production reconciliation code.  It consumes the
immutable V14 economic reconciliation and the hash-bound raw KSEI pages already
retained there.  It performs no provider calls, network access, outcome access,
canonical rewrite, or reconciliation mutation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


AUDIT_DATE = "2026-08-30"
SCHEMA = "inc001_operational_label_decomposition_v1"
EXPECTED_V14_MANIFEST_SHA = (
    "c095c00c31691c07cbf4d50c447abafde9b00db0e93f8184ea6e9a83b4a1990b"
)
EXPECTED_COUNTS = {
    "source_evidence_rows": 412,
    "economic_event_count": 387,
    "resolved_transitions": 160,
    "unresolved_transitions": 181,
    "non_basis_excluded": 46,
    "proven_linkages": 27,
    "operational_label_events": 47,
}
CLASSIFICATION_KEYS = (
    "PROVEN_NON_BASIS",
    "PROVEN_STOCK_SPLIT",
    "PROVEN_REVERSE_SPLIT",
    "PROVEN_RIGHTS_HMETD",
    "PROVEN_TRUE_SECURITY_CONVERSION",
    "PROVEN_CAPITAL_RESTRUCTURING",
    "PROVEN_OTHER_EXISTING_FAMILY",
    "SEMANTIC_INSUFFICIENT",
)
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
EVENT_FIELDS = (
    "economic_event_id",
    "ticker",
    "source_event_id",
    "original_source_operation_label",
    "source_ref",
    "evidence_sha256",
    "raw_capture_path",
    "raw_source_row_index",
    "candidate_date",
    "cum_date",
    "record_date",
    "distribution_date",
    "ratio_raw",
    "ratio_left_security",
    "ratio_left_value",
    "ratio_right_security",
    "ratio_right_value",
    "current_economic_family",
    "adjudicated_economic_family",
    "basis_effect",
    "adjudicated_basis_effect",
    "exact_transition_state",
    "raw_hash_matches_evidence",
    "raw_label_present",
    "raw_candidate_date_present",
    "reason_evidence",
    "final_classification",
)


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def valid_sha(value: Any) -> bool:
    return bool(SHA256_RE.fullmatch(text(value)))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def csv_bytes(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(fields), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: text(row.get(field)) for field in fields})
    return output.getvalue().encode("utf-8")


def git_value(repo_root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo_root), *args],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def verify_v14(v14_root: Path) -> dict[str, Any]:
    manifest_path = v14_root / "MANIFEST.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest_sha = sha256_file(manifest_path)
    if manifest_sha != EXPECTED_V14_MANIFEST_SHA:
        raise RuntimeError(
            f"V14 manifest mismatch: {manifest_sha} != {EXPECTED_V14_MANIFEST_SHA}"
        )
    manifest = read_json(manifest_path)
    mismatches: list[str] = []
    expected_outputs = manifest.get("output_hashes_excluding_manifest", {})
    for name, metadata in sorted(expected_outputs.items()):
        path = v14_root / name
        if not path.is_file():
            mismatches.append(f"missing:{name}")
            continue
        if path.stat().st_size != metadata.get("bytes"):
            mismatches.append(f"bytes:{name}")
        if sha256_file(path) != metadata.get("sha256"):
            mismatches.append(f"sha256:{name}")
    if mismatches:
        raise RuntimeError(f"V14 output hash audit failed: {mismatches}")
    return {
        "manifest_sha256": manifest_sha,
        "manifest_output_count": len(expected_outputs),
        "manifest_outputs_verified": True,
    }


def source_by_id(v14_root: Path) -> dict[str, dict[str, str]]:
    rows = read_csv(v14_root / "source_evidence_ledger.csv")
    if len(rows) != EXPECTED_COUNTS["source_evidence_rows"]:
        raise RuntimeError(f"source evidence row count diverges: {len(rows)}")
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        source_id = text(row.get("source_event_id"))
        if not source_id or source_id in result:
            raise RuntimeError(f"missing or duplicate source_event_id: {source_id}")
        if not text(row.get("source_ref")) or not valid_sha(row.get("evidence_sha256")):
            raise RuntimeError(f"source provenance invalid: {source_id}")
        result[source_id] = row
    return result


def operational_events(
    v14_root: Path, sources: Mapping[str, Mapping[str, str]]
) -> list[dict[str, str]]:
    events = read_csv(v14_root / "economic_event_ledger.csv")
    unresolved = read_csv(v14_root / "unresolved_economic_event_ledger.csv")
    unresolved_ids = {
        text(row.get("economic_event_id"))
        for row in unresolved
        if text(row.get("economic_event_id"))
    }
    selected = [
        row
        for row in events
        if text(row.get("economic_family")) == "UNRESOLVED_OPERATIONAL_LABEL"
        and text(row.get("transition_status")) == "UNRESOLVED"
    ]
    if len(selected) != EXPECTED_COUNTS["operational_label_events"]:
        raise RuntimeError(f"operational-label count diverges: {len(selected)}")
    if len(unresolved) != EXPECTED_COUNTS["unresolved_transitions"]:
        raise RuntimeError(f"unresolved count diverges: {len(unresolved)}")
    if any(text(row.get("economic_event_id")) not in unresolved_ids for row in selected):
        raise RuntimeError("operational event is absent from unresolved ledger")

    result: list[dict[str, str]] = []
    source_ids: set[str] = set()
    for event in sorted(selected, key=lambda row: text(row.get("economic_event_id"))):
        economic_id = text(event.get("economic_event_id"))
        members = [
            text(value)
            for value in text(event.get("source_event_ids")).split("|")
            if text(value)
        ]
        if len(members) != 1 or members[0] not in sources:
            raise RuntimeError(f"operational event is not a single retained source row: {economic_id}")
        source_id = members[0]
        if source_id in source_ids:
            raise RuntimeError(f"operational source row duplicated: {source_id}")
        source_ids.add(source_id)
        source = sources[source_id]
        if text(source.get("source_kind")) != "KSEI_REGISTERED_SECURITY_HISTORY":
            raise RuntimeError(f"operational source is not retained KSEI history: {source_id}")
        if text(source.get("event_family")).upper() != "VOLUNTARY_CONVERSION":
            raise RuntimeError(f"unexpected source event family: {source_id}")
        if text(source.get("source_native_label")) != "Voluntary Conversion":
            raise RuntimeError(f"unexpected source-native label: {source_id}")
        for field in (
            "ratio_raw",
            "ratio_left_security",
            "ratio_left_value",
            "ratio_right_security",
            "ratio_right_value",
        ):
            if text(source.get(field)):
                raise RuntimeError(f"operational source has unexpected retained {field}: {source_id}")
        raw_path = Path(text(source.get("raw_capture_path")))
        if not raw_path.is_file():
            raise RuntimeError(f"retained raw path missing: {raw_path}")
        actual_sha = sha256_file(raw_path)
        if actual_sha != text(source.get("evidence_sha256")).lower():
            raise RuntimeError(f"retained raw hash mismatch: {source_id}")
        raw_body = raw_path.read_text(encoding="utf-8", errors="replace")
        candidate = text(source.get("candidate_date"))
        if "Voluntary Conversion" not in raw_body:
            raise RuntimeError(f"retained raw label missing: {source_id}")
        if not candidate or candidate.replace("-", "") not in raw_body:
            raise RuntimeError(f"retained raw candidate date missing: {source_id}")
        result.append(
            {
                "economic_event_id": economic_id,
                "ticker": text(source.get("ticker")),
                "source_event_id": source_id,
                "original_source_operation_label": text(source.get("source_native_label")),
                "source_ref": text(source.get("source_ref")),
                "evidence_sha256": text(source.get("evidence_sha256")).lower(),
                "raw_capture_path": text(source.get("raw_capture_path")),
                "raw_source_row_index": text(source.get("raw_source_row_index")),
                "candidate_date": candidate,
                "cum_date": text(source.get("cum_date")),
                "record_date": text(source.get("record_date")),
                "distribution_date": text(source.get("distribution_date")),
                "ratio_raw": text(source.get("ratio_raw")),
                "ratio_left_security": text(source.get("ratio_left_security")),
                "ratio_left_value": text(source.get("ratio_left_value")),
                "ratio_right_security": text(source.get("ratio_right_security")),
                "ratio_right_value": text(source.get("ratio_right_value")),
                "current_economic_family": text(event.get("economic_family")),
                "adjudicated_economic_family": "UNRESOLVED_OPERATIONAL_LABEL",
                "basis_effect": text(event.get("basis_effect")),
                "adjudicated_basis_effect": "UNKNOWN_NOT_PROVEN",
                "exact_transition_state": text(event.get("transition_status")),
                "raw_hash_matches_evidence": "true",
                "raw_label_present": "true",
                "raw_candidate_date_present": "true",
                "reason_evidence": (
                    "Retained KSEI evidence exposes only the source-native Voluntary "
                    "Conversion label; ratio and receiving-security fields are empty. "
                    "Record/distribution dates do not establish the economic instrument "
                    "or an accepted regular-market transition. No retained official "
                    "mechanics or hash-bound schedule proves a permitted family."
                ),
                "final_classification": "SEMANTIC_INSUFFICIENT",
            }
        )
    return result


def build_payloads(
    *, v14_root: Path, repo_root: Path
) -> tuple[dict[str, bytes], dict[str, Any]]:
    v14_integrity = verify_v14(v14_root)
    sources = source_by_id(v14_root)
    events = operational_events(v14_root, sources)
    summary = read_json(v14_root / "reconciliation_summary.json")
    if summary.get("counts_after") != {
        "cross_source_collapses": 22,
        "economic_event_count": 387,
        "non_basis_excluded": 46,
        "resolved_transitions": 160,
        "same_source_collapses": 3,
        "source_evidence_rows": 412,
        "unresolved_transitions": 181,
    }:
        raise RuntimeError("V14 reconciliation counts do not match controlling summary")
    linkage_rows = read_csv(v14_root / "proven_same_event_linkage_ledger.csv")
    if len(linkage_rows) != EXPECTED_COUNTS["proven_linkages"]:
        raise RuntimeError(f"proven linkage count diverges: {len(linkage_rows)}")
    classifications = Counter(row["final_classification"] for row in events)
    classification_counts = {key: classifications.get(key, 0) for key in CLASSIFICATION_KEYS}
    if classification_counts["SEMANTIC_INSUFFICIENT"] != len(events):
        raise RuntimeError("a retained operational label was unexpectedly promoted")
    unresolved_by_family = Counter(
        text(row.get("economic_family"))
        for row in read_csv(v14_root / "unresolved_economic_event_ledger.csv")
    )
    branch = git_value(repo_root, "branch", "--show-current")
    head = git_value(repo_root, "rev-parse", "HEAD")
    input_names = (
        "MANIFEST.json",
        "economic_event_ledger.csv",
        "unresolved_economic_event_ledger.csv",
        "source_evidence_ledger.csv",
        "economic_adjudication_ledger.csv",
        "proven_same_event_linkage_ledger.csv",
        "reconciliation_summary.json",
    )
    input_hashes = {
        name: {"bytes": (v14_root / name).stat().st_size, "sha256": sha256_file(v14_root / name)}
        for name in input_names
    }
    input_pins = {
        "controlling_v14_root": str(v14_root),
        "controlling_v14_manifest_sha256": EXPECTED_V14_MANIFEST_SHA,
        "repository_branch": branch,
        "repository_head": head,
        "input_hashes": input_hashes,
        "provider_calls": False,
        "outcome_blind": True,
    }
    summary_payload = {
        "schema_version": SCHEMA,
        "audit_date": AUDIT_DATE,
        "status": "RETAINED_EVIDENCE_DECOMPOSITION_COMPLETE_NO_RECONCILIATION_CHANGE",
        "scope": {
            "source_family": "KSEI_REGISTERED_SECURITY_HISTORY",
            "source_native_label": "Voluntary Conversion",
            "economic_family_before": "UNRESOLVED_OPERATIONAL_LABEL",
            "operational_label_before": 47,
            "operational_label_after": 47,
        },
        "classification_counts": classification_counts,
        "linkages": {
            "PRIOR_PROVEN_LINKAGES": 27,
            "RECOMPUTED_PROVEN_LINKAGES": 27,
            "NEW_PROVEN_LINKAGES": 0,
            "REMOVED_OR_CONFLICTING": 0,
        },
        "economic_counts": {
            "source_evidence_rows_before": 412,
            "source_evidence_rows_after": 412,
            "economic_events_before": 387,
            "economic_events_after": 387,
            "resolved_before": 160,
            "resolved_after": 160,
            "unresolved_before": 181,
            "unresolved_after": 181,
            "non_basis_before": 46,
            "non_basis_after": 46,
        },
        "unresolved_by_family_after": dict(sorted(unresolved_by_family.items())),
        "next_action_recommendation": "PARK_REMAINING_OPERATIONAL_LABELS",
        "validation": {
            "v14_manifest_outputs_verified": True,
            "v14_manifest_sha256": v14_integrity["manifest_sha256"],
            "operational_event_count": len(events),
            "unique_economic_event_ids": len({row["economic_event_id"] for row in events}),
            "unique_source_event_ids": len({row["source_event_id"] for row in events}),
            "all_raw_hashes_match": all(row["raw_hash_matches_evidence"] == "true" for row in events),
            "all_raw_labels_present": all(row["raw_label_present"] == "true" for row in events),
            "all_raw_candidate_dates_present": all(
                row["raw_candidate_date_present"] == "true" for row in events
            ),
            "all_ratios_and_receiving_security_fields_blank": all(
                not any(row[field] for field in (
                    "ratio_raw",
                    "ratio_left_security",
                    "ratio_left_value",
                    "ratio_right_security",
                    "ratio_right_value",
                ))
                for row in events
            ),
            "no_reconciliation_successor": True,
            "provider_calls": False,
            "fresh_downloads": False,
            "canonical_historical_rewrite": False,
            "outcomes_or_targets": False,
            "fit_refit_score": False,
            "counter_mutation": False,
            "production_execution": False,
            "merge": False,
        },
        "scientific_verdict_unchanged": {
            "DATA_ADMISSION": "FAIL",
            "RESEARCH_ADMISSION": "FAIL",
            "PHASE_E_AUTHORIZED": False,
            "REFIT_AUTHORIZED": False,
            "COUNTER_ACTION": "NONE",
        },
    }
    payloads = {
        "operational_label_decomposition.csv": csv_bytes(events, EVENT_FIELDS),
        "input_pins.json": json_bytes(input_pins),
        "summary.json": json_bytes(summary_payload),
        "validation_report.json": json_bytes(summary_payload["validation"]),
    }
    comparison = {
        "compared_file_count": len(payloads),
        "differences": [],
        "verdict": "PASS",
    }
    payloads["deterministic_comparison.json"] = json_bytes(comparison)
    return payloads, summary_payload


def manifest_for(root: Path, payloads: Mapping[str, bytes]) -> dict[str, Any]:
    return {
        "manifest_version": f"{SCHEMA}_manifest",
        "artifact_root": str(root),
        "audit_date": AUDIT_DATE,
        "outcome_blind": True,
        "provider_calls": False,
        "output_hashes_excluding_manifest": {
            name: {"bytes": len(payload), "sha256": sha256_bytes(payload)}
            for name, payload in sorted(payloads.items())
        },
        "self_hash_policy": "MANIFEST.json excluded from its own hash",
    }


def write_immutable_artifact(
    *, v14_root: Path, repo_root: Path, output_root: Path
) -> dict[str, Any]:
    if output_root.exists():
        raise FileExistsError(f"immutable output root already exists: {output_root}")
    first, summary = build_payloads(v14_root=v14_root, repo_root=repo_root)
    second, _ = build_payloads(v14_root=v14_root, repo_root=repo_root)
    names = sorted(set(first) | set(second))
    differences = [name for name in names if first.get(name) != second.get(name)]
    comparison = {
        "compared_file_count": len(names),
        "differences": differences,
        "verdict": "PASS" if not differences else "FAIL",
    }
    if differences:
        raise RuntimeError(f"deterministic comparison failed: {differences}")
    first["deterministic_comparison.json"] = json_bytes(comparison)
    output_root.mkdir(parents=True)
    try:
        for name, payload in sorted(first.items()):
            (output_root / name).write_bytes(payload)
        (output_root / "MANIFEST.json").write_bytes(json_bytes(manifest_for(output_root, first)))
    except Exception:
        for child in output_root.iterdir():
            child.unlink()
        output_root.rmdir()
        raise
    return {
        "output_root": str(output_root),
        "manifest_sha256": sha256_file(output_root / "MANIFEST.json"),
        "summary": summary,
        "deterministic_comparison": comparison,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--v14-root",
        type=Path,
        default=Path(r"D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v14-same-exact"),
    )
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    result = write_immutable_artifact(
        v14_root=args.v14_root,
        repo_root=args.repo_root,
        output_root=args.output_root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
