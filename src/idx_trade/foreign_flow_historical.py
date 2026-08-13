"""Resumable historical official IDX Foreign Flow acquisition.

This module deliberately keeps historical acquisition separate from the
prospective forward archive.  It stores exact Stock Summary response bytes,
normalizes only the two official foreign-flow fields, and refuses to treat a
partial or revised response as valid historical evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections.abc import Callable, Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
import requests

from .forward_foreign_flow import parse_stock_summary_foreign_flow
from .providers.idx_stock_summary import (
    StockSummaryPayloadCapture,
    fetch_stock_summary_payload_capture,
)


HISTORICAL_SCHEMA_VERSION = 1
LABEL_PROVENANCE = "OFFICIAL_IDX_HISTORICAL_EOD"
ACQUISITION_MODE = "RETROSPECTIVELY_ACQUIRED"
NORMALIZED_COLUMNS = (
    "ticker",
    "session_date",
    "foreign_buy",
    "foreign_sell",
    "foreign_net",
    "unit",
    "label_provenance",
    "acquisition_mode",
    "knowledge_at_utc",
    "source",
    "source_ref",
    "source_sha256",
)
STATUS_VALUES = {
    "READY",
    "ALREADY_VALID",
    "ERROR",
    "REVISION_CONFLICT",
    "INCOMPLETE_ARTIFACT",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _exclusive_bytes(path: Path, payload: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(str(path), flags, 0o666)
    except FileExistsError:
        return False
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    return True


def _exclusive_json(path: Path, value: Mapping[str, object]) -> bool:
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
    return _exclusive_bytes(path, payload + b"\n")


def _write_json_replace(path: Path, value: Mapping[str, object]) -> None:
    """Write a non-canonical run summary atomically; never used for raw data."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_bytes(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        + b"\n"
    )
    temporary.replace(path)


def _session_key(value: str | pd.Timestamp) -> str:
    parsed = pd.Timestamp(value)
    if pd.isna(parsed):
        raise ValueError(f"invalid session date: {value!r}")
    if parsed.tzinfo is not None:
        parsed = parsed.tz_convert("Asia/Jakarta").tz_localize(None)
    return parsed.normalize().date().isoformat()


def load_official_session_dates(path: str | Path) -> list[str]:
    """Load a previously verified official session artifact, not weekdays."""

    frame = pd.read_csv(path)
    column = "date" if "date" in frame.columns else "session_date"
    if column not in frame.columns:
        raise ValueError("official session artifact needs date or session_date")
    dates = [_session_key(value) for value in frame[column].tolist()]
    if not dates or len(set(dates)) != len(dates):
        raise ValueError("official session artifact is empty or duplicated")
    return sorted(dates)


def _paths(root: Path, key: str) -> dict[str, Path]:
    directory = root / "sessions" / key
    return {
        "directory": directory,
        "raw": directory / "stock_summary.raw.json",
        "normalized": directory / "foreign_flow.parquet",
        "manifest": directory / "manifest.json",
    }


def _normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.rename(columns={"security_code": "ticker"}).copy()
    output["session_date"] = pd.to_datetime(output["session_date"], errors="coerce").dt.normalize()
    output["label_provenance"] = LABEL_PROVENANCE
    output["acquisition_mode"] = ACQUISITION_MODE
    output = output.loc[:, NORMALIZED_COLUMNS]
    return output.sort_values(["session_date", "ticker"]).reset_index(drop=True)


def _read_valid_existing(paths: Mapping[str, Path], key: str) -> dict[str, object] | None:
    if not all(paths[name].exists() for name in ("raw", "normalized", "manifest")):
        if any(paths[name].exists() for name in ("raw", "normalized", "manifest")):
            raise RuntimeError(f"incomplete historical artifact set for {key}")
        return None
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    if not isinstance(manifest, Mapping) or manifest.get("status") != "READY":
        raise RuntimeError(f"historical manifest is not READY for {key}")
    if manifest.get("session_date") != key:
        raise RuntimeError(f"historical manifest date mismatch for {key}")
    raw_sha = sha256_path(paths["raw"])
    if raw_sha != str(manifest.get("raw_sha256", "")).lower():
        raise RuntimeError(f"historical raw SHA mismatch for {key}")
    normalized_sha = sha256_path(paths["normalized"])
    if normalized_sha != str(manifest.get("normalized_sha256", "")).lower():
        raise RuntimeError(f"historical normalized SHA mismatch for {key}")
    frame = pd.read_parquet(paths["normalized"])
    if list(frame.columns) != list(NORMALIZED_COLUMNS):
        raise RuntimeError(f"historical normalized schema mismatch for {key}")
    if len(frame) != int(manifest.get("rows", -1)):
        raise RuntimeError(f"historical normalized row count mismatch for {key}")
    return dict(manifest)


def _capture_default(
    value: str,
    *,
    session: requests.Session,
    timeout: int,
    prepare_session: bool,
) -> StockSummaryPayloadCapture:
    return fetch_stock_summary_payload_capture(
        value,
        session=session,
        timeout=timeout,
        prepare_session=prepare_session,
    )


