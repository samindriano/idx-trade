from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from .research_labels import add_causal_atr


PIVOT_LOOKBACK = 5
LEVEL_LOOKBACK = 60
ROLE_LOOKBACK = 120
MIN_TOUCH_SEPARATION = 3
RETEST_HORIZON = 10
VOLUME_LOOKBACK = 20
CLUSTER_ATR_MULTIPLIER = 0.50
TOUCH_ATR_MULTIPLIER = 0.50
TOUCH_PRICE_FLOOR = 0.01
VOLUME_CONFIRM_MULTIPLIER = 1.50
MIN_VOLUME_BASELINE_OBSERVATIONS = 10

STRUCTURE_LITE_FEATURE_COLUMNS = (
    "structure_support_distance_atr",
    "structure_resistance_distance_atr",
    "structure_support_touch_count_60",
    "structure_resistance_touch_count_60",
    "structure_nearest_level_age_sessions",
    "structure_role_reversal_count_120",
    "structure_breakout_retest_state",
    "structure_breakout_volume_confirmed",
)


@dataclass(frozen=True)
class Pivot:
    session_index: int
    price: float
    atr: float
    side: str
    order: int


@dataclass(frozen=True)
class Cluster:
    side: str
    level: float
    newest_pivot_session: int
    members: tuple[Pivot, ...]
    order: int


@dataclass(frozen=True)
class StructureContext:
    valid: bool
    support: Cluster | None
    resistance: Cluster | None
    support_touch_count: float
    resistance_touch_count: float
    nearest_level_age: float
    role_reversal_count: float


def normalize_official_sessions(values: Iterable[object]) -> pd.DatetimeIndex:
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


def _finite_positive(value: object) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return bool(np.isfinite(number) and number > 0.0)


def _touch_half_width(level: float, atr: float) -> float:
    if not np.isfinite(level) or not _finite_positive(atr):
        return np.nan
    return float(max(TOUCH_ATR_MULTIPLIER * float(atr), TOUCH_PRICE_FLOOR * abs(float(level))))


def _causal_pivots(
    session_index: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    atr: np.ndarray,
) -> tuple[Pivot, ...]:
    """Left-only five-official-session pivots. Gaps break the window."""

    if not (len(session_index) == len(high) == len(low) == len(atr)):
        raise ValueError("pivot inputs must be aligned")
    by_session = {int(value): pos for pos, value in enumerate(session_index)}
    pivots: list[Pivot] = []
    order = 0
    for pos, current_session in enumerate(session_index):
        s = int(current_session)
        required_sessions = list(range(s - (PIVOT_LOOKBACK - 1), s + 1))
        positions = [by_session.get(value) for value in required_sessions]
        if any(value is None for value in positions):
            continue
        idx = np.asarray([int(value) for value in positions], dtype=int)
        hi = high[idx]
        lo = low[idx]
        if not (np.isfinite(hi).all() and np.isfinite(lo).all() and _finite_positive(atr[pos])):
            continue
        if float(high[pos]) == float(np.max(hi)) and float(high[pos]) > 0.0:
            pivots.append(Pivot(s, float(high[pos]), float(atr[pos]), "HIGH", order))
            order += 1
        if float(low[pos]) == float(np.min(lo)) and float(low[pos]) > 0.0:
            pivots.append(Pivot(s, float(low[pos]), float(atr[pos]), "LOW", order))
            order += 1
    return tuple(pivots)


class _UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra = self.find(a)
        rb = self.find(b)
        if ra != rb:
            if ra < rb:
                self.parent[rb] = ra
            else:
                self.parent[ra] = rb


