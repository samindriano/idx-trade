from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from .states import ExistenceState, TradabilityState


SECURITY_COLUMNS = (
    "security_id", "ticker", "company_name", "listed_from", "listed_to", "source"
)
TRADABILITY_COLUMNS = (
    "ticker", "state", "effective_from", "effective_to", "announced_at", "source", "source_ref"
)
COVERAGE_WINDOW_COLUMNS = (
    "effective_from", "effective_to", "source", "is_complete"
)


def normalise_ticker(value: object) -> str:
    return str(value).upper().replace(".JK", "").strip()


def build_security_master(active: pd.DataFrame, delisted: pd.DataFrame) -> pd.DataFrame:
    """Build listing intervals only; tradability is intentionally stored elsewhere."""

    rows = pd.concat([active.copy(), delisted.copy()], ignore_index=True)
    if rows.empty:
        raise ValueError("Security master must not be empty")

    rows["ticker"] = rows["ticker"].map(normalise_ticker)
    rows["listed_from"] = pd.to_datetime(rows["listed_from"], errors="coerce").dt.normalize()
    rows["listed_to"] = pd.to_datetime(rows.get("listed_to"), errors="coerce").dt.normalize()
    rows = rows.dropna(subset=["ticker", "listed_from"])
    rows = rows[rows["ticker"].str.fullmatch(r"[A-Z0-9]{4}", na=False)]

    if "company_name" not in rows.columns:
        rows["company_name"] = ""
    if "source" not in rows.columns:
        rows["source"] = "UNKNOWN"

    # Prefer a delisted row when active+delisted sources describe the same listing interval.
    rows["_has_end"] = rows["listed_to"].notna().astype(int)
    rows = (
        rows.sort_values(["ticker", "listed_from", "_has_end"])
        .drop_duplicates(["ticker", "listed_from"], keep="last")
        .drop(columns="_has_end")
    )

    invalid = rows[rows["listed_to"].notna() & rows["listed_to"].lt(rows["listed_from"])]
    if not invalid.empty:
        raise ValueError(f"Invalid listing intervals for: {invalid['ticker'].tolist()[:10]}")

    rows["security_id"] = "IDX:" + rows["ticker"] + ":" + rows["listed_from"].dt.strftime("%Y%m%d")
    return rows[list(SECURITY_COLUMNS)].sort_values(["ticker", "listed_from"]).reset_index(drop=True)


def existence_state(master: pd.DataFrame, ticker: str, session: pd.Timestamp) -> ExistenceState:
    session = pd.Timestamp(session).normalize()
    ticker = normalise_ticker(ticker)
    rows = master[master["ticker"].eq(ticker)]
    if rows.empty:
        return ExistenceState.NOT_LISTED

    starts = pd.to_datetime(rows["listed_from"])
    ends = pd.to_datetime(rows["listed_to"], errors="coerce")
    if not starts.le(session).any():
        return ExistenceState.NOT_LISTED
    active = starts.le(session) & (ends.isna() | ends.ge(session))
    if active.any():
        return ExistenceState.LISTED
    return ExistenceState.DELISTED


