"""Verify KSEI schedule-acquisition provenance before the final V4 CA gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import runpy
import sys


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--continuity-ledger", type=Path, required=True)
    parser.add_argument("--prior-event-evidence", type=Path, required=True)
    parser.add_argument("--official-calendar", type=Path, required=True)
    parser.add_argument("--ksei-census-root", type=Path, required=True)
    parser.add_argument("--schedule-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def verify_schedule_root(root: Path) -> Path:
    manifest_path = root / "MANIFEST.json"
    summary_path = root / "summary.json"
    evidence_path = root / "schedule_evidence.csv"
    for path in (manifest_path, summary_path, evidence_path):
        if not path.is_file():
            raise RuntimeError(f"SCHEDULE_ROOT_REQUIRED_FILE_MISSING:{path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "v4_ca_schedule_acquisition_manifest_v1":
        raise RuntimeError("SCHEDULE_MANIFEST_SCHEMA_MISMATCH")
    if summary.get("schema_version") != "v4_ca_schedule_acquisition_v1":
        raise RuntimeError("SCHEDULE_SUMMARY_SCHEMA_MISMATCH")
    if manifest.get("summary_sha256") != sha256(summary_path):
        raise RuntimeError("SCHEDULE_SUMMARY_SHA_MISMATCH")
    if summary.get("output_hashes", {}).get("schedule_evidence") != sha256(evidence_path):
        raise RuntimeError("SCHEDULE_EVIDENCE_SHA_MISMATCH")
    required_flags = {
        "outcome_blind": True,
        "provider_calls": True,
        "source_substitution": False,
        "target_or_rank_materialized": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
    }
    for key, expected in required_flags.items():
        if summary.get(key) is not expected:
            raise RuntimeError(f"SCHEDULE_SUMMARY_FLAG_MISMATCH:{key}")
    if summary.get("status") != "V4_CA_TARGETED_KSEI_SCHEDULE_ACQUISITION_COMPLETE":
        raise RuntimeError("SCHEDULE_ACQUISITION_STATUS_MISMATCH")
    return evidence_path


def main() -> int:
    args = parse_args()
    evidence = verify_schedule_root(args.schedule_root)
    target = Path(__file__).with_name("run_v4_ca_event_window_support.py")
    sys.argv = [
        str(target),
        "--continuity-ledger", str(args.continuity_ledger),
        "--prior-event-evidence", str(args.prior_event_evidence),
        "--official-calendar", str(args.official_calendar),
        "--ksei-census-root", str(args.ksei_census_root),
        "--schedule-evidence", str(evidence),
        "--output-dir", str(args.output_dir),
    ]
    runpy.run_path(str(target), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
