from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from .ranking_v4_3_preregistration import (
    build_session_geometry_features,
    normalized_percentile_rank,
)


TARGET_H5_AVAILABLE = "TARGET_H5_AVAILABLE"
TARGET_H10_AVAILABLE = "TARGET_H10_AVAILABLE"
TARGET_BOTH_AVAILABLE = "TARGET_BOTH_AVAILABLE"
NO_FUTURE_SESSION = "NO_FUTURE_SESSION"
MARKET_ENTRY_UNAVAILABLE = "MARKET_ENTRY_UNAVAILABLE"
TARGET_DATA_UNOBSERVABLE = "TARGET_DATA_UNOBSERVABLE"
PRICE_CONTINUITY_UNRESOLVED = "PRICE_CONTINUITY_UNRESOLVED"
TRADING_MECHANISM_REFERENCE_UNRESOLVED = "TRADING_MECHANISM_REFERENCE_UNRESOLVED"

ACTIVE = "ACTIVE"
NO_TRADE = "NO_TRADE"
SUSPENDED = "SUSPENDED"
UNKNOWN = "UNKNOWN"
AMBIGUOUS = "AMBIGUOUS"

MARKET_STATES = {ACTIVE, NO_TRADE, SUSPENDED, UNKNOWN, AMBIGUOUS}
MECHANISM_UNRESOLVED_STATES = {UNKNOWN, AMBIGUOUS}
ENTRY_UNAVAILABLE_STATES = {NO_TRADE, SUSPENDED}

CONTINUITY_PASSING = {
    "RESOLVED_NO_MECHANICAL_DISCONTINUITY",
    "RESOLVED_SAME_BASIS_ENDPOINTS",
}
CONTINUITY_FAILING = {
    "PRICE_CONTINUITY_UNRESOLVED_COVERAGE",
    "PRICE_CONTINUITY_UNRESOLVED_EVENT",
    "PRICE_CONTINUITY_UNRESOLVED_EFFECTIVE_DATE",
    "PRICE_CONTINUITY_UNRESOLVED_CONFLICT",
}
CONTINUITY_STATES = CONTINUITY_PASSING | CONTINUITY_FAILING

HORIZONS = (5, 10)


@dataclass(frozen=True)
class HorizonResult:
    state: str
    raw_return: float
    entry_market_active: bool
    entry_open_observable: bool
    terminal_market_active: bool
    terminal_close_observable: bool
    continuity_resolved: bool
    continuity_status: str
    entry_date: pd.Timestamp | pd.NaT
    terminal_date: pd.Timestamp | pd.NaT


def _normalize_ticker(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )


def _normalize_date(series: pd.Series, *, name: str) -> pd.Series:
    normalized = pd.to_datetime(series, errors="coerce").dt.tz_localize(None).dt.normalize()
    if normalized.isna().any():
        raise ValueError(f"{name} contains invalid date")
    return normalized


def _normalize_sessions(values: Iterable[object]) -> pd.DatetimeIndex:
    sessions = (
        pd.DatetimeIndex(pd.to_datetime(list(values), errors="coerce"))
        .tz_localize(None)
        .normalize()
        .dropna()
        .unique()
        .sort_values()
    )
    if not len(sessions):
        raise ValueError("official_sessions must not be empty")
    return sessions


def _strict_boolean(series: pd.Series, *, name: str) -> pd.Series:
    if series.isna().any():
        raise ValueError(f"{name} contains null boolean")
    values = set(series.tolist())
    if not values.issubset({True, False, np.bool_(True), np.bool_(False)}):
        raise ValueError(f"{name} must contain only booleans")
    return series.astype(bool)