def canonicalize_tradability_intervals(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate exchange-state intervals. Missing intervals never imply ACTIVE."""

    if frame.empty:
        return pd.DataFrame(columns=TRADABILITY_COLUMNS)
    data = frame.copy()
    missing = {"ticker", "state", "effective_from", "source"} - set(data.columns)
    if missing:
        raise ValueError(f"Tradability columns missing: {sorted(missing)}")

    data["ticker"] = data["ticker"].map(normalise_ticker)
    data["state"] = data["state"].map(lambda value: TradabilityState(str(value)).value)
    data["effective_from"] = pd.to_datetime(data["effective_from"], errors="coerce").dt.normalize()
    data["effective_to"] = pd.to_datetime(data.get("effective_to"), errors="coerce").dt.normalize()
    data["announced_at"] = pd.to_datetime(data.get("announced_at"), errors="coerce")
    if "source_ref" not in data.columns:
        data["source_ref"] = ""
    data = data.dropna(subset=["ticker", "effective_from", "source"])

    invalid = data[data["effective_to"].notna() & data["effective_to"].lt(data["effective_from"])]
    if not invalid.empty:
        raise ValueError("Tradability interval ends before it starts")

    # Overlap of conflicting states is forbidden for the same ticker.
    ordered = data.sort_values(["ticker", "effective_from", "effective_to"], na_position="last")
    for ticker, group in ordered.groupby("ticker", sort=False):
        previous_to: pd.Timestamp | None = None
        previous_state: str | None = None
        for row in group.itertuples(index=False):
            current_from = pd.Timestamp(row.effective_from)
            current_to = pd.Timestamp.max.normalize() if pd.isna(row.effective_to) else pd.Timestamp(row.effective_to)
            if previous_to is not None and current_from <= previous_to and row.state != previous_state:
                raise ValueError(f"Conflicting tradability intervals for {ticker}")
            previous_to = max(previous_to, current_to) if previous_to is not None else current_to
            previous_state = row.state

    return ordered[list(TRADABILITY_COLUMNS)].reset_index(drop=True)


def canonicalize_coverage_windows(frame: pd.DataFrame) -> pd.DataFrame:
    """Periods for which suspension/tradability reconstruction is known complete."""

    if frame.empty:
        return pd.DataFrame(columns=COVERAGE_WINDOW_COLUMNS)
    data = frame.copy()
    missing = {"effective_from", "source", "is_complete"} - set(data.columns)
    if missing:
        raise ValueError(f"Coverage-window columns missing: {sorted(missing)}")
    data["effective_from"] = pd.to_datetime(data["effective_from"], errors="coerce").dt.normalize()
    data["effective_to"] = pd.to_datetime(data.get("effective_to"), errors="coerce").dt.normalize()
    data["is_complete"] = data["is_complete"].astype(bool)
    return data.dropna(subset=["effective_from", "source"])[list(COVERAGE_WINDOW_COLUMNS)].sort_values("effective_from").reset_index(drop=True)


def tradability_state(
    intervals: pd.DataFrame,
    coverage_windows: pd.DataFrame,
    ticker: str,
    session: pd.Timestamp,
) -> TradabilityState:
    """Resolve state fail-closed.

    Explicit intervals always win. Outside a declared-complete reconstruction window,
    lack of a suspension record remains UNKNOWN rather than being inferred ACTIVE.
    Within a complete coverage window, the complement of explicit non-active intervals
    may be treated as ACTIVE.
    """

    ticker = normalise_ticker(ticker)
    session = pd.Timestamp(session).normalize()
    rows = intervals[intervals["ticker"].eq(ticker)] if not intervals.empty else intervals
    if not rows.empty:
        starts = pd.to_datetime(rows["effective_from"])
        ends = pd.to_datetime(rows["effective_to"], errors="coerce")
        match = rows[starts.le(session) & (ends.isna() | ends.ge(session))]
        if len(match) > 1 and match["state"].nunique() > 1:
            raise ValueError(f"Ambiguous tradability state for {ticker} on {session.date()}")
        if not match.empty:
            return TradabilityState(str(match.iloc[-1]["state"]))

    if coverage_windows.empty:
        return TradabilityState.UNKNOWN
    starts = pd.to_datetime(coverage_windows["effective_from"])
    ends = pd.to_datetime(coverage_windows["effective_to"], errors="coerce")
    covered = coverage_windows[
        starts.le(session) & (ends.isna() | ends.ge(session)) & coverage_windows["is_complete"].astype(bool)
    ]
    return TradabilityState.ACTIVE if not covered.empty else TradabilityState.UNKNOWN


@dataclass(frozen=True)
class EligibilityDecision:
    eligible: bool
    reason: str
    existence: ExistenceState
    tradability: TradabilityState
    age_sessions: int | None


def model_eligibility(
    master: pd.DataFrame,
    intervals: pd.DataFrame,
    coverage_windows: pd.DataFrame,
    ticker: str,
    session: pd.Timestamp,
    observed_sessions_since_listing: int | None,
    minimum_warmup_sessions: int,
) -> EligibilityDecision:
    existence = existence_state(master, ticker, session)
    if existence is not ExistenceState.LISTED:
        return EligibilityDecision(False, existence.value, existence, TradabilityState.UNKNOWN, observed_sessions_since_listing)
    state = tradability_state(intervals, coverage_windows, ticker, session)
    if state is not TradabilityState.ACTIVE:
        return EligibilityDecision(False, state.value, existence, state, observed_sessions_since_listing)
    if observed_sessions_since_listing is None or observed_sessions_since_listing < minimum_warmup_sessions:
        return EligibilityDecision(False, "IPO_WARMUP", existence, state, observed_sessions_since_listing)
    return EligibilityDecision(True, "ELIGIBLE", existence, state, observed_sessions_since_listing)
