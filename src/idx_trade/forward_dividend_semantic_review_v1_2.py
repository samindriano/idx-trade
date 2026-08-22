from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re
from typing import Sequence

from .forward_dividend_semantic_review_v1 import (
    CashDividendSemanticExtraction,
    DividendSemanticReviewError,
    _schedule_candidate,
    normalize_text,
)


_SUBJECT_TERMS = (
    "dividen tunai",
    "dividen interim",
    "interim dividend",
    "cash dividend",
)

_NON_CASH_TERMS = (
    "dividen saham",
    "stock dividend",
    "bonus share",
    "bonus shares",
)

_LEGAL_REFERENCE_MARKERS = (
    "peraturan",
    "regulation",
    "surat keputusan",
    "decree",
    "ketentuan pelaksanaan",
    "implementation provisions",
    "perubahan ketentuan",
    "changes to implementation",
)

_AMOUNT = r"(?P<amount>[0-9]+(?:[.,][0-9]+)*)"

_PER_SHARE_SUFFIX = (
    r"\s*(?:,\s*-\s*|-\s*)?"
    r"(?:\s*\([^)]{0,180}\))?"
    r"\s*(?:"
    r"per\s+(?:lembar\s+)?saham"
    r"|per\s+share"
    r")"
)


def _parse_per_share_number(
    token: str,
) -> Decimal:
    value = str(token).strip()

    if not value:
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_V1_2_AMOUNT_EMPTY"
        )

    value = value.rstrip(".,")
    value = value.replace(" ", "")

    if "," in value and "." in value:
        # Last separator is decimal; the other one is grouping.
        if value.rfind(",") > value.rfind("."):
            value = (
                value.replace(".", "")
                .replace(",", ".")
            )
        else:
            value = value.replace(",", "")

    elif "," in value:
        parts = value.split(",")

        if (
            len(parts) > 2
            and all(len(x) == 3 for x in parts[1:])
        ):
            value = "".join(parts)
        else:
            left, right = value.rsplit(",", 1)

            if len(right) == 3:
                # Conventional thousands grouping.
                value = left.replace(",", "") + right
            else:
                # IDX can publish high-precision dividend/share,
                # e.g. TLKM 223,1658777.
                value = (
                    left.replace(",", "")
                    + "."
                    + right
                )

    elif "." in value:
        parts = value.split(".")

        if (
            len(parts) > 2
            and all(len(x) == 3 for x in parts[1:])
        ):
            value = "".join(parts)
        else:
            left, right = value.rsplit(".", 1)

            if len(right) == 3:
                value = left.replace(".", "") + right
            else:
                value = (
                    left.replace(".", "")
                    + "."
                    + right
                )

    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_V1_2_AMOUNT_INVALID"
        ) from exc

    if result <= 0:
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_V1_2_AMOUNT_NONPOSITIVE"
        )

    return result


def _canonical_decimal(
    value: Decimal,
) -> str:
    normalized = value.normalize()

    if normalized == normalized.to_integral():
        return str(int(normalized))

    return format(normalized, "f")


def _matches(
    text: str,
    patterns: Sequence[re.Pattern[str]],
) -> set[str]:
    result: set[str] = set()

    for pattern in patterns:
        for match in pattern.finditer(text):
            amount = _parse_per_share_number(
                match.group("amount")
            )
            result.add(
                _canonical_decimal(amount)
            )

    return result


_REMAINING_PATTERNS = (
    re.compile(
        r"(?:sisa|remaining)"
        r".{0,160}?"
        r"(?:dividen|dividend)"
        r".{0,260}?"
        r"(?:rp\.?|idr)\s*"
        + _AMOUNT
        + _PER_SHARE_SUFFIX,
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"(?:sisa\s+jumlah\s+dividen|"
        r"remaining\s+cash\s+dividend)"
        r".{0,360}?"
        r"(?:rp\.?|idr)\s*"
        + _AMOUNT
        + _PER_SHARE_SUFFIX,
        flags=re.IGNORECASE,
    ),
)


_FIELD_PATTERNS = (
    re.compile(
        r"(?:dividen|dividend)"
        r"\s+per\s+(?:saham|share)"
        r"(?:\s*\([^)]{0,180}\))?"
        r".{0,100}?"
        r"(?:idr|rp\.?)\s*"
        + _AMOUNT,
        flags=re.IGNORECASE,
    ),
)


_GENERIC_PATTERNS = (
    re.compile(
        r"(?:dividen|dividend)"
        r".{0,280}?"
        r"(?:rp\.?|idr)\s*"
        + _AMOUNT
        + _PER_SHARE_SUFFIX,
        flags=re.IGNORECASE,
    ),
)


