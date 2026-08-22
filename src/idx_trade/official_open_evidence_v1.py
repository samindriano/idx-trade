from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping
from uuid import uuid4
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from .storage import write_parquet_atomic
from .v4_x1_decision_v1_contract import _normalize_ticker


JAKARTA = ZoneInfo("Asia/Jakarta")
SCHEMA_VERSION = "idx_official_open_evidence_v1"
AUTHORITY = "IDX"
UPSTREAM_PATH = "TradingSummary/GetStockSummary"
FIELD_SEMANTICS = "IDX_OFFICIAL_OPENPRICE"
FALLBACK_POLICY = "NONE"
TRANSPORT = "DIRECT_IDX_HTTPS"
DIRECT_IDX_URL = "https://www.idx.co.id/primary/TradingSummary/GetStockSummary"


class OfficialOpenEvidenceError(RuntimeError):
    pass


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _session(value: object) -> str:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise OfficialOpenEvidenceError("OFFICIAL_OPEN_SESSION_INVALID")
    return pd.Timestamp(parsed).tz_localize(None).normalize().date().isoformat()


def _atomic_bytes(payload: bytes, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temp.write_bytes(payload)
    temp.replace(path)


def _atomic_json(payload: Mapping[str, object], path: Path) -> None:
    data = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n").encode("utf-8")
    _atomic_bytes(data, path)


def normalize_idx_stock_summary_payload(
    raw_bytes: bytes,
    *,
    expected_session_date: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Parse one complete official IDX Stock Summary response without price fallback.

    `open_price` is a literal numeric projection of raw `OpenPrice`. `FirstTrade`
    is retained only as an audit witness so downstream verification can prove
    that a positive FirstTrade never substitutes for a missing/non-positive OpenPrice.
    """

    session_date = _session(expected_session_date)
    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OfficialOpenEvidenceError("OFFICIAL_OPEN_RAW_JSON_INVALID") from exc
    if not isinstance(payload, dict):
        raise OfficialOpenEvidenceError("OFFICIAL_OPEN_RAW_NOT_OBJECT")
    rows = payload.get("data")
    if not isinstance(rows, list) or not rows:
        raise OfficialOpenEvidenceError("OFFICIAL_OPEN_RAW_DATA_MISSING")

    try:
        records_total = int(payload["recordsTotal"])
        records_filtered = int(payload["recordsFiltered"])
    except (KeyError, TypeError, ValueError) as exc:
        raise OfficialOpenEvidenceError("OFFICIAL_OPEN_RAW_COUNTS_INVALID") from exc
    if records_total <= 0 or records_filtered != records_total or len(rows) != records_total:
        raise OfficialOpenEvidenceError(
            "OFFICIAL_OPEN_RAW_FULL_SESSION_COUNT_MISMATCH:"
            f"ROWS={len(rows)}:TOTAL={records_total}:FILTERED={records_filtered}"
        )

    out: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise OfficialOpenEvidenceError("OFFICIAL_OPEN_RAW_ROW_INVALID")
        missing = {"StockCode", "Date", "OpenPrice", "FirstTrade"} - set(row)
        if missing:
            raise OfficialOpenEvidenceError(
                f"OFFICIAL_OPEN_RAW_SCHEMA_MISSING:{sorted(missing)}"
            )
        ticker = _normalize_ticker(row.get("StockCode"))
        row_date = _session(row.get("Date"))
        if row_date != session_date:
            raise OfficialOpenEvidenceError(
                f"OFFICIAL_OPEN_RAW_DATE_MISMATCH:{ticker}:{row_date}!={session_date}"
            )
        key = (ticker, row_date)
        if key in seen:
            raise OfficialOpenEvidenceError(f"OFFICIAL_OPEN_RAW_DUPLICATE_KEY:{ticker}:{row_date}")
        seen.add(key)
        out.append(
            {
                "ticker": ticker,
                "session_date": row_date,
                "open_price": pd.to_numeric(row.get("OpenPrice"), errors="coerce"),
                "first_trade": pd.to_numeric(row.get("FirstTrade"), errors="coerce"),
            }
        )

    frame = pd.DataFrame(out).sort_values(["ticker", "session_date"]).reset_index(drop=True)
    if frame["ticker"].eq("").any():
        raise OfficialOpenEvidenceError("OFFICIAL_OPEN_RAW_EMPTY_TICKER")
    return frame, {
        "records_total": records_total,
        "records_filtered": records_filtered,
        "row_count": int(len(frame)),
        "unique_ticker_count": int(frame["ticker"].nunique()),
    }


def fetch_direct_idx_stock_summary(
    session_date: str,
    *,
    get: Callable[..., requests.Response] = requests.get,
    timeout_seconds: float = 30.0,
) -> tuple[bytes, dict[str, object]]:
    session = _session(session_date)
    params = {
        "date": session.replace("-", ""),
        "start": 0,
        "length": 9999,
    }
    response = get(
        DIRECT_IDX_URL,
        params=params,
        headers={
            "Referer": "https://www.idx.co.id/",
            "User-Agent": "idx-trade-official-open/1.0",
            "Accept": "application/json,text/plain,*/*",
        },
        timeout=timeout_seconds,
    )
    if response.status_code != 200:
        raise OfficialOpenEvidenceError(
            f"OFFICIAL_OPEN_DIRECT_IDX_HTTP_{response.status_code}"
        )
    raw = bytes(response.content)
    if not raw:
        raise OfficialOpenEvidenceError("OFFICIAL_OPEN_DIRECT_IDX_EMPTY_RESPONSE")
    return raw, {
        "transport": TRANSPORT,
        "url": DIRECT_IDX_URL,
        "upstream_path": UPSTREAM_PATH,
        "request_params": params,
        "http_status": int(response.status_code),
    }


def certify_official_open_raw_response(
    raw_bytes: bytes,
    *,
    session_date: str,
    output_dir: str | Path,
    transport_metadata: Mapping[str, object] | None = None,
    captured_at_jakarta: datetime | None = None,
) -> Path:
    """Build complete evidence in staging, then atomically promote the session folder."""

    session = _session(session_date)
    normalized, counts = normalize_idx_stock_summary_payload(
        raw_bytes, expected_session_date=session
    )
    folder = Path(output_dir).expanduser().resolve()
    if folder.exists():
        raise OfficialOpenEvidenceError("OFFICIAL_OPEN_EVIDENCE_ALREADY_EXISTS")
    folder.parent.mkdir(parents=True, exist_ok=True)
    stage = folder.parent / f".{folder.name}.{uuid4().hex}.stage"
    if stage.exists():
        raise OfficialOpenEvidenceError("OFFICIAL_OPEN_STAGING_COLLISION")

    raw_path = stage / "raw_response.json"
    normalized_path = stage / "open_prices.parquet"
    manifest_path = stage / "manifest.json"
    try:
        stage.mkdir(parents=False, exist_ok=False)
        _atomic_bytes(raw_bytes, raw_path)
        write_parquet_atomic(normalized, normalized_path)
        raw_sha = _sha256_file(raw_path)
        normalized_sha = _sha256_file(normalized_path)

        open_numeric = pd.to_numeric(normalized["open_price"], errors="coerce")
        positive = open_numeric.notna() & (open_numeric > 0)
        now = captured_at_jakarta or datetime.now(JAKARTA)
        if now.tzinfo is None:
            now = now.replace(tzinfo=JAKARTA)
        else:
            now = now.astimezone(JAKARTA)

        manifest: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "session_date": session,
            "authority": AUTHORITY,
            "upstream_path": UPSTREAM_PATH,
            "transport": TRANSPORT,
            "transport_metadata": dict(transport_metadata or {}),
            "field_semantics": FIELD_SEMANTICS,
            "fallback_policy": FALLBACK_POLICY,
            "raw_artifact_path": raw_path.name,
            "raw_artifact_sha256": raw_sha,
            "normalized_artifact_path": normalized_path.name,
            "normalized_artifact_sha256": normalized_sha,
            "row_count": counts["row_count"],
            "unique_ticker_count": counts["unique_ticker_count"],
            "records_total": counts["records_total"],
            "records_filtered": counts["records_filtered"],
            "duplicate_key_count": 0,
            "positive_openprice_count": int(positive.sum()),
            "unavailable_openprice_count": int((~positive).sum()),
            "capture_timestamp_jakarta": now.isoformat(),
            "execution_grade": True,
        }
        _atomic_json(manifest, manifest_path)
        stage.replace(folder)
    except Exception:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        raise
    return folder / "manifest.json"


def capture_direct_idx_official_open(
    session_date: str,
    *,
    output_root: str | Path,
    get: Callable[..., requests.Response] = requests.get,
    timeout_seconds: float = 30.0,
) -> Path:
    session = _session(session_date)
    raw, metadata = fetch_direct_idx_stock_summary(
        session,
        get=get,
        timeout_seconds=timeout_seconds,
    )
    folder = Path(output_root) / "official_open" / session
    return certify_official_open_raw_response(
        raw,
        session_date=session,
        output_dir=folder,
        transport_metadata=metadata,
    )


__all__ = [
    "AUTHORITY",
    "DIRECT_IDX_URL",
    "FALLBACK_POLICY",
    "FIELD_SEMANTICS",
    "JAKARTA",
    "OfficialOpenEvidenceError",
    "SCHEMA_VERSION",
    "TRANSPORT",
    "UPSTREAM_PATH",
    "capture_direct_idx_official_open",
    "certify_official_open_raw_response",
    "fetch_direct_idx_stock_summary",
    "normalize_idx_stock_summary_payload",
]
