"""Lean prospective Stockbit Stream capture with a prior-session liquidity universe.

This module is acquisition-only: it never reads returns, targets, model scores, O2,
or forward counters. Routine membership is selected from the last completed IDX
stock-summary session using regular-market traded value.
"""
from __future__ import annotations

import csv
import math
import os
import re
import secrets
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import quote

import requests

from idx_trade.stockbit_stream_archive import (
    MONTHLY_RESERVE,
    TICKER_RE,
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
V2_SLOTS = frozenset({"pre_open", "midday", "after_close"})
ATTEMPT_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")


@dataclass(frozen=True)
class RuntimeUniverse:
    capture_date: str
    source_session: str
    rows: list[dict[str, Any]]
    source_raw: bytes
    source_sha256: str
    universe_sha256: str
    identity_source_sha256: str = ""
    selection_diagnostics: dict[str, Any] = field(default_factory=dict)


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
    """S3-compatible immutable writes; body-read verification occurs only on collisions."""

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

        # Collision is rare, so verify the actual immutable body rather than trusting
        # user-controlled object metadata as an integrity oracle.
        try:
            existing = self.client.get_object(Bucket=self.bucket, Key=object_key)["Body"].read()
        except Exception as exc:
            raise StreamArchiveError(f"R2 collision verification failed for {key}") from exc
        if sha256_bytes(existing) != digest:
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
        if not ticker:
            continue
        if not TICKER_RE.fullmatch(ticker):
            raise StreamArchiveError(f"invalid identity ticker: {ticker!r}")
        if str(row.get("listed_to", "")).strip():
            continue
        if ticker in result:
            raise StreamArchiveError(f"duplicate active identity ticker: {ticker}")
        result[ticker] = row
    return result


def _row_date_matches(row: Mapping[str, Any], requested: date) -> bool:
    return str(row.get("Date", ""))[:10] == requested.isoformat()


def _unwrap_zapi_envelope(payload: Any) -> Any:
    if (
        isinstance(payload, dict)
        and "project" in payload
        and "timestamp" in payload
        and isinstance(payload.get("data"), dict)
    ):
        return payload["data"]
    return payload


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
    identity_source_sha = sha256_bytes(identity_csv.read_bytes())
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
            payload = _unwrap_zapi_envelope(response.json())
            if not isinstance(payload, dict):
                raise TypeError("payload is not an object")
            data = payload["data"]
            records_total = int(payload["recordsTotal"])
            records_filtered = int(payload.get("recordsFiltered", records_total))
        except (ValueError, KeyError, TypeError):
            raise StreamArchiveError(f"malformed stock-summary for {candidate}")
        if payload.get("provider") != "idx" or payload.get("dataset") != "stock-summary" or not isinstance(data, list):
            raise StreamArchiveError(f"invalid stock-summary contract for {candidate}")
        if not data:
            if records_total == 0 and records_filtered == 0:
                last_error = f"empty stock-summary for non-session {candidate}"
                continue
            raise StreamArchiveError(f"stock-summary row-count metadata inconsistent for {candidate}")
        if records_total != records_filtered or records_filtered != len(data):
            raise StreamArchiveError(
                f"incomplete stock-summary pagination for {candidate}: "
                f"recordsTotal={records_total}, recordsFiltered={records_filtered}, rows={len(data)}"
            )
        if not all(isinstance(row, dict) and _row_date_matches(row, candidate) for row in data):
            raise StreamArchiveError(f"stock-summary date filter not honored for {candidate}")

        provider_codes = [str(row.get("StockCode", "")).strip().upper() for row in data]
        nonblank_codes = [code for code in provider_codes if code]
        if len(nonblank_codes) != len(set(nonblank_codes)):
            raise StreamArchiveError(f"duplicate StockCode rows in stock-summary for {candidate}")

        ranked: list[dict[str, Any]] = []
        invalid_numeric: list[str] = []
        for row in data:
            ticker = str(row.get("StockCode", "")).strip().upper()
            if ticker not in identities:
                continue
            try:
                total_value = float(row.get("Value") or 0)
                nonregular_value = float(row.get("NonRegularValue") or 0)
            except (TypeError, ValueError):
                invalid_numeric.append(ticker)
                continue
            if (
                not math.isfinite(total_value)
                or not math.isfinite(nonregular_value)
                or total_value < 0
                or nonregular_value < 0
                or nonregular_value > total_value
            ):
                invalid_numeric.append(ticker)
                continue
            value = total_value - nonregular_value
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
            raise StreamArchiveError(f"only {len(ranked)} valid active positive-value rows for {candidate}")
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
            identity_source_sha256=identity_source_sha,
            selection_diagnostics={"invalid_numeric_tickers": sorted(invalid_numeric)},
        )

    raise StreamArchiveError(f"no valid completed IDX stock-summary session found: {last_error}")


