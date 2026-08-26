from __future__ import annotations

import argparse
from datetime import date, datetime, time
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.e2e_paper_cloud_runtime_v1 import (  # noqa: E402
    CloudInputBundle,
    ConditionalS3Store,
    load_schedule_from_bundle,
)
from idx_trade.stockbit_intraday_cloud_archive import (  # noqa: E402
    SLOTS,
    StockbitIntradayCloudArchive,
    build_intraday_store_from_env,
)
from idx_trade.stockbit_intraday_cloud_runner import (  # noqa: E402
    materialize_eod_context_from_e2e,
    run_cloud_slot,
)
from idx_trade.stockbit_intraday_runtime import JAKARTA, request_chart  # noqa: E402


SLOT_MINIMUMS = {
    "1830": time(18, 30),
    "1930": time(19, 30),
    "2030": time(20, 30),
}


def _now() -> datetime:
    return datetime.now(tz=JAKARTA)


def _git_head() -> str:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip().lower()


def _require_current_session(value: str | None, *, now: datetime) -> date:
    current = now.astimezone(JAKARTA).date()
    requested = date.fromisoformat(value) if value else current
    if requested != current:
        raise RuntimeError("STOCKBIT_INTRADAY_RETROACTIVE_SESSION_FORBIDDEN")
    return requested


def _validate_slot_clock(slot: str, *, now: datetime) -> None:
    local = now.astimezone(JAKARTA)
    minimum = SLOT_MINIMUMS[slot]
    if local.time().replace(tzinfo=None) < minimum:
        raise RuntimeError(f"STOCKBIT_INTRADAY_SLOT_TOO_EARLY:{slot}")


def _verify_code_pin() -> str:
    actual = _git_head()
    expected = os.getenv("STOCKBIT_INTRADAY_EXPECTED_IMPLEMENTATION_REF", "").strip().lower()
    if expected and actual != expected:
        raise RuntimeError("STOCKBIT_INTRADAY_IMPLEMENTATION_REF_MISMATCH")
    return actual


def _e2e_store_from_intraday_env() -> ConditionalS3Store:
    env = os.environ
    return ConditionalS3Store(
        env.get("STOCKBIT_INTRADAY_S3_ENDPOINT", "").strip(),
        env.get("STOCKBIT_INTRADAY_S3_BUCKET", "").strip(),
        env.get("STOCKBIT_INTRADAY_S3_ACCESS_KEY_ID", "").strip(),
        env.get("STOCKBIT_INTRADAY_S3_SECRET_ACCESS_KEY", "").strip(),
        env.get("STOCKBIT_INTRADAY_E2E_PREFIX", "e2e-paper-v1").strip("/"),
    )


def _result_payload(archive: StockbitIntradayCloudArchive, commit) -> dict[str, Any]:
    raw = archive.store.read(commit.result_key)
    if raw is None:
        raise RuntimeError("STOCKBIT_INTRADAY_COMMITTED_RESULT_MISSING")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("STOCKBIT_INTRADAY_COMMITTED_RESULT_INVALID")
    return value


def run_once(*, slot: str, session_date: str | None = None) -> dict[str, Any]:
    now = _now()
    session = _require_current_session(session_date, now=now)
    _validate_slot_clock(slot, now=now)
    code_ref = _verify_code_pin()

    intraday_store = build_intraday_store_from_env()
    intraday_archive = StockbitIntradayCloudArchive(intraday_store)
    e2e_store = _e2e_store_from_intraday_env()

    with tempfile.TemporaryDirectory(prefix="idx-trade-stockbit-intraday-") as raw_tmp:
        tmp = Path(raw_tmp)
        bundle = CloudInputBundle.load(
            e2e_store,
            os.getenv("STOCKBIT_INTRADAY_E2E_INPUT_MANIFEST_KEY", "inputs/manifest.json"),
        )
        roles = bundle.materialize(e2e_store, tmp / "inputs")
        schedule = load_schedule_from_bundle(bundle, roles)
        if session.isoformat() < schedule.coverage_start or session.isoformat() > schedule.coverage_end:
            raise RuntimeError("STOCKBIT_INTRADAY_SESSION_OUTSIDE_SCHEDULE_COVERAGE")

        context = None
        if session.isoformat() in schedule.session_dates:
            context = materialize_eod_context_from_e2e(
                store=e2e_store,
                session_date=session,
                target_root=tmp / "e2e-post-eod",
            )

        http = requests.Session()
        api_key = os.getenv("ZAPI_API_KEY", "").strip()

        def requester(ticker: str):
            if not api_key:
                raise RuntimeError("ZAPI_API_KEY_REQUIRED_FOR_STOCKBIT_INTRADAY_PROVIDER_CALL")
            return request_chart(http, ticker, api_key)

        commit = run_cloud_slot(
            expected_date=session,
            slot=slot,
            now=now,
            schedule=schedule,
            context=context,
            archive=intraday_archive,
            journal_root=tmp / "journal",
            requester=requester,
            code_identity={
                "repo": "samindriano/idx-trade",
                "commit": code_ref,
            },
        )
        result = _result_payload(intraday_archive, commit)
        return {
            "status": "COMMITTED_OR_VERIFIED",
            "session_date": commit.session_date,
            "slot": commit.slot,
            "cycle_status": commit.status,
            "commit_sha256": commit.commit_sha256,
            "snapshot_sha256": commit.snapshot_sha256,
            "result_sha256": commit.result_sha256,
            "provider_calls_attempted": result.get("provider_calls_attempted"),
            "session_manifest_sha256": result.get("session_manifest_sha256"),
            "outcome_accessed": False,
            "retroactive_capture_used": False,
            "synthetic_fill_used": False,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one restart-safe Stockbit Intraday cloud slot")
    parser.add_argument("--slot", choices=SLOTS, required=True)
    parser.add_argument("--session-date", default="")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "mode": "DRY_RUN",
                    "slot": args.slot,
                    "session_date": args.session_date or "CURRENT_ASIA_JAKARTA_DATE",
                    "storage_prefix": "stockbit-intraday-v1",
                    "e2e_source_prefix": "e2e-paper-v1",
                    "provider_calls": 0,
                    "r2_calls": 0,
                    "retroactive_capture_authorized": False,
                    "synthetic_fill_authorized": False,
                    "outcome_access_authorized": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    result = run_once(slot=args.slot, session_date=args.session_date or None)
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
