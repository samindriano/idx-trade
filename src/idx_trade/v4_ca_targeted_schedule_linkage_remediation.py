"""Strict V4 remediation for KSEI stock-split rows split across PDF lines.

This module is intentionally narrower than the preceding layout/geometry
remediation. It accepts a stock-split transition only when the semantic anchor
(``Mulai perdagangan ... Nilai Nominal Baru``) is on one PDF-extracted line and
the immediately following line completes the Regular-Market phrase. The joined
two-line row must contain exactly one explicit calendar date.

Document-to-event linkage remains independent from that transition extraction:
all frozen source dates for the event must be explicitly present somewhere in
the same official document, and the caller must separately enforce unique
candidate-document identity.
"""

from __future__ import annotations

import re
from typing import Iterable

from idx_trade.v4_ca_schedule_semantics import clean, date_iso
from idx_trade.v4_ca_targeted_schedule_parser_remediation import DATE_TEXT


STOCK_SPLIT_ANCHOR = re.compile(
    r"Mulai\s+perdagangan\s+saham\s+dengan\s+Nilai\s+Nominal\s+Baru",
    flags=re.IGNORECASE,
)
REGULAR_MARKET_ANCHOR = re.compile(
    r"(?:Pasar\s+Reguler|Pasar\s+Regular|Regular\s+Market)",
    flags=re.IGNORECASE,
)


def explicit_date_set(text: str) -> set[str]:
    """Return every explicit full calendar date appearing in official text."""

    values: set[str] = set()
    for match in re.finditer(DATE_TEXT, str(text or ""), flags=re.IGNORECASE):
        value = date_iso(match.group(0))
        if value:
            values.add(value)
    return values


def _dates(text: str) -> list[str]:
    values: list[str] = []
    for match in re.finditer(DATE_TEXT, text, flags=re.IGNORECASE):
        value = date_iso(match.group(0))
        if value:
            values.append(value)
    return values


def two_line_stock_split_transition(text: str) -> tuple[str | None, tuple[str, ...]]:
    """Extract one exact new-basis Regular-Market date from a two-line row.

    Only the anchor line and its immediately following non-empty line are
    joined. This specifically addresses KSEI PDFs where the schedule label/date
    remains on the first visual row fragment while ``Pasar Reguler ...`` wraps
    to the next fragment. No ordering of detached date lists is permitted.
    """

    lines = [clean(line) for line in str(text or "").replace("\r", "").splitlines() if clean(line)]
    candidates: set[str] = set()
    ambiguous = False

    for index, line in enumerate(lines):
        if not STOCK_SPLIT_ANCHOR.search(line):
            continue
        window = line
        if index + 1 < len(lines):
            window = f"{line} {lines[index + 1]}"
        if not REGULAR_MARKET_ANCHOR.search(window):
            continue
        dates = _dates(window)
        if len(dates) == 1:
            candidates.add(dates[0])
        elif len(dates) > 1:
            ambiguous = True

    if ambiguous or len(candidates) > 1:
        return None, ("MULTIPLE_OR_AMBIGUOUS_TWO_LINE_STOCK_SPLIT_TRANSITIONS",)
    if len(candidates) == 1:
        return next(iter(candidates)), ()
    return None, ("NO_EXACT_TWO_LINE_STOCK_SPLIT_TRANSITION",)


def frozen_source_dates_contained(source_dates: Iterable[str], document_dates: set[str]) -> bool:
    source = {clean(value) for value in source_dates if clean(value)}
    return bool(source) and source.issubset(document_dates)
