from __future__ import annotations

import argparse
import json
from datetime import datetime, time
from pathlib import Path
from typing import Callable
from uuid import uuid4

import requests

from .official_open_evidence_v1 import (
    JAKARTA,
    OfficialOpenEvidenceError,
    capture_direct_idx_official_open,
)


STATUS_CAPTURED = "CAPTURED"
STATUS_ALREADY_CAPTURED = "ALREADY_CAPTURED"
STATUS_TOO_EARLY = "TOO_EARLY"
STATUS_WEEKEND_NO_SESSION = "WEEKEND_NO_SESSION"
STATUS_SOURCE_NOT_READY_OR_NO_SESSION = "SOURCE_NOT_READY_OR_NO_SESSION"
STATUS_PARTIAL_EVIDENCE_FAIL_CLOSED = "PARTIAL_EVIDENCE_FAIL_CLOSED"
STATUS_CAPTURE_FAIL_CLOSED = "CAPTURE_FAIL_CLOSED"

NOT_BEFORE = time(9, 2)


def _atomic_json(payload: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


def _session_paths(runtime_root: str | Path, session_date: str) -> tuple[Path, Path, Path, Path]:
    folder = Path(runtime_root).expanduser().resolve() / "official_open" / session_date
    return (
        folder,
        folder / "raw_response.json",
        folder / "open_prices.parquet",
        folder / "manifest.json",
    )


def run_same_session_official_open_capture(
    *,
    runtime_root: str | Path,
    now: datetime | None = None,
    get: Callable[..., requests.Response] = requests.get,
    timeout_seconds: float = 30.0,
) -> dict[str, object]:
    """Capture only today's official IDX Open evidence, fail-closed.

    The runtime intentionally does not infer exchange holidays from weekdays or
    backfill prior sessions. A weekday with no Stock Summary data is reported as
    source-not-ready-or-no-session and may be retried by the scheduler. Other
    provider/schema failures are durably recorded as fail-closed while leaving
    the final session path absent so a later scheduled retry can try again.
    """

    current = now or datetime.now(JAKARTA)
    if current.tzinfo is None:
        current = current.replace(tzinfo=JAKARTA)
    else:
        current = current.astimezone(JAKARTA)
    session_date = current.date().isoformat()
    root = Path(runtime_root).expanduser().resolve()
    status_path = root / "official_open" / "latest_capture.json"

    def finish(status: str, **extra: object) -> dict[str, object]:
        result: dict[str, object] = {
            "status": status,
            "session_date": session_date,
            "run_at_jakarta": current.isoformat(),
            "current_session_only": True,
            **extra,
        }
        _atomic_json(result, status_path)
        return result

    if current.weekday() > 4:
        return finish(STATUS_WEEKEND_NO_SESSION)
    if current.time().replace(tzinfo=None) < NOT_BEFORE:
        return finish(STATUS_TOO_EARLY, not_before_jakarta=NOT_BEFORE.isoformat(timespec="minutes"))

    folder, raw_path, normalized_path, manifest_path = _session_paths(root, session_date)
    if manifest_path.is_file():
        return finish(
            STATUS_ALREADY_CAPTURED,
            manifest_path=str(manifest_path),
            evidence_folder=str(folder),
        )
    partial = [str(path) for path in (raw_path, normalized_path) if path.exists()]
    if partial or folder.exists():
        return finish(
            STATUS_PARTIAL_EVIDENCE_FAIL_CLOSED,
            evidence_folder=str(folder),
            existing_paths=partial,
        )

    try:
        manifest = capture_direct_idx_official_open(
            session_date,
            output_root=root,
            get=get,
            timeout_seconds=timeout_seconds,
        )
    except OfficialOpenEvidenceError as exc:
        message = str(exc)
        if message in {
            "OFFICIAL_OPEN_RAW_DATA_MISSING",
            "OFFICIAL_OPEN_DIRECT_IDX_EMPTY_RESPONSE",
        }:
            return finish(
                STATUS_SOURCE_NOT_READY_OR_NO_SESSION,
                provider_error=message,
            )
        return finish(
            STATUS_CAPTURE_FAIL_CLOSED,
            provider_error=message,
        )

    return finish(
        STATUS_CAPTURED,
        manifest_path=str(manifest),
        evidence_folder=str(manifest.parent),
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture same-session execution-grade official IDX OpenPrice evidence"
    )
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = run_same_session_official_open_capture(
        runtime_root=args.runtime_root,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    status = str(result["status"])
    if status == STATUS_PARTIAL_EVIDENCE_FAIL_CLOSED:
        return 3
    if status == STATUS_SOURCE_NOT_READY_OR_NO_SESSION:
        return 2
    if status == STATUS_CAPTURE_FAIL_CLOSED:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
