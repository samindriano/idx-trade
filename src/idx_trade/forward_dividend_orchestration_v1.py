from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable, Mapping, Sequence


class ForwardDividendOrchestrationError(RuntimeError):
    pass


POLICY_ID = "FORWARD_DIVIDEND_ORCHESTRATION_V1"
JOURNAL_SCHEMA = "idx_trade_forward_dividend_acquisition_journal_v1"
PREOPEN = "PREOPEN"
POST_EOD = "POST_EOD"
_CAPTURE_PHASE_ORDER = {
    PREOPEN: 0,
    POST_EOD: 1,
}
BOOTSTRAP_LOOKBACK_DAYS = 366
INCREMENTAL_OVERLAP_DAYS = 7
BLOCKER_RESOLUTION_CERTIFIED_LIVE = "CERTIFIED_LIVE"
BLOCKER_RESOLUTION_HISTORICAL_OBSERVED = "HISTORICAL_OBSERVED"
_BLOCKER_RESOLUTION_STATUSES = frozenset({
    BLOCKER_RESOLUTION_CERTIFIED_LIVE,
    BLOCKER_RESOLUTION_HISTORICAL_OBSERVED,
})
_DISPOSITION_STATUSES = frozenset({
    "CERTIFIED_LIVE",
    "HISTORICAL_OBSERVED",
    "CORROBORATING_ONLY",
    "SUPERSEDED",
    "BLOCKED_LIVE_UNRESOLVED",
})


@dataclass(frozen=True)
class DividendCoverage:
    ticker: str
    covered_through: str


@dataclass(frozen=True)
class CertifiedDividendJournalEntry:
    announcement_identity: str
    ticker: str
    event_id: str
    event_sha256: str
    evidence_dir: str
    review_sha256: str
    review_filename: str = "ATTACHMENT_REVIEW.json"


@dataclass(frozen=True)
class BlockingDividendJournalEntry:
    announcement_identity: str
    ticker: str
    classification: str


@dataclass(frozen=True)
class DividendBlockerResolutionEntry:
    blocker_announcement_identity: str
    blocker_ticker: str
    blocker_classification: str
    resolver_announcement_identity: str
    resolver_ticker: str
    resolver_event_id: str
    resolver_event_sha256: str
    resolver_evidence_dir: str
    resolver_review_sha256: str
    resolver_status: str
    resolver_review_filename: str = "ATTACHMENT_REVIEW.json"


@dataclass(frozen=True)
class DividendAcquisitionJournal:
    as_of_date: str
    required_tickers: tuple[str, ...]
    coverage: tuple[DividendCoverage, ...]
    certified_events: tuple[CertifiedDividendJournalEntry, ...] = ()
    # Current payable/live projection.  `certified_history` is the immutable
    # evidence registry and must survive historical/superseded transitions.
    certified_history: tuple[CertifiedDividendJournalEntry, ...] = ()
    blockers: tuple[BlockingDividendJournalEntry, ...] = ()
    capture_phase: str = POST_EOD
    blocker_resolution_history: tuple[
        DividendBlockerResolutionEntry, ...
    ] = ()


@dataclass(frozen=True)
class DividendDiscoveryPlan:
    as_of_date: str
    required_tickers: tuple[str, ...]
    date_from: str
    date_to: str


_TICKER_RE = re.compile(r"^[A-Z0-9]{1,12}$")


def _iso(value: object, code: str) -> str:
    text = str(value or "").strip()

    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ForwardDividendOrchestrationError(code) from exc

    if parsed.isoformat() != text:
        raise ForwardDividendOrchestrationError(code)

    return text


def normalize_capture_phase(value: object) -> str:
    phase = str(value or "").strip().upper()

    if phase not in _CAPTURE_PHASE_ORDER:
        raise ForwardDividendOrchestrationError(
            f"FORWARD_DIVIDEND_ORCHESTRATION_CAPTURE_PHASE_INVALID:{phase}"
        )

    return phase


def _journal_order_key(
    journal: DividendAcquisitionJournal,
) -> tuple[date, int]:
    canonical_date = date.fromisoformat(
        _iso(
            journal.as_of_date,
            "FORWARD_DIVIDEND_ORCHESTRATION_JOURNAL_DATE_INVALID",
        )
    )

    phase = normalize_capture_phase(
        journal.capture_phase
    )

    return (
        canonical_date,
        _CAPTURE_PHASE_ORDER[phase],
    )


def normalize_tickers(values: Iterable[object]) -> tuple[str, ...]:
    result = set()

    for raw in values:
        ticker = str(raw or "").strip().upper()

        if not _TICKER_RE.fullmatch(ticker):
            raise ForwardDividendOrchestrationError(
                f"FORWARD_DIVIDEND_ORCHESTRATION_TICKER_INVALID:{ticker}"
            )

        result.add(ticker)

    return tuple(sorted(result))


def required_execution_tickers(
    *,
    actual_positions: Iterable[object],
    pending_buys: Iterable[object],
    pending_sells: Iterable[object],
    decision_targets: Iterable[object],
) -> tuple[str, ...]:
    return normalize_tickers(
        (
            *actual_positions,
            *pending_buys,
            *pending_sells,
            *decision_targets,
        )
    )


