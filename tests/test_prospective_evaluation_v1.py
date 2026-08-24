from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from idx_trade.prospective_evaluation_v1 import (
    BOOTSTRAP_REPLICATES,
    BOOTSTRAP_SEED,
    MODEL_FINGERPRINT,
    MODEL_GENERATION,
    MODEL_NAME,
    ProspectiveEvaluationBlocked,
    alpha_verdict,
    deterministic_rank,
    economic_verdict,
    evaluate_alpha_metrics,
    evaluate_benchmark,
    evaluate_pending_orders,
    evaluate_portfolio_metrics,
    evaluate_prospective_v1,
    evaluate_turnover,
    max_drawdown_metrics,
    moving_block_bootstrap_distribution,
    nav_daily_returns,
    overall_verdict,
    spearman_rank_correlation,
    validate_alpha_session_alignment,
    validate_development_identity,
    validate_exclusion_ledger,
)


def _dates(n: int) -> pd.DatetimeIndex:
    return pd.date_range("2026-01-02", periods=n, freq="B")


def _alpha_fixture(session_count: int = 10, ticker_count: int = 12) -> pd.DataFrame:
    rows = []
    for session_no, date in enumerate(_dates(session_count)):
        for ticker_no in range(ticker_count):
            score = float(ticker_count - ticker_no) + session_no * 1e-4
            target = score * 0.01 + session_no * 1e-5
            rows.append(
                {
                    "session_date": date,
                    "session_index": 1000 + session_no,
                    "ticker": f"T{ticker_no:03d}",
                    "alpha_consensus": score,
                    "canonical_target": target,
                }
            )
    return pd.DataFrame(rows)


def _nav_fixture(n: int = 11) -> pd.DataFrame:
    returns = np.array([0.01, -0.005, 0.007, -0.002, 0.004, 0.003, -0.004, 0.006, 0.002, 0.005])
    if n != 11:
        returns = np.resize(returns, n - 1)
    nav = [100.0]
    for value in returns:
        nav.append(nav[-1] * (1.0 + value))
    return pd.DataFrame({"session_date": _dates(n), "nav": nav})


def _session_inventory(n: int = 10) -> pd.DataFrame:
    return pd.DataFrame({"session_date": _dates(n), "session_index": np.arange(1000, 1000 + n)})


def _ledger(n: int = 10, state: str = "EVALUABLE") -> pd.DataFrame:
    sessions = _session_inventory(n)
    return sessions.assign(state=state, reason="")


