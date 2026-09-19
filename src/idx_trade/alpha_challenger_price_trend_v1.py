"""Outcome-blind Price/Trend State V1 alpha challenger overlay.

This module consumes the accepted descriptive Price/Trend State V1 sidecar and
turns only its frozen ``trend_state`` into a fixed, low-weight quality overlay.
It does not fit, inspect outcomes, rescore the incumbent, or write runtime
artifacts.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


STATE_CONTRACT = "PRICE_TREND_CONFIRMATION_STATE_V1"
INCUMBENT_WEIGHT = 0.90
TREND_WEIGHT = 0.10

TREND_STATE_SCORES = {
    "UPTREND": 1.0,
    "EARLY_REVERSAL": 0.75,
    "BASING": 0.5,
    "TRANSITION": 0.5,
    "DOWNTREND": 0.0,
    "INDETERMINATE": 0.5,
}

REQUIRED_COLUMNS = frozenset({"ticker", "feature_session", "trend_state"})
OPTIONAL_GUARD_COLUMNS = frozenset(
    {"state_contract_version", "outcome_blind", "model_fitted", "trade_recommendation"}
)


def build_price_trend_alpha_overlay(frame: pd.DataFrame) -> pd.DataFrame:
    """Map the frozen descriptive trend state to a fixed higher-is-better score."""

    forbidden = [
        str(column)
        for column in frame.columns
        if str(column) not in OPTIONAL_GUARD_COLUMNS
        and any(
            token in str(column).lower()
            for token in ("target", "label", "outcome", "realized", "forward_return")
        )
    ]
    if forbidden:
        raise ValueError(f"price-trend overlay input contains outcome-like columns: {forbidden}")

    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise KeyError(f"missing required columns: {sorted(missing)}")

    if "state_contract_version" in frame.columns:
        values = frame["state_contract_version"].astype(str)
        if not values.eq(STATE_CONTRACT).all():
            raise ValueError("price-trend state contract version mismatch")
    if "outcome_blind" in frame.columns and not frame["outcome_blind"].astype(bool).all():
        raise ValueError("price-trend input is not outcome-blind")
    if "model_fitted" in frame.columns and frame["model_fitted"].astype(bool).any():
        raise ValueError("price-trend input unexpectedly contains fitted state")
    if "trade_recommendation" in frame.columns and frame["trade_recommendation"].astype(bool).any():
        raise ValueError("price-trend input unexpectedly contains trade recommendation")

    out = frame[["ticker", "feature_session", "trend_state"]].copy()
    out["ticker"] = out["ticker"].astype(str).str.upper().str.strip()
    out["feature_session"] = pd.to_datetime(
        out["feature_session"], errors="raise"
    ).dt.tz_localize(None).dt.normalize()
    if out["ticker"].eq("").any() or out.duplicated(["ticker", "feature_session"]).any():
        raise ValueError("price-trend overlay has invalid or duplicate identity")

    out["trend_state"] = out["trend_state"].astype(str).str.upper().str.strip()
    unknown = sorted(set(out["trend_state"]) - set(TREND_STATE_SCORES))
    if unknown:
        raise ValueError(f"unsupported trend state: {unknown}")
    out["price_trend_quality"] = out["trend_state"].map(TREND_STATE_SCORES).astype(float)
    out["price_trend_available"] = out["trend_state"].ne("INDETERMINATE")
    return out[
        [
            "ticker",
            "feature_session",
            "trend_state",
            "price_trend_quality",
            "price_trend_available",
        ]
    ]


def fixed_quality_blend(
    incumbent_alpha_consensus: pd.Series,
    price_trend_quality: pd.Series,
) -> pd.Series:
    """Apply the fixed 90/10 higher-is-better blend."""

    incumbent = pd.to_numeric(incumbent_alpha_consensus, errors="raise").astype(float)
    trend = pd.to_numeric(price_trend_quality, errors="raise").astype(float)
    if len(incumbent) != len(trend):
        raise ValueError("blend inputs must have equal length")
    if not np.isfinite(incumbent.to_numpy()).all() or not np.isfinite(trend.to_numpy()).all():
        raise ValueError("blend inputs must be finite")
    if ((incumbent < 0.0) | (incumbent > 1.0)).any():
        raise ValueError("incumbent alpha must be within [0, 1]")
    if ((trend < 0.0) | (trend > 1.0)).any():
        raise ValueError("price-trend quality must be within [0, 1]")
    return INCUMBENT_WEIGHT * incumbent + TREND_WEIGHT * trend
