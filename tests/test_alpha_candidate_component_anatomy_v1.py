from __future__ import annotations

import pandas as pd

from research.alpha_candidate_component_anatomy_v1 import (
    CANDIDATES,
    daily_component_correlations,
)


def test_component_correlations_reports_formula_and_top30_metrics() -> None:
    dates = pd.to_datetime(["2025-01-02"] * 32)
    frame = pd.DataFrame(
        {
            "ticker": [f"T{i:02d}" for i in range(32)],
            "date": dates,
            "eligible_decision_universe": True,
            CANDIDATES["C1"]: [float(32 - i) for i in range(32)],
            f"rank_{CANDIDATES['C1']}": [float(32 - i) for i in range(32)],
            "c1_score_recomputed": [float(32 - i) for i in range(32)],
            "c1_residual": [float(i) for i in range(32)],
            "c1_beta_market_component": [float(i % 4) for i in range(32)],
            "vol_20": [float(i + 1) for i in range(32)],
        }
    )
    result = daily_component_correlations(frame, "C1", ["c1_residual", "c1_beta_market_component", "vol_20"])
    assert result["formula_checked_values"] == 32
    assert result["formula_max_abs_difference"] == 0.0
    assert result["component_vs_score_daily_spearman"]["c1_residual"]["count"] == 1
    assert result["top30_component_percentile_mean"]["vol_20"]["count"] == 1
