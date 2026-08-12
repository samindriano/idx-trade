from __future__ import annotations

import json

import pandas as pd
import pytest

from idx_trade.expected_payoff_v0 import (
    MAX_ALLOWED_DATE,
    PayoffDataBlocked,
    build_payoff_rows,
    compute_metrics,
    evaluate_gates,
    load_parent_predictions,
    protected_runtime_flags,
    sha256_file,
    session_deciles,
    validate_parent_historical_dates,
    write_post_review_diagnostics,
)


def _calendar() -> pd.DataFrame:
    return pd.DataFrame({"date": pd.to_datetime(["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-06", "2026-07-07", "2026-07-08", "2026-07-09", "2026-07-10", "2026-07-13", "2026-07-14", "2026-07-15", "2026-07-16"])}) .assign(session_index=range(1, 13))


def _inputs():
    calendar = _calendar()
    parent = pd.DataFrame({"model": ["O2_OPEN_GEOMETRY"], "fold": ["V2F1"], "ticker": ["AAA"], "date": [pd.Timestamp("2026-07-01")], "signal_session_index": [1], "score": [0.8]})
    features = pd.DataFrame({"ticker": ["AAA"], "date": [pd.Timestamp("2026-07-01")], "signal_session_index": [1], "atr14_over_close": [0.1]})
    panel = pd.DataFrame({"ticker": ["AAA", "AAA", "AAA"], "date": pd.to_datetime(["2026-07-01", "2026-07-02", "2026-07-15"]), "close": [100.0, 101.0, 110.0], "high": [101.0, 102.0, 111.0], "low": [99.0, 100.0, 109.0], "volume": [10, 10, 10], "regular_market_value": [1000, 1000, 1100], "corporate_action_integrity_verified": [True, True, True]})
    open_panel = pd.DataFrame({"ticker": ["AAA"], "date": [pd.Timestamp("2026-07-02")], "open": [101.0]})
    open_prov = pd.DataFrame({"ticker": ["AAA"], "date": [pd.Timestamp("2026-07-02")], "validation_status": ["ACCEPTED"], "open_source": ["TEST"], "source_cache_ref": ["fixture"], "source_raw_sha256": ["sha"]})
    tradability = pd.DataFrame({"ticker": ["AAA", "AAA"], "date": pd.to_datetime(["2026-07-02", "2026-07-15"]), "state": ["ACTIVE", "ACTIVE"], "market": ["REGULAR", "REGULAR"]})
    actions = pd.DataFrame({"ticker": pd.Series(dtype=str), "date": pd.Series(dtype="datetime64[ns]"), "action": pd.Series(dtype=str)})
    return parent, features, calendar, panel, open_panel, open_prov, tradability, actions


def test_signal_maps_to_next_open_and_tenth_session_close_without_signal_close_entry():
    inputs = _inputs()
    ledger, resolved = build_payoff_rows(*inputs)
    row = resolved.iloc[0]
    assert row.entry_date == pd.Timestamp("2026-07-02")
    assert row.exit_date == pd.Timestamp("2026-07-15")
    assert row.entry_open == 101.0
    assert row.exit_close == 110.0
    assert row.atr14 == 10.0
    assert row.payoff_atr_gross == 0.9
    assert row.entry_gap_pct == pytest.approx(0.01)
    assert ledger.status.tolist() == ["RESOLVED"]


def test_missing_open_is_excluded_without_fill():
    inputs = list(_inputs())
    inputs[5] = inputs[5].iloc[0:0]
    ledger, resolved = build_payoff_rows(*inputs)
    assert resolved.empty
    assert ledger.exclusion_reason.iloc[0] == "MISSING_ACCEPTED_OPEN"


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ("missing", "MISSING_EXIT_CLOSE"),
        ("invalid", "INVALID_EXIT_CLOSE"),
    ],
)
def test_missing_or_invalid_exit_close_is_excluded_without_fill(mutation, reason):
    inputs = list(_inputs())
    panel = inputs[3].copy()
    if mutation == "missing":
        panel = panel.loc[panel.date != pd.Timestamp("2026-07-15")]
    else:
        panel.loc[panel.date == pd.Timestamp("2026-07-15"), "close"] = 0.0
    inputs[3] = panel
    ledger, resolved = build_payoff_rows(*inputs)
    assert resolved.empty
    assert ledger.exclusion_reason.iloc[0] == reason


def test_price_scale_action_crossing_is_fail_closed():
    inputs = list(_inputs())
    inputs[-1] = pd.DataFrame({"ticker": ["AAA"], "date": [pd.Timestamp("2026-07-05")], "action": ["stockSplit"]})
    ledger, resolved = build_payoff_rows(*inputs)
    assert resolved.empty
    assert ledger.exclusion_reason.iloc[0] == "PRICE_SCALE_CA_CROSSED"


def test_deterministic_deciles_resolve_score_ties_by_ticker():
    frame = pd.DataFrame({"ticker": ["B", "A", "C"], "score": [1.0, 1.0, 0.0]})
    first = session_deciles(frame)
    second = session_deciles(frame.sample(frac=1, random_state=9))
    assert first.sort_values("ticker").decile.tolist() == second.sort_values("ticker").decile.tolist()


