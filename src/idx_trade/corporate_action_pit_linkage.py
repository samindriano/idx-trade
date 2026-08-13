from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping, Sequence
import re


class LinkageStatus(StrEnum):
    EXACT = "EXACT"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"
    CONFLICT = "CONFLICT"


class EventFamily(StrEnum):
    RIGHTS_ISSUE = "RIGHTS_ISSUE"
    STOCK_SPLIT = "STOCK_SPLIT"
    REVERSE_SPLIT = "REVERSE_SPLIT"
    BONUS_SHARES = "BONUS_SHARES"
    STOCK_DIVIDEND = "STOCK_DIVIDEND"
    CASH_DIVIDEND = "CASH_DIVIDEND"
    MIXED_DIVIDEND = "MIXED_DIVIDEND"
    NON_PREEMPTIVE_ISSUANCE = "NON_PREEMPTIVE_ISSUANCE"
    PARTIAL_DELISTING = "PARTIAL_DELISTING"
    CAPITAL_REDUCTION = "CAPITAL_REDUCTION"
    IPO = "IPO"
    MANDATORY_CONVERSION_UNCLASSIFIED = "MANDATORY_CONVERSION_UNCLASSIFIED"
    OTHER = "OTHER"


@dataclass(frozen=True)
class LinkageDecision:
    status: LinkageStatus
    candidate_index: int | None = None
    reasons: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    evidence: tuple[tuple[str, str], ...] = ()


def _norm_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _norm_upper(value: Any) -> str:
    return _norm_text(value).upper()


