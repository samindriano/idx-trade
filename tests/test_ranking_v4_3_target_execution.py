from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from idx_trade.ranking_v4_3_target_execution import (
    MARKET_ENTRY_UNAVAILABLE,
    NO_FUTURE_SESSION,
    PRICE_CONTINUITY_UNRESOLVED,
    TARGET_BOTH_AVAILABLE,
    TARGET_DATA_UNOBSERVABLE,
    TARGET_H10_AVAILABLE,
    TARGET_H5_AVAILABLE,
    TRADING_MECHANISM_REFERENCE_UNRESOLVED,
    build_geometry_from_accepted_open,
    materialize_v4_target_ledger,
    prepare_continuity_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
GOOD_SHA = "1" * 64


def sessions() -> pd.DatetimeIndex:
    return pd.date_range("2024-01-02", periods=15, freq="B")


def continuity(tickers: list[str], signal_date: pd.Timestamp, status: str = "RESOLVED_NO_MECHANICAL_DISCONTINUITY") -> pd.DataFrame:
    rows = []
    for ticker in tickers:
        for horizon in (5, 10):
            rows.append(
                {
                    "ticker": ticker,
                    "signal_date": signal_date,
                    "horizon": horizon,
                    "continuity_status": status,
                    "policy_id": "SYNTHETIC_TEST_POLICY",
                    "evidence_id": f"{ticker}-{horizon}",
                    "evidence_sha256": GOOD_SHA,
                }
            )
    return pd.DataFrame(rows)


def price_row(
    ticker: str,
    date: pd.Timestamp,
    *,
    state: str = "ACTIVE",
    open_value: float | None = 100.0,
    open_admitted: bool = True,
    close_value: float | None = 100.0,
    close_admitted: bool = True,
) -> dict[str, object]:
    return {
        "ticker": ticker,
        "date": date,
        "market_state": state,
        "accepted_open": np.nan if open_value is None else open_value,
        "open_admitted": open_admitted,
        "close": np.nan if close_value is None else close_value,
        "close_admitted": close_admitted,
    }


def test_protocol_is_locked_and_historical_execution_is_still_blocked() -> None:
    protocol = json.loads(
        (ROOT / "config" / "ranking_v4_3_target_execution_protocol.json").read_text(
            encoding="utf-8"
        )
    )
    assert protocol["outcome_blind"] is True
    assert protocol["target"]["entry_offset_official_sessions"] == 1
    assert protocol["target"]["h5_terminal_offset_official_sessions"] == 5
    assert protocol["target"]["h10_terminal_offset_official_sessions"] == 10
    assert protocol["target"]["close_t_fallback"] is False
    assert protocol["continuity_evidence_contract"][
        "corporate_action_integrity_verified_boolean_is_not_full_v4_continuity_proof"
    ] is True
    assert protocol["historical_execution_authorization"]["target_materialization"] is False
    assert protocol["historical_execution_authorization"]["model_fit"] is False


def test_geometry_uses_admitted_open_not_signal_open_and_missing_open_fails_closed() -> None:
    day = sessions()[0]
    signal = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "date": [day, day],
            "open": [999.0, 999.0],
            "high": [110.0, 110.0],
            "low": [100.0, 100.0],
            "close": [108.0, 108.0],
        }
    )
    prices = pd.DataFrame(
        [
            price_row("AAA", day, open_value=105.0, open_admitted=True),
            price_row("BBB", day, open_value=None, open_admitted=False),
        ]
    )
    geometry = build_geometry_from_accepted_open(signal, prices).set_index("ticker")
    assert np.isclose(geometry.loc["AAA", "session_open_position_range"], 0.5)
    assert np.isclose(geometry.loc["AAA", "session_body_signed_range"], 0.3)
    assert bool(geometry.loc["AAA", "geometry_open_admitted"])
    assert np.isnan(geometry.loc["BBB", "session_open_position_range"])
    assert np.isnan(geometry.loc["BBB", "session_body_signed_range"])
    assert not bool(geometry.loc["BBB", "geometry_open_admitted"])
    assert np.isfinite(geometry.loc["BBB", "session_log_high_low_range"])


