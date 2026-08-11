from __future__ import annotations

import pandas as pd

from idx_trade.corporate_action_diagnostics import scan_split_candidate_transitions


def test_scanner_finds_nearby_mechanical_split_transition() -> None:
    events = pd.DataFrame(
        [
            {
                "ticker": "ABCD",
                "source_anchor_date": "2025-01-08",
                "ratio_old": 1,
                "ratio_new": 2,
            }
        ]
    )
    prices = pd.DataFrame(
        [
            {"ticker": "ABCD", "date": "2025-01-07", "raw_open": 990, "raw_close": 1000},
            {"ticker": "ABCD", "date": "2025-01-08", "raw_open": 1005, "raw_close": 1010},
            {"ticker": "ABCD", "date": "2025-01-09", "raw_open": 1008, "raw_close": 1000},
            {"ticker": "ABCD", "date": "2025-01-10", "raw_open": 505, "raw_close": 510},
            {"ticker": "ABCD", "date": "2025-01-13", "raw_open": 512, "raw_close": 515},
        ]
    )

    result = scan_split_candidate_transitions(prices, events, window_sessions=3)
    best = result.sort_values("best_relative_error").iloc[0]

    assert best["candidate_session"] == pd.Timestamp("2025-01-10")
    assert best["session_offset"] == 2
    assert bool(best["match_within_10pct"])


def test_scanner_does_not_fabricate_match_for_adjusted_continuous_prices() -> None:
    events = pd.DataFrame(
        [
            {
                "ticker": "ABCD",
                "source_anchor_date": "2025-01-08",
                "ratio_old": 1,
                "ratio_new": 2,
            }
        ]
    )
    prices = pd.DataFrame(
        [
            {"ticker": "ABCD", "date": "2025-01-07", "raw_open": 500, "raw_close": 500},
            {"ticker": "ABCD", "date": "2025-01-08", "raw_open": 502, "raw_close": 501},
            {"ticker": "ABCD", "date": "2025-01-09", "raw_open": 501, "raw_close": 503},
            {"ticker": "ABCD", "date": "2025-01-10", "raw_open": 504, "raw_close": 502},
            {"ticker": "ABCD", "date": "2025-01-13", "raw_open": 503, "raw_close": 505},
        ]
    )

    result = scan_split_candidate_transitions(prices, events, window_sessions=3)

    assert not result["match_within_20pct"].any()


def test_scanner_rejects_nonpositive_ratio() -> None:
    events = pd.DataFrame(
        [
            {
                "ticker": "ABCD",
                "source_anchor_date": "2025-01-08",
                "ratio_old": 0,
                "ratio_new": 2,
            }
        ]
    )
    prices = pd.DataFrame(
        [
            {"ticker": "ABCD", "date": "2025-01-07", "raw_open": 500, "raw_close": 500},
            {"ticker": "ABCD", "date": "2025-01-08", "raw_open": 250, "raw_close": 250},
        ]
    )

    try:
        scan_split_candidate_transitions(prices, events)
    except ValueError as exc:
        assert "invalid anchor date or ratio" in str(exc)
    else:
        raise AssertionError("Expected invalid split ratio to fail closed")
