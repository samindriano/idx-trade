from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


REGIME_HISTORY = 252
REGIME_MIN_HISTORY = 126
REGIME_CONTEXT_ATOL = 1e-12

REGIME_NORMAL = "NORMAL"
REGIME_STRESS = "STRESS"
REGIME_MISSING = "MISSING_WARMUP"
REGIME_STATES = (REGIME_NORMAL, REGIME_STRESS)

REGIME_SOURCE_COLUMNS = (
    "market_breadth_return_20_positive",
    "market_median_close_return_20",
    "market_median_atr14_over_close",
)

REGIME_AUDIT_COLUMNS = (
    *REGIME_SOURCE_COLUMNS,
    "regime_breadth_q25_prior",
    "regime_return_q25_prior",
    "regime_atr_q75_prior",
    "regime_breadth_stress_vote",
    "regime_return_stress_vote",
    "regime_volatility_stress_vote",
    "stress_votes",
    "regime_state",
)

_BANNED_OUTCOME_COLUMNS = {
    "binary_target",
    "label_status",
    "tp_first",
    "sl_first",
    "outcome",
    "realized_return",
}


def _sessions(values: Iterable[object]) -> pd.DatetimeIndex:
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


def _finite(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").astype(float)
    return values.where(np.isfinite(values))


def extract_market_context(v2_features: pd.DataFrame) -> pd.DataFrame:
    """Return one deterministic outcome-independent market-context row per date."""

    banned = _BANNED_OUTCOME_COLUMNS.intersection(v2_features.columns)
    if banned:
        raise ValueError(f"V3-C regime input may not contain label/outcome columns: {sorted(banned)}")

    required = {"date", "universe_primary_liquid", *REGIME_SOURCE_COLUMNS}
    missing = required - set(v2_features.columns)
    if missing:
        raise ValueError(f"V3-C regime input missing columns: {sorted(missing)}")

    data = v2_features.loc[v2_features["universe_primary_liquid"].astype(bool), ["date", *REGIME_SOURCE_COLUMNS]].copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if data["date"].isna().any():
        raise ValueError("V3-C regime input contains invalid dates")
    for column in REGIME_SOURCE_COLUMNS:
        data[column] = _finite(data[column])

    rows: list[dict[str, object]] = []
    for date, block in data.groupby("date", sort=True):
        row: dict[str, object] = {"date": pd.Timestamp(date)}
        for column in REGIME_SOURCE_COLUMNS:
            values = block[column].dropna().to_numpy(dtype=float)
            if not len(values):
                row[column] = np.nan
                continue
            if float(np.max(values) - np.min(values)) > REGIME_CONTEXT_ATOL:
                raise RuntimeError(f"market context is not date-wide for {date} column={column}")
            row[column] = float(values[0])
        rows.append(row)

    result = pd.DataFrame(rows)
    if result.empty:
        raise ValueError("V3-C regime input produced no market context")
    if result["date"].duplicated().any():
        raise RuntimeError("V3-C market context produced duplicate dates")
    return result.sort_values("date", kind="mergesort").reset_index(drop=True)


def _prior_quantile(values: np.ndarray, *, start: int, end: int, q: float) -> float:
    history = values[start:end]
    finite = history[np.isfinite(history)]
    if len(finite) < REGIME_MIN_HISTORY:
        return np.nan
    return float(np.quantile(finite.astype(np.float64, copy=False), q, method="linear"))


def build_regime_table(
    v2_features: pd.DataFrame,
    official_sessions: Iterable[object],
    *,
    max_signal_session_index: int,
) -> pd.DataFrame:
    """Build the frozen two-state causal regime table through one official session boundary."""

    sessions = _sessions(official_sessions)
    if max_signal_session_index <= 0 or max_signal_session_index > len(sessions):
        raise ValueError("invalid max_signal_session_index")

    context = extract_market_context(v2_features)
    base = pd.DataFrame(
        {
            "signal_session_index": np.arange(1, max_signal_session_index + 1, dtype=int),
            "date": sessions[:max_signal_session_index],
        }
    )
    base = base.merge(context, on="date", how="left", validate="one_to_one")

    breadth = _finite(base[REGIME_SOURCE_COLUMNS[0]]).to_numpy(dtype=float)
    returns = _finite(base[REGIME_SOURCE_COLUMNS[1]]).to_numpy(dtype=float)
    atr = _finite(base[REGIME_SOURCE_COLUMNS[2]]).to_numpy(dtype=float)

    breadth_q25 = np.full(len(base), np.nan, dtype=float)
    return_q25 = np.full(len(base), np.nan, dtype=float)
    atr_q75 = np.full(len(base), np.nan, dtype=float)
    breadth_vote = np.full(len(base), np.nan, dtype=float)
    return_vote = np.full(len(base), np.nan, dtype=float)
    volatility_vote = np.full(len(base), np.nan, dtype=float)
    stress_votes = np.full(len(base), np.nan, dtype=float)
    states = np.full(len(base), REGIME_MISSING, dtype=object)

    for i in range(len(base)):
        start = max(0, i - REGIME_HISTORY)
        end = i  # strictly prior sessions only
        bq = _prior_quantile(breadth, start=start, end=end, q=0.25)
        rq = _prior_quantile(returns, start=start, end=end, q=0.25)
        aq = _prior_quantile(atr, start=start, end=end, q=0.75)
        breadth_q25[i] = bq
        return_q25[i] = rq
        atr_q75[i] = aq

        current = (breadth[i], returns[i], atr[i])
        thresholds = (bq, rq, aq)
        if not all(np.isfinite(value) for value in (*current, *thresholds)):
            continue

        bv = float(breadth[i] <= bq)
        rv = float(returns[i] <= rq)
        vv = float(atr[i] >= aq)
        total = int(bv + rv + vv)
        breadth_vote[i] = bv
        return_vote[i] = rv
        volatility_vote[i] = vv
        stress_votes[i] = float(total)
        states[i] = REGIME_STRESS if total >= 2 else REGIME_NORMAL

    base["regime_breadth_q25_prior"] = breadth_q25
    base["regime_return_q25_prior"] = return_q25
    base["regime_atr_q75_prior"] = atr_q75
    base["regime_breadth_stress_vote"] = breadth_vote
    base["regime_return_stress_vote"] = return_vote
    base["regime_volatility_stress_vote"] = volatility_vote
    base["stress_votes"] = stress_votes
    base["regime_state"] = states

    observed = base[base["regime_state"].isin(REGIME_STATES)]
    if not observed.empty:
        votes = pd.to_numeric(observed["stress_votes"], errors="raise").astype(int)
        expected = np.where(votes.to_numpy() >= 2, REGIME_STRESS, REGIME_NORMAL)
        if not np.array_equal(expected, observed["regime_state"].to_numpy(dtype=object)):
            raise RuntimeError("V3-C 2-of-3 regime state invariant failed")

    return base[["signal_session_index", "date", *REGIME_AUDIT_COLUMNS]].copy()
