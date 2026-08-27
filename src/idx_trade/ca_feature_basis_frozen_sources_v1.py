from __future__ import annotations

from collections.abc import Iterable, Sequence

import pandas as pd

from .ca_feature_basis_family_coverage_v1 import (
    FAMILY_COVERAGE_CERTIFIED,
    FAMILY_COVERAGE_UNKNOWN,
)
from .ca_feature_basis_v1 import (
    BONUS_SHARES,
    CAPITAL_RESTRUCTURING,
    MANDATORY_CONVERSION,
    RESOLVED,
    REVERSE_SPLIT,
    RIGHTS_HMETD,
    STOCK_DIVIDEND,
    STOCK_SPLIT,
    STRUCTURAL_EVENT_FAMILIES,
    prepare_basis_events,
)


EXACT_TRANSITION = "EXACT_TRANSITION"
SCHEDULE_REQUIRED = "SCHEDULE_REQUIRED"

# These mappings are used only to create an epoch boundary from an already
# source-certified EXACT_TRANSITION.  They do not authorize any price factor or
# economic adjustment.  Ambiguous/unsupported families remain UNKNOWN.
_FROZEN_EXACT_FAMILY_MAP = {
    "RIGHT_DISTRIBUTION": RIGHTS_HMETD,
    "STOCK_DIVIDEND": STOCK_DIVIDEND,
    "MIXED_STOCK_DIVIDEND": STOCK_DIVIDEND,
    "SHARE_BONUS": BONUS_SHARES,
    "BONUS_SHARES": BONUS_SHARES,
    "BONUS_SHARE": BONUS_SHARES,
    "BONUS_DISTRIBUTION": BONUS_SHARES,
    "STOCK_SPLIT": STOCK_SPLIT,
    "REVERSE_STOCK": REVERSE_SPLIT,
    "REVERSE_STOCK_SPLIT": REVERSE_SPLIT,
    "REVERSE_SPLIT": REVERSE_SPLIT,
    "MANDATORY_CONVERSION": MANDATORY_CONVERSION,
    "CAPITAL_RESTRUCTURING": CAPITAL_RESTRUCTURING,
    "CAPITAL_REDUCTION": CAPITAL_RESTRUCTURING,
    # Historical KSEI schedule evidence used MERGER_OR_RESTRUCTURING as its
    # source-native umbrella.  An already source-certified exact transition may
    # create a conservative epoch boundary under CAPITAL_RESTRUCTURING; this
    # still does not authorize an adjustment factor or imply every merger is a
    # basis change without event-specific semantics.
    "MERGER_OR_RESTRUCTURING": CAPITAL_RESTRUCTURING,
}

# Historical KSEI evidence in this project directly demonstrates issuer-history
# representation for these source-native families.  Do not broaden this merely
# because the parser has a normalization label for another family.  In
# particular, voluntary conversion taxonomy was historically inconsistent and
# split/bonus/restructuring coverage is primarily proven through separate IDX
# evidence.
KSEI_PROVEN_COVERAGE_FAMILIES: tuple[str, ...] = (
    RIGHTS_HMETD,
    STOCK_DIVIDEND,
)

_EVENT_SEMANTICS_REQUIRED = {
    "event_id",
    "ticker",
    "family",
    "semantic_class",
    "transition_date",
    "transition_source",
    "reason",
    "source_dates",
}

# The historical KSEI ticker census alone is not sufficient to claim an
# arbitrary research interval.  Each row consumed by this adapter must be
# accompanied by a source-bound temporal scope attestation.  The legacy census
# can therefore be reused only after a separate immutable scope artifact adds
# these fields; absence of that attestation fails closed.
_KSEI_COVERAGE_REQUIRED = {
    "ticker",
    "coverage_status",
    "coverage_certified",
    "source_url",
    "source_sha256",
    "coverage_start_session",
    "coverage_end_session",
    "coverage_observed_at",
}


def _sha256(value: object, *, label: str) -> str:
    text = str(value or "").strip().lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise ValueError(f"{label} must be 64 lowercase/uppercase hex characters")
    return text


def _ticker(value: object) -> str:
    return str(value or "").upper().replace(".JK", "").strip()


