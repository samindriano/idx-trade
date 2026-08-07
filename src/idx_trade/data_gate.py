from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping

import pandas as pd

from .coverage import SecurityCoverage, coverage_gate, security_coverage
from .security_master import normalise_ticker


@dataclass(frozen=True)
class TickerDataGate:
    ticker: str
    session_coverage_complete: bool
    corporate_actions_verified: bool
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
    corporate_action_verified: Mapping[str, bool],
    price_semantics_verified: Mapping[str, bool] | None = None,
) -> dict[str, object]:
    """Hard pre-model gate for the required research universe.

    The gate is intentionally strict: a ticker with unresolved tradability,
    missing expected sessions, unverified corporate actions or unverified price
    semantics cannot silently enter model development.
    """

    price_semantics_verified = price_semantics_verified or {}
    coverage_reports: list[SecurityCoverage] = []
    ticker_reports: list[TickerDataGate] = []

    for value in required_tickers:
        ticker = normalise_ticker(value)
        frame = price_frames.get(ticker, pd.DataFrame())
        observed_dates = frame["date"] if "date" in frame.columns else pd.DatetimeIndex([])
        coverage = security_coverage(
            ticker,
            exchange_sessions,
            observed_dates,
            security_master,
            tradability_intervals,
            tradability_coverage_windows,
        )
        coverage_reports.append(coverage)

        action_ok = bool(corporate_action_verified.get(ticker, False))
        semantics_ok = bool(price_semantics_verified.get(ticker, True))
        blockers: list[str] = []
        if not coverage.complete:
            blockers.append("SESSION_COVERAGE_INCOMPLETE")
        if not action_ok:
            blockers.append("CORPORATE_ACTIONS_UNVERIFIED")
        if not semantics_ok:
            blockers.append("PRICE_SEMANTICS_UNVERIFIED")

        ticker_reports.append(
            TickerDataGate(
                ticker=ticker,
                session_coverage_complete=coverage.complete,
                corporate_actions_verified=action_ok,
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
