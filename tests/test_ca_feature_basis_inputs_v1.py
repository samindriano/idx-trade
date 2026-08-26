from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.ca_feature_basis_gate_v1 import CA_COVERAGE_CERTIFIED
from idx_trade.ca_feature_basis_inputs_v1 import (
    expand_ca_coverage_intervals,
    strict_census_to_unresolved_event_ledger,
)
from idx_trade.ca_feature_basis_v1 import UNRESOLVED


SHA = "d" * 64


def sessions(n: int = 8) -> pd.DatetimeIndex:
    return pd.bdate_range("2021-03-01", periods=n)


def test_strict_census_import_never_promotes_semantics_or_transition() -> None:
    census = pd.DataFrame(
        [
            {
                "ticker": "BBCA",
                "event_family": "STOCK_SPLIT",
                "candidate_date": "2021-10-13",
                "continuity_status": "PRICE_CONTINUITY_UNRESOLVED_EFFECTIVE_DATE",
                "source_action_id": "Stock Split",
                "source_ref": "fixture://strict-census",
                "source_sha256": SHA,
                "evidence_id": "BBCA-2021-SPLIT",
            }
        ]
    )
    out = strict_census_to_unresolved_event_ledger(census)
    row = out.iloc[0]

    assert row["effective_transition_state"] == UNRESOLVED
    assert not row["event_semantics_certified"]
    assert row["semantic_evidence_sha256"] == ""
    assert pd.isna(row["transition_session"])
    assert row["candidate_date"] == "2021-10-13"
    assert row["import_state"] == "UNRESOLVED_NO_SEMANTIC_PROMOTION"


def test_coverage_interval_expansion_is_inclusive_and_sparse() -> None:
    days = sessions()
    intervals = pd.DataFrame(
        [
            {
                "ticker": "TEST",
                "start_session": days[2],
                "end_session": days[4],
                "coverage_state": CA_COVERAGE_CERTIFIED,
                "coverage_policy_id": "OFFICIAL_CA_ARCHIVE_V1",
                "evidence_id": "COVERAGE-1",
                "source_ref": "fixture://coverage",
                "evidence_sha256": SHA,
            }
        ]
    )
    out = expand_ca_coverage_intervals(intervals, days)

    assert out["date"].tolist() == [days[2], days[3], days[4]]
    assert days[1] not in set(out["date"])
    assert days[5] not in set(out["date"])


def test_overlapping_coverage_intervals_fail_closed() -> None:
    days = sessions()
    common = {
        "ticker": "TEST",
        "coverage_state": CA_COVERAGE_CERTIFIED,
        "coverage_policy_id": "OFFICIAL_CA_ARCHIVE_V1",
        "source_ref": "fixture://coverage",
        "evidence_sha256": SHA,
    }
    intervals = pd.DataFrame(
        [
            {
                **common,
                "start_session": days[1],
                "end_session": days[3],
                "evidence_id": "C1",
            },
            {
                **common,
                "start_session": days[3],
                "end_session": days[5],
                "evidence_id": "C2",
            },
        ]
    )
    with pytest.raises(ValueError, match="overlap"):
        expand_ca_coverage_intervals(intervals, days)


def test_coverage_interval_must_use_official_session_boundaries() -> None:
    days = sessions()
    intervals = pd.DataFrame(
        [
            {
                "ticker": "TEST",
                "start_session": pd.Timestamp("2021-03-06"),
                "end_session": days[4],
                "coverage_state": CA_COVERAGE_CERTIFIED,
                "coverage_policy_id": "OFFICIAL_CA_ARCHIVE_V1",
                "evidence_id": "C1",
                "source_ref": "fixture://coverage",
                "evidence_sha256": SHA,
            }
        ]
    )
    with pytest.raises(ValueError, match="official session"):
        expand_ca_coverage_intervals(intervals, days)
