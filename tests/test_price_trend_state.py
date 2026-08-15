from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from idx_trade.price_trend_state import (
    STATE_CONTRACT_VERSION,
    build_price_state_for_source_session,
    build_price_trend_confirmation_state_v1,
)


def _panel(closes: list[float] | np.ndarray, *, volumes: list[float] | np.ndarray | None = None) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    closes = np.asarray(closes, dtype=float)
    dates = pd.bdate_range("2025-01-02", periods=len(closes) + 1)
    if volumes is None:
        volumes = np.full(len(closes), 1_000_000.0)
    volumes = np.asarray(volumes, dtype=float)
    frame = pd.DataFrame(
        {
            "ticker": "TEST",
            "session_date": dates[: len(closes)],
            "raw_high": closes * 1.01,
            "raw_low": closes * 0.99,
            "raw_close": closes,
            "raw_volume": volumes,
        }
    )
    return frame, dates


def test_uptrend_and_long_term_state_are_descriptive() -> None:
    frame, sessions = _panel(np.linspace(50.0, 150.0, 260))
    result = build_price_state_for_source_session(frame, sessions, frame["session_date"].iloc[-1])
    row = result.iloc[0]

    assert row["trend_state"] == "UPTREND"
    assert row["ma_structure_state"] == "BULLISH_STACK"
    assert row["long_term_state"] == "ABOVE_RISING_MA200"
    assert row["state_contract_version"] == STATE_CONTRACT_VERSION
    assert bool(row["outcome_blind"]) is True
    assert bool(row["model_fitted"]) is False
    assert bool(row["trade_recommendation"]) is False


def test_downtrend_is_not_reinterpreted_as_entry_signal() -> None:
    frame, sessions = _panel(np.linspace(150.0, 50.0, 260))
    row = build_price_state_for_source_session(frame, sessions, frame["session_date"].iloc[-1]).iloc[0]

    assert row["trend_state"] == "DOWNTREND"
    assert row["ma_structure_state"] == "BEARISH_STACK"
    assert row["long_term_state"] == "BELOW_FALLING_MA200"


def test_basing_does_not_require_ma200() -> None:
    frame, sessions = _panel(np.full(80, 100.0))
    row = build_price_state_for_source_session(frame, sessions, frame["session_date"].iloc[-1]).iloc[0]

    assert row["trend_state"] == "BASING"
    assert row["long_term_state"] == "UNAVAILABLE"
    assert row["volume_state"] == "NORMAL"
    assert row["volatility_state"] == "NORMAL"


def test_breakout_confirmation_requires_expanded_volume() -> None:
    closes = np.concatenate([np.full(80, 100.0), [105.0]])
    volumes = np.concatenate([np.full(80, 1_000_000.0), [2_000_000.0]])
    frame, sessions = _panel(closes, volumes=volumes)
    row = build_price_state_for_source_session(frame, sessions, frame["session_date"].iloc[-1]).iloc[0]

    assert row["confirmation_state"] == "BREAKOUT_CONFIRMED"
    assert row["volume_state"] == "EXPANDING"
    assert row["source_close"] > row["prior_high_20"]


def test_breakout_without_volume_is_kept_separate() -> None:
    closes = np.concatenate([np.full(80, 100.0), [105.0]])
    frame, sessions = _panel(closes)
    row = build_price_state_for_source_session(frame, sessions, frame["session_date"].iloc[-1]).iloc[0]

    assert row["confirmation_state"] == "BREAKOUT_WEAK_VOLUME"
    assert row["volume_state"] == "NORMAL"


def test_recent_failed_breakout_is_causal() -> None:
    closes = np.concatenate([np.full(80, 100.0), [105.0, 100.0]])
    volumes = np.concatenate([np.full(80, 1_000_000.0), [2_000_000.0, 1_000_000.0]])
    frame, sessions = _panel(closes, volumes=volumes)
    row = build_price_state_for_source_session(frame, sessions, frame["session_date"].iloc[-1]).iloc[0]

    assert row["confirmation_state"] == "FAILED_BREAKOUT_RECENT"
    assert row["recent_breakout_level_5"] == pytest.approx(101.0)


def test_source_t_state_is_invariant_to_target_and_future_data() -> None:
    closes = np.concatenate([np.full(79, 100.0), [105.0]])
    volumes = np.concatenate([np.full(79, 1_000_000.0), [2_000_000.0]])
    frame, sessions = _panel(closes, volumes=volumes)
    source = frame["session_date"].iloc[-1]

    before = build_price_state_for_source_session(frame, sessions, source)

    target = sessions[len(frame)]
    contaminated = pd.concat(
        [
            frame,
            pd.DataFrame(
                [
                    {
                        "ticker": "TEST",
                        "session_date": target,
                        "raw_high": 1000.0,
                        "raw_low": 1.0,
                        "raw_close": 900.0,
                        "raw_volume": 999_000_000.0,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    after = build_price_state_for_source_session(contaminated, sessions, source)

    pd.testing.assert_frame_equal(before, after)
    assert before["feature_session"].iloc[0] == target


def test_outcome_like_columns_are_rejected() -> None:
    frame, sessions = _panel(np.full(80, 100.0))
    frame["binary_target"] = 1
    with pytest.raises(ValueError, match="outcome-like"):
        build_price_trend_confirmation_state_v1(frame, sessions)


def test_duplicate_identity_is_rejected() -> None:
    frame, sessions = _panel(np.full(80, 100.0))
    frame = pd.concat([frame, frame.iloc[[-1]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        build_price_trend_confirmation_state_v1(frame, sessions)


def test_short_history_fails_closed_to_indeterminate() -> None:
    frame, sessions = _panel(np.full(20, 100.0))
    row = build_price_state_for_source_session(frame, sessions, frame["session_date"].iloc[-1]).iloc[0]

    assert row["trend_state"] == "INDETERMINATE"
    assert row["confirmation_state"] == "INDETERMINATE"
    assert row["ma_structure_state"] == "INDETERMINATE"


def test_open_column_is_not_required_by_contract() -> None:
    frame, sessions = _panel(np.full(80, 100.0))
    assert "raw_open" not in frame.columns
    result = build_price_state_for_source_session(frame, sessions, frame["session_date"].iloc[-1])
    assert len(result) == 1


def test_invalid_hlc_fails_closed() -> None:
    frame, sessions = _panel(np.full(80, 100.0))
    frame.loc[frame.index[-1], "raw_low"] = 110.0
    with pytest.raises(ValueError, match="low above high|close outside"):
        build_price_trend_confirmation_state_v1(frame, sessions)
