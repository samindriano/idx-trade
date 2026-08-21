from __future__ import annotations

import pandas as pd

from idx_trade.decision_v3_failure_diagnosis import DecisionV3FailureDiagnosisResult
from idx_trade.decision_v3_failure_diagnosis_boundary import apply_terminal_observation_boundary


def test_terminal_entries_and_right_censored_spells_are_excluded_from_rates() -> None:
    lifecycle = pd.DataFrame(
        [
            {
                "entry_tier": "C",
                "entry_index": 598,
                "entry_block": 6,
                "duration_sessions": 1,
                "completed": True,
                "right_censored": False,
                "one_session_holding": True,
                "next_session_severe_exit": True,
                "eventual_severe_exit": True,
                "entry_session_high_churn_ge3": True,
            },
            {
                "entry_tier": "C",
                "entry_index": 599,
                "entry_block": 6,
                "duration_sessions": 1,
                "completed": False,
                "right_censored": True,
                "one_session_holding": True,
                "next_session_severe_exit": False,
                "eventual_severe_exit": False,
                "entry_session_high_churn_ge3": False,
            },
        ]
    )
    severe = pd.DataFrame(
        [
            {
                "block": 6,
                "replacement_count": 3,
                "high_churn_ge3": True,
                "severe_exit_count": 1,
                "severe_exit_session": True,
                "vacancy_fill_count": 1,
                "soft_replacement_count": 0,
                "severe_and_vacancy_fill_overlap": True,
            }
        ]
    )
    blocks = pd.DataFrame(
        [
            {
                "block": block,
                "tier_a_next_severe_rate": None,
                "tier_a_one_session_share": None,
                "tier_b_next_severe_rate": None,
                "tier_b_one_session_share": None,
                "tier_c_next_severe_rate": None,
                "tier_c_one_session_share": None,
                "tier_a_soft_next_severe_rate": None,
                "tier_a_soft_one_session_share": None,
            }
            for block in range(1, 7)
        ]
    )
    result = DecisionV3FailureDiagnosisResult(
        summary={
            "entry_tier_lifecycle": {},
            "block_mechanism_summary": [],
            "block_3_6_vs_reference": {},
        },
        severe_exit_sessions=severe,
        entry_lifecycle=lifecycle,
        block_summary=blocks,
    )

    hardened = apply_terminal_observation_boundary(result)
    c = hardened.summary["entry_tier_lifecycle"]["C"]
    assert c["entries"] == 2
    assert c["next_session_observable_entries"] == 1
    assert c["next_session_severe_exit_rate"] == 1.0
    assert c["completed_spells"] == 1
    assert c["eventual_severe_exit_rate"] == 1.0
    assert hardened.summary["terminal_observation_boundary"]["next_session_unobservable_entries"] == 1