def normalize_coverage(
    rows: Sequence[DividendCoverage],
) -> tuple[DividendCoverage, ...]:
    result = {}

    for row in rows:
        if not isinstance(row, DividendCoverage):
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_COVERAGE_ROW_INVALID"
            )

        ticker = normalize_tickers((row.ticker,))[0]
        covered = _iso(
            row.covered_through,
            "FORWARD_DIVIDEND_ORCHESTRATION_COVERAGE_DATE_INVALID",
        )

        previous = result.get(ticker)

        if previous is not None and previous != covered:
            raise ForwardDividendOrchestrationError(
                f"FORWARD_DIVIDEND_ORCHESTRATION_COVERAGE_CONFLICT:{ticker}"
            )

        result[ticker] = covered

    return tuple(
        DividendCoverage(ticker=ticker, covered_through=result[ticker])
        for ticker in sorted(result)
    )


def plan_discovery(
    *,
    as_of_date: str,
    required_tickers: Iterable[object],
    prior_coverage: Sequence[DividendCoverage] = (),
) -> DividendDiscoveryPlan:
    as_of = date.fromisoformat(
        _iso(
            as_of_date,
            "FORWARD_DIVIDEND_ORCHESTRATION_ASOF_INVALID",
        )
    )

    tickers = normalize_tickers(required_tickers)

    if not tickers:
        raise ForwardDividendOrchestrationError(
            "FORWARD_DIVIDEND_ORCHESTRATION_REQUIRED_TICKERS_EMPTY"
        )

    coverage = {
        row.ticker: date.fromisoformat(row.covered_through)
        for row in normalize_coverage(prior_coverage)
    }

    starts = []

    for ticker in tickers:
        previous = coverage.get(ticker)

        if previous is None:
            start = as_of - timedelta(
                days=BOOTSTRAP_LOOKBACK_DAYS
            )
        else:
            if previous > as_of:
                raise ForwardDividendOrchestrationError(
                    f"FORWARD_DIVIDEND_ORCHESTRATION_COVERAGE_IN_FUTURE:{ticker}"
                )

            start = previous - timedelta(
                days=INCREMENTAL_OVERLAP_DAYS
            )

        starts.append(start)

    return DividendDiscoveryPlan(
        as_of_date=as_of.isoformat(),
        required_tickers=tickers,
        date_from=min(starts).isoformat(),
        date_to=as_of.isoformat(),
    )


def normalize_certified_entries(
    rows: Sequence[CertifiedDividendJournalEntry],
) -> tuple[CertifiedDividendJournalEntry, ...]:
    by_identity = {}
    by_event = {}

    for row in rows:
        if not isinstance(row, CertifiedDividendJournalEntry):
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_CERTIFIED_ROW_INVALID"
            )

        ticker = normalize_tickers((row.ticker,))[0]
        identity = str(row.announcement_identity or "").strip()
        event_id = str(row.event_id or "").strip()
        event_sha = str(row.event_sha256 or "").strip().lower()
        evidence_dir = str(row.evidence_dir or "").strip()
        review_sha = str(row.review_sha256 or "").strip().lower()
        review_filename = str(
            row.review_filename
            or "ATTACHMENT_REVIEW.json"
        ).strip()

        if not identity or not event_id:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_CERTIFIED_IDENTITY_MISSING"
            )

        if not re.fullmatch(r"[0-9a-f]{64}", event_sha):
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_EVENT_SHA_INVALID"
            )

        if not evidence_dir:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_EVIDENCE_DIR_MISSING"
            )

        if not re.fullmatch(r"[0-9a-f]{64}", review_sha):
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_REVIEW_SHA_INVALID"
            )

        if review_filename not in {
            "ATTACHMENT_REVIEW.json",
            "ATTACHMENT_REVIEW_V1_2.json",
        }:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_REVIEW_FILENAME_INVALID"
            )

        canonical = CertifiedDividendJournalEntry(
            announcement_identity=identity,
            ticker=ticker,
            event_id=event_id,
            event_sha256=event_sha,
            evidence_dir=evidence_dir,
            review_sha256=review_sha,
            review_filename=review_filename,
        )

        previous = by_identity.get(identity)

        if previous is not None and previous != canonical:
            raise ForwardDividendOrchestrationError(
                f"FORWARD_DIVIDEND_ORCHESTRATION_ANNOUNCEMENT_CONFLICT:{identity}"
            )

        previous_event = by_event.get(event_id)

        if previous_event is not None and previous_event != canonical:
            raise ForwardDividendOrchestrationError(
                f"FORWARD_DIVIDEND_ORCHESTRATION_EVENT_CONFLICT:{event_id}"
            )

        by_identity[identity] = canonical
        by_event[event_id] = canonical

    return tuple(
        by_identity[key]
        for key in sorted(by_identity)
    )


def normalize_blockers(
    rows: Sequence[BlockingDividendJournalEntry],
) -> tuple[BlockingDividendJournalEntry, ...]:
    by_identity = {}

    for row in rows:
        if not isinstance(row, BlockingDividendJournalEntry):
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_ROW_INVALID"
            )

        ticker = normalize_tickers((row.ticker,))[0]
        identity = str(row.announcement_identity or "").strip()
        classification = str(row.classification or "").strip()

        if not identity or not classification:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_IDENTITY_MISSING"
            )

        canonical = BlockingDividendJournalEntry(
            announcement_identity=identity,
            ticker=ticker,
            classification=classification,
        )

        previous = by_identity.get(identity)

        if previous is not None and previous != canonical:
            raise ForwardDividendOrchestrationError(
                f"FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_CONFLICT:{identity}"
            )

        by_identity[identity] = canonical

    return tuple(
        by_identity[key]
        for key in sorted(by_identity)
    )


