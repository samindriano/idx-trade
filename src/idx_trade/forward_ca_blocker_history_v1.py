from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json
import re
from typing import Any, Sequence

from .forward_dividend_disposition_v1_2 import (
    BLOCKED_LIVE_UNRESOLVED,
    CERTIFIED_LIVE,
    HISTORICAL_OBSERVED,
    SUPERSEDED,
    DividendDisposition,
    DividendDispositionResult,
)


HISTORY_SCHEMA = "idx_trade_forward_ca_blocker_resolution_history_v1"
BLOCKED = "BLOCKED"
RESOLVED_CERTIFIED = "RESOLVED_CERTIFIED"
RESOLVED_SUPERSEDED = "RESOLVED_SUPERSEDED"

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TICKER_RE = re.compile(r"^[A-Z0-9]{1,12}$")


class ForwardCABlockerHistoryError(RuntimeError):
    pass


@dataclass(frozen=True)
class CABlockerHistoryEntry:
    """One immutable blocker lifecycle observation.

    ``announcement_identity`` is the lifecycle key.  The query window is
    retained as provenance for the observation, but it is deliberately not
    part of that key, so a later bounded query can resolve the same candidate.
    """

    batch_id: str
    as_of_date: str
    query_window_from: str
    query_window_to: str
    announcement_identity: str
    ticker: str
    status: str
    disposition_category: str
    reason: str
    resolution_identity: str | None = None
    event_id: str | None = None
    event_sha256: str | None = None


