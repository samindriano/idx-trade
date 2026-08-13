from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from .coverage import active_price_view
from .security_master import model_eligibility, normalise_ticker


@dataclass(frozen=True)
class UniverseRow:
    as_of_date: str
    ticker: str
    eligible: bool
    eligibility_reason: str
    observed_sessions_since_listing: int
    recent_exchange_sessions: int
    recent_observed_sessions: int
    active_share: float
    median_traded_value: float | None
    liquidity_rank: int | None
    selected: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_dynamic_liquidity_universe(
    as_of_date: pd.Timestamp,
    exchange_sessions: pd.DatetimeIndex,
    price_frames: dict[str, pd.DataFrame],
    security_master: pd.DataFrame,
    tradability_intervals: pd.DataFrame,
    tradability_coverage_windows: pd.DataFrame,
    *,
    tradability_anchors: pd.DataFrame | None = None,
    top_n: int = 200,
    lookback_sessions: int = 60,
    minimum_warmup_sessions: int = 60,
    minimum_active_share: float = 0.80,
) -> pd.DataFrame:
    """Construct an as-of-date universe from model-safe ACTIVE price rows only."""

    as_of_date = pd.Timestamp(as_of_date).normalize()
    sessions = (
        pd.DatetimeIndex(pd.to_datetime(exchange_sessions))
        .tz_localize(None)
        .normalize()
        .unique()
        .sort_values()
    )
    sessions = sessions[sessions <= as_of_date]
    recent_sessions = sessions[-lookback_sessions:]
    recent_set = set(recent_sessions)

    rows: list[UniverseRow] = []
    for raw_ticker, frame in sorted(price_frames.items()):
        ticker = normalise_ticker(raw_ticker)
        data = active_price_view(
            frame,
            ticker,
            security_master,
            tradability_intervals,
            tradability_coverage_windows,
            tradability_anchors=tradability_anchors,
        )
        if data.empty or "date" not in data.columns:
            observed_dates = pd.DatetimeIndex([])
            observed_sessions = 0
            median_value = None
            active_share = 0.0
        else:
            data = data[data["date"].le(as_of_date)].sort_values("date")
            observed_dates = pd.DatetimeIndex(data["date"].drop_duplicates())
            observed_sessions = len(observed_dates)
            recent = data[data["date"].isin(recent_set)]
            recent_observed = recent["date"].nunique()
            active_share = (
                recent_observed / len(recent_sessions)
                if len(recent_sessions)
                else 0.0
            )
            if {"raw_close", "raw_volume"}.issubset(recent.columns) and not recent.empty:
                traded_value = pd.to_numeric(
                    recent["raw_close"], errors="coerce"
                ) * pd.to_numeric(recent["raw_volume"], errors="coerce")
                clean_values = traded_value.replace(
                    [np.inf, -np.inf], np.nan
                ).dropna()
                median_value = float(clean_values.median()) if not clean_values.empty else None
            else:
                median_value = None

        eligibility = model_eligibility(
            security_master,
            tradability_intervals,
            tradability_coverage_windows,
            ticker,
            as_of_date,
            observed_sessions,
            minimum_warmup_sessions,
            tradability_anchors=tradability_anchors,
        )
        eligible = bool(
            eligibility.eligible
            and len(recent_sessions) > 0
            and active_share >= minimum_active_share
            and median_value is not None
        )
        reason = (
            eligibility.reason
            if not eligibility.eligible
            else (
                "LOW_TRADING_ACTIVITY"
                if active_share < minimum_active_share
                else ("NO_LIQUIDITY_DATA" if median_value is None else "ELIGIBLE")
            )
        )
        rows.append(
            UniverseRow(
                as_of_date=as_of_date.date().isoformat(),
                ticker=ticker,
                eligible=eligible,
                eligibility_reason=reason,
                observed_sessions_since_listing=observed_sessions,
                recent_exchange_sessions=len(recent_sessions),
                recent_observed_sessions=len(set(observed_dates) & recent_set),
                active_share=float(active_share),
                median_traded_value=median_value,
                liquidity_rank=None,
                selected=False,
            )
        )

    output = pd.DataFrame([row.to_dict() for row in rows])
    if output.empty:
        return output

    ranked_idx = (
        output[output["eligible"]]
        .sort_values(
            ["median_traded_value", "ticker"],
            ascending=[False, True],
            na_position="last",
        )
        .index
    )
    if len(ranked_idx):
        output.loc[ranked_idx, "liquidity_rank"] = np.arange(1, len(ranked_idx) + 1)
        output.loc[ranked_idx[:top_n], "selected"] = True
    return output.sort_values(
        ["selected", "liquidity_rank", "ticker"],
        ascending=[False, True, True],
        na_position="last",
    ).reset_index(drop=True)
