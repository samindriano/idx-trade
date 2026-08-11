from __future__ import annotations

import numpy as np
import pandas as pd

from .security_master import normalise_ticker


DIAGNOSTIC_COLUMNS = (
    "event_key",
    "ticker",
    "source_anchor_date",
    "candidate_session",
    "previous_session",
    "session_offset",
    "expected_post_price_ratio",
    "previous_close",
    "candidate_open",
    "candidate_close",
    "observed_open_ratio",
    "observed_close_ratio",
    "best_relative_error",
    "match_within_10pct",
    "match_within_20pct",
)


def scan_split_candidate_transitions(
    prices: pd.DataFrame,
    events: pd.DataFrame,
    *,
    anchor_date_column: str = "source_anchor_date",
    ticker_column: str = "ticker",
    date_column: str = "date",
    open_column: str = "raw_open",
    close_column: str = "raw_close",
    ratio_old_column: str = "ratio_old",
    ratio_new_column: str = "ratio_new",
    event_key_column: str | None = None,
    window_sessions: int = 5,
) -> pd.DataFrame:
    """Scan nearby trading-session transitions for split-like mechanics.

    This is deliberately *pre-canonical* diagnostics. ``anchor_date_column`` may
    be an IDX source date whose market-effective semantics are not yet proven.
    The function never promotes a candidate session to ``market_effective_date``
    and never rewrites prices.

    For each event it inspects adjacent price transitions around the first
    observed session on/after the source anchor date. A nearby mechanical match
    can identify a date-semantic offset worth validating against official
    evidence. No nearby match can also be informative, e.g. when the upstream
    price panel is already split-adjusted.
    """

    if window_sessions < 0:
        raise ValueError("window_sessions must be non-negative")

    required_events = {
        ticker_column,
        anchor_date_column,
        ratio_old_column,
        ratio_new_column,
    }
    missing_events = required_events - set(events.columns)
    if missing_events:
        raise ValueError(f"Event columns missing: {sorted(missing_events)}")

    required_prices = {ticker_column, date_column, open_column, close_column}
    missing_prices = required_prices - set(prices.columns)
    if missing_prices:
        raise ValueError(f"Price columns missing: {sorted(missing_prices)}")

    panel = prices.copy()
    panel[ticker_column] = panel[ticker_column].map(normalise_ticker)
    panel[date_column] = pd.to_datetime(panel[date_column], errors="coerce").dt.normalize()
    panel[open_column] = pd.to_numeric(panel[open_column], errors="coerce")
    panel[close_column] = pd.to_numeric(panel[close_column], errors="coerce")
    panel = panel.dropna(subset=[ticker_column, date_column]).sort_values(
        [ticker_column, date_column]
    )

    source = events.copy()
    source[ticker_column] = source[ticker_column].map(normalise_ticker)
    source[anchor_date_column] = pd.to_datetime(
        source[anchor_date_column], errors="coerce"
    ).dt.normalize()
    source[ratio_old_column] = pd.to_numeric(source[ratio_old_column], errors="coerce")
    source[ratio_new_column] = pd.to_numeric(source[ratio_new_column], errors="coerce")

    invalid = (
        source[anchor_date_column].isna()
        | source[ratio_old_column].isna()
        | source[ratio_new_column].isna()
        | source[ratio_old_column].le(0)
        | source[ratio_new_column].le(0)
    )
    if invalid.any():
        raise ValueError("Split diagnostic event has invalid anchor date or ratio")

    rows: list[dict[str, object]] = []
    for ordinal, event in enumerate(source.itertuples(index=False)):
        event_map = event._asdict()
        ticker = str(event_map[ticker_column])
        anchor = pd.Timestamp(event_map[anchor_date_column])
        ratio_old = float(event_map[ratio_old_column])
        ratio_new = float(event_map[ratio_new_column])
        expected = ratio_old / ratio_new
        event_key = (
            str(event_map[event_key_column])
            if event_key_column is not None
            else f"{ticker}:{anchor.date().isoformat()}:{ordinal}"
        )

        ticker_rows = panel[panel[ticker_column].eq(ticker)].reset_index(drop=True)
        if len(ticker_rows) < 2:
            continue

        dates = pd.DatetimeIndex(ticker_rows[date_column])
        anchor_pos = int(dates.searchsorted(anchor, side="left"))
        start = max(1, anchor_pos - window_sessions)
        stop = min(len(ticker_rows), anchor_pos + window_sessions + 1)

        for current_pos in range(start, stop):
            previous = ticker_rows.iloc[current_pos - 1]
            current = ticker_rows.iloc[current_pos]
            previous_close = previous[close_column]
            candidate_open = current[open_column]
            candidate_close = current[close_column]

            observed_open = (
                candidate_open / previous_close
                if pd.notna(candidate_open)
                and pd.notna(previous_close)
                and previous_close != 0
                else np.nan
            )
            observed_close = (
                candidate_close / previous_close
                if pd.notna(candidate_close)
                and pd.notna(previous_close)
                and previous_close != 0
                else np.nan
            )
            errors = [
                abs(float(value) / expected - 1.0)
                for value in (observed_open, observed_close)
                if pd.notna(value) and expected != 0
            ]
            best_error = min(errors) if errors else np.nan

            rows.append(
                {
                    "event_key": event_key,
                    "ticker": ticker,
                    "source_anchor_date": anchor,
                    "candidate_session": current[date_column],
                    "previous_session": previous[date_column],
                    "session_offset": current_pos - anchor_pos,
                    "expected_post_price_ratio": expected,
                    "previous_close": previous_close,
                    "candidate_open": candidate_open,
                    "candidate_close": candidate_close,
                    "observed_open_ratio": observed_open,
                    "observed_close_ratio": observed_close,
                    "best_relative_error": best_error,
                    "match_within_10pct": bool(pd.notna(best_error) and best_error <= 0.10),
                    "match_within_20pct": bool(pd.notna(best_error) and best_error <= 0.20),
                }
            )

    return pd.DataFrame(rows, columns=DIAGNOSTIC_COLUMNS)
