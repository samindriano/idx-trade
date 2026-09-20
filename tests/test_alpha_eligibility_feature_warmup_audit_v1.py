from __future__ import annotations

import pandas as pd

from research.alpha_eligibility_feature_warmup_audit_v1 import summarize


def _frame(score_c1: list[float | None]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "BBB"],
            "date": pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-01"]),
            "eligible_decision_universe": [False, True, True],
            "C1_residual_reversal_5_v1": score_c1,
            "C2_participation_confirmation_5_v1": [None, 2.0, 3.0],
            "C3_financial_quality_growth_v1": [None, None, 4.0],
            "C4_path_efficiency_reversal_20_v1": [None, 5.0, 6.0],
        }
    )


def test_scores_are_gated_and_missingness_is_decomposed() -> None:
    result = summarize(_frame([None, 1.0, 2.0]))

    assert result["status"] == "PASS_ELIGIBILITY_FEATURE_WARMUP_SEPARATION"
    assert result["all_candidates_score_gated_by_eligibility"] is True
    assert result["candidates"]["C1"]["eligible_missing_rows"] == 0
    assert result["candidates"]["C3"]["eligible_missing_rows"] == 1


def test_finite_score_outside_eligibility_fails_closed() -> None:
    result = summarize(_frame([9.0, 1.0, 2.0]))

    assert result["status"] == "FAIL_SCORE_OUTSIDE_ELIGIBILITY"
    assert result["all_candidates_score_gated_by_eligibility"] is False
    assert result["candidates"]["C1"]["outside_eligible_finite_rows"] == 1
