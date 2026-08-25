"""Report one forward session's safe artifact health without opening outcomes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from idx_trade.forward_evidence_health_v1 import (
    build_operational_summary,
    discover_session_artifacts,
    evaluate_session,
    write_health_report,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-date", required=True)
    parser.add_argument("--forward-monitoring-root", required=True)
    parser.add_argument("--e2e-runtime-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--reported-at-utc")
    parser.add_argument("--stockbit-run-summary")
    parser.add_argument("--current-forward-counter", default="NOT_READ")
    parser.add_argument("--next-scheduled-action", default="NEXT_GENUINE_SCHEDULED_SESSION")
    args = parser.parse_args()
    artifacts = discover_session_artifacts(
        forward_monitoring_root=args.forward_monitoring_root,
        e2e_runtime_root=args.e2e_runtime_root,
        session_date=args.session_date,
    )
    report = evaluate_session(
        args.session_date,
        artifacts,
        reported_at_utc=args.reported_at_utc,
    )
    stockbit_status = "NOT_READ"
    if args.stockbit_run_summary:
        try:
            stockbit = json.loads(Path(args.stockbit_run_summary).read_text(encoding="utf-8"))
            if not isinstance(stockbit, dict) or stockbit.get("expected_date") != args.session_date:
                stockbit_status = "PROVENANCE_INVALID"
            elif stockbit.get("complete") is True and stockbit.get("shadow_certification_eligible") is True:
                stockbit_status = "COMPLETE_SHADOW"
            else:
                stockbit_status = "FAIL_CLOSED_EXTERNAL"
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError):
            stockbit_status = "PROVENANCE_INVALID"
    report["operational_summary"] = build_operational_summary(
        report,
        stockbit_last_status=stockbit_status,
        current_forward_counter=args.current_forward_counter,
        next_scheduled_action=args.next_scheduled_action,
    )
    path, sha256 = write_health_report(args.output, report)
    print(json.dumps({"output": str(path), "sha256": sha256, **report}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
