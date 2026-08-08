from __future__ import annotations

from pathlib import Path
from typing import Mapping

import pandas as pd

from .coverage import active_price_view
from .security_master import normalise_ticker
from .storage import write_parquet_atomic


def build_model_safe_price_panel(
    price_frames: Mapping[str, pd.DataFrame],
    required_tickers: list[str] | tuple[str, ...],
    security_master: pd.DataFrame,
    tradability_intervals: pd.DataFrame,
    tradability_coverage_windows: pd.DataFrame,
    *,
    tradability_anchors: pd.DataFrame | None = None,
    exchange_sessions: pd.DatetimeIndex | None = None,
) -> pd.DataFrame:
    """Build the canonical model input panel from official ACTIVE sessions only.

    Raw Yahoo artifacts remain untouched for audit. This materialized panel is a
    derived, model-safe view: any provider row whose official point-in-time
    existence/tradability state is not ACTIVE is excluded before feature, label,
    support/resistance, liquidity, or backtest code can see it.
    """

    session_set: set[pd.Timestamp] | None = None
    if exchange_sessions is not None:
        sessions = (
            pd.DatetimeIndex(pd.to_datetime(exchange_sessions))
            .dropna()
            .tz_localize(None)
            .normalize()
            .unique()
        )
        session_set = set(pd.Timestamp(value).normalize() for value in sessions)

    panels: list[pd.DataFrame] = []
    for raw_ticker in sorted({normalise_ticker(value) for value in required_tickers}):
        frame = price_frames.get(raw_ticker, pd.DataFrame())
        safe = active_price_view(
            frame,
            raw_ticker,
            security_master,
            tradability_intervals,
            tradability_coverage_windows,
            tradability_anchors=tradability_anchors,
        )
        if safe.empty:
            continue
        data = safe.copy()
        data["date"] = (
            pd.to_datetime(data["date"], errors="coerce")
            .dt.tz_localize(None)
            .dt.normalize()
        )
        data = data[data["date"].notna()].copy()
        if session_set is not None:
            data = data[data["date"].isin(session_set)]
        if data.empty:
            continue
        data["ticker"] = raw_ticker
        panels.append(data)

    if not panels:
        return pd.DataFrame()

    panel = pd.concat(panels, ignore_index=True, sort=False)
    panel = panel.sort_values(["ticker", "date"]).reset_index(drop=True)
    duplicated = panel.duplicated(["ticker", "date"], keep=False)
    if duplicated.any():
        examples = panel.loc[duplicated, ["ticker", "date"]].head(10).to_dict("records")
        raise ValueError(f"Duplicate model-safe ticker/session rows: {examples}")
    return panel


def write_model_safe_price_panel(
    price_frames: Mapping[str, pd.DataFrame],
    required_tickers: list[str] | tuple[str, ...],
    security_master: pd.DataFrame,
    tradability_intervals: pd.DataFrame,
    tradability_coverage_windows: pd.DataFrame,
    output_path: str | Path,
    *,
    tradability_anchors: pd.DataFrame | None = None,
    exchange_sessions: pd.DatetimeIndex | None = None,
) -> dict[str, object]:
    """Materialize and atomically persist the canonical model-safe panel."""

    panel = build_model_safe_price_panel(
        price_frames,
        required_tickers,
        security_master,
        tradability_intervals,
        tradability_coverage_windows,
        tradability_anchors=tradability_anchors,
        exchange_sessions=exchange_sessions,
    )
    path = Path(output_path)
    write_parquet_atomic(panel, path)
    if panel.empty:
        first_date = last_date = None
        ticker_count = 0
    else:
        dates = pd.to_datetime(panel["date"])
        first_date = dates.min().date().isoformat()
        last_date = dates.max().date().isoformat()
        ticker_count = int(panel["ticker"].nunique())
    return {
        "path": str(path),
        "rows": int(len(panel)),
        "tickers": ticker_count,
        "first_date": first_date,
        "last_date": last_date,
    }
