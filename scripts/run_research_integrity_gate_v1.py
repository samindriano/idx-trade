from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

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
        if not isinstance(row.get("check_id"), str) or not row["check_id"]:
            raise ValueError("Each check must have a non-empty string check_id")
        if not isinstance(row.get("category"), str) or not row["category"]:
            raise ValueError(f"Each check must have a non-empty category: {row.get('check_id')}")
        if not isinstance(row.get("status"), str):
            raise ValueError(f"Each check must have a string status: {row.get('check_id')}")
        evidence = row.get("evidence", {})
        if not isinstance(evidence, dict):
            raise ValueError(f"Check evidence must be an object: {row.get('check_id')}")
        required = row.get("required", True)
        if not isinstance(required, bool):
            raise ValueError(f"Check required flag must be boolean: {row.get('check_id')}")
        checks.append(
            IntegrityCheck(
                check_id=row["check_id"],
                category=row["category"],
                status=IntegrityStatus(str(row["status"])),
                summary=str(row.get("summary", "")),
                required=required,
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

    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite existing gate report: {args.output}")
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
