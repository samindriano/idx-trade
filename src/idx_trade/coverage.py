from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from .security_master import existence_state, normalise_ticker, tradability_state
from .states import ExistenceState, TradabilityState


@dataclass(frozen=True)
class SecurityCoverage:
    ticker: str
    first_session: str | None
    last_session: str | None
    listed_sessions: int
    expected_active_sessions: int
    observed_active_sessions: int
    missing_expected_sessions: int
    unknown_tradability_sessions: int
    unexpected_nonactive_bars: int
    coverage_ratio: float | None
    max_missing_gap_sessions: int
    complete: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _max_consecutive_missing(expected_dates: list[pd.Timestamp], observed: set[pd.Timestamp]) -> int:
    maximum = current = 0
    for session in expected_dates:
        if session not in observed:
            current += 1
            maximum = max(maximum, current)
        else:
            current = 0
    return maximum


def security_coverage(
    ticker: str,
    exchange_sessions: pd.DatetimeIndex,
    observed_dates: pd.Series | pd.DatetimeIndex,
    security_master: pd.DataFrame,
    tradability_intervals: pd.DataFrame,
    tradability_coverage_windows: pd.DataFrame,
) -> SecurityCoverage:
    """Audit expected-vs-observed daily records for one ticker.

    This deliberately fails closed. An unresolved trading state is not silently
    converted to ACTIVE, and >=N rows alone can never make a security complete.
    """

    ticker = normalise_ticker(ticker)
    sessions = pd.DatetimeIndex(pd.to_datetime(exchange_sessions)).tz_localize(None).normalize().unique().sort_values()
    observed = set(pd.DatetimeIndex(pd.to_datetime(observed_dates, errors="coerce")).dropna().tz_localize(None).normalize())

    listed: list[pd.Timestamp] = []
    active: list[pd.Timestamp] = []
    unknown: list[pd.Timestamp] = []
    nonactive: list[pd.Timestamp] = []

    for session in sessions:
        if existence_state(security_master, ticker, session) is not ExistenceState.LISTED:
            continue
        listed.append(pd.Timestamp(session))
        state = tradability_state(tradability_intervals, tradability_coverage_windows, ticker, session)
        if state is TradabilityState.ACTIVE:
            active.append(pd.Timestamp(session))
        elif state is TradabilityState.UNKNOWN:
            unknown.append(pd.Timestamp(session))
        else:
            nonactive.append(pd.Timestamp(session))

    expected_set = set(active)
    observed_active = expected_set & observed
    missing = expected_set - observed
    unexpected = set(nonactive) & observed
    ratio = (len(observed_active) / len(active)) if active else None
    max_gap = _max_consecutive_missing(active, observed)

    complete = (
        bool(listed)
        and not unknown
        and not missing
        and not unexpected
        and len(active) > 0
    )

    return SecurityCoverage(
        ticker=ticker,
        first_session=listed[0].date().isoformat() if listed else None,
        last_session=listed[-1].date().isoformat() if listed else None,
        listed_sessions=len(listed),
        expected_active_sessions=len(active),
        observed_active_sessions=len(observed_active),
        missing_expected_sessions=len(missing),
        unknown_tradability_sessions=len(unknown),
        unexpected_nonactive_bars=len(unexpected),
        coverage_ratio=ratio,
        max_missing_gap_sessions=max_gap,
        complete=complete,
    )


def coverage_gate(reports: list[SecurityCoverage]) -> dict[str, object]:
    """Universe-level gate. One incomplete required security keeps the gate closed."""

    incomplete = [report for report in reports if not report.complete]
    return {
        "complete": bool(reports) and not incomplete,
        "expected_securities": len(reports),
        "complete_securities": len(reports) - len(incomplete),
        "incomplete_securities": len(incomplete),
        "incomplete_tickers": [report.ticker for report in incomplete],
        "reports": [report.to_dict() for report in reports],
    }
