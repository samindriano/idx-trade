"""Outcome-blind row-level price-evidence bridge for frozen V4 targets.

This module materializes the row schema already required by
``ranking_v4_3_target_execution.prepare_price_evidence`` from the same accepted
Open lineage and market-state semantics used by the outcome-blind V4 target
support census. It does not compute forward returns or inspect target/model
performance.
"""

from __future__ import annotations

from typing import Any, Iterable

import numpy as np
import pandas as pd

from .ranking_v4_3_target_execution import prepare_price_evidence


MARKET_STATES = {"ACTIVE", "NO_TRADE", "SUSPENDED", "UNKNOWN", "AMBIGUOUS"}


def _ticker(values: pd.Series) -> pd.Series:
    return (
        values.astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )


def _date(values: pd.Series, *, label: str) -> pd.Series:
    out = pd.to_datetime(values, errors="coerce").dt.tz_localize(None).dt.normalize()
    if out.isna().any():
        raise RuntimeError(f"INVALID_DATE_COLUMN:{label}")
    return out


def _sessions(values: Iterable[Any]) -> pd.DataFrame:
    dates = pd.DatetimeIndex(pd.to_datetime(list(values), errors="coerce"))
    if dates.isna().any():
        raise RuntimeError("OFFICIAL_CALENDAR_INVALID_DATE")
    dates = dates.tz_localize(None).normalize()
    if dates.duplicated().any():
        raise RuntimeError("OFFICIAL_CALENDAR_DUPLICATE_DATE")
    dates = dates.sort_values()
    return pd.DataFrame({"date": dates, "session_index": np.arange(len(dates), dtype=np.int64)})


def build_market_state_map(
    anchors: pd.DataFrame,
    intervals: pd.DataFrame,
    official_sessions: Iterable[Any],
) -> dict[tuple[str, pd.Timestamp], str]:
    calendar = _sessions(official_sessions)
    date_to_index = dict(zip(calendar["date"], calendar["session_index"]))
    index_to_date = dict(zip(calendar["session_index"], calendar["date"]))

    required_anchor = {"ticker", "market", "as_of_date", "state"}
    required_interval = {"ticker", "market", "state", "effective_from", "effective_to"}
    if not required_anchor.issubset(anchors.columns):
        raise RuntimeError("MARKET_STATE_ANCHOR_COLUMNS_MISSING")
    if not required_interval.issubset(intervals.columns):
        raise RuntimeError("MARKET_STATE_INTERVAL_COLUMNS_MISSING")

    anchor = anchors.copy()
    anchor["ticker"] = _ticker(anchor["ticker"])
    anchor["market"] = anchor["market"].astype(str).str.upper().str.strip()
    anchor["state"] = anchor["state"].astype(str).str.upper().str.strip()
    anchor["as_of_date"] = _date(anchor["as_of_date"], label="anchor.as_of_date")
    regular = anchor[anchor["market"].eq("REGULAR")].copy()
    regular["session_index"] = regular["as_of_date"].map(date_to_index)
    regular = regular[regular["session_index"].notna()].copy()
    grouped = regular.groupby(["ticker", "session_index"])["state"].agg(
        lambda values: tuple(sorted(set(values)))
    )
    states: dict[tuple[str, int], str] = {}
    for (ticker, index), values in grouped.items():
        value = values[0] if len(values) == 1 else "AMBIGUOUS"
        if value not in MARKET_STATES:
            value = "UNKNOWN"
        states[(str(ticker), int(index))] = value

    # Preserve the already-frozen support-census precedence: exact anchor state
    # wins when present; a regular/all-market suspension interval fills only a
    # missing anchor state via setdefault.
    interval = intervals.copy()
    interval["ticker"] = _ticker(interval["ticker"])
    interval["market"] = interval["market"].astype(str).str.upper().str.strip()
    interval["state"] = interval["state"].astype(str).str.upper().str.strip()
    interval = interval[
        interval["market"].isin(["REGULAR", "ALL"])
        & interval["state"].eq("SUSPENDED")
    ]
    last_date = pd.Timestamp(calendar["date"].iloc[-1])
    for row in interval.itertuples(index=False):
        start = pd.to_datetime(row.effective_from, errors="coerce")
        end = pd.to_datetime(row.effective_to, errors="coerce")
        if pd.isna(start):
            raise RuntimeError("SUSPENSION_INTERVAL_INVALID_START")
        start = pd.Timestamp(start).tz_localize(None).normalize()
        end = last_date if pd.isna(end) else pd.Timestamp(end).tz_localize(None).normalize()
        if end < start:
            raise RuntimeError("SUSPENSION_INTERVAL_END_BEFORE_START")
        covered = calendar.loc[calendar["date"].between(start, end), "session_index"]
        for index in covered:
            states.setdefault((str(row.ticker), int(index)), "SUSPENDED")

    return {
        (ticker, pd.Timestamp(index_to_date[index])): state
        for (ticker, index), state in states.items()
        if index in index_to_date
    }


