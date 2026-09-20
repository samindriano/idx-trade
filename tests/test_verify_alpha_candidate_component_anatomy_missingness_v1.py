from __future__ import annotations

import pandas as pd

from research.verify_alpha_candidate_component_anatomy_missingness_v1 import missingness_report


def test_full_formula_missingness_match_is_asserted() -> None:
    frame = pd.DataFrame(
        {
            "eligible_decision_universe": [True, True, True],
            "C1_residual_reversal_5_v1": [1.0, None, 3.0],
            "c1_score_recomputed": [1.0, None, 3.0],
            "C2_participation_confirmation_5_v1": [None, 2.0, None],
            "c2_score_recomputed": [None, 2.0, None],
            "C4_path_efficiency_reversal_20_v1": [1.0, None, None],
            "c4_score_recomputed": [1.0, None, None],
        }
    )

    result = missingness_report(frame)

    assert result["status"] == "PASS_FORMULA_MISSINGNESS_MATCH"
    assert result["all_candidates_match"] is True
    assert all(row["missingness_mismatch_rows"] == 0 for row in result["candidates"].values())


def test_full_formula_missingness_mismatch_fails_closed() -> None:
    frame = pd.DataFrame(
        {
            "eligible_decision_universe": [True, True],
            "C1_residual_reversal_5_v1": [1.0, None],
            "c1_score_recomputed": [1.0, 2.0],
            "C2_participation_confirmation_5_v1": [None, None],
            "c2_score_recomputed": [None, None],
            "C4_path_efficiency_reversal_20_v1": [None, None],
            "c4_score_recomputed": [None, None],
        }
    )

    result = missingness_report(frame)

    assert result["status"] == "FAIL_FORMULA_MISSINGNESS_MISMATCH"
    assert result["all_candidates_match"] is False
    assert result["candidates"]["C1"]["missingness_mismatch_rows"] == 1
