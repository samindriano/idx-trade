from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from idx_trade.ranking_v4_3_target_execution import TARGET_BOTH_AVAILABLE
from idx_trade import ranking_v4_3_model_eval as parent_eval
from idx_trade.ranking_v4_x1_eval import (
    MIN_ADMITTED_DATES,
    MIN_ADMITTED_DATES_PER_BLOCK,
    PROSPECTIVE_WINDOW_SESSIONS,
    SUPPORT_RATE,
    TOP_K,
    TOP_K_MIN_OBSERVABLE,
    attach_prospective_window,
    evaluate_head_by_date_x1,
    moving_block_bootstrap_mean_x1,
    summarize_x1_metrics,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "ranking_v4_x1_prospective_preregistration_v1.json"


def _consensus_day(*, top_observable: int, bottom_observable: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not 0 <= top_observable <= 30 or not 0 <= bottom_observable <= 30:
        raise ValueError("observable counts must be within 0..30")
    date = pd.Timestamp("2030-01-02")
    tickers = [f"T{i:02d}" for i in range(60)]
    alpha = np.linspace(0.0, 1.0, 60)
    scores = pd.DataFrame(
        {"ticker": tickers, "date": date, "alpha_consensus": alpha}
    )

    available = set(tickers[:bottom_observable])
    available.update(tickers[60 - top_observable :])
    ranks = np.linspace(0.0, 1.0, 60)
    ledger = pd.DataFrame(
        {
            "ticker": tickers,
            "date": date,
            "target_state_consensus": [
                TARGET_BOTH_AVAILABLE if ticker in available else "UNAVAILABLE"
                for ticker in tickers
            ],
            "realized_consensus": [
                float(ranks[i]) if ticker in available else np.nan
                for i, ticker in enumerate(tickers)
            ],
        }
    )
    return scores, ledger


def test_preregistration_is_mechanically_aligned_at_80pct() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    obs = config["observability_contract"]
    assert config["generation_id"] == "V4_X1_GEOMETRY3_PROSPECTIVE"
    assert obs["support_rate"] == SUPPORT_RATE == 0.8
    assert obs["top_k"] == TOP_K == 30
    assert obs["top_k_min_observable"] == TOP_K_MIN_OBSERVABLE == 24
    assert obs["minimum_admitted_dates_per_primary_metric"] == MIN_ADMITTED_DATES == 80
    assert obs["minimum_admitted_dates_per_robustness_block"] == MIN_ADMITTED_DATES_PER_BLOCK == 16
    assert obs["minimum_valid_robustness_blocks"] == 4
    assert config["model_freeze"]["required_final_refit_fit_count"] == 4
    assert config["prospective_boundary"]["fresh_only"] is True
    assert config["prospective_boundary"]["interim_outcome_peeking"] is False
    assert config["scientific_parent"]["historical_verdict"] == "V4_3R_GENERATION_NO_SURVIVOR"


def test_x1_accepts_exact_24_of_30_without_refill() -> None:
    scores, ledger = _consensus_day(top_observable=24, bottom_observable=24)
    result = evaluate_head_by_date_x1(scores, ledger, head="CONSENSUS")
    row = result.iloc[0]
    assert row["target_observable_rows"] == 48
    assert row["target_coverage_rate"] == 0.8
    assert bool(row["date_metric_admitted"]) is True
    assert row["top30_observable"] == 24
    assert row["bottom30_observable"] == 24
    assert bool(row["top30_metric_admitted"]) is True
    assert bool(row["spread_metric_admitted"]) is True


def test_x1_rejects_23_of_30_top_even_when_date_coverage_is_80pct() -> None:
    scores, ledger = _consensus_day(top_observable=23, bottom_observable=25)
    result = evaluate_head_by_date_x1(scores, ledger, head="CONSENSUS")
    row = result.iloc[0]
    assert row["target_observable_rows"] == 48
    assert row["target_coverage_rate"] == 0.8
    assert bool(row["date_metric_admitted"]) is True
    assert row["top30_observable"] == 23
    assert row["bottom30_observable"] == 25
    assert bool(row["top30_metric_admitted"]) is False
    assert bool(row["spread_metric_admitted"]) is False


def test_parent_v4_gates_are_restored_after_x1_overlay() -> None:
    scores, ledger = _consensus_day(top_observable=24, bottom_observable=24)
    evaluate_head_by_date_x1(scores, ledger, head="CONSENSUS")
    assert parent_eval.DATE_TARGET_COVERAGE_GATE == 0.90
    assert parent_eval.TOP_K_MIN_OBSERVABLE == 27
    assert parent_eval.TOP_K == 30


def _window_metrics(*, finite_dates: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2030-01-01", periods=PROSPECTIVE_WINDOW_SESSIONS)
    sessions = pd.DataFrame(
        {
            "prospective_index": np.arange(1, PROSPECTIVE_WINDOW_SESSIONS + 1),
            "date": dates,
        }
    )
    finite = np.arange(PROSPECTIVE_WINDOW_SESSIONS) < finite_dates
    metrics = pd.DataFrame(
        {
            "date": dates,
            "head": "CONSENSUS",
            "ic_admitted": finite,
            "top30_metric_admitted": finite,
            "spread_metric_admitted": finite,
            "daily_ic": np.where(finite, 0.05, np.nan),
            "top30_mean_realized_percentile": np.where(finite, 0.55, np.nan),
            "top30_bottom30_spread": np.where(finite, 0.06, np.nan),
        }
    )
    return sessions, metrics


def test_x1_window_accepts_80_of_100_metric_dates() -> None:
    sessions, metrics = _window_metrics(finite_dates=80)
    window = attach_prospective_window(metrics, sessions)
    blocks, aggregate = summarize_x1_metrics(window)
    assert aggregate["all_primary_metrics_valid"] is True
    assert aggregate["ic_admitted_dates"] == 80
    assert aggregate["top30_admitted_dates"] == 80
    assert aggregate["spread_admitted_dates"] == 80
    assert aggregate["valid_20session_ic_block_count"] == 4
    assert aggregate["positive_20session_block_count"] == 4
    assert blocks["block_ic_valid"].tolist() == [True, True, True, True, False]
    bootstrap = moving_block_bootstrap_mean_x1(window, replications=50, seed=42)
    assert np.isfinite(bootstrap).all()


def test_x1_window_rejects_79_of_100_metric_dates() -> None:
    sessions, metrics = _window_metrics(finite_dates=79)
    window = attach_prospective_window(metrics, sessions)
    _, aggregate = summarize_x1_metrics(window)
    assert aggregate["window_ic_valid"] is False
    assert aggregate["window_top30_valid"] is False
    assert aggregate["window_spread_valid"] is False
    assert aggregate["all_primary_metrics_valid"] is False