def _resolver_entry(
    row: DividendBlockerResolutionEntry,
) -> CertifiedDividendJournalEntry:
    return CertifiedDividendJournalEntry(
        announcement_identity=row.resolver_announcement_identity,
        ticker=row.resolver_ticker,
        event_id=row.resolver_event_id,
        event_sha256=row.resolver_event_sha256,
        evidence_dir=row.resolver_evidence_dir,
        review_sha256=row.resolver_review_sha256,
        review_filename=row.resolver_review_filename,
    )


def normalize_blocker_resolutions(
    rows: Sequence[DividendBlockerResolutionEntry],
) -> tuple[DividendBlockerResolutionEntry, ...]:
    by_blocker = {}
    by_resolver = {}

    for row in rows:
        if not isinstance(row, DividendBlockerResolutionEntry):
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_RESOLUTION_ROW_INVALID"
            )

        blocker_identity = str(
            row.blocker_announcement_identity or ""
        ).strip()
        blocker_ticker = normalize_tickers((row.blocker_ticker,))[0]
        blocker_classification = str(
            row.blocker_classification or ""
        ).strip()
        resolver_identity = str(
            row.resolver_announcement_identity or ""
        ).strip()
        resolver_ticker = normalize_tickers((row.resolver_ticker,))[0]
        resolver_event_id = str(row.resolver_event_id or "").strip()
        resolver_event_sha = str(
            row.resolver_event_sha256 or ""
        ).strip().lower()
        resolver_evidence_dir = str(
            row.resolver_evidence_dir or ""
        ).strip()
        resolver_review_sha = str(
            row.resolver_review_sha256 or ""
        ).strip().lower()
        resolver_status = str(row.resolver_status or "").strip().upper()
        resolver_review_filename = str(
            row.resolver_review_filename or "ATTACHMENT_REVIEW.json"
        ).strip()

        if not blocker_identity or not blocker_classification:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_RESOLUTION_BLOCKER_MISSING"
            )

        if not resolver_identity or not resolver_event_id:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_RESOLUTION_RESOLVER_MISSING"
            )

        if blocker_ticker != resolver_ticker:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_RESOLUTION_TICKER_MISMATCH:"
                + blocker_identity
            )

        if blocker_identity == resolver_identity:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_RESOLUTION_SELF_REFERENCE:"
                + blocker_identity
            )

        if not re.fullmatch(r"[0-9a-f]{64}", resolver_event_sha):
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_RESOLUTION_EVENT_SHA_INVALID"
            )

        if not resolver_evidence_dir:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_RESOLUTION_EVIDENCE_DIR_MISSING"
            )

        if not re.fullmatch(r"[0-9a-f]{64}", resolver_review_sha):
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_RESOLUTION_REVIEW_SHA_INVALID"
            )

        if resolver_status not in _BLOCKER_RESOLUTION_STATUSES:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_RESOLUTION_STATUS_INVALID:"
                + resolver_status
            )

        if resolver_review_filename not in {
            "ATTACHMENT_REVIEW.json",
            "ATTACHMENT_REVIEW_V1_2.json",
        }:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_RESOLUTION_REVIEW_FILENAME_INVALID"
            )

        canonical = DividendBlockerResolutionEntry(
            blocker_announcement_identity=blocker_identity,
            blocker_ticker=blocker_ticker,
            blocker_classification=blocker_classification,
            resolver_announcement_identity=resolver_identity,
            resolver_ticker=resolver_ticker,
            resolver_event_id=resolver_event_id,
            resolver_event_sha256=resolver_event_sha,
            resolver_evidence_dir=resolver_evidence_dir,
            resolver_review_sha256=resolver_review_sha,
            resolver_status=resolver_status,
            resolver_review_filename=resolver_review_filename,
        )

        previous = by_blocker.get(blocker_identity)

        if previous is not None and previous != canonical:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_RESOLUTION_CONFLICT:"
                + blocker_identity
            )

        previous_resolver = by_resolver.get(resolver_identity)

        if previous_resolver is not None and previous_resolver != canonical:
            resolver_fields = (
                "resolver_ticker",
                "resolver_event_id",
                "resolver_event_sha256",
                "resolver_evidence_dir",
                "resolver_review_sha256",
                "resolver_status",
                "resolver_review_filename",
            )
            if any(
                getattr(previous_resolver, field)
                != getattr(canonical, field)
                for field in resolver_fields
            ):
                raise ForwardDividendOrchestrationError(
                    "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_RESOLUTION_RESOLVER_CONFLICT:"
                    + resolver_identity
                )

        by_blocker[blocker_identity] = canonical
        by_resolver[resolver_identity] = canonical

    return tuple(
        by_blocker[key]
        for key in sorted(by_blocker)
    )