def test_compute_metrics_requires_nonconstant_score_and_payoff():
    rows = pd.DataFrame({"fold": ["V2F1", "V2F1"], "signal_date": pd.to_datetime(["2026-07-01", "2026-07-01"]), "ticker": ["A", "B"], "score": [1.0, 1.0], "payoff_atr_gross": [0.1, 0.2], "payoff_pct_gross": [0.1, 0.2]})
    sessions, fold_metrics, _ = compute_metrics(rows)
    assert not sessions.iloc[0].eligible
    assert fold_metrics.loc[fold_metrics.fold.eq("V2F1"), "eligible_signal_sessions"].iloc[0] == 0


def test_cutoff_is_frozen():
    assert str(MAX_ALLOWED_DATE.date()) == "2026-07-31"


def test_behavioral_cutoff_rejects_post_cutoff_parent():
    parent = pd.DataFrame({"date": [pd.Timestamp("2026-08-01")]})
    with pytest.raises(PayoffDataBlocked, match="frozen cutoff"):
        validate_parent_historical_dates(parent)


def _boundary_fold_metrics(ic=0.01, spread=0.01, coverage=0.85, sessions=80):
    return pd.DataFrame(
        {
            "fold": [f"V2F{i}" for i in range(1, 7)],
            "coverage_ratio": [coverage] * 6,
            "eligible_signal_sessions": [sessions] * 6,
            "median_session_ic_atr": [ic] * 6,
            "mean_d10_minus_d1_mean_payoff_atr": [spread] * 6,
        }
    )


def test_readiness_gate_accepts_exact_boundary_and_strict_feasibility_gate():
    result = evaluate_gates(
        parent_rows=100,
        resolved_rows=90,
        fold_metrics=_boundary_fold_metrics(),
        parent_key_sha="same",
        expected_parent_key_sha="same",
    )
    assert result["data_ready"] is True
    assert result["verdict"] == "EXPECTED_PAYOFF_V0_FEASIBILITY_GO"

    no_signal = evaluate_gates(
        parent_rows=100,
        resolved_rows=90,
        fold_metrics=_boundary_fold_metrics(ic=0.0),
        parent_key_sha="same",
        expected_parent_key_sha="same",
    )
    assert no_signal["verdict"] == "EXPECTED_PAYOFF_V0_NO_SIGNAL"


def test_feasibility_gate_requires_four_positive_spread_folds():
    spreads = [0.01, 0.01, 0.01, -0.01, -0.01, -0.01]
    metrics = _boundary_fold_metrics()
    metrics["mean_d10_minus_d1_mean_payoff_atr"] = spreads
    result = evaluate_gates(
        parent_rows=100,
        resolved_rows=90,
        fold_metrics=metrics,
        parent_key_sha="same",
        expected_parent_key_sha="same",
    )
    assert result["data_ready"] is True
    assert result["positive_spread_folds"] == 3
    assert result["verdict"] == "EXPECTED_PAYOFF_V0_NO_SIGNAL"


def test_accepted_o2_scores_are_consumed_exactly(tmp_path):
    frame = pd.DataFrame(
        {
            "model": ["O2_OPEN_GEOMETRY"] * 6,
            "fold": [f"V2F{i}" for i in range(1, 7)],
            "ticker": ["AAA"] * 6,
            "date": pd.date_range("2023-06-23", periods=6),
            "signal_session_index": range(525, 531),
            "score": [0.17, -0.23, 1.04, 0.0, -1.2, 0.88],
        }
    )
    path = tmp_path / "fold_predictions.parquet"
    frame.to_parquet(path, index=False)
    loaded = load_parent_predictions(path, sha256_file(path))
    assert loaded.score.tolist() == frame.score.tolist()


def test_protected_forward_runtime_flags_are_explicitly_false():
    flags = protected_runtime_flags()
    assert flags == {
        "fresh_forward_outcomes_accessed": False,
        "forward_outcome_access_marker_written": False,
        "provider_calls": False,
        "o2_model_modified": False,
        "payoff_model_fit": False,
    }


def test_post_review_diagnostics_persist_fold_quantiles_and_monotonicity(tmp_path):
    rows = []
    for fold_number in range(1, 7):
        for ticker_number in range(30):
            rows.append(
                {
                    "fold": f"V2F{fold_number}",
                    "signal_date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=fold_number),
                    "ticker": f"T{ticker_number:02d}",
                    "score": float(ticker_number),
                    "payoff_atr_gross": float(ticker_number) / 10,
                    "payoff_pct_gross": float(ticker_number) / 100,
                }
            )
    pd.DataFrame(rows).to_parquet(tmp_path / "resolved_payoff_rows.parquet", index=False)
    (tmp_path / "artifact_manifest.json").write_text(json.dumps({"status": "EXPECTED_PAYOFF_V0_FEASIBILITY_GO"}))
    result = write_post_review_diagnostics(tmp_path)
    assert result["source_verdict"] == "EXPECTED_PAYOFF_V0_FEASIBILITY_GO"
    quantiles = pd.read_csv(tmp_path / "post_review_fold_d1_d10_quantile_summary.csv")
    monotonicity = pd.read_csv(tmp_path / "post_review_decile_monotonicity.csv")
    assert len(quantiles) == 24
    assert set(quantiles.decile) == {1, 10}
    assert len(monotonicity) == 120
    assert monotonicity.monotonic_non_decreasing.all()
