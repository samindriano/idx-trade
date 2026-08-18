"""Outcome-blind continuity replay over the exact ICBP coverage overlay.

This runner consumes a successful one-ticker ICBP KSEI remediation root and
replays the frozen V4 continuity contract with the already accepted residual
and targeted schedule evidence.  It performs no provider calls and does not
change the 90% gate, universe, horizons, event semantics, or model state.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
SCRIPTS_ROOT = Path(__file__).resolve().parent
for path in (SRC_ROOT, SCRIPTS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import pandas as pd

import run_v4_ca_coverage_gap_continuity_replay as coverage_replay
import run_v4_ca_event_window_support as frozen
import run_v4_ca_targeted_schedule_continuity_replay as targeted_replay
from idx_trade.v4_ca_icbp_single_ticker_remediation import (
    EXPECTED_OUTPUT_UNRESOLVED,
    TARGET_TICKER,
    validate_output_coverage,
)
from idx_trade.v4_ca_targeted_schedule_evidence import classify_event_with_targeted_evidence
from idx_trade.v4_ksei_coverage_gap import read_jsonl, sha256_file


EXPECTED_PARENT_MANIFEST_SHA256 = "7e86f5e52d7c2ff609ee9dd4be28ff1aefea1e4d5c7d7d9dbffb6abd07185f50"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--continuity-ledger", type=Path, required=True)
    parser.add_argument("--prior-event-evidence", type=Path, required=True)
    parser.add_argument("--official-calendar", type=Path, required=True)
    parser.add_argument("--icbp-remediation-root", type=Path, required=True)
    parser.add_argument("--residual-document-root", type=Path, required=True)
    parser.add_argument("--targeted-evidence-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def verify_icbp_root(root: Path) -> tuple[dict[str, Any], str]:
    manifest_path = root / "MANIFEST.json"
    summary_path = root / "summary.json"
    coverage_path = root / "ticker_coverage.csv"
    history_path = root / "ksei_ca_history.jsonl"
    for path in (manifest_path, summary_path, coverage_path, history_path):
        if not path.is_file():
            raise RuntimeError(f"ICBP_REMEDIATION_REQUIRED_FILE_MISSING:{path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "v4_ca_icbp_single_ticker_coverage_remediation_manifest_v1":
        raise RuntimeError("ICBP_REMEDIATION_MANIFEST_SCHEMA_INVALID")
    if summary.get("schema_version") != "v4_ca_icbp_single_ticker_coverage_remediation_v1":
        raise RuntimeError("ICBP_REMEDIATION_SUMMARY_SCHEMA_INVALID")
    if summary.get("status") != "V4_CA_ICBP_SINGLE_TICKER_COVERAGE_REMEDIATION_COMPLETE":
        raise RuntimeError("ICBP_REMEDIATION_STATUS_INVALID")
    if summary.get("outcome_blind") is not True or manifest.get("outcome_blind") is not True:
        raise RuntimeError("ICBP_REMEDIATION_NOT_OUTCOME_BLIND")
    if summary.get("provider_calls") is not True:
        raise RuntimeError("ICBP_REMEDIATION_PROVIDER_FLAG_INVALID")
    if summary.get("source_substitution") is not False or summary.get("parser_relaxation") is not False:
        raise RuntimeError("ICBP_REMEDIATION_SOURCE_OR_PARSER_POLICY_INVALID")
    if summary.get("full_610_recrawl") is not False or summary.get("alternate_provider") is not False:
        raise RuntimeError("ICBP_REMEDIATION_SCOPE_POLICY_INVALID")
    if summary.get("target_ticker") != TARGET_TICKER:
        raise RuntimeError("ICBP_REMEDIATION_TARGET_CHANGED")
    if summary.get("parent_manifest_sha256") != EXPECTED_PARENT_MANIFEST_SHA256:
        raise RuntimeError("ICBP_REMEDIATION_PARENT_MANIFEST_CHANGED")
    if summary.get("merged_coverage_certified_tickers") != 599:
        raise RuntimeError("ICBP_REMEDIATION_CERTIFIED_COUNT_INVALID")
    if summary.get("remaining_unresolved_ticker_count") != 11:
        raise RuntimeError("ICBP_REMEDIATION_UNRESOLVED_COUNT_INVALID")
    if set(summary.get("remaining_unresolved_tickers") or []) != set(EXPECTED_OUTPUT_UNRESOLVED):
        raise RuntimeError("ICBP_REMEDIATION_UNRESOLVED_SET_INVALID")
    if sha256_file(summary_path) != manifest.get("summary_sha256"):
        raise RuntimeError("ICBP_REMEDIATION_SUMMARY_HASH_MISMATCH")

    outputs = summary.get("output_hashes") or {}
    manifest_outputs = manifest.get("output_hashes") or {}
    for logical, path in (("ticker_coverage", coverage_path), ("ksei_ca_history", history_path)):
        actual = sha256_file(path)
        if outputs.get(logical) != actual or manifest_outputs.get(logical) != actual:
            raise RuntimeError(f"ICBP_REMEDIATION_OUTPUT_HASH_MISMATCH:{logical}")

    coverage = validate_output_coverage(pd.read_csv(coverage_path))
    target = coverage[coverage["ticker"].eq(TARGET_TICKER)]
    if len(target) != 1 or not bool(target.iloc[0]["coverage_certified"]):
        raise RuntimeError("ICBP_REMEDIATION_TARGET_COVERAGE_INVALID")

    history = read_jsonl(history_path)
    target_history = [
        row for row in history if str(row.get("ticker") or "").upper().strip() == TARGET_TICKER
    ]
    if not target_history:
        raise RuntimeError("ICBP_REMEDIATION_HISTORY_MISSING")
    if any(not str(row.get("source_sha256") or "").strip() for row in target_history):
        raise RuntimeError("ICBP_REMEDIATION_HISTORY_PROVENANCE_MISSING")
    return summary, sha256_file(manifest_path)


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")

    icbp_summary, icbp_manifest_sha = verify_icbp_root(args.icbp_remediation_root)
    residual_evidence_path, residual_manifest_sha = coverage_replay.verify_document_root(
        args.residual_document_root
    )
    targeted_summary, targeted_evidence_path, targeted_manifest_sha = targeted_replay.verify_targeted_root(
        args.targeted_evidence_root
    )

    residual = pd.read_csv(residual_evidence_path, dtype=str, keep_default_na=False)
    targeted = pd.read_csv(targeted_evidence_path, dtype=str, keep_default_na=False)
    merged = pd.concat([residual, targeted], ignore_index=True, sort=False).fillna("")
    if merged.duplicated().any():
        merged = merged.drop_duplicates().reset_index(drop=True)

    outputs = icbp_summary["output_hashes"]
    frozen.PINNED = dict(frozen.PINNED)
    frozen.PINNED["ksei_manifest"] = icbp_manifest_sha
    frozen.PINNED["ksei_summary"] = sha256_file(args.icbp_remediation_root / "summary.json")
    frozen.PINNED["ksei_coverage"] = outputs["ticker_coverage"]
    frozen.PINNED["ksei_history"] = outputs["ksei_ca_history"]
    frozen.classify_event = classify_event_with_targeted_evidence

    original_build_window_ledger = frozen.build_window_ledger

    def build_window_ledger_with_policy(*inner_args, **inner_kwargs):
        frame = original_build_window_ledger(*inner_args, **inner_kwargs).copy()
        frame["policy_id"] = (
            "V4_CA_TARGETED_SCHEDULE_EVIDENCE_V1+"
            "V4_CA_ICBP_SINGLE_TICKER_COVERAGE_REMEDIATION_V1"
        )
        return frame

    frozen.build_window_ledger = build_window_ledger_with_policy

    with tempfile.TemporaryDirectory(prefix="v4_ca_icbp_continuity_") as tmp:
        merged_evidence_path = Path(tmp) / "merged_schedule_evidence.csv"
        merged.to_csv(merged_evidence_path, index=False, lineterminator="\n")
        original_argv = list(sys.argv)
        try:
            sys.argv = [
                original_argv[0],
                "--continuity-ledger", str(args.continuity_ledger),
                "--prior-event-evidence", str(args.prior_event_evidence),
                "--official-calendar", str(args.official_calendar),
                "--ksei-census-root", str(args.icbp_remediation_root),
                "--schedule-evidence", str(merged_evidence_path),
                "--output-dir", str(args.output_dir),
            ]
            result = frozen.main()
        finally:
            sys.argv = original_argv

    summary_path = args.output_dir / "summary.json"
    if not summary_path.is_file():
        raise RuntimeError("ICBP_CONTINUITY_SUMMARY_MISSING")
    continuity_summary = json.loads(summary_path.read_text(encoding="utf-8"))

    event_audit_path = args.output_dir / "event_semantics_audit.csv"
    event_audit = pd.read_csv(event_audit_path, dtype=str, keep_default_na=False)
    icbp_events = event_audit[event_audit["ticker"].eq(TARGET_TICKER)].to_dict("records")

    overlay = {
        "schema_version": "v4_ca_icbp_single_ticker_continuity_overlay_v1",
        "outcome_blind": True,
        "provider_calls_in_continuity_replay": False,
        "icbp_remediation_manifest_sha256": icbp_manifest_sha,
        "icbp_parsed_history": icbp_summary.get("parsed_history"),
        "icbp_event_semantics": icbp_events,
        "ksei_coverage_certified_tickers": icbp_summary.get("merged_coverage_certified_tickers"),
        "ksei_remaining_unresolved_tickers": icbp_summary.get("remaining_unresolved_ticker_count"),
        "residual_document_manifest_sha256": residual_manifest_sha,
        "targeted_evidence_manifest_sha256": targeted_manifest_sha,
        "targeted_exact_static_nonblocking_events": targeted_summary.get("exact_static_nonblocking_events"),
        "targeted_exact_schedule_transition_events": targeted_summary.get("exact_schedule_transition_events"),
        "targeted_unresolved_selected_events": targeted_summary.get("unresolved_selected_events"),
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
    overlay_path = args.output_dir / "icbp_single_ticker_continuity_overlay.json"
    overlay_path.write_text(json.dumps(overlay, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**overlay, "overlay_sha256": sha256_file(overlay_path)}, indent=2, sort_keys=True))
    return int(result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
