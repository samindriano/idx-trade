from __future__ import annotations

import pandas as pd

from research.alpha_c2_market_breadth_mixture_v1 import add_quadrants, merge_breadth_and_selection, summarize_table


def test_c2_breadth_and_selection_mixture_is_deterministic() -> None:
    rows = []
    for index in range(32):
        rows.append(
            {
                "ticker": f"T{index:02d}",
                "date": pd.Timestamp("2025-01-02"),
                "eligible_decision_universe": True,
                "rank_C2_participation_confirmation_5_v1": float(32 - index),
                "ret_5": 1.0 if index < 20 else -1.0,
                "c2_log_abnormal_turnover": 1.0 if index < 20 else -1.0,
            }
        )
    table = merge_breadth_and_selection(add_quadrants(pd.DataFrame(rows)))
    result = summarize_table(table)
    assert result["dates"] == 1
    assert result["selected_mixture"]["pp"]["mean"] == 2 / 3
    assert result["selected_mixture"]["nn"]["mean"] == 1 / 3
    assert result["selected_mixture"]["cross"]["mean"] == 0.0
