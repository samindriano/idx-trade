"""Final provenance-verified V4 CA gate with the preflight SHA pin correction."""

from __future__ import annotations

from pathlib import Path
import sys

import run_v4_ca_event_window_support_with_schedule as final_wrapper
from v4_ca_input_pin_remediation import execute_remediated_script


def main() -> int:
    args = final_wrapper.parse_args()
    evidence = final_wrapper.verify_schedule_root(args.schedule_root)
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
    execute_remediated_script(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