def _material_non_cash_subject(
    text: str,
) -> bool:
    for term in _NON_CASH_TERMS:
        for match in re.finditer(
            re.escape(term),
            text,
            flags=re.IGNORECASE,
        ):
            start = max(0, match.start() - 240)
            end = min(
                len(text),
                match.end() + 240,
            )

            context = text[start:end]

            if any(
                marker in context
                for marker in _LEGAL_REFERENCE_MARKERS
            ):
                continue

            return True

    return False


def _amount_mode_and_values(
    texts: Sequence[str],
) -> tuple[str, set[str]]:
    remaining: set[str] = set()

    for text in texts:
        remaining.update(
            _matches(
                text,
                _REMAINING_PATTERNS,
            )
        )

    if remaining:
        return (
            "REMAINING_PAYABLE",
            {
                _r2_amount_text(value)
                for value in remaining
            },
        )

    field: set[str] = set()

    for text in texts:
        field.update(
            _matches(
                text,
                _FIELD_PATTERNS,
            )
        )

    if field:
        return "IDX_PER_SHARE_FIELD", field

    generic: set[str] = set()

    for text in texts:
        generic.update(
            _matches(
                text,
                _GENERIC_PATTERNS,
            )
        )

    return "GENERIC_PER_SHARE", generic


def extract_cash_dividend_schedule_v1_2(
    texts: Sequence[str],
) -> tuple[str, str, str, str]:
    if not texts:
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_V1_2_DOCUMENTS_EMPTY"
        )

    normalized = [
        normalize_text(text)
        for text in texts
    ]

    schedules = {
        schedule
        for text in normalized
        if (
            schedule := _schedule_candidate(
                text
            )
        )
        is not None
    }

    if len(schedules) != 1:
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_V1_2_"
            f"SCHEDULE_NOT_UNIQUE:{sorted(schedules)}"
        )

    return next(iter(schedules))


def analyze_cash_dividend_documents_v1_2(
    texts: Sequence[str],
    *,
    ticker: str,
) -> CashDividendSemanticExtraction:
    symbol = str(
        ticker or ""
    ).strip().upper()

    if not re.fullmatch(
        r"[A-Z0-9]{1,12}",
        symbol,
    ):
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_V1_2_TICKER_INVALID"
        )

    if not texts:
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_V1_2_DOCUMENTS_EMPTY"
        )

    normalized = [
        normalize_text(text)
        for text in texts
    ]

    combined = " ".join(normalized)

    if any(
        _material_non_cash_subject(text)
        for text in normalized
    ):
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_V1_2_"
            "MATERIAL_NON_CASH_SUBJECT_PRESENT"
        )

    if not any(
        term in combined
        for term in _SUBJECT_TERMS
    ):
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_V1_2_"
            "CASH_SUBJECT_NOT_FOUND"
        )

    if not re.search(
        rf"\b{re.escape(symbol.lower())}\b",
        combined,
    ):
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_V1_2_TICKER_NOT_FOUND"
        )

    mode, amounts = _amount_mode_and_values(
        normalized
    )

    if len(amounts) != 1:
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_V1_2_"
            f"AMOUNT_NOT_UNIQUE:{mode}:{sorted(amounts)}"
        )

    amount = next(iter(amounts))

    schedule = (
        extract_cash_dividend_schedule_v1_2(
            normalized
        )
    )

    # Use the same R2 amount and schedule authorities that selected the
    # canonical values above. The legacy matcher silently returned zero for
    # valid structured/flattened IDX forms, making the review look
    # uncertified even when the evidence was independently complete.
    contributing = sum(
        _r2_document_contributes(
            text,
            mode=mode,
            amount=amount,
            schedule=schedule,
        )
        for text in normalized
    )

    if contributing < 1:
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_V1_2_NO_COMPLETE_CONTRIBUTING_DOCUMENT"
        )

    cum, ex, record, payment = schedule

    return CashDividendSemanticExtraction(
        ticker=symbol,
        gross_dividend_per_share_idr=amount,
        cum_regular_negotiated=cum,
        ex_regular_negotiated=ex,
        record_date=record,
        payment_date=payment,
        ticker_match=True,
        dividend_subject_match=True,
        contributing_document_count=contributing,
    )

# --- STEP 4D2B R2 REAL-EVIDENCE SEMANTIC ADJUDICATION ---
from datetime import date  # R2 schedule parsing