def test_spearman_perfect_positive_negative_and_ties() -> None:
    assert spearman_rank_correlation([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert spearman_rank_correlation([1, 2, 3, 4], [40, 30, 20, 10]) == pytest.approx(-1.0)
    tied = spearman_rank_correlation([1, 1, 2, 3], [10, 10, 20, 30])
    assert tied == pytest.approx(1.0)


def test_spearman_constant_input_fails_closed() -> None:
    with pytest.raises(ProspectiveEvaluationBlocked, match="constant"):
        spearman_rank_correlation([1, 1, 1], [1, 2, 3])


def test_deterministic_rank_uses_score_desc_ticker_asc_tiebreak() -> None:
    frame = pd.DataFrame(
        {
            "session_date": ["2026-01-02"] * 3,
            "ticker": ["BBB", "AAA", "CCC"],
            "alpha_consensus": [1.0, 1.0, 0.5],
            "canonical_target": [0.1, 0.2, -0.1],
        }
    )
    ranked = deterministic_rank(frame)
    assert ranked["ticker"].tolist() == ["AAA", "BBB", "CCC"]
    assert ranked["rank"].tolist() == [1, 2, 3]


def test_alpha_metrics_use_session_level_ic_and_frozen_bootstrap() -> None:
    result = evaluate_alpha_metrics(_alpha_fixture())
    assert result["session_count"] == 10
    assert result["mean_ic"] == pytest.approx(1.0)
    assert result["median_ic"] == pytest.approx(1.0)
    assert result["positive_ic_fraction"] == pytest.approx(1.0)
    assert result["bootstrap_ci_95"] == pytest.approx([1.0, 1.0])
    assert result["bootstrap_nonfinite_replicates"] == 0


def test_moving_block_bootstrap_is_deterministic_and_parameters_are_frozen() -> None:
    values = np.linspace(-0.03, 0.04, 20)
    first, first_bad = moving_block_bootstrap_distribution(values, lambda x: float(np.mean(x)))
    second, second_bad = moving_block_bootstrap_distribution(values, lambda x: float(np.mean(x)))
    assert first_bad == second_bad == 0
    assert np.array_equal(first, second)
    assert len(first) == BOOTSTRAP_REPLICATES

    with pytest.raises(ProspectiveEvaluationBlocked, match="seed"):
        moving_block_bootstrap_distribution(values, lambda x: float(np.mean(x)), seed=BOOTSTRAP_SEED + 1)


def test_nav_daily_returns_and_total_return_are_exact() -> None:
    nav = pd.DataFrame(
        {
            "session_date": _dates(6),
            "nav": [100.0, 110.0, 99.0, 108.9, 108.9, 108.9],
        }
    )
    daily = nav_daily_returns(nav)
    assert daily["daily_return"].tolist() == pytest.approx([0.10, -0.10, 0.10, 0.0, 0.0])
    metrics = evaluate_portfolio_metrics(nav)
    assert metrics["net_total_return"] == pytest.approx(0.089)


def test_portfolio_vol_sharpe_sortino_match_frozen_formulas() -> None:
    nav = _nav_fixture()
    metrics = evaluate_portfolio_metrics(nav)
    returns = nav["nav"].pct_change(fill_method=None).dropna().to_numpy(dtype=float)
    expected_std = np.std(returns, ddof=1)
    expected_vol = expected_std * np.sqrt(252)
    expected_sharpe = np.mean(returns) / expected_std * np.sqrt(252)
    downside = np.minimum(returns, 0.0)
    expected_sortino = np.mean(returns) / np.sqrt(np.mean(downside**2)) * np.sqrt(252)
    assert metrics["annualized_volatility"] == pytest.approx(expected_vol)
    assert metrics["sharpe_0"] == pytest.approx(expected_sharpe)
    assert metrics["sortino_0"] == pytest.approx(expected_sortino)


def test_max_drawdown_tracks_peak_trough_and_recovery() -> None:
    nav = pd.DataFrame(
        {
            "session_date": _dates(5),
            "nav": [100.0, 120.0, 90.0, 100.0, 121.0],
        }
    )
    result = max_drawdown_metrics(nav)
    assert result["max_drawdown"] == pytest.approx(-0.25)
    assert result["peak_date"] == _dates(5)[1].date().isoformat()
    assert result["trough_date"] == _dates(5)[2].date().isoformat()
    assert result["recovered"] is True
    assert result["recovery_date"] == _dates(5)[4].date().isoformat()


def test_turnover_uses_gross_buys_plus_sells_over_prior_nav() -> None:
    frame = pd.DataFrame(
        {
            "session_date": _dates(2),
            "gross_buy_notional": [10.0, 5.0],
            "gross_sell_notional": [5.0, 15.0],
            "nav_prev": [100.0, 200.0],
        }
    )
    result = evaluate_turnover(frame)
    assert result["daily"]["turnover"].tolist() == pytest.approx([0.15, 0.10])
    assert result["aggregate_turnover"] == pytest.approx(0.25)


def test_pending_rate_keeps_legitimate_unavailable_open_in_denominator() -> None:
    orders = pd.DataFrame(
        {
            "requires_open_decision": [True, True, True, False],
            "pending_due_to_unavailable_open": [True, False, True, False],
        }
    )
    result = evaluate_pending_orders(orders)
    assert result["prepared_open_leg_count"] == 3
    assert result["pending_open_leg_count"] == 2
    assert result["pending_order_rate"] == pytest.approx(2 / 3)

    bad = orders.copy()
    bad.loc[3, "pending_due_to_unavailable_open"] = True
    with pytest.raises(ProspectiveEvaluationBlocked, match="denominator"):
        evaluate_pending_orders(bad)


def test_benchmark_must_align_exact_strategy_start_and_end() -> None:
    nav = _nav_fixture()
    dates = nav["session_date"]
    benchmark = pd.DataFrame(
        {
            "session_date": dates,
            "benchmark_close": np.linspace(1000.0, 1050.0, len(dates)),
        }
    )
    result = evaluate_benchmark(nav, benchmark)
    expected_strategy = nav.iloc[-1]["nav"] / nav.iloc[0]["nav"] - 1.0
    assert result["benchmark_return"] == pytest.approx(0.05)
    assert result["net_excess_return_vs_benchmark"] == pytest.approx(expected_strategy - 0.05)

    missing_end = benchmark.iloc[:-1].copy()
    with pytest.raises(ProspectiveEvaluationBlocked, match="align"):
        evaluate_benchmark(nav, missing_end)


def test_exclusion_ledger_requires_exact_coverage_and_known_states() -> None:
    expected = _session_inventory()
    valid = validate_exclusion_ledger(_ledger(), expected)
    assert len(valid) == len(expected)

    missing = _ledger().iloc[:-1].copy()
    with pytest.raises(ProspectiveEvaluationBlocked, match="exactly cover"):
        validate_exclusion_ledger(missing, expected)

    invalid = _ledger()
    invalid.loc[0, "state"] = "MAGIC_EXCLUSION"
    with pytest.raises(ProspectiveEvaluationBlocked, match="invalid states"):
        validate_exclusion_ledger(invalid, expected)


def test_alpha_session_alignment_requires_exact_date_index_inventory() -> None:
    alpha = _alpha_fixture()
    expected = _session_inventory()
    aligned = validate_alpha_session_alignment(alpha, expected)
    assert len(aligned) == len(expected)

    missing = alpha.loc[alpha["session_index"] != expected.iloc[-1]["session_index"]].copy()
    with pytest.raises(ProspectiveEvaluationBlocked, match="exactly align"):
        validate_alpha_session_alignment(missing, expected)

    wrong_index = alpha.copy()
    wrong_index.loc[wrong_index["session_date"].eq(_dates(10)[0]), "session_index"] = 9999
    with pytest.raises(ProspectiveEvaluationBlocked, match="exactly align"):
        validate_alpha_session_alignment(wrong_index, expected)


def test_rank_bucket_and_top_k_are_session_aggregated() -> None:
    result = evaluate_alpha_metrics(_alpha_fixture(session_count=10, ticker_count=25))
    assert result["rank_buckets"]["RANK_1_10"]["session_count"] == 10
    assert result["rank_buckets"]["RANK_1_10"]["row_count"] == 100
    assert result["top_k"]["TOP_10"]["session_count"] == 10
    assert result["top_k"]["TOP_20"]["session_count"] == 10
    assert result["top_k"]["TOP_10"]["mean"] > result["top_k"]["TOP_20"]["mean"]


def test_verdict_boundaries_are_frozen() -> None:
    assert alpha_verdict(mean_ic=0.05, ci_low=0.01) == "ALPHA_CONFIRMED_POSITIVE"
    assert alpha_verdict(mean_ic=0.05, ci_low=-0.01) == "ALPHA_DIRECTIONALLY_POSITIVE"
    assert alpha_verdict(mean_ic=0.0, ci_low=-0.01) == "ALPHA_FAIL"

    assert economic_verdict(net_total_return=0.05, sharpe_0=0.5) == "ECONOMIC_POSITIVE"
    assert economic_verdict(net_total_return=0.05, sharpe_0=-0.1) == "ECONOMIC_MIXED"
    assert economic_verdict(net_total_return=-0.05, sharpe_0=-0.5) == "ECONOMIC_FAIL"

    assert (
        overall_verdict(
            operational_valid=True,
            alpha="ALPHA_CONFIRMED_POSITIVE",
            economics="ECONOMIC_POSITIVE",
            execution="EXECUTION_HEALTHY",
        )
        == "PROSPECTIVE_PASS"
    )
    assert (
        overall_verdict(
            operational_valid=True,
            alpha="ALPHA_FAIL",
            economics="ECONOMIC_MIXED",
            execution="EXECUTION_HEALTHY",
        )
        == "PROSPECTIVE_FAIL"
    )
    assert (
        overall_verdict(
            operational_valid=False,
            alpha="ALPHA_CONFIRMED_POSITIVE",
            economics="ECONOMIC_POSITIVE",
            execution="EXECUTION_HEALTHY",
        )
        == "PROSPECTIVE_INVALID_OPERATIONAL"
    )


def test_development_identity_refuses_protected_data_and_ambiguous_target() -> None:
    common = dict(
        model_name=MODEL_NAME,
        model_generation=MODEL_GENERATION,
        model_fingerprint=MODEL_FINGERPRINT,
        canonical_target_id="SYNTHETIC_CANONICAL_TARGET",
        canonical_target_resolved=True,
    )
    validate_development_identity(data_classification="SYNTHETIC", **common)

    with pytest.raises(ProspectiveEvaluationBlocked, match="protected prospective"):
        validate_development_identity(data_classification="PROTECTED_PROSPECTIVE", **common)

    ambiguous = dict(common)
    ambiguous["canonical_target_resolved"] = False
    with pytest.raises(ProspectiveEvaluationBlocked, match="ambiguous"):
        validate_development_identity(data_classification="SYNTHETIC", **ambiguous)

    wrong_model = dict(common)
    wrong_model["model_fingerprint"] = "0" * 64
    with pytest.raises(ProspectiveEvaluationBlocked, match="fingerprint"):
        validate_development_identity(data_classification="SYNTHETIC", **wrong_model)


def test_end_to_end_synthetic_engine_does_not_need_protected_outcomes() -> None:
    alpha = _alpha_fixture()
    nav = _nav_fixture()
    expected = _session_inventory()
    ledger = _ledger()
    benchmark = pd.DataFrame(
        {
            "session_date": nav["session_date"],
            "benchmark_close": np.linspace(1000.0, 1010.0, len(nav)),
        }
    )
    execution = pd.DataFrame(
        {
            "session_date": _dates(10),
            "gross_buy_notional": [5.0] * 10,
            "gross_sell_notional": [4.0] * 10,
            "nav_prev": [100.0] * 10,
        }
    )
    orders = pd.DataFrame(
        {
            "requires_open_decision": [True, True, False],
            "pending_due_to_unavailable_open": [False, True, False],
        }
    )

    result = evaluate_prospective_v1(
        alpha_frame=alpha,
        nav_frame=nav,
        ledger=ledger,
        expected_sessions=expected,
        data_classification="SYNTHETIC",
        canonical_target_id="SYNTHETIC_CANONICAL_TARGET",
        canonical_target_resolved=True,
        execution_frame=execution,
        order_frame=orders,
        benchmark_frame=benchmark,
    )
    assert result["data_classification"] == "SYNTHETIC"
    assert result["alpha"]["mean_ic"] == pytest.approx(1.0)
    assert result["verdicts"]["alpha"] == "ALPHA_CONFIRMED_POSITIVE"
    assert result["verdicts"]["execution"] == "EXECUTION_HEALTHY"
    assert result["diagnostics"]["pending_orders"]["pending_order_rate"] == pytest.approx(0.5)
    assert result["verdicts"]["overall"] in {"PROSPECTIVE_PASS", "PROSPECTIVE_MIXED"}


def test_sortino_without_negative_returns_is_infinite_by_frozen_convention() -> None:
    nav = pd.DataFrame({"session_date": _dates(7), "nav": [100, 101, 102, 103, 104, 105, 106]})
    metrics = evaluate_portfolio_metrics(nav)
    assert math.isinf(metrics["sortino_0"])