def _clusters_for_signal(
    pivots_by_side: dict[str, tuple[Pivot, ...]],
    pivot_sessions_by_side: dict[str, np.ndarray],
    *,
    signal_session: int,
) -> tuple[Cluster, ...]:
    left = int(signal_session) - LEVEL_LOOKBACK
    right = int(signal_session) - 1
    clusters: list[Cluster] = []
    cluster_order = 0

    for side in ("HIGH", "LOW"):
        all_side = pivots_by_side[side]
        sessions = pivot_sessions_by_side[side]
        lo = int(np.searchsorted(sessions, left, side="left"))
        hi = int(np.searchsorted(sessions, right, side="right"))
        side_pivots = list(all_side[lo:hi])
        n = len(side_pivots)
        if n == 0:
            continue
        uf = _UnionFind(n)
        for i in range(n):
            pi = side_pivots[i]
            for j in range(i + 1, n):
                pj = side_pivots[j]
                tolerance = CLUSTER_ATR_MULTIPLIER * max(float(pi.atr), float(pj.atr))
                if abs(float(pi.price) - float(pj.price)) <= tolerance:
                    uf.union(i, j)

        grouped: dict[int, list[Pivot]] = {}
        for i, pivot in enumerate(side_pivots):
            grouped.setdefault(uf.find(i), []).append(pivot)

        components = sorted(
            grouped.values(),
            key=lambda members: (
                min(member.session_index for member in members),
                float(np.median([member.price for member in members])),
                side,
            ),
        )
        for members in components:
            level = float(np.median(np.asarray([member.price for member in members], dtype=float)))
            newest = max(member.session_index for member in members)
            clusters.append(
                Cluster(
                    side=side,
                    level=level,
                    newest_pivot_session=int(newest),
                    members=tuple(sorted(members, key=lambda item: (item.session_index, item.price, item.order))),
                    order=cluster_order,
                )
            )
            cluster_order += 1

    return tuple(clusters)


def _select_levels(
    clusters: tuple[Cluster, ...],
    *,
    prior_close: float,
) -> tuple[Cluster | None, Cluster | None]:
    if not np.isfinite(prior_close):
        return None, None
    support = [cluster for cluster in clusters if cluster.level <= float(prior_close)]
    resistance = [cluster for cluster in clusters if cluster.level > float(prior_close)]
    support_level = None
    resistance_level = None
    if support:
        support_level = sorted(
            support,
            key=lambda cluster: (-cluster.level, -cluster.newest_pivot_session, cluster.order),
        )[0]
    if resistance:
        resistance_level = sorted(
            resistance,
            key=lambda cluster: (cluster.level, -cluster.newest_pivot_session, cluster.order),
        )[0]
    return support_level, resistance_level


def _window_positions(
    session_index: np.ndarray,
    *,
    start: int,
    end: int,
) -> np.ndarray:
    return np.flatnonzero((session_index >= int(start)) & (session_index <= int(end)))


def _touch_count(
    *,
    level: float,
    signal_session: int,
    session_index: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    atr: np.ndarray,
) -> float:
    positions = _window_positions(
        session_index,
        start=int(signal_session) - LEVEL_LOOKBACK,
        end=int(signal_session) - 1,
    )
    if len(positions) == 0:
        return 0.0
    hi = high[positions]
    lo = low[positions]
    at = atr[positions]
    valid = np.isfinite(hi) & np.isfinite(lo) & np.isfinite(at) & (at > 0.0)
    if not valid.any():
        return 0.0
    positions = positions[valid]
    hi = hi[valid]
    lo = lo[valid]
    at = at[valid]
    widths = np.maximum(TOUCH_ATR_MULTIPLIER * at, TOUCH_PRICE_FLOOR * abs(float(level)))
    touched = (lo <= float(level) + widths) & (hi >= float(level) - widths)
    touch_sessions = session_index[positions[touched]].astype(int)
    if len(touch_sessions) == 0:
        return 0.0
    kept = [int(touch_sessions[0])]
    for s in touch_sessions[1:]:
        if int(s) - kept[-1] >= MIN_TOUCH_SEPARATION:
            kept.append(int(s))
    return float(len(kept))


def _nearest_level_age(
    *,
    signal_session: int,
    prior_atr: float,
    prior_close: float,
    support: Cluster | None,
    resistance: Cluster | None,
) -> float:
    if not _finite_positive(prior_atr) or not np.isfinite(prior_close):
        return np.nan
    candidates: list[tuple[float, int, int]] = []
    if support is not None:
        distance = abs(float(prior_close) - support.level) / float(prior_atr)
        candidates.append((distance, 0, support.newest_pivot_session))
    if resistance is not None:
        distance = abs(resistance.level - float(prior_close)) / float(prior_atr)
        candidates.append((distance, 1, resistance.newest_pivot_session))
    if not candidates:
        return np.nan
    _, _, newest = sorted(candidates, key=lambda item: (item[0], item[1], -item[2]))[0]
    age = int(signal_session) - int(newest)
    if age < 1 or age > ROLE_LOOKBACK:
        raise RuntimeError("nearest Structure-Lite level age escaped expected bounds")
    return float(age)