def _strict_bool(value: object, *, label: str) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text == "true":
        return True
    if text == "false":
        return False
    raise ValueError(f"{label} must be a strict boolean")


def _official_sessions(values: Iterable[object]) -> pd.DatetimeIndex:
    sessions = (
        pd.DatetimeIndex(pd.to_datetime(list(values), errors="coerce"))
        .tz_localize(None)
        .normalize()
    )
    if sessions.isna().any() or not len(sessions):
        raise ValueError("official_sessions must be non-empty valid dates")
    return sessions.unique().sort_values()


def _optional_timestamp(value: object, *, label: str, normalize: bool) -> pd.Timestamp | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"{label} contains invalid timestamp")
    timestamp = pd.Timestamp(parsed)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_convert(None)
    if normalize:
        timestamp = timestamp.normalize()
    return timestamp


def _expand_family_coverage_intervals(
    intervals: pd.DataFrame,
    official_sessions: Iterable[object],
) -> pd.DataFrame:
    """Expand family-scoped source claims without promoting them to global coverage."""

    required = {
        "ticker",
        "event_family",
        "start_session",
        "end_session",
        "coverage_state",
        "source_contract_id",
        "evidence_id",
        "source_ref",
        "evidence_sha256",
        "coverage_reason",
    }
    missing = required - set(intervals.columns)
    if missing:
        raise ValueError(f"family coverage interval ledger missing columns: {sorted(missing)}")

    sessions = _official_sessions(official_sessions)
    index_by_date = {pd.Timestamp(day): idx for idx, day in enumerate(sessions)}
    rows: list[dict[str, object]] = []
    seen: set[tuple[str, pd.Timestamp, str, str]] = set()

    for source in intervals.itertuples(index=False):
        ticker = _ticker(source.ticker)
        family = str(source.event_family or "").upper().strip()
        state = str(source.coverage_state or "").upper().strip()
        contract_id = str(source.source_contract_id or "").strip()
        evidence_id = str(source.evidence_id or "").strip()
        source_ref = str(source.source_ref or "").strip()
        evidence_sha = str(source.evidence_sha256 or "").strip().lower()
        reason = str(source.coverage_reason or "").strip()
        start = pd.to_datetime(source.start_session, errors="coerce")
        end = pd.to_datetime(source.end_session, errors="coerce")

        if not ticker or family not in STRUCTURAL_EVENT_FAMILIES:
            raise ValueError("family coverage interval contains invalid ticker/family")
        if state not in {FAMILY_COVERAGE_CERTIFIED, FAMILY_COVERAGE_UNKNOWN}:
            raise ValueError(f"unsupported family coverage interval state: {state}")
        if not contract_id or not evidence_id or not reason:
            raise ValueError("family coverage interval requires contract/evidence/reason identity")
        if pd.isna(start) or pd.isna(end):
            raise ValueError("family coverage interval contains invalid boundary")
        start = pd.Timestamp(start).tz_localize(None).normalize()
        end = pd.Timestamp(end).tz_localize(None).normalize()
        if start not in index_by_date or end not in index_by_date:
            raise ValueError("family coverage interval boundary is not an official session")
        if start > end:
            raise ValueError("family coverage interval start is after end")
        if state == FAMILY_COVERAGE_CERTIFIED:
            if not source_ref:
                raise ValueError("certified family coverage interval requires source_ref")
            _sha256(evidence_sha, label=f"{ticker}:{family} evidence_sha256")

        for index in range(index_by_date[start], index_by_date[end] + 1):
            day = pd.Timestamp(sessions[index])
            key = (ticker, day, family, contract_id)
            if key in seen:
                raise ValueError("family coverage intervals overlap for ticker/session/family/source")
            seen.add(key)
            rows.append(
                {
                    "ticker": ticker,
                    "date": day,
                    "event_family": family,
                    "coverage_state": state,
                    "source_contract_id": contract_id,
                    "evidence_id": evidence_id,
                    "source_ref": source_ref,
                    "evidence_sha256": evidence_sha,
                    "coverage_reason": reason,
                }
            )

    if not rows:
        return pd.DataFrame(
            columns=[
                "ticker",
                "date",
                "event_family",
                "coverage_state",
                "source_contract_id",
                "evidence_id",
                "source_ref",
                "evidence_sha256",
                "coverage_reason",
            ]
        )
    return pd.DataFrame(rows).sort_values(
        ["ticker", "date", "event_family", "source_contract_id"], kind="mergesort"
    ).reset_index(drop=True)


