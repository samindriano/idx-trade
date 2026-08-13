from __future__ import annotations

import pandas as pd

from .security_master import (
    TRADABILITY_COLUMNS,
    canonicalize_tradability_anchors,
    canonicalize_tradability_intervals,
    normalise_market,
    normalise_ticker,
)
from .states import TradabilityState


ANCHOR_DIAGNOSTIC_COLUMNS = (
    "ticker",
    "market",
    "as_of_date",
    "status",
    "diagnostic",
    "source_ref",
)


def _complete_window_for_anchor(
    coverage_windows: pd.DataFrame,
    market: str,
    as_of_date: pd.Timestamp,
) -> pd.Series | None:
    if coverage_windows.empty:
        return None
    market = normalise_market(market)
    date = pd.Timestamp(as_of_date).normalize()
    rows = coverage_windows[
        coverage_windows["market"].isin([market, "ALL"])
        & coverage_windows["is_complete"].astype(bool)
    ].copy()
    if rows.empty:
        return None
    starts = pd.to_datetime(rows["effective_from"], errors="coerce")
    ends = pd.to_datetime(rows["effective_to"], errors="coerce")
    rows = rows[starts.le(date) & ends.notna() & ends.ge(date)]
    if rows.empty:
        return None
    exact = rows[rows["market"].eq(market)]
    chosen = exact if not exact.empty else rows[rows["market"].eq("ALL")]
    if chosen.empty:
        return None
    chosen = chosen.assign(
        _span=(
            pd.to_datetime(chosen["effective_to"])
            - pd.to_datetime(chosen["effective_from"])
        ).dt.days
    ).sort_values(["_span", "effective_from"])
    return chosen.iloc[0]


def _interval_covering_anchor(
    intervals: pd.DataFrame,
    ticker: str,
    market: str,
    as_of_date: pd.Timestamp,
) -> pd.DataFrame:
    if intervals.empty:
        return intervals
    ticker = normalise_ticker(ticker)
    market = normalise_market(market)
    date = pd.Timestamp(as_of_date).normalize()
    rows = intervals[intervals["ticker"].eq(ticker)]
    exact = rows[rows["market"].eq(market)]
    rows = exact if not exact.empty else rows[rows["market"].eq("ALL")]
    if rows.empty:
        return rows
    starts = pd.to_datetime(rows["effective_from"], errors="coerce")
    ends = pd.to_datetime(rows["effective_to"], errors="coerce")
    return rows[
        starts.le(date)
        & (ends.isna() | ends.ge(date))
        & rows["state"].eq(TradabilityState.SUSPENDED.value)
    ]


def _events_for_market(
    events: pd.DataFrame,
    ticker: str,
    market: str,
) -> pd.DataFrame:
    if events.empty:
        return events
    ticker = normalise_ticker(ticker)
    market = normalise_market(market)
    rows = events[events["ticker"].map(normalise_ticker).eq(ticker)].copy()
    if rows.empty:
        return rows
    rows["market"] = rows["market"].map(normalise_market)
    rows = rows[rows["market"].isin([market, "ALL"])]
    if rows.empty:
        return rows
    rows["effective_date"] = pd.to_datetime(
        rows["effective_date"], errors="coerce"
    ).dt.normalize()
    rows = rows.dropna(subset=["effective_date", "action"])
    # Exact-market evidence wins over an ALL-market duplicate on the same date.
    rows["_specific"] = rows["market"].eq(market).astype(int)
    return (
        rows.sort_values(
            ["effective_date", "_specific"], ascending=[True, False]
        )
        .drop_duplicates(["effective_date", "action"], keep="first")
        .drop(columns="_specific")
        .reset_index(drop=True)
    )


