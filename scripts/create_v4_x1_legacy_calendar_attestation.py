from __future__ import annotations

import argparse
import json
from pathlib import Path

from idx_trade.canonical_eod_calendar_parent_attestation import (
    ACCEPTED_BRIDGE_CALENDAR_SHA256,
    ATTESTATION_FILENAME,
    ATTESTATION_NAMESPACE,
    _find_matching_files,
    audit_canonical_eod_calendar_parent,
    create_canonical_eod_calendar_parent_attestation,
    verify_canonical_eod_calendar_parent_attestation,
)
from idx_trade.provenance import sha256_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Create one immutable legacy EOD calendar-parent attestation for V4-X1 automation")
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--session", required=True)
    args = parser.parse_args()

    runtime = args.runtime_root.expanduser().resolve()
    matches = _find_matching_files(runtime, ACCEPTED_BRIDGE_CALENDAR_SHA256)
    if len(matches) != 1:
        raise RuntimeError(
            "accepted bridge calendar must resolve to exactly one byte-identical runtime file; "
            f"matches={len(matches)} paths={[str(path) for path in matches]}"
        )
    bridge = matches[0]
    report = audit_canonical_eod_calendar_parent(
        runtime_root=runtime,
        session=args.session,
        accepted_bridge_calendar_path=bridge,
        accepted_bridge_calendar_sha256=ACCEPTED_BRIDGE_CALENDAR_SHA256,
    )
    destination = runtime / ATTESTATION_NAMESPACE / str(report["session_date"]) / ATTESTATION_FILENAME
    written = create_canonical_eod_calendar_parent_attestation(report=report, output_path=destination)
    verified = verify_canonical_eod_calendar_parent_attestation(
        written,
        expected_session=args.session,
        expected_bridge_calendar_path=bridge,
        expected_bridge_calendar_sha256=ACCEPTED_BRIDGE_CALENDAR_SHA256,
    )
    if not verified:
        raise RuntimeError("created legacy calendar-parent attestation failed strict verification")

    result = {
        "status": "V4_X1_LEGACY_CALENDAR_PARENT_ATTESTATION_VERIFIED",
        "session_date": str(report["session_date"]),
        "attestation_path": str(written),
        "attestation_sha256": sha256_file(written),
        "bridge_calendar_path": str(bridge),
        "bridge_calendar_sha256": ACCEPTED_BRIDGE_CALENDAR_SHA256,
        "declared_capture_time_calendar_sha256": report["declared_capture_time_calendar_sha256"],
        "declared_capture_time_calendar_status": report["declared_capture_time_calendar_status"],
        "canonical_session_rewritten": False,
        "provider_calls": 0,
        "protected_outcome_accessed": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