def frozen_event_semantics_to_basis_inputs(
    semantics: pd.DataFrame,
    official_sessions: Iterable[object],
    *,
    semantic_artifact_sha256: str,
    semantic_source_ref: str,
) -> tuple[pd.DataFrame, set[str]]:
    """Promote only frozen source-backed exact transitions into basis events.

    Returns ``(resolved_event_ledger, forced_unknown_tickers)``.

    Any schedule-required row, unknown semantic class, malformed exact row, or
    exact family without an explicit V1 mapping keeps the whole ticker in the
    forced-UNKNOWN set.  This is deliberately conservative: partial historical
    knowledge for a ticker is not interpreted as complete event continuity.
    """

    missing = _EVENT_SEMANTICS_REQUIRED - set(semantics.columns)
    if missing:
        raise ValueError(f"frozen CA semantics missing columns: {sorted(missing)}")
    artifact_sha = _sha256(semantic_artifact_sha256, label="semantic_artifact_sha256")
    source_ref = str(semantic_source_ref or "").strip()
    if not source_ref:
        raise ValueError("semantic_source_ref must be non-empty")
    sessions = _official_sessions(official_sessions)
    session_set = set(pd.Timestamp(day) for day in sessions)

    if semantics.duplicated(["event_id"]).any():
        raise ValueError("frozen CA semantics contains duplicate event_id")

    resolved_rows: list[dict[str, object]] = []
    forced_unknown: set[str] = set()
    for source in semantics.itertuples(index=False):
        ticker = _ticker(source.ticker)
        event_id = str(source.event_id or "").strip()
        family = str(source.family or "").upper().strip()
        semantic_class = str(source.semantic_class or "").upper().strip()
        if not ticker or not event_id or not family or not semantic_class:
            raise ValueError("frozen CA semantics contains empty event identity/classification")

        if semantic_class != EXACT_TRANSITION:
            forced_unknown.add(ticker)
            continue

        mapped_family = _FROZEN_EXACT_FAMILY_MAP.get(family)
        transition_source = str(source.transition_source or "").strip()
        transition = pd.to_datetime(source.transition_date, errors="coerce")
        if mapped_family is None or not transition_source or pd.isna(transition):
            forced_unknown.add(ticker)
            continue

        transition = pd.Timestamp(transition).tz_localize(None).normalize()
        if transition not in session_set:
            forced_unknown.add(ticker)
            continue

        resolved_rows.append(
            {
                "ticker": ticker,
                "event_family": mapped_family,
                "event_identity": event_id,
                "effective_transition_state": RESOLVED,
                "transition_session": transition,
                "transition_lower_session": None,
                "transition_upper_session": None,
                "source_ref": f"{source_ref}#event_id={event_id}",
                "evidence_id": event_id,
                "evidence_sha256": artifact_sha,
                "event_semantics_certified": True,
                "semantic_evidence_sha256": artifact_sha,
                "source_family": family,
                "transition_source": transition_source,
                "semantic_reason": str(source.reason or "").strip(),
                "source_dates": str(source.source_dates or "").strip(),
                "import_state": "FROZEN_EXACT_TRANSITION_PROMOTED",
            }
        )

    columns = [
        "ticker",
        "event_family",
        "event_identity",
        "effective_transition_state",
        "transition_session",
        "transition_lower_session",
        "transition_upper_session",
        "source_ref",
        "evidence_id",
        "evidence_sha256",
        "event_semantics_certified",
        "semantic_evidence_sha256",
        "source_family",
        "transition_source",
        "semantic_reason",
        "source_dates",
        "import_state",
    ]
    ledger = pd.DataFrame(resolved_rows, columns=columns)
    if not ledger.empty:
        ledger = prepare_basis_events(ledger, sessions)
    return ledger, forced_unknown


