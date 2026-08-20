from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.pit_security_identity_training_support import (
    ALLOWED_TARGET_STATE_COLUMNS,
    intersect_affected,
    normalize_per_date_support,
    normalize_target_states,
    select_exact_head_support,
    union_intersections,
    verify_target_projection,
)


def states() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC", "DDD"],
            "date": ["2020-01-02"] * 4,
            "target_state_h5": [
                "TARGET_H5_AVAILABLE",
                "TARGET_BOTH_AVAILABLE",
                "NO_FUTURE_SESSION",
                "TARGET_H5_AVAILABLE",
            ],
            "target_state_h10": [
                "TARGET_H10_AVAILABLE",
                "TARGET_BOTH_AVAILABLE",
                "NO_FUTURE_SESSION",
                "NO_FUTURE_SESSION",
            ],
        }
    )


def dates() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "session_index": [1, 2],
            "date": ["2020-01-02", "2020-01-03"],
            "h5_eligible": [True, False],
            "h10_eligible": [False, True],
        }
    )


def test_exact_head_support_requires_eligible_date_and_exact_state() -> None:
    h5 = select_exact_head_support(states(), dates(), head="h5", expected_eligible_dates=1)
    h10 = select_exact_head_support(states(), dates(), head="h10", expected_eligible_dates=1)
    assert h5["ticker"].tolist() == ["AAA", "DDD"]
    assert h10.empty


def test_forbidden_projection_and_unexpected_state_fail_closed() -> None:
    with pytest.raises(ValueError, match="exactly authorized"):
        verify_target_projection((*ALLOWED_TARGET_STATE_COLUMNS, "r5"))
    bad = states()
    bad.loc[0, "target_state_h5"] = "SYNTHETIC_AVAILABLE"
    with pytest.raises(ValueError, match="unexpected states"):
        normalize_target_states(bad)


def test_duplicate_target_and_per_date_keys_fail_closed() -> None:
    duplicate_target = pd.concat([states(), states().iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        normalize_target_states(duplicate_target)
    duplicate_date = dates().copy()
    duplicate_date.loc[1, "date"] = "2020-01-02"
    with pytest.raises(ValueError, match="duplicate"):
        normalize_per_date_support(duplicate_date)


def test_intersection_is_exact_and_union_deduplicates_identity_and_type() -> None:
    affected = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "BBB"],
            "date": ["2020-01-02"] * 3,
            "impact_type": ["DIRECT_FREN", "SPILLOVER", "SPILLOVER"],
        }
    ).drop_duplicates()
    support = pd.DataFrame({"ticker": ["AAA", "BBB"], "date": ["2020-01-02"] * 2})
    direct = intersect_affected(affected, support, impact_type="DIRECT_FREN")
    spill = intersect_affected(affected, support, impact_type="SPILLOVER")
    assert direct["ticker"].tolist() == ["AAA"]
    assert spill["ticker"].tolist() == ["BBB"]
    union = union_intersections(direct, spill, spill)
    assert len(union) == 2
