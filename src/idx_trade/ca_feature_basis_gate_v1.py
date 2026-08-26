from __future__ import annotations

from typing import Iterable, Sequence

import pandas as pd

from .ca_feature_basis_v1 import (
    BASIS_SAFE,
    BASIS_UNKNOWN,
    BASIS_UNSAFE,
    NOT_APPLICABLE,
    UNRESOLVED,
    FeatureDependency,
    V4_PRICE_FEATURE_DEPENDENCIES,
    evaluate_feature_basis_admission as evaluate_event_basis_admission,
)


CA_COVERAGE_CERTIFIED = "CA_COVERAGE_CERTIFIED"
CA_COVERAGE_UNKNOWN = "CA_COVERAGE_UNKNOWN"
CA_COVERAGE_STATES = {CA_COVERAGE_CERTIFIED, CA_COVERAGE_UNKNOWN}


def _sessions(values: Iterable[object]) -> pd.DatetimeIndex:
    sessions = (
        pd.DatetimeIndex(pd.to_datetime(list(values), errors="coerce"))
        .tz_localize(None)
        .normalize()
    )
    if sessions.isna().any():
        raise ValueError("official_sessions contains invalid date")
    sessions = sessions.unique().sort_values()
    if not len(sessions):
        raise ValueError("official_sessions must not be empty")
    return sessions


def _ticker(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )


def _dates(series: pd.Series, *, label: str) -> pd.Series:
    values = pd.to_datetime(series, errors="coerce").dt.tz_localize(None).dt.normalize()
    if values.isna().any():
        raise ValueError(f"{label} contains invalid date")
    return values


def _strict_bool(series: pd.Series, *, label: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series.dtype):
        return series.astype(bool)
    normalized = series.astype(str).str.strip().str.lower()
    if not set(normalized).issubset({"true", "false"}):
        raise ValueError(f"{label} must contain strict booleans")
    return normalized.eq("true")


def validate_event_semantic_certification(events: pd.DataFrame) -> pd.DataFrame:
    """Prevent an unresolved event taxonomy from being promoted to a boundary.

    Current INC-001 evidence contains known family-classification inconsistencies.
    Therefore a resolved/bounded/non-basis-changing transition must carry an
    independently source-bound semantic certification.  An unresolved event may
    remain uncertified and fail closed.
    """

    required = {
        "effective_transition_state",
        "event_semantics_certified",
        "semantic_evidence_sha256",
    }
    missing = required - set(events.columns)
    if missing:
        raise ValueError(f"basis event semantic certification missing: {sorted(missing)}")
    out = events.copy()
    out["event_semantics_certified"] = _strict_bool(
        out["event_semantics_certified"], label="event_semantics_certified"
    )
    out["semantic_evidence_sha256"] = (
        out["semantic_evidence_sha256"].fillna("").astype(str).str.strip().str.lower()
    )
    certified = out["event_semantics_certified"]
    bad_sha = certified & ~out["semantic_evidence_sha256"].str.fullmatch(r"[0-9a-f]{64}")
    if bad_sha.any():
        raise ValueError("certified event semantics requires semantic_evidence_sha256")

    transition = out["effective_transition_state"].astype(str).str.upper().str.strip()
    promoted = transition.ne(UNRESOLVED)
    if (promoted & ~certified).any():
        raise ValueError(
            "unresolved event semantics cannot be promoted to a transition boundary"
        )
    return out


