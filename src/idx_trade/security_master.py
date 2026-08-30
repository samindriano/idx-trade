from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .states import ExistenceState, TradabilityState


SECURITY_COLUMNS = (
    "security_id", "ticker", "company_name", "listed_from", "listed_to", "source"
)
TRADABILITY_COLUMNS = (
    "ticker", "market", "state", "effective_from", "effective_to", "announced_at", "source", "source_ref"
)
COVERAGE_WINDOW_COLUMNS = (
    "market", "effective_from", "effective_to", "source", "is_complete"
)
SUPPORTED_MARKETS = {"REGULAR", "CASH", "NEGOTIATED", "ALL"}


def _strict_boolean(value: object) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    raise ValueError("Coverage-window is_complete must be a strict boolean")


def normalise_ticker(value: object) -> str:
    return str(value).upper().replace(".JK", "").strip()


def normalise_market(value: object) -> str:
    market = str(value).upper().strip()
    if market not in SUPPORTED_MARKETS:
        raise ValueError(f"Unsupported IDX market: {market}")
    return market


def build_security_master(active: pd.DataFrame, delisted: pd.DataFrame) -> pd.DataFrame:
    """Build listing intervals only; tradability is intentionally stored elsewhere."""

    rows = pd.concat([active.copy(), delisted.copy()], ignore_index=True)
    if rows.empty:
        raise ValueError("Security master must not be empty")

    rows["ticker"] = rows["ticker"].map(normalise_ticker)
    rows["listed_from"] = pd.to_datetime(rows["listed_from"], errors="coerce").dt.normalize()
    if "listed_to" not in rows.columns:
        rows["listed_to"] = pd.NaT
    rows["listed_to"] = pd.to_datetime(rows["listed_to"], errors="coerce").dt.normalize()
    rows = rows.dropna(subset=["ticker", "listed_from"])
    rows = rows[rows["ticker"].str.fullmatch(r"[A-Z0-9]{4}", na=False)]

    if "company_name" not in rows.columns:
        rows["company_name"] = ""
    if "source" not in rows.columns:
        rows["source"] = "UNKNOWN"

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
    missing = {"ticker", "market", "state", "effective_from", "source"} - set(data.columns)
    if missing:
        raise ValueError(f"Tradability columns missing: {sorted(missing)}")

    data["ticker"] = data["ticker"].map(normalise_ticker)
    data["market"] = data["market"].map(normalise_market)
    data["state"] = data["state"].map(lambda value: TradabilityState(str(value)).value)
    data["effective_from"] = pd.to_datetime(data["effective_from"], errors="coerce").dt.normalize()
    if "effective_to" not in data.columns:
        data["effective_to"] = pd.NaT
    data["effective_to"] = pd.to_datetime(data["effective_to"], errors="coerce").dt.normalize()
    if "announced_at" not in data.columns:
        data["announced_at"] = pd.NaT
    data["announced_at"] = pd.to_datetime(data["announced_at"], errors="coerce")
    if "source_ref" not in data.columns:
        data["source_ref"] = ""
    data = data.dropna(subset=["ticker", "market", "effective_from", "source"])

    invalid = data[data["effective_to"].notna() & data["effective_to"].lt(data["effective_from"])]
    if not invalid.empty:
        raise ValueError("Tradability interval ends before it starts")

    # Conflicts are forbidden within the same market scope. Market-specific
    # intervals may intentionally overlap an ALL-market interval and override it.
    ordered = data.sort_values(["ticker", "market", "effective_from", "effective_to"], na_position="last")
    for (ticker, market), group in ordered.groupby(["ticker", "market"], sort=False):
        previous_to: pd.Timestamp | None = None
        previous_state: str | None = None
        for row in group.itertuples(index=False):
            current_from = pd.Timestamp(row.effective_from)
            current_to = pd.Timestamp.max.normalize() if pd.isna(row.effective_to) else pd.Timestamp(row.effective_to)
            if previous_to is not None and current_from <= previous_to and row.state != previous_state:
                raise ValueError(f"Conflicting tradability intervals for {ticker}/{market}")
            previous_to = max(previous_to, current_to) if previous_to is not None else current_to
            previous_state = row.state

    return ordered[list(TRADABILITY_COLUMNS)].reset_index(drop=True)


