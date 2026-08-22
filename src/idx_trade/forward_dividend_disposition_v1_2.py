from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import re
from typing import Any, Iterable, Mapping, Sequence


CERTIFIED_LIVE = "CERTIFIED_LIVE"
HISTORICAL_OBSERVED = "HISTORICAL_OBSERVED"
CORROBORATING_ONLY = "CORROBORATING_ONLY"
SUPERSEDED = "SUPERSEDED"
BLOCKED_LIVE_UNRESOLVED = "BLOCKED_LIVE_UNRESOLVED"

_CORROBORATION_TERMS = (
    "bukti iklan",
    "advertisement",
    "proof publication",
    "bukti publikasi",
)
_CORRECTION_TERMS = (
    "koreksi",
    "correction",
    "revisi",
    "revision",
)


class DividendDispositionError(RuntimeError):
    pass


@dataclass(frozen=True)
class DividendDispositionCandidate:
    announcement_identity: str
    ticker: str
    announcement_timestamp: str
    title: str
    event_id: str | None = None
    event_sha256: str | None = None
    gross_dividend_per_share_idr: str | None = None
    cum_date: str | None = None
    ex_date: str | None = None
    record_date: str | None = None
    payment_date: str | None = None
    document_sha256: tuple[str, ...] = ()
    review_status: str | None = None
    semantic_failures: tuple[str, ...] = ()


@dataclass(frozen=True)
class DividendDisposition:
    announcement_identity: str
    ticker: str
    category: str
    reason: str
    event_id: str | None
    event_sha256: str | None
    superseded_by: str | None = None


@dataclass(frozen=True)
class DividendDispositionResult:
    dispositions: tuple[DividendDisposition, ...]
    live_events: tuple[DividendDispositionCandidate, ...]
    blockers: tuple[DividendDisposition, ...]


def _canonical_identity(candidate: Mapping[str, Any]) -> str:
    ticker = str(candidate.get("ticker") or "").strip().upper()
    number = str(candidate.get("announcement_number") or "").strip()
    announcement_id = str(candidate.get("announcement_id") or "").strip()

    if not ticker or not (number or announcement_id):
        raise DividendDispositionError("DISPOSITION_ANNOUNCEMENT_IDENTITY_MISSING")

    return f"{ticker}|NUMBER|{number}" if number else f"{ticker}|ID|{announcement_id}"


def _iso_date(value: object, code: str) -> str:
    text = str(value or "").strip()
    try:
        parsed = date.fromisoformat(text[:10])
    except ValueError as exc:
        raise DividendDispositionError(code) from exc
    return parsed.isoformat()


def _date_from_timestamp(value: object) -> date:
    text = str(value or "").strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise DividendDispositionError("DISPOSITION_ANNOUNCEMENT_DATE_INVALID") from exc


def _event_value(event: object, name: str) -> str | None:
    value = getattr(event, name, None)
    if value is None:
        return None
    return str(value)


def candidate_from_review(
    candidate: Mapping[str, Any],
    *,
    review: Mapping[str, Any] | None = None,
    event: object | None = None,
    semantic_failures: Iterable[object] = (),
) -> DividendDispositionCandidate:
    identity = _canonical_identity(candidate)
    documents: set[str] = set()

    if isinstance(review, Mapping):
        for row in review.get("documents") or ():
            if isinstance(row, Mapping):
                value = str(row.get("sha256") or "").strip().lower()
                if value:
                    documents.add(value)

    failure_values = tuple(sorted({str(x) for x in semantic_failures if str(x)}))
    if isinstance(review, Mapping):
        failure_values = tuple(sorted({
            *failure_values,
            *(str(x) for x in (review.get("failures") or ()) if str(x)),
        }))

    return DividendDispositionCandidate(
        announcement_identity=identity,
        ticker=str(candidate.get("ticker") or "").strip().upper(),
        announcement_timestamp=str(
            candidate.get("announcement_timestamp")
            or candidate.get("announcement_date")
            or ""
        ).strip(),
        title=str(candidate.get("title") or "").strip(),
        event_id=_event_value(event, "event_id"),
        event_sha256=_event_value(event, "source_evidence_sha256"),
        gross_dividend_per_share_idr=_event_value(
            event,
            "gross_dividend_per_share_idr",
        ),
        cum_date=_event_value(event, "cum_date"),
        ex_date=_event_value(event, "ex_date"),
        record_date=_event_value(event, "record_date"),
        payment_date=_event_value(event, "payment_date"),
        document_sha256=tuple(sorted(documents)),
        review_status=(
            str(review.get("status") or "").strip()
            if isinstance(review, Mapping)
            else None
        ),
        semantic_failures=failure_values,
    )


