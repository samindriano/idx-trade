"""Same-session Official Open capture gated by the planned Bursa schedule."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import date, datetime, time
from pathlib import Path
import re
from typing import Callable
from uuid import uuid4

import requests

from .official_open_evidence_v1 import (
    JAKARTA,
    OfficialOpenEvidenceError,
    capture_official_open_with_transport_fallback,
)
from .official_trading_schedule_v1 import (
    OfficialTradingScheduleError,
    load_verified_official_trading_schedule,
)
from .v4_x1_execution_v1_verify import DecisionV1Error, verify_open_execution_inputs


STATUS_CAPTURED = "CAPTURED"
STATUS_ALREADY_CAPTURED = "ALREADY_CAPTURED"
STATUS_TOO_EARLY = "TOO_EARLY"
STATUS_WEEKEND_NO_SESSION = "WEEKEND_NO_SESSION"
STATUS_HOLIDAY_NO_SESSION = "HOLIDAY_NO_SESSION"
STATUS_SCHEDULE_COVERAGE_UNAVAILABLE = "SCHEDULE_COVERAGE_UNAVAILABLE"
STATUS_SOURCE_NOT_READY_OR_NO_SESSION = "SOURCE_NOT_READY_OR_NO_SESSION"
STATUS_PARTIAL_EVIDENCE_FAIL_CLOSED = "PARTIAL_EVIDENCE_FAIL_CLOSED"
STATUS_CAPTURE_FAIL_CLOSED = "CAPTURE_FAIL_CLOSED"
STATUS_AFTER_WINDOW_NO_EXECUTION_GRADE = "AFTER_WINDOW_NO_EXECUTION_GRADE"
NOT_BEFORE = time(9, 2)
NOT_AFTER = time(9, 22)
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def _atomic_json(payload: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


def _session_paths(runtime_root: Path, session_date: str) -> tuple[Path, Path, Path, Path]:
    folder = runtime_root / "official_open" / session_date
    return folder, folder / "raw_response.json", folder / "open_prices.parquet", folder / "manifest.json"


def _manifest_transport(manifest_path: Path) -> tuple[str | None, str | None]:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, None
    if not isinstance(payload, dict):
        return None, None
    return (
        str(payload.get("transport") or "") or None,
        str(payload.get("transport_policy") or "") or None,
    )


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


def _configured_schedule(runtime_root: Path) -> tuple[Path, str]:
    config_path = runtime_root / "operational" / "config.json"
    sidecar_path = runtime_root / "operational" / "config.json.sha256"
    if not config_path.is_file() or not sidecar_path.is_file():
        raise OfficialOpenEvidenceError("OFFICIAL_OPEN_RUNTIME_CONFIG_MISSING")
    config_bytes = config_path.read_bytes()
    actual = hashlib.sha256(config_bytes).hexdigest()
    if sidecar_path.read_text(encoding="utf-8").strip().lower() != actual:
        raise OfficialOpenEvidenceError("OFFICIAL_OPEN_RUNTIME_CONFIG_SHA_MISMATCH")
    try:
        payload = json.loads(config_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OfficialOpenEvidenceError("OFFICIAL_OPEN_RUNTIME_CONFIG_INVALID") from exc
    if not isinstance(payload, dict) or payload.get("operational_contract_version") != "DUAL_CALENDAR_V1":
        raise OfficialOpenEvidenceError("OFFICIAL_OPEN_RUNTIME_DUAL_CALENDAR_CONFIG_MISSING")
    raw_path = payload.get("execution_schedule_attestation_path")
    raw_sha = str(payload.get("execution_schedule_attestation_sha256") or "").lower()
    path = Path(str(raw_path or "")).expanduser()
    if not path.is_absolute() or not _SHA_RE.fullmatch(raw_sha):
        raise OfficialOpenEvidenceError("OFFICIAL_OPEN_RUNTIME_EXECUTION_SCHEDULE_IDENTITY_INVALID")
    return path.resolve(), raw_sha


def run_same_session_official_open_capture_v2(
    *,
    runtime_root: str | Path,
    now: datetime | None = None,
    get: Callable[..., requests.Response] | None = None,
    zapi_get: Callable[..., requests.Response] | None = None,
    zapi_api_key: str | None = None,
    timeout_seconds: float = 30.0,
    execution_schedule_attestation_path: str | Path | None = None,
    execution_schedule_attestation_sha256: str | None = None,
) -> dict[str, object]:
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
            "calendar_contract": "DUAL_CALENDAR_V1",
            **extra,
        }
        _atomic_json(result, status_path)
        return result

    try:
        if execution_schedule_attestation_path is None:
            schedule_path, schedule_sha = _configured_schedule(root)
        else:
            schedule_path = Path(execution_schedule_attestation_path).expanduser().resolve()
            schedule_sha = str(execution_schedule_attestation_sha256 or "").strip().lower()
            if not _SHA_RE.fullmatch(schedule_sha):
                raise OfficialOpenEvidenceError("OFFICIAL_OPEN_EXECUTION_SCHEDULE_SHA_INVALID")
        schedule = load_verified_official_trading_schedule(
            schedule_path, expected_sha256=schedule_sha
        )
    except (OSError, ValueError, OfficialOpenEvidenceError, OfficialTradingScheduleError) as exc:
        return finish(STATUS_CAPTURE_FAIL_CLOSED, provider_error=str(exc))

    today = date.fromisoformat(session_date)
    coverage_start = date.fromisoformat(schedule.coverage_start)
    coverage_end = date.fromisoformat(schedule.coverage_end)
    if today < coverage_start or today > coverage_end:
        return finish(
            STATUS_SCHEDULE_COVERAGE_UNAVAILABLE,
            reason="TODAY_OUTSIDE_VERIFIED_PLANNED_SCHEDULE_COVERAGE",
            execution_schedule_attestation_path=str(schedule.attestation_path),
            execution_schedule_attestation_sha256=schedule.attestation_sha256,
        )
    if current.weekday() > 4:
        return finish(STATUS_WEEKEND_NO_SESSION)
    if session_date not in schedule.session_dates:
        return finish(
            STATUS_HOLIDAY_NO_SESSION,
            reason="NO_PLANNED_OFFICIAL_SESSION_TODAY",
            execution_schedule_attestation_path=str(schedule.attestation_path),
            execution_schedule_attestation_sha256=schedule.attestation_sha256,
        )
    if current.time().replace(tzinfo=None) < NOT_BEFORE:
        return finish(STATUS_TOO_EARLY, not_before_jakarta=NOT_BEFORE.isoformat(timespec="minutes"))
    if current.time().replace(tzinfo=None) > NOT_AFTER:
        return finish(
            STATUS_AFTER_WINDOW_NO_EXECUTION_GRADE,
            reason="OFFICIAL_OPEN_CAPTURE_WINDOW_CLOSED",
            execution_grade=False,
        )

    folder, raw_path, normalized_path, manifest_path = _session_paths(root, session_date)
    if manifest_path.is_file():
        try:
            verified = verify_open_execution_inputs(
                execution_session_date=session_date,
                manifest_path=manifest_path,
            )
        except (DecisionV1Error, OSError, ValueError) as exc:
            return finish(
                STATUS_PARTIAL_EVIDENCE_FAIL_CLOSED,
                manifest_path=str(manifest_path),
                evidence_folder=str(folder),
                provider_error=f"EXISTING_OFFICIAL_OPEN_MANIFEST_INVALID:{exc}",
            )
        transport = verified.transport
        policy = verified.transport_policy
        return finish(
            STATUS_ALREADY_CAPTURED,
            manifest_path=str(manifest_path),
            evidence_folder=str(folder),
            transport=transport,
            transport_policy=policy,
            manifest_sha256=verified.manifest_sha256,
            raw_artifact_sha256=verified.raw_source_sha256,
            normalized_artifact_sha256=verified.ohlcv_artifact_sha256,
            execution_schedule_attestation_path=str(schedule.attestation_path),
            execution_schedule_attestation_sha256=schedule.attestation_sha256,
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
            return finish(STATUS_SOURCE_NOT_READY_OR_NO_SESSION, provider_error=message)
        return finish(STATUS_CAPTURE_FAIL_CLOSED, provider_error=message)

    transport, policy = _manifest_transport(manifest)
    return finish(
        STATUS_CAPTURED,
        manifest_path=str(manifest),
        evidence_folder=str(manifest.parent),
        transport=transport,
        transport_policy=policy,
        execution_schedule_attestation_path=str(schedule.attestation_path),
        execution_schedule_attestation_sha256=schedule.attestation_sha256,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--execution-schedule-attestation")
    parser.add_argument("--execution-schedule-attestation-sha256")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = run_same_session_official_open_capture_v2(
        runtime_root=args.runtime_root,
        timeout_seconds=args.timeout_seconds,
        execution_schedule_attestation_path=args.execution_schedule_attestation,
        execution_schedule_attestation_sha256=args.execution_schedule_attestation_sha256,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    status = str(result["status"])
    if status == STATUS_PARTIAL_EVIDENCE_FAIL_CLOSED:
        return 3
    if status == STATUS_SOURCE_NOT_READY_OR_NO_SESSION:
        return 2
    if status in {STATUS_CAPTURE_FAIL_CLOSED, STATUS_SCHEDULE_COVERAGE_UNAVAILABLE}:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
