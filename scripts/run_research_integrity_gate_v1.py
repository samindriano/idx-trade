from __future__ import annotations

import argparse
import json
from pathlib import Path

from idx_trade.research_integrity_gate_v1 import (
    IntegrityCheck,
    IntegrityStage,
    IntegrityStatus,
    evaluate_integrity_gate,
    load_gate_profile,
    required_checks_for_stage,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate evidence checks into the fail-closed Research Integrity Gate V1."
    )
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--stage", required=True, choices=[value.value for value in IntegrityStage])
    parser.add_argument("--checks-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def _load_checks(path: Path) -> list[IntegrityCheck]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("checks") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("checks-json must be a list or an object containing a 'checks' list")

    checks: list[IntegrityCheck] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Each check must be an object")
        evidence = row.get("evidence", {})
        if not isinstance(evidence, dict):
            raise ValueError(f"Check evidence must be an object: {row.get('check_id')}")
        checks.append(
            IntegrityCheck(
                check_id=str(row["check_id"]),
                category=str(row["category"]),
                status=IntegrityStatus(str(row["status"])),
                summary=str(row.get("summary", "")),
                required=bool(row.get("required", True)),
                evidence=evidence,
            )
        )
    return checks


def main() -> int:
    args = _parse_args()
    profile = load_gate_profile(args.profile)
    stage = IntegrityStage(args.stage)
    checks = _load_checks(args.checks_json)
    required = required_checks_for_stage(profile, stage)
    report = evaluate_integrity_gate(stage, checks, required_check_ids=required)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "stage": stage.value,
        "passed": report.passed,
        "blocking_check_ids": list(report.blocking_check_ids),
        "output": str(args.output),
    }, sort_keys=True))
    return 0 if report.passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
