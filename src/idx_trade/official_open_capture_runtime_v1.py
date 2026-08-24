from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, time
from pathlib import Path
from typing import Callable
from uuid import uuid4

import requests

from .official_open_evidence_v1 import (
    JAKARTA,
    OfficialOpenEvidenceError,
    capture_official_open_with_transport_fallback,
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


def _session_paths(
    runtime_root: str | Path, session_date: str
) -> tuple[Path, Path, Path, Path]:
    folder = Path(runtime_root).expanduser().resolve() / "official_open" / session_date
    return (
        folder,
        folder / "raw_response.json",
        folder / "open_prices.parquet",
        folder / "manifest.json",
    )


def _manifest_transport(manifest_path: Path) -> tuple[str | None, str | None]:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, None
    if not isinstance(payload, dict):
        return None, None
    transport = str(payload.get("transport") or "") or None
    policy = str(payload.get("transport_policy") or "") or None
    return transport, policy


def _source_not_ready(message: str) -> bool:
    if message in {
        "OFFICIAL_OPEN_RAW_DATA_MISSING",
        "OFFICIAL_OPEN_DIRECT_IDX_EMPTY_RESPONSE",
        "OFFICIAL_OPEN_ZAPI_RAW_EMPTY_RESPONSE",
    }:
        return True
    if not message.startswith("OFFICIAL_OPEN_TRANSPORT_CHAIN_FAILED:"):
        return False
    return "EMPTY_RESPONSE" in message and (
        "ZAPI=OFFICIAL_OPEN_ZAPI_RAW_EMPTY_RESPONSE" in message
        or "ZAPI=NOT_CONFIGURED" in message
    )


def run_same_session_official_open_capture(
    *,
    runtime_root: str | Path,
    now: datetime | None = None,
    get: Callable[..., requests.Response] | None = None,
    zapi_get: Callable[..., requests.Response] | None = None,
    zapi_api_key: str | None = None,
    timeout_seconds: float = 30.0,
) -> dict[str, object]:
    """Capture only today's official IDX Open evidence, fail-closed.

    Direct IDX is the primary transport. If and only if that transport fails,
    the runtime may use Zapi's raw IDX passthrough with the same complete-session
    and OpenPrice-only certification contract. No prior session is backfilled.
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
        return finish(
            STATUS_TOO_EARLY,
            not_before_jakarta=NOT_BEFORE.isoformat(timespec="minutes"),
        )

    folder, raw_path, normalized_path, manifest_path = _session_paths(root, session_date)
    if manifest_path.is_file():
        transport, policy = _manifest_transport(manifest_path)
        return finish(
            STATUS_ALREADY_CAPTURED,
            manifest_path=str(manifest_path),
            evidence_folder=str(folder),
            transport=transport,
            transport_policy=policy,
        )
    partial = [str(path) for path in (raw_path, normalized_path) if path.exists()]
    if partial or folder.exists():
        return finish(
            STATUS_PARTIAL_EVIDENCE_FAIL_CLOSED,
            evidence_folder=str(folder),
            existing_paths=partial,
        )

    key = zapi_api_key if zapi_api_key is not None else os.environ.get("ZAPI_API_KEY")
    try:
        manifest = capture_official_open_with_transport_fallback(
            session_date,
            output_root=root,
            zapi_api_key=key,
            direct_get=get,
            zapi_get=zapi_get or requests.get,
            timeout_seconds=timeout_seconds,
        )
    except OfficialOpenEvidenceError as exc:
        message = str(exc)
        if _source_not_ready(message):
            return finish(
                STATUS_SOURCE_NOT_READY_OR_NO_SESSION,
                provider_error=message,
            )
        return finish(
            STATUS_CAPTURE_FAIL_CLOSED,
            provider_error=message,
        )

    transport, policy = _manifest_transport(manifest)
    return finish(
        STATUS_CAPTURED,
        manifest_path=str(manifest),
        evidence_folder=str(manifest.parent),
        transport=transport,
        transport_policy=policy,
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