def _completed_role_reversal(
    *,
    cluster: Cluster,
    signal_session: int,
    session_index: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    atr: np.ndarray,
) -> bool:
    """One causal completed reversal for a current cluster, ending before signal."""

    start_session = max(int(cluster.newest_pivot_session) + 1, int(signal_session) - ROLE_LOOKBACK)
    end_session = int(signal_session) - 1
    positions = _window_positions(session_index, start=start_session - 1, end=end_session)
    if len(positions) < 2:
        return False

    s = session_index[positions].astype(int)
    hi = high[positions]
    lo = low[positions]
    cl = close[positions]
    at = atr[positions]
    level = float(cluster.level)

    valid = np.isfinite(cl) & np.isfinite(at) & (at > 0.0)
    widths = np.where(valid, np.maximum(TOUCH_ATR_MULTIPLIER * at, TOUCH_PRICE_FLOOR * abs(level)), np.nan)

    consecutive = np.diff(s) == 1
    for local in np.flatnonzero(consecutive):
        prev_i = int(local)
        cur_i = int(local + 1)
        crossing_session = int(s[cur_i])
        if crossing_session < start_session:
            continue
        if not (valid[prev_i] and valid[cur_i]):
            continue
        if cluster.side == "HIGH":
            old_side = float(cl[prev_i]) <= level + float(widths[prev_i])
            crossed = float(cl[cur_i]) > level + float(widths[cur_i])
        else:
            old_side = float(cl[prev_i]) >= level - float(widths[prev_i])
            crossed = float(cl[cur_i]) < level - float(widths[cur_i])
        if not (old_side and crossed):
            continue

        retest_mask = (s > crossing_session) & (s <= min(end_session, crossing_session + RETEST_HORIZON))
        for retest_i in np.flatnonzero(retest_mask):
            if not (
                valid[retest_i]
                and np.isfinite(hi[retest_i])
                and np.isfinite(lo[retest_i])
            ):
                continue
            width = float(widths[retest_i])
            touched = float(lo[retest_i]) <= level + width and float(hi[retest_i]) >= level - width
            if cluster.side == "HIGH":
                held_new_side = float(cl[retest_i]) > level + width
            else:
                held_new_side = float(cl[retest_i]) < level - width
            if touched and held_new_side:
                return True
    return False


def _role_reversal_count(
    *,
    clusters: tuple[Cluster, ...],
    signal_session: int,
    session_index: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    atr: np.ndarray,
) -> float:
    if not clusters:
        return np.nan
    count = 0
    for cluster in clusters:
        if int(signal_session) - cluster.newest_pivot_session > ROLE_LOOKBACK:
            continue
        if _completed_role_reversal(
            cluster=cluster,
            signal_session=signal_session,
            session_index=session_index,
            high=high,
            low=low,
            close=close,
            atr=atr,
        ):
            count += 1
    return float(count)