def prepare_price_evidence(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "ticker",
        "date",
        "market_state",
        "accepted_open",
        "open_admitted",
        "close",
        "close_admitted",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"price evidence missing columns: {sorted(missing)}")

    out = frame.loc[:, sorted(required)].copy()
    out["ticker"] = _normalize_ticker(out["ticker"])
    out["date"] = _normalize_date(out["date"], name="price evidence")
    if out.duplicated(["ticker", "date"]).any():
        raise ValueError("price evidence contains duplicate ticker/date identity")

    out["market_state"] = out["market_state"].astype(str).str.upper().str.strip()
    unknown_states = sorted(set(out["market_state"]) - MARKET_STATES)
    if unknown_states:
        raise ValueError(f"price evidence contains unsupported market state: {unknown_states}")

    out["open_admitted"] = _strict_boolean(out["open_admitted"], name="open_admitted")
    out["close_admitted"] = _strict_boolean(out["close_admitted"], name="close_admitted")
    out["accepted_open"] = pd.to_numeric(out["accepted_open"], errors="coerce").astype(float)
    out["close"] = pd.to_numeric(out["close"], errors="coerce").astype(float)

    bad_open = out["open_admitted"] & (
        ~np.isfinite(out["accepted_open"]) | out["accepted_open"].le(0.0)
    )
    if bad_open.any():
        raise ValueError("admitted Open must be finite and positive")
    bad_close = out["close_admitted"] & (
        ~np.isfinite(out["close"]) | out["close"].le(0.0)
    )
    if bad_close.any():
        raise ValueError("admitted Close must be finite and positive")

    return out.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)


def prepare_continuity_evidence(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "ticker",
        "signal_date",
        "horizon",
        "continuity_status",
        "policy_id",
        "evidence_id",
        "evidence_sha256",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"continuity evidence missing columns: {sorted(missing)}")

    out = frame.loc[:, sorted(required)].copy()
    out["ticker"] = _normalize_ticker(out["ticker"])
    out["signal_date"] = _normalize_date(out["signal_date"], name="continuity evidence")
    out["horizon"] = pd.to_numeric(out["horizon"], errors="raise").astype(int)
    if not set(out["horizon"]).issubset(set(HORIZONS)):
        raise ValueError("continuity evidence horizon must be exactly 5 or 10")

    out["continuity_status"] = (
        out["continuity_status"].astype(str).str.upper().str.strip()
    )
    unsupported = sorted(set(out["continuity_status"]) - CONTINUITY_STATES)
    if unsupported:
        raise ValueError(f"unsupported continuity state: {unsupported}")

    for column in ("policy_id", "evidence_id", "evidence_sha256"):
        out[column] = out[column].fillna("").astype(str).str.strip()
        if out[column].eq("").any():
            raise ValueError(f"continuity evidence missing provenance field: {column}")
    if (~out["evidence_sha256"].str.fullmatch(r"[0-9a-fA-F]{64}")).any():
        raise ValueError("continuity evidence SHA must be a 64-character hex digest")
    out["evidence_sha256"] = out["evidence_sha256"].str.lower()

    if out.duplicated(["ticker", "signal_date", "horizon"]).any():
        raise ValueError("continuity evidence contains duplicate ticker/signal_date/horizon identity")

    return out.sort_values(
        ["signal_date", "ticker", "horizon"], kind="mergesort"
    ).reset_index(drop=True)


def build_geometry_from_accepted_open(
    signal_frame: pd.DataFrame,
    price_evidence: pd.DataFrame,
) -> pd.DataFrame:
    """Build the frozen Geometry3 block using only admitted exact-session Open.

    The canonical signal H/L/C values are never replaced. Open-dependent
    geometry becomes NaN when exact-session Open is not admitted; no fallback or
    missingness feature is invented here.
    """

    required_signal = {"ticker", "date", "high", "low", "close"}
    missing = required_signal - set(signal_frame.columns)
    if missing:
        raise ValueError(f"signal frame missing columns: {sorted(missing)}")

    signal = signal_frame.copy()
    signal["ticker"] = _normalize_ticker(signal["ticker"])
    signal["date"] = _normalize_date(signal["date"], name="signal frame")
    if signal.duplicated(["ticker", "date"]).any():
        raise ValueError("signal frame contains duplicate ticker/date identity")

    prices = prepare_price_evidence(price_evidence)
    open_view = prices[["ticker", "date", "accepted_open", "open_admitted"]]
    merged = signal.merge(
        open_view,
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )
    admitted = merged["open_admitted"].fillna(False).astype(bool)
    valid_open = admitted & np.isfinite(merged["accepted_open"]) & merged["accepted_open"].gt(0.0)
    merged["open"] = merged["accepted_open"].where(valid_open, np.nan)

    geometry = build_session_geometry_features(merged)
    geometry["geometry_open_admitted"] = valid_open.to_numpy(dtype=bool)
    return geometry