def normalize_journal(
    journal: DividendAcquisitionJournal,
) -> DividendAcquisitionJournal:
    if not isinstance(journal, DividendAcquisitionJournal):
        raise ForwardDividendOrchestrationError(
            "FORWARD_DIVIDEND_ORCHESTRATION_JOURNAL_REQUIRED"
        )

    as_of = _iso(
        journal.as_of_date,
        "FORWARD_DIVIDEND_ORCHESTRATION_JOURNAL_DATE_INVALID",
    )

    required = normalize_tickers(journal.required_tickers)
    phase = normalize_capture_phase(journal.capture_phase)
    coverage = normalize_coverage(journal.coverage)
    certified = normalize_certified_entries(
        journal.certified_events
    )
    certified_history = normalize_certified_entries(
        journal.certified_history
    )
    history_by_identity = {
        row.announcement_identity: row
        for row in certified_history
    }
    for row in certified:
        previous = history_by_identity.get(row.announcement_identity)
        if previous is not None and previous != row:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_CERTIFIED_HISTORY_CHANGED:"
                + row.announcement_identity
            )
        history_by_identity[row.announcement_identity] = row
    blockers = normalize_blockers(journal.blockers)
    blocker_resolution_history = normalize_blocker_resolutions(
        journal.blocker_resolution_history
    )

    certified_ids = {
        row.announcement_identity
        for row in certified
    }

    blocker_ids = {
        row.announcement_identity
        for row in blockers
    }

    overlap = certified_ids & blocker_ids

    if overlap:
        raise ForwardDividendOrchestrationError(
            "FORWARD_DIVIDEND_ORCHESTRATION_CERTIFIED_BLOCKER_OVERLAP:"
            + ",".join(sorted(overlap))
        )

    history_blocker_ids = {
        row.blocker_announcement_identity
        for row in blocker_resolution_history
    }

    unresolved_history_overlap = history_blocker_ids & blocker_ids

    if unresolved_history_overlap:
        raise ForwardDividendOrchestrationError(
            "FORWARD_DIVIDEND_ORCHESTRATION_RESOLVED_BLOCKER_STILL_ACTIVE:"
            + ",".join(sorted(unresolved_history_overlap))
        )

    certified_by_identity = {
        row.announcement_identity: row
        for row in certified
    }

    for row in blocker_resolution_history:
        if (
            row.resolver_status
            == BLOCKER_RESOLUTION_HISTORICAL_OBSERVED
            and row.resolver_announcement_identity in certified_by_identity
        ):
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_HISTORICAL_RESOLVER_NEW_CASH:"
                + row.resolver_announcement_identity
            )

    return DividendAcquisitionJournal(
        as_of_date=as_of,
        required_tickers=required,
        coverage=coverage,
        certified_events=certified,
        blockers=blockers,
        capture_phase=phase,
        certified_history=tuple(history_by_identity.values())
        if journal.certified_history
        else (),
        blocker_resolution_history=blocker_resolution_history,
    )


def journal_hash(
    journal: DividendAcquisitionJournal,
) -> str:
    canonical = normalize_journal(journal)

    payload = {
        "policy_id": POLICY_ID,
        "journal": journal_payload(canonical),
    }

    raw = (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()


def unresolved_blockers_for_tickers(
    journal: DividendAcquisitionJournal,
    tickers: Iterable[object],
) -> tuple[BlockingDividendJournalEntry, ...]:
    canonical = normalize_journal(journal)
    required = set(normalize_tickers(tickers))

    return tuple(
        row
        for row in canonical.blockers
        if row.ticker in required
    )


def advance_coverage(
    *,
    journal: DividendAcquisitionJournal,
    successful_tickers: Iterable[object],
    covered_through: str,
) -> tuple[DividendCoverage, ...]:
    canonical = normalize_journal(journal)

    target_date = _iso(
        covered_through,
        "FORWARD_DIVIDEND_ORCHESTRATION_ADVANCE_DATE_INVALID",
    )

    result = {
        row.ticker: row.covered_through
        for row in canonical.coverage
    }

    for ticker in normalize_tickers(successful_tickers):
        previous = result.get(ticker)

        if previous is not None and previous > target_date:
            raise ForwardDividendOrchestrationError(
                f"FORWARD_DIVIDEND_ORCHESTRATION_COVERAGE_REGRESSION:{ticker}"
            )

        result[ticker] = target_date

    return normalize_coverage(
        tuple(
            DividendCoverage(
                ticker=ticker,
                covered_through=value,
            )
            for ticker, value in result.items()
        )
    )


@dataclass(frozen=True)
class VerifiedDividendJournalDocument:
    path: Path
    file_sha256: str
    journal: DividendAcquisitionJournal
    journal_sha256: str
    previous_path: Path | None
    previous_file_sha256: str | None


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)

    return h.hexdigest()


def journal_payload(
    journal: DividendAcquisitionJournal,
) -> dict[str, Any]:
    canonical = normalize_journal(journal)

    return {
        "as_of_date": canonical.as_of_date,
        "capture_phase": canonical.capture_phase,
        "required_tickers": list(canonical.required_tickers),
        "coverage": [
            asdict(row)
            for row in canonical.coverage
        ],
        "certified_events": [
            asdict(row)
            for row in canonical.certified_events
        ],
        **(
            {
                "certified_history": [
                    asdict(row)
                    for row in canonical.certified_history
                ],
            }
            if canonical.certified_history
            else {}
        ),
        "blockers": [
            asdict(row)
            for row in canonical.blockers
        ],
        **(
            {
                "blocker_resolution_history": [
                    asdict(row)
                    for row in canonical.blocker_resolution_history
                ],
            }
            if canonical.blocker_resolution_history
            else {}
        ),
    }


