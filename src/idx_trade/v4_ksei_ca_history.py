"""Fail-closed public-KSEI corporate-action history parsing for V4.

This module is intentionally outcome-blind.  It treats the static Corporate
Action table on a KSEI registered-security page as an issuer-level history
ledger only when page identity and table structure are exact.  It does not
infer an effective market date from Cum/Record/Distribution dates.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from lxml import html


CA_HEADERS = (
    "Type of CA",
    "Ratio",
    "Cum Date",
    "Record Date",
    "Distribution Date",
    "Status",
)

NON_MECHANICAL_FAMILIES = {
    "CASH_DIVIDEND",
    "PROXY_VOTING",
}

MECHANICAL_FAMILIES = {
    "RIGHTS_HMETD",
    "STOCK_DIVIDEND",
    "BONUS_SHARES",
    "MANDATORY_CONVERSION",
    "STOCK_SPLIT",
    "REVERSE_SPLIT",
    "MERGER_OR_RESTRUCTURING",
}


class KseiHistoryParseError(RuntimeError):
    """Raised when a KSEI security page cannot certify history coverage."""


@dataclass(frozen=True)
class ParsedKseiHistory:
    ticker: str
    source_url: str
    source_sha256: str
    coverage_certified: bool
    rows: tuple[dict[str, Any], ...]


def _compact_text(value: str) -> str:
    return " ".join(str(value).split())


def _date_token(text: str) -> str | None:
    """Parse KSEI's hidden YYYYMMDD token adjacent to visible localized dates."""

    match = re.search(r"(?<!\d)(20\d{6})", str(text))
    if not match:
        return None
    raw = match.group(1)
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"


def _cell_date(cell: Any) -> str | None:
    return _date_token(_compact_text(cell.text_content()))


def _ratio_fields(text: str) -> dict[str, Any]:
    clean = _compact_text(text)
    match = re.search(
        r"\(\s*([0-9.]+)\s+([^:()]+?)\s*:\s*([0-9.]+)\s+([^()]+?)\s*\)",
        clean,
    )
    if not match:
        return {
            "ratio_raw": clean,
            "ratio_parse_status": "UNRESOLVED_SOURCE_TEXT",
            "ratio_left_value": None,
            "ratio_left_security": None,
            "ratio_right_value": None,
            "ratio_right_security": None,
        }
    return {
        "ratio_raw": clean,
        "ratio_parse_status": "PARSED_SOURCE_TEXT_ONLY",
        "ratio_left_value": match.group(1),
        "ratio_left_security": match.group(2).strip(),
        "ratio_right_value": match.group(3),
        "ratio_right_security": match.group(4).strip(),
    }


def normalize_ca_family(source_type: str) -> str:
    """Map source-native KSEI CA names without inventing event dates."""

    key = re.sub(r"\s+", " ", str(source_type).strip()).casefold()
    mapping = {
        "cash dividend": "CASH_DIVIDEND",
        "proxy voting": "PROXY_VOTING",
        "right distribution": "RIGHTS_HMETD",
        "rights distribution": "RIGHTS_HMETD",
        "stock dividend": "STOCK_DIVIDEND",
        "share bonus": "BONUS_SHARES",
        "bonus shares": "BONUS_SHARES",
        "bonus share": "BONUS_SHARES",
        "bonus distribution": "BONUS_SHARES",
        "mandatory conversion": "MANDATORY_CONVERSION",
        "voluntary conversion": "MANDATORY_CONVERSION",
        "stock split": "STOCK_SPLIT",
        "reverse stock": "REVERSE_SPLIT",
        "reverse stock split": "REVERSE_SPLIT",
        "reverse split": "REVERSE_SPLIT",
        "merger": "MERGER_OR_RESTRUCTURING",
        "capital restructuring": "MERGER_OR_RESTRUCTURING",
        "capital reduction": "MERGER_OR_RESTRUCTURING",
    }
    return mapping.get(key, "UNKNOWN")


