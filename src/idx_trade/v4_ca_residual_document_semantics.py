"""Offline official-KSEI residual document semantics for V4 CA continuity.

This module is intentionally outcome-blind.  It accepts only two evidence
paths over already captured official KSEI schedule bytes:

1. exact Voluntary Conversion cash/tender/buyback identity -> NON_BLOCKING;
2. exact regular-market Ex / first-new-basis date -> EXACT_TRANSITION.

Record/Distribution dates are linkage fields only and are never transition
fallbacks.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from idx_trade.v4_ca_event_windows import (
    ACCEPTED_SCHEDULE_SEMANTICS,
    EventSemantic,
    event_identity,
    source_dates,
)
from idx_trade.v4_ca_schedule_semantics import (
    DATE_ANY,
    clean,
    date_iso,
    parse_ksei_schedule_transition,
    schedule_family,
)
from idx_trade.v4_ca_voluntary_conversion_semantics import (
    classify_event as classify_event_voluntary_base,
)


POLICY_ID = "V4_CA_RESIDUAL_DOCUMENT_SEMANTICS_V1"
CASH_DOCUMENT_CLASSES = {
    "VOLUNTARY_TENDER_OFFER",
    "MANDATORY_TENDER_OFFER",
    "SHARE_BUYBACK_CASH",
    "DISSENTING_SHAREHOLDER_CASH_REPURCHASE",
}


@dataclass(frozen=True)
class ParsedResidualDocument:
    expected_ticker: str
    ticker_evidenced: bool
    document_class: str
    event_family: str
    payment_dates: tuple[str, ...]
    settlement_dates: tuple[str, ...]
    cash_purchase_dates: tuple[str, ...]
    record_date: str | None
    distribution_date: str | None
    transition_date: str | None
    transition_semantic: str | None
    diagnostics: tuple[str, ...]

    @property
    def cash_identity_dates(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                set(self.payment_dates)
                | set(self.settlement_dates)
                | set(self.cash_purchase_dates)
            )
        )

    @property
    def mechanical_identity_dates(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                value
                for value in (self.record_date, self.distribution_date)
                if value
            )
        )


@dataclass(frozen=True)
class EventDocumentEvidence:
    event_id: str
    ticker: str
    event_source_type: str
    linkage_status: str
    evidence_kind: str
    document_semantic: str
    transition_date: str | None
    transition_semantic: str | None
    ksei_references: tuple[str, ...]
    source_urls: tuple[str, ...]
    source_sha256s: tuple[str, ...]
    linkage_basis: str
    diagnostics: tuple[str, ...]


def _ticker(value: Any) -> str:
    return clean(value).upper().replace(".JK", "")


def _exact_ticker_token(text: str, ticker: str) -> bool:
    if not ticker:
        return False
    return bool(
        re.search(
            rf"(?<![A-Z0-9]){re.escape(ticker)}(?![A-Z0-9])",
            str(text or "").upper(),
        )
    )


def _all_dates(text: str) -> tuple[str, ...]:
    values: list[str] = []
    for match in re.finditer(DATE_ANY, str(text or ""), flags=re.IGNORECASE):
        value = date_iso(match.group(0))
        if value:
            values.append(value)
    return tuple(values)


def _dates_after_anchors(
    text: str,
    patterns: Sequence[str],
    *,
    max_chars: int = 220,
) -> tuple[str, ...]:
    values: set[str] = set()
    normalized = str(text or "")
    for pattern in patterns:
        for anchor in re.finditer(pattern, normalized, flags=re.IGNORECASE | re.DOTALL):
            tail = normalized[anchor.end() : anchor.end() + max_chars]
            date_match = re.search(DATE_ANY, tail, flags=re.IGNORECASE)
            if not date_match:
                continue
            value = date_iso(date_match.group(0))
            if value:
                values.add(value)
    return tuple(sorted(values))


def cash_document_class(text: str, *, index_subject: str = "") -> str:
    value = clean(f"{index_subject} {text}").casefold()
    if (
        "pemegang saham yang tidak setuju" in value
        and ("pembelian kembali" in value or "repurchase" in value)
    ):
        return "DISSENTING_SHAREHOLDER_CASH_REPURCHASE"
    if "penawaran tender sukarela" in value or "voluntary tender offer" in value:
        return "VOLUNTARY_TENDER_OFFER"
    if "penawaran tender wajib" in value or "mandatory tender offer" in value:
        return "MANDATORY_TENDER_OFFER"
    if (
        "pembelian kembali saham" in value
        or "harga pembelian kembali saham" in value
        or "share buyback" in value
        or "repurchase of shares" in value
        or "share repurchase" in value
    ):
        return "SHARE_BUYBACK_CASH"
    return "NONE"


def _explicit_transition_from_layout(layout_text: str) -> tuple[str | None, str | None, tuple[str, ...]]:
    """Read an explicit transition only when one date is bound to the anchor.

    PDF table extraction can preserve schedule rows in layout mode even when
    plain extraction groups all labels before all dates.  We use only a line or
    short adjacent-line window containing one unambiguous date.
    """

    lines = [clean(line) for line in str(layout_text or "").splitlines() if clean(line)]
    ex_hits: set[str] = set()
    basis_hits: set[str] = set()
    for index in range(len(lines)):
        window = " ".join(lines[index : index + 3])
        dates = set(_all_dates(window))
        if len(dates) != 1:
            continue
        value = next(iter(dates))
        folded = window.casefold()
        regular = any(
            token in folded
            for token in ("pasar reguler", "pasar regular", "regular market")
        )
        if not regular:
            continue
        if any(
            token in folded
            for token in (
                "ex hmetd",
                "tidak memuat hmetd",
                "ex dividen",
                "ex-date",
                "ex date",
            )
        ):
            ex_hits.add(value)
        if (
            ("mulai perdagangan" in folded or "first trading" in folded or "start trading" in folded)
            and (
                "nilai nominal baru" in folded
                or "new nominal value" in folded
                or "basis baru" in folded
                or "new basis" in folded
            )
        ):
            basis_hits.add(value)

    diagnostics: list[str] = []
    if len(ex_hits) > 1 or len(basis_hits) > 1:
        return None, None, ("MULTIPLE_LAYOUT_TRANSITION_DATES",)
    ex_date = next(iter(ex_hits)) if ex_hits else None
    basis_date = next(iter(basis_hits)) if basis_hits else None
    if ex_date and basis_date and ex_date != basis_date:
        return None, None, ("LAYOUT_TRANSITION_SEMANTICS_CONFLICT",)
    if ex_date:
        return ex_date, "REGULAR_MARKET_EX_DATE", tuple(diagnostics)
    if basis_date:
        return basis_date, "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE", tuple(diagnostics)
    return None, None, ("NO_LAYOUT_EXPLICIT_TRANSITION",)


def parse_residual_document(
    plain_text: str,
    *,
    expected_ticker: str,
    index_subject: str = "",
    layout_text: str = "",
) -> ParsedResidualDocument:
    ticker = _ticker(expected_ticker)
    combined = f"{index_subject}\n{plain_text}"
    ticker_evidenced = _exact_ticker_token(combined, ticker)
    diagnostics: list[str] = []
    if not ticker_evidenced:
        diagnostics.append("EXPECTED_TICKER_NOT_EVIDENCED")

    cash_class = cash_document_class(plain_text, index_subject=index_subject)
    family = schedule_family(clean(f"{index_subject} {plain_text[:5000]}"))

    payment_dates = _dates_after_anchors(
        plain_text,
        (
            r"Tanggal\s+Pembayaran(?:\s+hasil\s+(?:Penawaran\s+)?Tender)?",
            r"Payment\s+Date",
            r"Tanggal\s+Pembayaran\s+Pembelian\s+Kembali",
        ),
    )
    settlement_dates = _dates_after_anchors(
        plain_text,
        (
            r"Tanggal\s+Penyelesaian(?:\s+Transaksi)?",
            r"Settlement\s+Date",
            r"Tanggal\s+Penyelesaian\s+Penawaran\s+Tender",
        ),
    )
    cash_purchase_dates = _dates_after_anchors(
        plain_text,
        (
            r"Tanggal\s+Pembelian\s+Kembali",
            r"Purchase\s+Date",
            r"Repurchase\s+Date",
        ),
    )

    parsed = parse_ksei_schedule_transition(plain_text)
    transition_date = parsed.transition_date
    transition_semantic = parsed.transition_semantic
    layout_date, layout_semantic, layout_diag = _explicit_transition_from_layout(layout_text)

    if transition_date and layout_date and transition_date != layout_date:
        diagnostics.append("PLAIN_LAYOUT_TRANSITION_CONFLICT")
        transition_date = None
        transition_semantic = None
    elif not transition_date and layout_date:
        transition_date = layout_date
        transition_semantic = layout_semantic

    diagnostics.extend(parsed.diagnostics)
    diagnostics.extend(layout_diag)
    diagnostics = list(dict.fromkeys(diagnostics))

    return ParsedResidualDocument(
        expected_ticker=ticker,
        ticker_evidenced=ticker_evidenced,
        document_class=cash_class,
        event_family=family,
        payment_dates=payment_dates,
        settlement_dates=settlement_dates,
        cash_purchase_dates=cash_purchase_dates,
        record_date=parsed.record_date,
        distribution_date=parsed.distribution_date,
        transition_date=transition_date,
        transition_semantic=transition_semantic,
        diagnostics=tuple(diagnostics),
    )


def _source_date_set(event_row: Mapping[str, Any]) -> set[str]:
    if clean(event_row.get("source_dates")):
        return {
            value
            for token in clean(event_row.get("source_dates")).split("|")
            if (value := date_iso(token) or clean(token))
        }
    return {value.date().isoformat() for value in source_dates(event_row)}


def compatible_family(source_type: str, parsed_family: str) -> bool:
    source = clean(source_type).casefold()
    family = clean(parsed_family)
    if source == "right distribution":
        return family == "RIGHTS_HMETD"
    if source == "stock dividend":
        return family in {"STOCK_DIVIDEND", "MIXED_DIVIDEND"}
    if source == "mixed dividend":
        return family == "MIXED_DIVIDEND"
    if "bonus" in source:
        return family == "BONUS_SHARES"
    if source == "mandatory conversion":
        return family in {
            "STOCK_SPLIT",
            "REVERSE_SPLIT",
            "MERGER_OR_RESTRUCTURING",
            "CONVERSION",
        }
    if source == "stock split":
        return family == "STOCK_SPLIT"
    if source in {"reverse stock", "reverse stock split", "reverse split"}:
        return family == "REVERSE_SPLIT"
    if source in {"merger", "capital restructuring", "capital reduction"}:
        return family == "MERGER_OR_RESTRUCTURING"
    return False


def resolve_event_document_evidence(
    event_row: Mapping[str, Any],
    documents: Sequence[Mapping[str, Any]],
    *,
    official_sessions: Iterable[Any],
) -> EventDocumentEvidence:
    event_id = clean(event_row.get("event_id"))
    ticker = _ticker(event_row.get("ticker"))
    source_type = clean(event_row.get("source_type") or event_row.get("event_source_type"))
    source_dates_set = _source_date_set(event_row)
    sessions = {
        pd.Timestamp(value).normalize().date().isoformat()
        for value in official_sessions
        if not pd.isna(pd.to_datetime(value, errors="coerce"))
    }

    cash_links: list[Mapping[str, Any]] = []
    transition_links: list[Mapping[str, Any]] = []
    for row in documents:
        parsed = row.get("parsed")
        if not isinstance(parsed, ParsedResidualDocument):
            continue
        if not parsed.ticker_evidenced or parsed.expected_ticker != ticker:
            continue
        if source_type.casefold() == "voluntary conversion" and parsed.document_class in CASH_DOCUMENT_CLASSES:
            if source_dates_set & set(parsed.cash_identity_dates):
                cash_links.append(row)
        if compatible_family(source_type, parsed.event_family):
            if not (source_dates_set & set(parsed.mechanical_identity_dates)):
                continue
            if parsed.transition_semantic not in ACCEPTED_SCHEDULE_SEMANTICS:
                continue
            if not parsed.transition_date or parsed.transition_date not in sessions:
                continue
            transition_links.append(row)

    if cash_links and transition_links:
        return EventDocumentEvidence(
            event_id, ticker, source_type, "CONFLICT", "CONFLICT", "CASH_AND_MECHANICAL_EVIDENCE",
            None, None, (), (), (), "FAIL_CLOSED", ("CASH_AND_TRANSITION_EVIDENCE_BOTH_LINKED",),
        )

    if cash_links:
        semantics = tuple(sorted({row["parsed"].document_class for row in cash_links}))
        return EventDocumentEvidence(
            event_id=event_id,
            ticker=ticker,
            event_source_type=source_type,
            linkage_status="EXACT_NON_BLOCKING",
            evidence_kind="VOLUNTARY_CASH_NON_BLOCKING",
            document_semantic="|".join(semantics),
            transition_date=None,
            transition_semantic=None,
            ksei_references=tuple(sorted({clean(row.get("reference")) for row in cash_links if clean(row.get("reference"))})),
            source_urls=tuple(sorted({clean(row.get("source_url")) for row in cash_links if clean(row.get("source_url"))})),
            source_sha256s=tuple(sorted({clean(row.get("source_sha256")) for row in cash_links if clean(row.get("source_sha256"))})),
            linkage_basis="EXACT_TICKER_CASH_DOCUMENT_AND_SOURCE_DATE_TO_PAYMENT_SETTLEMENT_PURCHASE_DATE",
            diagnostics=(),
        )

    if transition_links:
        dates = {row["parsed"].transition_date for row in transition_links}
        semantics = {row["parsed"].transition_semantic for row in transition_links}
        if len(dates) != 1 or len(semantics) != 1:
            return EventDocumentEvidence(
                event_id, ticker, source_type, "CONFLICT", "CONFLICT", "CONFLICTING_TRANSITIONS",
                None, None, (), (), (), "FAIL_CLOSED", ("CONFLICTING_EXACT_TRANSITIONS",),
            )
        return EventDocumentEvidence(
            event_id=event_id,
            ticker=ticker,
            event_source_type=source_type,
            linkage_status="EXACT",
            evidence_kind="EXACT_TRANSITION",
            document_semantic="MECHANICAL_REGULAR_MARKET_BASIS_TRANSITION",
            transition_date=next(iter(dates)),
            transition_semantic=next(iter(semantics)),
            ksei_references=tuple(sorted({clean(row.get("reference")) for row in transition_links if clean(row.get("reference"))})),
            source_urls=tuple(sorted({clean(row.get("source_url")) for row in transition_links if clean(row.get("source_url"))})),
            source_sha256s=tuple(sorted({clean(row.get("source_sha256")) for row in transition_links if clean(row.get("source_sha256"))})),
            linkage_basis="EXACT_TICKER_FAMILY_SOURCE_DATE_AND_EXPLICIT_REGULAR_MARKET_TRANSITION",
            diagnostics=(),
        )

    return EventDocumentEvidence(
        event_id=event_id,
        ticker=ticker,
        event_source_type=source_type,
        linkage_status="UNRESOLVED",
        evidence_kind="UNRESOLVED",
        document_semantic="",
        transition_date=None,
        transition_semantic=None,
        ksei_references=(),
        source_urls=(),
        source_sha256s=(),
        linkage_basis="NO_EXACT_ADMISSIBLE_DOCUMENT_LINK",
        diagnostics=("NO_EXACT_ADMISSIBLE_DOCUMENT_LINK",),
    )


def classify_event_with_residual_document_evidence(
    row: Mapping[str, Any],
    *,
    official_sessions: Iterable[Any],
    schedule_evidence: Iterable[Mapping[str, Any]] = (),
) -> EventSemantic:
    """Overlay exact non-blocking cash evidence; exact transitions use parent path."""

    evidence_rows = list(schedule_evidence)
    base = classify_event_voluntary_base(
        row,
        official_sessions=official_sessions,
        schedule_evidence=evidence_rows,
    )
    event_id = event_identity(row)
    cash_rows = [
        evidence
        for evidence in evidence_rows
        if clean(evidence.get("event_id")) == event_id
        and clean(evidence.get("linkage_status")) == "EXACT_NON_BLOCKING"
        and clean(evidence.get("evidence_kind")) == "VOLUNTARY_CASH_NON_BLOCKING"
        and clean(evidence.get("ksei_reference"))
        and clean(evidence.get("source_sha256"))
    ]
    conflict_rows = [
        evidence
        for evidence in evidence_rows
        if clean(evidence.get("event_id")) == event_id
        and clean(evidence.get("linkage_status")) == "CONFLICT"
    ]
    if conflict_rows:
        return EventSemantic(
            event_id=base.event_id,
            ticker=base.ticker,
            source_type=base.source_type,
            family=base.family,
            semantic_class="SCHEDULE_REQUIRED",
            transition_date=None,
            transition_source=None,
            reason="RESIDUAL_DOCUMENT_EVIDENCE_CONFLICT_FAIL_CLOSED",
            source_dates=base.source_dates,
        )
    if not cash_rows:
        return base
    if clean(row.get("event_family_source")).casefold() != "voluntary conversion":
        return base
    if base.semantic_class == "EXACT_TRANSITION":
        return EventSemantic(
            event_id=base.event_id,
            ticker=base.ticker,
            source_type=base.source_type,
            family=base.family,
            semantic_class="SCHEDULE_REQUIRED",
            transition_date=None,
            transition_source=None,
            reason="CASH_AND_TRANSITION_EVIDENCE_CONFLICT_FAIL_CLOSED",
            source_dates=base.source_dates,
        )
    return EventSemantic(
        event_id=base.event_id,
        ticker=base.ticker,
        source_type=base.source_type,
        family="VOLUNTARY_CASH_DOCUMENT_SETTLEMENT",
        semantic_class="NON_BLOCKING",
        transition_date=None,
        transition_source=None,
        reason="EXACT_OFFICIAL_KSEI_CASH_DOCUMENT_NOT_MARKET_WIDE_PRICE_BASIS_REBASE",
        source_dates=base.source_dates,
    )
