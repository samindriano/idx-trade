"""Strict offline remediation for KSEI schedule PDFs already captured in V4 CA.

The original targeted acquisition used normal pypdf text extraction. Several
KSEI table PDFs flattened column headers before their values, which caused two
failures: the header token ``KODE`` could be mistaken for the ticker, and an
explicit regular-market transition could lose its row/date association.

This module repairs only those parser mechanics. It does not fetch providers,
does not infer from prices, and never promotes Record/Distribution dates to a
transition. Exact transition dates are admitted only when the semantic anchor
and one date occur on the same layout-preserved PDF line.
"""

from __future__ import annotations

from dataclasses import replace
import re
from typing import Iterable

from idx_trade.v4_ca_schedule_semantics import (
    ParsedScheduleTransition,
    clean,
    date_iso,
    schedule_family,
)


INVALID_TICKER_TOKENS = {"KODE", "ISIN", "NAMA", "EMIT"}
DATE_TEXT = (
    r"(?:\d{1,2}\s+(?:Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|"
    r"September|Oktober|November|Desember|January|February|March|April|May|"
    r"June|July|August|September|October|November|December)\s+\d{4}|"
    r"(?:Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|"
    r"November|Desember|January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{1,2}\s*,?\s+\d{4})"
)


def _valid_ticker(value: str) -> str | None:
    token = str(value or "").upper()
    if token in INVALID_TICKER_TOKENS:
        return None
    if not re.fullmatch(r"[A-Z0-9]{4}", token):
        return None
    return token


def strict_ticker_from_layout(text: str, subject: str | None = None) -> str | None:
    """Extract the security code without ever admitting the header word KODE."""

    patterns = (
        r"(?:Kode\s+dan\s+Nama\s+Saham|Kode\s+Saham|Shares?\s+Code\s+and\s+Name)\s*:?\s*([A-Z0-9]{4})\s*-",
        r":\s*([A-Z][A-Z0-9]{3})\s*-\s*[A-Z]",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            token = _valid_ticker(match.group(1))
            if token:
                return token

    if subject:
        tokens = {
            token
            for raw in re.findall(r"\(([A-Z0-9]{4})\)", subject.upper())
            if (token := _valid_ticker(raw))
        }
        if len(tokens) == 1:
            return next(iter(tokens))
    return None


def _dates_on_line(line: str) -> list[str]:
    values: list[str] = []
    for match in re.finditer(DATE_TEXT, line, flags=re.IGNORECASE):
        value = date_iso(match.group(0))
        if value:
            values.append(value)
    return values


def _single_date_for_lines(lines: Iterable[str], pattern: str) -> str | None:
    candidates: set[str] = set()
    for raw_line in lines:
        line = clean(raw_line)
        if not re.search(pattern, line, flags=re.IGNORECASE):
            continue
        dates = _dates_on_line(line)
        if len(dates) == 1:
            candidates.add(dates[0])
        elif len(dates) > 1:
            return None
    return next(iter(candidates)) if len(candidates) == 1 else None


def strict_layout_transition(text: str) -> tuple[str | None, str | None, tuple[str, ...]]:
    """Return an exact transition only from one semantic row and one row date."""

    lines = str(text or "").replace("\r", "").splitlines()
    candidates: set[tuple[str, str]] = set()

    stock_split = _single_date_for_lines(
        lines,
        r"Mulai\s+perdagangan\s+saham\s+dengan\s+Nilai\s+Nominal\s+Baru.*(?:Pasar\s+Reguler|Pasar\s+Regular|Regular\s+Market)",
    )
    if stock_split:
        candidates.add((stock_split, "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE"))

    rights_ex = _single_date_for_lines(
        lines,
        r"(?:(?:tidak\s+memuat\s+HMETD|Ex\s+HMETD|Ex\s+Dividen|Ex\s+Date|Ex-Date)|(?:Tanggal\s+)?Ex(?:\s+HMETD)?(?:\s+di|\s+pada)?).*(?:Pasar\s+Reguler|Pasar\s+Regular|Regular\s+Market)",
    )
    if rights_ex:
        candidates.add((rights_ex, "REGULAR_MARKET_EX_DATE"))

    bonus_ex = _single_date_for_lines(
        lines,
        r"(?:Bonus\s+Shares?|Dividen\s+Saham|Share\s+Dividend).*Ex(?:-Date|\s+Date)?.*(?:Regular\s+Market|Pasar\s+Reguler|Pasar\s+Regular)",
    )
    if bonus_ex:
        candidates.add((bonus_ex, "REGULAR_MARKET_EX_DATE"))

    if len(candidates) == 1:
        date_value, semantic = next(iter(candidates))
        return date_value, semantic, ()
    if len(candidates) > 1:
        return None, None, ("MULTIPLE_LAYOUT_TRANSITION_SEMANTICS_CONFLICT",)
    return None, None, ("NO_EXPLICIT_LAYOUT_REGULAR_MARKET_TRANSITION",)


def repair_layout_parse(text: str, parsed: ParsedScheduleTransition) -> ParsedScheduleTransition:
    """Repair identity and row/date semantics from layout-preserved official text."""

    normalized = str(text or "").replace("\r", "")
    lines = normalized.splitlines()
    ticker = strict_ticker_from_layout(normalized, parsed.subject)
    family = parsed.event_family
    if family == "UNKNOWN":
        family = schedule_family(parsed.subject or normalized)

    record_date = _single_date_for_lines(
        lines,
        r"(?:Tanggal\s+(?:Pencatatan|Penentuan)|Recording\s+Date)",
    )
    distribution_date = _single_date_for_lines(
        lines,
        r"(?:Tanggal|Periode)?\s*(?:Distribusi|Pendistribusian|Pembayaran|Distribution\s+Date|Distribution)",
    )
    transition_date, transition_semantic, transition_diagnostics = strict_layout_transition(normalized)

    diagnostics = [
        value
        for value in parsed.diagnostics
        if value not in {
            "MISSING_TICKER",
            "UNKNOWN_SCHEDULE_FAMILY",
            "NO_EXPLICIT_REGULAR_MARKET_TRANSITION",
        }
    ]
    diagnostics.extend(transition_diagnostics)

    parse_status = (
        "PARSED_EXACT_TRANSITION"
        if parsed.ksei_reference
        and ticker
        and family != "UNKNOWN"
        and transition_date
        and transition_semantic
        else "UNRESOLVED"
    )
    return replace(
        parsed,
        parse_status=parse_status,
        ticker=ticker,
        event_family=family,
        record_date=record_date,
        distribution_date=distribution_date,
        transition_date=transition_date,
        transition_semantic=transition_semantic,
        diagnostics=tuple(dict.fromkeys(diagnostics)),
    )