def _context_for_signal(
    *,
    signal_pos: int,
    session_index: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    atr: np.ndarray,
    pivots_by_side: dict[str, tuple[Pivot, ...]],
    pivot_sessions_by_side: dict[str, np.ndarray],
    by_session: dict[int, int],
) -> StructureContext:
    signal_session = int(session_index[signal_pos])
    prior_pos = by_session.get(signal_session - 1)
    if prior_pos is None or not np.isfinite(close[prior_pos]):
        return StructureContext(False, None, None, np.nan, np.nan, np.nan, np.nan)

    clusters = _clusters_for_signal(pivots_by_side, pivot_sessions_by_side, signal_session=signal_session)
    if not clusters:
        return StructureContext(False, None, None, np.nan, np.nan, np.nan, np.nan)

    support, resistance = _select_levels(clusters, prior_close=float(close[prior_pos]))
    support_touch = (
        _touch_count(
            level=support.level,
            signal_session=signal_session,
            session_index=session_index,
            high=high,
            low=low,
            atr=atr,
        )
        if support is not None
        else np.nan
    )
    resistance_touch = (
        _touch_count(
            level=resistance.level,
            signal_session=signal_session,
            session_index=session_index,
            high=high,
            low=low,
            atr=atr,
        )
        if resistance is not None
        else np.nan
    )
    nearest_age = _nearest_level_age(
        signal_session=signal_session,
        prior_atr=float(atr[prior_pos]),
        prior_close=float(close[prior_pos]),
        support=support,
        resistance=resistance,
    )
    reversals = _role_reversal_count(
        clusters=clusters,
        signal_session=signal_session,
        session_index=session_index,
        high=high,
        low=low,
        close=close,
        atr=atr,
    )
    return StructureContext(
        True,
        support,
        resistance,
        support_touch,
        resistance_touch,
        nearest_age,
        reversals,
    )


def _volume_confirmed(
    *,
    trigger_session: int,
    session_index: np.ndarray,
    volume: np.ndarray,
) -> float:
    by_session = {int(value): pos for pos, value in enumerate(session_index)}
    trigger_pos = by_session.get(int(trigger_session))
    if trigger_pos is None or not _finite_positive(volume[trigger_pos]):
        return 0.0
    positions = _window_positions(
        session_index,
        start=int(trigger_session) - VOLUME_LOOKBACK,
        end=int(trigger_session) - 1,
    )
    values = np.asarray(
        [float(volume[pos]) for pos in positions if _finite_positive(volume[pos])],
        dtype=float,
    )
    if len(values) < MIN_VOLUME_BASELINE_OBSERVATIONS:
        return 0.0
    baseline = float(np.median(values))
    if not _finite_positive(baseline):
        return 0.0
    return float(float(volume[trigger_pos]) >= VOLUME_CONFIRM_MULTIPLIER * baseline)


def _event_features(
    *,
    session_index: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray,
    atr: np.ndarray,
    contexts: list[StructureContext],
) -> tuple[np.ndarray, np.ndarray]:
    n = len(session_index)
    state = np.full(n, np.nan, dtype=float)
    volume_confirmed = np.full(n, np.nan, dtype=float)
    by_session = {int(value): pos for pos, value in enumerate(session_index)}
    active: dict[str, object] | None = None

    for pos in range(n):
        s = int(session_index[pos])
        context = contexts[pos]
        atr_t = float(atr[pos]) if np.isfinite(atr[pos]) else np.nan
        if not context.valid or not _finite_positive(atr_t) or not np.isfinite(close[pos]):
            state[pos] = np.nan
            volume_confirmed[pos] = np.nan
            active = None
            continue

        current_state = 0
        trigger_session: int | None = None

        if active is not None:
            age = s - int(active["trigger_session"])
            if age > RETEST_HORIZON or age <= 0:
                active = None
            else:
                level = float(active["level"])
                direction = int(active["direction"])
                width = _touch_half_width(level, atr_t)
                if direction > 0:
                    invalidated = float(close[pos]) < level - width
                    retest = (
                        float(low[pos]) <= level + width
                        and float(high[pos]) >= level - width
                        and float(close[pos]) > level + width
                    )
                    if invalidated:
                        active = None
                    elif retest:
                        current_state = 2
                        trigger_session = int(active["trigger_session"])
                        active = None
                else:
                    invalidated = float(close[pos]) > level + width
                    retest = (
                        float(low[pos]) <= level + width
                        and float(high[pos]) >= level - width
                        and float(close[pos]) < level - width
                    )
                    if invalidated:
                        active = None
                    elif retest:
                        current_state = -2
                        trigger_session = int(active["trigger_session"])
                        active = None

        prior_pos = by_session.get(s - 1)
        if prior_pos is not None and np.isfinite(close[prior_pos]) and _finite_positive(atr[prior_pos]):
            candidates: list[tuple[float, int, float]] = []
            if context.resistance is not None:
                level = float(context.resistance.level)
                prev_width = _touch_half_width(level, float(atr[prior_pos]))
                cur_width = _touch_half_width(level, atr_t)
                if (
                    float(close[prior_pos]) <= level + prev_width
                    and float(close[pos]) > level + cur_width
                ):
                    distance = abs(float(close[prior_pos]) - level) / float(atr[prior_pos])
                    candidates.append((distance, 1, level))
            if context.support is not None:
                level = float(context.support.level)
                prev_width = _touch_half_width(level, float(atr[prior_pos]))
                cur_width = _touch_half_width(level, atr_t)
                if (
                    float(close[prior_pos]) >= level - prev_width
                    and float(close[pos]) < level - cur_width
                ):
                    distance = abs(float(close[prior_pos]) - level) / float(atr[prior_pos])
                    candidates.append((distance, -1, level))
            if candidates:
                chosen = sorted(
                    candidates,
                    key=lambda item: (item[0], 0 if item[1] < 0 else 1, item[2]),
                )[0]
                direction = int(chosen[1])
                level = float(chosen[2])
                current_state = direction
                trigger_session = s
                active = {
                    "direction": direction,
                    "level": level,
                    "trigger_session": s,
                }

        state[pos] = float(current_state)
        volume_confirmed[pos] = (
            _volume_confirmed(
                trigger_session=int(trigger_session),
                session_index=session_index,
                volume=volume,
            )
            if trigger_session is not None
            else 0.0
        )

    return state, volume_confirmed


