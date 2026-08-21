import pandas as pd

from idx_trade.decision_v2_failure_diagnosis import FailureDiagnosisResult
from idx_trade.decision_v2_failure_diagnosis_boundary import apply_next_session_boundary


def test_terminal_session_is_excluded_from_next_session_rate_denominators() -> None:
    exit_pending = pd.DataFrame(
        [
            {"index": 598, "block": 6, "current_rank_bin": "21_30", "recovered_to_le20": True, "next_top10": False, "next_top20": True, "confirmed_exit_next": False, "current_rank": 25},
            {"index": 599, "block": 6, "current_rank_bin": "21_30", "recovered_to_le20": False, "next_top10": False, "next_top20": False, "confirmed_exit_next": False, "current_rank": 25},
        ]
    )
    fresh = pd.DataFrame(
        [
            {"index": 598, "block": 6, "previous_rank_bin": "31_50", "next_top10": True, "next_top20": True, "next_present": True},
            {"index": 599, "block": 6, "previous_rank_bin": "31_50", "next_top10": False, "next_top20": False, "next_present": False},
        ]
    )
    summary = {
        "exit_grace_severity": {
            "overall_recovery_rate": 0.5,
            "by_current_rank_bin": {"21_30": {"recovery_rate": 0.5, "next_top10_rate": 0.0, "next_top20_rate": 0.5, "confirmed_exit_next_rate": 0.0}},
        },
        "candidate_scarcity": {
            "by_previous_rank_bin": {"31_50": {"next_top10_rate": 0.5, "next_top20_rate": 0.5, "next_absent_rate": 0.5}}
        },
        "block_mechanism_summary": [{"block": 6, "exit_pending_recovery_rate": 0.5, "rejected_fresh_next_top20_rate": 0.5}],
    }
    result = FailureDiagnosisResult(
        summary=summary,
        exit_pending=exit_pending,
        rejected_fresh=fresh,
        churn_attribution=pd.DataFrame(),
        block_summary=pd.DataFrame([{"block": 6, "exit_pending_recovery_rate": 0.5, "rejected_fresh_next_top20_rate": 0.5}]),
    )
    corrected = apply_next_session_boundary(result)
    assert corrected.summary["exit_grace_severity"]["overall_recovery_rate"] == 1.0
    assert corrected.summary["candidate_scarcity"]["by_previous_rank_bin"]["31_50"]["next_top20_rate"] == 1.0
    assert corrected.exit_pending["next_evaluable"].tolist() == [True, False]
    assert corrected.rejected_fresh["next_evaluable"].tolist() == [True, False]
