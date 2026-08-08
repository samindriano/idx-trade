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
    quarantined_nonactive_bars: int
    coverage_ratio: float | None
    max_missing_gap_sessions: int
    price_required: bool
    complete: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _normalised_observed_dates(
    observed: pd.DataFrame | pd.Series | pd.DatetimeIndex,
) -> set[pd.Timestamp]:
    if isinstance(observed, pd.DataFrame):
        if "date" not in observed.columns:
            return set()
        values = observed["date"]
    else:
        values = observed
    return set(
        pd.DatetimeIndex(pd.to_datetime(values, errors="coerce"))
        .dropna()
        .tz_localize(None)
        .normalize()
    )


def _max_consecutive_missing(expected_dates: list[pd.Timestamp], observed: set[pd.Timestamp]) -> int:
    maximum = current = 0
    for session in expected_dates:
        if session not in observed:
            current += 1
            maximum = max(maximum, current)
        else:
            current = 0
    return maximum


def active_price_view(
    frame: pd.DataFrame,
    ticker: str,
    security_master: pd.DataFrame,
    tradability_intervals: pd.DataFrame,
    tradability_coverage_windows: pd.DataFrame,
    *,
    tradability_anchors: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return the model-safe provider rows whose official point state is ACTIVE.

    Raw provider history is preserved elsewhere for auditability. A Yahoo row on
    a session that IDX evidence classifies as NO_TRADE, SUSPENDED, FCA_WATCHLIST,
    DELISTED, or UNKNOWN is not allowed into the research/model price view.

    This helper is not a substitute for DATA GATE: callers must still require
    zero UNKNOWN sessions and zero missing expected ACTIVE sessions before model
    development.
    """

    if frame.empty or "date" not in frame.columns:
        return frame.iloc[0:0].copy()

    ticker = normalise_ticker(ticker)
    data = frame.copy()
    data["date"] = (
        pd.to_datetime(data["date"], errors="coerce")
        .dt.tz_localize(None)
        .dt.normalize()
    )
    data = data[data["date"].notna()].copy()
    keep: list[bool] = []
    for day in data["date"]:
        session = pd.Timestamp(day).normalize()
        if existence_state(security_master, ticker, session) is not ExistenceState.LISTED:
            keep.append(False)
            continue
        state = tradability_state(
            tradability_intervals,
            tradability_coverage_windows,
            ticker,
            session,
            anchors=tradability_anchors,
        )
        keep.append(state is TradabilityState.ACTIVE)
    return data.loc[keep].sort_values("date").reset_index(drop=True)


def security_coverage(
    ticker: str,
    exchange_sessions: pd.DatetimeIndex,
    observed_prices: pd.DataFrame | pd.Series | pd.DatetimeIndex,
    security_master: pd.DataFrame,
    tradability_intervals: pd.DataFrame,
    tradability_coverage_windows: pd.DataFrame,
    tradability_anchors: pd.DataFrame | None = None,
) -> SecurityCoverage:
    """Audit expected-vs-observed daily records for one ticker.

    IDX point evidence is authoritative for whether a Regular-Market execution
    session exists. Provider rows on explicitly non-active sessions are retained
    as audit diagnostics but quarantined from the model-safe price view; they do
    not override exchange truth. UNKNOWN state and missing ACTIVE-session prices
    remain hard failures.
    """

    ticker = normalise_ticker(ticker)
    sessions = (
        pd.DatetimeIndex(pd.to_datetime(exchange_sessions))
        .tz_localize(None)
        .normalize()
        .unique()
        .sort_values()
    )
    observed = _normalised_observed_dates(observed_prices)

    listed: list[pd.Timestamp] = []
    active: list[pd.Timestamp] = []
    unknown: list[pd.Timestamp] = []
    nonactive: list[pd.Timestamp] = []

    for session in sessions:
        if existence_state(security_master, ticker, session) is not ExistenceState.LISTED:
            nonactive.append(pd.Timestamp(session))
            continue
        listed.append(pd.Timestamp(session))
        state = tradability_state(
            tradability_intervals,
            tradability_coverage_windows,
            ticker,
            session,
            anchors=tradability_anchors,
        )
        if state is TradabilityState.ACTIVE:
            active.append(pd.Timestamp(session))
        elif state is TradabilityState.UNKNOWN:
            unknown.append(pd.Timestamp(session))
        else:
            nonactive.append(pd.Timestamp(session))

    expected_set = set(active)
    observed_active = expected_set & observed
    missing = expected_set - observed
    provider_nonactive = set(nonactive) & observed
    ratio = (len(observed_active) / len(active)) if active else None
    max_gap = _max_consecutive_missing(active, observed)

    price_required = bool(active)
    complete = bool(listed) and not unknown and not missing

    return SecurityCoverage(
        ticker=ticker,
        first_session=listed[0].date().isoformat() if listed else None,
        last_session=listed[-1].date().isoformat() if listed else None,
        listed_sessions=len(listed),
        expected_active_sessions=len(active),
        observed_active_sessions=len(observed_active),
        missing_expected_sessions=len(missing),
        unknown_tradability_sessions=len(unknown),
        unexpected_nonactive_bars=len(provider_nonactive),
        quarantined_nonactive_bars=len(provider_nonactive),
        coverage_ratio=ratio,
        max_missing_gap_sessions=max_gap,
        price_required=price_required,
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
        "quarantined_nonactive_bars": sum(
            report.quarantined_nonactive_bars for report in reports
        ),
        "reports": [report.to_dict() for report in reports],
    }
