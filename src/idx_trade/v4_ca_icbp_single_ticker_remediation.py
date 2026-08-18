"""Fail-closed helpers for the exact ICBP V4 KSEI coverage retry.

This remediation is intentionally one-ticker only.  It exists because the
accepted 598/610 KSEI census still has ICBP unresolved from an HTTP transport
failure, while the frozen continuity gate needs only one additional resolved
common ticker on each of its five residual H10 dates.

The helpers do not perform network access and do not classify price behavior.
They only enforce immutable census identity and construct a strict replacement
row after the existing KSEI parser has successfully parsed an official ICBP
registered-security page.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import pandas as pd

from idx_trade.v4_ksei_ca_history import MECHANICAL_FAMILIES, is_active_status, row_dates
from idx_trade.v4_ksei_coverage_gap import parse_bool_series


TARGET_TICKER = "ICBP"
EXPECTED_PARENT_TICKERS = 610
EXPECTED_PARENT_CERTIFIED = 598
EXPECTED_PARENT_UNRESOLVED = frozenset(
    {
        "AMAN",
        "AVIA",
        "AYAM",
        "BCIP",
        "ICBP",
        "PRIM",
        "SKRN",
        "SLIS",
        "SMAR",
        "SNLK",
        "SOCI",
        "SOFA",
    }
)
EXPECTED_OUTPUT_CERTIFIED = 599
EXPECTED_OUTPUT_UNRESOLVED = EXPECTED_PARENT_UNRESOLVED - {TARGET_TICKER}


def normalize_parent_coverage(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate the exact accepted 598/610 logical census state."""

    required = {
        "ticker",
        "coverage_status",
        "coverage_certified",
        "attempt_count",
        "final_http_status",
        "source_url",
        "source_sha256",
        "ca_rows",
        "active_ca_rows",
        "active_mechanical_rows",
        "active_unknown_rows",
        "earliest_ca_date",
        "latest_ca_date",
        "failure_reason",
    }
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"ICBP_PARENT_COVERAGE_COLUMNS_MISSING:{','.join(sorted(missing))}")

    result = frame.copy()
    result["ticker"] = result["ticker"].astype(str).str.upper().str.strip()
    result["coverage_certified"] = parse_bool_series(
        result["coverage_certified"], label="icbp_parent_coverage_certified"
    )
    if len(result) != EXPECTED_PARENT_TICKERS or result["ticker"].nunique() != EXPECTED_PARENT_TICKERS:
        raise RuntimeError("ICBP_PARENT_COVERAGE_TICKER_IDENTITY_CHANGED")
    if int(result["coverage_certified"].sum()) != EXPECTED_PARENT_CERTIFIED:
        raise RuntimeError("ICBP_PARENT_CERTIFIED_COUNT_CHANGED")
    unresolved = set(result.loc[~result["coverage_certified"], "ticker"])
    if unresolved != EXPECTED_PARENT_UNRESOLVED:
        raise RuntimeError(f"ICBP_PARENT_UNRESOLVED_SET_CHANGED:{sorted(unresolved)}")
    target = result[result["ticker"].eq(TARGET_TICKER)]
    if len(target) != 1 or bool(target.iloc[0]["coverage_certified"]):
        raise RuntimeError("ICBP_PARENT_TARGET_NOT_EXACTLY_ONE_UNRESOLVED_ROW")
    return result.sort_values("ticker", kind="mergesort").reset_index(drop=True)


def validate_parent_history(rows: Sequence[Mapping[str, Any]]) -> None:
    """The accepted unresolved ICBP census must contain no ICBP history rows."""

    if any(str(row.get("ticker") or "").upper().strip() == TARGET_TICKER for row in rows):
        raise RuntimeError("ICBP_PARENT_HISTORY_ALREADY_CONTAINS_TARGET")


