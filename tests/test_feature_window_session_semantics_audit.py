from __future__ import annotations

import pandas as pd

from idx_trade.feature_window_session_semantics_audit import (
    build_session_span_state,
    subset_state,
    summarize_support,
)


def test_contiguous_rows_have_nominal_exchange_session_horizons() -> None:
    sessions = pd.date_range("2026-01-01", periods=80, freq="D")
    panel = pd.DataFrame({"ticker": "AAAA", "date": sessions})
    state = build_session_span_state(panel, sessions)
    last = state.iloc[-1]
    assert last["lag5_effective_sessions"] == 5
    assert last["lag20_effective_sessions"] == 20
    assert last["atr14_effective_sessions"] == 14
    assert last["rolling20_effective_sessions"] == 20
    assert last["rolling60_effective_sessions"] == 60


def test_gap_extends_observed_row_windows_in_exchange_time() -> None:
    sessions = pd.date_range("2026-01-01", periods=80, freq="D")
    kept = sessions.delete([20, 21, 22, 23, 24])
    panel = pd.DataFrame({"ticker": "AAAA", "date": kept})
    state = build_session_span_state(panel, sessions)
    after_gap = state[state["date"].eq(sessions[25])].iloc[0]
    assert after_gap["lag5_effective_sessions"] == 10
    assert after_gap["rolling20_effective_sessions"] == 25


def test_summary_distinguishes_extended_and_unavailable_rows() -> None:
    sessions = pd.date_range("2026-01-01", periods=70, freq="D")
    kept = sessions.delete([10, 11])
    panel = pd.DataFrame({"ticker": "AAAA", "date": kept})
    state = build_session_span_state(panel, sessions)
    summary = summarize_support(state)
    assert summary["windows"]["lag5"]["unavailable_rows"] == 5
    assert summary["windows"]["rolling60"]["unavailable_rows"] == 59
    assert summary["windows"]["lag5"]["extended_rows"] > 0
    assert summary["windows"]["rolling20"]["extended_rows"] > 0


def test_subset_state_requires_all_support_keys_in_panel() -> None:
    sessions = pd.date_range("2026-01-01", periods=10, freq="D")
    panel = pd.DataFrame({"ticker": "AAAA", "date": sessions})
    state = build_session_span_state(panel, sessions)
    keys = pd.DataFrame({"ticker": ["AAAA"], "date": [sessions[-1]]})
    out = subset_state(state, keys, "TEST")
    assert len(out) == 1
    assert out.iloc[0]["session_index"] == 9
