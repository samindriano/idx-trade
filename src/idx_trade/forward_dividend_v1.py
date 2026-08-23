from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Mapping, Sequence

from .v4_x1_decision_v1_contract import DecisionV1Error
from .v4_x1_execution_v1 import execute_open_v1, prepare_execution_v1
from .v4_x1_execution_v1_contract import (
    ExecutionOrderPlan,
    ExecutionResult,
    LOT_SIZE_SHARES,
    PaperPortfolioState,
    normalize_state,
    paper_state_hash,
)
from .v4_x1_sizing_v1 import (
    VerifiedDecisionPlan,
    _SIZING_PLAN_TOKEN,
    _size_entries_for_intents,
)
from .v4_x1_execution_v1_verify import (
    VerifiedCorporateActionAttestation,
    VerifiedEODExecutionInputs,
    VerifiedOpenExecutionInputs,
)

AUTHORITY = "DIRECT_IDX_ANNOUNCEMENT_PLUS_HASHED_ATTACHMENT"
REVIEW_STATUS = "PASS_DIRECT_IDX_ANNOUNCEMENT_ATTACHMENT_TERMS_ELIGIBLE_FOR_V1_1"
TAX_TREATMENT = "UNRESOLVED_GROSS_PAPER_CREDIT"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MONTHS = {
    "januari": 1,
    "februari": 2,
    "maret": 3,
    "april": 4,
    "mei": 5,
    "juni": 6,
    "juli": 7,
    "agustus": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "desember": 12,
    "january": 1,
    "february": 2,
    "march": 3,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "october": 10,
    "december": 12,
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical_hash(value: object) -> str:
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    return _sha256_bytes(raw)


def _ticker(value: object) -> str:
    symbol = str(value or "").upper().replace(".JK", "").strip()
    if not symbol or not re.fullmatch(r"[A-Z0-9]{1,12}", symbol):
        raise DecisionV1Error("DIVIDEND_V1_TICKER_INVALID")
    return symbol


def _positive(value: object, code: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise DecisionV1Error(code) from exc
    if not math.isfinite(result) or result <= 0:
        raise DecisionV1Error(code)
    return result


def _iso_date(value: object, code: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise DecisionV1Error(code)
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except Exception:
        pass
    match = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text)
    if not match:
        raise DecisionV1Error(code)
    day = int(match.group(1))
    month = _MONTHS.get(match.group(2).lower())
    if month is None:
        raise DecisionV1Error(code)
    try:
        return date(int(match.group(3)), month, day).isoformat()
    except ValueError as exc:
        raise DecisionV1Error(code) from exc


def _timestamp(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        raise DecisionV1Error("DIVIDEND_V1_ANNOUNCEMENT_TIMESTAMP_INVALID")
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DecisionV1Error("DIVIDEND_V1_ANNOUNCEMENT_TIMESTAMP_INVALID") from exc
    return text


def _sha(value: object, code: str) -> str:
    text = str(value or "")
    if not _SHA256_RE.fullmatch(text):
        raise DecisionV1Error(code)
    return text


@dataclass(frozen=True)
class CertifiedCashDividend:
    event_id: str
    ticker: str
    announcement_timestamp: str
    gross_dividend_per_share_idr: float
    cum_date: str
    ex_date: str
    record_date: str
    payment_date: str
    source_evidence_sha256: str
    # V1.2 may certify an economic event after its cum date. This is an
    # explicit knowledge-time marker, never a backdated trading decision.
    knowledge_at_timestamp: str | None = None


@dataclass(frozen=True)
class PaperDividendEntitlement:
    event_id: str
    ticker: str
    entitled_shares: int
    gross_dividend_per_share_idr: float
    cum_date: str
    ex_date: str
    record_date: str
    payment_date: str
    source_evidence_sha256: str


@dataclass(frozen=True)
class PaperDividendReceivable:
    event_id: str
    ticker: str
    entitled_shares: int
    gross_dividend_per_share_idr: float
    gross_amount_idr: float
    payment_date: str
    source_evidence_sha256: str


@dataclass(frozen=True)
class PaperDividendSettlement:
    event_id: str
    ticker: str
    entitled_shares: int
    gross_amount_idr: float
    payment_date: str
    settled_on_session_date: str
    source_evidence_sha256: str
    tax_treatment: str = TAX_TREATMENT


@dataclass(frozen=True)
class DividendLedger:
    entitlements: tuple[PaperDividendEntitlement, ...] = ()
    receivables: tuple[PaperDividendReceivable, ...] = ()
    settlements: tuple[PaperDividendSettlement, ...] = ()


@dataclass(frozen=True)
class DividendAwarePaperState:
    base_state: PaperPortfolioState
    dividend_ledger: DividendLedger = field(default_factory=DividendLedger)


@dataclass(frozen=True)
class DividendAwareExecutionOrderPlan:
    base_plan: ExecutionOrderPlan
    dividend_state_hash: str
    dividend_ledger_hash: str
    total_return_nav_idr: float


@dataclass(frozen=True)
class DividendAwareExecutionResult:
    base_result: ExecutionResult
    state_after: DividendAwarePaperState


def _event_dates(cum_date: str, ex_date: str, record_date: str, payment_date: str) -> tuple[str, str, str, str]:
    cum = _iso_date(cum_date, "DIVIDEND_V1_CUM_DATE_INVALID")
    ex = _iso_date(ex_date, "DIVIDEND_V1_EX_DATE_INVALID")
    record = _iso_date(record_date, "DIVIDEND_V1_RECORD_DATE_INVALID")
    payment = _iso_date(payment_date, "DIVIDEND_V1_PAYMENT_DATE_INVALID")
    if not (cum < ex <= record <= payment):
        raise DecisionV1Error("DIVIDEND_V1_DATE_ORDER_INVALID")
    return cum, ex, record, payment


def _validate_entitlement(row: PaperDividendEntitlement) -> PaperDividendEntitlement:
    if not row.event_id:
        raise DecisionV1Error("DIVIDEND_V1_EVENT_ID_INVALID")
    symbol = _ticker(row.ticker)
    shares = int(row.entitled_shares)
    if shares <= 0 or shares % LOT_SIZE_SHARES:
        raise DecisionV1Error("DIVIDEND_V1_ENTITLEMENT_SHARES_INVALID")
    amount = _positive(row.gross_dividend_per_share_idr, "DIVIDEND_V1_PER_SHARE_INVALID")
    cum, ex, record, payment = _event_dates(row.cum_date, row.ex_date, row.record_date, row.payment_date)
    source_sha = _sha(row.source_evidence_sha256, "DIVIDEND_V1_SOURCE_SHA_INVALID")
    return replace(
        row,
        ticker=symbol,
        entitled_shares=shares,
        gross_dividend_per_share_idr=amount,
        cum_date=cum,
        ex_date=ex,
        record_date=record,
        payment_date=payment,
        source_evidence_sha256=source_sha,
    )


def _validate_receivable(row: PaperDividendReceivable) -> PaperDividendReceivable:
    if not row.event_id:
        raise DecisionV1Error("DIVIDEND_V1_EVENT_ID_INVALID")
    symbol = _ticker(row.ticker)
    shares = int(row.entitled_shares)
    if shares <= 0 or shares % LOT_SIZE_SHARES:
        raise DecisionV1Error("DIVIDEND_V1_RECEIVABLE_SHARES_INVALID")
    per_share = _positive(row.gross_dividend_per_share_idr, "DIVIDEND_V1_PER_SHARE_INVALID")
    gross = _positive(row.gross_amount_idr, "DIVIDEND_V1_RECEIVABLE_AMOUNT_INVALID")
    expected = shares * per_share
    if not math.isclose(gross, expected, rel_tol=0.0, abs_tol=1e-6):
        raise DecisionV1Error("DIVIDEND_V1_RECEIVABLE_AMOUNT_MISMATCH")
    payment = _iso_date(row.payment_date, "DIVIDEND_V1_PAYMENT_DATE_INVALID")
    source_sha = _sha(row.source_evidence_sha256, "DIVIDEND_V1_SOURCE_SHA_INVALID")
    return replace(
        row,
        ticker=symbol,
        entitled_shares=shares,
        gross_dividend_per_share_idr=per_share,
        gross_amount_idr=gross,
        payment_date=payment,
        source_evidence_sha256=source_sha,
    )


def _validate_settlement(row: PaperDividendSettlement) -> PaperDividendSettlement:
    if not row.event_id:
        raise DecisionV1Error("DIVIDEND_V1_EVENT_ID_INVALID")
    symbol = _ticker(row.ticker)
    shares = int(row.entitled_shares)
    if shares <= 0 or shares % LOT_SIZE_SHARES:
        raise DecisionV1Error("DIVIDEND_V1_SETTLEMENT_SHARES_INVALID")
    gross = _positive(row.gross_amount_idr, "DIVIDEND_V1_SETTLEMENT_AMOUNT_INVALID")
    payment = _iso_date(row.payment_date, "DIVIDEND_V1_PAYMENT_DATE_INVALID")
    settled = _iso_date(row.settled_on_session_date, "DIVIDEND_V1_SETTLEMENT_DATE_INVALID")
    if settled < payment:
        raise DecisionV1Error("DIVIDEND_V1_SETTLED_BEFORE_PAYMENT_DATE")
    source_sha = _sha(row.source_evidence_sha256, "DIVIDEND_V1_SOURCE_SHA_INVALID")
    if row.tax_treatment != TAX_TREATMENT:
        raise DecisionV1Error("DIVIDEND_V1_TAX_TREATMENT_CHANGED")
    return replace(
        row,
        ticker=symbol,
        entitled_shares=shares,
        gross_amount_idr=gross,
        payment_date=payment,
        settled_on_session_date=settled,
        source_evidence_sha256=source_sha,
    )


def normalize_dividend_ledger(ledger: DividendLedger) -> DividendLedger:
    if not isinstance(ledger, DividendLedger):
        raise DecisionV1Error("DIVIDEND_V1_LEDGER_REQUIRED")
    entitlements = tuple(_validate_entitlement(x) for x in ledger.entitlements)
    receivables = tuple(_validate_receivable(x) for x in ledger.receivables)
    settlements = tuple(_validate_settlement(x) for x in ledger.settlements)

    def unique(rows: Sequence[object], kind: str) -> dict[str, object]:
        out: dict[str, object] = {}
        for row in rows:
            event_id = str(getattr(row, "event_id"))
            if event_id in out:
                raise DecisionV1Error(f"DIVIDEND_V1_DUPLICATE_{kind}_EVENT")
            out[event_id] = row
        return out

    ent_by_id = unique(entitlements, "ENTITLEMENT")
    recv_by_id = unique(receivables, "RECEIVABLE")
    set_by_id = unique(settlements, "SETTLEMENT")
    if set(recv_by_id) & set(set_by_id):
        raise DecisionV1Error("DIVIDEND_V1_EVENT_RECEIVABLE_AND_SETTLED")

    for event_id, raw in recv_by_id.items():
        row = raw
        entitlement = ent_by_id.get(event_id)
        if entitlement is None:
            raise DecisionV1Error("DIVIDEND_V1_RECEIVABLE_WITHOUT_ENTITLEMENT")
        assert isinstance(row, PaperDividendReceivable)
        assert isinstance(entitlement, PaperDividendEntitlement)
        if (
            row.ticker != entitlement.ticker
            or row.entitled_shares != entitlement.entitled_shares
            or not math.isclose(row.gross_dividend_per_share_idr, entitlement.gross_dividend_per_share_idr, rel_tol=0.0, abs_tol=1e-12)
            or row.payment_date != entitlement.payment_date
            or row.source_evidence_sha256 != entitlement.source_evidence_sha256
        ):
            raise DecisionV1Error("DIVIDEND_V1_RECEIVABLE_ENTITLEMENT_MISMATCH")

    for event_id, raw in set_by_id.items():
        row = raw
        entitlement = ent_by_id.get(event_id)
        if entitlement is None:
            raise DecisionV1Error("DIVIDEND_V1_SETTLEMENT_WITHOUT_ENTITLEMENT")
        assert isinstance(row, PaperDividendSettlement)
        assert isinstance(entitlement, PaperDividendEntitlement)
        expected = entitlement.entitled_shares * entitlement.gross_dividend_per_share_idr
        if (
            row.ticker != entitlement.ticker
            or row.entitled_shares != entitlement.entitled_shares
            or not math.isclose(row.gross_amount_idr, expected, rel_tol=0.0, abs_tol=1e-6)
            or row.payment_date != entitlement.payment_date
            or row.source_evidence_sha256 != entitlement.source_evidence_sha256
        ):
            raise DecisionV1Error("DIVIDEND_V1_SETTLEMENT_ENTITLEMENT_MISMATCH")

    return DividendLedger(
        entitlements=tuple(sorted(entitlements, key=lambda x: x.event_id)),
        receivables=tuple(sorted(receivables, key=lambda x: x.event_id)),
        settlements=tuple(sorted(settlements, key=lambda x: x.event_id)),
    )


def dividend_ledger_hash(ledger: DividendLedger) -> str:
    normalized = normalize_dividend_ledger(ledger)

    def rows(items: Sequence[object]) -> list[dict[str, object]]:
        return [dict(sorted(vars(x).items())) for x in items]

    return _canonical_hash(
        {
            "entitlements": rows(normalized.entitlements),
            "receivables": rows(normalized.receivables),
            "settlements": rows(normalized.settlements),
        }
    )


def dividend_aware_state_hash(state: DividendAwarePaperState) -> str:
    if not isinstance(state, DividendAwarePaperState):
        raise DecisionV1Error("DIVIDEND_V1_AWARE_STATE_REQUIRED")
    normalize_state(state.base_state)
    return _canonical_hash(
        {
            "base_paper_state_sha256": paper_state_hash(state.base_state),
            "dividend_ledger_sha256": dividend_ledger_hash(state.dividend_ledger),
        }
    )


def certify_direct_idx_dividend_from_attachment_review(
    review_path: str | Path,
    attachment_dir: str | Path,
) -> CertifiedCashDividend:
    review_file = Path(review_path).expanduser().resolve()
    root = Path(attachment_dir).expanduser().resolve()
    if not review_file.is_file():
        raise DecisionV1Error("DIVIDEND_V1_REVIEW_MISSING")
    try:
        review = json.loads(review_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV1Error("DIVIDEND_V1_REVIEW_INVALID") from exc
    if review.get("status") != REVIEW_STATUS:
        raise DecisionV1Error("DIVIDEND_V1_REVIEW_NOT_ADMITTED")
    if review.get("authority_recommendation") != AUTHORITY:
        raise DecisionV1Error("DIVIDEND_V1_AUTHORITY_MISMATCH")
    semantic = review.get("semantic_matches")
    required_semantics = {
        "ticker",
        "dividend_subject",
        "dividend_per_share",
        "cum_regular_negotiated",
        "ex_regular_negotiated",
        "record_date",
        "payment_date",
    }
    if not isinstance(semantic, dict) or any(semantic.get(k) is not True for k in required_semantics):
        raise DecisionV1Error("DIVIDEND_V1_SEMANTIC_GATE_INCOMPLETE")

    source_announcement_sha = _sha(
        review.get("source_announcement_raw_sha256"),
        "DIVIDEND_V1_ANNOUNCEMENT_SHA_INVALID",
    )
    documents = review.get("documents")
    if not isinstance(documents, list) or not documents:
        raise DecisionV1Error("DIVIDEND_V1_DOCUMENTS_MISSING")
    verified_docs: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in documents:
        if not isinstance(row, dict):
            raise DecisionV1Error("DIVIDEND_V1_DOCUMENT_ROW_INVALID")
        filename = str(row.get("pdf_filename") or "")
        if not filename or filename in seen or Path(filename).name != filename:
            raise DecisionV1Error("DIVIDEND_V1_DOCUMENT_FILENAME_INVALID")
        seen.add(filename)
        declared = _sha(row.get("sha256"), "DIVIDEND_V1_DOCUMENT_SHA_INVALID")
        path = root / filename
        if not path.is_file():
            raise DecisionV1Error(f"DIVIDEND_V1_DOCUMENT_MISSING:{filename}")
        if _sha256_file(path) != declared:
            raise DecisionV1Error(f"DIVIDEND_V1_DOCUMENT_SHA_MISMATCH:{filename}")
        verified_docs.append({"pdf_filename": filename, "sha256": declared})

    expected = review.get("expected_event")
    announcement = review.get("announcement")
    if not isinstance(expected, dict) or not isinstance(announcement, dict):
        raise DecisionV1Error("DIVIDEND_V1_EVENT_METADATA_MISSING")
    symbol = _ticker(expected.get("ticker"))
    amount = _positive(expected.get("gross_dividend_per_share_idr"), "DIVIDEND_V1_PER_SHARE_INVALID")
    cum, ex, record, payment = _event_dates(
        _iso_date(expected.get("cum_regular_negotiated"), "DIVIDEND_V1_CUM_DATE_INVALID"),
        _iso_date(expected.get("ex_regular_negotiated"), "DIVIDEND_V1_EX_DATE_INVALID"),
        _iso_date(expected.get("record_date"), "DIVIDEND_V1_RECORD_DATE_INVALID"),
        _iso_date(expected.get("payment_date"), "DIVIDEND_V1_PAYMENT_DATE_INVALID"),
    )
    announced = _timestamp(announcement.get("date"))
    if _iso_date(announced, "DIVIDEND_V1_ANNOUNCEMENT_DATE_INVALID") > cum:
        raise DecisionV1Error("DIVIDEND_V1_ANNOUNCEMENT_AFTER_CUM_DATE")

    evidence = {
        "authority": AUTHORITY,
        "announcement_raw_sha256": source_announcement_sha,
        "documents": sorted(verified_docs, key=lambda x: x["pdf_filename"]),
        "ticker": symbol,
        "announcement_timestamp": announced,
        "gross_dividend_per_share_idr": format(Decimal(str(amount)), "f"),
        "cum_date": cum,
        "ex_date": ex,
        "record_date": record,
        "payment_date": payment,
    }
    evidence_sha = _canonical_hash(evidence)
    return CertifiedCashDividend(
        event_id=f"CASH_DIVIDEND_{symbol}_{evidence_sha[:24]}",
        ticker=symbol,
        announcement_timestamp=announced,
        gross_dividend_per_share_idr=amount,
        cum_date=cum,
        ex_date=ex,
        record_date=record,
        payment_date=payment,
        source_evidence_sha256=evidence_sha,
    )


def _validated_event(event: CertifiedCashDividend) -> CertifiedCashDividend:
    if not isinstance(event, CertifiedCashDividend) or not event.event_id:
        raise DecisionV1Error("DIVIDEND_V1_CERTIFIED_EVENT_REQUIRED")
    symbol = _ticker(event.ticker)
    announced = _timestamp(event.announcement_timestamp)
    amount = _positive(event.gross_dividend_per_share_idr, "DIVIDEND_V1_PER_SHARE_INVALID")
    cum, ex, record, payment = _event_dates(event.cum_date, event.ex_date, event.record_date, event.payment_date)
    source_sha = _sha(event.source_evidence_sha256, "DIVIDEND_V1_SOURCE_SHA_INVALID")
    if (
        _iso_date(announced, "DIVIDEND_V1_ANNOUNCEMENT_DATE_INVALID") > cum
        and event.knowledge_at_timestamp is None
    ):
        raise DecisionV1Error("DIVIDEND_V1_ANNOUNCEMENT_AFTER_CUM_DATE")
    if event.knowledge_at_timestamp is not None:
        if _timestamp(event.knowledge_at_timestamp) != event.knowledge_at_timestamp:
            raise DecisionV1Error("DIVIDEND_V1_KNOWLEDGE_TIMESTAMP_INVALID")
        if event.knowledge_at_timestamp != announced:
            raise DecisionV1Error("DIVIDEND_V1_KNOWLEDGE_TIMESTAMP_MISMATCH")
    return replace(
        event,
        ticker=symbol,
        gross_dividend_per_share_idr=amount,
        cum_date=cum,
        ex_date=ex,
        record_date=record,
        payment_date=payment,
        source_evidence_sha256=source_sha,
    )


def snapshot_cum_date_entitlements(
    state: DividendAwarePaperState,
    events: Sequence[CertifiedCashDividend],
    *,
    session_date: str,
    historical_states_by_date: Mapping[str, "DividendAwarePaperState"] | None = None,
) -> DividendAwarePaperState:
    session = _iso_date(session_date, "DIVIDEND_V1_SESSION_DATE_INVALID")
    if _iso_date(state.base_state.as_of_session_date, "DIVIDEND_V1_STATE_DATE_INVALID") != session:
        raise DecisionV1Error("DIVIDEND_V1_STATE_SESSION_MISMATCH")
    _, positions, _, _ = normalize_state(state.base_state)
    ledger = normalize_dividend_ledger(state.dividend_ledger)
    by_id = {x.event_id: x for x in ledger.entitlements}
    same_cum = {(x.ticker, x.cum_date): x.event_id for x in ledger.entitlements}

    candidates: dict[str, CertifiedCashDividend] = {}
    for raw in events:
        event = _validated_event(raw)
        if event.event_id in candidates and candidates[event.event_id] != event:
            raise DecisionV1Error("DIVIDEND_V1_DUPLICATE_EVENT_CONFLICT")
        candidates[event.event_id] = event
    event_scope: dict[tuple[str, str], str] = {}
    for event in candidates.values():
        key = (event.ticker, event.cum_date)
        if key in event_scope and event_scope[key] != event.event_id:
            raise DecisionV1Error("DIVIDEND_V1_CONFLICTING_EVENT_SAME_TICKER_CUM")
        event_scope[key] = event.event_id

    changed = False
    entitlements = list(ledger.entitlements)
    for event in sorted(candidates.values(), key=lambda x: x.event_id):
        if event.cum_date > session:
            continue
        existing_other = same_cum.get((event.ticker, event.cum_date))
        if existing_other is not None and existing_other != event.event_id:
            raise DecisionV1Error("DIVIDEND_V1_CONFLICTING_EVENT_SAME_TICKER_CUM")
        existing = by_id.get(event.event_id)
        if event.cum_date == session:
            shares = positions.get(event.ticker, 0)
        elif existing is not None:
            # Once an entitlement is already recorded, later lifecycle passes
            # must not re-derive it from a mutated current position.
            shares = existing.entitled_shares
        else:
            historical = (
                None
                if historical_states_by_date is None
                else historical_states_by_date.get(event.cum_date)
            )
            if historical is None:
                raise DecisionV1Error("DIVIDEND_V1_HISTORICAL_CUM_STATE_REQUIRED")
            if _iso_date(historical.base_state.as_of_session_date, "DIVIDEND_V1_HISTORICAL_CUM_STATE_DATE_INVALID") != event.cum_date:
                raise DecisionV1Error("DIVIDEND_V1_HISTORICAL_CUM_STATE_DATE_MISMATCH")
            _, historical_positions, _, _ = normalize_state(historical.base_state)
            shares = historical_positions.get(event.ticker, 0)
        if existing is not None:
            if shares != existing.entitled_shares:
                raise DecisionV1Error("DIVIDEND_V1_REPLAY_POSITION_ENTITLEMENT_MISMATCH")
            expected = PaperDividendEntitlement(
                event_id=event.event_id,
                ticker=event.ticker,
                entitled_shares=shares,
                gross_dividend_per_share_idr=event.gross_dividend_per_share_idr,
                cum_date=event.cum_date,
                ex_date=event.ex_date,
                record_date=event.record_date,
                payment_date=event.payment_date,
                source_evidence_sha256=event.source_evidence_sha256,
            )
            if existing != expected:
                raise DecisionV1Error("DIVIDEND_V1_EXISTING_ENTITLEMENT_CONFLICT")
            continue
        if shares <= 0:
            continue
        entitlement = PaperDividendEntitlement(
            event_id=event.event_id,
            ticker=event.ticker,
            entitled_shares=shares,
            gross_dividend_per_share_idr=event.gross_dividend_per_share_idr,
            cum_date=event.cum_date,
            ex_date=event.ex_date,
            record_date=event.record_date,
            payment_date=event.payment_date,
            source_evidence_sha256=event.source_evidence_sha256,
        )
        entitlements.append(entitlement)
        by_id[event.event_id] = entitlement
        same_cum[(event.ticker, event.cum_date)] = event.event_id
        changed = True

    if not changed:
        return state
    return replace(
        state,
        dividend_ledger=normalize_dividend_ledger(
            DividendLedger(tuple(entitlements), ledger.receivables, ledger.settlements)
        ),
    )


def advance_dividend_lifecycle(
    state: DividendAwarePaperState,
    *,
    session_date: str,
) -> DividendAwarePaperState:
    session = _iso_date(session_date, "DIVIDEND_V1_SESSION_DATE_INVALID")
    if _iso_date(state.base_state.as_of_session_date, "DIVIDEND_V1_STATE_DATE_INVALID") != session:
        raise DecisionV1Error("DIVIDEND_V1_STATE_SESSION_MISMATCH")
    ledger = normalize_dividend_ledger(state.dividend_ledger)
    receivables = {x.event_id: x for x in ledger.receivables}
    settlements = {x.event_id: x for x in ledger.settlements}

    for entitlement in ledger.entitlements:
        if session < entitlement.ex_date or entitlement.event_id in settlements:
            continue
        expected = PaperDividendReceivable(
            event_id=entitlement.event_id,
            ticker=entitlement.ticker,
            entitled_shares=entitlement.entitled_shares,
            gross_dividend_per_share_idr=entitlement.gross_dividend_per_share_idr,
            gross_amount_idr=entitlement.entitled_shares * entitlement.gross_dividend_per_share_idr,
            payment_date=entitlement.payment_date,
            source_evidence_sha256=entitlement.source_evidence_sha256,
        )
        existing = receivables.get(entitlement.event_id)
        if existing is not None and existing != expected:
            raise DecisionV1Error("DIVIDEND_V1_EXISTING_RECEIVABLE_CONFLICT")
        if existing is None:
            receivables[entitlement.event_id] = expected

    cash, _, _, _ = normalize_state(state.base_state)
    settlements_new = dict(settlements)
    for event_id, receivable in sorted(list(receivables.items())):
        if session < receivable.payment_date:
            continue
        if event_id in settlements_new:
            raise DecisionV1Error("DIVIDEND_V1_RECEIVABLE_ALREADY_SETTLED")
        cash += receivable.gross_amount_idr
        settlements_new[event_id] = PaperDividendSettlement(
            event_id=event_id,
            ticker=receivable.ticker,
            entitled_shares=receivable.entitled_shares,
            gross_amount_idr=receivable.gross_amount_idr,
            payment_date=receivable.payment_date,
            settled_on_session_date=session,
            source_evidence_sha256=receivable.source_evidence_sha256,
        )
        del receivables[event_id]

    new_ledger = normalize_dividend_ledger(
        DividendLedger(
            entitlements=ledger.entitlements,
            receivables=tuple(receivables.values()),
            settlements=tuple(settlements_new.values()),
        )
    )
    new_base = state.base_state if math.isclose(cash, state.base_state.cash_idr, rel_tol=0.0, abs_tol=1e-9) else replace(state.base_state, cash_idr=float(cash))
    if new_base == state.base_state and new_ledger == ledger:
        return state
    return DividendAwarePaperState(base_state=new_base, dividend_ledger=new_ledger)


def process_dividend_eod(
    state: DividendAwarePaperState,
    events: Sequence[CertifiedCashDividend],
    *,
    session_date: str,
    historical_states_by_date: Mapping[str, DividendAwarePaperState] | None = None,
) -> DividendAwarePaperState:
    snapshotted = snapshot_cum_date_entitlements(
        state,
        events,
        session_date=session_date,
        historical_states_by_date=historical_states_by_date,
    )
    return advance_dividend_lifecycle(snapshotted, session_date=session_date)


def paper_total_return_nav_idr(
    state: DividendAwarePaperState,
    close_prices: Mapping[str, float],
) -> float:
    cash, positions, _, _ = normalize_state(state.base_state)
    ledger = normalize_dividend_ledger(state.dividend_ledger)
    market_value = 0.0
    for symbol, shares in positions.items():
        if symbol not in close_prices:
            raise DecisionV1Error(f"DIVIDEND_V1_NAV_CLOSE_MISSING:{symbol}")
        close = _positive(close_prices[symbol], f"DIVIDEND_V1_NAV_CLOSE_INVALID:{symbol}")
        market_value += shares * close
    receivable_value = sum(x.gross_amount_idr for x in ledger.receivables)
    nav = cash + market_value + receivable_value
    if not math.isfinite(nav) or nav <= 0:
        raise DecisionV1Error("DIVIDEND_V1_NAV_INVALID")
    return float(nav)


def prepare_execution_v1_1(
    verified_plan: VerifiedDecisionPlan,
    state: DividendAwarePaperState,
    *,
    eod_inputs: VerifiedEODExecutionInputs,
) -> DividendAwareExecutionOrderPlan:
    state_hash = dividend_aware_state_hash(state)
    ledger_hash = dividend_ledger_hash(state.dividend_ledger)
    base_plan = prepare_execution_v1(verified_plan, state.base_state, eod_inputs=eod_inputs)
    corrected_nav = paper_total_return_nav_idr(state, eod_inputs.raw_close_prices)
    if not math.isclose(corrected_nav, base_plan.eod_nav_idr, rel_tol=0.0, abs_tol=1e-6):
        sizing_plan = _size_entries_for_intents(
            verified_plan,
            base_plan.effective_buy_intents,
            nav_idr=corrected_nav,
            available_cash_idr=base_plan.projected_cash_for_sizing_idr,
            reference_prices=eod_inputs.raw_close_prices,
        )
        if sizing_plan._verification_token is not _SIZING_PLAN_TOKEN:
            raise DecisionV1Error("DIVIDEND_V1_SIZING_PLAN_NOT_VERIFIED")
        base_plan = replace(base_plan, eod_nav_idr=corrected_nav, sizing_plan=sizing_plan)
    return DividendAwareExecutionOrderPlan(
        base_plan=base_plan,
        dividend_state_hash=state_hash,
        dividend_ledger_hash=ledger_hash,
        total_return_nav_idr=corrected_nav,
    )


def prepare_execution_v1_1_from_decision_v2(
    verified_plan: object,
    state: DividendAwarePaperState,
    *,
    eod_inputs: object,
) -> DividendAwareExecutionOrderPlan:
    """Dividend-aware wrapper for the accepted Decision V2 execution adapter.

    The adapter remains the authority for frozen Execution V1 mechanics; this
    wrapper only replaces the sizing NAV with total-return NAV when an already
    earned receivable exists.
    """
    from .v4_x1_execution_v1_decision_v2_adapter import (
        prepare_execution_v1_from_decision_v2,
    )
    from .v4_x1_sizing_v1_decision_v2_adapter import _require_verified_v2
    from .v4_x1_sizing_v1 import _size_entries_core

    base_plan = prepare_execution_v1_from_decision_v2(
        verified_plan,
        state.base_state,
        eod_inputs=eod_inputs,
    )
    corrected_nav = paper_total_return_nav_idr(state, eod_inputs.raw_close_prices)
    if not math.isclose(corrected_nav, base_plan.eod_nav_idr, rel_tol=0.0, abs_tol=1e-6):
        decision_plan = _require_verified_v2(verified_plan)
        sizing_plan = _size_entries_core(
            decision_session_date=decision_plan.decision_session_date,
            target_positions=decision_plan.target_positions,
            intents=base_plan.effective_buy_intents,
            nav_idr=corrected_nav,
            available_cash_idr=base_plan.projected_cash_for_sizing_idr,
            reference_prices=eod_inputs.raw_close_prices,
        )
        if sizing_plan._verification_token is not _SIZING_PLAN_TOKEN:
            raise DecisionV1Error("DIVIDEND_V1_SIZING_PLAN_NOT_VERIFIED")
        base_plan = replace(base_plan, eod_nav_idr=corrected_nav, sizing_plan=sizing_plan)
    return DividendAwareExecutionOrderPlan(
        base_plan=base_plan,
        dividend_state_hash=dividend_aware_state_hash(state),
        dividend_ledger_hash=dividend_ledger_hash(state.dividend_ledger),
        total_return_nav_idr=float(corrected_nav),
    )


def execute_open_v1_1(
    order_plan: DividendAwareExecutionOrderPlan,
    state: DividendAwarePaperState,
    *,
    open_inputs: VerifiedOpenExecutionInputs,
    ca_attestation: VerifiedCorporateActionAttestation,
) -> DividendAwareExecutionResult:
    if not isinstance(order_plan, DividendAwareExecutionOrderPlan):
        raise DecisionV1Error("DIVIDEND_V1_EXECUTION_PLAN_REQUIRED")
    if dividend_aware_state_hash(state) != order_plan.dividend_state_hash:
        raise DecisionV1Error("DIVIDEND_V1_STATE_HASH_MISMATCH")
    if dividend_ledger_hash(state.dividend_ledger) != order_plan.dividend_ledger_hash:
        raise DecisionV1Error("DIVIDEND_V1_LEDGER_HASH_MISMATCH")
    result = execute_open_v1(
        order_plan.base_plan,
        state.base_state,
        open_inputs=open_inputs,
        ca_attestation=ca_attestation,
    )
    return DividendAwareExecutionResult(
        base_result=result,
        state_after=DividendAwarePaperState(
            base_state=result.state_after,
            dividend_ledger=normalize_dividend_ledger(state.dividend_ledger),
        ),
    )
