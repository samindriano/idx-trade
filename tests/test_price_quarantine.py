import pandas as pd

from idx_trade.coverage import active_price_view, security_coverage
from idx_trade.data_gate import evaluate_data_gate
from idx_trade.security_master import (
    build_security_master,
    canonicalize_coverage_windows,
    canonicalize_tradability_anchors,
    canonicalize_tradability_intervals,
)


def _master() -> pd.DataFrame:
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


def _intervals() -> pd.DataFrame:
    return canonicalize_tradability_intervals(
        pd.DataFrame(
            {
                "ticker": ["TEST"],
                "market": ["REGULAR"],
                "state": ["SUSPENDED"],
                "effective_from": ["2025-01-03"],
                "effective_to": ["2025-01-03"],
                "source": ["IDX_EXCHANGE_ANNOUNCEMENT"],
                "source_ref": ["idx://suspend"],
            }
        )
    )


def _anchors() -> pd.DataFrame:
    return canonicalize_tradability_anchors(
        pd.DataFrame(
            {
                "ticker": ["TEST", "TEST"],
                "market": ["REGULAR", "REGULAR"],
                "as_of_date": ["2025-01-02", "2025-01-06"],
                "state": ["ACTIVE", "ACTIVE"],
                "source": ["IDX_PUBLIC_STOCK_SUMMARY"] * 2,
                "source_ref": ["idx://20250102", "idx://20250106"],
                "evidence_type": [
                    "IDX_STOCK_SUMMARY_REGULAR_EXECUTION_OBSERVATION"
                ]
                * 2,
            }
        )
    )


def _prices() -> pd.DataFrame:
    dates = pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06"])
    return pd.DataFrame(
        {
            "date": dates,
            "raw_open": [100.0, 100.0, 101.0],
            "raw_high": [101.0, 100.0, 102.0],
            "raw_low": [99.0, 100.0, 100.0],
            "raw_close": [100.0, 100.0, 101.0],
            "raw_volume": [1000.0, 500.0, 1200.0],
        }
    )


def test_nonactive_provider_row_is_quarantined_not_a_coverage_failure():
    sessions = pd.DatetimeIndex(pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06"]))
    report = security_coverage(
        "TEST",
        sessions,
        _prices(),
        _master(),
        _intervals(),
        canonicalize_coverage_windows(pd.DataFrame()),
        tradability_anchors=_anchors(),
    )
    assert report.expected_active_sessions == 2
    assert report.observed_active_sessions == 2
    assert report.missing_expected_sessions == 0
    assert report.unexpected_nonactive_bars == 1
    assert report.quarantined_nonactive_bars == 1
    assert report.complete is True


def test_active_price_view_drops_provider_contamination_on_suspended_session():
    safe = active_price_view(
        _prices(),
        "TEST",
        _master(),
        _intervals(),
        canonicalize_coverage_windows(pd.DataFrame()),
        tradability_anchors=_anchors(),
    )
    assert safe["date"].tolist() == [
        pd.Timestamp("2025-01-02"),
        pd.Timestamp("2025-01-06"),
    ]


def test_data_gate_passes_when_only_issue_is_quarantined_provider_contamination():
    sessions = pd.DatetimeIndex(pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06"]))
    report = evaluate_data_gate(
        ["TEST"],
        sessions,
        {"TEST": _prices()},
        _master(),
        _intervals(),
        canonicalize_coverage_windows(pd.DataFrame()),
        tradability_anchors=_anchors(),
        split_history_verified={"TEST": True},
        price_semantics_verified={"TEST": True},
    )
    assert report["passed"] is True
    assert report["session_coverage"]["quarantined_nonactive_bars"] == 1