def test_exact_t1_h5_h10_offsets_returns_ranks_ties_and_consensus() -> None:
    cal = sessions()
    signal_date = cal[0]
    tickers = ["AAA", "BBB", "CCC"]
    decisions = pd.DataFrame({"ticker": tickers, "date": signal_date, "keep": [1, 2, 3]})
    rows: list[dict[str, object]] = []
    h5_close = {"AAA": 110.0, "BBB": 100.0, "CCC": 90.0}
    h10_close = {"AAA": 120.0, "BBB": 100.0, "CCC": 80.0}
    for ticker in tickers:
        rows.extend(
            [
                price_row(ticker, cal[1], open_value=100.0, close_value=101.0),
                price_row(ticker, cal[5], open_value=100.0, close_value=h5_close[ticker]),
                price_row(ticker, cal[10], open_value=100.0, close_value=h10_close[ticker]),
            ]
        )
    ledger = materialize_v4_target_ledger(
        decisions, cal, pd.DataFrame(rows), continuity(tickers, signal_date)
    ).set_index("ticker")

    assert ledger.loc["AAA", "h5_entry_date"] == cal[1]
    assert ledger.loc["AAA", "h5_terminal_date"] == cal[5]
    assert ledger.loc["AAA", "h10_terminal_date"] == cal[10]
    assert np.isclose(ledger.loc["AAA", "r5"], 0.10)
    assert np.isclose(ledger.loc["BBB", "r5"], 0.0)
    assert np.isclose(ledger.loc["CCC", "r5"], -0.10)
    assert ledger.loc["AAA", "target_state_h5"] == TARGET_H5_AVAILABLE
    assert ledger.loc["AAA", "target_state_h10"] == TARGET_H10_AVAILABLE
    assert ledger.loc["AAA", "target_state_consensus"] == TARGET_BOTH_AVAILABLE
    assert ledger.loc["AAA", "target_rank_h5"] == 1.0
    assert ledger.loc["BBB", "target_rank_h5"] == 0.5
    assert ledger.loc["CCC", "target_rank_h5"] == 0.0
    assert ledger.loc["AAA", "realized_consensus"] == 1.0
    assert ledger.loc["BBB", "realized_consensus"] == 0.5
    assert ledger.loc["CCC", "realized_consensus"] == 0.0
    assert ledger["keep"].sort_values().tolist() == [1, 2, 3]


def test_average_ties_are_ranked_without_dropping_valid_zero_or_negative_returns() -> None:
    cal = sessions()
    signal_date = cal[0]
    tickers = ["AAA", "BBB", "CCC"]
    decisions = pd.DataFrame({"ticker": tickers, "date": signal_date})
    rows: list[dict[str, object]] = []
    closes = {"AAA": 100.0, "BBB": 100.0, "CCC": 90.0}
    for ticker in tickers:
        rows.extend(
            [
                price_row(ticker, cal[1], open_value=100.0),
                price_row(ticker, cal[5], close_value=closes[ticker]),
                price_row(ticker, cal[10], close_value=closes[ticker]),
            ]
        )
    ledger = materialize_v4_target_ledger(
        decisions, cal, pd.DataFrame(rows), continuity(tickers, signal_date)
    ).set_index("ticker")
    assert ledger.loc["AAA", "r5"] == 0.0
    assert ledger.loc["BBB", "r5"] == 0.0
    assert ledger.loc["CCC", "r5"] < 0.0
    assert ledger.loc["AAA", "target_rank_h5"] == 0.75
    assert ledger.loc["BBB", "target_rank_h5"] == 0.75
    assert ledger.loc["CCC", "target_rank_h5"] == 0.0


def test_entry_no_trade_is_market_entry_unavailable_without_close_t_fallback() -> None:
    cal = sessions()
    signal_date = cal[0]
    decisions = pd.DataFrame({"ticker": ["AAA"], "date": [signal_date]})
    rows = [
        price_row("AAA", cal[0], open_value=777.0, close_value=777.0),
        price_row("AAA", cal[1], state="NO_TRADE", open_value=None, open_admitted=False),
        price_row("AAA", cal[5], close_value=110.0),
        price_row("AAA", cal[10], close_value=120.0),
    ]
    ledger = materialize_v4_target_ledger(
        decisions, cal, pd.DataFrame(rows), continuity(["AAA"], signal_date)
    ).iloc[0]
    assert ledger["target_state_h5"] == MARKET_ENTRY_UNAVAILABLE
    assert ledger["target_state_h10"] == MARKET_ENTRY_UNAVAILABLE
    assert np.isnan(ledger["r5"])
    assert np.isnan(ledger["r10"])


