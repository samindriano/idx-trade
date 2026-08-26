from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
from math import isfinite
from pathlib import Path
import re
from typing import Any, Mapping

import pandas as pd

from .provenance import sha256_file
from .security_master import normalise_ticker


EXPECTED_COMPLETENESS = "COMPLETE_RECORDS_TOTAL_SINGLE_RESPONSE"
EXPECTED_SOURCE = "IDX_OFFICIAL"
_TICKER_RE = re.compile(r"^[A-Z0-9]{4}$")


class StockbitIntradayGateError(RuntimeError):
    pass


@dataclass(frozen=True)
class VerifiedEodGate:
    session_date: str
    manifest_path: Path
    manifest_sha256: str
    stock_summary_path: Path
    stock_summary_sha256: str
    stock_summary_raw_path: Path
    stock_summary_raw_sha256: str
    source_ref: str
    observed_available_at_utc: str | None
    records_total: int
    records_filtered: int
    summary: pd.DataFrame
    decisions: pd.DataFrame


def _required_int(value: object, *, label: str) -> int:
    if value is None or isinstance(value, bool):
        raise StockbitIntradayGateError(f"{label}_INVALID")
    try:
        number = float(value)
        parsed = int(number)
    except (TypeError, ValueError, OverflowError) as exc:
        raise StockbitIntradayGateError(f"{label}_INVALID") from exc
    if not isfinite(number) or number != parsed or parsed < 0:
        raise StockbitIntradayGateError(f"{label}_INVALID")
    return parsed


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_hash(path: Path, expected: object, *, label: str) -> str:
    declared = str(expected or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", declared):
        raise StockbitIntradayGateError(f"{label}_SHA_INVALID")
    if not path.is_file() or sha256_file(path) != declared:
        raise StockbitIntradayGateError(f"{label}_SHA_MISMATCH")
    return declared


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StockbitIntradayGateError(f"{label}_JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise StockbitIntradayGateError(f"{label}_NOT_OBJECT")
    return value


def _canonical_universe(universe: pd.DataFrame) -> pd.DataFrame:
    if "ticker" not in universe.columns:
        raise StockbitIntradayGateError("INTRADAY_UNIVERSE_TICKER_MISSING")
    result = universe[["ticker"]].copy()
    result["ticker"] = result["ticker"].map(normalise_ticker).astype(str).str.upper().str.strip()
    if result.empty or not result["ticker"].map(lambda value: bool(_TICKER_RE.fullmatch(value))).all():
        raise StockbitIntradayGateError("INTRADAY_UNIVERSE_TICKER_INVALID")
    if result["ticker"].duplicated().any():
        raise StockbitIntradayGateError("INTRADAY_UNIVERSE_TICKER_DUPLICATE")
    return result.sort_values("ticker").reset_index(drop=True)


def _validate_raw_payload(payload: Mapping[str, Any], *, expected_date: date) -> tuple[int, int]:
    rows = payload.get("data")
    if not isinstance(rows, list) or not rows:
        raise StockbitIntradayGateError("EOD_GATE_RAW_EMPTY")
    records_total = _required_int(payload.get("recordsTotal"), label="EOD_GATE_RAW_RECORDS_TOTAL")
    filtered_raw = payload.get("recordsFiltered")
    records_filtered = records_total if filtered_raw in (None, "") else _required_int(
        filtered_raw, label="EOD_GATE_RAW_RECORDS_FILTERED"
    )
    if records_total == 0 or len(rows) != records_total or records_filtered != records_total:
        raise StockbitIntradayGateError("EOD_GATE_RAW_INCOMPLETE")

    tickers: list[str] = []
    expected = pd.Timestamp(expected_date).normalize()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise StockbitIntradayGateError(f"EOD_GATE_RAW_ROW_INVALID:{index}")
        ticker = normalise_ticker(str(row.get("StockCode") or "")).upper().strip()
        if not ticker or not re.fullmatch(r"[A-Z0-9]{4,5}", ticker):
            raise StockbitIntradayGateError(f"EOD_GATE_RAW_TICKER_INVALID:{index}")
        observed = pd.to_datetime(row.get("Date"), errors="coerce")
        if pd.isna(observed) or pd.Timestamp(observed).tz_localize(None).normalize() != expected:
            raise StockbitIntradayGateError(f"EOD_GATE_RAW_DATE_MISMATCH:{ticker}")
        tickers.append(ticker)
    if len(set(tickers)) != len(tickers):
        raise StockbitIntradayGateError("EOD_GATE_RAW_TICKER_DUPLICATE")
    return records_total, records_filtered


def _validate_normalized_summary(
    frame: pd.DataFrame,
    *,
    expected_date: date,
    expected_rows: int,
) -> pd.DataFrame:
    required = {"ticker", "as_of_date", "volume", "frequency", "regular_value"}
    missing = required - set(frame.columns)
    if missing:
        raise StockbitIntradayGateError("EOD_GATE_NORMALIZED_COLUMNS_MISSING:" + ",".join(sorted(missing)))
    if frame.empty or len(frame) != expected_rows:
        raise StockbitIntradayGateError("EOD_GATE_NORMALIZED_ROW_COUNT_MISMATCH")

    result = frame.copy()
    result["ticker"] = result["ticker"].map(normalise_ticker).astype(str).str.upper().str.strip()
    if result["ticker"].eq("").any() or result["ticker"].duplicated().any():
        raise StockbitIntradayGateError("EOD_GATE_NORMALIZED_TICKER_INVALID")
    dates = pd.to_datetime(result["as_of_date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    expected = pd.Timestamp(expected_date).normalize()
    if dates.isna().any() or not dates.eq(expected).all():
        raise StockbitIntradayGateError("EOD_GATE_NORMALIZED_DATE_MISMATCH")

    numeric = result[["volume", "frequency", "regular_value"]].apply(pd.to_numeric, errors="coerce")
    values = numeric.to_numpy(dtype=float)
    if pd.isna(numeric).any().any() or not all(isfinite(float(value)) for value in values.ravel()):
        raise StockbitIntradayGateError("EOD_GATE_NORMALIZED_ACTIVITY_NONFINITE")
    if (numeric < 0).any().any():
        raise StockbitIntradayGateError("EOD_GATE_NORMALIZED_ACTIVITY_NEGATIVE")
    result[["volume", "frequency", "regular_value"]] = numeric
    return result.sort_values("ticker").reset_index(drop=True)


def _build_decisions(universe: pd.DataFrame, summary: pd.DataFrame) -> pd.DataFrame:
    base = _canonical_universe(universe)
    activity = summary[["ticker", "volume", "frequency", "regular_value"]].copy()
    activity["activity_or"] = (
        activity["volume"].gt(0)
        | activity["frequency"].gt(0)
        | activity["regular_value"].gt(0)
    )
    merged = base.merge(activity, on="ticker", how="left", validate="one_to_one")
    merged["idx_summary_present"] = merged["activity_or"].notna()
    merged["gate_decision"] = "FETCH_TRADED"
    merged.loc[~merged["idx_summary_present"], "gate_decision"] = "FETCH_MISSING_SUMMARY"
    merged.loc[
        merged["idx_summary_present"] & ~merged["activity_or"].fillna(False).astype(bool),
        "gate_decision",
    ] = "SKIP_NO_ACTIVITY"
    merged["would_fetch_stockbit"] = merged["gate_decision"].ne("SKIP_NO_ACTIVITY")
    return merged.sort_values("ticker").reset_index(drop=True)


def load_verified_eod_gate(
    session_dir: str | Path,
    *,
    expected_date: date,
    universe: pd.DataFrame,
    expected_manifest_sha256: str | None = None,
) -> VerifiedEodGate:
    """Verify and consume the canonical E2E EOD Stock Summary; never refetch it."""

    root = Path(session_dir).expanduser().resolve()
    manifest_path = root / "manifest.json"
    summary_path = root / "idx_stock_summary.csv"
    raw_path = root / "idx_stock_summary.raw.json"
    if not manifest_path.is_file() or not summary_path.is_file() or not raw_path.is_file():
        raise StockbitIntradayGateError("EOD_GATE_CANONICAL_ARTIFACT_MISSING")

    manifest_sha = sha256_file(manifest_path)
    if expected_manifest_sha256 is not None:
        expected_sha = str(expected_manifest_sha256).strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", expected_sha) or manifest_sha != expected_sha:
            raise StockbitIntradayGateError("EOD_GATE_MANIFEST_SHA_MISMATCH")
    manifest = _load_json(manifest_path, label="EOD_GATE_MANIFEST")
    session = expected_date.isoformat()
    if manifest.get("status") != "DATA_READY" or manifest.get("session_date") != session:
        raise StockbitIntradayGateError("EOD_GATE_MANIFEST_NOT_DATA_READY")
    if manifest.get("outcome_blind") is not True or manifest.get("forward_outcomes_accessed") is not False:
        raise StockbitIntradayGateError("EOD_GATE_OUTCOME_GUARD_INVALID")

    source = manifest.get("stock_summary_source")
    meta = manifest.get("stock_summary_meta")
    if not isinstance(source, Mapping) or not isinstance(meta, Mapping):
        raise StockbitIntradayGateError("EOD_GATE_SOURCE_METADATA_MISSING")
    if source.get("source") != EXPECTED_SOURCE or source.get("session_date") != session:
        raise StockbitIntradayGateError("EOD_GATE_SOURCE_IDENTITY_MISMATCH")
    if source.get("completeness_status") != EXPECTED_COMPLETENESS:
        raise StockbitIntradayGateError("EOD_GATE_SOURCE_COMPLETENESS_INVALID")
    if meta.get("requested_date") != session or meta.get("completeness_status") != EXPECTED_COMPLETENESS:
        raise StockbitIntradayGateError("EOD_GATE_META_IDENTITY_MISMATCH")

    normalized_sha = _require_hash(
        summary_path, manifest.get("stock_summary_sha256"), label="EOD_GATE_NORMALIZED"
    )
    raw_sha = _require_hash(raw_path, manifest.get("stock_summary_raw_sha256"), label="EOD_GATE_RAW")
    declared_meta_raw_sha = str(meta.get("raw_sha256") or "").strip().lower()
    if declared_meta_raw_sha and declared_meta_raw_sha != raw_sha:
        raise StockbitIntradayGateError("EOD_GATE_META_RAW_SHA_MISMATCH")

    raw = _load_json(raw_path, label="EOD_GATE_RAW")
    raw_total, raw_filtered = _validate_raw_payload(raw, expected_date=expected_date)
    source_total = _required_int(source.get("records_total"), label="EOD_GATE_SOURCE_RECORDS_TOTAL")
    source_filtered = _required_int(
        source.get("records_filtered") if source.get("records_filtered") is not None else source_total,
        label="EOD_GATE_SOURCE_RECORDS_FILTERED",
    )
    source_rows = _required_int(source.get("row_count"), label="EOD_GATE_SOURCE_ROWS")
    meta_total = _required_int(meta.get("records_total"), label="EOD_GATE_META_RECORDS_TOTAL")
    meta_filtered = _required_int(
        meta.get("records_filtered") if meta.get("records_filtered") is not None else meta_total,
        label="EOD_GATE_META_RECORDS_FILTERED",
    )
    meta_rows = _required_int(meta.get("rows"), label="EOD_GATE_META_ROWS")
    if len({raw_total, raw_filtered, source_total, source_filtered, source_rows, meta_total, meta_filtered, meta_rows}) != 1:
        raise StockbitIntradayGateError("EOD_GATE_RECORD_COUNT_CONFLICT")

    summary = _validate_normalized_summary(
        pd.read_csv(summary_path),
        expected_date=expected_date,
        expected_rows=raw_total,
    )
    decisions = _build_decisions(universe, summary)
    source_ref = str(source.get("source_ref") or meta.get("source_ref") or "").strip()
    if not source_ref:
        raise StockbitIntradayGateError("EOD_GATE_SOURCE_REF_MISSING")

    return VerifiedEodGate(
        session_date=session,
        manifest_path=manifest_path,
        manifest_sha256=manifest_sha,
        stock_summary_path=summary_path,
        stock_summary_sha256=normalized_sha,
        stock_summary_raw_path=raw_path,
        stock_summary_raw_sha256=raw_sha,
        source_ref=source_ref,
        observed_available_at_utc=(
            str(source.get("observed_available_at_utc"))
            if source.get("observed_available_at_utc") is not None
            else None
        ),
        records_total=raw_total,
        records_filtered=raw_filtered,
        summary=summary,
        decisions=decisions,
    )


def gate_skip_evidence(gate: VerifiedEodGate, row: Mapping[str, Any]) -> dict[str, Any]:
    if str(row.get("gate_decision") or "") != "SKIP_NO_ACTIVITY":
        raise StockbitIntradayGateError("EOD_GATE_SKIP_EVIDENCE_NON_SKIP_ROW")
    return {
        "source": EXPECTED_SOURCE,
        "source_ref": gate.source_ref,
        "session_date": gate.session_date,
        "eod_manifest_sha256": gate.manifest_sha256,
        "stock_summary_sha256": gate.stock_summary_sha256,
        "stock_summary_raw_sha256": gate.stock_summary_raw_sha256,
        "observed_available_at_utc": gate.observed_available_at_utc,
        "activity_or": False,
        "volume": float(row.get("volume") or 0),
        "frequency": float(row.get("frequency") or 0),
        "regular_value": float(row.get("regular_value") or 0),
    }
