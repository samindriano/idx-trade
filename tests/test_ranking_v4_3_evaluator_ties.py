from __future__ import annotations

import numpy as np
import pandas as pd

from idx_trade.ranking_v4_3_model_eval import evaluate_head_by_date
from idx_trade.ranking_v4_3_target_execution import TARGET_H5_AVAILABLE


def test_all_tied_scores_still_produce_disjoint_deterministic_extremes() -> None:
    day = pd.Timestamp("2025-01-02")
    tickers = [f"T{i:02d}" for i in range(60)]
    scored = pd.DataFrame(
        {
            "ticker": tickers,
            "date": day,
            "alpha_h5": 0.5,
        }
    )
    targets = pd.DataFrame(
        {
            "ticker": tickers,
            "date": day,
            "target_state_h5": TARGET_H5_AVAILABLE,
            "target_rank_h5": np.linspace(0.0, 1.0, 60),
            "r5": np.linspace(-0.1, 0.1, 60),
        }
    )
    metric = evaluate_head_by_date(scored, targets, head="H5").iloc[0]
    assert metric["top30_observable"] == 30
    assert metric["bottom30_observable"] == 30
    assert bool(metric["top30_metric_admitted"])
    assert bool(metric["spread_metric_admitted"])
    # Top tie-break is ticker ascending; Bottom is exact reverse. If the two
    # sets overlapped, this synthetic monotonic target would produce zero.
    assert metric["top30_bottom30_spread"] < 0.0
