from pathlib import Path

import pandas as pd

from idx_trade.adversarial import load_adversarial_cases, run_adversarial_data_gate, unique_required_tickers
from idx_trade.data import canonicalize_ohlcv
from idx_trade.security_master import (
    build_security_master,
    canonicalize_coverage_windows,
    canonicalize_tradability_intervals,
)


CATALOG = Path(__file__).resolve().parents[1] / "config" / "adversarial_cases.csv"


def test_adversarial_catalog_is_large_and_covers_required_failure_families():
    cases = load_adversarial_cases(CATALOG)
    assert len(cases) >= 30
    assert len(unique_required_tickers(cases)) >= 30
    required_families = {
        "NORMAL_LIQUID",
        "RECENT_IPO",
        "SUSPEND_RESUME",
        "LONG_SUSPENSION",
        "COMPLEX_MARKET_SCOPE",
        "DELISTED_HISTORY",
        "DATA_QUALITY_STRESS",
    }
    assert required_families.issubset(set(cases["case_family"]))


def test_adversarial_runner_fails_closed_without_tradability_coverage():
    cases = pd.DataFrame(
        [
            {
                "case_id": "case-1",
                "ticker": "TEST",
                "case_family": "NORMAL_LIQUID",
                "gate_focus": "fixture",
                "reference_note": "fixture",
            }
        ]
    )
    master = build_security_master(
        pd.DataFrame(
            {
                "ticker": ["TEST"],
                "company_name": ["Test Tbk"],
                "listed_from": ["2025-01-01"],
                "listed_to": [None],
                "source": ["TEST"],
            }
        ),
        pd.DataFrame(),
    )
    sessions = pd.bdate_range("2025-01-01", periods=70)
    prices = canonicalize_ohlcv(
        pd.DataFrame(
            {
                "date": sessions,
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 100,
                "volume": 1_000_000,
            }
        ),
        ticker="TEST",
    )
    report = run_adversarial_data_gate(
        cases,
        sessions,
        {"TEST": prices},
        master,
        canonicalize_tradability_intervals(pd.DataFrame()),
        canonicalize_coverage_windows(pd.DataFrame()),
        split_history_verified={"TEST": True},
        price_semantics_verified={"TEST": True},
    )
    assert report["passed"] is False
    assert report["failed_ticker_symbols"] == ["TEST"]
    assert report["case_family_summary"][0]["passed"] is False
