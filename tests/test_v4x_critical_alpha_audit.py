from __future__ import annotations

import numpy as np
import pandas as pd
import pandas.testing as pdt

from idx_trade.ranking_v4_3_features import (
    V4_CONTROL_FEATURE_COLUMNS,
    build_v4_control_feature_table,
)
from idx_trade.ranking_v4_3_preregistration import (
    SESSION_GEOMETRY_FEATURE_COLUMNS,
    materialize_validation_folds,
)
from idx_trade.ranking_v4_3_target_execution import (
    ACTIVE,
    CONTINUITY_PASSING,
    build_geometry_from_accepted_open,
    materialize_v4_target_ledger,
)


def _sessions(count: int = 90) -> pd.DatetimeIndex:
    return pd.date_range("2024-01-02", periods=count, freq="B")


def _signal_panel(sessions: pd.DatetimeIndex) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for ticker_index, ticker in enumerate(("AAA", "BBB", "CCC"), start=1):
        base = 100.0 + 17.0 * ticker_index
        for index, day in enumerate(sessions):
            close = base + 0.35 * index + 0.7 * np.sin(index / 5.0 + ticker_index)
            high = close + 2.0 + 0.1 * ticker_index
            low = close - 2.0 - 0.1 * ticker_index
            rows.append(
                {
                    "ticker": ticker,
                    "date": day,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": 1_000_000.0 + 10_000.0 * index + ticker_index,
                    "regular_market_value": 2_000_000_000.0 + 10_000_000.0 * index + ticker_index,
                }
            )
    return pd.DataFrame(rows)


def _security_master(sessions: pd.DatetimeIndex) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "listed_from": [sessions[0]] * 3,
            "listed_to": [pd.NaT] * 3,
        }
    )


def _price_evidence(panel: pd.DataFrame) -> pd.DataFrame:
    out = panel[["ticker", "date", "high", "low", "close"]].copy()
    out["accepted_open"] = 0.5 * (out["high"] + out["low"])
    out["open_admitted"] = True
    out["close_admitted"] = True
    out["market_state"] = ACTIVE
    return out[
        [
            "ticker",
            "date",
            "market_state",
            "accepted_open",
            "open_admitted",
            "close",
            "close_admitted",
        ]
    ]


def test_control_features_are_invariant_to_future_market_mutation() -> None:
    sessions = _sessions()
    panel = _signal_panel(sessions)
    master = _security_master(sessions)
    cutoff = sessions[64]

    baseline, _ = build_v4_control_feature_table(panel, sessions, master)

    mutated = panel.copy()
    future = mutated["date"] > cutoff
    # Deliberately make the future wildly different while preserving valid HLCV.
    mutated.loc[future, "close"] *= 3.0
    mutated.loc[future, "high"] = mutated.loc[future, "close"] * 1.10
    mutated.loc[future, "low"] = mutated.loc[future, "close"] * 0.90
    mutated.loc[future, "volume"] *= 11.0
    mutated.loc[future, "regular_market_value"] *= 7.0
    after, _ = build_v4_control_feature_table(mutated, sessions, master)

    columns = [
        "ticker",
        "date",
        "universe_history_qualified",
        "universe_primary_liquid",
        *V4_CONTROL_FEATURE_COLUMNS,
    ]
    left = baseline.loc[baseline["date"] <= cutoff, columns].reset_index(drop=True)
    right = after.loc[after["date"] <= cutoff, columns].reset_index(drop=True)
    pdt.assert_frame_equal(left, right, check_exact=True)


def test_geometry_is_invariant_to_future_open_and_hlc_mutation() -> None:
    sessions = _sessions(20)
    panel = _signal_panel(sessions)
    prices = _price_evidence(panel)
    cutoff = sessions[9]

    baseline = build_geometry_from_accepted_open(panel, prices)

    mutated_panel = panel.copy()
    future = mutated_panel["date"] > cutoff
    mutated_panel.loc[future, "close"] *= 2.0
    mutated_panel.loc[future, "high"] = mutated_panel.loc[future, "close"] * 1.15
    mutated_panel.loc[future, "low"] = mutated_panel.loc[future, "close"] * 0.85

    mutated_prices = _price_evidence(mutated_panel)
    mutated_prices.loc[mutated_prices["date"] > cutoff, "accepted_open"] = (
        mutated_panel.loc[future, "low"].to_numpy()
        + 0.2
        * (
            mutated_panel.loc[future, "high"].to_numpy()
            - mutated_panel.loc[future, "low"].to_numpy()
        )
    )
    after = build_geometry_from_accepted_open(mutated_panel, mutated_prices)

    columns = ["ticker", "date", *SESSION_GEOMETRY_FEATURE_COLUMNS, "geometry_open_admitted"]
    left = baseline.loc[baseline["date"] <= cutoff, columns].reset_index(drop=True)
    right = after.loc[after["date"] <= cutoff, columns].reset_index(drop=True)
    pdt.assert_frame_equal(left, right, check_exact=True)


