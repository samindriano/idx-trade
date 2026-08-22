from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable, Sequence


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
class DividendAcquisitionJournal:
    as_of_date: str
    required_tickers: tuple[str, ...]
    coverage: tuple[DividendCoverage, ...]
    certified_events: tuple[CertifiedDividendJournalEntry, ...] = ()
    blockers: tuple[BlockingDividendJournalEntry, ...] = ()
    capture_phase: str = POST_EOD


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
    blockers = normalize_blockers(journal.blockers)

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

    return DividendAcquisitionJournal(
        as_of_date=as_of,
        required_tickers=required,
        coverage=coverage,
        certified_events=certified,
        blockers=blockers,
        capture_phase=phase,
    )


def journal_hash(
    journal: DividendAcquisitionJournal,
) -> str:
    canonical = normalize_journal(journal)

    payload = {
        "policy_id": POLICY_ID,
        "journal": asdict(canonical),
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
        "blockers": [
            asdict(row)
            for row in canonical.blockers
        ],
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
    blockers = value.get("blockers")
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

    if not isinstance(blockers, list):
        raise ForwardDividendOrchestrationError(
            "FORWARD_DIVIDEND_ORCHESTRATION_BLOCKERS_PAYLOAD_INVALID"
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
            blockers=tuple(
                BlockingDividendJournalEntry(**row)
                for row in blockers
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

    for row in canonical.certified_events:
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

    parent_certified = {
        row.announcement_identity: row
        for row in parent.certified_events
    }

    child_certified = {
        row.announcement_identity: row
        for row in child.certified_events
    }

    for identity, row in parent_certified.items():
        if identity not in child_certified:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_CERTIFIED_HISTORY_DROPPED:"
                + identity
            )

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

    for identity, row in parent_blockers.items():
        if identity in child_certified:
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

    current_ids = {
        row.announcement_identity
        for row in certified_now
    } | {
        row.announcement_identity
        for row in blockers_now
    }

    prior_certified = {}
    prior_blockers = {}

    if prior is not None:
        prior_certified = {
            row.announcement_identity: row
            for row in prior.certified_events
        }

        prior_blockers = {
            row.announcement_identity: row
            for row in prior.blockers
        }

    certified_out = dict(prior_certified)
    blockers_out = dict(prior_blockers)

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

    for row in blockers_now:
        if row.announcement_identity in prior_certified:
            raise ForwardDividendOrchestrationError(
                "FORWARD_DIVIDEND_ORCHESTRATION_CERTIFIED_DOWNGRADE_BLOCKED:"
                + row.announcement_identity
            )

        blockers_out[
            row.announcement_identity
        ] = row

    for identity in current_ids:
        if identity not in {
            row.announcement_identity
            for row in certified_now
        }:
            certified_out.pop(identity, None)

    return normalize_journal(
        DividendAcquisitionJournal(
            as_of_date=current_as_of,
            required_tickers=normalize_tickers(
                required_tickers
            ),
            coverage=tuple(coverage),
            certified_events=tuple(
                certified_out.values()
            ),
            blockers=tuple(
                blockers_out.values()
            ),
            capture_phase=phase,
        )
    )
