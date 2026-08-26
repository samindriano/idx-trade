from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
import re
from typing import Any

from .provenance import sha256_file
from .stockbit_intraday_runtime import SessionJournal
from .stockbit_intraday_session_v2 import (
    SESSION_SCHEMA,
    StockbitIntradaySessionError,
    load_run_contract,
    verify_bound_gate,
)


_SHA = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_BOUND_FILES = {
    "day_metadata.json",
    "universe_snapshot.csv",
    "session_contract.json",
    "gate/manifest.json",
    "gate/decisions.csv",
    "gate/evidence.json",
}


def _verify_shadow_metrics(payload: dict[str, Any]) -> None:
    mode = str(payload.get("run_mode") or "")
    metrics = payload.get("shadow_metrics")
    if mode == "ENFORCE":
        if metrics is not None:
            raise StockbitIntradaySessionError("SESSION_MANIFEST_ENFORCE_SHADOW_METRICS_PRESENT")
        return
    if not isinstance(metrics, dict):
        raise StockbitIntradaySessionError("SESSION_MANIFEST_SHADOW_METRICS_MISSING")
    for field in ("false_negative", "false_positive", "actual_success", "actual_no_chart_404"):
        value = metrics.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise StockbitIntradaySessionError(f"SESSION_MANIFEST_SHADOW_METRIC_INVALID:{field}")
    if metrics.get("certification_eligible") not in {True, False}:
        raise StockbitIntradaySessionError("SESSION_MANIFEST_CERTIFICATION_ELIGIBLE_INVALID")


def load_verified_session_manifest(journal: SessionJournal) -> tuple[dict[str, Any], str] | None:
    path = journal.root / "session_manifest.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StockbitIntradaySessionError("SESSION_MANIFEST_INVALID") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != SESSION_SCHEMA:
        raise StockbitIntradaySessionError("SESSION_MANIFEST_SCHEMA_INVALID")
    if payload.get("session_date") != journal.expected_date.isoformat():
        raise StockbitIntradaySessionError("SESSION_MANIFEST_SESSION_MISMATCH")
    if payload.get("status") != "ADMISSIBLE_COMPLETE":
        raise StockbitIntradaySessionError("SESSION_MANIFEST_STATUS_INVALID")
    if payload.get("run_mode") not in {"SHADOW", "SHADOW_RECHECK", "ENFORCE"}:
        raise StockbitIntradaySessionError("SESSION_MANIFEST_MODE_INVALID")
    completion = payload.get("completion")
    if (
        not isinstance(completion, dict)
        or completion.get("admissible_complete") is not True
        or completion.get("complete") is not True
    ):
        raise StockbitIntradaySessionError("SESSION_MANIFEST_COMPLETION_INVALID")
    if (
        payload.get("synthetic_fill_used") is not False
        or payload.get("retroactive_capture_used") is not False
        or payload.get("outcome_accessed") is not False
    ):
        raise StockbitIntradaySessionError("SESSION_MANIFEST_SAFETY_GUARD_INVALID")

    files = payload.get("files")
    if not isinstance(files, dict) or not files:
        raise StockbitIntradaySessionError("SESSION_MANIFEST_FILES_INVALID")
    if not _REQUIRED_BOUND_FILES.issubset(set(str(value) for value in files)):
        raise StockbitIntradaySessionError("SESSION_MANIFEST_REQUIRED_BOUND_FILE_MISSING")
    root = journal.root.resolve()
    for relative, declared_sha in files.items():
        text = str(relative).replace("\\", "/")
        posix = PurePosixPath(text)
        if not text or posix.is_absolute() or ".." in posix.parts or "." in posix.parts:
            raise StockbitIntradaySessionError("SESSION_MANIFEST_FILE_PATH_INVALID")
        digest = str(declared_sha or "").strip().lower()
        if not _SHA.fullmatch(digest):
            raise StockbitIntradaySessionError("SESSION_MANIFEST_FILE_SHA_INVALID")
        target = (root / Path(text)).resolve()
        if root not in target.parents or not target.is_file() or sha256_file(target) != digest:
            raise StockbitIntradaySessionError("SESSION_MANIFEST_FILE_SHA_MISMATCH")

    # File hashes are necessary but not sufficient. Re-evaluate the frozen
    # semantic parents and require the final manifest to bind the same values.
    contract = load_run_contract(journal)
    gate = verify_bound_gate(journal)
    gate_sha = sha256_file(journal.root / "gate" / "manifest.json")
    if payload.get("run_mode") != contract.get("run_mode"):
        raise StockbitIntradaySessionError("SESSION_MANIFEST_CONTRACT_MODE_MISMATCH")
    if payload.get("schedule_attestation_sha256") != contract.get("schedule_attestation_sha256"):
        raise StockbitIntradaySessionError("SESSION_MANIFEST_CONTRACT_SCHEDULE_MISMATCH")
    if payload.get("gate_manifest_sha256") != contract.get("gate_manifest_sha256") or payload.get("gate_manifest_sha256") != gate_sha:
        raise StockbitIntradaySessionError("SESSION_MANIFEST_GATE_BINDING_MISMATCH")
    if payload.get("eod_manifest_sha256") != gate.get("eod_manifest_sha256"):
        raise StockbitIntradaySessionError("SESSION_MANIFEST_EOD_BINDING_MISMATCH")

    recomputed = journal.summary()
    if recomputed != completion:
        raise StockbitIntradaySessionError("SESSION_MANIFEST_COMPLETION_RECOMPUTE_MISMATCH")
    _verify_shadow_metrics(payload)
    return payload, sha256_file(path)
