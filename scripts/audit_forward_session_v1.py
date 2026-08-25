from __future__ import annotations

import argparse
import json
from pathlib import Path

from idx_trade.forward_session_audit_v1 import audit_session, summarize_ledgers, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only outcome-blind IDX forward session audit")
    parser.add_argument("--session-date", required=True)
    parser.add_argument("--forward-monitoring-root")
    parser.add_argument("--e2e-runtime-root")
    parser.add_argument("--calendar-metadata")
    parser.add_argument("--runtime-identity")
    parser.add_argument("--stockbit-capture")
    parser.add_argument("--ca-dividend")
    parser.add_argument("--scheduler-metadata")
    parser.add_argument("--prepared-metadata")
    parser.add_argument("--schedule-binding-metadata")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument("--reported-at-utc", default="2026-01-01T00:00:00+00:00")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    ledger = audit_session(
        args.session_date,
        forward_monitoring_root=args.forward_monitoring_root,
        e2e_runtime_root=args.e2e_runtime_root,
        calendar_metadata=args.calendar_metadata,
        runtime_identity=args.runtime_identity,
        stockbit_capture=args.stockbit_capture,
        ca_dividend=args.ca_dividend,
        scheduler_metadata=args.scheduler_metadata,
        prepared_metadata=args.prepared_metadata,
        schedule_binding_metadata=args.schedule_binding_metadata,
        reported_at_utc=args.reported_at_utc,
    )
    output, output_sha = write_json(args.output, ledger)
    summary_path = args.summary_output or output.with_name("session_audit_summary.json")
    summary, summary_sha = write_json(summary_path, summarize_ledgers([ledger]))
    print(json.dumps({
        "status": "AUDIT_COMPLETE",
        "session_date": ledger["session_date"],
        "overall_status": ledger["overall_status"],
        "ledger_path": str(output),
        "ledger_sha256": output_sha,
        "summary_path": str(summary),
        "summary_sha256": summary_sha,
        "provider_capture_triggered": False,
        "protected_outcomes_accessed": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
