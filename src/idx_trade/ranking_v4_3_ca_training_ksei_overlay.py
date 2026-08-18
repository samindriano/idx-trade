"""Fail-closed merge helpers for the V4-3 historical KSEI coverage expansion.

The accepted final CA census remains immutable.  These helpers only construct
an in-memory offline view by appending the exact frozen 129-ticker KSEI delta.
Unresolved delta tickers remain explicit `coverage_certified=False`; they are
never dropped or converted into successful coverage.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

import pandas as pd


COVERAGE_REQUIRED = {
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


def normalize_coverage(frame: pd.DataFrame, *, label: str) -> pd.DataFrame:
    missing = COVERAGE_REQUIRED - set(frame.columns)
    if missing:
        raise RuntimeError(f"{label}_COVERAGE_COLUMNS_MISSING:{sorted(missing)}")
    out = frame.copy()
    out["ticker"] = (
        out["ticker"]
        .astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )
    if out["ticker"].eq("").any() or out["ticker"].duplicated().any():
        raise RuntimeError(f"{label}_COVERAGE_TICKER_IDENTITY_INVALID")
    parsed = (
        out["coverage_certified"]
        .astype(str)
        .str.strip()
        .str.casefold()
        .map({"true": True, "false": False})
    )
    if parsed.isna().any():
        raise RuntimeError(f"{label}_COVERAGE_BOOLEAN_INVALID")
    out["coverage_certified"] = parsed.astype(bool)
    return out.sort_values("ticker", kind="mergesort").reset_index(drop=True)


def _history_ticker(row: Mapping[str, Any]) -> str:
    return str(row.get("ticker") or "").upper().replace(".JK", "").strip()


def merge_coverage_and_history(
    *,
    parent_coverage: pd.DataFrame,
    parent_history: Sequence[Mapping[str, Any]],
    delta_coverage: pd.DataFrame,
    delta_history: Sequence[Mapping[str, Any]],
    expected_delta_tickers: int = 129,
    expected_delta_certified: int = 93,
    expected_delta_unresolved: int = 36,
) -> tuple[pd.DataFrame, list[dict[str, Any]], dict[str, Any]]:
    parent = normalize_coverage(parent_coverage, label="PARENT")
    delta = normalize_coverage(delta_coverage, label="DELTA")

    if len(delta) != expected_delta_tickers:
        raise RuntimeError(
            f"DELTA_TICKER_COUNT_CHANGED:{len(delta)}!={expected_delta_tickers}"
        )
    certified = int(delta["coverage_certified"].sum())
    unresolved = int((~delta["coverage_certified"]).sum())
    if certified != expected_delta_certified or unresolved != expected_delta_unresolved:
        raise RuntimeError(
            "DELTA_COVERAGE_COUNTS_CHANGED:"
            f"{certified}:{unresolved}!={expected_delta_certified}:{expected_delta_unresolved}"
        )

    parent_tickers = set(parent["ticker"])
    delta_tickers = set(delta["ticker"])
    overlap = sorted(parent_tickers & delta_tickers)
    if overlap:
        raise RuntimeError(f"PARENT_DELTA_TICKER_OVERLAP:{overlap[:10]}")

    certified_delta = set(delta.loc[delta["coverage_certified"], "ticker"])
    unresolved_delta = delta_tickers - certified_delta
    normalized_delta_history: list[dict[str, Any]] = []
    for raw in delta_history:
        row = dict(raw)
        ticker = _history_ticker(row)
        if not ticker:
            raise RuntimeError("DELTA_HISTORY_TICKER_MISSING")
        if ticker not in delta_tickers:
            raise RuntimeError(f"DELTA_HISTORY_OUT_OF_SCOPE:{ticker}")
        if ticker in unresolved_delta:
            raise RuntimeError(f"DELTA_HISTORY_FOR_UNRESOLVED_TICKER:{ticker}")
        row["ticker"] = ticker
        normalized_delta_history.append(row)

    parent_rows = [dict(row) for row in parent_history]
    parent_history_tickers = {_history_ticker(row) for row in parent_rows}
    if parent_history_tickers & delta_tickers:
        raise RuntimeError("PARENT_HISTORY_UNEXPECTED_DELTA_TICKER")

    seen: set[str] = set()
    merged_history: list[dict[str, Any]] = []
    for row in [*parent_rows, *normalized_delta_history]:
        canonical = json.dumps(row, sort_keys=True, ensure_ascii=False, default=str)
        if canonical in seen:
            raise RuntimeError("MERGED_HISTORY_DUPLICATE_ROW")
        seen.add(canonical)
        merged_history.append(row)

    merged_coverage = pd.concat([parent, delta], ignore_index=True)
    if merged_coverage["ticker"].duplicated().any():
        raise RuntimeError("MERGED_COVERAGE_DUPLICATE_TICKER")
    merged_coverage = merged_coverage.sort_values(
        "ticker", kind="mergesort"
    ).reset_index(drop=True)

    diagnostics = {
        "parent_tickers": int(len(parent)),
        "delta_tickers": int(len(delta)),
        "delta_certified_tickers": certified,
        "delta_unresolved_tickers": unresolved,
        "merged_tickers": int(len(merged_coverage)),
        "parent_history_rows": int(len(parent_rows)),
        "delta_history_rows": int(len(normalized_delta_history)),
        "merged_history_rows": int(len(merged_history)),
        "certified_delta_tickers_with_history": int(
            len({_history_ticker(row) for row in normalized_delta_history})
        ),
        "unresolved_delta_tickers": sorted(unresolved_delta),
    }
    return merged_coverage, merged_history, diagnostics
