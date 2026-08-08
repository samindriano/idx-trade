from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .states import ExistenceState, TradabilityState


SECURITY_COLUMNS = (
    "security_id",
    "ticker",
    "company_name",
    "listed_from",
    "listed_to",
    "source",
)
TRADABILITY_COLUMNS = (
    "ticker",
    "market",
    "state",
    "effective_from",
    "effective_to",
    "announced_at",
    "source",
    "source_ref",
)
COVERAGE_WINDOW_COLUMNS = (
    "market",
    "effective_from",
    "effective_to",
    "source",
    "is_complete",
    "discovery_basis",
    "left_boundary_basis",
)
TRADABILITY_ANCHOR_COLUMNS = (
    "ticker",
    "market",
    "as_of_date",
    "state",
    "source",
    "source_ref",
    "evidence_type",
)
SUPPORTED_MARKETS = {"REGULAR", "CASH", "NEGOTIATED", "ALL"}


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
    """Canonicalize periods where event-source discovery is independently complete.

    Coverage windows describe source/event completeness only. They deliberately
    do not carry a market-wide initial ACTIVE state; security state must be
    anchored per ticker before the ACTIVE complement can be inferred.
    """

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
    data["is_complete"] = data["is_complete"].astype(bool)
    for column in ("discovery_basis", "left_boundary_basis"):
        if column not in data.columns:
            data[column] = ""
        data[column] = data[column].fillna("").astype(str).str.strip()

    invalid = data[data["effective_to"].notna() & data["effective_to"].lt(data["effective_from"])]
    if not invalid.empty:
        raise ValueError("Coverage window ends before it starts")

    complete_without_basis = data["is_complete"] & (
        data["discovery_basis"].eq("")
        | data["left_boundary_basis"].eq("")
        | data["effective_to"].isna()
    )
    data.loc[complete_without_basis, "is_complete"] = False

    return (
        data.dropna(subset=["market", "effective_from", "source"])[list(COVERAGE_WINDOW_COLUMNS)]
        .sort_values(["market", "effective_from"])
        .reset_index(drop=True)
    )


