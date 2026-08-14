"""Outcome-blind Foreign Flow V2 representation features.

V2 separates current-turnover participation from abnormal flow magnitude,
relative preference, accumulation dynamics, and flow/price divergence.
Every source-session value at session t is assigned only to the next official
feature session t+1.
"""
from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

PRIOR_LIQUIDITY_LOOKBACK = 20
MIN_PRIOR_LIQUIDITY_OBSERVATIONS = 10
HISTORY_PERCENTILE_LOOKBACK = 120
MIN_HISTORY_PERCENTILE_OBSERVATIONS = 60
SHORT_WINDOW = 5
MEDIUM_WINDOW = 20
STREAK_CAP = 10

FEATURE_COLUMNS_V2 = (
    "foreign_participation_1",
    "foreign_flow_shock_1",
    "foreign_flow_shock_mean_5",
    "foreign_flow_shock_mean_20",
    "foreign_flow_shock_percentile_120",
    "xs_rank_foreign_flow_shock_1",
    "xs_rank_foreign_flow_shock_mean_5",
    "foreign_weighted_persistence_5",
    "foreign_weighted_persistence_20",
    "foreign_signed_streak_10",
    "foreign_flow_acceleration_5_20",
    "foreign_flow_price_divergence_5",
    "foreign_flow_price_divergence_20",
)

OUTPUT_COLUMNS_V2 = (
    "ticker",
    "feature_session",
    "flow_through_session",
    *FEATURE_COLUMNS_V2,
)


def _date(value: object) -> pd.Timestamp:
    parsed = pd.Timestamp(value)
    if pd.isna(parsed):
        raise ValueError(f"invalid date: {value!r}")
    if parsed.tzinfo is not None:
        parsed = parsed.tz_convert("Asia/Jakarta").tz_localize(None)
    return parsed.normalize()


def _sessions(values: Iterable[object]) -> pd.DatetimeIndex:
    result = pd.DatetimeIndex([_date(value) for value in values]).sort_values()
    if len(result) == 0 or result.has_duplicates:
        raise ValueError("official sessions are empty or duplicated")
    return result


def _normalise_flow(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "session_date", "foreign_buy", "foreign_sell", "foreign_net", "unit"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"foreign flow missing columns: {sorted(missing)}")
    out = frame.copy()
    out["ticker"] = out["ticker"].astype(str).str.upper().str.strip()
    out["session_date"] = [_date(v) for v in out["session_date"]]
    if out.duplicated(["ticker", "session_date"]).any():
        raise ValueError("foreign flow has duplicate ticker/session rows")
    for column in ("foreign_buy", "foreign_sell", "foreign_net"):
        values = pd.to_numeric(out[column], errors="coerce")
        if values.isna().any() or (~np.isfinite(values)).any() or (values % 1 != 0).any():
            raise ValueError(f"foreign flow has invalid {column}")
        out[column] = values.astype("int64")
    if (out[["foreign_buy", "foreign_sell"]] < 0).any().any():
        raise ValueError("foreign flow has negative buy/sell")
    if not out["foreign_net"].eq(out["foreign_buy"] - out["foreign_sell"]).all():
        raise ValueError("foreign flow net identity mismatch")
    if not out["unit"].astype(str).eq("SHARES").all():
        raise ValueError("foreign flow unit is not SHARES")
    return out.sort_values(["ticker", "session_date"], kind="mergesort").reset_index(drop=True)


