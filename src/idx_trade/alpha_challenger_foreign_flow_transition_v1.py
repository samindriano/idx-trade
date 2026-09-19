"""PIT-safe foreign-flow fast/slow transition challenger.

This module is deliberately outcome-blind.  It materializes one fixed state
overlay from the already-audited Foreign Flow V2 representation; it does not
fit, rescore, or alter the incumbent alpha.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {
    "ticker",
    "feature_session",
    "foreign_weighted_persistence_5",
    "foreign_weighted_persistence_20",
}


def build_foreign_flow_transition_overlay(frame: pd.DataFrame) -> pd.DataFrame:
    """Build the frozen fast-minus-slow foreign-flow state overlay.

    Positive values mean that recent five-session foreign-flow persistence is
    stronger than the twenty-session state.  Cross-sectional percentile ranks
    are computed independently within each feature session.  Missing inputs
    receive a neutral rank of 0.5 and are explicitly marked unavailable;
    there is no imputation or forward filling.
    """

    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise KeyError(f"missing required columns: {sorted(missing)}")

    out = frame.copy()
    out["ticker"] = out["ticker"].astype(str).str.upper().str.strip()
    out["feature_session"] = pd.to_datetime(
        out["feature_session"], errors="raise"
    ).dt.normalize()
    if out.duplicated(["ticker", "feature_session"]).any():
        raise ValueError("duplicate ticker/feature_session rows")

    fast = pd.to_numeric(out["foreign_weighted_persistence_5"], errors="raise")
    slow = pd.to_numeric(out["foreign_weighted_persistence_20"], errors="raise")
    valid = np.isfinite(fast.to_numpy()) & np.isfinite(slow.to_numpy())
    raw = pd.Series(np.nan, index=out.index, dtype="float64")
    raw.loc[valid] = fast.loc[valid] - slow.loc[valid]

    rank = raw.groupby(out["feature_session"], sort=False).rank(
        method="average", pct=True
    )
    out["foreign_flow_transition_score"] = raw
    out["foreign_flow_transition_available"] = valid
    out["foreign_flow_transition_rank"] = rank.fillna(0.5)
    return out[
        [
            "ticker",
            "feature_session",
            "foreign_flow_transition_score",
            "foreign_flow_transition_available",
            "foreign_flow_transition_rank",
        ]
    ]