def _has_term(title: str, terms: Sequence[str]) -> bool:
    lowered = title.casefold()
    return any(term in lowered for term in terms)


def _has_event(candidate: DividendDispositionCandidate) -> bool:
    return bool(
        candidate.event_id
        and candidate.event_sha256
        and candidate.gross_dividend_per_share_idr
        and candidate.cum_date
        and candidate.ex_date
        and candidate.record_date
        and candidate.payment_date
    )


def _same_economic_event(
    left: DividendDispositionCandidate,
    right: DividendDispositionCandidate,
) -> bool:
    if left.ticker != right.ticker:
        return False

    left_docs = set(left.document_sha256)
    right_docs = set(right.document_sha256)
    if left_docs and right_docs and left_docs.intersection(right_docs):
        return True

    comparable = (
        left.cum_date,
        left.ex_date,
        left.record_date,
        left.payment_date,
        left.gross_dividend_per_share_idr,
    )
    return all(value is not None for value in comparable) and comparable == (
        right.cum_date,
        right.ex_date,
        right.record_date,
        right.payment_date,
        right.gross_dividend_per_share_idr,
    )


def _historical_completed(
    candidate: DividendDispositionCandidate,
    as_of: date,
) -> bool:
    return bool(
        candidate.payment_date
        and date.fromisoformat(candidate.payment_date) < as_of
    )


def _relevant_at_as_of(
    candidate: DividendDispositionCandidate,
    as_of: date,
) -> bool:
    """Return whether a published candidate can affect this snapshot."""
    return _date_from_timestamp(candidate.announcement_timestamp) <= as_of


