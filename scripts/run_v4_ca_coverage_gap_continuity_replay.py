"""Outcome-blind V4 CA continuity replay after targeted KSEI gap recovery.

This wrapper verifies the exact targeted-remediation artifact, repins only the
KSEI census byte identities consumed by the accepted event-window runner, and
replays the latest accepted residual-document/voluntary-cash semantics.

It does not alter the frozen 90% gate, universe, target, evaluator, or model.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import run_v4_ca_event_window_support as frozen

from idx_trade.v4_ca_residual_document_semantics import (
    POLICY_ID as RESIDUAL_POLICY_ID,
    classify_event_with_residual_document_evidence,
)
from idx_trade.v4_ksei_coverage_gap import sha256_file


EXPECTED_PARENT = {
    "manifest": "7cc3ac4d409c3e15c6aa566b63bedab4268562fd4914d1af198ab29657dba25a",
    "summary": "a046637fbcff69cbc42c09e4cac30d9181b2ce93a3cf7297a9a01cfc23a2f422",
    "ticker_coverage": "bb5414125862411e5d3ee760f8e7415b8418803c71d1cc1ef26fb0c55397bc70",
    "ksei_ca_history": "3ea2f0a160300dd4d74c40281dbcbf680e03accc565487cf00b190630471c08d",
    "request_records": "e68d60103cc3efc04299c1b330c4ef39e55ba1e44bbcf79f178b2f1ccff812e5",
}
EXPECTED_GAP_SHA = "1cd050985841519d24f58a38d10014693ff4a843cbd438586237ad4419ffe812"
EXPECTED_DOCUMENT_MANIFEST_SHA = "6f2070dbd89307c39579aa9617807c2c8ae746390466476f29504b31ae4988a5"
EXPECTED_DOCUMENT_EVIDENCE_SHA = "6be49b4fc8a930c9bc61fde64a0652a7cb6233459f5a2e140cb4b4ad0f56592e"


def verify_remediation_root(root: Path) -> tuple[dict, str]:
    required = {
        "manifest": root / "MANIFEST.json",
        "summary": root / "summary.json",
        "ticker_coverage": root / "ticker_coverage.csv",
        "ksei_ca_history": root / "ksei_ca_history.jsonl",
    }
    for label, path in required.items():
        if not path.is_file():
            raise RuntimeError(f"KSEI_GAP_REMEDIATION_REQUIRED_FILE_MISSING:{label}:{path}")
    manifest = json.loads(required["manifest"].read_text(encoding="utf-8"))
    summary = json.loads(required["summary"].read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "v4_ksei_coverage_gap_remediation_manifest_v1":
        raise RuntimeError("KSEI_GAP_REMEDIATION_MANIFEST_SCHEMA_INVALID")
    if summary.get("schema_version") != "v4_ksei_coverage_gap_remediation_v1":
        raise RuntimeError("KSEI_GAP_REMEDIATION_SUMMARY_SCHEMA_INVALID")
    if not str(summary.get("status", "")).startswith("V4_KSEI_COVERAGE_GAP_REMEDIATION_COMPLETE"):
        raise RuntimeError("KSEI_GAP_REMEDIATION_STATUS_INVALID")
    if summary.get("outcome_blind") is not True or manifest.get("outcome_blind") is not True:
        raise RuntimeError("KSEI_GAP_REMEDIATION_NOT_OUTCOME_BLIND")
    if summary.get("provider_calls") is not True or manifest.get("provider_calls") is not True:
        raise RuntimeError("KSEI_GAP_REMEDIATION_PROVIDER_FLAG_INVALID")
    if summary.get("source_substitution") is not False or summary.get("parser_relaxation") is not False:
        raise RuntimeError("KSEI_GAP_REMEDIATION_SOURCE_OR_PARSER_POLICY_INVALID")
    if summary.get("full_610_recrawl") is not False:
        raise RuntimeError("KSEI_GAP_REMEDIATION_FULL_RECRAWL_FLAG_INVALID")
    if summary.get("gap_ticker_identity_sha256") != EXPECTED_GAP_SHA:
        raise RuntimeError("KSEI_GAP_REMEDIATION_TICKER_IDENTITY_INVALID")
    if summary.get("parent_hashes") != EXPECTED_PARENT or manifest.get("parent_hashes") != EXPECTED_PARENT:
        raise RuntimeError("KSEI_GAP_REMEDIATION_PARENT_HASHES_INVALID")
    if sha256_file(required["summary"]) != manifest.get("summary_sha256"):
        raise RuntimeError("KSEI_GAP_REMEDIATION_SUMMARY_HASH_MISMATCH")
    outputs = summary.get("output_hashes") or {}
    manifest_outputs = manifest.get("output_hashes") or {}
    for logical, path_key in (("ticker_coverage", "ticker_coverage"), ("ksei_ca_history", "ksei_ca_history")):
        actual = sha256_file(required[path_key])
        if outputs.get(logical) != actual or manifest_outputs.get(logical) != actual:
            raise RuntimeError(f"KSEI_GAP_REMEDIATION_OUTPUT_HASH_MISMATCH:{logical}")
    return summary, sha256_file(required["manifest"])


def verify_document_root(root: Path) -> tuple[Path, str]:
    manifest = root / "MANIFEST.json"
    evidence = root / "residual_event_document_evidence.csv"
    if not manifest.is_file() or not evidence.is_file():
        raise RuntimeError("RESIDUAL_DOCUMENT_EVIDENCE_ROOT_INCOMPLETE")
    if sha256_file(manifest) != EXPECTED_DOCUMENT_MANIFEST_SHA:
        raise RuntimeError("RESIDUAL_DOCUMENT_MANIFEST_HASH_MISMATCH")
    if sha256_file(evidence) != EXPECTED_DOCUMENT_EVIDENCE_SHA:
        raise RuntimeError("RESIDUAL_DOCUMENT_EVIDENCE_HASH_MISMATCH")
    return evidence, sha256_file(manifest)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--continuity-ledger", type=Path, required=True)
    parser.add_argument("--prior-event-evidence", type=Path, required=True)
    parser.add_argument("--official-calendar", type=Path, required=True)
    parser.add_argument("--ksei-remediation-root", type=Path, required=True)
    parser.add_argument("--document-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    remediation_summary, remediation_manifest_sha = verify_remediation_root(args.ksei_remediation_root)
    schedule_evidence, document_manifest_sha = verify_document_root(args.document_root)

    # The accepted event-window runner still pins the immutable parent KSEI
    # census.  Repin exactly the four KSEI logical files to the verified merged
    # remediation root; every non-KSEI input remains frozen in the parent runner.
    outputs = remediation_summary["output_hashes"]
    frozen.PINNED = dict(frozen.PINNED)
    frozen.PINNED["ksei_manifest"] = remediation_manifest_sha
    frozen.PINNED["ksei_summary"] = sha256_file(args.ksei_remediation_root / "summary.json")
    frozen.PINNED["ksei_coverage"] = outputs["ticker_coverage"]
    frozen.PINNED["ksei_history"] = outputs["ksei_ca_history"]
    frozen.classify_event = classify_event_with_residual_document_evidence

    original_build_window_ledger = frozen.build_window_ledger

    def build_window_ledger_with_policy(*inner_args, **inner_kwargs):
        frame = original_build_window_ledger(*inner_args, **inner_kwargs).copy()
        frame["policy_id"] = "V4_CA_KSEI_COVERAGE_GAP_REMEDIATION_V1+" + RESIDUAL_POLICY_ID
        return frame

    frozen.build_window_ledger = build_window_ledger_with_policy
    original_argv = list(sys.argv)
    try:
        sys.argv = [
            original_argv[0],
            "--continuity-ledger", str(args.continuity_ledger),
            "--prior-event-evidence", str(args.prior_event_evidence),
            "--official-calendar", str(args.official_calendar),
            "--ksei-census-root", str(args.ksei_remediation_root),
            "--schedule-evidence", str(schedule_evidence),
            "--output-dir", str(args.output_dir),
        ]
        result = frozen.main()
    finally:
        sys.argv = original_argv

    summary_path = args.output_dir / "summary.json"
    if not summary_path.is_file():
        raise RuntimeError("KSEI_GAP_CONTINUITY_SUMMARY_MISSING")
    continuity_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    overlay = {
        "schema_version": "v4_ca_ksei_coverage_gap_continuity_overlay_v1",
        "outcome_blind": True,
        "provider_calls_in_continuity_replay": False,
        "ksei_remediation_manifest_sha256": remediation_manifest_sha,
        "ksei_recovered_ticker_count": remediation_summary.get("recovered_ticker_count"),
        "ksei_remaining_unresolved_ticker_count": remediation_summary.get("remaining_unresolved_ticker_count"),
        "ksei_recovered_active_mechanical_or_unknown_rows": remediation_summary.get("recovered_active_mechanical_or_unknown_rows"),
        "document_manifest_sha256": document_manifest_sha,
        "document_evidence_sha256": sha256_file(schedule_evidence),
        "continuity_summary_sha256": sha256_file(summary_path),
        "continuity_verdict": continuity_summary.get("verdict"),
        "corporate_action_continuity_certified": continuity_summary.get("corporate_action_continuity_certified"),
        "event_rows_relevant_to_study": continuity_summary.get("event_rows_relevant_to_study"),
        "event_semantic_counts": continuity_summary.get("event_semantic_counts"),
        "schedule_required_events": continuity_summary.get("schedule_required_events"),
        "schedule_required_tickers": continuity_summary.get("schedule_required_tickers"),
        "coverage_certified_tickers": continuity_summary.get("coverage_certified_tickers"),
        "coverage_unresolved_tickers": continuity_summary.get("coverage_unresolved_tickers"),
        "cross_source_conflict_tickers": continuity_summary.get("cross_source_conflict_tickers"),
        "per_date": continuity_summary.get("per_date"),
    }
    overlay_path = args.output_dir / "ksei_coverage_gap_continuity_overlay.json"
    overlay_path.write_text(json.dumps(overlay, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**overlay, "overlay_sha256": sha256_file(overlay_path)}, indent=2, sort_keys=True))
    return int(result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