def _extract_short_code(document: Any) -> str | None:
    # The registered-security detail renders a literal "Short Code" label.
    # DOM wrappers have changed historically, so identity extraction uses the
    # flattened page text but still requires the exact four-character code.
    text = _compact_text(document.text_content())
    match = re.search(r"\bShort Code\s+([A-Z0-9]{4})\b", text, flags=re.IGNORECASE)
    return match.group(1).upper() if match else None


def _find_ca_table(document: Any) -> Any:
    matches: list[Any] = []
    for table in document.xpath("//table"):
        headers = tuple(
            _compact_text(cell.text_content())
            for cell in table.xpath(".//thead//th")[:6]
        )
        if headers == CA_HEADERS:
            matches.append(table)
    if len(matches) != 1:
        raise KseiHistoryParseError(
            f"expected exactly one Corporate Action table, found {len(matches)}"
        )
    return matches[0]


def parse_ksei_security_history(
    payload: bytes,
    *,
    expected_ticker: str,
    source_url: str,
    source_sha256: str,
) -> ParsedKseiHistory:
    """Parse and certify one complete static KSEI registered-security CA table.

    Coverage certification means only that the requested ticker identity and
    the authoritative visible Corporate Action table were captured and parsed
    structurally.  It does not mean every event is mechanically harmless.
    Unknown active CA types remain explicit and are quarantined downstream.
    """

    if not payload:
        raise KseiHistoryParseError("empty KSEI response body")
    ticker = str(expected_ticker).upper().strip()
    if not re.fullmatch(r"[A-Z0-9]{4}", ticker):
        raise KseiHistoryParseError(f"invalid expected ticker: {expected_ticker!r}")

    try:
        document = html.fromstring(payload)
    except Exception as exc:  # pragma: no cover - parser library detail
        raise KseiHistoryParseError("invalid KSEI HTML") from exc

    short_code = _extract_short_code(document)
    if short_code != ticker:
        raise KseiHistoryParseError(
            f"KSEI short-code identity mismatch: expected {ticker}, got {short_code}"
        )

    table = _find_ca_table(document)
    rows: list[dict[str, Any]] = []
    for row_index, tr in enumerate(table.xpath(".//tbody/tr"), start=1):
        cells = tr.xpath("./td")
        if len(cells) != 6:
            raise KseiHistoryParseError(
                f"KSEI {ticker}: malformed Corporate Action row {row_index}"
            )
        values = [_compact_text(cell.text_content()) for cell in cells]
        source_family = values[0]
        status = values[5]
        if not source_family:
            raise KseiHistoryParseError(
                f"KSEI {ticker}: empty CA type at row {row_index}"
            )
        if not status:
            raise KseiHistoryParseError(
                f"KSEI {ticker}: empty CA status at row {row_index}"
            )
        ratio = _ratio_fields(values[1])
        rows.append(
            {
                "ticker": ticker,
                "row_index": row_index,
                "event_family_source": source_family,
                "event_family": normalize_ca_family(source_family),
                "cum_date": _cell_date(cells[2]),
                "record_date": _cell_date(cells[3]),
                "distribution_date": _cell_date(cells[4]),
                "status": status,
                "source_url": source_url,
                "source_sha256": source_sha256,
                **ratio,
            }
        )

    return ParsedKseiHistory(
        ticker=ticker,
        source_url=source_url,
        source_sha256=source_sha256,
        coverage_certified=True,
        rows=tuple(rows),
    )


def is_active_status(value: str) -> bool:
    return str(value).strip().casefold() == "active"


def is_cancelled_status(value: str) -> bool:
    return str(value).strip().casefold() == "cancelled"


def row_dates(row: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        str(value)
        for value in (
            row.get("cum_date"),
            row.get("record_date"),
            row.get("distribution_date"),
        )
        if value
    )
