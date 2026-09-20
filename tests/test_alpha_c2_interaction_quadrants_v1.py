from __future__ import annotations

import pandas as pd

from research.alpha_c2_interaction_quadrants_v1 import summarize_quadrants
from research.alpha_candidate_component_anatomy_v1 import CANDIDATES


def test_quadrants_partition_and_top30_selection() -> None:
    rows = []
    for index in range(32):
        ret = 1.0 if index % 2 == 0 else -1.0
        activity = 1.0 if index < 16 else -1.0
        rows.append(
            {
                "ticker": f"T{index:02d}",
                "date": pd.Timestamp("2025-01-02"),
                "eligible_decision_universe": True,
                CANDIDATES["C2"]: float(32 - index),
                f"rank_{CANDIDATES['C2']}": float(32 - index),
                "ret_5": ret,
                "c2_log_abnormal_turnover": activity,
            }
        )
    result = summarize_quadrants(pd.DataFrame(rows))
    assert result["usable_dates"] == 1
    pooled = result["pooled_quadrants"]
    assert sum(value["eligible_rows"] for value in pooled.values()) == 32
    assert sum(value["selected_slots"] for value in pooled.values()) == 30
    assert result["daily_selected_positive_score_fraction"]["count"] == 1
