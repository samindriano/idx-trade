"""Verify residual-document evidence then run one offline V4 continuity replay."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import run_v4_ca_event_window_support as frozen

from idx_trade.v4_ca_residual_document_semantics import (
    POLICY_ID,
    classify_event_with_residual_document_evidence,
)


GOOD_KSEI_MANIFEST_SHA = "7cc3ac4d409c3e15c6aa566b63bedab4268562fd4914d1af198ab29657dba25a"
BAD_KSEI_MANIFEST_SHA = "7cc3ac4d409c3e15c6aa566b63bedab4268562fd4914d1af198ab29657dba25"
EXPECTED_DOCUMENT_STATUS = "V4_CA_RESIDUAL_DOCUMENT_SEMANTICS_COMPLETE"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_document_root(root: Path) -> tuple[Path, dict, str]:
    manifest_path = root / "MANIFEST.json"
    summary_path = root / "summary.json"
    evidence_path = root / "residual_event_document_evidence.csv"
    for path in (manifest_path, summary_path, evidence_path):
        if not path.is_file():
            raise RuntimeError(f"RESIDUAL_DOCUMENT_REQUIRED_FILE_MISSING:{path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if manifest.get("status") != EXPECTED_DOCUMENT_STATUS:
        raise RuntimeError(f"RESIDUAL_DOCUMENT_MANIFEST_STATUS_INVALID:{manifest.get('status')}")
    if summary.get("status") != EXPECTED_DOCUMENT_STATUS:
        raise RuntimeError(f"RESIDUAL_DOCUMENT_SUMMARY_STATUS_INVALID:{summary.get('status')}")
    for obj, label in ((manifest, "MANIFEST"), (summary, "SUMMARY")):
        if obj.get("outcome_blind") is not True:
            raise RuntimeError(f"RESIDUAL_DOCUMENT_{label}_NOT_OUTCOME_BLIND")
        if obj.get("provider_calls") is not False:
            raise RuntimeError(f"RESIDUAL_DOCUMENT_{label}_PROVIDER_FLAG_INVALID")
    if summary.get("source_substitution") is not False:
        raise RuntimeError("RESIDUAL_DOCUMENT_SOURCE_SUBSTITUTION_INVALID")
    if int(summary.get("residual_events") or -1) != 61:
        raise RuntimeError("RESIDUAL_DOCUMENT_EVENT_COUNT_INVALID")
    if sha256(summary_path) != manifest.get("summary_sha256"):
        raise RuntimeError("RESIDUAL_DOCUMENT_SUMMARY_HASH_MISMATCH")
    expected_evidence = (manifest.get("output_hashes") or {}).get("residual_event_document_evidence")
    actual_evidence = sha256(evidence_path)
    if not expected_evidence or actual_evidence != expected_evidence:
        raise RuntimeError("RESIDUAL_DOCUMENT_EVIDENCE_HASH_MISMATCH")
    if (summary.get("output_hashes") or {}).get("residual_event_document_evidence") != actual_evidence:
        raise RuntimeError("RESIDUAL_DOCUMENT_SUMMARY_EVIDENCE_HASH_MISMATCH")
    return evidence_path, summary, sha256(manifest_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--continuity-ledger", type=Path, required=True)
    parser.add_argument("--prior-event-evidence", type=Path, required=True)
    parser.add_argument("--ksei-census-root", type=Path, required=True)
    parser.add_argument("--official-calendar", type=Path, required=True)
    parser.add_argument("--document-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    evidence_path, document_summary, document_manifest_sha = verify_document_root(args.document_root)

    if frozen.PINNED.get("ksei_manifest") not in {BAD_KSEI_MANIFEST_SHA, GOOD_KSEI_MANIFEST_SHA}:
        raise RuntimeError("V4_CA_RESIDUAL_DOCUMENT_UNEXPECTED_PARENT_KSEI_PIN")
    frozen.PINNED = dict(frozen.PINNED)
    frozen.PINNED["ksei_manifest"] = GOOD_KSEI_MANIFEST_SHA
    frozen.classify_event = classify_event_with_residual_document_evidence

    original_build_window_ledger = frozen.build_window_ledger

    def build_window_ledger_with_policy(*inner_args, **inner_kwargs):
        frame = original_build_window_ledger(*inner_args, **inner_kwargs).copy()
        frame["policy_id"] = POLICY_ID
        return frame

    frozen.build_window_ledger = build_window_ledger_with_policy
    original_argv = list(sys.argv)
    try:
        sys.argv = [
            original_argv[0],
            "--continuity-ledger", str(args.continuity_ledger),
            "--prior-event-evidence", str(args.prior_event_evidence),
            "--official-calendar", str(args.official_calendar),
            "--ksei-census-root", str(args.ksei_census_root),
            "--schedule-evidence", str(evidence_path),
            "--output-dir", str(args.output_dir),
        ]
        result = frozen.main()
    finally:
        sys.argv = original_argv

    summary_path = args.output_dir / "summary.json"
    if not summary_path.is_file():
        raise RuntimeError("RESIDUAL_DOCUMENT_CONTINUITY_SUMMARY_MISSING")
    continuity_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    overlay = {
        "schema_version": "v4_ca_residual_document_continuity_overlay_v1",
        "policy_id": POLICY_ID,
        "outcome_blind": True,
        "provider_calls": False,
        "document_manifest_sha256": document_manifest_sha,
        "document_evidence_sha256": sha256(evidence_path),
        "document_exact_nonblocking_events": int(document_summary.get("exact_nonblocking_events") or 0),
        "document_exact_transition_events": int(document_summary.get("exact_transition_events") or 0),
        "document_conflict_events": int(document_summary.get("conflict_events") or 0),
        "document_unresolved_events": int(document_summary.get("unresolved_events") or 0),
        "continuity_summary_sha256": sha256(summary_path),
        "continuity_verdict": continuity_summary.get("verdict"),
        "corporate_action_continuity_certified": continuity_summary.get("corporate_action_continuity_certified"),
        "per_date": continuity_summary.get("per_date"),
    }
    overlay_path = args.output_dir / "residual_document_continuity_overlay.json"
    overlay_path.write_text(json.dumps(overlay, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**overlay, "overlay_sha256": sha256(overlay_path)}, indent=2, sort_keys=True))
    return int(result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