def _text(value: object, code: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise ForwardCABlockerHistoryError(code)
    return result


def _date(value: object, code: str) -> str:
    result = _text(value, code)
    if not _DATE_RE.fullmatch(result):
        raise ForwardCABlockerHistoryError(code)
    try:
        parsed = date.fromisoformat(result)
    except ValueError as exc:
        raise ForwardCABlockerHistoryError(code) from exc
    if parsed.isoformat() != result:
        raise ForwardCABlockerHistoryError(code)
    return result


def _ticker(value: object) -> str:
    result = _text(value, "FORWARD_CA_BLOCKER_HISTORY_TICKER_INVALID")
    if not _TICKER_RE.fullmatch(result):
        raise ForwardCABlockerHistoryError(
            "FORWARD_CA_BLOCKER_HISTORY_TICKER_INVALID"
        )
    return result


def _sha256(value: object) -> str:
    result = _text(value, "FORWARD_CA_BLOCKER_HISTORY_EVENT_SHA_INVALID")
    if not _SHA256_RE.fullmatch(result):
        raise ForwardCABlockerHistoryError(
            "FORWARD_CA_BLOCKER_HISTORY_EVENT_SHA_INVALID"
        )
    return result


def _validate_identity(identity: object, ticker: str) -> str:
    result = _text(
        identity,
        "FORWARD_CA_BLOCKER_HISTORY_IDENTITY_INVALID",
    )
    if not result.startswith(f"{ticker}|"):
        raise ForwardCABlockerHistoryError(
            "FORWARD_CA_BLOCKER_HISTORY_IDENTITY_TICKER_MISMATCH"
        )
    return result


def _validate_entry(entry: CABlockerHistoryEntry) -> CABlockerHistoryEntry:
    if not isinstance(entry, CABlockerHistoryEntry):
        raise ForwardCABlockerHistoryError(
            "FORWARD_CA_BLOCKER_HISTORY_ENTRY_INVALID"
        )

    batch_id = _text(
        entry.batch_id,
        "FORWARD_CA_BLOCKER_HISTORY_BATCH_ID_INVALID",
    )
    as_of_date = _date(
        entry.as_of_date,
        "FORWARD_CA_BLOCKER_HISTORY_ASOF_INVALID",
    )
    query_window_from = _date(
        entry.query_window_from,
        "FORWARD_CA_BLOCKER_HISTORY_WINDOW_FROM_INVALID",
    )
    query_window_to = _date(
        entry.query_window_to,
        "FORWARD_CA_BLOCKER_HISTORY_WINDOW_TO_INVALID",
    )
    if query_window_to < query_window_from:
        raise ForwardCABlockerHistoryError(
            "FORWARD_CA_BLOCKER_HISTORY_WINDOW_REVERSED"
        )

    ticker = _ticker(entry.ticker)
    identity = _validate_identity(entry.announcement_identity, ticker)
    status = _text(
        entry.status,
        "FORWARD_CA_BLOCKER_HISTORY_STATUS_INVALID",
    )
    category = _text(
        entry.disposition_category,
        "FORWARD_CA_BLOCKER_HISTORY_CATEGORY_INVALID",
    )
    reason = _text(
        entry.reason,
        "FORWARD_CA_BLOCKER_HISTORY_REASON_INVALID",
    )

    resolution_identity = entry.resolution_identity
    if resolution_identity is not None:
        resolution_identity = _text(
            resolution_identity,
            "FORWARD_CA_BLOCKER_HISTORY_RESOLUTION_IDENTITY_INVALID",
        )

    event_id = entry.event_id
    if event_id is not None:
        event_id = _text(
            event_id,
            "FORWARD_CA_BLOCKER_HISTORY_EVENT_ID_INVALID",
        )

    event_sha256 = entry.event_sha256
    if event_sha256 is not None:
        event_sha256 = _sha256(event_sha256)

    if status == BLOCKED:
        if category != BLOCKED_LIVE_UNRESOLVED:
            raise ForwardCABlockerHistoryError(
                "FORWARD_CA_BLOCKER_HISTORY_BLOCKED_CATEGORY_INVALID"
            )
        if resolution_identity is not None or event_id is not None or event_sha256 is not None:
            raise ForwardCABlockerHistoryError(
                "FORWARD_CA_BLOCKER_HISTORY_BLOCKED_EVIDENCE_PRESENT"
            )
    elif status == RESOLVED_CERTIFIED:
        if category not in {CERTIFIED_LIVE, HISTORICAL_OBSERVED}:
            raise ForwardCABlockerHistoryError(
                "FORWARD_CA_BLOCKER_HISTORY_CERTIFIED_CATEGORY_INVALID"
            )
        if not event_id or not event_sha256:
            raise ForwardCABlockerHistoryError(
                "FORWARD_CA_BLOCKER_HISTORY_CERTIFIED_EVIDENCE_MISSING"
            )
        if resolution_identity is not None:
            raise ForwardCABlockerHistoryError(
                "FORWARD_CA_BLOCKER_HISTORY_CERTIFIED_REPLACEMENT_UNEXPECTED"
            )
    elif status == RESOLVED_SUPERSEDED:
        if category != SUPERSEDED or not resolution_identity:
            raise ForwardCABlockerHistoryError(
                "FORWARD_CA_BLOCKER_HISTORY_SUPERSEDED_RESOLUTION_INVALID"
            )
        if event_id is not None or event_sha256 is not None:
            raise ForwardCABlockerHistoryError(
                "FORWARD_CA_BLOCKER_HISTORY_SUPERSEDED_EVIDENCE_UNEXPECTED"
            )
    else:
        raise ForwardCABlockerHistoryError(
            "FORWARD_CA_BLOCKER_HISTORY_STATUS_INVALID"
        )

    return CABlockerHistoryEntry(
        batch_id=batch_id,
        as_of_date=as_of_date,
        query_window_from=query_window_from,
        query_window_to=query_window_to,
        announcement_identity=identity,
        ticker=ticker,
        status=status,
        disposition_category=category,
        reason=reason,
        resolution_identity=resolution_identity,
        event_id=event_id,
        event_sha256=event_sha256,
    )


def normalize_blocker_history(
    history: Sequence[CABlockerHistoryEntry],
) -> tuple[CABlockerHistoryEntry, ...]:
    normalized: list[CABlockerHistoryEntry] = []
    seen_batch_identity: dict[tuple[str, str], CABlockerHistoryEntry] = {}
    ticker_by_identity: dict[str, str] = {}
    status_by_identity: dict[str, str] = {}

    for raw in history:
        entry = _validate_entry(raw)
        key = (entry.batch_id, entry.announcement_identity)
        previous_same_batch = seen_batch_identity.get(key)
        if previous_same_batch is not None:
            if previous_same_batch != entry:
                raise ForwardCABlockerHistoryError(
                    "FORWARD_CA_BLOCKER_HISTORY_BATCH_IDENTITY_CONFLICT"
                )
            raise ForwardCABlockerHistoryError(
                "FORWARD_CA_BLOCKER_HISTORY_DUPLICATE_ENTRY"
            )
        seen_batch_identity[key] = entry

        previous_ticker = ticker_by_identity.get(entry.announcement_identity)
        if previous_ticker is not None and previous_ticker != entry.ticker:
            raise ForwardCABlockerHistoryError(
                "FORWARD_CA_BLOCKER_HISTORY_IDENTITY_TICKER_CHANGED"
            )
        ticker_by_identity[entry.announcement_identity] = entry.ticker

        previous_status = status_by_identity.get(entry.announcement_identity)
        if previous_status in {RESOLVED_CERTIFIED, RESOLVED_SUPERSEDED}:
            if entry.status == BLOCKED:
                raise ForwardCABlockerHistoryError(
                    "FORWARD_CA_BLOCKER_HISTORY_RESOLUTION_REGRESSED"
                )
        if previous_status is None and entry.status != BLOCKED:
            raise ForwardCABlockerHistoryError(
                "FORWARD_CA_BLOCKER_HISTORY_RESOLUTION_WITHOUT_BLOCKER"
            )
        status_by_identity[entry.announcement_identity] = entry.status
        normalized.append(entry)

    return tuple(normalized)


def _current_dispositions(
    result: DividendDispositionResult,
) -> dict[str, DividendDisposition]:
    if not isinstance(result, DividendDispositionResult):
        raise ForwardCABlockerHistoryError(
            "FORWARD_CA_BLOCKER_HISTORY_RESULT_INVALID"
        )

    by_identity: dict[str, DividendDisposition] = {}
    for disposition in result.dispositions:
        if not isinstance(disposition, DividendDisposition):
            raise ForwardCABlockerHistoryError(
                "FORWARD_CA_BLOCKER_HISTORY_DISPOSITION_INVALID"
            )
        identity = _validate_identity(
            disposition.announcement_identity,
            _ticker(disposition.ticker),
        )
        if identity in by_identity:
            raise ForwardCABlockerHistoryError(
                "FORWARD_CA_BLOCKER_HISTORY_CURRENT_IDENTITY_CONFLICT"
            )
        by_identity[identity] = DividendDisposition(
            announcement_identity=identity,
            ticker=_ticker(disposition.ticker),
            category=_text(
                disposition.category,
                "FORWARD_CA_BLOCKER_HISTORY_CATEGORY_INVALID",
            ),
            reason=_text(
                disposition.reason,
                "FORWARD_CA_BLOCKER_HISTORY_REASON_INVALID",
            ),
            event_id=disposition.event_id,
            event_sha256=disposition.event_sha256,
            superseded_by=disposition.superseded_by,
        )
    return by_identity


def _resolution_for(
    disposition: DividendDisposition,
) -> tuple[str, str | None, str | None, str | None]:
    if disposition.category in {CERTIFIED_LIVE, HISTORICAL_OBSERVED}:
        if not disposition.event_id or not disposition.event_sha256:
            return ("", None, None, None)
        return (
            RESOLVED_CERTIFIED,
            None,
            disposition.event_id,
            disposition.event_sha256,
        )
    if disposition.category == SUPERSEDED and disposition.superseded_by:
        return (
            RESOLVED_SUPERSEDED,
            disposition.superseded_by,
            None,
            None,
        )
    return ("", None, None, None)


def append_blocker_resolution_history(
    history: Sequence[CABlockerHistoryEntry],
    *,
    batch_id: str,
    as_of_date: str,
    query_window_from: str,
    query_window_to: str,
    result: DividendDispositionResult,
) -> tuple[CABlockerHistoryEntry, ...]:
    """Append V1 blocker observations and supported resolutions.

    A candidate missing from a later query is left open.  Only the same
    announcement identity returning with certified evidence, or with a
    defensible correction replacement, resolves a prior blocker.  Replaying
    an exact batch is idempotent; a different result under the same batch id
    fails closed.
    """

    prior = normalize_blocker_history(history)
    current = _current_dispositions(result)
    batch_id = _text(
        batch_id,
        "FORWARD_CA_BLOCKER_HISTORY_BATCH_ID_INVALID",
    )
    as_of_date = _date(
        as_of_date,
        "FORWARD_CA_BLOCKER_HISTORY_ASOF_INVALID",
    )
    query_window_from = _date(
        query_window_from,
        "FORWARD_CA_BLOCKER_HISTORY_WINDOW_FROM_INVALID",
    )
    query_window_to = _date(
        query_window_to,
        "FORWARD_CA_BLOCKER_HISTORY_WINDOW_TO_INVALID",
    )
    if query_window_to < query_window_from:
        raise ForwardCABlockerHistoryError(
            "FORWARD_CA_BLOCKER_HISTORY_WINDOW_REVERSED"
        )

    latest: dict[str, CABlockerHistoryEntry] = {}
    for entry in prior:
        latest[entry.announcement_identity] = entry

    same_batch = {
        entry.announcement_identity: entry
        for entry in prior
        if entry.batch_id == batch_id
    }
    additions: list[CABlockerHistoryEntry] = []

    for identity, disposition in current.items():
        previous = latest.get(identity)
        resolution_status, resolution_identity, event_id, event_sha256 = _resolution_for(
            disposition
        )
        if disposition.category == BLOCKED_LIVE_UNRESOLVED:
            proposed = CABlockerHistoryEntry(
                batch_id=batch_id,
                as_of_date=as_of_date,
                query_window_from=query_window_from,
                query_window_to=query_window_to,
                announcement_identity=identity,
                ticker=disposition.ticker,
                status=BLOCKED,
                disposition_category=disposition.category,
                reason=disposition.reason,
            )
            validated = _validate_entry(proposed)
            existing = same_batch.get(identity)
            if existing is not None:
                if existing != validated:
                    raise ForwardCABlockerHistoryError(
                        "FORWARD_CA_BLOCKER_HISTORY_BATCH_IDENTITY_CONFLICT"
                    )
                continue
            if previous is not None and previous.status != BLOCKED:
                raise ForwardCABlockerHistoryError(
                    "FORWARD_CA_BLOCKER_HISTORY_RESOLUTION_REGRESSED"
                )
            additions.append(validated)
            latest[identity] = validated
            continue

        if not resolution_status or previous is None or previous.status != BLOCKED:
            continue

        proposed = CABlockerHistoryEntry(
            batch_id=batch_id,
            as_of_date=as_of_date,
            query_window_from=query_window_from,
            query_window_to=query_window_to,
            announcement_identity=identity,
            ticker=disposition.ticker,
            status=resolution_status,
            disposition_category=disposition.category,
            reason=disposition.reason,
            resolution_identity=resolution_identity,
            event_id=event_id,
            event_sha256=event_sha256,
        )
        validated = _validate_entry(proposed)
        existing = same_batch.get(identity)
        if existing is not None:
            if existing != validated:
                raise ForwardCABlockerHistoryError(
                    "FORWARD_CA_BLOCKER_HISTORY_BATCH_IDENTITY_CONFLICT"
                )
            continue
        additions.append(validated)
        latest[identity] = validated

    return normalize_blocker_history((*prior, *additions))


def blocker_history_payload(
    history: Sequence[CABlockerHistoryEntry],
) -> dict[str, Any]:
    normalized = normalize_blocker_history(history)
    return {
        "schema_version": HISTORY_SCHEMA,
        "entries": [asdict(entry) for entry in normalized],
    }


def blocker_history_sha256(
    history: Sequence[CABlockerHistoryEntry],
) -> str:
    blob = json.dumps(
        blocker_history_payload(history),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()
