from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.ca_feature_basis_gate_v1 import (
    BASIS_SAFE,
    BASIS_UNKNOWN,
    BASIS_UNSAFE,
    CA_COVERAGE_CERTIFIED,
    CA_COVERAGE_UNKNOWN,
    evaluate_feature_basis_admission,
    prepare_ca_coverage,
    validate_event_semantic_certification,
)
from idx_trade.ca_feature_basis_v1 import (
    FeatureDependency,
    RESOLVED,
    STOCK_SPLIT,
    UNRESOLVED,
)


SHA = "b" * 64
SEMANTIC_SHA = "c" * 64


def sessions(n: int = 12) -> pd.DatetimeIndex:
    return pd.bdate_range("2021-02-01", periods=n)


def identities(days: pd.DatetimeIndex) -> pd.DataFrame:
    return pd.DataFrame({"ticker": "TEST", "date": days})


def event(
    days: pd.DatetimeIndex,
    *,
    state: str = RESOLVED,
    certified: bool = True,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "TEST",
                "event_family": STOCK_SPLIT,
                "event_identity": "EV1",
                "effective_transition_state": state,
                "transition_session": days[5] if state == RESOLVED else None,
                "transition_lower_session": None,
                "transition_upper_session": None,
                "source_ref": "fixture://event",
                "evidence_id": "EV1-EVIDENCE",
                "evidence_sha256": SHA,
                "event_semantics_certified": certified,
                "semantic_evidence_sha256": SEMANTIC_SHA if certified else "",
            }
        ]
    )


def coverage(days: pd.DatetimeIndex, *, omit: int | None = None) -> pd.DataFrame:
    rows = []
    for index, day in enumerate(days):
        if omit is not None and index == omit:
            continue
        rows.append(
            {
                "ticker": "TEST",
                "date": day,
                "coverage_state": CA_COVERAGE_CERTIFIED,
                "source_ref": "fixture://coverage",
                "evidence_sha256": SHA,
            }
        )
    return pd.DataFrame(rows)


def test_certified_coverage_preserves_known_resolved_crossing() -> None:
    days = sessions()
    dependency = (FeatureDependency("lag2", (-2, 0)),)
    result = evaluate_feature_basis_admission(
        identities(days),
        event(days),
        coverage(days),
        days,
        dependencies=dependency,
    ).set_index("date")

    assert result.loc[days[5], "basis_integrity_state"] == BASIS_UNSAFE
    assert result.loc[days[6], "basis_integrity_state"] == BASIS_UNSAFE
    assert result.loc[days[7], "basis_integrity_state"] == BASIS_SAFE
    assert result.loc[days[7], "unknown_ca_coverage_sessions"] == 0


def test_absence_of_event_is_not_no_event_evidence() -> None:
    days = sessions(8)
    dependency = (FeatureDependency("lag1", (-1, 0)),)
    empty_events = event(days, state=UNRESOLVED, certified=False).iloc[0:0].copy()
    result = evaluate_feature_basis_admission(
        identities(days),
        empty_events,
        coverage(days, omit=4),
        days,
        dependencies=dependency,
    ).set_index("date")

    assert result.loc[days[4], "basis_integrity_state"] == BASIS_UNKNOWN
    assert result.loc[days[5], "basis_integrity_state"] == BASIS_UNKNOWN
    assert result.loc[days[6], "basis_integrity_state"] == BASIS_SAFE


def test_unknown_coverage_state_blocks_dependency_window() -> None:
    days = sessions(8)
    cov = coverage(days)
    cov.loc[cov["date"].eq(days[3]), "coverage_state"] = CA_COVERAGE_UNKNOWN
    cov.loc[cov["date"].eq(days[3]), ["source_ref", "evidence_sha256"]] = ""
    dependency = (FeatureDependency("lag2", (-2, 0)),)
    empty_events = event(days, state=UNRESOLVED, certified=False).iloc[0:0].copy()

    result = evaluate_feature_basis_admission(
        identities(days), empty_events, cov, days, dependencies=dependency
    ).set_index("date")

    assert result.loc[days[3], "basis_integrity_state"] == BASIS_UNKNOWN
    assert result.loc[days[4], "basis_integrity_state"] == BASIS_UNKNOWN
    assert result.loc[days[5], "basis_integrity_state"] == BASIS_UNKNOWN
    assert result.loc[days[6], "basis_integrity_state"] == BASIS_SAFE


def test_resolved_transition_requires_semantic_certification() -> None:
    days = sessions()
    with pytest.raises(ValueError, match="cannot be promoted"):
        validate_event_semantic_certification(event(days, certified=False))


def test_unresolved_transition_may_remain_semantically_uncertified() -> None:
    days = sessions()
    checked = validate_event_semantic_certification(
        event(days, state=UNRESOLVED, certified=False)
    )
    assert not checked["event_semantics_certified"].iloc[0]


def test_certified_coverage_requires_hash_and_source() -> None:
    days = sessions(4)
    cov = coverage(days)
    cov.loc[0, "evidence_sha256"] = ""
    with pytest.raises(ValueError, match="requires evidence_sha256"):
        prepare_ca_coverage(cov, days)


def test_missing_intermediate_official_session_blocks_even_when_ticker_row_missing() -> None:
    days = sessions(9)
    # The frozen observed-row lag is over ticker observations, but CA coverage
    # must certify every official session that lies between those observations.
    ids = identities(days).drop(index=3).reset_index(drop=True)
    cov = coverage(days, omit=3)
    dependency = (FeatureDependency("lag1", (-1, 0)),)
    empty_events = event(days, state=UNRESOLVED, certified=False).iloc[0:0].copy()

    result = evaluate_feature_basis_admission(
        ids, empty_events, cov, days, dependencies=dependency
    ).set_index("date")

    # Current observation day[4] depends on previous observed row day[2], so
    # unknown CA coverage on official day[3] lies inside the dependency span.
    assert result.loc[days[4], "basis_integrity_state"] == BASIS_UNKNOWN