def _normalise_volume(frame: pd.DataFrame) -> pd.DataFrame:
    if {"ticker", "date", "raw_volume"}.issubset(frame.columns):
        date_col, volume_col = "date", "raw_volume"
    elif {"ticker", "as_of_date", "volume"}.issubset(frame.columns):
        date_col, volume_col = "as_of_date", "volume"
    else:
        raise ValueError("volume needs (ticker,date,raw_volume) or (ticker,as_of_date,volume)")
    out = frame[["ticker", date_col, volume_col]].rename(columns={date_col: "date", volume_col: "raw_volume"}).copy()
    out["ticker"] = out["ticker"].astype(str).str.upper().str.strip()
    out["date"] = [_date(v) for v in out["date"]]
    out["raw_volume"] = pd.to_numeric(out["raw_volume"], errors="coerce")
    if out.duplicated(["ticker", "date"]).any():
        raise ValueError("volume has duplicate ticker/session rows")
    invalid = out["raw_volume"].notna() & ((~np.isfinite(out["raw_volume"])) | out["raw_volume"].lt(0))
    if invalid.any():
        raise ValueError("volume has invalid negative/infinite values")
    return out.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def _normalise_context(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "date", "universe_primary_liquid", "close_return_5", "close_return_20"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"market context missing columns: {sorted(missing)}")
    forbidden = [
        c for c in frame.columns
        if any(token in str(c).lower() for token in ("binary_target", "label_status", "outcome", "tp_first", "sl_first", "realized"))
    ]
    if forbidden:
        raise ValueError(f"market context must be outcome-blind: {sorted(forbidden)}")
    out = frame[["ticker", "date", "universe_primary_liquid", "close_return_5", "close_return_20"]].copy()
    out["ticker"] = out["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    out["date"] = [_date(v) for v in out["date"]]
    if out.duplicated(["ticker", "date"]).any():
        raise ValueError("market context has duplicate ticker/date rows")
    for c in ("close_return_5", "close_return_20"):
        v = pd.to_numeric(out[c], errors="coerce").astype(float)
        out[c] = v.where(np.isfinite(v))
    out["universe_primary_liquid"] = out["universe_primary_liquid"].astype(bool)
    return out.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def _historical_percentile(current: float, history: np.ndarray) -> float:
    valid = history[np.isfinite(history)]
    if not np.isfinite(current) or len(valid) < MIN_HISTORY_PERCENTILE_OBSERVATIONS:
        return np.nan
    less = float(np.sum(valid < current))
    equal = float(np.sum(valid == current))
    return (less + 0.5 * equal) / float(len(valid))


def _signed_streak(values: np.ndarray, *, cap: int = STREAK_CAP) -> float:
    if len(values) == 0 or not np.isfinite(values[-1]):
        return np.nan
    last_sign = float(np.sign(values[-1]))
    if last_sign == 0.0:
        return 0.0
    count = 0
    for value in values[::-1]:
        if not np.isfinite(value) or float(np.sign(value)) != last_sign:
            break
        count += 1
        if count >= cap:
            break
    return last_sign * float(count) / float(cap)


def _weighted_persistence(values: np.ndarray) -> float:
    if len(values) == 0 or not np.isfinite(values).all():
        return np.nan
    denom = float(np.abs(values).sum())
    if denom == 0.0:
        return 0.0
    return float(values.sum() / denom)


def _ticker_source_features(
    ticker: str,
    sessions: pd.DatetimeIndex,
    flow: pd.DataFrame,
    volume: pd.Series,
) -> pd.DataFrame:
    by_date_flow = flow.set_index("session_date")
    net = np.full(len(sessions), np.nan, dtype=float)
    for i, day in enumerate(sessions):
        if day in by_date_flow.index:
            net[i] = float(by_date_flow.loc[day, "foreign_net"])

    by_date_volume = volume.copy()
    vol = np.full(len(sessions), np.nan, dtype=float)
    for i, day in enumerate(sessions):
        if day in by_date_volume.index:
            vol[i] = float(by_date_volume.loc[day])

    participation = np.full(len(sessions), np.nan, dtype=float)
    valid_current = np.isfinite(net) & np.isfinite(vol) & (vol > 0.0)
    participation[valid_current] = net[valid_current] / vol[valid_current]

    shock = np.full(len(sessions), np.nan, dtype=float)
    for i in range(len(sessions)):
        start = max(0, i - PRIOR_LIQUIDITY_LOOKBACK)
        prior = vol[start:i]
        valid = prior[np.isfinite(prior) & (prior >= 0.0)]
        if len(valid) < MIN_PRIOR_LIQUIDITY_OBSERVATIONS or not np.isfinite(net[i]):
            continue
        baseline = float(np.median(valid))
        if baseline <= 0.0:
            continue
        shock[i] = net[i] / baseline

    mean5 = np.full(len(sessions), np.nan, dtype=float)
    mean20 = np.full(len(sessions), np.nan, dtype=float)
    persist5 = np.full(len(sessions), np.nan, dtype=float)
    persist20 = np.full(len(sessions), np.nan, dtype=float)
    streak10 = np.full(len(sessions), np.nan, dtype=float)
    pct120 = np.full(len(sessions), np.nan, dtype=float)

    for i in range(len(sessions)):
        if i + 1 >= SHORT_WINDOW:
            x5 = shock[i - SHORT_WINDOW + 1 : i + 1]
            if np.isfinite(x5).all():
                mean5[i] = float(np.mean(x5))
                persist5[i] = _weighted_persistence(x5)
        if i + 1 >= MEDIUM_WINDOW:
            x20 = shock[i - MEDIUM_WINDOW + 1 : i + 1]
            if np.isfinite(x20).all():
                mean20[i] = float(np.mean(x20))
                persist20[i] = _weighted_persistence(x20)
        start10 = max(0, i - STREAK_CAP + 1)
        streak10[i] = _signed_streak(net[start10 : i + 1])
        hist_start = max(0, i - HISTORY_PERCENTILE_LOOKBACK)
        pct120[i] = _historical_percentile(shock[i], shock[hist_start:i])

    acceleration = mean5 - mean20
    return pd.DataFrame({
        "ticker": ticker,
        "source_session": sessions,
        "foreign_participation_1": participation,
        "foreign_flow_shock_1": shock,
        "foreign_flow_shock_mean_5": mean5,
        "foreign_flow_shock_mean_20": mean20,
        "foreign_flow_shock_percentile_120": pct120,
        "foreign_weighted_persistence_5": persist5,
        "foreign_weighted_persistence_20": persist20,
        "foreign_signed_streak_10": streak10,
        "foreign_flow_acceleration_5_20": acceleration,
    })


def build_foreign_flow_representation_v2(
    flow_frame: pd.DataFrame,
    volume_frame: pd.DataFrame,
    market_context: pd.DataFrame,
    official_sessions: Iterable[object],
) -> pd.DataFrame:
    """Build V2 Foreign Flow representation without outcomes or model access.

    ``market_context`` is source-session context. Cross-sectional ranks use the
    exact Ranking-V2 convention: average percentile rank within each source
    date's causal primary-liquid universe. Flow and price context from source
    session t are assigned only to official feature session t+1.
    """
    sessions = _sessions(official_sessions)
    flow = _normalise_flow(flow_frame)
    volume = _normalise_volume(volume_frame)
    context = _normalise_context(market_context)

    session_set = set(sessions)
    if not set(flow["session_date"]).issubset(session_set):
        raise ValueError("flow contains dates outside official sessions")
    if not set(volume["date"]).issubset(session_set):
        raise ValueError("volume contains dates outside official sessions")
    if not set(context["date"]).issubset(session_set):
        raise ValueError("market context contains dates outside official sessions")

    pieces: list[pd.DataFrame] = []
    tickers = sorted(set(flow["ticker"]) | set(volume["ticker"]))
    for ticker in tickers:
        tf = flow[flow["ticker"].eq(ticker)].copy()
        tv = volume[volume["ticker"].eq(ticker)].set_index("date")["raw_volume"]
        pieces.append(_ticker_source_features(ticker, sessions, tf, tv))
    source = pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()
    if source.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS_V2)

    source = source.merge(
        context,
        left_on=["ticker", "source_session"],
        right_on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    ).drop(columns=["date"])

    source["xs_rank_foreign_flow_shock_1"] = np.nan
    source["xs_rank_foreign_flow_shock_mean_5"] = np.nan
    source["xs_rank_close_return_5_source"] = np.nan
    source["xs_rank_close_return_20_source"] = np.nan

    primary = source["universe_primary_liquid"].fillna(False).astype(bool)
    primary_frame = source.loc[primary]
    for raw, out in (
        ("foreign_flow_shock_1", "xs_rank_foreign_flow_shock_1"),
        ("foreign_flow_shock_mean_5", "xs_rank_foreign_flow_shock_mean_5"),
        ("close_return_5", "xs_rank_close_return_5_source"),
        ("close_return_20", "xs_rank_close_return_20_source"),
    ):
        ranks = primary_frame.groupby("source_session", sort=True)[raw].rank(method="average", pct=True)
        source.loc[ranks.index, out] = ranks.astype(float)

    source["xs_rank_foreign_flow_shock_mean_20"] = np.nan
    ranks20 = primary_frame.groupby("source_session", sort=True)["foreign_flow_shock_mean_20"].rank(method="average", pct=True)
    source.loc[ranks20.index, "xs_rank_foreign_flow_shock_mean_20"] = ranks20.astype(float)

    source["foreign_flow_price_divergence_5"] = (
        source["xs_rank_foreign_flow_shock_mean_5"] - source["xs_rank_close_return_5_source"]
    )
    source["foreign_flow_price_divergence_20"] = (
        source["xs_rank_foreign_flow_shock_mean_20"] - source["xs_rank_close_return_20_source"]
    )

    next_by_day = {sessions[i]: sessions[i + 1] for i in range(len(sessions) - 1)}
    source["feature_session"] = source["source_session"].map(next_by_day)
    source = source[source["feature_session"].notna()].copy()
    source = source.rename(columns={"source_session": "flow_through_session"})

    for column in FEATURE_COLUMNS_V2:
        values = pd.to_numeric(source[column], errors="coerce").astype(float)
        if np.isinf(values.to_numpy()).any():
            raise RuntimeError(f"V2 feature contains infinity: {column}")
        source[column] = values

    return source[list(OUTPUT_COLUMNS_V2)].sort_values(
        ["feature_session", "ticker"], kind="mergesort"
    ).reset_index(drop=True)
