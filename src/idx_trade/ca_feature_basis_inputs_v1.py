from __future__ import annotations

from typing import Iterable

import pandas as pd

from .ca_feature_basis_gate_v1 import CA_COVERAGE_STATES
from .ca_feature_basis_v1 import SUPPORTED_EVENT_FAMILIES, UNRESOLVED


_STRICT_CENSUS_REQUIRED = {
    "ticker",
    "event_family",
    "candidate_date",
    "continuity_status",
    "source_action_id",
    "source_ref",
    "source_sha256",
    "evidence_id",
}

_COVERAGE_INTERVAL_REQUIRED = {
    "ticker",
    "start_session",
    "end_session",
    "coverage_state",
    "coverage_policy_id",
    "evidence_id",
    "source_ref",
    "evidence_sha256",
}


def _ticker(value: object) -> str:
    return str(value or "").upper().replace(".JK", "").strip()


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


def strict_census_to_unresolved_event_ledger(census: pd.DataFrame) -> pd.DataFrame:
    """Import prior strict CA census evidence without promoting its semantics.

    INC-001 found family-taxonomy inconsistencies and unresolved effective
    transition dates.  This adapter therefore preserves the observed family
    label only as a candidate classification and forces every imported event to
    remain semantically uncertified and transition-unresolved.
    """

    missing = _STRICT_CENSUS_REQUIRED - set(census.columns)
    if missing:
        raise ValueError(f"strict CA census missing columns: {sorted(missing)}")
    rows: list[dict[str, object]] = []
    for source in census.itertuples(index=False):
        ticker = _ticker(source.ticker)
        family = str(source.event_family or "").upper().strip()
        evidence_id = str(source.evidence_id or "").strip()
        source_ref = str(source.source_ref or "").strip()
        source_sha = str(source.source_sha256 or "").strip().lower()
        if not ticker or not evidence_id or not source_ref:
            raise ValueError("strict CA census contains empty identity/provenance")
        if family not in SUPPORTED_EVENT_FAMILIES:
            raise ValueError(f"strict CA census has unsupported family: {family}")
        if len(source_sha) != 64 or any(ch not in "0123456789abcdef" for ch in source_sha):
            raise ValueError("strict CA census source_sha256 is invalid")
        rows.append(
            {
                "ticker": ticker,
                "event_family": family,
                "event_identity": evidence_id,
                "effective_transition_state": UNRESOLVED,
                "transition_session": None,
                "transition_lower_session": None,
                "transition_upper_session": None,
                "source_ref": source_ref,
                "evidence_id": evidence_id,
                "evidence_sha256": source_sha,
                "event_semantics_certified": False,
                "semantic_evidence_sha256": "",
                "candidate_date": str(source.candidate_date or "").strip(),
                "source_action_id": str(source.source_action_id or "").strip(),
                "imported_continuity_status": str(source.continuity_status or "").strip(),
                "import_state": "UNRESOLVED_NO_SEMANTIC_PROMOTION",
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(
            columns=[
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
                "candidate_date",
                "source_action_id",
                "imported_continuity_status",
                "import_state",
            ]
        )
    if out.duplicated(["ticker", "event_identity"]).any():
        raise ValueError("strict CA census produces duplicate event identity")
    return out.sort_values(["ticker", "event_identity"], kind="mergesort").reset_index(drop=True)


def expand_ca_coverage_intervals(
    intervals: pd.DataFrame,
    official_sessions: Iterable[object],
) -> pd.DataFrame:
    """Expand source-backed CA coverage intervals to explicit session coverage.

    Absence of an interval is intentionally not filled.  Downstream admission
    interprets missing ticker/session coverage as `CA_COVERAGE_UNKNOWN`.
    """

    missing = _COVERAGE_INTERVAL_REQUIRED - set(intervals.columns)
    if missing:
        raise ValueError(f"CA coverage interval ledger missing columns: {sorted(missing)}")
    sessions = _sessions(official_sessions)
    index_by_date = {pd.Timestamp(day): idx for idx, day in enumerate(sessions)}

    rows: list[dict[str, object]] = []
    seen: set[tuple[str, pd.Timestamp]] = set()
    for source in intervals.itertuples(index=False):
        ticker = _ticker(source.ticker)
        if not ticker:
            raise ValueError("CA coverage interval contains empty ticker")
        start = pd.to_datetime(source.start_session, errors="coerce")
        end = pd.to_datetime(source.end_session, errors="coerce")
        if pd.isna(start) or pd.isna(end):
            raise ValueError("CA coverage interval contains invalid boundary")
        start = pd.Timestamp(start).tz_localize(None).normalize()
        end = pd.Timestamp(end).tz_localize(None).normalize()
        if start not in index_by_date or end not in index_by_date:
            raise ValueError("CA coverage interval boundary is not an official session")
        if start > end:
            raise ValueError("CA coverage interval start is after end")
        state = str(source.coverage_state or "").upper().strip()
        if state not in CA_COVERAGE_STATES:
            raise ValueError(f"unsupported CA coverage interval state: {state}")

        policy_id = str(source.coverage_policy_id or "").strip()
        evidence_id = str(source.evidence_id or "").strip()
        source_ref = str(source.source_ref or "").strip()
        evidence_sha = str(source.evidence_sha256 or "").strip().lower()
        if not policy_id or not evidence_id:
            raise ValueError("CA coverage interval requires policy/evidence identity")

        start_index = index_by_date[start]
        end_index = index_by_date[end]
        for index in range(start_index, end_index + 1):
            day = pd.Timestamp(sessions[index])
            key = (ticker, day)
            if key in seen:
                raise ValueError("CA coverage intervals overlap for ticker/session")
            seen.add(key)
            rows.append(
                {
                    "ticker": ticker,
                    "date": day,
                    "coverage_state": state,
                    "coverage_policy_id": policy_id,
                    "evidence_id": evidence_id,
                    "source_ref": source_ref,
                    "evidence_sha256": evidence_sha,
                }
            )

    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(
            columns=[
                "ticker",
                "date",
                "coverage_state",
                "coverage_policy_id",
                "evidence_id",
                "source_ref",
                "evidence_sha256",
            ]
        )
    return out.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
