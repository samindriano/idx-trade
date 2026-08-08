from __future__ import annotations

import pandas as pd

from .security_master import (
    TRADABILITY_ANCHOR_COLUMNS,
    canonicalize_tradability_anchors,
)


EXECUTION_DIAGNOSTIC_COLUMNS = (
    "ticker",
    "as_of_date",
    "status",
    "diagnostic",
    "regular_volume",
    "regular_frequency",
)


def stock_summary_execution_anchors(
    frame: pd.DataFrame,
    *,
    market: str = "REGULAR",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Convert official IDX Stock Summary rows into direct execution-state anchors.

    Positive Regular-Market volume and frequency prove ACTIVE trading on that
    session. Exactly zero Regular-Market volume and frequency prove NO_TRADE.
    NO_TRADE is an execution observation, not a legal suspension claim.
    """

    required = {
        "ticker",
        "as_of_date",
        "volume",
        "frequency",
        "nonregular_volume",
        "nonregular_frequency",
        "source",
        "source_ref",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Stock-summary columns missing: {sorted(missing)}")

    anchors: list[dict[str, object]] = []
    diagnostics: list[dict[str, object]] = []

    for row in frame.itertuples(index=False):
        total_volume = pd.to_numeric(row.volume, errors="coerce")
        total_frequency = pd.to_numeric(row.frequency, errors="coerce")
        nonregular_volume = pd.to_numeric(row.nonregular_volume, errors="coerce")
        nonregular_frequency = pd.to_numeric(
            row.nonregular_frequency, errors="coerce"
        )
        values = (
            total_volume,
            total_frequency,
            nonregular_volume,
            nonregular_frequency,
        )
        if any(pd.isna(value) for value in values):
            diagnostics.append(
                {
                    "ticker": row.ticker,
                    "as_of_date": row.as_of_date,
                    "status": "UNRESOLVED",
                    "diagnostic": "REGULAR_TRADE_METRICS_MISSING",
                    "regular_volume": None,
                    "regular_frequency": None,
                }
            )
            continue

        regular_volume = float(total_volume - nonregular_volume)
        regular_frequency = float(total_frequency - nonregular_frequency)
        if regular_volume < 0 or regular_frequency < 0:
            diagnostics.append(
                {
                    "ticker": row.ticker,
                    "as_of_date": row.as_of_date,
                    "status": "UNRESOLVED",
                    "diagnostic": "REGULAR_TRADE_METRICS_NEGATIVE_AFTER_SUBTRACTION",
                    "regular_volume": regular_volume,
                    "regular_frequency": regular_frequency,
                }
            )
            continue

        if (regular_volume > 0) != (regular_frequency > 0):
            diagnostics.append(
                {
                    "ticker": row.ticker,
                    "as_of_date": row.as_of_date,
                    "status": "UNRESOLVED",
                    "diagnostic": "REGULAR_TRADE_METRICS_INCONSISTENT",
                    "regular_volume": regular_volume,
                    "regular_frequency": regular_frequency,
                }
            )
            continue

        anchors.append(
            {
                "ticker": row.ticker,
                "market": market,
                "as_of_date": row.as_of_date,
                "state": "ACTIVE" if regular_volume > 0 else "NO_TRADE",
                "source": row.source,
                "source_ref": row.source_ref,
                "evidence_type": "IDX_STOCK_SUMMARY_REGULAR_EXECUTION_OBSERVATION",
            }
        )

    anchor_frame = canonicalize_tradability_anchors(pd.DataFrame(anchors))
    diagnostic_frame = pd.DataFrame(
        diagnostics,
        columns=EXECUTION_DIAGNOSTIC_COLUMNS,
    )
    return anchor_frame, diagnostic_frame


def merge_tradability_point_evidence(*frames: pd.DataFrame) -> pd.DataFrame:
    """Merge point evidence while preserving more-specific legal non-trading states.

    NO_TRADE is compatible with SUSPENDED/FCA_WATCHLIST because it only states
    that no Regular-Market transaction occurred. SUSPENDED or FCA_WATCHLIST is
    therefore kept as the more specific state. ACTIVE versus any non-trading
    state is a hard conflict.
    """

    canonical = [canonicalize_tradability_anchors(frame) for frame in frames if not frame.empty]
    if not canonical:
        return canonicalize_tradability_anchors(pd.DataFrame())

    data = pd.concat(canonical, ignore_index=True)
    resolved: list[pd.Series] = []
    keys = ["ticker", "market", "as_of_date"]
    for _, group in data.groupby(keys, sort=False):
        states = set(group["state"])
        if len(states) == 1:
            resolved.append(group.iloc[-1])
            continue
        if states <= {"NO_TRADE", "SUSPENDED"}:
            resolved.append(group[group["state"].eq("SUSPENDED")].iloc[-1])
            continue
        if states <= {"NO_TRADE", "FCA_WATCHLIST"}:
            resolved.append(group[group["state"].eq("FCA_WATCHLIST")].iloc[-1])
            continue
        raise ValueError(
            "Conflicting tradability point evidence for "
            f"{group.iloc[0]['ticker']}/{group.iloc[0]['market']} "
            f"on {pd.Timestamp(group.iloc[0]['as_of_date']).date()}: {sorted(states)}"
        )

    return canonicalize_tradability_anchors(
        pd.DataFrame(resolved, columns=TRADABILITY_ANCHOR_COLUMNS)
    )
