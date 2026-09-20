from __future__ import annotations

import pandas as pd

from research.alpha_candidate_overlap_market_state_v1 import classify_market_state, summarize_rows


def test_market_state_threshold_and_empty_summary_are_deterministic() -> None:
    assert classify_market_state(0.5, 0.5) == "HIGH_HIGH"
    assert classify_market_state(0.5, 0.4) == "RET_HIGH_ACT_LOW"
    assert classify_market_state(0.4, 0.5) == "RET_LOW_ACT_HIGH"
    assert classify_market_state(0.4, 0.4) == "LOW_LOW"
    assert summarize_rows(pd.DataFrame()) == {"dates": 0, "by_state": {}}
