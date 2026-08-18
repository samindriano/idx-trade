"""Outcome-blind exact entitlement semantics for the ADRO 2024 AAI/AADI PUPS.

This module does not infer an ex-date from the KSEI record/distribution dates.
It accepts 2024-11-28 only when two issuer-official documents jointly prove:

1. the PUPS participant/record set is the same 2024-11-29 ADRO shareholder set
   used for the additional final cash dividend approved by the 2024-11-18 EGMS;
   the prospectus also visibly states this linkage on its first page, although
   some pypdf builds omit that boxed all-caps sentence from extracted text; and
2. that dividend's Regular and Negotiated Market Ex Dividend date is explicitly
   2024-11-28.

The rule is bound to the exact frozen KSEI Right Distribution event identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import hashlib
import re
from typing import Any, Mapping

import pandas as pd
from pypdf import PdfReader

from idx_trade.v4_ca_event_windows import EventSemantic, source_dates


ADRO_EVENT_ID = "41c1e8493213d0151799837330c0dc7d8fea633d458c03e40b61ea0247bb9e58"
ADRO_TRANSITION_DATE = pd.Timestamp("2024-11-28")
ADRO_RECORD_DATE = "2024-11-29"
ADRO_DISTRIBUTION_DATE = "2024-12-02"
ADRO_RATIO_LEFT = "4389"
ADRO_RATIO_RIGHT = "1000"
ADRO_RATIO_LEFT_SECURITY = "ADRO"
ADRO_RATIO_RIGHT_SECURITY = "ADRO-H"

ADRO_PUPS_PROSPECTUS_URL = (
    "https://www.alamtri.com/files/news/berkas_eng/2309/"
    "Prospektus%20PUPS%20Alamtri.pdf"
)
ADRO_EGMS_MINUTES_URL = (
    "https://www.alamtri.com/files/news/berkas_eng/2307/"
    "ADRO-Ringkasan%20Risalah%20RUPSLB%20181124-English.pdf"
)


@dataclass(frozen=True)
class AdroEntitlementEvidence:
    prospectus_sha256: str
    egms_minutes_sha256: str
    transition_date: pd.Timestamp = ADRO_TRANSITION_DATE
    semantic: str = "REGULAR_MARKET_EX_DATE_BY_EXACT_DIVIDEND_ENTITLEMENT_IDENTITY"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _pdf_text(payload: bytes) -> str:
    if not payload:
        raise RuntimeError("ADRO_OFFICIAL_PDF_EMPTY")
    reader = PdfReader(BytesIO(payload))
    return " ".join((page.extract_text() or "") for page in reader.pages)


def _norm(text: str) -> str:
    """Normalize PDF extraction artifacts without changing semantic content."""

    value = str(text)
    for char in ("\u00a0", "\u00ad", "\u200b", "\ufeff"):
        value = value.replace(char, " ")
    value = value.replace("\x02", " ")
    value = " ".join(value.split()).casefold()
    # pypdf can detach ordinal suffixes in tables: ``29 th`` -> ``29th``.
    value = re.sub(r"\b(\d+)\s+(st|nd|rd|th)\b", r"\1\2", value)
    return value


def _verify_adro_normalized_texts(prospectus: str, egms: str) -> str:
    """Verify the same entitlement set without depending on one boxed PDF sentence.

    AlamTri's first prospectus page visibly states that PUPS participants are
    shareholders entitled to the 2024-11-18 EGMS dividend. Some pypdf builds do
    not extract that boxed all-caps line. The machine-verifiable fallback below
    therefore requires the same official prospectus to state the PUPS record set
    (DPS on 2024-11-29) and exact 4389:1000 right ratio, while the official EGMS
    minutes must independently state that 2024-11-29 is the dividend-entitlement
    record date and explicitly give the Regular/Negotiated ex-dividend date.

    This is cross-document set identity, not ``record_date - 1`` inference.
    """

    prospectus_core = (
        "penawaran umum oleh pemegang saham",
        "pt adaro andalan indonesia tbk",
        "daftar pemegang saham",
        "29 november 2024",
        "setiap pemegang saham yang memiliki 4.389",
        "1.000",
        "hak membeli saham",
        "tanggal distribusi hak membeli saham",
        "2 desember 2024",
    )
    missing_core = [token for token in prospectus_core if token not in prospectus]
    if missing_core:
        raise RuntimeError(
            f"ADRO_PUPS_PROSPECTUS_RECORD_SET_IDENTITY_MISSING:{missing_core}"
        )

    direct_clause_parts = (
        "pihak yang dapat berpartisipasi dalam pups ini",
        "memperoleh dividen berdasarkan keputusan",
        "18 november 2024",
    )
    direct_clause_visible = all(token in prospectus for token in direct_clause_parts)

    egms_required = (
        "distribution schedule of the additional final cash dividend",
        "the date for recording the shareholders who are entitled to the additional final cash dividend",
        "november 29th, 2024",
        "regular and negotiated market",
        "cum dividend",
        "ex dividend",
        "november 26th, 2024",
        "november 28th, 2024",
    )
    missing_egms = [token for token in egms_required if token not in egms]
    if missing_egms:
        raise RuntimeError(f"ADRO_EGMS_EX_DIVIDEND_SCHEDULE_MISSING:{missing_egms}")

    return (
        "DIRECT_PROSPECTUS_DIVIDEND_ENTITLEMENT_CLAUSE"
        if direct_clause_visible
        else "EXACT_2024-11-29_SHAREHOLDER_RECORD_SET_IDENTITY"
    )


def verify_adro_official_documents(
    prospectus_payload: bytes,
    egms_minutes_payload: bytes,
) -> AdroEntitlementEvidence:
    """Require exact cross-document identity; never derive from record date alone."""

    prospectus = _norm(_pdf_text(prospectus_payload))
    egms = _norm(_pdf_text(egms_minutes_payload))
    _verify_adro_normalized_texts(prospectus, egms)

    return AdroEntitlementEvidence(
        prospectus_sha256=sha256_bytes(prospectus_payload),
        egms_minutes_sha256=sha256_bytes(egms_minutes_payload),
    )


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def is_exact_adro_pups_row(
    row: Mapping[str, Any],
    *,
    event_id: str,
) -> bool:
    """Bind the cross-document evidence to one immutable KSEI event only."""

    return bool(
        event_id == ADRO_EVENT_ID
        and _text(row.get("ticker")).upper().replace(".JK", "") == "ADRO"
        and _text(row.get("event_family_source")).casefold() == "right distribution"
        and _text(row.get("status")).casefold() == "active"
        and not _text(row.get("cum_date"))
        and _text(row.get("record_date")) == ADRO_RECORD_DATE
        and _text(row.get("distribution_date")) == ADRO_DISTRIBUTION_DATE
        and _text(row.get("ratio_left_value")) == ADRO_RATIO_LEFT
        and _text(row.get("ratio_left_security")).upper() == ADRO_RATIO_LEFT_SECURITY
        and _text(row.get("ratio_right_value")) == ADRO_RATIO_RIGHT
        and _text(row.get("ratio_right_security")).upper() == ADRO_RATIO_RIGHT_SECURITY
    )


def apply_adro_entitlement_evidence(
    row: Mapping[str, Any],
    *,
    base_event: EventSemantic,
    evidence: AdroEntitlementEvidence,
) -> EventSemantic:
    """Promote only the exact frozen ADRO PUPS event to a proven transition."""

    if not is_exact_adro_pups_row(row, event_id=base_event.event_id):
        return base_event
    if evidence.transition_date != ADRO_TRANSITION_DATE:
        raise RuntimeError("ADRO_ENTITLEMENT_TRANSITION_DATE_CHANGED")
    return EventSemantic(
        event_id=base_event.event_id,
        ticker="ADRO",
        source_type=base_event.source_type,
        family="RIGHT_DISTRIBUTION_AAI_PUPS",
        semantic_class="EXACT_TRANSITION",
        transition_date=ADRO_TRANSITION_DATE,
        transition_source="OFFICIAL_ISSUER_CROSS_DOCUMENT_ENTITLEMENT_EX_DATE",
        reason=(
            "PUPS_PARTICIPANT_SET_MATCHES_2024_EGMS_DIVIDEND_ENTITLEMENT;"
            "OFFICIAL_REGULAR_AND_NEGOTIATED_MARKET_EX_DIVIDEND_2024-11-28"
        ),
        source_dates=source_dates(row),
    )