def parsed_history_stats(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Validate strict-parser output and summarize it without semantic rescue."""

    if not rows:
        raise RuntimeError("ICBP_STRICT_PARSE_RETURNED_NO_HISTORY_ROWS")
    for row in rows:
        if str(row.get("ticker") or "").upper().strip() != TARGET_TICKER:
            raise RuntimeError("ICBP_PARSED_HISTORY_TICKER_MISMATCH")
        if not str(row.get("source_url") or "").strip():
            raise RuntimeError("ICBP_PARSED_HISTORY_SOURCE_URL_MISSING")
        if not str(row.get("source_sha256") or "").strip():
            raise RuntimeError("ICBP_PARSED_HISTORY_SOURCE_SHA_MISSING")

    active = [row for row in rows if is_active_status(str(row.get("status") or ""))]
    active_mechanical = [
        row for row in active if str(row.get("event_family") or "") in MECHANICAL_FAMILIES
    ]
    active_unknown = [row for row in active if str(row.get("event_family") or "") == "UNKNOWN"]
    dates = sorted({date for row in rows for date in row_dates(dict(row))})
    families = sorted({str(row.get("event_family") or "") for row in rows})
    source_types = sorted({str(row.get("event_family_source") or "") for row in rows})
    return {
        "ca_rows": len(rows),
        "active_ca_rows": len(active),
        "active_mechanical_rows": len(active_mechanical),
        "active_unknown_rows": len(active_unknown),
        "earliest_ca_date": dates[0] if dates else "",
        "latest_ca_date": dates[-1] if dates else "",
        "event_families": families,
        "event_source_types": source_types,
    }


def build_certified_target_row(
    parent_row: Mapping[str, Any],
    *,
    success_record: Mapping[str, Any],
    security_attempt_count: int,
    stats: Mapping[str, Any],
) -> dict[str, Any]:
    """Construct the only logical coverage mutation allowed by this lane."""

    if str(parent_row.get("ticker") or "").upper().strip() != TARGET_TICKER:
        raise RuntimeError("ICBP_REPLACEMENT_PARENT_TICKER_MISMATCH")
    if int(success_record.get("status_code") or 0) != 200:
        raise RuntimeError("ICBP_REPLACEMENT_SUCCESS_HTTP_NOT_200")
    if not str(success_record.get("final_url") or "").strip():
        raise RuntimeError("ICBP_REPLACEMENT_FINAL_URL_MISSING")
    if not str(success_record.get("sha256") or "").strip():
        raise RuntimeError("ICBP_REPLACEMENT_SOURCE_SHA_MISSING")
    if security_attempt_count < 1 or security_attempt_count > 2:
        raise RuntimeError("ICBP_REPLACEMENT_ATTEMPT_COUNT_OUT_OF_BOUNDS")

    result = dict(parent_row)
    result.update(
        {
            "coverage_status": "COVERAGE_CERTIFIED",
            "coverage_certified": True,
            "attempt_count": security_attempt_count,
            "final_http_status": 200,
            "source_url": str(success_record["final_url"]),
            "source_sha256": str(success_record["sha256"]),
            "ca_rows": int(stats["ca_rows"]),
            "active_ca_rows": int(stats["active_ca_rows"]),
            "active_mechanical_rows": int(stats["active_mechanical_rows"]),
            "active_unknown_rows": int(stats["active_unknown_rows"]),
            "earliest_ca_date": str(stats["earliest_ca_date"]),
            "latest_ca_date": str(stats["latest_ca_date"]),
            "failure_reason": "",
        }
    )
    return result


def validate_output_coverage(frame: pd.DataFrame) -> pd.DataFrame:
    """Assert that exactly ICBP changed the census from 598/12 to 599/11."""

    result = frame.copy()
    result["ticker"] = result["ticker"].astype(str).str.upper().str.strip()
    if result["coverage_certified"].dtype != bool:
        result["coverage_certified"] = parse_bool_series(
            result["coverage_certified"], label="icbp_output_coverage_certified"
        )
    if len(result) != EXPECTED_PARENT_TICKERS or result["ticker"].nunique() != EXPECTED_PARENT_TICKERS:
        raise RuntimeError("ICBP_OUTPUT_COVERAGE_TICKER_IDENTITY_CHANGED")
    if int(result["coverage_certified"].sum()) != EXPECTED_OUTPUT_CERTIFIED:
        raise RuntimeError("ICBP_OUTPUT_CERTIFIED_COUNT_NOT_599")
    unresolved = set(result.loc[~result["coverage_certified"], "ticker"])
    if unresolved != EXPECTED_OUTPUT_UNRESOLVED:
        raise RuntimeError(f"ICBP_OUTPUT_UNRESOLVED_SET_CHANGED:{sorted(unresolved)}")
    target = result[result["ticker"].eq(TARGET_TICKER)]
    if len(target) != 1 or not bool(target.iloc[0]["coverage_certified"]):
        raise RuntimeError("ICBP_OUTPUT_TARGET_NOT_CERTIFIED")
    return result.sort_values("ticker", kind="mergesort").reset_index(drop=True)
