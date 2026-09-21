"""Fail-closed classification of caller-supplied legacy migration evidence.

This module does not construct a V2 state and does not activate a runtime.
It classifies only an explicit, canonical evidence envelope so that missing
quantity history cannot be inferred from current positions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json
import re
from typing import Any

from .v4_x1_decision_v1_contract import DecisionV1Error


MIGRATION_COMPATIBILITY_SCHEMA = "idx_trade_legacy_execution_evidence_v1"
RECOVERABLE_COMPLETE = "RECOVERABLE_COMPLETE"
RECOVERABLE_ZERO_FILL_PENDING = "RECOVERABLE_ZERO_FILL_PENDING"
RECOVERABLE_PARTIAL = "RECOVERABLE_PARTIAL"
UNKNOWN_ORPHANED_PARTIAL = "UNKNOWN_ORPHANED_PARTIAL"
LEGACY_POSITION_ONLY = "LEGACY_POSITION_ONLY"
REQUIRES_RECONCILIATION = "REQUIRES_RECONCILIATION"
MIGRATABLE = "MIGRATABLE"
MIGRATION_CANDIDATE = "MIGRATION_CANDIDATE"
BLOCKED = "BLOCKED"
LOT_SIZE_SHARES = 100
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_INPUT_KEYS = frozenset(
    {
        "schema_version",
        "session_date",
        "ticker",
        "side",
        "planned_shares",
        "fill_vector",
        "position_shares",
        "pending",
        "event_payload_sha256",
    }
)


def _hash(value: object) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256((body + chr(10)).encode("utf-8")).hexdigest()


def _date(value: object) -> str:
    if not isinstance(value, str):
        raise DecisionV1Error("MIGRATION_COMPATIBILITY_SESSION_DATE_INVALID")
    normalized = value.strip()
    try:
        parsed = date.fromisoformat(normalized)
    except ValueError as exc:
        raise DecisionV1Error("MIGRATION_COMPATIBILITY_SESSION_DATE_INVALID") from exc
    if parsed.isoformat() != normalized:
        raise DecisionV1Error("MIGRATION_COMPATIBILITY_SESSION_DATE_INVALID")
    return normalized


def _shares(value: object, code: str, *, allow_zero: bool = True) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DecisionV1Error(code)
    if value < 0 or (not allow_zero and value == 0) or value % LOT_SIZE_SHARES:
        raise DecisionV1Error(code)
    return value


def _optional_shares(
    value: object,
    code: str,
    *,
    allow_zero: bool,
) -> int | None:
    if value is None:
        return None
    return _shares(value, code, allow_zero=allow_zero)


def _ticker(value: object) -> str:
    if not isinstance(value, str):
        raise DecisionV1Error("MIGRATION_COMPATIBILITY_TICKER_INVALID")
    normalized = value.strip().upper().replace(".JK", "")
    if not normalized:
        raise DecisionV1Error("MIGRATION_COMPATIBILITY_TICKER_INVALID")
    return normalized


def _event_rows(value: object) -> tuple[tuple[str, str], ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise DecisionV1Error("MIGRATION_COMPATIBILITY_EVENT_ROWS_INVALID")
    rows: list[tuple[str, str]] = []
    for row in value:
        if set(row) != {"event_id", "payload_sha256"}:
            raise DecisionV1Error("MIGRATION_COMPATIBILITY_EVENT_ROWS_INVALID")
        event_id = row["event_id"]
        payload_sha = row["payload_sha256"]
        if (
            not isinstance(event_id, str)
            or not event_id.strip()
            or not isinstance(payload_sha, str)
            or not _SHA_RE.fullmatch(payload_sha)
        ):
            raise DecisionV1Error("MIGRATION_COMPATIBILITY_EVENT_ROWS_INVALID")
        rows.append((event_id, payload_sha))
    return tuple(rows)


def _fill_vector(value: object) -> tuple[int, ...] | None:
    if value is None:
        return None
    if not isinstance(value, list) or not value:
        raise DecisionV1Error("MIGRATION_COMPATIBILITY_FILL_VECTOR_INVALID")
    return tuple(
        _shares(item, "MIGRATION_COMPATIBILITY_FILL_VECTOR_INVALID")
        for item in value
    )


@dataclass(frozen=True)
class MigrationCompatibilityResultV1:
    schema_version: str
    source_payload_sha256: str
    session_date: str
    ticker: str
    side: str
    planned_shares: int | None
    filled_shares: int | None
    position_shares: int | None
    pending: bool
    classification: str
    disposition: str
    reason_code: str

    def payload(self) -> dict[str, Any]:
        body = asdict(self)
        body["payload_sha256"] = _hash(body)
        return body


def _duplicate_conflict(events: tuple[tuple[str, str], ...]) -> bool:
    seen: dict[str, str] = {}
    for event_id, payload_sha in events:
        previous = seen.get(event_id)
        if previous is not None and previous != payload_sha:
            return True
        seen[event_id] = payload_sha
    return False


def classify_legacy_evidence(
    value: dict[str, Any],
) -> MigrationCompatibilityResultV1:
    """Classify explicit evidence without constructing or mutating runtime state."""

    if not isinstance(value, dict) or set(value) != _INPUT_KEYS:
        raise DecisionV1Error("MIGRATION_COMPATIBILITY_PAYLOAD_NOT_CANONICAL")
    if value["schema_version"] != MIGRATION_COMPATIBILITY_SCHEMA:
        raise DecisionV1Error("MIGRATION_COMPATIBILITY_SCHEMA_MISMATCH")
    session = _date(value["session_date"])
    ticker = _ticker(value["ticker"])
    side = value["side"]
    if side not in {"BUY", "SELL"}:
        raise DecisionV1Error("MIGRATION_COMPATIBILITY_SIDE_INVALID")
    if not isinstance(value["pending"], bool):
        raise DecisionV1Error("MIGRATION_COMPATIBILITY_PENDING_INVALID")
    events = _event_rows(value["event_payload_sha256"])
    planned = _optional_shares(
        value["planned_shares"],
        "MIGRATION_COMPATIBILITY_PLANNED_SHARES_INVALID",
        allow_zero=False,
    )
    position = _optional_shares(
        value["position_shares"],
        "MIGRATION_COMPATIBILITY_POSITION_SHARES_INVALID",
        allow_zero=True,
    )
    vector = _fill_vector(value["fill_vector"])
    if _duplicate_conflict(events):
        classification = REQUIRES_RECONCILIATION
        reason = "CONFLICTING_DUPLICATE_EVENT_BYTES"
        disposition = BLOCKED
        filled = None
    elif planned is None and position is not None and position > 0:
        classification = UNKNOWN_ORPHANED_PARTIAL
        reason = "POSITION_WITHOUT_PLAN_OR_FILL_VECTOR"
        disposition = BLOCKED
        filled = None
    elif planned is None:
        classification = LEGACY_POSITION_ONLY
        reason = "NO_QUANTIFIED_PLAN_OR_POSITIVE_POSITION"
        disposition = BLOCKED
        filled = None
    elif vector is None:
        if value["pending"] and position in {None, 0}:
            classification = RECOVERABLE_ZERO_FILL_PENDING
            reason = "EXPLICIT_PLAN_WITH_ZERO_FILL_PENDING"
            disposition = MIGRATABLE
            filled = 0
        else:
            classification = REQUIRES_RECONCILIATION
            reason = "PLAN_WITHOUT_PRESERVED_FILL_VECTOR"
            disposition = BLOCKED
            filled = None
    else:
        filled = sum(vector)
        if filled > planned:
            classification = REQUIRES_RECONCILIATION
            reason = "FILL_VECTOR_EXCEEDS_PLAN"
            disposition = BLOCKED
        elif filled == planned:
            classification = RECOVERABLE_COMPLETE
            reason = "COMPLETE_PLAN_AND_FILL_VECTOR"
            disposition = MIGRATABLE
        elif filled > 0 and value["pending"]:
            classification = RECOVERABLE_PARTIAL
            reason = "PRESERVED_POSITIVE_PARTIAL_FILL_VECTOR"
            disposition = MIGRATION_CANDIDATE
        else:
            classification = REQUIRES_RECONCILIATION
            reason = "INCOMPLETE_VECTOR_WITHOUT_PENDING_REMAINDER"
            disposition = BLOCKED
    return MigrationCompatibilityResultV1(
        schema_version="idx_trade_migration_compatibility_result_v1",
        source_payload_sha256=_hash(value),
        session_date=session,
        ticker=ticker,
        side=side,
        planned_shares=planned,
        filled_shares=filled,
        position_shares=position,
        pending=value["pending"],
        classification=classification,
        disposition=disposition,
        reason_code=reason,
    )


def verify_compatibility_result(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or "payload_sha256" not in value:
        raise DecisionV1Error("MIGRATION_COMPATIBILITY_RESULT_REQUIRED")
    declared = value.get("payload_sha256")
    if not isinstance(declared, str) or not _SHA_RE.fullmatch(declared):
        raise DecisionV1Error("MIGRATION_COMPATIBILITY_RESULT_HASH_INVALID")
    body = dict(value)
    body.pop("payload_sha256")
    if _hash(body) != declared:
        raise DecisionV1Error("MIGRATION_COMPATIBILITY_RESULT_HASH_MISMATCH")
    return value


__all__ = [
    "BLOCKED",
    "LEGACY_POSITION_ONLY",
    "MIGRATION_CANDIDATE",
    "MIGRATION_COMPATIBILITY_SCHEMA",
    "MIGRATABLE",
    "MigrationCompatibilityResultV1",
    "RECOVERABLE_COMPLETE",
    "RECOVERABLE_PARTIAL",
    "RECOVERABLE_ZERO_FILL_PENDING",
    "REQUIRES_RECONCILIATION",
    "UNKNOWN_ORPHANED_PARTIAL",
    "classify_legacy_evidence",
    "verify_compatibility_result",
]