def _norm_number(value: Any) -> str | None:
    text = _norm_text(value)
    if not text:
        return None
    text = text.replace(",", "")
    try:
        from decimal import Decimal, InvalidOperation

        value_decimal = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    normalized = format(value_decimal.normalize(), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized or "0"


def canonical_ratio(row: Mapping[str, Any]) -> tuple[str, str, str, str] | None:
    left_value = _norm_number(row.get("ratio_left_value"))
    right_value = _norm_number(row.get("ratio_right_value"))
    left_security = _norm_upper(row.get("ratio_left_security"))
    right_security = _norm_upper(row.get("ratio_right_security"))
    if not left_value or not right_value or not left_security or not right_security:
        return None
    return left_value, left_security, right_value, right_security


def _family_from_text(text: str) -> EventFamily | None:
    """Classify explicit economic-family language in one source field."""

    # Check the negative/pre-emptive distinction before the generic HMETD
    # token.  "Tanpa HMETD" contains HMETD but is not a rights issue.
    if any(token in text for token in ("tanpa hmetd", "pmthmetd", "private placement", "non-preemptive")):
        return EventFamily.NON_PREEMPTIVE_ISSUANCE
    if any(token in text for token in ("hmetd", "right distribution", "rights issue", "hak memesan efek")):
        return EventFamily.RIGHTS_ISSUE
    if "reverse stock" in text or "reverse split" in text:
        return EventFamily.REVERSE_SPLIT
    if "stock split" in text or "pemecahan saham" in text:
        return EventFamily.STOCK_SPLIT
    if any(token in text for token in ("saham bonus", "bonus share", "share bonus")):
        return EventFamily.BONUS_SHARES
    if "stock dividend" in text or "dividen saham" in text:
        return EventFamily.STOCK_DIVIDEND
    if "mixed dividend" in text or "dividen tunai & saham" in text:
        return EventFamily.MIXED_DIVIDEND
    if "cash dividend" in text or "dividen tunai" in text or "deviden tunai" in text:
        return EventFamily.CASH_DIVIDEND
    if "partial delisting" in text:
        return EventFamily.PARTIAL_DELISTING
    if "pengurangan modal" in text or "capital reduction" in text:
        return EventFamily.CAPITAL_REDUCTION
    if "ipo" in text or "penawaran umum perdana" in text:
        return EventFamily.IPO
    return None


def normalize_event_family(*, source_family: Any = None, schedule_subject: Any = None) -> EventFamily:
    """Normalize economic family with authoritative document-subject precedence."""

    source = _norm_text(source_family).casefold()
    subject = _norm_text(schedule_subject).casefold()

    # The linked schedule document is the economic identity authority. This
    # must be checked before the operational/C-BEST label: e.g. a bonus-share
    # schedule can be exposed as Right Distribution or Mixed Dividend.
    subject_family = _family_from_text(subject)
    if subject_family is not None:
        return subject_family
    source_family_value = _family_from_text(source)
    if source_family_value is not None:
        return source_family_value
    if "mandatory conversion" in source or "mandatory conversion" in subject:
        return EventFamily.MANDATORY_CONVERSION_UNCLASSIFIED
    return EventFamily.OTHER


def validate_schedule_locator(locator: Mapping[str, Any], document: Mapping[str, Any]) -> LinkageDecision:
    """Validate KSEI schedule-index metadata against linked document internals."""

    conflicts: list[str] = []
    reasons: list[str] = []
    locator_reference = _norm_upper(locator.get("reference"))
    document_reference = _norm_upper(document.get("ksei_reference"))
    locator_ticker = _norm_upper(locator.get("ticker"))
    document_ticker = _norm_upper(document.get("ticker"))
    evidence = (
        ("locator_reference", locator_reference),
        ("document_reference", document_reference),
        ("locator_ticker", locator_ticker),
        ("document_ticker", document_ticker),
    )
    if locator_reference and document_reference:
        if locator_reference != document_reference:
            conflicts.append("KSEI_REFERENCE_MISMATCH")
        else:
            reasons.append("KSEI_REFERENCE_EXACT")
    elif locator_reference or document_reference:
        reasons.append("KSEI_REFERENCE_INCOMPLETE")
    if locator_ticker and document_ticker:
        if locator_ticker != document_ticker:
            conflicts.append("TICKER_MISMATCH")
        else:
            reasons.append("TICKER_EXACT")
    elif locator_ticker or document_ticker:
        reasons.append("TICKER_INCOMPLETE")
    if not locator_reference and not document_reference and not locator_ticker and not document_ticker:
        return LinkageDecision(LinkageStatus.UNRESOLVED, reasons=("DOCUMENT_IDENTITY_INCOMPLETE",))
    if conflicts:
        return LinkageDecision(
            LinkageStatus.CONFLICT,
            reasons=tuple(reasons),
            conflicts=tuple(conflicts),
            evidence=evidence,
        )
    if any(reason.endswith("_INCOMPLETE") for reason in reasons):
        incomplete = tuple(reason for reason in reasons if reason.endswith("_INCOMPLETE"))
        return LinkageDecision(LinkageStatus.UNRESOLVED, reasons=incomplete, evidence=evidence)
    status = LinkageStatus.CONFLICT if conflicts else LinkageStatus.EXACT
    return LinkageDecision(status=status, reasons=tuple(reasons), conflicts=tuple(conflicts), evidence=evidence)


def _date_equal(left: Any, right: Any) -> bool:
    left_text = _norm_text(left)
    right_text = _norm_text(right)
    return bool(left_text and right_text and left_text == right_text)


def _field_conflicts(event: Mapping[str, Any], candidate: Mapping[str, Any], fields: Sequence[str]) -> list[str]:
    conflicts: list[str] = []
    for field in fields:
        event_value = _norm_text(event.get(field))
        candidate_value = _norm_text(candidate.get(field))
        if event_value and candidate_value and event_value != candidate_value:
            conflicts.append(field)
    return conflicts


def _ratio_equal(event: Mapping[str, Any], candidate: Mapping[str, Any]) -> bool:
    left = canonical_ratio(event)
    right = canonical_ratio(candidate)
    return left is not None and left == right


def _family(candidate: Mapping[str, Any]) -> EventFamily:
    explicit = _norm_upper(candidate.get("event_family"))
    subject = candidate.get("schedule_subject") or candidate.get("subject")
    if _norm_text(subject):
        return normalize_event_family(
            source_family=candidate.get("event_family_source") or candidate.get("source_action") or explicit,
            schedule_subject=subject,
        )
    if explicit in {item.value for item in EventFamily}:
        return EventFamily(explicit)
    return normalize_event_family(
        source_family=candidate.get("event_family_source") or candidate.get("source_action"),
        schedule_subject=candidate.get("schedule_subject") or candidate.get("subject"),
    )


def _event_family(event: Mapping[str, Any]) -> EventFamily:
    explicit = _norm_upper(event.get("event_family"))
    subject = event.get("schedule_subject") or event.get("subject")
    if _norm_text(subject):
        return normalize_event_family(
            source_family=event.get("event_family_source") or event.get("source_action") or explicit,
            schedule_subject=subject,
        )
    if explicit in {item.value for item in EventFamily}:
        return EventFamily(explicit)
    return normalize_event_family(
        source_family=event.get("event_family_source") or event.get("source_action"),
        schedule_subject=event.get("schedule_subject") or event.get("subject"),
    )


def _exact_rights(event: Mapping[str, Any], candidate: Mapping[str, Any]) -> tuple[bool, list[str], list[str]]:
    if _norm_upper(event.get("ticker")) != _norm_upper(candidate.get("ticker")):
        return False, [], ["ticker"]
    reasons: list[str] = []
    strong_identity = False

    event_code = _norm_upper(event.get("rights_code"))
    candidate_code = _norm_upper(candidate.get("rights_code"))
    event_isin = _norm_upper(event.get("rights_isin"))
    candidate_isin = _norm_upper(candidate.get("rights_isin"))
    if bool(event_code) != bool(candidate_code):
        return False, [], ["rights_code_incomplete"]
    if bool(event_isin) != bool(candidate_isin):
        return False, [], ["rights_isin_incomplete"]
    if event_code and candidate_code:
        if event_code != candidate_code:
            return False, [], ["rights_code"]
        reasons.append("RIGHTS_CODE_EXACT")
        strong_identity = True

    if event_isin and candidate_isin:
        if event_isin != candidate_isin:
            return False, [], ["rights_isin"]
        reasons.append("RIGHTS_ISIN_EXACT")
        strong_identity = True

    if strong_identity:
        for field in ("record_date", "distribution_date", "listing_date", "exercise_price"):
            event_value = _norm_text(event.get(field))
            candidate_value = _norm_text(candidate.get(field))
            if event_value and candidate_value and event_value == candidate_value:
                reasons.append(f"{field.upper()}_EXACT")
            elif event_value and candidate_value and event_value != candidate_value:
                reasons.append(f"{field.upper()}_VERSION_DIFF")
        if _ratio_equal(event, candidate):
            reasons.append("RATIO_EXACT")
        elif canonical_ratio(event) is not None and canonical_ratio(candidate) is not None:
            return False, [], ["ratio"]
        return True, reasons, []

    ratio_exact = _ratio_equal(event, candidate)
    record_exact = _date_equal(event.get("record_date"), candidate.get("record_date"))
    listing_exact = _date_equal(event.get("listing_date"), candidate.get("listing_date"))
    exercise_start_exact = _date_equal(event.get("exercise_start_date"), candidate.get("exercise_start_date"))
    if ratio_exact:
        reasons.append("RATIO_EXACT")
    if record_exact:
        reasons.append("RECORD_DATE_EXACT")
    if listing_exact:
        reasons.append("LISTING_DATE_EXACT")
    if exercise_start_exact:
        reasons.append("EXERCISE_START_DATE_EXACT")
    return bool(ratio_exact and (record_exact or listing_exact or exercise_start_exact)), reasons, []


def _exact_split(event: Mapping[str, Any], candidate: Mapping[str, Any]) -> tuple[bool, list[str], list[str]]:
    conflicts = _field_conflicts(event, candidate, ("ticker", "record_date", "distribution_date", "listing_date"))
    if conflicts:
        return False, [], conflicts
    if canonical_ratio(event) is not None and canonical_ratio(candidate) is not None and not _ratio_equal(event, candidate):
        return False, [], ["ratio"]
    ratio_exact = _ratio_equal(event, candidate)
    date_matches = [
        name
        for name in ("record_date", "distribution_date", "listing_date")
        if _date_equal(event.get(name), candidate.get(name))
    ]
    reasons = (["RATIO_EXACT"] if ratio_exact else []) + [f"{name.upper()}_EXACT" for name in date_matches]
    return bool(ratio_exact and date_matches), reasons, []


def _exact_distribution(event: Mapping[str, Any], candidate: Mapping[str, Any]) -> tuple[bool, list[str], list[str]]:
    conflicts = _field_conflicts(event, candidate, ("ticker", "record_date", "distribution_date"))
    if conflicts:
        return False, [], conflicts
    if canonical_ratio(event) is not None and canonical_ratio(candidate) is not None and not _ratio_equal(event, candidate):
        return False, [], ["ratio"]
    ratio_exact = _ratio_equal(event, candidate)
    record_exact = _date_equal(event.get("record_date"), candidate.get("record_date"))
    distribution_exact = _date_equal(event.get("distribution_date"), candidate.get("distribution_date"))
    reasons = (["RATIO_EXACT"] if ratio_exact else [])
    if record_exact:
        reasons.append("RECORD_DATE_EXACT")
    if distribution_exact:
        reasons.append("DISTRIBUTION_DATE_EXACT")
    return bool(ratio_exact and record_exact and distribution_exact), reasons, []


def _exact_cash(event: Mapping[str, Any], candidate: Mapping[str, Any]) -> tuple[bool, list[str], list[str]]:
    return _exact_distribution(event, candidate)


def _exact_share_state(event: Mapping[str, Any], candidate: Mapping[str, Any]) -> tuple[bool, list[str], list[str]]:
    conflicts = _field_conflicts(event, candidate, ("ticker", "listing_date"))
    if conflicts:
        return False, [], conflicts
    after = _norm_number(event.get("total_shares_after_action"))
    candidate_after = _norm_number(candidate.get("total_shares_after_action"))
    listing_exact = _date_equal(event.get("listing_date"), candidate.get("listing_date"))
    reasons: list[str] = []
    if after and candidate_after and after == candidate_after:
        reasons.append("TOTAL_SHARES_AFTER_EXACT")
    if listing_exact:
        reasons.append("LISTING_DATE_EXACT")
    return bool(after and candidate_after and after == candidate_after and listing_exact), reasons, []


_REVISION_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"\bkoreksi\b",
        r"\bperubahan\b",
        r"\binformasi tambahan\b",
        r"\bpenjadwalan ulang\b",
        r"\brevision\b",
        r"\brevised\b",
        r"\bchange(?:s|d)?\b",
        r"\badditional information\b",
        r"\brescheduling\b",
    )
)


