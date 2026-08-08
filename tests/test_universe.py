import pandas as pd

from idx_trade.data import canonicalize_ohlcv
from idx_trade.security_master import (
    build_security_master,
    canonicalize_coverage_windows,
    canonicalize_tradability_intervals,
)
from idx_trade.universe import build_dynamic_liquidity_universe


def _prices(start: str, periods: int, close: float, volume: float) -> pd.DataFrame:
    dates = pd.bdate_range(start, periods=periods)
    return canonicalize_ohlcv(
        pd.DataFrame(
            {
                "date": dates,
                "open": close,
                "high": close * 1.01,
                "low": close * 0.99,
                "close": close,
                "volume": volume,
            }
        )
    )


def _coverage():
    return canonicalize_coverage_windows(
        pd.DataFrame(
            {
                "market": ["REGULAR"],
                "effective_from": ["2020-01-01"],
                "effective_to": ["2026-12-31"],
                "source": ["TEST_COMPLETE"],
                "is_complete": [True],
                "discovery_basis": ["TEST_PUBLIC_DISCOVERY_AUDIT"],
                "left_boundary_basis": ["TEST_INITIAL_ACTIVE_SNAPSHOT"],
                "initial_state": ["ACTIVE"],
            }
        )
    )


def test_historical_delisted_name_can_be_selected_before_delisting_but_not_after():
    active = pd.DataFrame(
        {
            "ticker": ["LIVE"],
            "company_name": ["Live Tbk"],
            "listed_from": ["2020-01-01"],
            "listed_to": [None],
            "source": ["IDX"],
        }
    )
    delisted = pd.DataFrame(
        {
            "ticker": ["OLDX"],
            "company_name": ["Old Tbk"],
            "listed_from": ["2020-01-01"],
            "listed_to": ["2025-06-30"],
            "source": ["IDX"],
        }
    )
    master = build_security_master(active, delisted)
    intervals = canonicalize_tradability_intervals(pd.DataFrame())
    sessions = pd.bdate_range("2024-01-01", "2025-12-31")
    frames = {
        "LIVE": _prices("2024-01-01", len(sessions), 100.0, 1_000_000),
        "OLDX": _prices("2024-01-01", 390, 50.0, 4_000_000),
    }

    before = build_dynamic_liquidity_universe(
        pd.Timestamp("2025-06-20"), sessions, frames, master, intervals, _coverage(),
        top_n=2, lookback_sessions=60, minimum_warmup_sessions=60,
    )
    assert set(before.loc[before["selected"], "ticker"]) == {"LIVE", "OLDX"}

    after = build_dynamic_liquidity_universe(
        pd.Timestamp("2025-08-01"), sessions, frames, master, intervals, _coverage(),
        top_n=2, lookback_sessions=60, minimum_warmup_sessions=60,
    )
    old = after.loc[after["ticker"].eq("OLDX")].iloc[0]
    assert not bool(old["eligible"])
    assert old["eligibility_reason"] == "DELISTED"


def test_recent_ipo_is_not_selected_until_warmup_passes():
    active = pd.DataFrame(
        {
            "ticker": ["IPO1"],
            "company_name": ["IPO Tbk"],
            "listed_from": ["2025-01-02"],
            "listed_to": [None],
            "source": ["IDX"],
        }
    )
    master = build_security_master(active, pd.DataFrame())
    intervals = canonicalize_tradability_intervals(pd.DataFrame())
    sessions = pd.bdate_range("2025-01-02", periods=100)
    frames = {"IPO1": _prices("2025-01-02", 100, 100.0, 10_000_000)}

    early = build_dynamic_liquidity_universe(
        sessions[39], sessions, frames, master, intervals, _coverage(), top_n=10,
        minimum_warmup_sessions=60,
    )
    assert early.loc[0, "eligibility_reason"] == "IPO_WARMUP"
    assert not bool(early.loc[0, "selected"])

    mature = build_dynamic_liquidity_universe(
        sessions[79], sessions, frames, master, intervals, _coverage(), top_n=10,
        minimum_warmup_sessions=60,
    )
    assert mature.loc[0, "eligibility_reason"] == "ELIGIBLE"
    assert bool(mature.loc[0, "selected"])
