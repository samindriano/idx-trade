import pandas as pd

from idx_trade.coverage import security_coverage
from idx_trade.data_gate import evaluate_data_gate
from idx_trade.security_master import (
    build_security_master,
    canonicalize_coverage_windows,
    canonicalize_tradability_intervals,
)


def _delisted_master(ticker: str = "OLDX") -> pd.DataFrame:
    return build_security_master(
        pd.DataFrame(),
        pd.DataFrame(
            {
                "ticker": [ticker],
                "company_name": ["Old Listed Company Tbk"],
                "listed_from": ["2010-01-01"],
                "listed_to": ["2025-07-18"],
                "source": ["IDX_DIGITAL_STATISTIC_DELISTING"],
            }
        ),
    )


def test_known_delisted_security_before_window_is_complete_noneligible_coverage():
    sessions = pd.bdate_range("2026-06-02", "2026-07-31")
    report = security_coverage(
        "OLDX",
        sessions,
        pd.DatetimeIndex([]),
        _delisted_master(),
        canonicalize_tradability_intervals(pd.DataFrame()),
        canonicalize_coverage_windows(pd.DataFrame()),
    )

    assert report.identity_present is True
    assert report.listed_sessions == 0
    assert report.expected_active_sessions == 0
    assert report.price_required is False
    assert report.complete is True


def test_known_delisted_security_does_not_require_price_or_split_flags():
    sessions = pd.bdate_range("2026-06-02", "2026-07-31")
    report = evaluate_data_gate(
        ["OLDX"],
        sessions,
        {"OLDX": pd.DataFrame()},
        _delisted_master(),
        canonicalize_tradability_intervals(pd.DataFrame()),
        canonicalize_coverage_windows(pd.DataFrame()),
        split_history_verified={"OLDX": False},
        price_semantics_verified={"OLDX": False},
    )

    gate = report["ticker_gates"][0]
    assert report["passed"] is True
    assert gate["identity_resolved"] is True
    assert gate["expected_active_sessions"] == 0
    assert gate["price_requirements_applicable"] is False
    assert gate["blockers"] == ()


def test_absent_security_master_identity_fails_closed_explicitly():
    sessions = pd.bdate_range("2026-06-02", "2026-07-31")
    report = evaluate_data_gate(
        ["MISS"],
        sessions,
        {"MISS": pd.DataFrame()},
        _delisted_master("OLDX"),
        canonicalize_tradability_intervals(pd.DataFrame()),
        canonicalize_coverage_windows(pd.DataFrame()),
        split_history_verified={"MISS": False},
        price_semantics_verified={"MISS": False},
    )

    gate = report["ticker_gates"][0]
    assert report["passed"] is False
    assert gate["identity_resolved"] is False
    assert gate["blockers"] == ("SECURITY_IDENTITY_UNRESOLVED",)
