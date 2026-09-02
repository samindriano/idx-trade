"""Evidence-only Official Open cloud runner with strict ZAPI raw compatibility."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from idx_trade.official_open_cloud_archive_v1 import (
    OfficialOpenCloudArchiveError,
    build_official_open_store_from_env,
    capture_and_archive_official_open,
)
from idx_trade.official_open_evidence_v1 import OfficialOpenEvidenceError
from idx_trade.official_open_transport_compat_v2 import (
    capture_official_open_with_transport_fallback_v2,
)
from idx_trade.stockbit_stream_archive import StreamArchiveError


JAKARTA = ZoneInfo("Asia/Jakarta")


def _runner_provenance() -> dict[str, object]:
    env = os.environ
    return {
        "runner": "GITHUB_ACTIONS" if env.get("GITHUB_ACTIONS") == "true" else "LOCAL_OR_OTHER",
        "github_repository": env.get("GITHUB_REPOSITORY", ""),
        "github_sha": env.get("GITHUB_SHA", ""),
        "github_workflow": env.get("GITHUB_WORKFLOW", ""),
        "github_event_name": env.get("GITHUB_EVENT_NAME", ""),
        "github_run_id": env.get("GITHUB_RUN_ID", ""),
        "github_run_attempt": env.get("GITHUB_RUN_ATTEMPT", ""),
        "capture_code_ref": env.get("OFFICIAL_OPEN_CAPTURE_CODE_REF", ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", required=True, choices=("0902", "0912", "0922"))
    parser.add_argument("--session-date")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    args = parser.parse_args()

    session_date = args.session_date or datetime.now(JAKARTA).date().isoformat()
    try:
        result = capture_and_archive_official_open(
            session_date=session_date,
            slot=args.slot,
            store=build_official_open_store_from_env(),
            zapi_api_key=os.environ.get("ZAPI_API_KEY") or None,
            timeout_seconds=args.timeout_seconds,
            capture_fn=capture_official_open_with_transport_fallback_v2,
            runner_provenance=_runner_provenance(),
        )
        result.update(
            {
                "model_accessed": False,
                "outcome_accessed": False,
                "paper_state_mutated": False,
                "forward_counter_mutated": False,
                "execution_admitted": False,
            }
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (
        OfficialOpenCloudArchiveError,
        OfficialOpenEvidenceError,
        StreamArchiveError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
    ) as exc:
        print(
            json.dumps(
                {
                    "status": "BLOCKED_OR_FAILED",
                    "detail": str(exc),
                    "session_date": session_date,
                    "slot": args.slot,
                    "model_accessed": False,
                    "outcome_accessed": False,
                    "paper_state_mutated": False,
                    "forward_counter_mutated": False,
                    "execution_admitted": False,
                },
                sort_keys=True,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
