"""Pre-run hardening for residual KSEI document date binding.

The base residual parser identifies document class/family/ticker.  This module
rebinds every date that can admit evidence (cash identity, Record/Distribution
identity, or market-basis transition) to an explicit PDF-layout row.  It never
uses a later free-floating date from flattened PDF text.
"""

from __future__ import annotations

import re
from typing import Callable

from idx_trade.v4_ca_residual_document_semantics import (
    ParsedResidualDocument,
    parse_residual_document as parse_base,
)
from idx_trade.v4_ca_schedule_semantics import DATE_ANY, clean, date_iso


SEMANTIC_ANCHORS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "PAYMENT_DATE",
        (
            "tanggal pembayaran",
            "payment date",
        ),
    ),
    (
        "SETTLEMENT_DATE",
        (
            "tanggal penyelesaian",
            "settlement date",
        ),
    ),
    (
        "CASH_PURCHASE_DATE",
        (
            "tanggal pembelian kembali",
            "purchase date",
            "repurchase date",
        ),
    ),
    (
        "RECORD_DATE",
        (
            "tanggal pencatatan",
            "tanggal penentuan",
            "recording date",
            "record date",
        ),
    ),
    (
        "DISTRIBUTION_DATE",
        (
            "tanggal distribusi",
            "tanggal pendistribusian",
            "distribution date",
        ),
    ),
    (
        "REGULAR_MARKET_EX_DATE",
        (
            "ex hmetd",
            "tidak memuat hmetd",
            "ex dividen",
            "ex-date",
            "ex date",
        ),
    ),
    (
        "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE",
        (
            "mulai perdagangan",
            "first trading",
            "start trading",
        ),
    ),
)


def _dates(text: str) -> tuple[str, ...]:
    values: list[str] = []
    for match in re.finditer(DATE_ANY, str(text or ""), flags=re.IGNORECASE):
        value = date_iso(match.group(0))
        if value:
            values.append(value)
    return tuple(values)


def _semantic_for_line(line: str) -> set[str]:
    folded = clean(line).casefold()
    result: set[str] = set()
    for semantic, anchors in SEMANTIC_ANCHORS:
        if any(anchor in folded for anchor in anchors):
            if semantic == "REGULAR_MARKET_EX_DATE" and not any(
                token in folded
                for token in ("pasar reguler", "pasar regular", "regular market")
            ):
                continue
            if semantic == "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE":
                if not any(
                    token in folded
                    for token in ("pasar reguler", "pasar regular", "regular market")
                ):
                    continue
                if not any(
                    token in folded
                    for token in ("nilai nominal baru", "new nominal value", "basis baru", "new basis")
                ):
                    continue
            result.add(semantic)
    return result


def _starts_any_semantic(line: str) -> bool:
    folded = clean(line).casefold()
    return any(anchor in folded for _, anchors in SEMANTIC_ANCHORS for anchor in anchors)


def layout_bound_dates(layout_text: str) -> tuple[dict[str, tuple[str, ...]], tuple[str, ...]]:
    """Return unique dates explicitly bound to semantic rows.

    A date is admitted from the same physical layout line, or from exactly the
    next line only when that next line does not begin another semantic row.
    Multiple different dates for one semantic in the same document are kept
    unresolved for that semantic rather than choosing one.
    """

    lines = [clean(line) for line in str(layout_text or "").splitlines() if clean(line)]
    hits: dict[str, set[str]] = {semantic: set() for semantic, _ in SEMANTIC_ANCHORS}
    diagnostics: list[str] = []

    for index, line in enumerate(lines):
        semantics = _semantic_for_line(line)
        if not semantics:
            continue
        same_dates = set(_dates(line))
        if len(same_dates) == 1:
            value = next(iter(same_dates))
            for semantic in semantics:
                hits[semantic].add(value)
            continue
        if len(same_dates) > 1:
            diagnostics.append("MULTIPLE_DATES_ON_ONE_SEMANTIC_ROW")
            continue

        if index + 1 >= len(lines):
            continue
        next_line = lines[index + 1]
        if _starts_any_semantic(next_line):
            continue
        next_dates = set(_dates(next_line))
        if len(next_dates) == 1:
            value = next(iter(next_dates))
            for semantic in semantics:
                hits[semantic].add(value)
        elif len(next_dates) > 1:
            diagnostics.append("MULTIPLE_DATES_ON_SEMANTIC_CONTINUATION")

    output: dict[str, tuple[str, ...]] = {}
    for semantic, values in hits.items():
        if len(values) <= 1:
            output[semantic] = tuple(sorted(values))
        else:
            output[semantic] = ()
            diagnostics.append(f"CONFLICTING_LAYOUT_DATES:{semantic}")
    return output, tuple(dict.fromkeys(diagnostics))


def _one(values: tuple[str, ...]) -> str | None:
    return values[0] if len(values) == 1 else None


def parse_residual_document_hardened(
    plain_text: str,
    *,
    expected_ticker: str,
    index_subject: str = "",
    layout_text: str = "",
) -> ParsedResidualDocument:
    base = parse_base(
        plain_text,
        expected_ticker=expected_ticker,
        index_subject=index_subject,
        layout_text=layout_text,
    )
    bound, diagnostics = layout_bound_dates(layout_text or plain_text)

    ex_date = _one(bound["REGULAR_MARKET_EX_DATE"])
    new_basis = _one(bound["REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE"])
    transition_date: str | None = None
    transition_semantic: str | None = None
    extra_diag = list(diagnostics)
    if ex_date and new_basis and ex_date != new_basis:
        extra_diag.append("LAYOUT_EX_NEW_BASIS_CONFLICT")
    elif ex_date:
        transition_date = ex_date
        transition_semantic = "REGULAR_MARKET_EX_DATE"
    elif new_basis:
        transition_date = new_basis
        transition_semantic = "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE"

    return ParsedResidualDocument(
        expected_ticker=base.expected_ticker,
        ticker_evidenced=base.ticker_evidenced,
        document_class=base.document_class,
        event_family=base.event_family,
        payment_dates=bound["PAYMENT_DATE"],
        settlement_dates=bound["SETTLEMENT_DATE"],
        cash_purchase_dates=bound["CASH_PURCHASE_DATE"],
        record_date=_one(bound["RECORD_DATE"]),
        distribution_date=_one(bound["DISTRIBUTION_DATE"]),
        transition_date=transition_date,
        transition_semantic=transition_semantic,
        diagnostics=tuple(dict.fromkeys((*base.diagnostics, *extra_diag))),
    )
