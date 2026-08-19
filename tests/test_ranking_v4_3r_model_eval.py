from __future__ import annotations

import numpy as np
import pandas as pd

from idx_trade import ranking_v4_3_model_eval as base
from idx_trade.ranking_v4_3_target_execution import TARGET_H5_AVAILABLE
from idx_trade.ranking_v4_3r_model_eval import (
    V4_3_REFERENCE_DATE_TARGET_COVERAGE_GATE,
    V4_3R_DATE_TARGET_COVERAGE_GATE,
    evaluate_head_by_date_ca80,
)


def _case(observable_total: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    day = pd.Timestamp("2025-01-02")
    tickers = [f"T{i:02d}" for i in range(60)]
    scored = pd.DataFrame(
        {
            "ticker": tickers,
            "date": day,
            "alpha_h5": np.linspace(0.0, 1.0, 60),
        }
    )
    available = set(tickers[:observable_total])
    ranks = np.linspace(0.0, 1.0, 60)
    targets = pd.DataFrame(
        {
            "ticker": tickers,
            "date": day,
            "target_state_h5": [
                TARGET_H5_AVAILABLE if ticker in available else "TARGET_DATA_UNOBSERVABLE"
                for ticker in tickers
            ],
            "target_rank_h5": [
                rank if ticker in available else np.nan
                for ticker, rank in zip(tickers, ranks)
            ],
            "r5": [
                rank - 0.5 if ticker in available else np.nan
                for ticker, rank in zip(tickers, ranks)
            ],
        }
    )
    return scored, targets


def test_ca80_overlay_changes_only_date_level_coverage_admission() -> None:
    scored, targets = _case(observable_total=53)
    strict = base.evaluate_head_by_date(scored, targets, head="H5").iloc[0]
    relaxed = evaluate_head_by_date_ca80(scored, targets, head="H5").iloc[0]

    assert V4_3_REFERENCE_DATE_TARGET_COVERAGE_GATE == 0.90
    assert V4_3R_DATE_TARGET_COVERAGE_GATE == 0.80
    assert strict["target_coverage_rate"] == relaxed["target_coverage_rate"]
    assert strict["target_coverage_rate"] < 0.90
    assert strict["target_coverage_rate"] >= 0.80
    assert not bool(strict["date_metric_admitted"])
    assert bool(relaxed["date_metric_admitted"])
    assert strict["target_observable_rows"] == relaxed["target_observable_rows"] == 53


def test_ca80_overlay_preserves_no_refill_and_restores_inherited_constant() -> None:
    scored, targets = _case(observable_total=53)
    before = float(base.DATE_TARGET_COVERAGE_GATE)
    relaxed = evaluate_head_by_date_ca80(scored, targets, head="H5").iloc[0]
    after = float(base.DATE_TARGET_COVERAGE_GATE)

    assert before == after == 0.90
    assert relaxed["top30_observable"] == 23
    assert not bool(relaxed["top30_metric_admitted"])
    assert np.isnan(relaxed["top30_mean_realized_percentile"])
    assert bool(relaxed["ic_admitted"])
    assert np.isfinite(relaxed["daily_ic"])
