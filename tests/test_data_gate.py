import pandas as pd
import pytest

from idx_trade.data import canonicalize_ohlcv
from idx_trade.data_gate import assert_data_gate, evaluate_data_gate
from idx_trade.security_master import (
    build_security_master,
    canonicalize_coverage_windows,
    canonicalize_tradability_anchors,
    canonicalize_tradability_intervals,
)


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
                "discovery_basis": ["TEST_PUBLIC_DISCOVERY_AUDIT"],
                "left_boundary_basis": ["TEST_ARCHIVE_START_AUDIT"],
            }
        )
    )


def _anchors():
    return canonicalize_tradability_anchors(
        pd.DataFrame(
            {
                "ticker": ["TEST"],
                "market": ["REGULAR"],
                "as_of_date": ["2025-01-02"],
                "state": ["ACTIVE"],
                "source": ["IDX_TEST_STATUS"],
                "source_ref": ["idx://test-active"],
                "evidence_type": ["OFFICIAL_ACTIVE_STATUS"],
            }
        )
    )


def test_model_is_blocked_when_split_history_is_unverified():
    sessions = pd.bdate_range("2025-01-01", periods=20)
    report = evaluate_data_gate(
        ["TEST"],
        sessions,
        {"TEST": _frame(sessions)},
        _master(),
        canonicalize_tradability_intervals(pd.DataFrame()),
        _coverage(),
        tradability_anchors=_anchors(),
        split_history_verified={"TEST": False},
        price_semantics_verified={"TEST": True},
    )
    assert not report["passed"]
    assert report["ticker_gates"][0]["blockers"] == ("SPLIT_HISTORY_UNVERIFIED",)
    assert report["ticker_gates"][0]["split_history_verified"] is False
    with pytest.raises(RuntimeError, match="DATA GATE failed"):
        assert_data_gate(report)


def test_model_is_blocked_when_price_semantics_flag_is_missing():
    sessions = pd.bdate_range("2025-01-01", periods=20)
    report = evaluate_data_gate(
        ["TEST"],
        sessions,
        {"TEST": _frame(sessions)},
        _master(),
        canonicalize_tradability_intervals(pd.DataFrame()),
        _coverage(),
        tradability_anchors=_anchors(),
        split_history_verified={"TEST": True},
    )
    assert not report["passed"]
    assert report["ticker_gates"][0]["blockers"] == ("PRICE_SEMANTICS_UNVERIFIED",)


def test_model_is_blocked_when_complete_window_has_no_ticker_anchor():
    sessions = pd.bdate_range("2025-01-01", periods=20)
    report = evaluate_data_gate(
        ["TEST"],
        sessions,
        {"TEST": _frame(sessions)},
        _master(),
        canonicalize_tradability_intervals(pd.DataFrame()),
        _coverage(),
        split_history_verified={"TEST": True},
        price_semantics_verified={"TEST": True},
    )
    assert not report["passed"]
    assert report["ticker_gates"][0]["blockers"] == ("SESSION_COVERAGE_INCOMPLETE",)


def test_complete_verified_ticker_passes_data_gate():
    sessions = pd.bdate_range("2025-01-01", periods=20)
    report = evaluate_data_gate(
        ["TEST"],
        sessions,
        {"TEST": _frame(sessions)},
        _master(),
        canonicalize_tradability_intervals(pd.DataFrame()),
        _coverage(),
        tradability_anchors=_anchors(),
        split_history_verified={"TEST": True},
        price_semantics_verified={"TEST": True},
    )
    assert report["passed"]
    assert_data_gate(report)


def test_dividend_verification_is_informational_only_for_v1_price_gate():
    sessions = pd.bdate_range("2025-01-01", periods=20)
    report = evaluate_data_gate(
        ["TEST"],
        sessions,
        {"TEST": _frame(sessions)},
        _master(),
        canonicalize_tradability_intervals(pd.DataFrame()),
        _coverage(),
        tradability_anchors=_anchors(),
        split_history_verified={"TEST": True},
        dividend_history_verified={"TEST": False},
        price_semantics_verified={"TEST": True},
    )
    assert report["passed"] is True
    assert report["ticker_gates"][0]["dividend_history_verified"] is False
    assert all("DIVIDEND" not in blocker for blocker in report["ticker_gates"][0]["blockers"])


def test_zero_expected_active_sessions_do_not_require_price_rows_or_price_flags():
    sessions = pd.bdate_range("2025-01-01", periods=20)
    intervals = canonicalize_tradability_intervals(
        pd.DataFrame(
            {
                "ticker": ["TEST"],
                "market": ["REGULAR"],
                "state": ["SUSPENDED"],
                "effective_from": ["2025-01-01"],
                "effective_to": ["2025-01-31"],
                "source": ["TEST"],
            }
        )
    )
    report = evaluate_data_gate(
        ["TEST"],
        sessions,
        {"TEST": pd.DataFrame()},
        _master(),
        intervals,
        _coverage(),
        split_history_verified={"TEST": False},
        price_semantics_verified={"TEST": False},
    )
    ticker = report["ticker_gates"][0]
    assert report["passed"] is True
    assert ticker["expected_active_sessions"] == 0
    assert ticker["price_requirements_applicable"] is False
    assert ticker["session_coverage_complete"] is True
    assert ticker["blockers"] == ()
