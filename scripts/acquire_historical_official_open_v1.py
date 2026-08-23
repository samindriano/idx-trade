"""Acquire execution-session official IDX Open evidence for the research lane.

This is deliberately separate from the live same-session scheduler.  It reads
only the outcome-blind structural session ledger and the frozen official
calendar, calls the accepted official Open transport, and writes immutable
session folders plus a progress manifest outside Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from uuid import uuid4

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.official_open_evidence_v1 import (  # noqa: E402
    OfficialOpenEvidenceError,
    capture_official_open_with_transport_fallback,
)
from idx_trade.v4_x1_execution_v1_verify import verify_open_execution_inputs  # noqa: E402


EXPECTED_CALENDAR_SHA256 = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
EXPECTED_STRUCTURAL_MANIFEST_SHA256 = "a555368181dff5084be342dbf13b79993252767ae7e00804f7601477b29995ba"
EXPECTED_SESSION_COUNT = 600


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    raw = (json.dumps(value, indent=2, sort_keys=True, default=str) + "\n").encode("utf-8")
    try:
        with tmp.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def load_execution_sessions(structural_root: Path, calendar_path: Path) -> list[str]:
    structural_manifest = structural_root / "MANIFEST.json"
    if sha256(structural_manifest) != EXPECTED_STRUCTURAL_MANIFEST_SHA256:
        raise RuntimeError("STRUCTURAL_MANIFEST_SHA_MISMATCH")
    manifest = json.loads(structural_manifest.read_text(encoding="utf-8"))
    if manifest.get("status") != "DECISION_V2_MINIMAL_STRUCTURAL_REJECT":
        raise RuntimeError("STRUCTURAL_MANIFEST_STATUS_CHANGED")
    sessions = pd.read_csv(structural_root / "decision_session_ledger.csv", usecols=["index", "date"])
    if len(sessions) != EXPECTED_SESSION_COUNT or sessions["index"].tolist() != list(range(EXPECTED_SESSION_COUNT)):
        raise RuntimeError("STRUCTURAL_SESSION_COUNT_CHANGED")
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    calendar = pd.read_csv(calendar_path, usecols=["date"])
    if sha256(calendar_path) != EXPECTED_CALENDAR_SHA256:
        raise RuntimeError("CALENDAR_SHA_MISMATCH")
    calendar["date"] = pd.to_datetime(calendar["date"], errors="raise").dt.normalize()
    if len(calendar) != 1260 or calendar["date"].duplicated().any():
        raise RuntimeError("CALENDAR_INVALID")
    next_by_date = dict(zip(calendar["date"], calendar["date"].shift(-1)))
    execution = [next_by_date[pd.Timestamp(value)] for value in sessions["date"]]
    if any(pd.isna(value) for value in execution):
        raise RuntimeError("NEXT_EXECUTION_SESSION_MISSING")
    result = sorted({pd.Timestamp(value).date().isoformat() for value in execution})
    if len(result) != EXPECTED_SESSION_COUNT:
        raise RuntimeError(f"EXECUTION_SESSION_COUNT_CHANGED:{len(result)}")
    return result


def retryable(error: str) -> bool:
    return any(token in error for token in ("ZAPI_RAW_HTTP_429", "ZAPI_RAW_HTTP_500", "ZAPI_RAW_HTTP_502", "ZAPI_RAW_HTTP_503", "ZAPI_RAW_HTTP_504", "REQUEST_ERROR"))


def acquire(*, structural_root: Path, calendar_path: Path, output_root: Path, attempts: int, pause_seconds: float) -> dict:
    sessions = load_execution_sessions(structural_root, calendar_path)
    api_key = __import__("os").environ.get("ZAPI_API_KEY")
    if not api_key:
        raise RuntimeError("ZAPI_API_KEY_NOT_CONFIGURED")
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "ACQUISITION_MANIFEST.json"
    records: list[dict] = []
    if manifest_path.is_file():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("session_count") != len(sessions):
            raise RuntimeError("ACQUISITION_SESSION_COUNT_CHANGED")
        existing_records = existing.get("records")
        if not isinstance(existing_records, list):
            raise RuntimeError("ACQUISITION_RECORDS_INVALID")
        for row in existing_records:
            if not isinstance(row, dict) or str(row.get("session_date") or "") not in sessions:
                raise RuntimeError("ACQUISITION_EXISTING_RECORD_INVALID")
            if row.get("status") == "CERTIFIED":
                session_folder = output_root / "official_open" / str(row["session_date"])
                session_manifest = session_folder / "manifest.json"
                if not session_manifest.is_file() or sha256(session_manifest) != row.get("manifest_sha256"):
                    raise RuntimeError("ACQUISITION_EXISTING_CERTIFIED_SHA_MISMATCH")
                records.append(dict(row))
            elif row.get("status") not in {"FAILED_FAIL_CLOSED"}:
                raise RuntimeError("ACQUISITION_EXISTING_STATUS_INVALID")
    progress = {"schema_version": "historical_official_open_acquisition_progress_v1", "status": "RUNNING", "session_count": len(sessions), "records": records}
    atomic_json(manifest_path, progress)
    for ordinal, session in enumerate(sessions, start=1):
        session_folder = output_root / "official_open" / session
        if any(row.get("session_date") == session and row.get("status") == "CERTIFIED" for row in records):
            continue
        existing_manifest = session_folder / "manifest.json"
        if existing_manifest.is_file():
            verified = verify_open_execution_inputs(
                execution_session_date=session,
                manifest_path=existing_manifest,
            )
            payload = json.loads(existing_manifest.read_text(encoding="utf-8"))
            records = [row for row in records if row.get("session_date") != session]
            records.append({
                "session_date": session,
                "status": "CERTIFIED",
                "transport": verified.transport,
                "row_count": int(payload["row_count"]),
                "positive_openprice_count": int(payload["positive_openprice_count"]),
                "unavailable_openprice_count": int(payload["unavailable_openprice_count"]),
                "manifest_sha256": sha256(existing_manifest),
                "reused_existing": True,
            })
            continue
        records = [row for row in records if row.get("session_date") != session]
        last_error = None
        for attempt in range(1, attempts + 1):
            try:
                manifest = capture_official_open_with_transport_fallback(
                    session,
                    output_root=output_root,
                    zapi_api_key=api_key,
                    timeout_seconds=30.0,
                )
                payload = json.loads(manifest.read_text(encoding="utf-8"))
                records.append({"session_date": session, "status": "CERTIFIED", "transport": payload.get("transport"), "row_count": payload.get("row_count"), "positive_openprice_count": payload.get("positive_openprice_count"), "unavailable_openprice_count": payload.get("unavailable_openprice_count"), "manifest_sha256": sha256(manifest)})
                last_error = None
                break
            except OfficialOpenEvidenceError as exc:
                last_error = str(exc)
                if attempt < attempts and retryable(last_error):
                    time.sleep(pause_seconds)
                else:
                    break
        if last_error is not None:
            records.append({"session_date": session, "status": "FAILED_FAIL_CLOSED", "error": last_error, "attempts": attempt})
        progress = {"schema_version": "historical_official_open_acquisition_progress_v1", "status": "RUNNING", "session_count": len(sessions), "completed_count": len(records), "records": records}
        atomic_json(manifest_path, progress)
        if ordinal % 10 == 0 or ordinal == len(sessions):
            print(f"completed={ordinal}/{len(sessions)} certified={sum(row['status'] == 'CERTIFIED' for row in records)} failed={sum(row['status'] == 'FAILED_FAIL_CLOSED' for row in records)}", flush=True)
    progress = {
        "schema_version": "historical_official_open_acquisition_progress_v1",
        "status": "RUNNING",
        "session_count": len(sessions),
        "completed_count": len(records),
        "records": records,
    }
    final = {**progress, "status": "COMPLETE"}
    atomic_json(manifest_path, final)
    final["manifest_sha256"] = sha256(manifest_path)
    return final


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--structural-root", type=Path, default=Path(r"D:\Documents\Project\idx-v4-x1-decision-v2-minimal-structural-replay-20260821-v1"))
    parser.add_argument("--calendar", type=Path, default=Path(r"D:\Documents\Project\idx-v4-x1-clean-historical-input-stage-r2-20260820\official_exchange_sessions_1260.csv"))
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--attempts", type=int, default=2)
    parser.add_argument("--pause-seconds", type=float, default=1.0)
    args = parser.parse_args()
    if args.attempts < 1 or args.attempts > 3:
        raise SystemExit("ATTEMPTS_MUST_BE_1_TO_3")
    result = acquire(structural_root=args.structural_root.resolve(), calendar_path=args.calendar.resolve(), output_root=args.output_root.resolve(), attempts=args.attempts, pause_seconds=args.pause_seconds)
    print(json.dumps({"status": result["status"], "session_count": result["session_count"], "completed_count": result["completed_count"], "manifest_sha256": result["manifest_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
