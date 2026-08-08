import pandas as pd

from idx_trade.coverage import security_coverage
from idx_trade.execution_evidence import stock_summary_execution_anchors
from idx_trade.security_master import (
    build_security_master,
    canonicalize_coverage_windows,
    canonicalize_tradability_intervals,
)
from idx_trade.states import TradabilityState


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


def _summary() -> pd.DataFrame:
    dates = pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06"])
    return pd.DataFrame(
        {
            "ticker": ["TEST"] * 3,
            "as_of_date": dates,
            "volume": [1000, 0, 1500],
            "frequency": [10, 0, 15],
            "nonregular_volume": [2000, 200, 0],
            "nonregular_frequency": [20, 2, 0],
            "source": ["IDX_PUBLIC_STOCK_SUMMARY"] * 3,
            "source_ref": ["idx://summary"] * 3,
        }
    )


def test_stock_summary_execution_evidence_distinguishes_trade_from_no_trade():
    anchors, diagnostics = stock_summary_execution_anchors(_summary())
    assert diagnostics.empty
    states = dict(zip(anchors["as_of_date"], anchors["state"]))
    assert states[pd.Timestamp("2025-01-02")] == TradabilityState.ACTIVE.value
    assert states[pd.Timestamp("2025-01-03")] == TradabilityState.NO_TRADE.value
    assert states[pd.Timestamp("2025-01-06")] == TradabilityState.ACTIVE.value


def test_nonregular_metrics_are_separate_not_subtracted_from_regular_metrics():
    frame = pd.DataFrame(
        {
            "ticker": ["GOTO"],
            "as_of_date": [pd.Timestamp("2026-06-02")],
            "volume": [100.0],
            "frequency": [1.0],
            "nonregular_volume": [10_000.0],
            "nonregular_frequency": [50.0],
            "source": ["IDX_PUBLIC_STOCK_SUMMARY"],
            "source_ref": ["idx://summary/20260602"],
        }
    )
    anchors, diagnostics = stock_summary_execution_anchors(frame)
    assert diagnostics.empty
    assert anchors.loc[0, "state"] == TradabilityState.ACTIVE.value


def test_direct_execution_evidence_can_complete_session_coverage_without_announcement_window():
    sessions = pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06"])
    anchors, _ = stock_summary_execution_anchors(_summary())
    report = security_coverage(
        "TEST",
        pd.DatetimeIndex(sessions),
        pd.to_datetime(["2025-01-02", "2025-01-06"]),
        _master(),
        canonicalize_tradability_intervals(pd.DataFrame()),
        canonicalize_coverage_windows(pd.DataFrame()),
        tradability_anchors=anchors,
    )
    assert report.expected_active_sessions == 2
    assert report.unknown_tradability_sessions == 0
    assert report.unexpected_nonactive_bars == 0
    assert report.complete is True


def test_missing_direct_evidence_keeps_session_unknown():
    sessions = pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07"])
    anchors, _ = stock_summary_execution_anchors(_summary())
    report = security_coverage(
        "TEST",
        pd.DatetimeIndex(sessions),
        pd.to_datetime(["2025-01-02", "2025-01-06"]),
        _master(),
        canonicalize_tradability_intervals(pd.DataFrame()),
        canonicalize_coverage_windows(pd.DataFrame()),
        tradability_anchors=anchors,
    )
    assert report.unknown_tradability_sessions == 1
    assert report.complete is False