def apply_temporal_disposition(
    candidates: Sequence[DividendDispositionCandidate],
    *,
    as_of_date: str,
) -> DividendDispositionResult:
    as_of = date.fromisoformat(_iso_date(as_of_date, "DISPOSITION_ASOF_INVALID"))
    by_identity: dict[str, DividendDispositionCandidate] = {}

    for candidate in candidates:
        if candidate.announcement_identity in by_identity:
            previous = by_identity[candidate.announcement_identity]
            if previous != candidate:
                raise DividendDispositionError(
                    "DISPOSITION_CONFLICTING_ANNOUNCEMENT_IDENTITY:"
                    + candidate.announcement_identity
                )
            continue
        by_identity[candidate.announcement_identity] = candidate

    ordered = sorted(
        by_identity.values(),
        key=lambda row: (
            row.ticker,
            _date_from_timestamp(row.announcement_timestamp),
            row.announcement_identity,
        ),
    )

    # A later correction with the same defensible economic/document lineage
    # replaces the earlier version, including when the earlier version had
    # already completed.  A live correction with a different economic event
    # must not silently coexist with the earlier live event.
    superseded_by: dict[str, DividendDispositionCandidate] = {}
    for later in ordered:
        if not _has_event(later) or not _has_term(
            later.title,
            _CORRECTION_TERMS,
        ):
            continue
        for earlier in ordered:
            if (
                earlier.ticker != later.ticker
                or earlier.announcement_identity
                == later.announcement_identity
                or _date_from_timestamp(
                    earlier.announcement_timestamp
                ) >= _date_from_timestamp(
                    later.announcement_timestamp
                )
                or not _has_event(earlier)
                or not _relevant_at_as_of(earlier, as_of)
                or not _relevant_at_as_of(later, as_of)
            ):
                continue
            if _same_economic_event(earlier, later):
                superseded_by[earlier.announcement_identity] = later
            elif not _historical_completed(earlier, as_of):
                raise DividendDispositionError(
                    "DISPOSITION_CONFLICTING_LIVE_CORRECTION:"
                    + earlier.announcement_identity
                    + "->"
                    + later.announcement_identity
                )

    dispositions: list[DividendDisposition] = []

    for candidate in ordered:
        replacement = superseded_by.get(
            candidate.announcement_identity
        )
        if replacement is not None:
            dispositions.append(DividendDisposition(
                candidate.announcement_identity,
                candidate.ticker,
                SUPERSEDED,
                "CORRECTION_CHAIN_RESOLVED_BY_LATER_CERTIFIED_EVIDENCE",
                candidate.event_id,
                candidate.event_sha256,
                replacement.announcement_identity,
            ))
            continue

        if _has_event(candidate):
            if _has_term(candidate.title, _CORROBORATION_TERMS):
                dispositions.append(DividendDisposition(
                    candidate.announcement_identity,
                    candidate.ticker,
                    CORROBORATING_ONLY,
                    "ADVERTISEMENT_OR_PUBLICATION_PROOF",
                    candidate.event_id,
                    candidate.event_sha256,
                ))
            elif _historical_completed(candidate, as_of):
                dispositions.append(DividendDisposition(
                    candidate.announcement_identity,
                    candidate.ticker,
                    HISTORICAL_OBSERVED,
                    "PAYMENT_COMPLETED_BEFORE_AS_OF",
                    candidate.event_id,
                    candidate.event_sha256,
                ))
            else:
                dispositions.append(DividendDisposition(
                    candidate.announcement_identity,
                    candidate.ticker,
                    CERTIFIED_LIVE,
                    "CERTIFIED_EVENT_RELEVANT_AT_AS_OF",
                    candidate.event_id,
                    candidate.event_sha256,
                ))
            continue

        later_replacement = next(
            (
                other for other in ordered
                if (
                    other.ticker == candidate.ticker
                    and _has_event(other)
                    and _has_term(other.title, _CORRECTION_TERMS)
                    and _same_economic_event(candidate, other)
                    and _date_from_timestamp(other.announcement_timestamp)
                    > _date_from_timestamp(candidate.announcement_timestamp)
                )
            ),
            None,
        )
        if later_replacement is not None:
            dispositions.append(DividendDisposition(
                candidate.announcement_identity,
                candidate.ticker,
                SUPERSEDED,
                "CORRECTION_CHAIN_RESOLVED_BY_LATER_CERTIFIED_EVIDENCE",
                None,
                None,
                later_replacement.announcement_identity,
            ))
            continue

        prior_event = next(
            (
                other for other in reversed(ordered)
                if (
                    other.ticker == candidate.ticker
                    and _has_event(other)
                    and _date_from_timestamp(other.announcement_timestamp)
                    < _date_from_timestamp(candidate.announcement_timestamp)
                    and (
                        _has_term(candidate.title, _CORROBORATION_TERMS)
                        or (
                            other.payment_date
                            and date.fromisoformat(other.payment_date)
                            < _date_from_timestamp(candidate.announcement_timestamp)
                        )
                    )
                )
            ),
            None,
        )
        if prior_event is not None:
            dispositions.append(DividendDisposition(
                candidate.announcement_identity,
                candidate.ticker,
                CORROBORATING_ONLY,
                "POST_EVENT_OR_CORROBORATING_REPORT_WITHOUT_PAYABLE_SCHEDULE",
                None,
                None,
                prior_event.announcement_identity,
            ))
            continue

        dispositions.append(DividendDisposition(
            candidate.announcement_identity,
            candidate.ticker,
            BLOCKED_LIVE_UNRESOLVED,
            "NO_CERTIFIED_EVENT_OR_DEFENSIBLE_LINEAGE",
            None,
            None,
        ))

    by_event: dict[str, DividendDisposition] = {}
    live: list[DividendDispositionCandidate] = []
    blockers: list[DividendDisposition] = []

    for disposition in dispositions:
        if disposition.category == CERTIFIED_LIVE:
            candidate = by_identity[disposition.announcement_identity]
            assert candidate.event_id is not None
            previous = by_event.get(candidate.event_id)
            if previous is not None and previous != disposition:
                raise DividendDispositionError(
                    "DISPOSITION_LIVE_EVENT_DUPLICATE_CONFLICT:"
                    + candidate.event_id
                )
            by_event[candidate.event_id] = disposition
            live.append(candidate)
        elif disposition.category == BLOCKED_LIVE_UNRESOLVED:
            blockers.append(disposition)

    return DividendDispositionResult(
        dispositions=tuple(dispositions),
        live_events=tuple(live),
        blockers=tuple(blockers),
    )


def disposition_payload(result: DividendDispositionResult) -> dict[str, Any]:
    return {
        "schema_version": "idx_trade_forward_dividend_disposition_v1_2",
        "dispositions": [asdict(row) for row in result.dispositions],
        "live_event_ids": [row.event_id for row in result.live_events],
        "blocker_identities": [row.announcement_identity for row in result.blockers],
    }
