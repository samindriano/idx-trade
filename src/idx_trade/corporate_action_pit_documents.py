"""Conservative parsing helpers for bounded KSEI schedule-document audits.

This module parses text extracted from an immutable official KSEI PDF.  It is
deliberately not a PDF downloader and does not infer missing corporate-action
fields from market prices or security-page labels.  Missing or ambiguous
document evidence remains explicit in the returned row.
"""

from __future__ import annotations

import re
from typing import Any

from .corporate_action_pit_linkage import EventFamily, normalize_event_family


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
}
_DATE = r"\d{1,2}\s+(?:Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)\s+\d{4}"


def _clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _date_iso(value: str | None) -> str | None:
    if not value:
        return None
    day, month, year = _clean(value).casefold().split()
    month_number = _MONTHS.get(month)
    if month_number is None:
        return None
    return f"{int(year):04d}-{month_number:02d}-{int(day):02d}"


def _match(pattern: str, text: str, *, flags: int = re.IGNORECASE | re.DOTALL) -> re.Match[str] | None:
    return re.search(pattern, text, flags)


def _value_after_label(label: str, text: str) -> str | None:
    found = _match(rf"{label}\s*:\s*(.+)", text, flags=re.IGNORECASE)
    return _clean(found.group(1).splitlines()[0]) if found else None


def _evidence(text: str, match: re.Match[str] | None, kind: str) -> dict[str, Any] | None:
    if match is None:
        return None
    line = text.count("\n", 0, match.start()) + 1
    return {"kind": kind, "line": line, "text": _clean(match.group(0))}


def _date_value(pattern: str, text: str, kind: str, evidence: list[dict[str, Any]]) -> str | None:
    found = _match(pattern, text)
    if found is None:
        return None
    value = _date_iso(found.group(1))
    if value is not None:
        item = _evidence(text, found, kind)
        if item:
            evidence.append(item)
    return value