def _structure_for_ticker(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.sort_values("signal_session_index", kind="mergesort").reset_index(drop=True).copy()
    session_index = pd.to_numeric(work["signal_session_index"], errors="raise").to_numpy(dtype=int)
    if len(session_index) > 1 and np.any(np.diff(session_index) <= 0):
        raise ValueError("Structure-Lite ticker sessions must be strictly increasing")

    high = pd.to_numeric(work["high"], errors="coerce").to_numpy(dtype=float)
    low = pd.to_numeric(work["low"], errors="coerce").to_numpy(dtype=float)
    close = pd.to_numeric(work["close"], errors="coerce").to_numpy(dtype=float)
    volume = pd.to_numeric(work["volume"], errors="coerce").to_numpy(dtype=float)
    atr = pd.to_numeric(work["atr14"], errors="coerce").to_numpy(dtype=float)
    pivots = _causal_pivots(session_index, high, low, atr)
    pivots_by_side = {
        side: tuple(sorted((pivot for pivot in pivots if pivot.side == side), key=lambda item: item.session_index))
        for side in ("HIGH", "LOW")
    }
    pivot_sessions_by_side = {
        side: np.asarray([pivot.session_index for pivot in pivots_by_side[side]], dtype=int)
        for side in ("HIGH", "LOW")
    }
    by_session = {int(value): pos for pos, value in enumerate(session_index)}

    contexts: list[StructureContext] = []
    support_distance = np.full(len(work), np.nan, dtype=float)
    resistance_distance = np.full(len(work), np.nan, dtype=float)

    for pos in range(len(work)):
        context = _context_for_signal(
            signal_pos=pos,
            session_index=session_index,
            high=high,
            low=low,
            close=close,
            atr=atr,
            pivots_by_side=pivots_by_side,
            pivot_sessions_by_side=pivot_sessions_by_side,
            by_session=by_session,
        )
        contexts.append(context)
        atr_t = atr[pos]
        if context.valid and _finite_positive(atr_t) and np.isfinite(close[pos]):
            if context.support is not None:
                support_distance[pos] = (float(close[pos]) - context.support.level) / float(atr_t)
            if context.resistance is not None:
                resistance_distance[pos] = (context.resistance.level - float(close[pos])) / float(atr_t)

    event_state, event_volume = _event_features(
        session_index=session_index,
        high=high,
        low=low,
        close=close,
        volume=volume,
        atr=atr,
        contexts=contexts,
    )

    result = work[["ticker", "date", "signal_session_index"]].copy()
    result["structure_support_distance_atr"] = support_distance
    result["structure_resistance_distance_atr"] = resistance_distance
    result["structure_support_touch_count_60"] = [context.support_touch_count for context in contexts]
    result["structure_resistance_touch_count_60"] = [context.resistance_touch_count for context in contexts]
    result["structure_nearest_level_age_sessions"] = [context.nearest_level_age for context in contexts]
    result["structure_role_reversal_count_120"] = [context.role_reversal_count for context in contexts]
    result["structure_breakout_retest_state"] = event_state
    result["structure_breakout_volume_confirmed"] = event_volume
    return result


def build_structure_lite_features(
    panel: pd.DataFrame,
    official_sessions: Iterable[object],
    *,
    max_signal_session_index: int,
) -> pd.DataFrame:
    """Build frozen V3-B geometry without labels/outcomes or post-boundary rows."""

    required = {"ticker", "date", "high", "low", "close", "volume"}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"Structure-Lite panel missing columns: {sorted(missing)}")
    forbidden_tokens = ("binary_target", "label_status", "actual_up", "realized_return", "outcome")
    present_forbidden = [
        column
        for column in panel.columns
        if any(token in str(column).lower() for token in forbidden_tokens)
    ]
    if present_forbidden:
        raise ValueError(
            "Structure-Lite feature builder must not receive label/outcome columns: "
            f"{sorted(present_forbidden)}"
        )
    if max_signal_session_index <= 0:
        raise ValueError("max_signal_session_index must be positive")

    sessions = normalize_official_sessions(official_sessions)
    if max_signal_session_index > len(sessions):
        raise ValueError("Structure-Lite discovery boundary exceeds official calendar")
    index_by_date = {pd.Timestamp(day): idx + 1 for idx, day in enumerate(sessions)}

    data = panel.copy()
    data["ticker"] = (
        data["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    )
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if data["date"].isna().any():
        raise ValueError("Structure-Lite panel contains invalid dates")
    data["signal_session_index"] = data["date"].map(index_by_date)
    if data["signal_session_index"].isna().any():
        raise ValueError("Structure-Lite panel has dates outside official calendar")
    data["signal_session_index"] = data["signal_session_index"].astype(int)
    data = data[data["signal_session_index"] <= int(max_signal_session_index)].copy()
    if data.empty:
        raise ValueError("Structure-Lite panel is empty inside discovery boundary")
    if data.duplicated(["ticker", "date"]).any():
        raise ValueError("Structure-Lite panel contains duplicate ticker/date rows")
    if "tradability_state" in data.columns:
        state = data["tradability_state"].astype(str).str.upper()
        if not state.eq("ACTIVE").all():
            raise ValueError("Structure-Lite signal-research panel must contain ACTIVE rows only")
    for column in ("high", "low", "close", "volume"):
        values = pd.to_numeric(data[column], errors="coerce")
        if column != "volume" and (values.dropna() <= 0).any():
            raise ValueError(f"Structure-Lite panel contains non-positive {column}")
        if column == "volume" and (values.dropna() < 0).any():
            raise ValueError("Structure-Lite panel contains negative volume")

    data = add_causal_atr(data, window=14)
    pieces = [_structure_for_ticker(group) for _, group in data.groupby("ticker", sort=True)]
    result = pd.concat(pieces, ignore_index=True, sort=False)

    if result.duplicated(["ticker", "date"]).any():
        raise RuntimeError("Structure-Lite builder produced duplicate ticker/date rows")
    if int(result["signal_session_index"].max()) > int(max_signal_session_index):
        raise RuntimeError("Structure-Lite builder escaped the discovery boundary")

    for column in STRUCTURE_LITE_FEATURE_COLUMNS:
        values = pd.to_numeric(result[column], errors="coerce").astype(float)
        if np.isinf(values.to_numpy(dtype=float)).any():
            raise RuntimeError(f"Structure-Lite feature contains infinity: {column}")
        result[column] = values

    event = result["structure_breakout_retest_state"].dropna().astype(int)
    if not set(event.unique()).issubset({-2, -1, 0, 1, 2}):
        raise RuntimeError("Structure-Lite event state escaped frozen state space")
    confirmed = result["structure_breakout_volume_confirmed"].dropna()
    if not set(pd.to_numeric(confirmed, errors="raise").astype(int).unique()).issubset({0, 1}):
        raise RuntimeError("Structure-Lite volume confirmation escaped {0,1}")

    return result.sort_values(["signal_session_index", "ticker"], kind="mergesort").reset_index(drop=True)
