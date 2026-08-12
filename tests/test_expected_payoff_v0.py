from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.expected_payoff_v0 import (
    MAX_ALLOWED_DATE,
    build_payoff_rows,
    compute_metrics,
    session_deciles,
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