def journal_from_payload(
    value: object,
) -> DividendAcquisitionJournal:
    if not isinstance(value, dict):
        raise ForwardDividendOrchestrationError(
            "FORWARD_DIVIDEND_ORCHESTRATION_JOURNAL_PAYLOAD_INVALID"
        )

    coverage = value.get("coverage")
    certified = value.get("certified_events")
    certified_history = value.get("certified_history", [])
    blockers = value.get("blockers")
    blocker_resolution_history = value.get(
        "blocker_resolution_history",
        [],
    )
    required = value.get("required_tickers")

    if not isinstance(required, list):
        raise ForwardDividendOrchestrationError(
            "FORWARD_DIVIDEND_ORCHESTRATION_REQUIRED_PAYLOAD_INVALID"
        )

    if not isinstance(coverage, list):
        raise ForwardDividendOrchestrationError(
            "FORWARD_DIVIDEND_ORCHESTRATION_COVERAGE_PAYLOAD_INVALID"
        )

    if not isinstance(certified, list):
        raise ForwardDividendOrchestrationError(
            "FORWARD_DIVIDEND_ORCHESTRATION_CERTIFIED_PAYLOAD_INVALID"
        )

    if not isinstance(certified_history, list):
        raise ForwardDividendOrchestrationError(
            "FORWARD_DIVIDEND_ORCHESTRATION_CERTIFIED_HISTORY_PAYLOAD_INVALID"
        )

    if not isinstance(blockers, list):
        raise ForwardDividendOrchestrationError(
            "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKERS_PAYLOAD_INVALID"
        )

    if not isinstance(blocker_resolution_history, list):
        raise ForwardDividendOrchestrationError(
            "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_RESOLUTION_HISTORY_PAYLOAD_INVALID"
        )

    try:
        journal = DividendAcquisitionJournal(
            as_of_date=str(value.get("as_of_date") or ""),
            required_tickers=tuple(str(x) for x in required),
            coverage=tuple(
                DividendCoverage(**row)
                for row in coverage
            ),
            certified_events=tuple(
                CertifiedDividendJournalEntry(**row)
                for row in certified
            ),
            certified_history=tuple(
                CertifiedDividendJournalEntry(**row)
                for row in certified_history
            ),
            blockers=tuple(
                BlockingDividendJournalEntry(**row)
                for row in blockers
            ),
            blocker_resolution_history=tuple(
                DividendBlockerResolutionEntry(**row)
                for row in blocker_resolution_history
            ),
            capture_phase=str(
                value.get("capture_phase")
                or POST_EOD
            ),
        )
    except (TypeError, ValueError) as exc:
        raise ForwardDividendOrchestrationError(
            "FORWARD_DIVIDEND_ORCHESTRATION_JOURNAL_PAYLOAD_ROW_INVALID"
        ) from exc

    return normalize_journal(journal)


def _document_bytes(
    value: dict[str, Any],
) -> bytes:
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")



def _verify_journal_evidence_files(
    journal: DividendAcquisitionJournal,
) -> None:
    canonical = normalize_journal(journal)
    evidence_rows = list(canonical.certified_events)
    evidence_rows.extend(canonical.certified_history)
    evidence_rows.extend(
        _resolver_entry(row)
        for row in canonical.blocker_resolution_history
    )
    seen_rows = set()

    for row in evidence_rows:
        evidence_key = (
            row.announcement_identity,
            row.ticker,
            row.event_id,
            row.event_sha256,
            row.evidence_dir,
            row.review_sha256,
            row.review_filename,
        )

        if evidence_key in seen_rows:
            continue

        seen_rows.add(evidence_key)
        root = Path(
            row.evidence_dir
        ).expanduser().resolve()

        review = root / row.review_filename

        if not review.is_file():
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_REVIEW_FILE_MISSING:"
                + row.announcement_identity
            )

        if _sha256_file(review) != row.review_sha256:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_REVIEW_FILE_HASH_MISMATCH:"
                + row.announcement_identity
            )

        if row.review_filename == "ATTACHMENT_REVIEW_V1_2.json":
            from .forward_dividend_provenance_v1_2 import (
                ForwardDividendProvenanceV12Error,
                certify_direct_idx_dividend_from_attachment_review_v1_2,
            )

            try:
                event = (
                    certify_direct_idx_dividend_from_attachment_review_v1_2(
                        review,
                        root,
                    )
                )
            except ForwardDividendProvenanceV12Error as exc:
                raise ForwardDividendOrchestrationError(
                    "FORWARD_DIVIDEND_ORCHESTRATION_V1_2_EVIDENCE_INVALID:"
                    + row.announcement_identity
                ) from exc

            if (
                event.event_id != row.event_id
                or event.source_evidence_sha256 != row.event_sha256
                or event.ticker != row.ticker
            ):
                raise ForwardDividendOrchestrationError(
                    "FORWARD_DIVIDEND_ORCHESTRATION_V1_2_EVENT_BINDING_MISMATCH:"
                    + row.announcement_identity
                )


