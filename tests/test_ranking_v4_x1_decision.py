from __future__ import annotations

import json
from pathlib import Path

from idx_trade.ranking_v4_x1_decision import (
    decide_v4_x1,
    evaluate_absolute_confirmation,
    evaluate_incremental_confirmation,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "ranking_v4_x1_prospective_preregistration_v1.json"


def _config() -> dict[str, object]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _absolute_aggregate(*, mean_ic: float, q25: float, top: float, spread: float) -> dict[str, object]:
    return {
        "all_primary_metrics_valid": True,
        "valid_20session_ic_block_count": 5,
        "mean_daily_ic": mean_ic,
        "q25_20session_block_mean_daily_ic": q25,
        "positive_20session_block_count": 5,
        "mean_top30_realized_percentile": top,
        "mean_top30_bottom30_spread": spread,
    }


def _delta_aggregate(*, mean_ic: float, q25: float, top: float, spread: float) -> dict[str, object]:
    return {
        "all_paired_primary_metrics_valid": True,
        "valid_20session_ic_delta_block_count": 5,
        "mean_ic_delta": mean_ic,
        "q25_20session_block_mean_ic_delta": q25,
        "positive_20session_block_ic_delta_count": 5,
        "mean_top30_delta": top,
        "mean_spread_delta": spread,
    }


def test_exact_frozen_thresholds_can_confirm_geometry3() -> None:
    cfg = _config()
    h5 = evaluate_absolute_confirmation(
        head="H5",
        aggregate=_absolute_aggregate(mean_ic=0.015, q25=0.0, top=0.51, spread=0.02),
        preregistration=cfg,
    )
    h10 = evaluate_absolute_confirmation(
        head="H10",
        aggregate=_absolute_aggregate(mean_ic=0.015, q25=0.0, top=0.51, spread=0.02),
        preregistration=cfg,
    )
    consensus = evaluate_absolute_confirmation(
        head="CONSENSUS",
        aggregate=_absolute_aggregate(mean_ic=0.025, q25=0.01, top=0.52, spread=0.04),
        preregistration=cfg,
        bootstrap_ci=(0.0001, 0.05),
    )
    assert h5["pass"] is True
    assert h10["pass"] is True
    assert consensus["pass"] is True

    incremental = evaluate_incremental_confirmation(
        consensus_delta=_delta_aggregate(mean_ic=0.005, q25=0.0, top=0.005, spread=0.01),
        h5_delta=_delta_aggregate(mean_ic=0.0, q25=-0.005, top=0.0, spread=0.0),
        h10_delta=_delta_aggregate(mean_ic=0.0, q25=-0.005, top=0.0, spread=0.0),
        challenger_absolute_pass=True,
        preregistration=cfg,
        consensus_bootstrap_delta_ci=(0.0001, 0.02),
    )
    assert incremental["pass"] is True
    assert decide_v4_x1(
        challenger_consensus_absolute=consensus,
        challenger_h5_absolute=h5,
        challenger_h10_absolute=h10,
        incremental=incremental,
    ) == "V4_X1_GEOMETRY3_PROSPECTIVE_CONFIRMED"


def test_missing_portfolio_admissibility_cannot_be_rescued_by_strong_ic() -> None:
    cfg = _config()
    aggregate = _absolute_aggregate(mean_ic=0.20, q25=0.15, top=0.70, spread=0.20)
    aggregate["all_primary_metrics_valid"] = False
    consensus = evaluate_absolute_confirmation(
        head="CONSENSUS",
        aggregate=aggregate,
        preregistration=cfg,
        bootstrap_ci=(0.10, 0.25),
    )
    assert consensus["pass"] is False
    assert consensus["gates"]["all_primary_metrics_valid"] is False


def test_incremental_confirmation_requires_challenger_absolute_pass() -> None:
    cfg = _config()
    excellent = _delta_aggregate(mean_ic=0.10, q25=0.08, top=0.05, spread=0.10)
    result = evaluate_incremental_confirmation(
        consensus_delta=excellent,
        h5_delta=excellent,
        h10_delta=excellent,
        challenger_absolute_pass=False,
        preregistration=cfg,
        consensus_bootstrap_delta_ci=(0.05, 0.15),
    )
    assert result["pass"] is False
    assert result["gates"]["challenger_absolute_pass"] is False