def acquire_historical_foreign_flow(
    sessions: Iterable[str | pd.Timestamp],
    output_root: str | Path,
    *,
    timeout: int = 30,
    fetch_capture: Callable[..., StockSummaryPayloadCapture] | None = None,
) -> dict[str, object]:
    """Acquire each official session once and produce a resumable run summary."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    ordered = sorted({_session_key(value) for value in sessions})
    if not ordered:
        raise ValueError("no official sessions supplied")

    fetcher = fetch_capture or _capture_default
    client = requests.Session()
    results: list[dict[str, object]] = []
    prepared = False
    for key in ordered:
        paths = _paths(root, key)
        try:
            existing = _read_valid_existing(paths, key)
            if existing is not None:
                results.append({"session_date": key, "status": "ALREADY_VALID", **existing})
                continue

            capture = fetcher(
                key,
                session=client,
                timeout=timeout,
                prepare_session=not prepared,
            )
            prepared = True
            incoming_raw_sha = capture.raw_sha256
            if paths["raw"].exists():
                if sha256_path(paths["raw"]) != incoming_raw_sha:
                    raise RuntimeError(f"raw response revision conflict for {key}")
            else:
                _exclusive_bytes(paths["raw"], capture.raw_bytes)

            frame, parse_meta = parse_stock_summary_foreign_flow(
                capture.payload,
                session_date=key,
                knowledge_at_utc=capture.observed_available_at_utc,
                source_ref=capture.source_ref,
                source_sha256=incoming_raw_sha,
            )
            normalized = _normalize_frame(frame)
            normalized_path = paths["normalized"]
            if normalized_path.exists():
                existing_frame = pd.read_parquet(normalized_path)
                if not existing_frame.equals(normalized):
                    raise RuntimeError(f"normalized response revision conflict for {key}")
            else:
                temporary = normalized_path.with_name(f".{normalized_path.name}.{uuid4().hex}.tmp")
                normalized_path.parent.mkdir(parents=True, exist_ok=True)
                normalized.to_parquet(temporary, index=False)
                try:
                    _exclusive_bytes(normalized_path, temporary.read_bytes())
                finally:
                    temporary.unlink(missing_ok=True)

            manifest = {
                "schema_version": HISTORICAL_SCHEMA_VERSION,
                "status": "READY",
                "session_date": key,
                "unit": "SHARES",
                "label_provenance": LABEL_PROVENANCE,
                "acquisition_mode": ACQUISITION_MODE,
                "endpoint": capture.endpoint,
                "source_ref": capture.source_ref,
                "params": capture.params,
                "retrieval_started_at_utc": capture.retrieval_started_at_utc,
                "observed_available_at_utc": capture.observed_available_at_utc,
                "records_total": capture.records_total,
                "records_filtered": capture.records_filtered,
                "row_count": capture.row_count,
                "completeness_status": capture.completeness_status,
                "raw_path": str(paths["raw"]),
                "raw_sha256": incoming_raw_sha,
                "normalized_path": str(normalized_path),
                "normalized_sha256": sha256_path(normalized_path),
                "rows": len(normalized),
                "zero_flow_rows": int(parse_meta["zero_flow_rows"]),
                "publication_time_known": False,
                "causality": "SESSION_T_DATA_USABLE_FROM_NEXT_OFFICIAL_SESSION_T_PLUS_1",
            }
            _exclusive_json(paths["manifest"], manifest)
            if not paths["manifest"].exists():
                raise RuntimeError(f"manifest could not be persisted for {key}")
            results.append(manifest)
        except Exception as error:
            status = "REVISION_CONFLICT" if "revision conflict" in str(error).lower() else "ERROR"
            results.append(
                {
                    "schema_version": HISTORICAL_SCHEMA_VERSION,
                    "status": status,
                    "session_date": key,
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "observed_at_utc": _utc_now(),
                }
            )

    summary = build_coverage_census(ordered, root, results=results)
    summary["provider_call_accounting"] = {
        "session_setup_requests": 2 if any(r["status"] in {"READY", "ERROR", "REVISION_CONFLICT"} for r in results) else 0,
        "summary_endpoint_requests": sum(
            1 for r in results if r["status"] in {"READY", "ERROR", "REVISION_CONFLICT"}
        ),
        "estimated_http_requests": (
            2
            + sum(1 for r in results if r["status"] in {"READY", "ERROR", "REVISION_CONFLICT"})
            if any(r["status"] in {"READY", "ERROR", "REVISION_CONFLICT"} for r in results)
            else 0
        ),
    }
    _write_json_replace(root / "acquisition_summary.json", summary)
    _write_json_replace(root / "coverage_census.json", summary)
    return summary


def build_coverage_census(
    sessions: Iterable[str | pd.Timestamp],
    root: str | Path,
    *,
    results: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Summarize complete versus unavailable official session snapshots."""

    root = Path(root)
    ordered = sorted({_session_key(value) for value in sessions})
    by_date = {str(row["session_date"]): row for row in (results or [])}
    available: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    for key in ordered:
        row = by_date.get(key)
        if row is None:
            try:
                manifest = _read_valid_existing(_paths(root, key), key)
                row = manifest or {"session_date": key, "status": "READY"}
            except Exception as error:
                row = {"session_date": key, "status": "ERROR", "error": str(error)}
        if row.get("status") in {"READY", "ALREADY_VALID"}:
            available.append(row)
        else:
            errors.append(row)

    def year_summary(year: int) -> dict[str, object]:
        expected = [key for key in ordered if key.startswith(str(year))]
        got = [row for row in available if str(row["session_date"]).startswith(str(year))]
        bad = [row for row in errors if str(row["session_date"]).startswith(str(year))]
        year_frames: list[pd.DataFrame] = []
        for row in got:
            normalized_path = Path(
                str(row.get("normalized_path", _paths(root, str(row["session_date"]))["normalized"]))
            )
            if normalized_path.exists():
                year_frames.append(pd.read_parquet(normalized_path))
        year_frame = pd.concat(year_frames, ignore_index=True) if year_frames else pd.DataFrame()
        zero_flow_rows = (
            int(year_frame["foreign_buy"].eq(0).mul(year_frame["foreign_sell"].eq(0)).sum())
            if not year_frame.empty
            else 0
        )
        return {
            "expected_sessions": len(expected),
            "available_sessions": len(got),
            "missing_or_error_sessions": len(bad),
            "missing_dates": [key for key in expected if key not in {str(r["session_date"]) for r in got}],
            "row_count_min": min((int(r.get("rows", 0)) for r in got), default=0),
            "row_count_median": float(pd.Series([int(r.get("rows", 0)) for r in got]).median()) if got else 0.0,
            "row_count_max": max((int(r.get("rows", 0)) for r in got), default=0),
            "rows": int(len(year_frame)),
            "unique_tickers": int(year_frame["ticker"].nunique()) if not year_frame.empty else 0,
            "zero_flow_rows": zero_flow_rows,
            "zero_flow_prevalence": float(zero_flow_rows / len(year_frame)) if len(year_frame) else 0.0,
            "error_types": sorted({str(r.get("error_type", r.get("status", "ERROR"))) for r in bad}),
        }

    all_frames: list[pd.DataFrame] = []
    for row in available:
        path = Path(str(row.get("normalized_path", _paths(root, str(row["session_date"]))["normalized"])))
        if path.exists():
            all_frames.append(pd.read_parquet(path))
    combined = pd.concat(all_frames, ignore_index=True) if all_frames else pd.DataFrame(columns=NORMALIZED_COLUMNS)
    first = available[0]["session_date"] if available else None
    last = available[-1]["session_date"] if available else None
    years = sorted({int(key[:4]) for key in ordered})
    error_histogram: dict[str, int] = {}
    for row in errors:
        label = str(row.get("error_type", row.get("status", "ERROR")))
        error_histogram[label] = error_histogram.get(label, 0) + 1
    return {
        "schema_version": HISTORICAL_SCHEMA_VERSION,
        "status": "COVERAGE_CENSUS_COMPLETE",
        "unit": "SHARES",
        "label_provenance": LABEL_PROVENANCE,
        "acquisition_mode": ACQUISITION_MODE,
        "causality_rule": "SESSION_T_DATA_USABLE_FROM_NEXT_OFFICIAL_SESSION_T_PLUS_1",
        "expected_sessions": len(ordered),
        "available_sessions": len(available),
        "missing_or_error_sessions": len(errors),
        "first_available_session": first,
        "last_available_session": last,
        "years": {str(year): year_summary(year) for year in years},
        "available_row_count_total": int(len(combined)),
        "row_count_min": min((int(row.get("rows", 0)) for row in available), default=0),
        "row_count_median": float(pd.Series([int(row.get("rows", 0)) for row in available]).median()) if available else 0.0,
        "row_count_max": max((int(row.get("rows", 0)) for row in available), default=0),
        "unique_tickers": int(combined["ticker"].nunique()) if not combined.empty else 0,
        "zero_flow_rows": int(combined["foreign_buy"].eq(0).mul(combined["foreign_sell"].eq(0)).sum()) if not combined.empty else 0,
        "zero_flow_prevalence": float(
            combined["foreign_buy"].eq(0).mul(combined["foreign_sell"].eq(0)).mean()
        ) if not combined.empty else 0.0,
        "malformed_or_rejected_rows_materialized": 0,
        "malformed_or_rejected_session_count": int(error_histogram.get("ValueError", 0)),
        "error_histogram": error_histogram,
        "errors": errors,
        "normalized_schema": list(NORMALIZED_COLUMNS),
    }


def _cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions-csv", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    sessions = load_official_session_dates(args.sessions_csv)
    summary = acquire_historical_foreign_flow(sessions, args.output_root, timeout=args.timeout)
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True, default=str))
    return 0 if summary["missing_or_error_sessions"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(_cli())