def test_geometry_changes_when_same_session_open_changes() -> None:
    sessions = _sessions(3)
    panel = _signal_panel(sessions)
    prices = _price_evidence(panel)
    baseline = build_geometry_from_accepted_open(panel, prices)

    target = (prices["ticker"].eq("AAA")) & (prices["date"].eq(sessions[1]))
    panel_target = (panel["ticker"].eq("AAA")) & (panel["date"].eq(sessions[1]))
    low = float(panel.loc[panel_target, "low"].iloc[0])
    high = float(panel.loc[panel_target, "high"].iloc[0])
    prices.loc[target, "accepted_open"] = low + 0.1 * (high - low)
    changed = build_geometry_from_accepted_open(panel, prices)

    identity = baseline["ticker"].eq("AAA") & baseline["date"].eq(sessions[1])
    assert not np.isclose(
        float(baseline.loc[identity, "session_open_position_range"].iloc[0]),
        float(changed.loc[identity, "session_open_position_range"].iloc[0]),
    )


def test_h10_training_target_finishes_before_each_validation_fold() -> None:
    sessions = pd.date_range("2020-01-02", periods=700, freq="B")
    eligible = pd.DataFrame({"session_index": np.arange(len(sessions)), "date": sessions})
    folds = materialize_validation_folds(eligible)

    for _, block in folds.groupby("fold", sort=True):
        validation_start = int(block["session_index"].min())
        max_training_signal = int(block["max_training_signal_session_index"].iloc[0])
        assert max_training_signal + 10 == validation_start - 1
        assert max_training_signal + 10 < validation_start


def test_target_ledger_uses_next_open_and_horizon_terminal_close_exactly() -> None:
    sessions = pd.date_range("2024-01-02", periods=12, freq="B")
    tickers = ("AAA", "BBB")
    decision_rows = pd.DataFrame({"ticker": tickers, "date": [sessions[0], sessions[0]]})

    prices: list[dict[str, object]] = []
    for ticker_index, ticker in enumerate(tickers):
        for index, day in enumerate(sessions):
            prices.append(
                {
                    "ticker": ticker,
                    "date": day,
                    "market_state": ACTIVE,
                    "accepted_open": 100.0 + 20.0 * ticker_index + index,
                    "open_admitted": True,
                    "close": 110.0 + 20.0 * ticker_index + 2.0 * index,
                    "close_admitted": True,
                }
            )
    price_evidence = pd.DataFrame(prices)

    passing = next(iter(CONTINUITY_PASSING))
    continuity_rows: list[dict[str, object]] = []
    for ticker in tickers:
        for horizon in (5, 10):
            continuity_rows.append(
                {
                    "ticker": ticker,
                    "signal_date": sessions[0],
                    "horizon": horizon,
                    "continuity_status": passing,
                    "policy_id": "synthetic-policy",
                    "evidence_id": f"{ticker}-{horizon}",
                    "evidence_sha256": "a" * 64,
                }
            )
    ledger = materialize_v4_target_ledger(
        decision_rows,
        sessions,
        price_evidence,
        pd.DataFrame(continuity_rows),
    ).set_index("ticker")

    for ticker_index, ticker in enumerate(tickers):
        entry_open = 100.0 + 20.0 * ticker_index + 1.0
        h5_close = 110.0 + 20.0 * ticker_index + 2.0 * 5.0
        h10_close = 110.0 + 20.0 * ticker_index + 2.0 * 10.0
        assert ledger.loc[ticker, "h5_entry_date"] == sessions[1]
        assert ledger.loc[ticker, "h5_terminal_date"] == sessions[5]
        assert ledger.loc[ticker, "h10_entry_date"] == sessions[1]
        assert ledger.loc[ticker, "h10_terminal_date"] == sessions[10]
        assert np.isclose(float(ledger.loc[ticker, "r5"]), h5_close / entry_open - 1.0)
        assert np.isclose(float(ledger.loc[ticker, "r10"]), h10_close / entry_open - 1.0)
