from __future__ import annotations

import argparse
from datetime import date, datetime
import json
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.stockbit_intraday_e2e_bridge import (  # noqa: E402
    ACCEPTED_E2E_IMPLEMENTATION_SHA,
    materialize_accepted_e2e_context,
    validate_accepted_e2e_checkout,
)
from idx_trade.stockbit_intraday_runtime import JAKARTA  # noqa: E402


def _current_session(value: str | None) -> date:
    current = datetime.now(tz=JAKARTA).date()
    requested = date.fromisoformat(value) if value else current
    if requested != current:
        raise RuntimeError("STOCKBIT_INTRADAY_PREFLIGHT_RETROACTIVE_DATE_FORBIDDEN")
    return requested


def _accepted_root() -> Path:
    raw = os.getenv("STOCKBIT_INTRADAY_ACCEPTED_E2E_ROOT", "").strip()
    if not raw:
        raise RuntimeError("STOCKBIT_INTRADAY_ACCEPTED_E2E_ROOT_REQUIRED")
    return validate_accepted_e2e_checkout(raw)


def run_preflight(*, session_date: str | None = None) -> dict[str, object]:
    session = _current_session(session_date)
    accepted_root = _accepted_root()
    import tempfile

    with tempfile.TemporaryDirectory(prefix="idx-trade-stockbit-intraday-preflight-") as raw_tmp:
        materialized = materialize_accepted_e2e_context(
            accepted_runtime_root=accepted_root,
            output_root=Path(raw_tmp) / "accepted-e2e-readback",
            session_date=session,
        )
        schedule = materialized.schedule
        scheduled = session.isoformat() in schedule.session_dates
        eod = materialized.eod
        status = "READ_ONLY_PREFLIGHT_PASS"
        if scheduled and eod is None:
            status = "READ_ONLY_PREFLIGHT_PASS_WAITING_CANONICAL_EOD"

        decision_counts: dict[str, int] | None = None
        universe_rows: int | None = None
        eod_manifest_sha256: str | None = None
        if eod is not None:
            universe_rows = len(eod.universe)
            decision_counts = {
                str(key): int(value)
                for key, value in eod.gate.decisions["gate_decision"].astype(str).value_counts().to_dict().items()
            }
            eod_manifest_sha256 = eod.eod_manifest_sha256

        return {
            "status": status,
            "session_date": session.isoformat(),
            "accepted_e2e_runtime_sha": ACCEPTED_E2E_IMPLEMENTATION_SHA,
            "input_manifest_sha256": materialized.input_manifest_sha256,
            "schedule_attestation_sha256": schedule.attestation_sha256,
            "schedule_coverage_start": schedule.coverage_start,
            "schedule_coverage_end": schedule.coverage_end,
            "scheduled_session": scheduled,
            "post_eod_commit_sha256": materialized.post_eod_commit_sha256,
            "eod_available": eod is not None,
            "eod_manifest_sha256": eod_manifest_sha256,
            "universe_rows": universe_rows,
            "gate_decision_counts": decision_counts,
            "provider_calls": 0,
            "r2_writes": 0,
            "production_intraday_prefix_written": False,
            "outcome_accessed": False,
            "retroactive_capture_used": False,
            "synthetic_fill_used": False,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only preflight for the Stockbit Intraday cloud migration bridge"
    )
    parser.add_argument("--session-date", default="")
    parser.add_argument("--checkout-only", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.checkout_only:
        root = _accepted_root()
        print(
            json.dumps(
                {
                    "status": "ACCEPTED_E2E_CHECKOUT_PIN_PASS",
                    "accepted_e2e_runtime_sha": ACCEPTED_E2E_IMPLEMENTATION_SHA,
                    "accepted_e2e_root": str(root),
                    "provider_calls": 0,
                    "r2_reads": 0,
                    "r2_writes": 0,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    print(json.dumps(run_preflight(session_date=args.session_date or None), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
