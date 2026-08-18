"""Outcome-blind V4 CA continuity replay with targeted seven-event evidence.

The replay rebuilds the frozen 600-date continuity state from the immutable
base ledger, the accepted 598/610 KSEI remediation census, the accepted
residual-document evidence, and the new targeted evidence. It never mutates an
existing ledger and it never treats a newly found transition as automatically
resolved: target intervals crossing that exact transition remain blocked.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import pandas as pd

import run_v4_ca_event_window_support as frozen
import run_v4_ca_coverage_gap_continuity_replay as coverage_replay
from idx_trade.v4_ca_targeted_schedule_evidence import (
    classify_event_with_targeted_evidence,
)
from idx_trade.v4_ksei_coverage_gap import sha256_file


EXPECTED_TARGETED_SELECTED_SHA = "f6650daf7256196f976b0a9d161dbf0cf896d0d349306be4fe4c76b1d2168529"
EXPECTED_TARGETED_CALENDAR_SHA = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"


def verify_targeted_root(root: Path) -> tuple[dict, Path, str]:
    manifest_path = root / "MANIFEST.json"
    summary_path = root / "summary.json"
    evidence_path = root / "targeted_evidence.csv"
    for path in (manifest_path, summary_path, evidence_path):
        if not path.is_file():
            raise RuntimeError(f"TARGETED_EVIDENCE_REQUIRED_FILE_MISSING:{path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "v4_ca_targeted_schedule_evidence_manifest_v1":
        raise RuntimeError("TARGETED_EVIDENCE_MANIFEST_SCHEMA_INVALID")
    if summary.get("schema_version") != "v4_ca_targeted_schedule_evidence_v1":
        raise RuntimeError("TARGETED_EVIDENCE_SUMMARY_SCHEMA_INVALID")
    if summary.get("status") != "V4_CA_TARGETED_SEVEN_EVENT_EVIDENCE_COMPLETE":
        raise RuntimeError("TARGETED_EVIDENCE_STATUS_INVALID")
    if summary.get("outcome_blind") is not True or manifest.get("outcome_blind") is not True:
        raise RuntimeError("TARGETED_EVIDENCE_NOT_OUTCOME_BLIND")
    if summary.get("provider_calls") is not True or manifest.get("provider_calls") is not True:
        raise RuntimeError("TARGETED_EVIDENCE_PROVIDER_FLAG_INVALID")
    if summary.get("source_substitution") is not False:
        raise RuntimeError("TARGETED_EVIDENCE_SOURCE_SUBSTITUTION_INVALID")
    inputs = summary.get("input_hashes") or {}
    if inputs.get("selected_subset") != EXPECTED_TARGETED_SELECTED_SHA:
        raise RuntimeError("TARGETED_EVIDENCE_SELECTED_SHA_INVALID")
    if inputs.get("official_calendar") != EXPECTED_TARGETED_CALENDAR_SHA:
        raise RuntimeError("TARGETED_EVIDENCE_CALENDAR_SHA_INVALID")
    if sha256_file(summary_path) != manifest.get("summary_sha256"):
        raise RuntimeError("TARGETED_EVIDENCE_SUMMARY_HASH_MISMATCH")
    actual_evidence_sha = sha256_file(evidence_path)
    if (summary.get("output_hashes") or {}).get("targeted_evidence") != actual_evidence_sha:
        raise RuntimeError("TARGETED_EVIDENCE_OUTPUT_HASH_MISMATCH")
    if (manifest.get("output_hashes") or {}).get("targeted_evidence") != actual_evidence_sha:
        raise RuntimeError("TARGETED_EVIDENCE_MANIFEST_OUTPUT_HASH_MISMATCH")
    return summary, evidence_path, sha256_file(manifest_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--continuity-ledger", type=Path, required=True)
    parser.add_argument("--prior-event-evidence", type=Path, required=True)
    parser.add_argument("--official-calendar", type=Path, required=True)
    parser.add_argument("--ksei-remediation-root", type=Path, required=True)
    parser.add_argument("--residual-document-root", type=Path, required=True)
    parser.add_argument("--targeted-evidence-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")

    remediation_summary, remediation_manifest_sha = coverage_replay.verify_remediation_root(
        args.ksei_remediation_root
    )
    residual_evidence_path, residual_manifest_sha = coverage_replay.verify_document_root(
        args.residual_document_root
    )
    targeted_summary, targeted_evidence_path, targeted_manifest_sha = verify_targeted_root(
        args.targeted_evidence_root
    )

    residual = pd.read_csv(residual_evidence_path, dtype=str, keep_default_na=False)
    targeted = pd.read_csv(targeted_evidence_path, dtype=str, keep_default_na=False)
    merged = pd.concat([residual, targeted], ignore_index=True, sort=False).fillna("")
    if merged.duplicated().any():
        merged = merged.drop_duplicates().reset_index(drop=True)

    outputs = remediation_summary["output_hashes"]
    frozen.PINNED = dict(frozen.PINNED)
    frozen.PINNED["ksei_manifest"] = remediation_manifest_sha
    frozen.PINNED["ksei_summary"] = sha256_file(args.ksei_remediation_root / "summary.json")
    frozen.PINNED["ksei_coverage"] = outputs["ticker_coverage"]
    frozen.PINNED["ksei_history"] = outputs["ksei_ca_history"]
    frozen.classify_event = classify_event_with_targeted_evidence

    original_build_window_ledger = frozen.build_window_ledger

    def build_window_ledger_with_policy(*inner_args, **inner_kwargs):
        frame = original_build_window_ledger(*inner_args, **inner_kwargs).copy()
        frame["policy_id"] = "V4_CA_TARGETED_SCHEDULE_EVIDENCE_V1+V4_CA_KSEI_COVERAGE_GAP_REMEDIATION_V1"
        return frame

    frozen.build_window_ledger = build_window_ledger_with_policy

    with tempfile.TemporaryDirectory(prefix="v4_ca_targeted_schedule_") as tmp:
        merged_evidence_path = Path(tmp) / "merged_schedule_evidence.csv"
        merged.to_csv(merged_evidence_path, index=False, lineterminator="\n")
        original_argv = list(sys.argv)
        try:
            sys.argv = [
                original_argv[0],
                "--continuity-ledger", str(args.continuity_ledger),
                "--prior-event-evidence", str(args.prior_event_evidence),
                "--official-calendar", str(args.official_calendar),
                "--ksei-census-root", str(args.ksei_remediation_root),
                "--schedule-evidence", str(merged_evidence_path),
                "--output-dir", str(args.output_dir),
            ]
            result = frozen.main()
        finally:
            sys.argv = original_argv

    summary_path = args.output_dir / "summary.json"
    if not summary_path.is_file():
        raise RuntimeError("TARGETED_CONTINUITY_SUMMARY_MISSING")
    continuity_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    overlay = {
        "schema_version": "v4_ca_targeted_schedule_continuity_overlay_v1",
        "outcome_blind": True,
        "provider_calls_in_continuity_replay": False,
        "ksei_remediation_manifest_sha256": remediation_manifest_sha,
        "ksei_coverage_certified_tickers": remediation_summary.get("merged_coverage_certified_tickers"),
        "ksei_remaining_unresolved_tickers": remediation_summary.get("remaining_unresolved_ticker_count"),
        "residual_document_manifest_sha256": residual_manifest_sha,
        "targeted_evidence_manifest_sha256": targeted_manifest_sha,
        "targeted_exact_static_nonblocking_events": targeted_summary.get("exact_static_nonblocking_events"),
        "targeted_exact_schedule_transition_events": targeted_summary.get("exact_schedule_transition_events"),
        "targeted_unresolved_selected_events": targeted_summary.get("unresolved_selected_events"),
        "targeted_resolved_event_ids": targeted_summary.get("resolved_event_ids"),
        "targeted_unresolved_event_ids": targeted_summary.get("unresolved_event_ids"),
        "merged_evidence_rows": int(len(merged)),
        "continuity_summary_sha256": sha256_file(summary_path),
        "continuity_verdict": continuity_summary.get("verdict"),
        "corporate_action_continuity_certified": continuity_summary.get("corporate_action_continuity_certified"),
        "event_rows_relevant_to_study": continuity_summary.get("event_rows_relevant_to_study"),
        "event_semantic_counts": continuity_summary.get("event_semantic_counts"),
        "schedule_required_events": continuity_summary.get("schedule_required_events"),
        "schedule_required_tickers": continuity_summary.get("schedule_required_tickers"),
        "cross_source_conflict_tickers": continuity_summary.get("cross_source_conflict_tickers"),
        "per_date": continuity_summary.get("per_date"),
    }
    overlay_path = args.output_dir / "targeted_schedule_continuity_overlay.json"
    overlay_path.write_text(json.dumps(overlay, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**overlay, "overlay_sha256": sha256_file(overlay_path)}, indent=2, sort_keys=True))
    return int(result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