def _verify_blocker_resolution_progression(
    parent: DividendAcquisitionJournal,
    child: DividendAcquisitionJournal,
) -> None:
    parent_history = {
        row.blocker_announcement_identity: row
        for row in parent.blocker_resolution_history
    }
    child_history = {
        row.blocker_announcement_identity: row
        for row in child.blocker_resolution_history
    }
    parent_blockers = {
        row.announcement_identity: row
        for row in parent.blockers
    }
    child_certified = {
        row.announcement_identity: row
        for row in child.certified_events
    }

    for identity, row in parent_history.items():
        if child_history.get(identity) != row:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_RESOLUTION_HISTORY_DROPPED_OR_CHANGED:"
                + identity
            )

    for identity, row in child_history.items():
        if identity not in parent_history:
            previous_blocker = parent_blockers.get(identity)

            if previous_blocker is None:
                raise ForwardDividendOrchestrationError(
                    "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_RESOLUTION_SOURCE_MISSING:"
                    + identity
                )

            if (
                previous_blocker.ticker != row.blocker_ticker
                or previous_blocker.classification
                != row.blocker_classification
            ):
                raise ForwardDividendOrchestrationError(
                    "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_RESOLUTION_BLOCKER_MISMATCH:"
                    + identity
                )

        resolver = _resolver_entry(row)
        certified = child_certified.get(
            row.resolver_announcement_identity
        )

        if row.resolver_status == BLOCKER_RESOLUTION_CERTIFIED_LIVE:
            if certified is None:
                raise ForwardDividendOrchestrationError(
                    "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_RESOLUTION_RESOLVER_MISSING:"
                    + row.resolver_announcement_identity
                )

            if certified.ticker != resolver.ticker:
                raise ForwardDividendOrchestrationError(
                    "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_RESOLUTION_RESOLVER_TICKER_MISMATCH:"
                    + row.resolver_announcement_identity
                )

            if certified.event_sha256 != resolver.event_sha256:
                raise ForwardDividendOrchestrationError(
                    "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_RESOLUTION_RESOLVER_SHA_MISMATCH:"
                    + row.resolver_announcement_identity
                )

            if certified != resolver:
                raise ForwardDividendOrchestrationError(
                    "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_RESOLUTION_RESOLVER_BINDING_MISMATCH:"
                    + row.resolver_announcement_identity
                )
        elif certified is not None:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_HISTORICAL_RESOLVER_NEW_CASH:"
                + row.resolver_announcement_identity
            )


def _verify_journal_progression(
    parent: DividendAcquisitionJournal,
    child: DividendAcquisitionJournal,
) -> None:
    parent = normalize_journal(parent)
    child = normalize_journal(child)

    if _journal_order_key(parent) >= _journal_order_key(child):
        raise ForwardDividendOrchestrationError(
            "FORWARD_DIVIDEND_ORCHESTRATION_PARENT_ORDER_NOT_PRIOR"
        )

    _verify_blocker_resolution_progression(parent, child)

    parent_certified = {
        row.announcement_identity: row
        for row in parent.certified_events
    }
    parent_history = {
        row.announcement_identity: row
        for row in (parent.certified_history or parent.certified_events)
    }

    child_certified = {
        row.announcement_identity: row
        for row in child.certified_events
    }
    child_history = {
        row.announcement_identity: row
        for row in (child.certified_history or child.certified_events)
    }

    for identity, row in parent_history.items():
        if child_history.get(identity) != row:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_CERTIFIED_HISTORY_DROPPED_OR_CHANGED:"
                + identity
            )

    for identity, row in parent_certified.items():
        if identity not in child_certified:
            # The current payable projection may retire an event, but only
            # after the immutable certified-history registry retains it.
            if child_history.get(identity) != row:
                raise ForwardDividendOrchestrationError(
                    "FORWARD_DIVIDEND_ORCHESTRATION_CERTIFIED_HISTORY_DROPPED:"
                    + identity
                )
            continue

        if child_certified[identity] != row:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_CERTIFIED_HISTORY_CHANGED:"
                + identity
            )

    parent_blockers = {
        row.announcement_identity: row
        for row in parent.blockers
    }

    child_blockers = {
        row.announcement_identity: row
        for row in child.blockers
    }
    child_resolutions = {
        row.blocker_announcement_identity: row
        for row in child.blocker_resolution_history
    }

    for identity, row in parent_blockers.items():
        if identity in child_certified or identity in child_resolutions:
            continue

        if child_blockers.get(identity) != row:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_HISTORY_DROPPED_OR_CHANGED:"
                + identity
            )

    parent_coverage = {
        row.ticker: row.covered_through
        for row in parent.coverage
    }

    child_coverage = {
        row.ticker: row.covered_through
        for row in child.coverage
    }

    for ticker, covered_through in parent_coverage.items():
        current = child_coverage.get(ticker)

        if current is None:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_COVERAGE_HISTORY_DROPPED:"
                + ticker
            )

        if current < covered_through:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_COVERAGE_HISTORY_REGRESSED:"
                + ticker
            )