# --- STEP 4D2B R2 REAL-EVIDENCE SEMANTIC ADJUDICATION ---
#
# Rationale:
# - PDF table extraction can place aggregate dividend value beside a
#   "dividend per share" label before the actual DPS cell.
# - A DPS amount therefore needs local unit evidence, or a bounded
#   structured-field interpretation with a per-share magnitude guard.
# - IDX schedule forms often extract labels first and six values later.
#   The economic regular-market schedule can be reconstructed from the
#   official ordered form fields without using issuer-specific rules.
#
# This remains V1.2 only. Historical V1/V1.1 behavior is untouched.


_AMOUNT_TOKEN_R2 = r"[0-9][0-9.,]*"

_DIRECT_PER_SHARE_R2 = re.compile(
    rf"""
    (?:
        rp
        |
        idr
    )
    \s*
    (?P<amount>{_AMOUNT_TOKEN_R2})
    \s*
    -?
    \s*
    (?:
        \(
            [^)]{{0,220}}
        \)
        \s*
    )?
    per
    \s+
    (?:
        lembar
        \s+
    )?
    (?:
        saham
        |
        share
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

_REMAINING_MARKER_R2 = re.compile(
    r"""
    (?:
        remaining
        (?:
            \s+cash
        )?
        \s+dividend
        s?
        |
        sisa
        (?:
            \s+jumlah
        )?
        \s+dividen
        (?:
            \s+tunai
        )?
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

_STRUCTURED_DPS_LABEL_R2 = re.compile(
    r"""
    (?:
        dividen
        \s+per
        \s+saham
        |
        dividend
        \s+per
        \s+share
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

_STRUCTURED_IDR_AFTER_R2 = re.compile(
    rf"""
    \bidr\b
    \s*
    (?P<amount>{_AMOUNT_TOKEN_R2})
    """,
    re.IGNORECASE | re.VERBOSE,
)

_STRUCTURED_IDR_BEFORE_R2 = re.compile(
    rf"""
    (?P<amount>{_AMOUNT_TOKEN_R2})
    \s*
    \bidr\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Aggregate cash payouts in IDX forms are typically billions/trillions.
# Values >= this ceiling are not defensible as cash dividend PER SHARE
# without explicit local "per share/per saham" syntax.
_STRUCTURED_DPS_MAX_IDR_R2 = Decimal("100000000")


_MONTHS_R2 = {
    # Indonesian
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

    # English
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

_MONTH_PATTERN_R2 = "|".join(
    sorted(
        (re.escape(name) for name in _MONTHS_R2),
        key=len,
        reverse=True,
    )
)

_HUMAN_DATE_R2 = re.compile(
    rf"""
    \b
    (?P<day>[0-3]?\d)
    \s+
    (?P<month>{_MONTH_PATTERN_R2})
    \s+
    (?P<year>20\d{{2}})
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _r2_parse_date_match(
    match: re.Match[str],
) -> str:
    day = int(match.group("day"))
    month_name = match.group("month").lower()
    month = _MONTHS_R2[month_name]
    year = int(match.group("year"))

    try:
        return date(
            year,
            month,
            day,
        ).isoformat()
    except ValueError as exc:
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_V1_2_DATE_INVALID"
        ) from exc


def _r2_dates(
    text: str,
) -> list[str]:
    return [
        _r2_parse_date_match(match)
        for match in _HUMAN_DATE_R2.finditer(text)
    ]


def _r2_direct_per_share_values(
    text: str,
) -> set[Decimal]:
    values: set[Decimal] = set()

    for match in _DIRECT_PER_SHARE_R2.finditer(text):
        values.add(
            _parse_per_share_number(
                match.group("amount")
            )
        )

    return values


def _r2_remaining_payable_values(
    text: str,
) -> set[Decimal]:
    values: set[Decimal] = set()

    for marker in _REMAINING_MARKER_R2.finditer(text):
        # The economic amount must appear locally AFTER the
        # "remaining/sisa" proposition. A bounded window prevents an
        # earlier total/interim amount from being reused.
        window = text[
            marker.start():
            min(
                len(text),
                marker.start() + 700,
            )
        ]

        local = _r2_direct_per_share_values(window)

        if local:
            values.update(local)

    return values


def _r2_structured_per_share_values(
    text: str,
) -> set[Decimal]:
    values: set[Decimal] = set()

    for label in _STRUCTURED_DPS_LABEL_R2.finditer(text):
        # PDF extraction of IDX forms can flatten columns:
        #
        # "Total Nilai Dividen  Dividen per saham
        #  20,633,761,718,348 IDR Tidak 137 IDR ..."
        #
        # Therefore inspect a bounded field neighbourhood and retain
        # only IDR-valued numbers that are economically plausible as
        # DPS. This is a disambiguation guard, not event authority.
        window = text[
            label.end():
            min(
                len(text),
                label.end() + 500,
            )
        ]

        candidates: set[Decimal] = set()

        for pattern in (
            _STRUCTURED_IDR_AFTER_R2,
            _STRUCTURED_IDR_BEFORE_R2,
        ):
            for match in pattern.finditer(window):
                try:
                    amount = _parse_per_share_number(
                        match.group("amount")
                    )
                except DividendSemanticReviewError:
                    continue

                if (
                    amount > 0
                    and amount < _STRUCTURED_DPS_MAX_IDR_R2
                ):
                    candidates.add(amount)

        values.update(candidates)

    return values


def _r2_amount_text(
    value: Decimal,
) -> str:
    """
    Preserve the pre-R2 V1.2 semantic contract:
    canonical dividend/share amounts leave extraction as strings.

    Examples:
      Decimal("55.00")      -> "55"
      Decimal("137")        -> "137"
      Decimal("281.00")     -> "281"
      Decimal("223.1658777")-> "223.1658777"
    """

    if not isinstance(value, Decimal):
        value = Decimal(str(value))

    if not value.is_finite() or value <= 0:
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_V1_2_AMOUNT_INVALID"
        )

    normalized = value.normalize()

    if normalized == normalized.to_integral():
        return str(int(normalized))

    return format(normalized, "f")


def _amount_mode_and_values(
    texts: Sequence[str],
) -> tuple[str, set[str]]:
    """
    R2 precedence:

    1. Explicit remaining/sisa PAYABLE DPS.
    2. Explicit local currency + amount + per-share syntax.
    3. Official IDX structured DPS field.
    4. No evidence => fail closed at caller.

    Aggregate total payout is never allowed to masquerade as DPS merely
    because a PDF table extraction placed it near a DPS label.
    """

    remaining: set[Decimal] = set()

    for text in texts:
        remaining.update(
            _r2_remaining_payable_values(text)
        )

    if remaining:
        return (
            "REMAINING_PAYABLE",
            {
                _r2_amount_text(value)
                for value in remaining
            },
        )

    direct: set[Decimal] = set()

    for text in texts:
        direct.update(
            _r2_direct_per_share_values(text)
        )

    if direct:
        return (
            "GENERIC_PER_SHARE",
            {
                _r2_amount_text(value)
                for value in direct
            },
        )

    structured: set[Decimal] = set()

    for text in texts:
        structured.update(
            _r2_structured_per_share_values(text)
        )

    if structured:
        return (
            "IDX_PER_SHARE_FIELD",
            {
                _r2_amount_text(value)
                for value in structured
            },
        )

    return "GENERIC_PER_SHARE", set()


# Preserve the original V1.2 schedule parser as first authority.
_extract_cash_dividend_schedule_v1_2_pre_r2 = (
    extract_cash_dividend_schedule_v1_2
)


def _r2_schedule_is_valid(
    schedule: tuple[str, str, str, str],
) -> bool:
    cum, ex, record, payment = schedule

    try:
        cum_d = date.fromisoformat(cum)
        ex_d = date.fromisoformat(ex)
        record_d = date.fromisoformat(record)
        payment_d = date.fromisoformat(payment)
    except ValueError:
        return False

    return (
        cum_d < ex_d
        and ex_d <= record_d
        and record_d <= payment_d
    )


def _r2_schedule_from_ordered_idx_form(
    text: str,
) -> tuple[str, str, str, str] | None:
    lowered = text.lower()

    # IDX structured forms present six semantic fields in order:
    #
    # record date
    # cum regular/negotiation
    # ex regular/negotiation
    # cum cash
    # ex cash
    # payment
    #
    # PDF extraction commonly emits ALL labels first, then all values.
    record_markers = (
        "tanggal daftar pemegang saham",
        "record date to determine",
    )

    payment_markers = (
        "tanggal pembayaran dividen",
        "dividend payment date",
    )

    start = None

    for marker in record_markers:
        position = lowered.find(marker)

        if position >= 0 and (
            start is None
            or position < start
        ):
            start = position

    if start is None:
        return None

    payment_label_end = None

    for marker in payment_markers:
        position = lowered.find(
            marker,
            start,
        )

        if position >= 0:
            candidate_end = position + len(marker)

            if (
                payment_label_end is None
                or candidate_end < payment_label_end
            ):
                payment_label_end = candidate_end

    if payment_label_end is None:
        return None

    # Six actual values should follow the final header label.
    value_window = text[
        payment_label_end:
        min(
            len(text),
            payment_label_end + 1800,
        )
    ]

    dates = _r2_dates(value_window)

    if len(dates) < 6:
        return None

    record = dates[0]
    cum_regular = dates[1]
    ex_regular = dates[2]
    # dates[3] = cum cash
    # dates[4] = ex cash
    payment = dates[5]

    schedule = (
        cum_regular,
        ex_regular,
        record,
        payment,
    )

    if not _r2_schedule_is_valid(schedule):
        return None

    return schedule


def _r2_schedule_from_explicit_labels(
    text: str,
) -> tuple[str, str, str, str] | None:
    lowered = text.lower()

    date_atom = (
        rf"(?P<day>[0-3]?\d)\s+"
        rf"(?P<month>{_MONTH_PATTERN_R2})\s+"
        rf"(?P<year>20\d{{2}})"
    )

    def one(
        patterns: Sequence[str],
    ) -> str | None:
        values: set[str] = set()

        for prefix in patterns:
            regex = re.compile(
                prefix
                + r"\s*(?:=|:)?\s*"
                + date_atom,
                re.IGNORECASE | re.VERBOSE,
            )

            for match in regex.finditer(lowered):
                values.add(
                    _r2_parse_date_match(match)
                )

        if len(values) == 1:
            return next(iter(values))

        return None

    record = one(
        (
            r"recording\s+date",
            r"record\s+date",
        )
    )

    # These patterns intentionally require an explicit label close to
    # the date; generic occurrences of "cum/ex" elsewhere are ignored.
    cum = one(
        (
            r"cum\s+dividen",
            r"cum\s+dividend",
        )
    )

    ex = one(
        (
            r"ex\s+dividen",
            r"ex\s+dividend",
        )
    )

    payment = one(
        (
            r"payment\s+date"
            r"\s*(?:at\s+the\s+latest)?",
            r"tanggal\s+pembayaran"
            r"\s*(?:dividen|dividend)?"
            r"\s*(?:paling\s+lambat)?",
        )
    )

    if not all(
        value is not None
        for value in (
            cum,
            ex,
            record,
            payment,
        )
    ):
        return None

    schedule = (
        str(cum),
        str(ex),
        str(record),
        str(payment),
    )

    if not _r2_schedule_is_valid(schedule):
        return None

    return schedule


def extract_cash_dividend_schedule_v1_2(
    texts: Sequence[str],
) -> tuple[str, str, str, str]:
    if not texts:
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_V1_2_DOCUMENTS_EMPTY"
        )

    # Existing V1 schedule semantics remain first choice. This keeps
    # already-green BBCA behavior unchanged.
    try:
        return (
            _extract_cash_dividend_schedule_v1_2_pre_r2(
                texts
            )
        )
    except DividendSemanticReviewError:
        pass

    normalized = [
        normalize_text(text)
        for text in texts
    ]

    candidates: set[
        tuple[str, str, str, str]
    ] = set()

    for text in normalized:
        for extractor in (
            _r2_schedule_from_ordered_idx_form,
            _r2_schedule_from_explicit_labels,
        ):
            candidate = extractor(text)

            if candidate is not None:
                candidates.add(candidate)

    if len(candidates) == 1:
        return next(iter(candidates))

    if len(candidates) > 1:
        raise DividendSemanticReviewError(
            "DIVIDEND_SEMANTIC_V1_2_"
            f"SCHEDULE_NOT_UNIQUE:{sorted(candidates)}"
        )

    raise DividendSemanticReviewError(
        "DIVIDEND_SEMANTIC_V1_2_SCHEDULE_NOT_UNIQUE:[]"
    )


def _r2_document_contributes(
    text: str,
    *,
    mode: str,
    amount: str,
    schedule: tuple[str, str, str, str],
) -> bool:
    """Return whether one document independently supports the selected terms."""
    normalized = normalize_text(text)

    # The canonical mode is selected across the filing set, but an official
    # IDX filing may split the authoritative amount and schedule across
    # language/attachment representations.  A document can therefore be a
    # complete contributor through any strict local authority that yields the
    # already-selected canonical amount.  Total payout values remain excluded
    # by the bounded structured parser and are never added here.
    values = {
        _r2_amount_text(value)
        for value in (
            _r2_remaining_payable_values(normalized)
            | _r2_direct_per_share_values(normalized)
            | _r2_structured_per_share_values(normalized)
        )
    }

    if amount not in values:
        return False

    schedules: set[tuple[str, str, str, str]] = set()
    legacy = _schedule_candidate(normalized)
    if legacy is not None:
        schedules.add(legacy)

    for extractor in (
        _r2_schedule_from_ordered_idx_form,
        _r2_schedule_from_explicit_labels,
    ):
        candidate = extractor(normalized)
        if candidate is not None:
            schedules.add(candidate)

    return schedule in schedules
