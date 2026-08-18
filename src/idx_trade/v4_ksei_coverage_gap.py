"""Strict helpers for the targeted V4 KSEI 43-ticker coverage-gap remediation.

This module is outcome-blind.  It does not relax the accepted KSEI history
parser or corporate-action semantics.  It only validates the immutable parent
census, classifies prior acquisition failures, and merges a bounded recovery
delta for the exact frozen gap ticker set.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd


PARENT_CERTIFIED = "COVERAGE_CERTIFIED"
PARENT_UNRESOLVED = "COVERAGE_UNRESOLVED"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ticker_identity_sha256(tickers: Iterable[str]) -> str:
    values = sorted({str(value).upper().strip() for value in tickers})
    return sha256_bytes(("\n".join(values) + "\n").encode("utf-8"))


def parse_bool_series(values: pd.Series, *, label: str) -> pd.Series:
    parsed = (
        values.astype(str)
        .str.strip()
        .str.casefold()
        .map({"true": True, "false": False})
    )
    if parsed.isna().any():
        raise RuntimeError(f"INVALID_BOOLEAN_COLUMN:{label}")
    return parsed.astype(bool)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"INVALID_JSONL:{path}:{line_number}") from exc
            if not isinstance(value, dict):
                raise RuntimeError(f"INVALID_JSONL_ROW:{path}:{line_number}")
            rows.append(value)
    return rows


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True, ensure_ascii=False) + "\n")


def classify_attempt(record: Mapping[str, Any]) -> str:
    """Classify one immutable parent request attempt without interpreting price data."""

    status = int(record.get("status_code") or 0)
    size = int(record.get("bytes") or 0)
    error = str(record.get("error") or "")
    folded = error.casefold()

    if "short-code identity mismatch" in folded:
        return "PARSE_IDENTITY_MISMATCH"
    if (
        "corporate action table" in folded
        or "malformed corporate action row" in folded
        or "empty ca type" in folded
        or "empty ca status" in folded
    ):
        return "PARSE_TABLE_STRUCTURE"
    if "invalid ksei html" in folded or "empty ksei response body" in folded:
        return "PARSE_INVALID_OR_EMPTY_HTML"
    if status and (status != 200 or size <= 0):
        return "HTTP_NON_200_OR_EMPTY"
    if "http_or_empty" in folded:
        return "HTTP_NON_200_OR_EMPTY"
    if status == 0 and size == 0:
        return "NETWORK_OR_TRANSPORT"
    if error:
        return "OTHER_PARSE_OR_RUNTIME"
    if status == 200 and size > 0:
        return "HTTP_200_NO_RECORDED_ERROR"
    return "UNCLASSIFIED"


def parent_failure_summary(
    request_records: Sequence[Mapping[str, Any]],
    *,
    gap_tickers: Sequence[str],
) -> pd.DataFrame:
    gap = {str(value).upper().strip() for value in gap_tickers}
    rows: list[dict[str, Any]] = []
    by_ticker: dict[str, list[Mapping[str, Any]]] = {ticker: [] for ticker in gap}
    for record in request_records:
        ticker = str(record.get("ticker") or "").upper().strip()
        if ticker in by_ticker:
            by_ticker[ticker].append(record)

    for ticker in sorted(gap):
        attempts = sorted(
            by_ticker[ticker],
            key=lambda value: int(value.get("attempt") or 0),
        )
        if not attempts:
            raise RuntimeError(f"PARENT_REQUEST_RECORDS_MISSING_GAP_TICKER:{ticker}")
        classes = [classify_attempt(record) for record in attempts]
        statuses = [int(record.get("status_code") or 0) for record in attempts]
        sizes = [int(record.get("bytes") or 0) for record in attempts]
        errors = [str(record.get("error") or "") for record in attempts]
        counter = Counter(classes)
        dominant = sorted(counter.items(), key=lambda item: (-item[1], item[0]))[0][0]
        rows.append(
            {
                "ticker": ticker,
                "parent_attempt_count": len(attempts),
                "parent_attempt_classes": "|".join(classes),
                "parent_dominant_failure_class": dominant,
                "parent_status_codes": "|".join(str(value) for value in statuses),
                "parent_bytes": "|".join(str(value) for value in sizes),
                "parent_errors": " || ".join(value for value in errors if value),
            }
        )
    return pd.DataFrame(rows).sort_values("ticker", kind="mergesort").reset_index(drop=True)


def validate_parent_coverage(
    coverage: pd.DataFrame,
    *,
    gap_tickers: Sequence[str],
    expected_tickers: int,
    expected_certified: int,
    expected_unresolved: int,
) -> pd.DataFrame:
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
    missing = required - set(coverage.columns)
    if missing:
        raise RuntimeError(f"PARENT_COVERAGE_COLUMNS_MISSING:{','.join(sorted(missing))}")
    frame = coverage.copy()
    frame["ticker"] = frame["ticker"].astype(str).str.upper().str.strip()
    frame["coverage_certified"] = parse_bool_series(
        frame["coverage_certified"], label="coverage_certified"
    )
    if len(frame) != expected_tickers or frame["ticker"].nunique() != expected_tickers:
        raise RuntimeError("PARENT_COVERAGE_TICKER_IDENTITY_CHANGED")
    if frame["ticker"].str.fullmatch(r"[A-Z0-9]{4}").eq(False).any():
        raise RuntimeError("PARENT_COVERAGE_TICKER_FORMAT_INVALID")
    certified = int(frame["coverage_certified"].sum())
    unresolved = int((~frame["coverage_certified"]).sum())
    if certified != expected_certified or unresolved != expected_unresolved:
        raise RuntimeError(
            f"PARENT_COVERAGE_COUNTS_CHANGED:{certified}:{unresolved}"
        )
    actual_gap = set(frame.loc[~frame["coverage_certified"], "ticker"])
    expected_gap = {str(value).upper().strip() for value in gap_tickers}
    if actual_gap != expected_gap:
        raise RuntimeError("PARENT_COVERAGE_GAP_IDENTITY_CHANGED")
    return frame.sort_values("ticker", kind="mergesort").reset_index(drop=True)


def merge_coverage(
    parent: pd.DataFrame,
    remediation: pd.DataFrame,
    *,
    gap_tickers: Sequence[str],
) -> pd.DataFrame:
    gap = {str(value).upper().strip() for value in gap_tickers}
    if remediation["ticker"].duplicated().any():
        raise RuntimeError("REMEDIATION_COVERAGE_DUPLICATE_TICKER")
    if set(remediation["ticker"]) != gap:
        raise RuntimeError("REMEDIATION_COVERAGE_TICKER_SET_CHANGED")

    parent_sorted = parent.sort_values("ticker", kind="mergesort").reset_index(drop=True)
    remediation_indexed = remediation.set_index("ticker", drop=False)
    rows: list[dict[str, Any]] = []
    for row in parent_sorted.to_dict("records"):
        ticker = str(row["ticker"])
        if ticker not in gap:
            rows.append(dict(row))
            continue
        replacement = remediation_indexed.loc[ticker].to_dict()
        if bool(replacement.get("coverage_certified")):
            rows.append(replacement)
        else:
            # Failed remediation must not mutate the immutable parent logical row.
            rows.append(dict(row))
    merged = pd.DataFrame(rows, columns=parent_sorted.columns)
    non_gap = ~parent_sorted["ticker"].isin(gap)
    if not parent_sorted.loc[non_gap].reset_index(drop=True).equals(
        merged.loc[non_gap].reset_index(drop=True)
    ):
        raise RuntimeError("NON_GAP_PARENT_COVERAGE_MUTATED")
    return merged


def merge_history(
    parent_rows: Sequence[Mapping[str, Any]],
    recovered_rows: Sequence[Mapping[str, Any]],
    *,
    gap_tickers: Sequence[str],
) -> list[dict[str, Any]]:
    gap = {str(value).upper().strip() for value in gap_tickers}
    parent_gap_rows = [
        row for row in parent_rows
        if str(row.get("ticker") or "").upper().strip() in gap
    ]
    if parent_gap_rows:
        raise RuntimeError("PARENT_HISTORY_UNEXPECTED_ROWS_FOR_GAP_TICKERS")
    for row in recovered_rows:
        ticker = str(row.get("ticker") or "").upper().strip()
        if ticker not in gap:
            raise RuntimeError(f"RECOVERED_HISTORY_OUT_OF_SCOPE:{ticker}")
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for row in [*parent_rows, *recovered_rows]:
        canonical = json.dumps(dict(row), sort_keys=True, ensure_ascii=False)
        if canonical in seen:
            raise RuntimeError("MERGED_HISTORY_DUPLICATE_ROW")
        seen.add(canonical)
        merged.append(dict(row))
    return merged