def _load_journal_document(
    path: Path,
    *,
    seen: set[Path],
) -> VerifiedDividendJournalDocument:
    resolved = path.expanduser().resolve()

    if resolved in seen:
        raise ForwardDividendOrchestrationError(
            "FORWARD_DIVIDEND_ORCHESTRATION_JOURNAL_PARENT_CYCLE"
        )

    seen.add(resolved)

    if not resolved.is_file():
        raise ForwardDividendOrchestrationError(
            f"FORWARD_DIVIDEND_ORCHESTRATION_JOURNAL_MISSING:{resolved}"
        )

    try:
        payload = json.loads(
            resolved.read_text(encoding="utf-8")
        )
    except Exception as exc:
        raise ForwardDividendOrchestrationError(
            "FORWARD_DIVIDEND_ORCHESTRATION_JOURNAL_JSON_INVALID"
        ) from exc

    if not isinstance(payload, dict):
        raise ForwardDividendOrchestrationError(
            "FORWARD_DIVIDEND_ORCHESTRATION_JOURNAL_DOCUMENT_INVALID"
        )

    if payload.get("schema_version") != JOURNAL_SCHEMA:
        raise ForwardDividendOrchestrationError(
            "FORWARD_DIVIDEND_ORCHESTRATION_JOURNAL_SCHEMA_MISMATCH"
        )

    if payload.get("policy_id") != POLICY_ID:
        raise ForwardDividendOrchestrationError(
            "FORWARD_DIVIDEND_ORCHESTRATION_POLICY_ID_MISMATCH"
        )

    journal = journal_from_payload(payload.get("journal"))
    _verify_journal_evidence_files(journal)
    actual_journal_sha = journal_hash(journal)

    declared_journal_sha = str(
        payload.get("journal_sha256") or ""
    )

    if actual_journal_sha != declared_journal_sha:
        raise ForwardDividendOrchestrationError(
            "FORWARD_DIVIDEND_ORCHESTRATION_JOURNAL_HASH_MISMATCH"
        )

    previous_path = None
    previous_file_sha = None

    previous = payload.get("previous_journal")

    if previous is not None:
        if not isinstance(previous, dict):
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_PARENT_METADATA_INVALID"
            )

        previous_path = Path(
            str(previous.get("path") or "")
        ).expanduser().resolve()

        previous_file_sha = str(
            previous.get("file_sha256") or ""
        )

        if not previous_path.is_file():
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_PARENT_MISSING"
            )

        if _sha256_file(previous_path) != previous_file_sha:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_PARENT_FILE_HASH_MISMATCH"
            )

        parent = _load_journal_document(
            previous_path,
            seen=seen,
        )

        if (
            parent.journal_sha256
            != str(previous.get("journal_sha256") or "")
        ):
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_PARENT_JOURNAL_HASH_MISMATCH"
            )

        if (
            parent.journal.as_of_date
            != str(previous.get("as_of_date") or "")
        ):
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_PARENT_DATE_MISMATCH"
            )

        if (
            parent.journal.capture_phase
            != str(previous.get("capture_phase") or "")
        ):
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_PARENT_PHASE_MISMATCH"
            )

        _verify_journal_progression(
            parent.journal,
            journal,
        )

    return VerifiedDividendJournalDocument(
        path=resolved,
        file_sha256=_sha256_file(resolved),
        journal=journal,
        journal_sha256=actual_journal_sha,
        previous_path=previous_path,
        previous_file_sha256=previous_file_sha,
    )


def load_journal_document(
    path: str | Path,
) -> VerifiedDividendJournalDocument:
    return _load_journal_document(
        Path(path),
        seen=set(),
    )


def write_journal_document(
    path: str | Path,
    journal: DividendAcquisitionJournal,
    *,
    previous_journal_path: str | Path | None = None,
) -> VerifiedDividendJournalDocument:
    target = Path(path).expanduser().resolve()
    canonical = normalize_journal(journal)
    _verify_journal_evidence_files(canonical)

    previous_payload = None

    if previous_journal_path is not None:
        parent = load_journal_document(
            previous_journal_path
        )

        _verify_journal_progression(
            parent.journal,
            canonical,
        )

        previous_payload = {
            "path": str(parent.path),
            "file_sha256": parent.file_sha256,
            "journal_sha256": parent.journal_sha256,
            "as_of_date": parent.journal.as_of_date,
            "capture_phase": parent.journal.capture_phase,
        }

    payload = {
        "schema_version": JOURNAL_SCHEMA,
        "policy_id": POLICY_ID,
        "journal": journal_payload(canonical),
        "journal_sha256": journal_hash(canonical),
        "previous_journal": previous_payload,
    }

    data = _document_bytes(payload)

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if target.exists():
        if target.read_bytes() != data:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_JOURNAL_IMMUTABLE_CONFLICT"
            )

        return load_journal_document(target)

    fd, temp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
    )

    temp = Path(temp_name)

    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())

        if target.exists():
            if target.read_bytes() != data:
                raise ForwardDividendOrchestrationError(
                    "FORWARD_DIVIDEND_ORCHESTRATION_JOURNAL_IMMUTABLE_CONFLICT"
                )

            temp.unlink(missing_ok=True)
        else:
            os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)

    if target.read_bytes() != data:
        raise ForwardDividendOrchestrationError(
            "FORWARD_DIVIDEND_ORCHESTRATION_JOURNAL_WRITE_MISMATCH"
        )

    return load_journal_document(target)


