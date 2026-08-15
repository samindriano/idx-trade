from __future__ import annotations

import numpy as np
import pandas as pd

from idx_trade.price_trend_state import build_price_state_for_source_session


def _panel() -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    closes = np.concatenate([np.full(79, 100.0), [105.0]])
    volumes = np.concatenate([np.full(79, 1_000_000.0), [2_000_000.0]])
    sessions = pd.bdate_range("2025-01-02", periods=len(closes) + 2)
    frame = pd.DataFrame(
        {
            "ticker": "TEST",
            "session_date": sessions[: len(closes)],
            "raw_high": closes * 1.01,
            "raw_low": closes * 0.99,
            "raw_close": closes,
            "raw_volume": volumes,
        }
    )
    return frame, sessions


def test_invalid_future_row_cannot_change_source_state() -> None:
    frame, sessions = _panel()
    source = frame["session_date"].iloc[-1]
    baseline = build_price_state_for_source_session(frame, sessions, source)

    target = sessions[len(frame)]
    future_invalid = pd.DataFrame(
        [
            {
                "ticker": "TEST",
                "session_date": target,
                "raw_high": 90.0,
                "raw_low": 110.0,
                "raw_close": 100.0,
                "raw_volume": 1_000_000.0,
            }
        ]
    )
    contaminated = pd.concat([frame, future_invalid], ignore_index=True)
    observed = build_price_state_for_source_session(contaminated, sessions, source)

    pd.testing.assert_frame_equal(baseline, observed)


def test_duplicate_future_identity_cannot_change_source_state() -> None:
    frame, sessions = _panel()
    source = frame["session_date"].iloc[-1]
    baseline = build_price_state_for_source_session(frame, sessions, source)

    target = sessions[len(frame)]
    future = pd.DataFrame(
        [
            {
                "ticker": "TEST",
                "session_date": target,
                "raw_high": 102.0,
                "raw_low": 98.0,
                "raw_close": 100.0,
                "raw_volume": 1_000_000.0,
            },
            {
                "ticker": "TEST",
                "session_date": target,
                "raw_high": 103.0,
                "raw_low": 97.0,
                "raw_close": 101.0,
                "raw_volume": 1_500_000.0,
            },
        ]
    )
    contaminated = pd.concat([frame, future], ignore_index=True)
    observed = build_price_state_for_source_session(contaminated, sessions, source)

    pd.testing.assert_frame_equal(baseline, observed)
