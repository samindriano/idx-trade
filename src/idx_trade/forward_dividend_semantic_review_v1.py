from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from typing import Sequence
import unicodedata


class DividendSemanticReviewError(RuntimeError):
    pass


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
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

_MONTH_TOKEN = "|".join(
    sorted(_MONTHS, key=len, reverse=True)
)

_INDO_DATE_RE = re.compile(
    rf"\b(?P<day>\d{{1,2}})\s+"
    rf"(?P<month>{_MONTH_TOKEN})\s+"
    rf"(?P<year>20\d{{2}})\b",
    flags=re.IGNORECASE,
)

_EN_DATE_RE = re.compile(
    rf"\b(?P<month>{_MONTH_TOKEN})\s+"
    rf"(?P<day>\d{{1,2}}),?\s+"
    rf"(?P<year>20\d{{2}})\b",
    flags=re.IGNORECASE,
)

_NON_CASH_TERMS = (
    "dividen saham",
    "stock dividend",
    "bonus share",
    "bonus shares",
)

_SUBJECT_TERMS = (
    "dividen tunai",
    "dividen interim",
    "interim dividend",
    "cash dividend",
)


@dataclass(frozen=True)
class CashDividendSemanticExtraction:
    ticker: str
    gross_dividend_per_share_idr: str
    cum_regular_negotiated: str
    ex_regular_negotiated: str
    record_date: str
    payment_date: str
    ticker_match: bool
    dividend_subject_match: bool
    contributing_document_count: int


def normalize_text(text: str) -> str:
    value = unicodedata.normalize("NFKC", str(text))
    value = value.replace("\u00a0", " ")
    value = value.replace("?", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip().lower()


def _parse_number(token: str) -> Decimal:
    value = token.strip().replace(" ", "")

    if not value:
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_AMOUNT_EMPTY"
        )

    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        left, right = value.rsplit(",", 1)
        if len(right) <= 2:
            value = left.replace(",", "") + "." + right
        else:
            value = value.replace(",", "")
    elif "." in value:
        left, right = value.rsplit(".", 1)
        if len(right) <= 2:
            value = left.replace(".", "") + "." + right
        else:
            value = value.replace(".", "")

    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_AMOUNT_INVALID"
        ) from exc

    if result <= 0:
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_AMOUNT_NONPOSITIVE"
        )

    return result


def _canonical_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(int(normalized))
    return format(normalized, "f")


def _dates_with_positions(
    text: str,
) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []

    for pattern in (_INDO_DATE_RE, _EN_DATE_RE):
        for match in pattern.finditer(text):
            month = _MONTHS[match.group("month").lower()]
            parsed = date(
                int(match.group("year")),
                month,
                int(match.group("day")),
            ).isoformat()
            found.append((match.start(), parsed))

    found.sort(key=lambda row: row[0])

    deduped: list[tuple[int, str]] = []
    seen_positions: set[tuple[int, str]] = set()

    for row in found:
        if row not in seen_positions:
            seen_positions.add(row)
            deduped.append(row)

    return deduped


def _dates(text: str) -> list[str]:
    return [value for _, value in _dates_with_positions(text)]


def _amount_candidates(text: str) -> set[str]:
    patterns = (
        re.compile(
            r"(?:dividen|dividend).{0,180}?"
            r"(?:rp\.?|idr)\s*"
            r"(?P<amount>[0-9][0-9\.,]*)\s*"
            r"(?:per\s+(?:lembar\s+)?saham|"
            r"per\s+share|/\s*(?:lembar\s+)?saham)",
            flags=re.IGNORECASE,
        ),
    )

    result: set[str] = set()

    for pattern in patterns:
        for match in pattern.finditer(text):
            amount = _parse_number(match.group("amount"))
            result.add(_canonical_decimal(amount))

    return result


