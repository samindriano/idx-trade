"""Official Open cloud runner with strict transport and trigger provenance."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from idx_trade.official_open_capture_timing_v1 import (
    OfficialOpenCaptureTimingError,
    require_runner_start_in_slot_window,
    validate_source_manifest_timing,
)
from idx_trade.official_open_cloud_archive_v1 import (
    OfficialOpenCloudArchiveError,
    build_official_open_store_from_env,
    capture_and_archive_official_open,
)
from idx_trade.official_open_evidence_v1 import OfficialOpenEvidenceError
from idx_trade.official_open_scheduler_attestation_v1 import (
    OfficialOpenSchedulerAttestationError,
    trusted_runner_provenance,
)
from idx_trade.official_open_transport_compat_v2 import (
    capture_official_open_with_transport_fallback_v2,
)
from idx_trade.stockbit_stream_archive import StreamArchiveError


JAKARTA = ZoneInfo("Asia/Jakarta")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", required=True, choices=("0902", "0912", "0922"))
    parser.add_argument("--session-date")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    args = parser.parse_args()

    session_date = args.session_date or datetime.now(JAKARTA).date().isoformat()
    try:
        # Provenance and runner-start timing are proven before the store is
        # constructed and before any provider call. A delayed or arbitrary
        # workflow_dispatch therefore cannot occupy the deterministic slot.
        provenance = trusted_runner_provenance(
            env=os.environ,
            session_date=session_date,
            slot=args.slot,
        )
        require_runner_start_in_slot_window(
            session_date=session_date,
            slot=args.slot,
        )

        # Provider capture still occurs in a temporary local bundle. Validate
        # the source timestamp before the archive layer performs any immutable
        # artifact or slot-manifest write, covering a capture that crosses the
        # cutoff after an otherwise timely runner start.
        def timely_capture(capture_session: str, **kwargs: object):
            manifest_path = capture_official_open_with_transport_fallback_v2(
                capture_session,
                **kwargs,
            )
            return validate_source_manifest_timing(
                manifest_path=manifest_path,
                session_date=session_date,
                slot=args.slot,
            )

        result = capture_and_archive_official_open(
            session_date=session_date,
            slot=args.slot,
            store=build_official_open_store_from_env(),
            zapi_api_key=os.environ.get("ZAPI_API_KEY") or None,
            timeout_seconds=args.timeout_seconds,
            capture_fn=timely_capture,
            runner_provenance=provenance,
        )
        result.update(
            {
                "trigger_authority": provenance.get("trigger_authority"),
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
        OfficialOpenCaptureTimingError,
        OfficialOpenCloudArchiveError,
        OfficialOpenEvidenceError,
        OfficialOpenSchedulerAttestationError,
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
