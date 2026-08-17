"""Exact official-KSEI schedule semantics for V4 CA continuity.

Only explicit regular-market basis transition dates are admitted. Record and
distribution dates are retained for deterministic linkage but are never used as
fallback transition dates.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


MONTHS = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5,
    "juni": 6, "juli": 7, "agustus": 8, "september": 9, "oktober": 10,
    "november": 11, "desember": 12, "january": 1, "february": 2,
    "march": 3, "may": 5, "june": 6, "july": 7, "august": 8,
    "october": 10, "december": 12,
}
MONTH_PATTERN = "|".join(sorted(MONTHS, key=len, reverse=True))
DAY_FIRST = rf"\d{{1,2}}\s+(?:{MONTH_PATTERN})\s+\d{{4}}"
MONTH_FIRST = rf"(?:{MONTH_PATTERN})\s+\d{{1,2}}\s*,?\s+\d{{4}}"
DATE_ANY = rf"(?:{DAY_FIRST}|{MONTH_FIRST})"


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
    text = str(value)
    match = re.search(
        rf"(\d{{1,2}})\s+({MONTH_PATTERN})\s+(\d{{4}})",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        day, month_text, year = int(match.group(1)), match.group(2), int(match.group(3))
    else:
        match = re.search(
            rf"({MONTH_PATTERN})\s+(\d{{1,2}})\s*,?\s+(\d{{4}})",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            return None
        month_text, day, year = match.group(1), int(match.group(2)), int(match.group(3))
    month = MONTHS.get(month_text.casefold())
    if month is None:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def _date_after(pattern: str, text: str) -> str | None:
    match = re.search(
        rf"{pattern}.{{0,180}}?({DATE_ANY})",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return date_iso(match.group(1)) if match else None


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
    for pattern in (
        r"Kode\s+dan\s+Nama\s+Saham\s*:?\s*([A-Z0-9]{4})\b",
        r"Shares?\s+Code\s+and\s+Name\s*:?\s*([A-Z0-9]{4})\b",
    ):
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
    diagnostics: list[str] = []

    ref_match = re.search(
        r"(?:Nomor|No\.?|Number)\s*:\s*(KSEI-[0-9]+/[A-Z]+/[0-9]+)",
        normalized,
        flags=re.IGNORECASE,
    )
    reference = ref_match.group(1).upper() if ref_match else None
    if reference is None:
        diagnostics.append("MISSING_KSEI_REFERENCE")

    subject_match = re.search(
        r"(?:Perihal|Re)\s*:\s*(.+?)(?=\n\s*\n|\n\s*(?:Berdasarkan|Based on|Dengan hormat|Dear)\b|$)",
        normalized,
        flags=re.IGNORECASE | re.DOTALL,
    )
    subject = clean(subject_match.group(1)) if subject_match else None
    if subject is None:
        diagnostics.append("MISSING_SUBJECT")

    ticker = _ticker_from_text(normalized, subject)
    if ticker is None:
        diagnostics.append("MISSING_TICKER")

    document_date = None
    if ref_match:
        document_date = date_iso(normalized[ref_match.end() : ref_match.end() + 180])
    if document_date is None:
        jakarta = re.search(
            rf"Jakarta\s*,?\s*({DATE_ANY})",
            normalized,
            flags=re.IGNORECASE,
        )
        document_date = date_iso(jakarta.group(1)) if jakarta else None

    record_date = _date_after(
        r"(?:Tanggal\s+(?:Pencatatan|Penentuan)[^\n]{0,110}(?:Recording\s+Date)?|Recording\s+Date)",
        normalized,
    )
    distribution_date = _date_after(
        r"(?:Tanggal|Periode)?\s*(?:Distribusi|Pendistribusian|Pembayaran|Distribution\s+Date|Distribution)",
        normalized,
    )

    ex_patterns = [
        r"(?:Tanggal\s+)?(?:perdagangan\s+bursa\s+)?(?:tidak\s+memuat\s+HMETD|Ex\s+HMETD|Ex\s+Dividen|Ex\s+Date|Ex-Date)[^\n]{0,150}(?:Pasar\s+Reguler|Regular\s+Market)[^\n]{0,90}",
        r"(?:Bonus\s+Shares?|Dividen\s+Saham|Share\s+Dividend)[^\n]{0,90}Ex(?:-Date|\s+Date)?[^\n]{0,130}(?:Regular\s+Market|Pasar\s+Reguler)[^\n]{0,90}",
    ]
    regular_ex = next(
        (value for pattern in ex_patterns if (value := _date_after(pattern, normalized))),
        None,
    )

    new_basis_patterns = [
        r"Mulai\s+perdagangan\s+saham\s+dengan\s+Nilai\s+Nominal\s+Baru[^\n]{0,190}(?:Pasar\s+Reguler|Pasar\s+Negosiasi)[^\n]{0,90}",
        r"(?:First|Start)\s+(?:Trading|trading)\s+of\s+Shares?\s+with\s+(?:the\s+)?New\s+Nominal\s+Value[^\n]{0,190}(?:Regular\s+Market|Negotiated\s+Market)[^\n]{0,90}",
    ]
    first_new_basis = next(
        (value for pattern in new_basis_patterns if (value := _date_after(pattern, normalized))),
        None,
    )

    if regular_ex and first_new_basis and regular_ex != first_new_basis:
        diagnostics.append("MULTIPLE_TRANSITION_SEMANTICS_CONFLICT")
        transition_date = None
        transition_semantic = None
    elif regular_ex:
        transition_date = regular_ex
        transition_semantic = "REGULAR_MARKET_EX_DATE"
    elif first_new_basis:
        transition_date = first_new_basis
        transition_semantic = "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE"
    else:
        transition_date = None
        transition_semantic = None
        diagnostics.append("NO_EXPLICIT_REGULAR_MARKET_TRANSITION")

    family = schedule_family(subject)
    if family == "UNKNOWN":
        diagnostics.append("UNKNOWN_SCHEDULE_FAMILY")

    parse_status = (
        "PARSED_EXACT_TRANSITION"
        if reference and ticker and subject and transition_date and transition_semantic
        else "UNRESOLVED"
    )
    return ParsedScheduleTransition(
        parse_status=parse_status,
        ksei_reference=reference,
        ticker=ticker,
        subject=subject,
        event_family=family,
        document_date=document_date,
        record_date=record_date,
        distribution_date=distribution_date,
        transition_date=transition_date,
        transition_semantic=transition_semantic,
        diagnostics=tuple(diagnostics),
    )