def reconcile_boundary_suspension_anchors(
    events: pd.DataFrame,
    intervals: pd.DataFrame,
    compile_diagnostics: pd.DataFrame,
    anchors: pd.DataFrame,
    coverage_windows: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Use authoritative SUSPENDED anchors to resolve left-boundary gaps.

    A SUSPENDED anchor can safely seed state *from the anchor date forward* when
    event discovery is independently complete for the same bounded market
    window. If the next transition is RESUME, the synthetic suspension ends on
    the preceding day. With no later transition, it extends only to the audited
    window end. Nothing before the anchor is inferred.

    ACTIVE anchors do not create intervals; the resolver uses them as state
    anchors directly. Genuine conflicts remain diagnostics and are never
    converted into guessed state.
    """

    canonical_anchors = canonicalize_tradability_anchors(anchors)
    base_intervals = canonicalize_tradability_intervals(intervals)
    diagnostics = compile_diagnostics.copy()
    synthetic_rows: list[dict[str, object]] = []
    anchor_diagnostics: list[dict[str, object]] = []

    suspended = canonical_anchors[
        canonical_anchors["state"].eq(TradabilityState.SUSPENDED.value)
    ]
    for anchor in suspended.itertuples(index=False):
        ticker = normalise_ticker(anchor.ticker)
        market = normalise_market(anchor.market)
        anchor_date = pd.Timestamp(anchor.as_of_date).normalize()
        source_ref = str(anchor.source_ref)

        already_covered = _interval_covering_anchor(
            base_intervals, ticker, market, anchor_date
        )
        if not already_covered.empty:
            anchor_diagnostics.append(
                {
                    "ticker": ticker,
                    "market": market,
                    "as_of_date": anchor_date,
                    "status": "VALIDATED_EXISTING_INTERVAL",
                    "diagnostic": "ANCHOR_MATCHES_COMPILED_SUSPENSION",
                    "source_ref": source_ref,
                }
            )
            continue

        window = _complete_window_for_anchor(
            coverage_windows, market, anchor_date
        )
        if window is None:
            anchor_diagnostics.append(
                {
                    "ticker": ticker,
                    "market": market,
                    "as_of_date": anchor_date,
                    "status": "UNRESOLVED",
                    "diagnostic": "ANCHOR_OUTSIDE_COMPLETE_DISCOVERY_WINDOW",
                    "source_ref": source_ref,
                }
            )
            continue

        window_end = pd.Timestamp(window["effective_to"]).normalize()
        future_events = _events_for_market(events, ticker, market)
        if not future_events.empty:
            future_events = future_events[
                pd.to_datetime(future_events["effective_date"]).gt(anchor_date)
                & pd.to_datetime(future_events["effective_date"]).le(window_end)
            ]

        if future_events.empty:
            synthetic_rows.append(
                {
                    "ticker": ticker,
                    "market": market,
                    "state": TradabilityState.SUSPENDED.value,
                    "effective_from": anchor_date,
                    "effective_to": window_end,
                    "announced_at": pd.NaT,
                    "source": "IDX_ANCHOR_RECONSTRUCTION",
                    "source_ref": source_ref,
                }
            )
            anchor_diagnostics.append(
                {
                    "ticker": ticker,
                    "market": market,
                    "as_of_date": anchor_date,
                    "status": "RESOLVED_TO_WINDOW_END",
                    "diagnostic": "SUSPENDED_ANCHOR_WITH_NO_LATER_TRANSITION",
                    "source_ref": source_ref,
                }
            )
            continue

        first_date = pd.Timestamp(future_events.iloc[0]["effective_date"]).normalize()
        same_day = future_events[
            pd.to_datetime(future_events["effective_date"]).eq(first_date)
        ]
        actions = set(same_day["action"].astype(str))
        if len(actions) != 1:
            anchor_diagnostics.append(
                {
                    "ticker": ticker,
                    "market": market,
                    "as_of_date": anchor_date,
                    "status": "UNRESOLVED",
                    "diagnostic": "CONFLICTING_NEXT_TRANSITIONS",
                    "source_ref": source_ref,
                }
            )
            continue

        action = next(iter(actions))
        if action != "RESUME":
            anchor_diagnostics.append(
                {
                    "ticker": ticker,
                    "market": market,
                    "as_of_date": anchor_date,
                    "status": "UNRESOLVED",
                    "diagnostic": "SUSPENDED_ANCHOR_FOLLOWED_BY_SUSPEND",
                    "source_ref": source_ref,
                }
            )
            continue

        resume = same_day.iloc[0]
        synthetic_rows.append(
            {
                "ticker": ticker,
                "market": market,
                "state": TradabilityState.SUSPENDED.value,
                "effective_from": anchor_date,
                "effective_to": first_date - pd.Timedelta(days=1),
                "announced_at": pd.NaT,
                "source": "IDX_ANCHOR_RECONSTRUCTION",
                "source_ref": f"{source_ref}|{resume.get('source_ref', '')}",
            }
        )
        anchor_diagnostics.append(
            {
                "ticker": ticker,
                "market": market,
                "as_of_date": anchor_date,
                "status": "RESOLVED_BY_RESUME",
                "diagnostic": "BOUNDARY_SUSPENSION_CLOSED_BY_OFFICIAL_RESUME",
                "source_ref": source_ref,
            }
        )

        if not diagnostics.empty and {
            "ticker",
            "market",
            "effective_date",
            "status",
        }.issubset(diagnostics.columns):
            diag_dates = pd.to_datetime(
                diagnostics["effective_date"], errors="coerce"
            ).dt.normalize()
            resolved = (
                diagnostics["ticker"].map(normalise_ticker).eq(ticker)
                & diagnostics["market"].map(normalise_market).eq(market)
                & diag_dates.eq(first_date)
                & diagnostics["status"].eq("UNMATCHED_RESUME")
            )
            diagnostics = diagnostics.loc[~resolved].reset_index(drop=True)

    if synthetic_rows:
        combined = pd.concat(
            [base_intervals, pd.DataFrame(synthetic_rows, columns=TRADABILITY_COLUMNS)],
            ignore_index=True,
        )
        combined = combined.drop_duplicates(
            ["ticker", "market", "state", "effective_from", "effective_to", "source_ref"],
            keep="last",
        )
        output = canonicalize_tradability_intervals(combined)
    else:
        output = base_intervals

    anchor_diag_frame = pd.DataFrame(
        anchor_diagnostics, columns=ANCHOR_DIAGNOSTIC_COLUMNS
    )
    return output, diagnostics, anchor_diag_frame