def is_explicit_revision_subject(value: Any) -> bool:
    text = _norm_text(value).casefold()
    return any(pattern.search(text) for pattern in _REVISION_PATTERNS)


def revision_relation(base: Mapping[str, Any], later: Mapping[str, Any]) -> LinkageDecision:
    """Recognize append-only revision lineage only with explicit revision language."""

    revision_text = " ".join(
        _norm_text(later.get(field)) for field in ("subject", "title") if _norm_text(later.get(field))
    )
    if not is_explicit_revision_subject(revision_text):
        return LinkageDecision(LinkageStatus.UNRESOLVED, reasons=("NO_EXPLICIT_REVISION_LANGUAGE",))
    if _norm_upper(base.get("ticker")) != _norm_upper(later.get("ticker")):
        return LinkageDecision(LinkageStatus.CONFLICT, conflicts=("ticker",))
    if _family(base) != _family(later):
        return LinkageDecision(LinkageStatus.CONFLICT, conflicts=("event_family",))

    # An explicit prior-reference citation is the strongest append-only
    # relation. It is allowed to carry changed schedule dates/economics; those
    # differences are version content, not a reason to lose the lineage.
    prior_reference = _norm_upper(later.get("prior_ksei_reference"))
    base_reference = _norm_upper(base.get("ksei_reference"))
    if prior_reference:
        if not base_reference or prior_reference != base_reference:
            return LinkageDecision(LinkageStatus.CONFLICT, conflicts=("prior_ksei_reference",))
        return LinkageDecision(
            LinkageStatus.EXACT,
            candidate_index=0,
            reasons=("EXPLICIT_REVISION", "PRIOR_KSEI_REFERENCE_EXACT"),
        )

    decision = link_event(base, [later])
    if decision.status == LinkageStatus.EXACT:
        return LinkageDecision(
            LinkageStatus.EXACT,
            candidate_index=0,
            reasons=("EXPLICIT_REVISION", *decision.reasons),
        )
    return decision


