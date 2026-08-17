"""Outcome-blind V4 CA continuity remediation policy.

The policy deliberately avoids effective-date inference.  A ticker with a
certified complete KSEI CA history is accepted only when no active mechanical
or unknown CA record appears in the broad V4 validation period.  Tickers with
any such record are quarantined for every frozen V4 horizon row.  This is more
conservative than trying to place an unresolved CA onto a specific H5/H10
window and therefore does not require post-hoc effective-date choices.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Iterable

import pandas as pd

from .v4_ksei_ca_history import MECHANICAL_FAMILIES, is_active_status, row_dates


HALO_CALENDAR_DAYS = 60
RESOLVED = "RESOLVED_NO_MECHANICAL_DISCONTINUITY"
UNRESOLVED_COVERAGE = "PRICE_CONTINUITY_UNRESOLVED_COVERAGE"
UNRESOLVED_EVENT = "PRICE_CONTINUITY_UNRESOLVED_EFFECTIVE_DATE"


def _timestamp(value: Any) -> pd.Timestamp:
    result = pd.Timestamp(value)
    if result.tz is not None:
        result = result.tz_localize(None)
    return result.normalize()


def row_intersects_period(
    row: dict[str, Any],
    *,
    period_start: Any,
    period_end: Any,
    halo_days: int = HALO_CALENDAR_DAYS,
) -> bool:
    """Return whether any source-native CA date falls in the frozen broad period.

    The fixed 60-calendar-day halo is frozen before provider acquisition.  It
    absorbs timing differences among Cum/Record/Distribution and an unknown
    market-effective date without choosing an event-specific effective date.
    An active mechanical/unknown event with no parseable date is treated as
    intersecting by construction.
    """

    if halo_days < 0:
        raise ValueError("halo_days must be non-negative")
    start = _timestamp(period_start) - timedelta(days=halo_days)
    end = _timestamp(period_end) + timedelta(days=halo_days)
    dates = row_dates(row)
    if not dates:
        return True
    parsed: list[pd.Timestamp] = []
    for value in dates:
        candidate = pd.to_datetime(value, errors="coerce")
        if pd.isna(candidate):
            return True
        parsed.append(_timestamp(candidate))
    return any(start <= value <= end for value in parsed)


def active_risk_rows(
    rows: Iterable[dict[str, Any]],
    *,
    period_start: Any,
    period_end: Any,
) -> list[dict[str, Any]]:
    risk: list[dict[str, Any]] = []
    for row in rows:
        if not is_active_status(str(row.get("status", ""))):
            continue
        family = str(row.get("event_family", "UNKNOWN"))
        if family not in MECHANICAL_FAMILIES and family != "UNKNOWN":
            continue
        if row_intersects_period(
            row, period_start=period_start, period_end=period_end
        ):
            risk.append(dict(row))
    return risk


def classify_ticker_period(
    *,
    coverage_certified: bool,
    rows: Iterable[dict[str, Any]],
    period_start: Any,
    period_end: Any,
    prior_official_candidate_in_period: bool = False,
) -> dict[str, Any]:
    """Classify one ticker without looking at any V4 return or model result."""

    materialized = [dict(row) for row in rows]
    if not coverage_certified:
        return {
            "continuity_status": UNRESOLVED_COVERAGE,
            "reason": "KSEI_REGISTERED_SECURITY_HISTORY_NOT_CERTIFIED",
            "risk_rows": 0,
        }

    risk = active_risk_rows(
        materialized, period_start=period_start, period_end=period_end
    )
    if risk:
        families = sorted({str(row.get("event_family", "UNKNOWN")) for row in risk})
        return {
            "continuity_status": UNRESOLVED_EVENT,
            "reason": "KSEI_ACTIVE_MECHANICAL_OR_UNKNOWN_CA_IN_V4_PERIOD:"
            + "|".join(families),
            "risk_rows": len(risk),
        }

    if prior_official_candidate_in_period:
        # The prior bounded IDX/KSEI evidence found a mechanical candidate but
        # the supposedly complete KSEI history has no corresponding active
        # mechanical/unknown row in the broad period.  Treat that disagreement
        # as a coverage conflict, never as a clean no-event proof.
        return {
            "continuity_status": UNRESOLVED_COVERAGE,
            "reason": "CROSS_SOURCE_CANDIDATE_NOT_REPRESENTED_IN_KSEI_HISTORY",
            "risk_rows": 0,
        }

    return {
        "continuity_status": RESOLVED,
        "reason": "KSEI_COMPLETE_HISTORY_NO_ACTIVE_MECHANICAL_CA_IN_V4_PERIOD",
        "risk_rows": 0,
    }