def _attempt_id() -> str:
    configured = os.environ.get("STOCKBIT_STREAM_ATTEMPT_ID", "").strip()
    if configured:
        if not ATTEMPT_ID_RE.fullmatch(configured):
            raise StreamArchiveError("invalid STOCKBIT_STREAM_ATTEMPT_ID")
        return configured
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{stamp}-{secrets.token_hex(4)}"


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
    if slot not in V2_SLOTS:
        raise StreamArchiveError(f"invalid capture slot: {slot}")

    logical_slot_id = f"{universe.capture_date}_{slot}_{universe.universe_sha256[:16]}"
    attempt_id = _attempt_id()
    run_id = f"{logical_slot_id}_{attempt_id}"
    attempt_started_at = datetime.now(timezone.utc)
    quota_before = client.get_usage()
    planned_calls = len(universe.rows)
    if quota_before.remaining - planned_calls < monthly_reserve:
        return {
            "status": "QUOTA_BLOCKED_BEFORE_STREAM_REQUEST",
            "logical_slot_id": logical_slot_id,
            "attempt_id": attempt_id,
            "run_id": run_id,
            "planned_calls": planned_calls,
            "quota_before": quota_before.__dict__,
            "provider_calls": 0,
            "outcome_accessed": False,
        }

    universe_input_key = f"universe_inputs/{run_id}/idx-stock-summary-{universe.source_session}.json"
    archive.put_immutable(universe_input_key, universe.source_raw, "application/json")

    request_records: list[dict[str, Any]] = []
    total_rows = 0
    ok_responses = 0
    for selected in universe.rows:
        symbol = selected["ticker"]
        try:
            response, raw, observed_at = client.stream(symbol)
        except (requests.RequestException, StreamArchiveError) as exc:
            request_records.append({
                "ticker": symbol,
                "activity_rank": selected["activity_rank"],
                "response_classification": "REQUEST_EXCEPTION",
                "error_type": type(exc).__name__,
                "row_count": 0,
            })
            continue

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
        if response.status_code in {401, 403, 429}:
            break

    quota_after = None
    quota_after_error = None
    try:
        quota_after = client.get_usage()
    except StreamArchiveError as exc:
        quota_after_error = {"type": type(exc).__name__, "detail": str(exc)}

    completed_calls = len(request_records)
    if completed_calls == planned_calls and ok_responses == planned_calls:
        status = "DATA_READY"
    elif ok_responses > 0:
        status = "DATA_PARTIAL"
    else:
        status = "DATA_FAILED"

    attempt_finished_at = datetime.now(timezone.utc)
    manifest = {
        "schema_version": "stockbit_stream_capture_v2_hardened",
        "status": status,
        "logical_slot_id": logical_slot_id,
        "attempt_id": attempt_id,
        "run_id": run_id,
        "capture_date": universe.capture_date,
        "slot": slot,
        "attempt_started_at_utc": attempt_started_at.isoformat().replace("+00:00", "Z"),
        "attempt_finished_at_utc": attempt_finished_at.isoformat().replace("+00:00", "Z"),
        "attempt_duration_seconds": (attempt_finished_at - attempt_started_at).total_seconds(),
        "selection_rule": "top N active pinned identities by prior completed IDX session regular-market Value; ticker tie-break",
        "source_session": universe.source_session,
        "universe_size": len(universe.rows),
        "universe_sha256": universe.universe_sha256,
        "universe_source_sha256": universe.source_sha256,
        "identity_source_sha256": universe.identity_source_sha256,
        "selection_diagnostics": universe.selection_diagnostics,
        "planned_calls": planned_calls,
        "completed_calls": completed_calls,
        "successful_responses": ok_responses,
        "normalized_post_rows": total_rows,
        "response_classification_counts": {},
        "quota_before": quota_before.__dict__,
        "quota_after": quota_after.__dict__ if quota_after is not None else None,
        "quota_after_error": quota_after_error,
        "request_records": request_records,
        "storage_contract": "conditional immutable PUT; no normal-path object readback; collision body hash verified by GET only on 412",
        "first_seen_semantics": "derive post first-seen offline as minimum observed_available_at_utc across immutable observations; no per-post hot-path object writes",
        "model_accessed": False,
        "outcome_accessed": False,
        "counter_mutated": False,
    }
    for record in request_records:
        key = record["response_classification"]
        manifest["response_classification_counts"][key] = manifest["response_classification_counts"].get(key, 0) + 1
    manifest_bytes = canonical_json_bytes(manifest)
    manifest_key = f"manifests/{logical_slot_id}/{attempt_id}.json"
    manifest_sha = archive.put_immutable(manifest_key, manifest_bytes, "application/json")
    manifest["manifest_sha256"] = manifest_sha
    return manifest