def link_event(event: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]) -> LinkageDecision:
    """Link one normalized official event to exactly one official candidate.

    Date or title proximity is intentionally insufficient. Event-family-specific
    exact anchors are required. Multiple exact candidates fail closed.
    """

    event_family = _event_family(event)
    ticker = _norm_upper(event.get("ticker"))
    if not ticker or event_family in {EventFamily.OTHER, EventFamily.MANDATORY_CONVERSION_UNCLASSIFIED}:
        return LinkageDecision(LinkageStatus.UNRESOLVED, reasons=("EVENT_IDENTITY_INCOMPLETE",))

    exact_candidates: list[tuple[int, list[str]]] = []
    conflict_notes: list[str] = []
    for index, candidate in enumerate(candidates):
        if _norm_upper(candidate.get("ticker")) != ticker:
            continue
        if _family(candidate) != event_family:
            continue
        if event_family == EventFamily.RIGHTS_ISSUE:
            exact, reasons, conflicts = _exact_rights(event, candidate)
        elif event_family in {EventFamily.STOCK_SPLIT, EventFamily.REVERSE_SPLIT}:
            exact, reasons, conflicts = _exact_split(event, candidate)
        elif event_family in {EventFamily.BONUS_SHARES, EventFamily.STOCK_DIVIDEND, EventFamily.MIXED_DIVIDEND}:
            exact, reasons, conflicts = _exact_distribution(event, candidate)
        elif event_family == EventFamily.CASH_DIVIDEND:
            exact, reasons, conflicts = _exact_cash(event, candidate)
        elif event_family in {
            EventFamily.NON_PREEMPTIVE_ISSUANCE,
            EventFamily.PARTIAL_DELISTING,
            EventFamily.CAPITAL_REDUCTION,
        }:
            exact, reasons, conflicts = _exact_share_state(event, candidate)
        else:
            exact, reasons, conflicts = False, [], []
        if conflicts:
            conflict_notes.extend(f"candidate[{index}]:{field}" for field in conflicts)
            continue
        if exact:
            exact_candidates.append((index, reasons))

    # A contradictory explicit candidate must not be hidden by another exact
    # candidate.  Keep the result fail-closed rather than choosing by order.
    if conflict_notes:
        return LinkageDecision(LinkageStatus.CONFLICT, conflicts=tuple(conflict_notes))
    if len(exact_candidates) == 1:
        index, reasons = exact_candidates[0]
        return LinkageDecision(LinkageStatus.EXACT, candidate_index=index, reasons=tuple(reasons))
    if len(exact_candidates) > 1:
        return LinkageDecision(
            LinkageStatus.AMBIGUOUS,
            reasons=tuple(f"candidate[{index}]" for index, _ in exact_candidates),
        )
    if conflict_notes:
        return LinkageDecision(LinkageStatus.CONFLICT, conflicts=tuple(conflict_notes))
    return LinkageDecision(LinkageStatus.UNRESOLVED, reasons=("NO_EVENT_SPECIFIC_EXACT_ANCHOR",))


