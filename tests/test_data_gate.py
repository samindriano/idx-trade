import pandas as pd
import pytest

from idx_trade.data import canonicalize_ohlcv
from idx_trade.data_gate import assert_data_gate, evaluate_data_gate
from idx_trade.security_master import build_security_master, canonicalize_coverage_windows, canonicalize_tradability_intervals


def _frame(dates):
    return canonicalize_ohlcv(
        pd.DataFrame(
            {
                "date": dates,
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.0,
                "volume": 1_000_000,
            }
        ),
        "TEST",
    )


def _master():
    return build_security_master(
        pd.DataFrame(
            {
                "ticker": ["TEST"],
                "company_name": ["Test Tbk"],
                "listed_from": ["2025-01-01"],
                "listed_to": [None],
                "source": ["IDX"],
            }
        ),
        pd.DataFrame(),
    )


def _coverage():
    return canonicalize_coverage_windows(
        pd.DataFrame(
            {
                "market": ["REGULAR"],
                "effective_from": ["2025-01-01"],
                "effective_to": ["2025-12-31"],
                "source": ["TEST_COMPLETE"],
                "is_complete": [True],
            }
        )
    )


def test_model_is_blocked_when_corporate_actions_are_unverified():
    sessions = pd.bdate_range("2025-01-01", periods=20)
    report = evaluate_data_gate(
        ["TEST"], sessions, {"TEST": _frame(sessions)}, _master(),
        canonicalize_tradability_intervals(pd.DataFrame()), _coverage(),
        corporate_action_verified={"TEST": False},
    )
    assert not report["passed"]
    assert report["ticker_gates"][0]["blockers"] == ("CORPORATE_ACTIONS_UNVERIFIED",)
    with pytest.raises(RuntimeError, match="DATA GATE failed"):
        assert_data_gate(report)


def test_complete_verified_ticker_passes_data_gate():
    sessions = pd.bdate_range("2025-01-01", periods=20)
    report = evaluate_data_gate(
        ["TEST"], sessions, {"TEST": _frame(sessions)}, _master(),
        canonicalize_tradability_intervals(pd.DataFrame()), _coverage(),
        corporate_action_verified={"TEST": True},
        price_semantics_verified={"TEST": True},
    )
    assert report["passed"]
    assert_data_gate(report)
