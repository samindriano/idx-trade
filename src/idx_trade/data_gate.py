from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping

import pandas as pd

from .coverage import SecurityCoverage, coverage_gate, security_coverage
from .security_master import normalise_ticker


@dataclass(frozen=True)
class TickerDataGate:
    ticker: str
    identity_resolved: bool
    session_coverage_complete: bool
    expected_active_sessions: int
    price_requirements_applicable: bool
    split_history_verified: bool
    dividend_history_verified: bool | None
    price_semantics_verified: bool
    passed: bool
    blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def evaluate_data_gate(
    required_tickers: list[str],
    exchange_sessions: pd.DatetimeIndex,
    price_frames: Mapping[str, pd.DataFrame],
    security_master: pd.DataFrame,
    tradability_intervals: pd.DataFrame,
    tradability_coverage_windows: pd.DataFrame,
    *,
    tradability_anchors: pd.DataFrame | None = None,
    split_history_verified: Mapping[str, bool],
    dividend_history_verified: Mapping[str, bool] | None = None,
    price_semantics_verified: Mapping[str, bool] | None = None,
) -> dict[str, object]:
    """Hard pre-model gate for the required research universe."""

    dividend_history_verified = dividend_history_verified or {}
    price_semantics_verified = price_semantics_verified or {}
    coverage_reports: list[SecurityCoverage] = []
    ticker_reports: list[TickerDataGate] = []

    for value in required_tickers:
        ticker = normalise_ticker(value)
        frame = price_frames.get(ticker, pd.DataFrame())
        coverage = security_coverage(
            ticker,
            exchange_sessions,
            frame,
            security_master,
            tradability_intervals,
            tradability_coverage_windows,
            tradability_anchors=tradability_anchors,
        )
        coverage_reports.append(coverage)

        split_ok = bool(split_history_verified.get(ticker, False))
        dividend_ok = (
            bool(dividend_history_verified[ticker])
            if ticker in dividend_history_verified
            else None
        )
        semantics_ok = bool(price_semantics_verified.get(ticker, False))
        price_required = coverage.price_required
        blockers: list[str] = []
        if not coverage.identity_present:
            blockers.append("SECURITY_IDENTITY_UNRESOLVED")
        elif not coverage.complete:
            blockers.append("SESSION_COVERAGE_INCOMPLETE")
        if price_required and not split_ok:
            blockers.append("SPLIT_HISTORY_UNVERIFIED")
        if price_required and not semantics_ok:
            blockers.append("PRICE_SEMANTICS_UNVERIFIED")

        ticker_reports.append(
            TickerDataGate(
                ticker=ticker,
                identity_resolved=coverage.identity_present,
                session_coverage_complete=coverage.complete,
                expected_active_sessions=coverage.expected_active_sessions,
                price_requirements_applicable=price_required,
                split_history_verified=split_ok,
                dividend_history_verified=dividend_ok,
                price_semantics_verified=semantics_ok,
                passed=not blockers,
                blockers=tuple(blockers),
            )
        )

    session_gate = coverage_gate(coverage_reports)
    failed = [report for report in ticker_reports if not report.passed]
    return {
        "passed": bool(ticker_reports) and not failed,
        "required_tickers": len(ticker_reports),
        "passed_tickers": len(ticker_reports) - len(failed),
        "failed_tickers": len(failed),
        "failed_ticker_symbols": [report.ticker for report in failed],
        "session_coverage": session_gate,
        "ticker_gates": [report.to_dict() for report in ticker_reports],
    }


def assert_data_gate(report: dict[str, object]) -> None:
    if not bool(report.get("passed", False)):
        failed = report.get("failed_ticker_symbols", [])
        raise RuntimeError(f"DATA GATE failed; model development blocked. Failed tickers: {failed}")
