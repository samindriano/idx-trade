"""Run the outcome-blind V4 Voluntary Conversion forensic replay.

No provider/network access is performed.  The runner uses the immutable KSEI
history census plus already-promoted parent/remediation audit artifacts.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from idx_trade.v4_ca_voluntary_conversion_forensic import (
    VERDICT_INCONSISTENT,
    compare_per_date_outputs,
    replay_parent_relevant_events,
)


PINNED = {
    "ksei_history": "3ea2f0a160300dd4d74c40281dbcbf680e03accc565487cf00b190630471c08d",
    "official_calendar": "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a",
    "parent_event_audit": "ba08fbdab5b72b377888320163ba8b893e7d1a19f69384ba7be0fdac5ca33908",
    "remediation_event_audit": "a2fe0206189916a796cda170e819053dd7147bf988ceed27f278081684ca4f1a",
    "parent_per_date": "eefd6cbeed7381b01935a95b777cd88cfa4e073c0abc7d318005c2bc381fd85d",
    "remediation_per_date": "55de6a8dc981bc2b16be96e3c02d767c6655b7025c402dbd50aa5d95aa65cbb9",
}
EXPECTED_PARENT_EVENTS = 136
EXPECTED_REMEDIATION_EVENTS = 102
EXPECTED_DATES = 600


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise RuntimeError(f"REQUIRED_INPUT_MISSING:{label}:{path}")
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"PINNED_INPUT_HASH_MISMATCH:{label}:{actual}")
    return actual


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ksei-history", type=Path, required=True)
    parser.add_argument("--official-calendar", type=Path, required=True)
    parser.add_argument("--parent-event-audit", type=Path, required=True)
    parser.add_argument("--remediation-event-audit", type=Path, required=True)
    parser.add_argument("--parent-per-date", type=Path, required=True)
    parser.add_argument("--remediation-per-date", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")

    input_hashes = {
        "ksei_history": verify(args.ksei_history, PINNED["ksei_history"], "ksei_history"),
        "official_calendar": verify(
            args.official_calendar, PINNED["official_calendar"], "official_calendar"
        ),
        "parent_event_audit": verify(
            args.parent_event_audit, PINNED["parent_event_audit"], "parent_event_audit"
        ),
        "remediation_event_audit": verify(
            args.remediation_event_audit,
            PINNED["remediation_event_audit"],
            "remediation_event_audit",
        ),
        "parent_per_date": verify(
            args.parent_per_date, PINNED["parent_per_date"], "parent_per_date"
        ),
        "remediation_per_date": verify(
            args.remediation_per_date,
            PINNED["remediation_per_date"],
            "remediation_per_date",
        ),
    }

    history = read_jsonl(args.ksei_history)
    calendar = pd.read_csv(args.official_calendar)
    if "date" not in calendar.columns:
        raise RuntimeError("OFFICIAL_CALENDAR_DATE_COLUMN_MISSING")
    sessions = pd.to_datetime(calendar["date"], errors="raise").dt.tz_localize(None).dt.normalize().tolist()

    parent_audit = pd.read_csv(args.parent_event_audit)
    remediation_audit = pd.read_csv(args.remediation_event_audit)
    if len(parent_audit) != EXPECTED_PARENT_EVENTS:
        raise RuntimeError(f"PARENT_EVENT_COUNT_CHANGED:{len(parent_audit)}")
    if len(remediation_audit) != EXPECTED_REMEDIATION_EVENTS:
        raise RuntimeError(f"REMEDIATION_EVENT_COUNT_CHANGED:{len(remediation_audit)}")

    side, voluntary, diff, classifier_summary = replay_parent_relevant_events(
        history_rows=history,
        official_sessions=sessions,
        parent_audit=parent_audit,
        remediation_audit=remediation_audit,
    )

    parent_per_date = pd.read_csv(args.parent_per_date)
    remediation_per_date = pd.read_csv(args.remediation_per_date)
    if len(parent_per_date) != EXPECTED_DATES or len(remediation_per_date) != EXPECTED_DATES:
        raise RuntimeError("PER_DATE_COUNT_CHANGED")
    per_date_diff, per_date_summary = compare_per_date_outputs(
        parent_per_date,
        remediation_per_date,
        reclassified_count=int(classifier_summary["reclassified_to_nonblocking_count"]),
    )

    verdict = classifier_summary["verdict"]
    if per_date_summary.get("verdict") == VERDICT_INCONSISTENT:
        verdict = VERDICT_INCONSISTENT

    # Hard fail-closed consistency requirements for the actual observed delta.
    if classifier_summary["removed_event_count"] != (
        classifier_summary["parent_relevant_event_count"]
        - classifier_summary["remediation_relevant_event_count"]
    ):
        verdict = VERDICT_INCONSISTENT
    if classifier_summary["removed_event_count"] and not (
        classifier_summary["removed_ids_equal_reclassified_nonblocking_ids"]
        and classifier_summary["all_removed_ids_are_strict_voluntary_cash"]
        and classifier_summary["added_ids_empty"]
    ):
        verdict = VERDICT_INCONSISTENT

    args.output_dir.mkdir(parents=True)
    side_path = args.output_dir / "classifier_side_by_side.csv"
    voluntary_path = args.output_dir / "voluntary_conversion_ratio_dump.csv"
    diff_path = args.output_dir / "event_set_diff.csv"
    per_date_path = args.output_dir / "continuity_per_date_diff.csv"
    side.to_csv(side_path, index=False, lineterminator="\n")
    voluntary.to_csv(voluntary_path, index=False, lineterminator="\n")
    diff.to_csv(diff_path, index=False, lineterminator="\n")
    per_date_diff.to_csv(per_date_path, index=False, lineterminator="\n")

    summary = {
        "schema_version": "v4_ca_voluntary_conversion_forensic_replay_v1",
        "verdict": verdict,
        "outcome_blind": True,
        "provider_calls": 0,
        "schedule_acquisition": False,
        "target_or_rank_materialized": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "classifier_replay": classifier_summary,
        "continuity_comparison": per_date_summary,
        "input_hashes": input_hashes,
    }
    output_hashes = {
        "classifier_side_by_side": sha256_file(side_path),
        "voluntary_conversion_ratio_dump": sha256_file(voluntary_path),
        "event_set_diff": sha256_file(diff_path),
        "continuity_per_date_diff": sha256_file(per_date_path),
    }
    summary["output_hashes"] = output_hashes
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest = {
        "schema_version": "v4_ca_voluntary_conversion_forensic_replay_manifest_v1",
        "created_at_utc": utc_now(),
        "verdict": verdict,
        "outcome_blind": True,
        "input_hashes": input_hashes,
        "summary_sha256": sha256_file(summary_path),
        "output_hashes": output_hashes,
    }
    manifest_path = args.output_dir / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                **summary,
                "manifest_sha256": sha256_file(manifest_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if verdict != VERDICT_INCONSISTENT else 2


if __name__ == "__main__":
    raise SystemExit(main())