def build_v4_price_evidence(
    panel: pd.DataFrame,
    derivative_open: pd.DataFrame,
    overlay_open: pd.DataFrame,
    anchors: pd.DataFrame,
    intervals: pd.DataFrame,
    official_sessions: Iterable[Any],
) -> pd.DataFrame:
    required_panel = {"ticker", "date", "high", "low", "close"}
    if not required_panel.issubset(panel.columns):
        raise RuntimeError("PRICE_PANEL_COLUMNS_MISSING")
    if not {"ticker", "date", "open"}.issubset(derivative_open.columns):
        raise RuntimeError("OPEN_DERIVATIVE_COLUMNS_MISSING")
    required_overlay = {"ticker", "date", "recovered_open", "panel_high", "panel_low", "panel_close"}
    if not required_overlay.issubset(overlay_open.columns):
        raise RuntimeError("OPEN_OVERLAY_COLUMNS_MISSING")

    base = panel[list(required_panel)].copy()
    base["ticker"] = _ticker(base["ticker"])
    base["date"] = _date(base["date"], label="panel.date")
    if base.duplicated(["ticker", "date"]).any():
        raise RuntimeError("PRICE_PANEL_DUPLICATE_IDENTITY")

    derivative = derivative_open[["ticker", "date", "open"]].copy()
    derivative["ticker"] = _ticker(derivative["ticker"])
    derivative["date"] = _date(derivative["date"], label="derivative.date")
    if derivative.duplicated(["ticker", "date"]).any():
        raise RuntimeError("OPEN_DERIVATIVE_DUPLICATE_IDENTITY")
    key_check = base[["ticker", "date"]].merge(
        derivative[["ticker", "date"]],
        on=["ticker", "date"],
        how="outer",
        indicator=True,
        validate="one_to_one",
    )
    if not key_check["_merge"].eq("both").all():
        raise RuntimeError("OPEN_DERIVATIVE_IDENTITY_MISMATCH")

    overlay = overlay_open[list(required_overlay)].copy()
    overlay["ticker"] = _ticker(overlay["ticker"])
    overlay["date"] = _date(overlay["date"], label="overlay.date")
    if overlay.duplicated(["ticker", "date"]).any():
        raise RuntimeError("OPEN_OVERLAY_DUPLICATE_IDENTITY")
    if not set(zip(overlay["ticker"], overlay["date"])).issubset(
        set(zip(base["ticker"], base["date"]))
    ):
        raise RuntimeError("OPEN_OVERLAY_OUTSIDE_PANEL")

    joined = base.merge(
        derivative.rename(columns={"open": "derivative_open"}),
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    ).merge(
        overlay,
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )
    derivative_value = pd.to_numeric(joined["derivative_open"], errors="coerce")
    recovered_value = pd.to_numeric(joined["recovered_open"], errors="coerce")
    derivative_ok = np.isfinite(derivative_value) & derivative_value.gt(0.0)
    overlay_present = joined["recovered_open"].notna()
    overlay_ok = overlay_present & np.isfinite(recovered_value) & recovered_value.gt(0.0)

    # The accepted overlay is incremental only. A positive derivative Open on
    # an overlay identity would make provenance priority ambiguous and therefore
    # fails closed instead of silently choosing one.
    if (overlay_present & derivative_ok).any():
        raise RuntimeError("OPEN_OVERLAY_OVERLAPS_ADMITTED_DERIVATIVE")

    # Re-attest the accepted overlay against canonical H/L/C identity.
    if overlay_present.any():
        overlay_rows = joined.loc[overlay_present]
        comparisons = (
            np.isclose(pd.to_numeric(overlay_rows["panel_high"], errors="coerce"), pd.to_numeric(overlay_rows["high"], errors="coerce"), rtol=0, atol=1e-9)
            & np.isclose(pd.to_numeric(overlay_rows["panel_low"], errors="coerce"), pd.to_numeric(overlay_rows["low"], errors="coerce"), rtol=0, atol=1e-9)
            & np.isclose(pd.to_numeric(overlay_rows["panel_close"], errors="coerce"), pd.to_numeric(overlay_rows["close"], errors="coerce"), rtol=0, atol=1e-9)
        )
        if not bool(np.all(comparisons)):
            raise RuntimeError("OPEN_OVERLAY_CANONICAL_HLC_MISMATCH")
        low = pd.to_numeric(overlay_rows["low"], errors="coerce")
        high = pd.to_numeric(overlay_rows["high"], errors="coerce")
        open_value = pd.to_numeric(overlay_rows["recovered_open"], errors="coerce")
        if (~np.isfinite(open_value) | open_value.le(0.0) | open_value.lt(low - 1e-9) | open_value.gt(high + 1e-9)).any():
            raise RuntimeError("OPEN_OVERLAY_RECOVERED_OPEN_INVALID")

    accepted_open = derivative_value.where(derivative_ok, recovered_value.where(overlay_ok, np.nan))
    open_admitted = np.isfinite(accepted_open) & accepted_open.gt(0.0)
    close = pd.to_numeric(joined["close"], errors="coerce")
    close_admitted = np.isfinite(close) & close.gt(0.0)

    states = build_market_state_map(anchors, intervals, official_sessions)
    market_state = [states.get((ticker, pd.Timestamp(date)), "UNKNOWN") for ticker, date in zip(joined["ticker"], joined["date"])]

    evidence = pd.DataFrame(
        {
            "ticker": joined["ticker"],
            "date": joined["date"],
            "market_state": market_state,
            "accepted_open": accepted_open,
            "open_admitted": open_admitted.astype(bool),
            "close": close,
            "close_admitted": close_admitted.astype(bool),
        }
    )
    return prepare_price_evidence(evidence)