def _lookup_row(
    lookup: dict[tuple[str, int], tuple[str, float, bool, float, bool]],
    ticker: str,
    index: int,
) -> tuple[str, float, bool, float, bool] | None:
    return lookup.get((ticker, int(index)))


def _continuity_status(
    lookup: dict[tuple[str, pd.Timestamp, int], str],
    ticker: str,
    signal_date: pd.Timestamp,
    horizon: int,
) -> str:
    return lookup.get(
        (ticker, pd.Timestamp(signal_date), int(horizon)),
        "PRICE_CONTINUITY_UNRESOLVED_COVERAGE",
    )


def _materialize_horizon(
    *,
    ticker: str,
    signal_date: pd.Timestamp,
    signal_index: int,
    horizon: int,
    sessions: pd.DatetimeIndex,
    price_lookup: dict[tuple[str, int], tuple[str, float, bool, float, bool]],
    continuity_lookup: dict[tuple[str, pd.Timestamp, int], str],
) -> HorizonResult:
    available_state = TARGET_H5_AVAILABLE if horizon == 5 else TARGET_H10_AVAILABLE
    entry_index = int(signal_index) + 1
    terminal_index = int(signal_index) + int(horizon)
    if entry_index >= len(sessions) or terminal_index >= len(sessions):
        return HorizonResult(
            state=NO_FUTURE_SESSION,
            raw_return=np.nan,
            entry_market_active=False,
            entry_open_observable=False,
            terminal_market_active=False,
            terminal_close_observable=False,
            continuity_resolved=False,
            continuity_status="PRICE_CONTINUITY_UNRESOLVED_COVERAGE",
            entry_date=pd.NaT,
            terminal_date=pd.NaT,
        )

    entry_date = pd.Timestamp(sessions[entry_index])
    terminal_date = pd.Timestamp(sessions[terminal_index])
    entry = _lookup_row(price_lookup, ticker, entry_index)
    terminal = _lookup_row(price_lookup, ticker, terminal_index)
    entry_missing = entry is None
    terminal_missing = terminal is None

    entry_state = entry[0] if entry is not None else UNKNOWN
    terminal_state = terminal[0] if terminal is not None else UNKNOWN
    entry_open = entry[1] if entry is not None else np.nan
    entry_open_admitted = bool(entry[2]) if entry is not None else False
    terminal_close = terminal[3] if terminal is not None else np.nan
    terminal_close_admitted = bool(terminal[4]) if terminal is not None else False

    entry_market_active = entry_state == ACTIVE
    terminal_market_active = terminal_state == ACTIVE
    entry_open_observable = (
        entry_market_active
        and entry_open_admitted
        and np.isfinite(entry_open)
        and float(entry_open) > 0.0
    )
    terminal_close_observable = (
        terminal_market_active
        and terminal_close_admitted
        and np.isfinite(terminal_close)
        and float(terminal_close) > 0.0
    )

    continuity_status = _continuity_status(
        continuity_lookup, ticker, signal_date, horizon
    )
    continuity_resolved = continuity_status in CONTINUITY_PASSING

    mechanism_unresolved = (
        (not entry_missing and entry_state in MECHANISM_UNRESOLVED_STATES)
        or (not terminal_missing and terminal_state in MECHANISM_UNRESOLVED_STATES)
    )
    entry_unavailable = not entry_missing and entry_state in ENTRY_UNAVAILABLE_STATES
    data_unobservable = not entry_open_observable or not terminal_close_observable

    # Frozen primary-state precedence. Component flags above remain available so
    # diagnostics do not lose secondary reasons.
    if mechanism_unresolved:
        state = TRADING_MECHANISM_REFERENCE_UNRESOLVED
    elif entry_unavailable:
        state = MARKET_ENTRY_UNAVAILABLE
    elif not continuity_resolved:
        state = PRICE_CONTINUITY_UNRESOLVED
    elif data_unobservable:
        state = TARGET_DATA_UNOBSERVABLE
    else:
        state = available_state

    raw_return = np.nan
    if state == available_state:
        raw_return = float(terminal_close / entry_open - 1.0)

    return HorizonResult(
        state=state,
        raw_return=raw_return,
        entry_market_active=entry_market_active,
        entry_open_observable=entry_open_observable,
        terminal_market_active=terminal_market_active,
        terminal_close_observable=terminal_close_observable,
        continuity_resolved=continuity_resolved,
        continuity_status=continuity_status,
        entry_date=entry_date,
        terminal_date=terminal_date,
    )