def parse_ksei_schedule_text(
    text: str,
    *,
    source_url: str | None = None,
    source_sha256: str | None = None,
) -> dict[str, Any]:
    """Parse only explicit KSEI schedule-document evidence.

    The result is suitable for a bounded validation row.  ``parse_status`` is
    ``UNRESOLVED`` when identity/date evidence needed by the caller is absent;
    no heuristic fallback is attempted.
    """

    normalized = text.replace("\r", "")
    evidence: list[dict[str, Any]] = []
    ref_match = _match(r"(?:Nomor|No\.?)\s*:\s*(KSEI-[0-9]+/[A-Z]+/[0-9]+)", normalized, flags=re.IGNORECASE)
    reference = ref_match.group(1).upper() if ref_match else None
    if ref_match:
        evidence_item = _evidence(normalized, ref_match, "KSEI_REFERENCE")
        if evidence_item:
            evidence.append(evidence_item)

    subject_match = _match(r"Perihal\s*:\s*(.+?)(?=\n\s*\n|\n\s*(?:Sebagai|Berdasarkan|Jadwal|Adapun)\b|$)", normalized)
    subject = _clean(subject_match.group(1)) if subject_match else None
    if subject_match:
        evidence_item = _evidence(normalized, subject_match, "DOCUMENT_SUBJECT")
        if evidence_item:
            evidence.append(evidence_item)

    document_date_match = _match(
        rf"(?:{re.escape(reference or 'KSEI-[0-9]+/[A-Z]+/[0-9]+')}).{{0,180}}?({_DATE})|Jakarta,\s*({_DATE})",
        normalized,
    )
    document_date = _date_iso(next((group for group in document_date_match.groups() if group), None)) if document_date_match else None
    if document_date_match:
        evidence_item = _evidence(normalized, document_date_match, "DOCUMENT_DATE")
        if evidence_item:
            evidence.append(evidence_item)

    ticker_match = _match(r"Kode dan Nama Saham\s*:\s*([A-Z0-9]+)\s*-", normalized, flags=re.IGNORECASE)
    ticker = ticker_match.group(1).upper() if ticker_match else None
    if ticker_match:
        evidence_item = _evidence(normalized, ticker_match, "TICKER")
        if evidence_item:
            evidence.append(evidence_item)
    if ticker is None and subject:
        # Some KSEI follow-up/additional-information letters omit the table
        # header but put the issuer ticker in the authoritative subject.
        subject_ticker = re.search(r"\(([A-Z0-9]{2,6})\)\s*$", subject)
        if subject_ticker:
            ticker = subject_ticker.group(1).upper()
            evidence.append({"kind": "TICKER_SUBJECT", "line": 0, "text": subject})

    isin = _value_after_label("Kode ISIN(?: Saham)?", normalized)
    isin_match = _match(r"Kode ISIN(?: Saham)?\s*:\s*(ID[A-Z0-9]+)", normalized, flags=re.IGNORECASE)
    if isin_match:
        isin = isin_match.group(1).upper()
        evidence_item = _evidence(normalized, isin_match, "STOCK_ISIN")
        if evidence_item:
            evidence.append(evidence_item)

    rights_match = _match(r"Kode HMETD\s*&\s*ISIN\s*:\s*([^,\s]+)\s*,\s*(ID[A-Z0-9]+)", normalized)
    rights_code = rights_match.group(1).upper() if rights_match else None
    rights_isin = rights_match.group(2).upper() if rights_match else None
    if rights_match:
        evidence_item = _evidence(normalized, rights_match, "RIGHTS_IDENTITY")
        if evidence_item:
            evidence.append(evidence_item)

    record_date = _date_value(
        rf"Tanggal\s+Pencatatan\s*\(\s*Recording\s+Date\s*\)\s+({_DATE})",
        normalized,
        "RECORD_DATE",
        evidence,
    )
    distribution_date = _date_value(
        rf"Tanggal\s+distribusi(?:\s+saham[^\n]*)?\s+({_DATE})",
        normalized,
        "DISTRIBUTION_DATE",
        evidence,
    )
    listing_date = _date_value(
        rf"Tanggal\s+Pencatatan\s+di\s+Bursa\s+({_DATE})",
        normalized,
        "LISTING_DATE",
        evidence,
    )
    exercise_range = _match(rf"Periode\s+Pelaksanaan\s+HMETD\s+(\d{{1,2}})\s*-\s*({_DATE})", normalized)
    exercise_start_date = None
    if exercise_range:
        end_date = _date_iso(exercise_range.group(2))
        if end_date:
            year, month, _ = end_date.split("-")
            exercise_start_date = f"{year}-{month}-{int(exercise_range.group(1)):02d}"
            evidence_item = _evidence(normalized, exercise_range, "EXERCISE_START_DATE")
            if evidence_item:
                evidence.append(evidence_item)

    split_match = _match(r"Rasio\s+pemecahan\s+unit\s+saham\s*(\d+)\s*:\s*(\d+)", normalized)
    bonus_match = _match(r"setiap\s+(\d+)\s*\([^)]*\)\s+saham\s+lama\s+akan\s+mendapatkan\s+(\d+)\s*\([^)]*\)\s+saham\s+bonus", normalized)
    rights_ratio_match = _match(r"Setiap\s+(\d+)\s*\([^)]*\)\s*Saham\s+akan\s+mendapatkan\s+(\d+)\s*\([^)]*\)\s*HMETD", normalized)
    ratio_match = split_match or bonus_match or rights_ratio_match
    ratio_left_value = ratio_match.group(1) if ratio_match else None
    ratio_right_value = ratio_match.group(2) if ratio_match else None
    ratio_left_security = ticker if ratio_match else None
    ratio_right_security = rights_code or ticker if ratio_match else None
    if ratio_match:
        kind = "SPLIT_RATIO" if split_match else "RATIO"
        evidence_item = _evidence(normalized, ratio_match, kind)
        if evidence_item:
            evidence.append(evidence_item)

    exercise_match = _match(r"Harga\s+Pelaksanaan\s+Exercise\s+adalah\s+Rp\.?\s*([0-9.,]+)", normalized)
    exercise_price = exercise_match.group(1).replace(".", "").replace(",", "") if exercise_match else None
    if exercise_match:
        evidence_item = _evidence(normalized, exercise_match, "EXERCISE_PRICE")
        if evidence_item:
            evidence.append(evidence_item)

    prior_match = _match(r"Pengumuman\s+KSEI\s+No\.\s*(KSEI-[0-9]+/[A-Z]+/[0-9]+)", normalized)
    prior_reference = prior_match.group(1).upper() if prior_match else None
    if prior_match:
        evidence_item = _evidence(normalized, prior_match, "PRIOR_KSEI_REFERENCE")
        if evidence_item:
            evidence.append(evidence_item)

    family = normalize_event_family(schedule_subject=subject)
    required_identity = reference and ticker and subject and document_date
    parse_status = "PARSED" if required_identity else "UNRESOLVED"
    diagnostics = []
    if not reference:
        diagnostics.append("MISSING_KSEI_REFERENCE")
    if not ticker:
        diagnostics.append("MISSING_TICKER")
    if not subject:
        diagnostics.append("MISSING_SUBJECT")
    if not document_date:
        diagnostics.append("MISSING_DOCUMENT_DATE")

    return {
        "parse_status": parse_status,
        "diagnostics": diagnostics,
        "ksei_reference": reference,
        "document_subject": subject,
        "document_date": document_date,
        "ticker": ticker,
        "stock_isin": isin,
        "rights_code": rights_code,
        "rights_isin": rights_isin,
        "economic_family": family.value if isinstance(family, EventFamily) else str(family),
        "ratio_left_value": ratio_left_value,
        "ratio_left_security": ratio_left_security,
        "ratio_right_value": ratio_right_value,
        "ratio_right_security": ratio_right_security,
        "record_date": record_date,
        "distribution_date": distribution_date,
        "listing_date": listing_date,
        "exercise_start_date": exercise_start_date,
        "exercise_price": exercise_price,
        "prior_ksei_reference": prior_reference,
        "source_url": source_url,
        "source_sha256": source_sha256,
        "evidence": evidence,
    }
