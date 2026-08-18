"""Exact-event offline semantics for the frozen 2024 ADRO PUPS right.

This module is deliberately non-generic. It validates one frozen KSEI event
only. The event distributes ADRO-H, a separate purchase-right security, under a
Penawaran Umum oleh Pemegang Saham (PUPS) schedule. It is not treated as a
regular ADRO HMETD/right issue and is never generalized to other rights events.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence

from idx_trade.v4_ca_event_windows import event_identity


ADRO_EVENT_ID = "41c1e8493213d0151799837330c0dc7d8fea633d458c03e40b61ea0247bb9e58"
ADRO_REFERENCES = frozenset({"KSEI-27597/JKU/1124", "KSEI-28171/JKU/1224"})
ADRO_SOURCE_DATES = frozenset({"2024-11-29", "2024-12-02"})
PUPS_PHRASE = "penawaran umum oleh pemegang saham"
RIGHT_SECURITY = "ADRO-H"


@dataclass(frozen=True)
class AdroPupsValidation:
    valid: bool
    diagnostics: tuple[str, ...]


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def validate_history_row(row: Mapping[str, Any]) -> AdroPupsValidation:
    diagnostics: list[str] = []
    if event_identity(row) != ADRO_EVENT_ID:
        diagnostics.append("EVENT_ID_MISMATCH")
    if _text(row.get("ticker")).upper() != "ADRO":
        diagnostics.append("TICKER_MISMATCH")
    if _text(row.get("event_family_source")).casefold() != "right distribution":
        diagnostics.append("SOURCE_TYPE_MISMATCH")
    if _text(row.get("status")).casefold() != "active":
        diagnostics.append("STATUS_NOT_ACTIVE")
    if _text(row.get("ratio_parse_status")) != "PARSED_SOURCE_TEXT_ONLY":
        diagnostics.append("RATIO_NOT_PARSED")
    if _text(row.get("ratio_left_value")) != "4389":
        diagnostics.append("RATIO_LEFT_VALUE_MISMATCH")
    if _text(row.get("ratio_left_security")).upper() != "ADRO":
        diagnostics.append("RATIO_LEFT_SECURITY_MISMATCH")
    if _text(row.get("ratio_right_value")) != "1000":
        diagnostics.append("RATIO_RIGHT_VALUE_MISMATCH")
    if _text(row.get("ratio_right_security")).upper() != RIGHT_SECURITY:
        diagnostics.append("RATIO_RIGHT_SECURITY_MISMATCH")
    if _text(row.get("cum_date")) not in {"", "None", "nan"}:
        diagnostics.append("UNEXPECTED_STATIC_CUM_DATE")
    dates = {
        _text(row.get("record_date")),
        _text(row.get("distribution_date")),
    } - {""}
    if dates != ADRO_SOURCE_DATES:
        diagnostics.append("SOURCE_DATE_SET_MISMATCH")
    if not _text(row.get("source_url")) or not _text(row.get("source_sha256")):
        diagnostics.append("HISTORY_PROVENANCE_MISSING")
    return AdroPupsValidation(not diagnostics, tuple(diagnostics))


def validate_documents(
    parse_rows: Sequence[Mapping[str, Any]],
    text_by_reference: Mapping[str, str],
) -> AdroPupsValidation:
    diagnostics: list[str] = []
    refs = {_text(row.get("reference") or row.get("ksei_reference")) for row in parse_rows}
    if len(parse_rows) != 2 or refs != ADRO_REFERENCES:
        diagnostics.append("EXACT_TWO_DOCUMENT_REFERENCE_SET_REQUIRED")

    for row in parse_rows:
        if _text(row.get("ticker")).upper() != "ADRO":
            diagnostics.append("DOCUMENT_TICKER_MISMATCH")
        if not _text(row.get("source_sha256")):
            diagnostics.append("DOCUMENT_SHA_MISSING")
        if not _text(row.get("source_url") or row.get("document_url")):
            diagnostics.append("DOCUMENT_URL_MISSING")

    combined_subject = " ".join(_text(row.get("subject")) for row in parse_rows).casefold()
    if PUPS_PHRASE not in combined_subject:
        diagnostics.append("PUPS_SUBJECT_SEMANTIC_MISSING")

    combined_text = "\n".join(text_by_reference.get(ref, "") for ref in sorted(ADRO_REFERENCES))
    combined_fold = _text(combined_text).casefold()
    if PUPS_PHRASE not in combined_fold:
        diagnostics.append("PUPS_DOCUMENT_SEMANTIC_MISSING")
    if RIGHT_SECURITY.casefold() not in combined_fold:
        diagnostics.append("ADRO_H_SECURITY_MISSING")

    # Explicitly reject evidence that instead describes an ADRO share-basis
    # rebase. Generic mentions in legal boilerplate are not enough; these are
    # the exact mechanical schedule anchors used elsewhere in this project.
    forbidden = (
        r"mulai\s+perdagangan\s+saham\s+dengan\s+nilai\s+nominal\s+baru",
        r"pemecahan\s+saham",
        r"stock\s+split",
        r"reverse\s+(?:stock|split)",
    )
    for pattern in forbidden:
        if re.search(pattern, combined_text, flags=re.IGNORECASE):
            diagnostics.append("ADRO_SHARE_BASIS_REBASE_SEMANTIC_PRESENT")
            break

    return AdroPupsValidation(not diagnostics, tuple(dict.fromkeys(diagnostics)))