def canonicalize_coverage_windows(frame: pd.DataFrame) -> pd.DataFrame:
    """Periods for which suspension/tradability reconstruction is known complete."""

    if frame.empty:
        return pd.DataFrame(columns=COVERAGE_WINDOW_COLUMNS)
    data = frame.copy()
    missing = {"market", "effective_from", "source", "is_complete"} - set(data.columns)
    if missing:
        raise ValueError(f"Coverage-window columns missing: {sorted(missing)}")
    data["market"] = data["market"].map(normalise_market)
    data["effective_from"] = pd.to_datetime(data["effective_from"], errors="coerce").dt.normalize()
    if "effective_to" not in data.columns:
        data["effective_to"] = pd.NaT
    data["effective_to"] = pd.to_datetime(data["effective_to"], errors="coerce").dt.normalize()
    data["is_complete"] = data["is_complete"].map(_strict_boolean)
    return data.dropna(subset=["market", "effective_from", "source"])[list(COVERAGE_WINDOW_COLUMNS)].sort_values(["market", "effective_from"]).reset_index(drop=True)


def _matching_interval(rows: pd.DataFrame, session: pd.Timestamp) -> pd.DataFrame:
    if rows.empty:
        return rows
    starts = pd.to_datetime(rows["effective_from"])
    ends = pd.to_datetime(rows["effective_to"], errors="coerce")
    return rows[starts.le(session) & (ends.isna() | ends.ge(session))]


def tradability_state(
    intervals: pd.DataFrame,
    coverage_windows: pd.DataFrame,
    ticker: str,
    session: pd.Timestamp,
    market: str = "REGULAR",
) -> TradabilityState:
    """Resolve market-specific state fail-closed.

    Exact-market intervals override `ALL`. Outside a declared-complete coverage
    window, absence of a suspension record remains UNKNOWN.
    """

    ticker = normalise_ticker(ticker)
    market = normalise_market(market)
    session = pd.Timestamp(session).normalize()
    ticker_rows = intervals[intervals["ticker"].eq(ticker)] if not intervals.empty else intervals

    if not ticker_rows.empty:
        exact = _matching_interval(ticker_rows[ticker_rows["market"].eq(market)], session)
        fallback = _matching_interval(ticker_rows[ticker_rows["market"].eq("ALL")], session)
        match = exact if not exact.empty else fallback
        if len(match) > 1 and match["state"].nunique() > 1:
            raise ValueError(f"Ambiguous tradability state for {ticker}/{market} on {session.date()}")
        if not match.empty:
            return TradabilityState(str(match.iloc[-1]["state"]))

    if coverage_windows.empty:
        return TradabilityState.UNKNOWN
    applicable = coverage_windows[coverage_windows["market"].isin([market, "ALL"])]
    if applicable.empty:
        return TradabilityState.UNKNOWN
    starts = pd.to_datetime(applicable["effective_from"])
    ends = pd.to_datetime(applicable["effective_to"], errors="coerce")
    covered = applicable[
        starts.le(session) & (ends.isna() | ends.ge(session)) & applicable["is_complete"].astype(bool)
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
    market: str = "REGULAR",
) -> EligibilityDecision:
    existence = existence_state(master, ticker, session)
    if existence is not ExistenceState.LISTED:
        return EligibilityDecision(False, existence.value, existence, TradabilityState.UNKNOWN, observed_sessions_since_listing)
    state = tradability_state(intervals, coverage_windows, ticker, session, market=market)
    if state is not TradabilityState.ACTIVE:
        return EligibilityDecision(False, state.value, existence, state, observed_sessions_since_listing)
    if observed_sessions_since_listing is None or observed_sessions_since_listing < minimum_warmup_sessions:
        return EligibilityDecision(False, "IPO_WARMUP", existence, state, observed_sessions_since_listing)
    return EligibilityDecision(True, "ELIGIBLE", existence, state, observed_sessions_since_listing)