def merge_journal_state(
    *,
    prior_journal: DividendAcquisitionJournal | None,
    as_of_date: str,
    capture_phase: str,
    required_tickers: Iterable[object],
    coverage: Sequence[DividendCoverage],
    current_certified: Sequence[
        CertifiedDividendJournalEntry
    ] = (),
    current_blockers: Sequence[
        BlockingDividendJournalEntry
    ] = (),
    current_blocker_resolutions: Sequence[
        DividendBlockerResolutionEntry
    ] = (),
    current_disposition_statuses: Mapping[object, object] | None = None,
) -> DividendAcquisitionJournal:
    current_as_of = _iso(
        as_of_date,
        "FORWARD_DIVIDEND_ORCHESTRATION_MERGE_DATE_INVALID",
    )

    phase = normalize_capture_phase(capture_phase)

    prior = (
        None
        if prior_journal is None
        else normalize_journal(prior_journal)
    )

    proposed_order = (
        date.fromisoformat(current_as_of),
        _CAPTURE_PHASE_ORDER[phase],
    )

    if (
        prior is not None
        and _journal_order_key(prior) >= proposed_order
    ):
        raise ForwardDividendOrchestrationError(
            "FORWARD_DIVIDEND_ORCHESTRATION_MERGE_PARENT_ORDER_NOT_PRIOR"
        )

    certified_now = normalize_certified_entries(
        current_certified
    )

    blockers_now = normalize_blockers(
        current_blockers
    )

    resolutions_now = normalize_blocker_resolutions(
        current_blocker_resolutions
    )

    disposition_statuses = {
        str(identity).strip(): str(status).strip().upper()
        for identity, status in (current_disposition_statuses or {}).items()
    }
    if any(
        not identity or status not in _DISPOSITION_STATUSES
        for identity, status in disposition_statuses.items()
    ):
        raise ForwardDividendOrchestrationError(
            "FORWARD_DIVIDEND_ORCHESTRATION_DISPOSITION_STATUS_INVALID"
        )

    if prior is None and resolutions_now:
        raise ForwardDividendOrchestrationError(
            "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_RESOLUTION_PARENT_REQUIRED"
        )

    current_ids = {
        row.announcement_identity
        for row in certified_now
    } | {
        row.announcement_identity
        for row in blockers_now
    }
    current_certified_ids = {
        row.announcement_identity for row in certified_now
    }
    current_blocker_ids = {
        row.announcement_identity for row in blockers_now
    }
    for identity, status in disposition_statuses.items():
        if status == "CERTIFIED_LIVE" and identity not in current_certified_ids:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_DISPOSITION_LIVE_BINDING_MISSING:"
                + identity
            )
        if (
            status == "BLOCKED_LIVE_UNRESOLVED"
            and identity not in current_blocker_ids
        ):
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_DISPOSITION_BLOCKER_BINDING_MISSING:"
                + identity
            )

    prior_certified = {}
    prior_certified_history = {}
    prior_blockers = {}
    prior_resolutions = {}

    if prior is not None:
        prior_certified = {
            row.announcement_identity: row
            for row in prior.certified_events
        }
        prior_certified_history = {
            row.announcement_identity: row
            for row in (
                prior.certified_history
                or prior.certified_events
            )
        }

        prior_blockers = {
            row.announcement_identity: row
            for row in prior.blockers
        }

        prior_resolutions = {
            row.blocker_announcement_identity: row
            for row in prior.blocker_resolution_history
        }

    certified_out = dict(prior_certified)
    certified_history_out = dict(prior_certified_history)
    blockers_out = dict(prior_blockers)
    resolutions_out = dict(prior_resolutions)

    # A prior active blocker may not silently become historical,
    # corroborating, superseded, or certified. The disposition is only a
    # classification; the append-only resolution entry is the evidence-bound
    # state transition. If a producer has already recorded a resolution,
    # retaining it across later batches is sufficient.
    if prior is not None and disposition_statuses:
        resolution_ids = set(prior_resolutions) | {
            row.blocker_announcement_identity
            for row in resolutions_now
        }
        for identity in prior_blockers:
            status = disposition_statuses.get(identity)
            if (
                status is not None
                and status != "BLOCKED_LIVE_UNRESOLVED"
                and identity not in resolution_ids
            ):
                raise ForwardDividendOrchestrationError(
                    "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_TRANSITION_REQUIRES_RESOLUTION:"
                    + identity
                )

    for row in certified_now:
        previous = prior_certified.get(
            row.announcement_identity
        )

        if previous is not None and previous != row:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_CERTIFIED_HISTORY_CHANGED:"
                + row.announcement_identity
            )

        blockers_out.pop(
            row.announcement_identity,
            None,
        )

        certified_out[
            row.announcement_identity
        ] = row
        certified_history_out[row.announcement_identity] = row

    for row in blockers_now:
        if row.announcement_identity in prior_certified:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_CERTIFIED_DOWNGRADE_BLOCKED:"
                + row.announcement_identity
            )

        blockers_out[
            row.announcement_identity
        ] = row

    for identity, status in disposition_statuses.items():
        if status != "CERTIFIED_LIVE":
            certified_out.pop(identity, None)

    for row in resolutions_now:
        previous_resolution = prior_resolutions.get(
            row.blocker_announcement_identity
        )

        if (
            previous_resolution is not None
            and previous_resolution != row
        ):
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_RESOLUTION_HISTORY_CHANGED:"
                + row.blocker_announcement_identity
            )

        if previous_resolution is None:
            previous_blocker = prior_blockers.get(
                row.blocker_announcement_identity
            )

            if previous_blocker is None:
                raise ForwardDividendOrchestrationError(
                    "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_RESOLUTION_SOURCE_MISSING:"
                    + row.blocker_announcement_identity
                )

            if (
                previous_blocker.ticker != row.blocker_ticker
                or previous_blocker.classification
                != row.blocker_classification
            ):
                raise ForwardDividendOrchestrationError(
                    "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKER_RESOLUTION_BLOCKER_MISMATCH:"
                    + row.blocker_announcement_identity
                )

        resolutions_out[
            row.blocker_announcement_identity
        ] = row
        blockers_out.pop(
            row.blocker_announcement_identity,
            None,
        )

    for identity in current_ids:
        if identity not in {
            row.announcement_identity
            for row in certified_now
        }:
            certified_out.pop(identity, None)

    merged = normalize_journal(
        DividendAcquisitionJournal(
            as_of_date=current_as_of,
            required_tickers=normalize_tickers(
                required_tickers
            ),
            coverage=tuple(coverage),
            certified_events=tuple(
                certified_out.values()
            ),
            certified_history=tuple(
                certified_history_out.values()
            ),
            blockers=tuple(
                blockers_out.values()
            ),
            capture_phase=phase,
            blocker_resolution_history=tuple(
                resolutions_out.values()
            ),
        )
    )

    if prior is not None:
        _verify_blocker_resolution_progression(
            prior,
            merged,
        )

    return merged