def test_explicit_ambiguous_mechanism_fails_as_mechanism_unresolved() -> None:
    cal = sessions()
    signal_date = cal[0]
    decisions = pd.DataFrame({"ticker": ["AAA"], "date": [signal_date]})
    rows = [
        price_row("AAA", cal[1], state="AMBIGUOUS", open_value=100.0),
        price_row("AAA", cal[5], close_value=110.0),
        price_row("AAA", cal[10], close_value=120.0),
    ]
    ledger = materialize_v4_target_ledger(
        decisions, cal, pd.DataFrame(rows), continuity(["AAA"], signal_date)
    ).iloc[0]
    assert ledger["target_state_h5"] == TRADING_MECHANISM_REFERENCE_UNRESOLVED
    assert ledger["target_state_h10"] == TRADING_MECHANISM_REFERENCE_UNRESOLVED


def test_active_entry_with_unadmitted_open_is_data_unobservable() -> None:
    cal = sessions()
    signal_date = cal[0]
    decisions = pd.DataFrame({"ticker": ["AAA"], "date": [signal_date]})
    rows = [
        price_row("AAA", cal[1], state="ACTIVE", open_value=None, open_admitted=False),
        price_row("AAA", cal[5], close_value=110.0),
        price_row("AAA", cal[10], close_value=120.0),
    ]
    ledger = materialize_v4_target_ledger(
        decisions, cal, pd.DataFrame(rows), continuity(["AAA"], signal_date)
    ).iloc[0]
    assert ledger["target_state_h5"] == TARGET_DATA_UNOBSERVABLE
    assert ledger["target_state_h10"] == TARGET_DATA_UNOBSERVABLE


def test_missing_price_row_is_data_unobservable_not_invented_unknown_market_state() -> None:
    cal = sessions()
    signal_date = cal[0]
    decisions = pd.DataFrame({"ticker": ["AAA"], "date": [signal_date]})
    rows = [
        price_row("AAA", cal[5], close_value=110.0),
        price_row("AAA", cal[10], close_value=120.0),
    ]
    ledger = materialize_v4_target_ledger(
        decisions, cal, pd.DataFrame(rows), continuity(["AAA"], signal_date)
    ).iloc[0]
    assert ledger["target_state_h5"] == TARGET_DATA_UNOBSERVABLE
    assert ledger["target_state_h10"] == TARGET_DATA_UNOBSERVABLE


def test_missing_or_explicit_failed_continuity_never_computes_return() -> None:
    cal = sessions()
    signal_date = cal[0]
    decisions = pd.DataFrame({"ticker": ["AAA", "BBB"], "date": signal_date})
    rows = []
    for ticker in ("AAA", "BBB"):
        rows.extend(
            [
                price_row(ticker, cal[1], open_value=100.0),
                price_row(ticker, cal[5], close_value=110.0),
                price_row(ticker, cal[10], close_value=120.0),
            ]
        )
    ca = continuity(["BBB"], signal_date, "PRICE_CONTINUITY_UNRESOLVED_EVENT")
    ledger = materialize_v4_target_ledger(decisions, cal, pd.DataFrame(rows), ca).set_index("ticker")
    assert ledger.loc["AAA", "target_state_h5"] == PRICE_CONTINUITY_UNRESOLVED
    assert ledger.loc["AAA", "h5_continuity_status"] == "PRICE_CONTINUITY_UNRESOLVED_COVERAGE"
    assert ledger.loc["BBB", "target_state_h5"] == PRICE_CONTINUITY_UNRESOLVED
    assert ledger.loc["BBB", "h5_continuity_status"] == "PRICE_CONTINUITY_UNRESOLVED_EVENT"
    assert np.isnan(ledger.loc["AAA", "r5"])
    assert np.isnan(ledger.loc["BBB", "r5"])


def test_no_future_session_is_explicit_and_row_is_retained() -> None:
    cal = sessions()
    decisions = pd.DataFrame({"ticker": ["AAA"], "date": [cal[-3]], "sentinel": [7]})
    prices = pd.DataFrame([price_row("AAA", cal[-2])])
    ca = continuity(["AAA"], cal[-3])
    ledger = materialize_v4_target_ledger(decisions, cal, prices, ca).iloc[0]
    assert ledger["target_state_h5"] == NO_FUTURE_SESSION
    assert ledger["target_state_h10"] == NO_FUTURE_SESSION
    assert ledger["sentinel"] == 7


def test_continuity_evidence_requires_exact_unique_provenance() -> None:
    day = sessions()[0]
    valid = continuity(["AAA"], day)
    duplicate = pd.concat([valid, valid.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        prepare_continuity_evidence(duplicate)
    bad_sha = valid.copy()
    bad_sha.loc[0, "evidence_sha256"] = "not-a-sha"
    with pytest.raises(ValueError, match="SHA"):
        prepare_continuity_evidence(bad_sha)
