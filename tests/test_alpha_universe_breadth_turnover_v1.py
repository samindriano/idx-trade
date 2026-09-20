from __future__ import annotations

import pandas as pd

from research.alpha_universe_breadth_turnover_v1 import pair_metrics, select_top30, summarize_pairs


def test_selection_and_breadth_pair_metrics_are_deterministic() -> None:
    rows = []
    for date, offset in [("2025-01-02", 0), ("2025-01-03", 1)]:
        for index in range(32):
            rows.append(
                {
                    "ticker": f"T{index:02d}",
                    "date": pd.Timestamp(date),
                    "eligible_decision_universe": True,
                    "rank_C1_residual_reversal_5_v1": float(32 - index - offset),
                }
            )
    frame = pd.DataFrame(rows)
    selections = select_top30(frame, "C1")
    pairs = pair_metrics(
        selections,
        {date: 32 for date in selections},
        {date: 32 for date in selections},
        [pd.Timestamp("2025-01-02"), pd.Timestamp("2025-01-03")],
    )
    result = summarize_pairs(pairs)
    assert result["pairs"] == 1
    assert result["turnover"]["mean"] == 0.0
    assert result["correlations"]["to_finite_count_vs_turnover"]["pairs"] == 1
