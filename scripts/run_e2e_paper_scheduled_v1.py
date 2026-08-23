"""Run the E2E PAPER controller from one immutable external runtime config."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from idx_trade.e2e_paper_operational_controller_v1 import run_operational_cycle  # noqa: E402
from idx_trade.e2e_paper_runtime_config_v1 import (  # noqa: E402
    E2ERuntimeConfigError,
    load_runtime_config,
)


_NON_ERROR_STATUSES = {
    "ALREADY_COMPLETE",
    "EXECUTION_COMPLETE",
    "POST_EOD_PREPARED",
    "PREOPEN_CA_READY",
    "PREOPEN_CA_REUSED",
    "WEEKEND_OR_HOLIDAY_NOOP",
    "WAITING_PREOPEN_WINDOW",
    "WAITING_PREPARED_EXECUTION",
    "WAITING_PREOPEN_CA_CAPTURE",
    "WAITING_OFFICIAL_OPEN",
    "WAITING_UPSTREAM_EOD_SCORE",
    "PREOPEN_WINDOW_MISSED_NO_EXECUTION",
}


def scheduler_exit_code(status: str) -> int:
    return 0 if status in _NON_ERROR_STATUSES else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--config-sha256")
    args = parser.parse_args()
    try:
        loaded = load_runtime_config(args.runtime_root, expected_sha256=args.config_sha256)
        result = run_operational_cycle(loaded.controller)
    except E2ERuntimeConfigError as exc:
        print(json.dumps({"controller_status": "WAITING_OPERATIONAL_CONFIGURATION", "reason": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True, default=str))
    return scheduler_exit_code(str(result.get("controller_status") or "FAIL_CLOSED"))


if __name__ == "__main__":
    raise SystemExit(main())