def compare_ksei_population_to_identities(
    identities: pd.DataFrame,
    coverage_census: pd.DataFrame,
) -> dict[str, object]:
    """Compare the exact application ticker population with a KSEI census.

    Extra census tickers are harmless, but every application ticker must be
    represented before the census can support a market-wide application claim.
    The function intentionally compares exact normalized identities rather than
    inferring population equivalence from row counts.
    """

    if "ticker" not in identities.columns:
        raise ValueError("application identities require ticker")
    if "ticker" not in coverage_census.columns:
        raise ValueError("KSEI CA coverage census requires ticker")

    application = {_ticker(value) for value in identities["ticker"]}
    census = {_ticker(value) for value in coverage_census["ticker"]}
    if "" in application or "" in census:
        raise ValueError("population comparison contains empty ticker")

    missing = sorted(application - census)
    extra = sorted(census - application)
    return {
        "application_ticker_count": len(application),
        "coverage_ticker_count": len(census),
        "coverage_contains_application_population": not missing,
        "missing_application_tickers": missing,
        "extra_coverage_tickers": extra,
    }


def ksei_ticker_coverage_to_family_coverage(
    coverage_census: pd.DataFrame,
    official_sessions: Iterable[object],
    *,
    start_session: object,
    end_session: object,
    coverage_artifact_sha256: str,
    coverage_source_ref: str,
    covered_event_families: Sequence[str] = KSEI_PROVEN_COVERAGE_FAMILIES,
    forced_unknown_tickers: Iterable[str] = (),
    source_contract_id: str = "KSEI_REGISTERED_SECURITY_HISTORY_V1",
) -> pd.DataFrame:
    """Convert KSEI history-page coverage into explicit family-scoped claims.

    This function deliberately does *not* return the binary global CA coverage
    consumed by the feature gate.  KSEI may certify only the event families
    explicitly named by ``covered_event_families``; a separate composite step
    must prove all required structural families across all authoritative
    sources before global coverage can become ``CA_COVERAGE_CERTIFIED``.

    The requested study interval is never treated as source truth.  Certified
    rows must carry explicit source-bound ``coverage_start_session``,
    ``coverage_end_session``, and ``coverage_observed_at`` fields, and the
    requested interval must lie wholly inside that attested history scope.
    """

    missing = _KSEI_COVERAGE_REQUIRED - set(coverage_census.columns)
    if missing:
        raise ValueError(f"KSEI CA coverage census missing columns: {sorted(missing)}")
    artifact_sha = _sha256(coverage_artifact_sha256, label="coverage_artifact_sha256")
    source_ref = str(coverage_source_ref or "").strip()
    contract_id = str(source_contract_id or "").strip()
    if not source_ref or not contract_id:
        raise ValueError("coverage source/contract identity must be non-empty")

    families = tuple(dict.fromkeys(str(value).upper().strip() for value in covered_event_families))
    if not families:
        raise ValueError("covered_event_families must not be empty")
    unsupported = sorted(set(families) - set(STRUCTURAL_EVENT_FAMILIES))
    if unsupported:
        raise ValueError(f"unsupported KSEI structural family coverage: {unsupported}")
    not_proven = sorted(set(families) - set(KSEI_PROVEN_COVERAGE_FAMILIES))
    if not_proven:
        raise ValueError(
            "KSEI source contract cannot certify unproven event families: "
            f"{not_proven}"
        )

    sessions = _official_sessions(official_sessions)
    start = pd.to_datetime(start_session, errors="coerce")
    end = pd.to_datetime(end_session, errors="coerce")
    if pd.isna(start) or pd.isna(end):
        raise ValueError("coverage study boundary is invalid")
    start = pd.Timestamp(start).tz_localize(None).normalize()
    end = pd.Timestamp(end).tz_localize(None).normalize()
    session_set = set(pd.Timestamp(day) for day in sessions)
    if start not in session_set or end not in session_set or start > end:
        raise ValueError("coverage study boundaries must be ordered official sessions")

    blocked = {_ticker(value) for value in forced_unknown_tickers if _ticker(value)}
    normalized_tickers = coverage_census["ticker"].map(_ticker)
    if normalized_tickers.duplicated().any():
        raise ValueError("KSEI CA coverage census contains duplicate ticker")

    intervals: list[dict[str, object]] = []
    for source in coverage_census.itertuples(index=False):
        ticker = _ticker(source.ticker)
        if not ticker:
            raise ValueError("KSEI CA coverage census contains empty ticker")
        certified_flag = _strict_bool(source.coverage_certified, label="coverage_certified")
        status = str(source.coverage_status or "").upper().strip()
        raw_source_ref = str(source.source_url or "").strip()
        raw_sha = str(source.source_sha256 or "").strip().lower()
        status_certified = status == "COVERAGE_CERTIFIED"

        source_start = _optional_timestamp(
            source.coverage_start_session,
            label=f"{ticker} coverage_start_session",
            normalize=True,
        )
        source_end = _optional_timestamp(
            source.coverage_end_session,
            label=f"{ticker} coverage_end_session",
            normalize=True,
        )
        observed_at = _optional_timestamp(
            source.coverage_observed_at,
            label=f"{ticker} coverage_observed_at",
            normalize=False,
        )

        source_scope_valid = False
        if source_start is not None or source_end is not None or observed_at is not None:
            if source_start is None or source_end is None or observed_at is None:
                raise ValueError(f"{ticker} KSEI temporal coverage scope must be complete")
            if source_start not in session_set or source_end not in session_set:
                raise ValueError(f"{ticker} KSEI temporal coverage scope must use official sessions")
            if source_start > source_end:
                raise ValueError(f"{ticker} KSEI temporal coverage scope is reversed")
            if observed_at.normalize() < source_end:
                raise ValueError(f"{ticker} coverage_observed_at predates certified history end")
            source_scope_valid = source_start <= start and source_end >= end

        base_certified = ticker not in blocked and certified_flag and status_certified
        certified = base_certified and source_scope_valid

        if certified:
            raw_sha = _sha256(raw_sha, label=f"{ticker} source_sha256")
            if not raw_source_ref:
                raise ValueError(f"{ticker} certified coverage requires source_url")
            state = FAMILY_COVERAGE_CERTIFIED
            evidence_sha = raw_sha
            evidence_ref = raw_source_ref
            reason = "KSEI_TICKER_HISTORY_SCOPE_CERTIFIED_FOR_EXPLICIT_FAMILY"
        else:
            state = FAMILY_COVERAGE_UNKNOWN
            evidence_sha = artifact_sha
            evidence_ref = source_ref
            if ticker in blocked:
                reason = "FORCED_UNKNOWN_BY_EVENT_SEMANTICS_OR_CROSS_SOURCE_CONFLICT"
            elif certified_flag != status_certified:
                reason = "KSEI_COVERAGE_FIELDS_DISAGREE"
            elif base_certified and not source_scope_valid:
                reason = "REQUESTED_INTERVAL_EXCEEDS_KSEI_CERTIFIED_HISTORY_SCOPE"
            else:
                reason = (
                    str(getattr(source, "failure_reason", "") or "").strip()
                    or "KSEI_TICKER_HISTORY_COVERAGE_UNRESOLVED"
                )

        for family in families:
            intervals.append(
                {
                    "ticker": ticker,
                    "event_family": family,
                    "start_session": start,
                    "end_session": end,
                    "coverage_state": state,
                    "source_contract_id": contract_id,
                    "evidence_id": f"KSEI_CA_COVERAGE:{ticker}:{family}",
                    "source_ref": evidence_ref,
                    "evidence_sha256": evidence_sha,
                    "coverage_reason": reason,
                }
            )

    return _expand_family_coverage_intervals(pd.DataFrame(intervals), sessions)


def ksei_ticker_coverage_to_basis_coverage(*args: object, **kwargs: object) -> pd.DataFrame:
    """Removed unsafe compatibility path.

    Historical KSEI page coverage is not sufficient to certify every structural
    CA family market-wide.  Call ``ksei_ticker_coverage_to_family_coverage`` and
    then ``combine_family_coverage`` instead.
    """

    raise RuntimeError(
        "DIRECT_KSEI_TO_GLOBAL_CA_COVERAGE_FORBIDDEN_USE_FAMILY_SCOPED_COMPOSITE_GATE"
    )
