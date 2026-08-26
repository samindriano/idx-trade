from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
import re
from typing import Any

from .provenance import sha256_file
from .stockbit_intraday_runtime import SessionJournal
from .stockbit_intraday_session_v2 import SESSION_SCHEMA, StockbitIntradaySessionError


_SHA = re.compile(r"^[0-9a-f]{64}$")


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

    return payload, sha256_file(path)