def _first_date_between(
    text: str,
    start_pattern: str,
    end_pattern: str,
    *,
    require_market_marker: bool = False,
) -> str | None:
    match = re.search(
        rf"{start_pattern}(?P<body>.{{0,600}}?)(?={end_pattern})",
        text,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    body = match.group("body")

    if require_market_marker:
        has_regular = (
            "pasar reguler" in body
            or "regular market" in body
            or "regular markets" in body
        )
        has_negotiated = (
            "pasar negosiasi" in body
            or "negotiated market" in body
            or "negotiated markets" in body
        )

        if not (has_regular and has_negotiated):
            return None

    values = _dates(body)
    return values[0] if values else None


def _first_date_after_label(
    text: str,
    patterns: Sequence[str],
) -> str | None:
    for pattern in patterns:
        match = re.search(
            rf"{pattern}(?P<body>.{{0,220}})",
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        values = _dates(match.group("body"))

        if values:
            return values[0]

    return None


def _schedule_candidate(
    text: str,
) -> tuple[str, str, str, str] | None:
    cum = _first_date_between(
        text,
        r"cum\s+dividen(?:ds)?",
        r"(?:ex\s+dividen(?:ds)?)",
        require_market_marker=True,
    )

    ex = _first_date_between(
        text,
        r"ex\s+dividen(?:ds)?",
        (
            r"(?:record\s+date|"
            r"tanggal\s+daftar\s+pemegang\s+saham)"
        ),
        require_market_marker=True,
    )

    record = _first_date_after_label(
        text,
        (
            r"record\s+date",
            r"tanggal\s+daftar\s+pemegang\s+saham",
        ),
    )

    payment = _first_date_after_label(
        text,
        (
            r"tanggal\s+pembayaran\s+dividen(?:\s+interim)?",
            r"payment\s+date\s+of\s+(?:interim\s+)?dividends?",
            r"payment\s+date",
        ),
    )

    if None in (cum, ex, record, payment):
        return None

    assert cum is not None
    assert ex is not None
    assert record is not None
    assert payment is not None

    if not (cum < ex <= record <= payment):
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_DATE_ORDER_INVALID"
        )

    return cum, ex, record, payment


def analyze_cash_dividend_documents(
    texts: Sequence[str],
    *,
    ticker: str,
) -> CashDividendSemanticExtraction:
    symbol = str(ticker or "").strip().upper()

    if not re.fullmatch(r"[A-Z0-9]{1,12}", symbol):
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_TICKER_INVALID"
        )

    if not texts:
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_DOCUMENTS_EMPTY"
        )

    normalized = [normalize_text(text) for text in texts]
    combined = " ".join(normalized)

    if any(term in combined for term in _NON_CASH_TERMS):
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_NON_CASH_TERM_PRESENT"
        )

    dividend_subject = any(
        term in combined
        for term in _SUBJECT_TERMS
    )

    if not dividend_subject:
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_CASH_SUBJECT_NOT_FOUND"
        )

    ticker_match = bool(
        re.search(
            rf"\b{re.escape(symbol.lower())}\b",
            combined,
        )
    )

    if not ticker_match:
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_TICKER_NOT_FOUND"
        )

    amounts: set[str] = set()
    schedules: set[tuple[str, str, str, str]] = set()
    contributing_documents = 0

    for text in normalized:
        doc_amounts = _amount_candidates(text)
        schedule = _schedule_candidate(text)

        if doc_amounts:
            amounts.update(doc_amounts)

        if schedule is not None:
            schedules.add(schedule)

        if doc_amounts and schedule is not None:
            contributing_documents += 1

    if len(amounts) != 1:
        raise DividendSemanticReviewError(
            f"DIVIDEND_SEMANTIC_AMOUNT_NOT_UNIQUE:{sorted(amounts)}"
        )

    if len(schedules) != 1:
        raise DividendSemanticReviewError(
            f"DIVIDEND_SEMANTIC_SCHEDULE_NOT_UNIQUE:{sorted(schedules)}"
        )

    if contributing_documents < 1:
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_NO_COMPLETE_SOURCE_DOCUMENT"
        )

    amount = next(iter(amounts))
    cum, ex, record, payment = next(iter(schedules))

    return CashDividendSemanticExtraction(
        ticker=symbol,
        gross_dividend_per_share_idr=amount,
        cum_regular_negotiated=cum,
        ex_regular_negotiated=ex,
        record_date=record,
        payment_date=payment,
        ticker_match=True,
        dividend_subject_match=True,
        contributing_document_count=contributing_documents,
    )
