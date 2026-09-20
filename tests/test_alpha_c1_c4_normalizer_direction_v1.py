from __future__ import annotations

import pandas as pd

from research.alpha_c1_c4_normalizer_direction_v1 import daily_group_rows, summarize_groups


def test_normalizer_direction_groups_are_deterministic() -> None:
    rows = []
    for index in range(32):
        rows.append(
            {
                "ticker": f"T{index:02d}",
                "date": pd.Timestamp("2025-01-02"),
                "eligible_decision_universe": True,
                "C1_residual_reversal_5_v1": float(index),
                "rank_C1_residual_reversal_5_v1": float(index),
                "c1_residual": float(index),
                "vol_20": float(index + 1),
            }
        )
    grouped = daily_group_rows(pd.DataFrame(rows), "C1")
    result = summarize_groups(grouped)
    assert result["dates"] == 1
    assert result["groups"]["both"]["mean_group_count"] == 28.0
    assert result["groups"]["score_only"]["mean_group_count"] == 2.0
    assert result["groups"]["numerator_only"]["mean_group_count"] == 2.0
