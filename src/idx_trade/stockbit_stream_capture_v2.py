"""Lean prospective Stockbit Stream capture with a prior-session liquidity universe.

This module is acquisition-only: it never reads returns, targets, model scores, O2,
or forward counters. Routine membership is selected from the last completed IDX
stock-summary session using regular-market traded value.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import quote

import requests

from idx_trade.stockbit_stream_archive import (
    MONTHLY_RESERVE,
    StreamArchiveError,
    ZapiClient,
    canonical_json_bytes,
    normalize_post,
    parse_stream_payload,
    sha256_bytes,
)

IDX_STOCK_SUMMARY_ENDPOINT = "https://api.zpi.web.id/v1/finance:idx/stock-summary"
ROUTINE_TOP_N = 200
PRIOR_SESSION_LOOKBACK_DAYS = 10


@dataclass(frozen=True)
class RuntimeUniverse:
    capture_date: str
    source_session: str
    rows: list[dict[str, Any]]
    source_raw: bytes
    source_sha256: str
    universe_sha256: str


class LeanArchive:
    def put_immutable(self, key: str, payload: bytes, content_type: str) -> str:
        raise NotImplementedError


class LocalLeanArchive(LeanArchive):
    def __init__(self, root: Path):
        self.root = root

    def put_immutable(self, key: str, payload: bytes, content_type: str) -> str:
        del content_type
        if key.startswith("/") or ".." in Path(key).parts:
            raise StreamArchiveError(f"unsafe archive key: {key}")
        path = self.root / key
        digest = sha256_bytes(payload)
        if path.exists():
            if sha256_bytes(path.read_bytes()) != digest:
                raise StreamArchiveError(f"immutable key changed: {key}")
            return digest
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return digest


class R2LeanArchive(LeanArchive):
    """S3-compatible immutable writes without read-after-write on the hot path."""

    def __init__(self, endpoint_url: str, bucket: str, access_key: str, secret_key: str, prefix: str):
        import boto3
        from botocore.config import Config

        if not all([endpoint_url, bucket, access_key, secret_key]):
            raise StreamArchiveError("R2/S3 archive credentials are incomplete")
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
            config=Config(retries={"max_attempts": 3, "mode": "standard"}),
        )

    def _key(self, key: str) -> str:
        if key.startswith("/") or ".." in Path(key).parts:
            raise StreamArchiveError(f"unsafe archive key: {key}")
        safe = key.replace("\\", "/")
        return f"{self.prefix}/{safe}" if self.prefix else safe

    def put_immutable(self, key: str, payload: bytes, content_type: str) -> str:
        from botocore.exceptions import ClientError

        digest = sha256_bytes(payload)
        object_key = self._key(key)
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=payload,
                ContentType=content_type,
                Metadata={"sha256": digest},
                IfNoneMatch="*",
            )
            return digest
        except ClientError as exc:
            status = int(exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0) or 0)
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if status != 412 and code not in {"PreconditionFailed", "412"}:
                raise StreamArchiveError(f"R2 immutable put failed for {key}: {code or status}") from exc

        try:
            head = self.client.head_object(Bucket=self.bucket, Key=object_key)
        except ClientError as exc:
            raise StreamArchiveError(f"R2 collision verification failed for {key}") from exc
        existing = str((head.get("Metadata") or {}).get("sha256", ""))
        if existing != digest:
            raise StreamArchiveError(f"immutable key changed: {key}")
        return digest


def archive_from_env() -> LeanArchive:
    backend = os.environ.get("STOCKBIT_STREAM_STORAGE_BACKEND", "s3").lower()
    if backend == "local":
        root = os.environ.get("STOCKBIT_STREAM_LOCAL_ROOT")
        if not root:
            raise StreamArchiveError("STOCKBIT_STREAM_LOCAL_ROOT is required")
        return LocalLeanArchive(Path(root))
    if backend != "s3":
        raise StreamArchiveError(f"unsupported archive backend: {backend}")
    return R2LeanArchive(
        os.environ.get("STOCKBIT_STREAM_S3_ENDPOINT", ""),
        os.environ.get("STOCKBIT_STREAM_S3_BUCKET", ""),
        os.environ.get("STOCKBIT_STREAM_S3_ACCESS_KEY_ID", ""),
        os.environ.get("STOCKBIT_STREAM_S3_SECRET_ACCESS_KEY", ""),
        os.environ.get("STOCKBIT_STREAM_STORAGE_PREFIX", "stockbit-stream-v2"),
    )


def _identity_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        ticker = str(row.get("ticker", "")).strip().upper()
        if not ticker or str(row.get("listed_to", "")).strip():
            continue
        if ticker in result:
            raise StreamArchiveError(f"duplicate active identity ticker: {ticker}")
        result[ticker] = row
    return result


def _row_date_matches(row: Mapping[str, Any], requested: date) -> bool:
    return str(row.get("Date", ""))[:10] == requested.isoformat()


def build_runtime_universe(
    *,
    api_key: str,
    identity_csv: Path,
    capture_date: str,
    top_n: int = ROUTINE_TOP_N,
    session_lookback_days: int = PRIOR_SESSION_LOOKBACK_DAYS,
    session: requests.Session | None = None,
) -> RuntimeUniverse:
    if top_n < 1 or top_n > 400:
        raise StreamArchiveError("top_n must be between 1 and 400")
    identities = _identity_rows(identity_csv)
    if len(identities) < top_n:
        raise StreamArchiveError(f"active identity whitelist has only {len(identities)} rows for top_n={top_n}")
    capture_day = date.fromisoformat(capture_date)
    http = session or requests.Session()

    last_error: str | None = None
    for lag in range(1, session_lookback_days + 1):
        candidate = capture_day - timedelta(days=lag)
        response = http.get(
            IDX_STOCK_SUMMARY_ENDPOINT,
            params={"length": 1000, "start": 0, "date": candidate.isoformat()},
            headers={"x-api-key": api_key},
            timeout=30,
        )
        if response.status_code in {401, 403, 429}:
            raise StreamArchiveError(f"IDX universe request blocked: HTTP {response.status_code}")
        if response.status_code != 200:
            last_error = f"HTTP {response.status_code} for {candidate}"
            continue
        raw = bytes(response.content)
        try:
            payload = response.json()
            data = payload["data"]
        except (ValueError, KeyError, TypeError):
            last_error = f"malformed stock-summary for {candidate}"
            continue
        if payload.get("provider") != "idx" or payload.get("dataset") != "stock-summary" or not isinstance(data, list) or not data:
            last_error = f"invalid/empty stock-summary for {candidate}"
            continue
        if not all(isinstance(row, dict) and _row_date_matches(row, candidate) for row in data):
            last_error = f"stock-summary date filter not honored for {candidate}"
            continue

        ranked: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in data:
            ticker = str(row.get("StockCode", "")).strip().upper()
            if ticker not in identities or ticker in seen:
                continue
            seen.add(ticker)
            try:
                total_value = float(row.get("Value") or 0)
                nonregular_value = float(row.get("NonRegularValue") or 0)
                value = max(total_value - nonregular_value, 0.0)
            except (TypeError, ValueError):
                continue
            if value <= 0:
                continue
            identity = identities[ticker]
            ranked.append({
                "ticker": ticker,
                "company_name": identity.get("company_name", ""),
                "listed_from": identity.get("listed_from", ""),
                "source_session": candidate.isoformat(),
                "regular_value": value,
            })
        ranked.sort(key=lambda row: (-row["regular_value"], row["ticker"]))
        if len(ranked) < top_n:
            last_error = f"only {len(ranked)} active positive-value rows for {candidate}"
            continue
        selected = ranked[:top_n]
        for rank, row in enumerate(selected, start=1):
            row["activity_rank"] = rank
        universe_bytes = canonical_json_bytes(selected)
        return RuntimeUniverse(
            capture_date=capture_date,
            source_session=candidate.isoformat(),
            rows=selected,
            source_raw=raw,
            source_sha256=sha256_bytes(raw),
            universe_sha256=sha256_bytes(universe_bytes),
        )

    raise StreamArchiveError(f"no valid completed IDX stock-summary session found: {last_error}")


def capture_stream_v2(
    *,
    client: ZapiClient,
    archive: LeanArchive,
    universe: RuntimeUniverse,
    slot: str,
    hmac_salt: str,
    monthly_reserve: int = MONTHLY_RESERVE,
) -> dict[str, Any]:
    if not hmac_salt:
        raise StreamArchiveError("STOCKBIT_STREAM_HMAC_SALT is required")
    if not universe.rows:
        raise StreamArchiveError("runtime universe is empty")

    run_id = f"{universe.capture_date}_{slot}_{universe.universe_sha256[:16]}"
    quota_before = client.get_usage()
    planned_calls = len(universe.rows)
    if quota_before.remaining - planned_calls < monthly_reserve:
        return {
            "status": "QUOTA_BLOCKED_BEFORE_STREAM_REQUEST",
            "run_id": run_id,
            "planned_calls": planned_calls,
            "quota_before": quota_before.__dict__,
            "provider_calls": 1,
            "outcome_accessed": False,
        }

    universe_input_key = f"universe_inputs/{run_id}/idx-stock-summary-{universe.source_session}.json"
    archive.put_immutable(universe_input_key, universe.source_raw, "application/json")

    request_records: list[dict[str, Any]] = []
    total_rows = 0
    ok_responses = 0
    for selected in universe.rows:
        symbol = selected["ticker"]
        response, raw, observed_at = client.stream(symbol)
        raw_key = f"raw/{run_id}/{quote(symbol, safe='')}.json"
        raw_sha = archive.put_immutable(raw_key, raw, response.headers.get("content-type", "application/json"))
        classification, _, items = parse_stream_payload(raw, response.status_code, symbol)
        record = {
            "ticker": symbol,
            "activity_rank": selected["activity_rank"],
            "response_classification": classification,
            "http_status": response.status_code,
            "observed_available_at_utc": observed_at.isoformat().replace("+00:00", "Z"),
            "row_count": len(items),
            "raw_key": raw_key,
            "raw_sha256": raw_sha,
        }
        if classification == "OK":
            normalized = [normalize_post(item, symbol, "ROUTINE_TOP_VALUE", observed_at, hmac_salt) for item in items]
            normalized_bytes = b"".join(canonical_json_bytes(row) for row in sorted(normalized, key=lambda row: row["post_id"]))
            normalized_key = f"normalized/{run_id}/{quote(symbol, safe='')}.jsonl"
            record["normalized_key"] = normalized_key
            record["normalized_sha256"] = archive.put_immutable(normalized_key, normalized_bytes, "application/jsonl")
            total_rows += len(normalized)
            ok_responses += 1
        request_records.append(record)

    try:
        quota_after_payload: dict[str, Any] = client.get_usage().__dict__
    except StreamArchiveError as exc:
        # The stream responses and immutable objects are already captured at
        # this point. A slow quota telemetry endpoint must not discard the run
        # manifest; preserve the diagnostic as an explicit non-authoritative
        # field instead of pretending the after-quota snapshot exists.
        quota_after_payload = {
            "status": "UNAVAILABLE",
            "source": "MCP_GET_USAGE",
            "detail": str(exc),
        }
    status = (
        "DATA_READY"
        if request_records
        and len(request_records) == planned_calls
        and all(record.get("response_classification") == "OK" for record in request_records)
        else "PARTIAL_FAILURE"
    )
    manifest = {
        "schema_version": "stockbit_stream_capture_v2",
        "status": status,
        "run_id": run_id,
        "capture_date": universe.capture_date,
        "slot": slot,
        "selection_rule": "top N active current identities by prior completed IDX session regular-market Value; ticker tie-break",
        "source_session": universe.source_session,
        "universe_size": len(universe.rows),
        "universe_sha256": universe.universe_sha256,
        "universe_source_sha256": universe.source_sha256,
        "planned_calls": planned_calls,
        "completed_calls": len(request_records),
        "successful_responses": ok_responses,
        "normalized_post_rows": total_rows,
        "response_classification_counts": {},
        "quota_before": quota_before.__dict__,
        "quota_after": quota_after_payload,
        "request_records": request_records,
        "storage_contract": "conditional immutable PUT; no normal-path object readback; collision verified by object SHA metadata",
        "first_seen_semantics": "derive post first-seen offline as minimum observed_available_at_utc across immutable observations; no per-post hot-path object writes",
        "model_accessed": False,
        "outcome_accessed": False,
        "counter_mutated": False,
    }
    for record in request_records:
        key = record["response_classification"]
        manifest["response_classification_counts"][key] = manifest["response_classification_counts"].get(key, 0) + 1
    manifest_bytes = canonical_json_bytes(manifest)
    manifest_key = f"manifests/{run_id}.json"
    manifest_sha = archive.put_immutable(manifest_key, manifest_bytes, "application/json")
    manifest["manifest_sha256"] = manifest_sha
    return manifest