def canonicalize_tradability_anchors(frame: pd.DataFrame) -> pd.DataFrame:
    """Canonicalize authoritative point-in-time state evidence per security."""

    if frame.empty:
        return pd.DataFrame(columns=TRADABILITY_ANCHOR_COLUMNS)

    data = frame.copy()
    required = {"ticker", "market", "as_of_date", "state", "source", "evidence_type"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Tradability-anchor columns missing: {sorted(missing)}")

    data["ticker"] = data["ticker"].map(normalise_ticker)
    data["market"] = data["market"].map(normalise_market)
    data["as_of_date"] = pd.to_datetime(data["as_of_date"], errors="coerce").dt.normalize()
    data["state"] = data["state"].map(lambda value: TradabilityState(str(value)).value)
    if "source_ref" not in data.columns:
        data["source_ref"] = ""
    for column in ("source", "source_ref", "evidence_type"):
        data[column] = data[column].fillna("").astype(str).str.strip()

    data = data.dropna(subset=["ticker", "market", "as_of_date"])
    data = data[
        data["ticker"].str.fullmatch(r"[A-Z0-9]{4}", na=False)
        & data["source"].ne("")
        & data["evidence_type"].ne("")
    ]

    if data["state"].eq(TradabilityState.UNKNOWN.value).any():
        raise ValueError("UNKNOWN is not an authoritative tradability anchor")

    duplicate = data.duplicated(["ticker", "market", "as_of_date"], keep=False)
    if duplicate.any():
        conflicts = data.loc[duplicate].groupby(["ticker", "market", "as_of_date"])["state"].nunique()
        if (conflicts > 1).any():
            raise ValueError("Conflicting tradability anchors for the same ticker/market/date")
        data = data.drop_duplicates(["ticker", "market", "as_of_date"], keep="last")

    return (
        data[list(TRADABILITY_ANCHOR_COLUMNS)]
        .sort_values(["ticker", "market", "as_of_date"])
        .reset_index(drop=True)
    )


def _matching_interval(rows: pd.DataFrame, session: pd.Timestamp) -> pd.DataFrame:
    if rows.empty:
        return rows
    starts = pd.to_datetime(rows["effective_from"])
    ends = pd.to_datetime(rows["effective_to"], errors="coerce")
    return rows[starts.le(session) & (ends.isna() | ends.ge(session))]


def _matching_interval_for_ticker(
    intervals: pd.DataFrame,
    ticker: str,
    session: pd.Timestamp,
    market: str,
) -> pd.DataFrame:
    if intervals.empty:
        return intervals

    ticker_rows = intervals[intervals["ticker"].eq(ticker)]
    if ticker_rows.empty:
        return ticker_rows

    exact = _matching_interval(ticker_rows[ticker_rows["market"].eq(market)], session)
    fallback = _matching_interval(ticker_rows[ticker_rows["market"].eq("ALL")], session)
    return exact if not exact.empty else fallback


def _complete_window_for_session(
    coverage_windows: pd.DataFrame,
    session: pd.Timestamp,
    market: str,
) -> pd.Series | None:
    if coverage_windows.empty:
        return None

    applicable = coverage_windows[
        coverage_windows["market"].isin([market, "ALL"])
        & coverage_windows["is_complete"].astype(bool)
    ].copy()
    if applicable.empty:
        return None

    starts = pd.to_datetime(applicable["effective_from"])
    ends = pd.to_datetime(applicable["effective_to"], errors="coerce")
    applicable = applicable[starts.le(session) & ends.notna() & ends.ge(session)]
    if applicable.empty:
        return None

    exact = applicable[applicable["market"].eq(market)]
    chosen = exact if not exact.empty else applicable[applicable["market"].eq("ALL")]
    if chosen.empty:
        return None

    chosen = chosen.assign(
        _span=(pd.to_datetime(chosen["effective_to"]) - pd.to_datetime(chosen["effective_from"])).dt.days
    ).sort_values(["_span", "effective_from"])
    return chosen.iloc[0]


def _anchors_for_window(
    anchors: pd.DataFrame,
    ticker: str,
    market: str,
    window: pd.Series,
) -> pd.DataFrame:
    if anchors.empty:
        return anchors

    rows = anchors[anchors["ticker"].eq(ticker)]
    if rows.empty:
        return rows

    exact = rows[rows["market"].eq(market)]
    rows = exact if not exact.empty else rows[rows["market"].eq("ALL")]
    if rows.empty:
        return rows

    start = pd.Timestamp(window["effective_from"]).normalize()
    end = pd.Timestamp(window["effective_to"]).normalize()
    dates = pd.to_datetime(rows["as_of_date"])
    return rows[dates.ge(start) & dates.le(end)]


def _validate_anchor_consistency(
    intervals: pd.DataFrame,
    anchors: pd.DataFrame,
    ticker: str,
    market: str,
) -> None:
    """Ensure anchors agree with explicit intervals before inferring complements."""

    for row in anchors.itertuples(index=False):
        anchor_date = pd.Timestamp(row.as_of_date).normalize()
        explicit = _matching_interval_for_ticker(intervals, ticker, anchor_date, market)
        implied = (
            TradabilityState(str(explicit.iloc[-1]["state"]))
            if not explicit.empty
            else TradabilityState.ACTIVE
        )
        anchored = TradabilityState(str(row.state))
        if anchored is not implied:
            raise ValueError(
                "Tradability anchor conflicts with reconstructed event state for "
                f"{ticker}/{market} on {anchor_date.date()}: "
                f"anchor={anchored.value}, reconstructed={implied.value}"
            )


def tradability_state(
    intervals: pd.DataFrame,
    coverage_windows: pd.DataFrame,
    ticker: str,
    session: pd.Timestamp,
    market: str = "REGULAR",
    anchors: pd.DataFrame | None = None,
) -> TradabilityState:
    """Resolve market-specific state from explicit events + per-security anchors.

    Explicit market intervals always win. The ACTIVE complement is available
    only inside a complete event-discovery window and only after authoritative
    anchor evidence exists for that ticker in the same window.
    """

    ticker = normalise_ticker(ticker)
    market = normalise_market(market)
    session = pd.Timestamp(session).normalize()

    explicit = _matching_interval_for_ticker(intervals, ticker, session, market)
    if len(explicit) > 1 and explicit["state"].nunique() > 1:
        raise ValueError(f"Ambiguous tradability state for {ticker}/{market} on {session.date()}")
    if not explicit.empty:
        return TradabilityState(str(explicit.iloc[-1]["state"]))

    window = _complete_window_for_session(coverage_windows, session, market)
    if window is None:
        return TradabilityState.UNKNOWN

    anchor_frame = (
        canonicalize_tradability_anchors(anchors)
        if anchors is not None
        else pd.DataFrame(columns=TRADABILITY_ANCHOR_COLUMNS)
    )
    applicable_anchors = _anchors_for_window(anchor_frame, ticker, market, window)
    if applicable_anchors.empty:
        return TradabilityState.UNKNOWN

    _validate_anchor_consistency(intervals, applicable_anchors, ticker, market)
    return TradabilityState.ACTIVE


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
    tradability_anchors: pd.DataFrame | None = None,
) -> EligibilityDecision:
    existence = existence_state(master, ticker, session)
    if existence is not ExistenceState.LISTED:
        return EligibilityDecision(False, existence.value, existence, TradabilityState.UNKNOWN, observed_sessions_since_listing)
    state = tradability_state(
        intervals,
        coverage_windows,
        ticker,
        session,
        market=market,
        anchors=tradability_anchors,
    )
    if state is not TradabilityState.ACTIVE:
        return EligibilityDecision(False, state.value, existence, state, observed_sessions_since_listing)
    if observed_sessions_since_listing is None or observed_sessions_since_listing < minimum_warmup_sessions:
        return EligibilityDecision(False, "IPO_WARMUP", existence, state, observed_sessions_since_listing)
    return EligibilityDecision(True, "ELIGIBLE", existence, state, observed_sessions_since_listing)