def materialize_v4_target_ledger(
    decision_rows: pd.DataFrame,
    official_sessions: Iterable[object],
    price_evidence: pd.DataFrame,
    continuity_evidence: pd.DataFrame,
) -> pd.DataFrame:
    """Materialize the locked V4 H5/H10 target ledger.

    This function is deterministic and fail-closed. Every input decision row is
    retained. Historical execution is separately gated; this implementation is
    intended to be validated on synthetic fixtures before any real V4 target is
    accessed.
    """

    required = {"ticker", "date"}
    missing = required - set(decision_rows.columns)
    if missing:
        raise ValueError(f"decision rows missing columns: {sorted(missing)}")

    sessions = _normalize_sessions(official_sessions)
    index_by_date = {pd.Timestamp(day): idx for idx, day in enumerate(sessions)}

    ledger = decision_rows.copy()
    ledger["ticker"] = _normalize_ticker(ledger["ticker"])
    ledger["date"] = _normalize_date(ledger["date"], name="decision rows")
    if ledger.duplicated(["ticker", "date"]).any():
        raise ValueError("decision rows contain duplicate ticker/date identity")
    ledger["signal_session_index"] = ledger["date"].map(index_by_date)
    if ledger["signal_session_index"].isna().any():
        raise ValueError("decision row date is absent from official session calendar")
    ledger["signal_session_index"] = ledger["signal_session_index"].astype(int)

    prices = prepare_price_evidence(price_evidence)
    prices["session_index"] = prices["date"].map(index_by_date)
    prices = prices[prices["session_index"].notna()].copy()
    prices["session_index"] = prices["session_index"].astype(int)
    price_lookup = {
        (ticker, int(index)): (
            str(market_state),
            float(open_value) if np.isfinite(open_value) else np.nan,
            bool(open_admitted),
            float(close_value) if np.isfinite(close_value) else np.nan,
            bool(close_admitted),
        )
        for ticker, index, market_state, open_value, open_admitted, close_value, close_admitted
        in prices[
            [
                "ticker",
                "session_index",
                "market_state",
                "accepted_open",
                "open_admitted",
                "close",
                "close_admitted",
            ]
        ].itertuples(index=False)
    }

    continuity = prepare_continuity_evidence(continuity_evidence)
    continuity_lookup = {
        (ticker, pd.Timestamp(signal_date), int(horizon)): str(status)
        for ticker, signal_date, horizon, status
        in continuity[
            ["ticker", "signal_date", "horizon", "continuity_status"]
        ].itertuples(index=False)
    }

    for horizon in HORIZONS:
        prefix = f"h{horizon}"
        states: list[str] = []
        returns: list[float] = []
        entry_active: list[bool] = []
        entry_observable: list[bool] = []
        terminal_active: list[bool] = []
        terminal_observable: list[bool] = []
        continuity_ok: list[bool] = []
        continuity_statuses: list[str] = []
        entry_dates: list[pd.Timestamp | pd.NaT] = []
        terminal_dates: list[pd.Timestamp | pd.NaT] = []

        for ticker, signal_date, signal_index in ledger[
            ["ticker", "date", "signal_session_index"]
        ].itertuples(index=False):
            result = _materialize_horizon(
                ticker=str(ticker),
                signal_date=pd.Timestamp(signal_date),
                signal_index=int(signal_index),
                horizon=horizon,
                sessions=sessions,
                price_lookup=price_lookup,
                continuity_lookup=continuity_lookup,
            )
            states.append(result.state)
            returns.append(result.raw_return)
            entry_active.append(result.entry_market_active)
            entry_observable.append(result.entry_open_observable)
            terminal_active.append(result.terminal_market_active)
            terminal_observable.append(result.terminal_close_observable)
            continuity_ok.append(result.continuity_resolved)
            continuity_statuses.append(result.continuity_status)
            entry_dates.append(result.entry_date)
            terminal_dates.append(result.terminal_date)

        ledger[f"target_state_{prefix}"] = states
        ledger[f"r{horizon}"] = returns
        ledger[f"{prefix}_entry_market_active"] = entry_active
        ledger[f"{prefix}_entry_open_observable"] = entry_observable
        ledger[f"{prefix}_terminal_market_active"] = terminal_active
        ledger[f"{prefix}_terminal_close_observable"] = terminal_observable
        ledger[f"{prefix}_continuity_resolved"] = continuity_ok
        ledger[f"{prefix}_continuity_status"] = continuity_statuses
        ledger[f"{prefix}_entry_date"] = entry_dates
        ledger[f"{prefix}_terminal_date"] = terminal_dates

    ledger["target_rank_h5"] = np.nan
    ledger["target_rank_h10"] = np.nan
    for _, group in ledger.groupby("date", sort=False):
        h5_mask = group["target_state_h5"].eq(TARGET_H5_AVAILABLE)
        if h5_mask.any():
            ranked = normalized_percentile_rank(group.loc[h5_mask, "r5"])
            ledger.loc[ranked.index, "target_rank_h5"] = ranked
        h10_mask = group["target_state_h10"].eq(TARGET_H10_AVAILABLE)
        if h10_mask.any():
            ranked = normalized_percentile_rank(group.loc[h10_mask, "r10"])
            ledger.loc[ranked.index, "target_rank_h10"] = ranked

    both_available = (
        ledger["target_state_h5"].eq(TARGET_H5_AVAILABLE)
        & ledger["target_state_h10"].eq(TARGET_H10_AVAILABLE)
    )
    ledger["realized_consensus"] = np.where(
        both_available,
        0.5 * ledger["target_rank_h5"] + 0.5 * ledger["target_rank_h10"],
        np.nan,
    )

    consensus_state: list[str] = []
    precedence = (
        NO_FUTURE_SESSION,
        TRADING_MECHANISM_REFERENCE_UNRESOLVED,
        MARKET_ENTRY_UNAVAILABLE,
        PRICE_CONTINUITY_UNRESOLVED,
        TARGET_DATA_UNOBSERVABLE,
    )
    for h5_state, h10_state, both in zip(
        ledger["target_state_h5"],
        ledger["target_state_h10"],
        both_available,
    ):
        if bool(both):
            consensus_state.append(TARGET_BOTH_AVAILABLE)
            continue
        pair = {str(h5_state), str(h10_state)}
        consensus_state.append(
            next(
                (state for state in precedence if state in pair),
                TARGET_DATA_UNOBSERVABLE,
            )
        )
    ledger["target_state_consensus"] = consensus_state

    if len(ledger) != len(decision_rows):
        raise RuntimeError("target materialization changed decision-row count")
    if ledger.duplicated(["ticker", "date"]).any():
        raise RuntimeError("target materialization produced duplicate decision identity")

    return ledger.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)