def resolve_availability_provenance(
    *,
    idx_published_at_utc: Any = None,
    ksei_document_date: Any = None,
    ksei_publication_table_date: Any = None,
    asset_timestamp_candidate_raw: Any = None,
    asset_url: Any = None,
    asset_filename: Any = None,
    observed_at_utc: Any = None,
    linkage_status: LinkageStatus | str | None = None,
) -> dict[str, Any]:
    """Resolve only defensible knowledge time; preserve weaker source dates.

    KSEI PDF dates, publication-table dates, and asset-name timestamp
    candidates are source-native evidence only.  They do not establish first
    public availability until an independent timing contract is proven.  An
    exact linked IDX timestamp remains the only timestamp-level result here.
    """

    from datetime import date, datetime, timezone

    published = _norm_text(idx_published_at_utc)
    source_dates = {
        "ksei_document_date": _norm_text(ksei_document_date) or None,
        "ksei_publication_table_date": _norm_text(ksei_publication_table_date) or None,
    }
    for field, value in source_dates.items():
        if value:
            try:
                date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError(f"malformed {field}") from exc

    observed = _norm_text(observed_at_utc)
    observed_normalized = None
    if observed:
        try:
            observed_parsed = datetime.fromisoformat(observed.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("malformed observed_at_utc") from exc
        if observed_parsed.tzinfo is None:
            raise ValueError("observed_at_utc must include timezone")
        observed_normalized = observed_parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    from urllib.parse import unquote, urlsplit
    asset_url_text = _norm_text(asset_url) or None
    asset_filename_text = _norm_text(asset_filename) or None
    if asset_url_text and asset_filename_text:
        url_filename = unquote(urlsplit(asset_url_text).path.rsplit("/", 1)[-1])
        if url_filename and url_filename != asset_filename_text:
            raise ValueError("asset_url and asset_filename disagree")
    if published:
        try:
            parsed = datetime.fromisoformat(published.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("malformed idx_published_at_utc") from exc
        if parsed.tzinfo is None:
            raise ValueError("idx_published_at_utc must include timezone")
        utc = parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        exact = linkage_status == LinkageStatus.EXACT or str(linkage_status) == LinkageStatus.EXACT.value
        return {
            "knowledge_at_utc": utc if exact else None,
            "knowledge_date": utc[:10] if exact else None,
            "precision": "IDX_TIMESTAMP_CONFIRMED" if exact else ("DATE_ONLY" if any(source_dates.values()) else "UNKNOWN"),
            "availability_status": "IDX_TIMESTAMP_CONFIRMED" if exact else "IDX_TIMESTAMP_LINKAGE_NOT_EXACT",
            "idx_published_at_utc": utc,
            "linkage_status": str(linkage_status) if linkage_status is not None else None,
            "source_dates": source_dates,
            "asset_timestamp_candidate_raw": _norm_text(asset_timestamp_candidate_raw) or None,
            "asset_url": asset_url_text,
            "asset_filename": asset_filename_text,
            "observed_at_utc": observed_normalized,
        }

    candidate = _norm_text(asset_timestamp_candidate_raw) or None
    if any(source_dates.values()) or candidate:
        return {
            "knowledge_at_utc": None,
            "knowledge_date": None,
            "precision": "DATE_ONLY" if any(source_dates.values()) else "UNKNOWN",
            "availability_status": "SOURCE_DATE_ONLY_NOT_AVAILABILITY_VERIFIED",
            "idx_published_at_utc": None,
            "linkage_status": str(linkage_status) if linkage_status is not None else None,
            "source_dates": source_dates,
            "asset_timestamp_candidate_raw": candidate,
            "asset_url": asset_url_text,
            "asset_filename": asset_filename_text,
            "observed_at_utc": observed_normalized,
        }
    return {
        "knowledge_at_utc": None,
        "knowledge_date": None,
        "precision": "UNKNOWN",
        "availability_status": "UNKNOWN",
        "idx_published_at_utc": None,
        "linkage_status": str(linkage_status) if linkage_status is not None else None,
        "source_dates": source_dates,
        "asset_timestamp_candidate_raw": candidate,
        "asset_url": asset_url_text,
        "asset_filename": asset_filename_text,
        "observed_at_utc": observed_normalized,
    }


def safe_availability_date(**kwargs: Any) -> dict[str, Any]:
    """Backward-compatible narrow entry point for availability resolution."""

    return resolve_availability_provenance(**kwargs)
