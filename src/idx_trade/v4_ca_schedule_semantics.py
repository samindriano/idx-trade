"""Exact official-KSEI schedule semantics for V4 CA continuity.

Only explicit regular-market basis transition dates are admitted.  Record and
distribution dates are retained for deterministic linkage but are never used as
fallback transition dates.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


MONTHS = {
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
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
MONTH_PATTERN = "|".join(sorted(MONTHS, key=len, reverse=True))
DATE_PATTERN = rf"(\d{{1,2}})\s+({MONTH_PATTERN})\s+(\d{{4}})"


@dataclass(frozen=True)
class ParsedScheduleTransition:
    parse_status: str
    ksei_reference: str | None
    ticker: str | None
    subject: str | None
    event_family: str
    document_date: str | None
    record_date: str | None
    distribution_date: str | None
    transition_date: str | None
    transition_semantic: str | None
    diagnostics: tuple[str, ...]


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def date_iso(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(DATE_PATTERN, value, flags=re.IGNORECASE)
    if not match:
        return None
    day = int(match.group(1))
    month = MONTHS.get(match.group(2).casefold())
    year = int(match.group(3))
    if month is None:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def _date_after(pattern: str, text: str) -> str | None:
    match = re.search(
        rf"{pattern}.{{0,160}}?({DATE_PATTERN})",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    # The outer capture contains the full date; nested captures follow it.
    return date_iso(match.group(1))


def schedule_family(subject: str | None) -> str:
    value = clean(subject).casefold()
    if "hmetd" in value or "hak memesan efek terlebih dahulu" in value:
        return "RIGHTS_HMETD"
    if "dividen saham" in value or "share dividend" in value:
        if "dividen tunai" in value or "cash dividend" in value:
            return "MIXED_DIVIDEND"
        return "STOCK_DIVIDEND"
    if "saham bonus" in value or "bonus share" in value:
        return "BONUS_SHARES"
    if "stock split" in value or "pemecahan saham" in value:
        return "STOCK_SPLIT"
    if "reverse stock" in value or "reverse split" in value or "penggabungan nominal" in value:
        return "REVERSE_SPLIT"
    if "merger" in value or "penggabungan" in value or "akuisisi" in value or "acquisition" in value:
        return "MERGER_OR_RESTRUCTURING"
    if "conversion" in value or "konversi" in value:
        return "CONVERSION"
    return "UNKNOWN"


def _ticker_from_text(text: str, subject: str | None) -> str | None:
    patterns = [
        r"Kode\s+dan\s+Nama\s+Saham\s*:?\s*([A-Z0-9]{4})\b",
        r"Shares?\s+Code\s+and\s+Name\s*:?\s*([A-Z0-9]{4})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).upper()
    if subject:
        matches = re.findall(r"\(([A-Z0-9]{4})\)", subject.upper())
        if len(matches) == 1:
            return matches[0]
    return None


def parse_ksei_schedule_transition(text: str) -> ParsedScheduleTransition:
    normalized = str(text or "").replace("\r", "")
    compact = clean(normalized)
    diagnostics: list[str] = []

    ref = None
    ref_match = re.search(
        r"(?:Nomor|No\.?|Number)\s*:\s*(KSEI-[0-9]+/[A-Z]+/[0-9]+)",
        normalized,
        flags=re.IGNORECASE,
    )
    if ref_match:
        ref = ref_match.group(1).upper()
    else:
        diagnostics.append("MISSING_KSEI_REFERENCE")

    subject = None
    subject_match = re.search(
        r"(?:Perihal|Re)\s*:\s*(.+?)(?=\n\s*\n|\n\s*(?:Berdasarkan|Based on|Dengan hormat|Dear)\b|$)",
        normalized,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if subject_match:
        subject = clean(subject_match.group(1))
    else:
        diagnostics.append("MISSING_SUBJECT")

    ticker = _ticker_from_text(normalized, subject)
    if ticker is None:
        diagnostics.append("MISSING_TICKER")

    document_date = None
    if ref_match:
        tail = normalized[ref_match.end() : ref_match.end() + 180]
        document_date = date_iso(tail)
    if document_date is None:
        jakarta = re.search(
            rf"(?:Jakarta|Jakarta,)\s*,?\s*({DATE_PATTERN})",
            normalized,
            flags=re.IGNORECASE,
        )
        document_date = date_iso(jakarta.group(1)) if jakarta else None

    record_date = _date_after(
        r"(?:Tanggal\s+(?:Pencatatan|Penentuan)[^\n]{0,100}(?:Recording\s+Date)?|Recording\s+Date)",
        normalized,
    )
    distribution_date = _date_after(
        r"(?:Tanggal|Periode)?\s*(?:Distribusi|Pendistribusian|Pembayaran|Distribution\s+Date|Distribution)",
        normalized,
    )

    # Entitlement-style CA: the regular/negotiated Ex Date is the exact point
    # at which regular-market prices cease carrying the entitlement.
    ex_patterns = [
        r"(?:Tanggal\s+)?(?:perdagangan\s+bursa\s+)?(?:tidak\s+memuat\s+HMETD|Ex\s+HMETD|Ex\s+Dividen|Ex\s+Date|Ex-Date)[^\n]{0,140}(?:Pasar\s+Reguler|Regular\s+Market)[^\n]{0,80}",
        r"(?:Bonus\s+Shares?|Dividen\s+Saham|Share\s+Dividend)[^\n]{0,80}Ex(?:-Date|\s+Date)?[^\n]{0,120}(?:Regular\s+Market|Pasar\s+Reguler)[^\n]{0,80}",
    ]
    regular_ex = None
    for pattern in ex_patterns:
        regular_ex = _date_after(pattern, normalized)
        if regular_ex:
            break

    # Split/reverse split: regular-market price basis changes on the first
    # trading date using the new nominal/share basis, not on record/distribution.
    new_basis_patterns = [
        r"Mulai\s+perdagangan\s+saham\s+dengan\s+Nilai\s+Nominal\s+Baru[^\n]{0,180}(?:Pasar\s+Reguler|Pasar\s+Negosiasi)[^\n]{0,80}",
        r"(?:First|Start)\s+(?:Trading|trading)\s+of\s+Shares?\s+with\s+(?:the\s+)?New\s+Nominal\s+Value[^\n]{0,180}(?:Regular\s+Market|Negotiated\s+Market)[^\n]{0,80}",
    ]
    first_new_basis = None
    for pattern in new_basis_patterns:
        first_new_basis = _date_after(pattern, normalized)
        if first_new_basis:
            break

    if regular_ex and first_new_basis and regular_ex != first_new_basis:
        diagnostics.append("MULTIPLE_TRANSITION_SEMANTICS_CONFLICT")
        transition = None
        semantic = None
    elif regular_ex:
        transition = regular_ex
        semantic = "REGULAR_MARKET_EX_DATE"
    elif first_new_basis:
        transition = first_new_basis
        semantic = "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE"
    else:
        transition = None
        semantic = None
        diagnostics.append("NO_EXPLICIT_REGULAR_MARKET_TRANSITION")

    family = schedule_family(subject)
    if family == "UNKNOWN":
        diagnostics.append("UNKNOWN_SCHEDULE_FAMILY")

    parse_status = (
        "PARSED_EXACT_TRANSITION"
        if ref and ticker and subject and transition and semantic
        else "UNRESOLVED"
    )
    return ParsedScheduleTransition(
        parse_status=parse_status,
        ksei_reference=ref,
        ticker=ticker,
        subject=subject,
        event_family=family,
        document_date=document_date,
        record_date=record_date,
        distribution_date=distribution_date,
        transition_date=transition,
        transition_semantic=semantic,
        diagnostics=tuple(diagnostics),
    )
