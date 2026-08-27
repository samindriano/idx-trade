from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from .ca_feature_basis_gate_v1 import CA_COVERAGE_CERTIFIED, CA_COVERAGE_UNKNOWN
from .ca_feature_basis_inputs_v1 import expand_ca_coverage_intervals
from .ca_feature_basis_v1 import (
    RESOLVED,
    RIGHTS_HMETD,
    STOCK_DIVIDEND,
    prepare_basis_events,
)


EXACT_TRANSITION = "EXACT_TRANSITION"
SCHEDULE_REQUIRED = "SCHEDULE_REQUIRED"

# Only source families whose transition semantics are already represented by the
# frozen KSEI event-window policy are admitted here.  An exact transition with
# any other family is not guessed into a V1 basis family; its ticker remains
# coverage-blocked instead.
_FROZEN_EXACT_FAMILY_MAP = {
    "RIGHT_DISTRIBUTION": RIGHTS_HMETD,
    "STOCK_DIVIDEND": STOCK_DIVIDEND,
}

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

_KSEI_COVERAGE_REQUIRED = {
    "ticker",
    "coverage_status",
    "coverage_certified",
    "source_url",
    "source_sha256",
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
        if transition not in set(sessions):
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
        # Reuse the core structural checks; this also rejects a transition that
        # is not on the supplied official-session calendar.
        ledger = prepare_basis_events(ledger, sessions)
    return ledger, forced_unknown


def ksei_ticker_coverage_to_basis_coverage(
    coverage_census: pd.DataFrame,
    official_sessions: Iterable[object],
    *,
    start_session: object,
    end_session: object,
    coverage_artifact_sha256: str,
    coverage_source_ref: str,
    forced_unknown_tickers: Iterable[str] = (),
    coverage_policy_id: str = "KSEI_REGISTERED_SECURITY_HISTORY_V1",
) -> pd.DataFrame:
    """Convert frozen per-ticker KSEI history census into explicit coverage.

    A ticker is certified only when both frozen coverage fields agree, its raw
    source SHA is valid, and it is not explicitly forced UNKNOWN by unresolved
    event semantics or cross-source conflict.  All other cases remain UNKNOWN.
    """

    missing = _KSEI_COVERAGE_REQUIRED - set(coverage_census.columns)
    if missing:
        raise ValueError(f"KSEI CA coverage census missing columns: {sorted(missing)}")
    artifact_sha = _sha256(coverage_artifact_sha256, label="coverage_artifact_sha256")
    source_ref = str(coverage_source_ref or "").strip()
    policy_id = str(coverage_policy_id or "").strip()
    if not source_ref or not policy_id:
        raise ValueError("coverage source/policy identity must be non-empty")

    sessions = _official_sessions(official_sessions)
    start = pd.to_datetime(start_session, errors="coerce")
    end = pd.to_datetime(end_session, errors="coerce")
    if pd.isna(start) or pd.isna(end):
        raise ValueError("coverage study boundary is invalid")
    start = pd.Timestamp(start).tz_localize(None).normalize()
    end = pd.Timestamp(end).tz_localize(None).normalize()
    if start not in set(sessions) or end not in set(sessions) or start > end:
        raise ValueError("coverage study boundaries must be ordered official sessions")

    blocked = {_ticker(value) for value in forced_unknown_tickers if _ticker(value)}
    if coverage_census["ticker"].map(_ticker).duplicated().any():
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

        certified = ticker not in blocked and certified_flag and status_certified
        if certified:
            raw_sha = _sha256(raw_sha, label=f"{ticker} source_sha256")
            if not raw_source_ref:
                raise ValueError(f"{ticker} certified coverage requires source_url")
            state = CA_COVERAGE_CERTIFIED
            evidence_sha = raw_sha
            evidence_ref = raw_source_ref
            reason = "KSEI_TICKER_HISTORY_COVERAGE_CERTIFIED"
        else:
            state = CA_COVERAGE_UNKNOWN
            evidence_sha = artifact_sha
            evidence_ref = source_ref
            if ticker in blocked:
                reason = "FORCED_UNKNOWN_BY_EVENT_SEMANTICS_OR_CROSS_SOURCE_CONFLICT"
            elif certified_flag != status_certified:
                reason = "KSEI_COVERAGE_FIELDS_DISAGREE"
            else:
                reason = str(getattr(source, "failure_reason", "") or "").strip() or "KSEI_TICKER_HISTORY_COVERAGE_UNRESOLVED"

        intervals.append(
            {
                "ticker": ticker,
                "start_session": start,
                "end_session": end,
                "coverage_state": state,
                "coverage_policy_id": policy_id,
                "evidence_id": f"KSEI_CA_COVERAGE:{ticker}",
                "source_ref": evidence_ref,
                "evidence_sha256": evidence_sha,
                "coverage_reason": reason,
            }
        )

    interval_frame = pd.DataFrame(intervals)
    expanded = expand_ca_coverage_intervals(interval_frame, sessions)
    if expanded.empty:
        return expanded
    reason_lookup = {
        str(row.ticker): str(row.coverage_reason)
        for row in interval_frame.itertuples(index=False)
    }
    expanded["coverage_reason"] = expanded["ticker"].map(reason_lookup)
    return expanded