def prepare_ca_coverage(
    coverage: pd.DataFrame,
    official_sessions: Iterable[object],
) -> pd.DataFrame:
    required = {"ticker", "date", "coverage_state", "source_ref", "evidence_sha256"}
    missing = required - set(coverage.columns)
    if missing:
        raise ValueError(f"CA coverage ledger missing columns: {sorted(missing)}")

    sessions = _sessions(official_sessions)
    session_set = set(pd.Timestamp(day) for day in sessions)
    out = coverage.copy()
    out["ticker"] = _ticker(out["ticker"])
    out["date"] = _dates(out["date"], label="CA coverage ledger")
    if out["ticker"].eq("").any():
        raise ValueError("CA coverage ledger contains empty ticker")
    if out.duplicated(["ticker", "date"]).any():
        raise ValueError("CA coverage ledger contains duplicate ticker/date")
    if not set(out["date"]).issubset(session_set):
        raise ValueError("CA coverage ledger contains non-official session")

    out["coverage_state"] = out["coverage_state"].astype(str).str.upper().str.strip()
    invalid = sorted(set(out["coverage_state"]) - CA_COVERAGE_STATES)
    if invalid:
        raise ValueError(f"unsupported CA coverage state: {invalid}")

    out["source_ref"] = out["source_ref"].fillna("").astype(str).str.strip()
    out["evidence_sha256"] = (
        out["evidence_sha256"].fillna("").astype(str).str.strip().str.lower()
    )
    certified = out["coverage_state"].eq(CA_COVERAGE_CERTIFIED)
    if (certified & out["source_ref"].eq("")).any():
        raise ValueError("certified CA coverage requires source_ref")
    if (
        certified
        & ~out["evidence_sha256"].str.fullmatch(r"[0-9a-f]{64}")
    ).any():
        raise ValueError("certified CA coverage requires evidence_sha256")
    return out.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def evaluate_feature_basis_admission(
    identities: pd.DataFrame,
    events: pd.DataFrame,
    coverage: pd.DataFrame,
    official_sessions: Iterable[object],
    *,
    dependencies: Sequence[FeatureDependency] = V4_PRICE_FEATURE_DEPENDENCIES,
) -> pd.DataFrame:
    """Outcome-blind CA basis admission with explicit no-event coverage.

    This is the authorized V1 application entry point.  The lower-level event
    geometry engine proves known-boundary behavior; this wrapper additionally
    refuses to interpret absence from the event ledger as evidence that no
    structural event exists.
    """

    sessions = _sessions(official_sessions)
    event_input = validate_event_semantic_certification(events)
    coverage_input = prepare_ca_coverage(coverage, sessions)
    base = evaluate_event_basis_admission(
        identities,
        event_input,
        sessions,
        dependencies=dependencies,
    )
    if base.empty:
        return base

    session_index = {pd.Timestamp(day): idx for idx, day in enumerate(sessions)}
    coverage_lookup = {
        (row.ticker, pd.Timestamp(row.date)): str(row.coverage_state)
        for row in coverage_input.itertuples(index=False)
    }

    states: list[str] = []
    reasons: list[str] = []
    unknown_counts: list[int] = []
    for row in base.itertuples(index=False):
        state = str(row.basis_integrity_state)
        reason_parts = [] if str(row.reason) == "SAME_RESOLVED_BASIS_EPOCH" else [str(row.reason)]
        if state == NOT_APPLICABLE:
            states.append(state)
            reasons.append(str(row.reason))
            unknown_counts.append(0)
            continue

        minimum = session_index[pd.Timestamp(row.dependency_min_date)]
        maximum = session_index[pd.Timestamp(row.dependency_max_date)]
        unknown = 0
        for index in range(minimum, maximum + 1):
            date = pd.Timestamp(sessions[index])
            coverage_state = coverage_lookup.get((str(row.ticker), date), CA_COVERAGE_UNKNOWN)
            if coverage_state != CA_COVERAGE_CERTIFIED:
                unknown += 1

        if unknown:
            reason_parts.append(f"CA_EVENT_COVERAGE_UNKNOWN:{unknown}")
            if state != BASIS_UNSAFE:
                state = BASIS_UNKNOWN
        elif not reason_parts:
            reason_parts.append("SAME_RESOLVED_BASIS_EPOCH_AND_CERTIFIED_CA_COVERAGE")

        states.append(state)
        reasons.append("|".join(sorted(set(reason_parts))))
        unknown_counts.append(unknown)

    out = base.copy()
    out["basis_integrity_state"] = states
    out["reason"] = reasons
    out["unknown_ca_coverage_sessions"] = unknown_counts
    return out
