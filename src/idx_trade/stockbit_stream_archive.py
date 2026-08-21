"""Outcome-blind, append-only Stockbit Stream capture primitives.

This module deliberately owns only community-stream archiving.  It does not
join prices, labels, model scores, sentiment, or forward counters.
"""

from __future__ import annotations

import csv
import hashlib
import hmac
import json
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol
from urllib.parse import quote

import requests


STREAM_ENDPOINT = "https://api.zpi.web.id/v1/finance:stockbit/stream"
MCP_ENDPOINT = "https://mcp.zpi.web.id/mcp"
STREAM_COUNT = 50
MONTHLY_RESERVE = 500
UNIVERSE_COLUMNS = (
    "ticker",
    "company_name",
    "listed_from",
    "listed_to",
    "capture_broad",
    "capture_high",
    "activity_rank",
    "activity_median_regular_value_60",
    "universe_source",
)
SLOTS = ("pre_open", "midday", "after_close")
SCHEDULE_CRONS = {
    "47 1 * * 1-5": "pre_open",  # 08:47 Asia/Jakarta
    "7 5 * * 1-5": "midday",  # 12:07 Asia/Jakarta
    "47 9 * * 1-5": "after_close",  # 16:47 Asia/Jakarta
}
CASHTAG_RE = re.compile(r"(?<![A-Za-z0-9_])\$([A-Z][A-Z0-9]{1,5})(?![A-Za-z0-9_])")
TICKER_RE = re.compile(r"^[A-Z][A-Z0-9]{1,5}$")


class StreamArchiveError(RuntimeError):
    """Fail-closed capture or archive error."""


class StorageConfigurationError(StreamArchiveError):
    """Durable private storage is not configured."""


class StorageImmutabilityConflict(StreamArchiveError):
    """An immutable key already exists with different bytes."""


class StorageArchiveError(StreamArchiveError):
    """A durable-store operation could not be verified."""


@dataclass(frozen=True)
class QuotaSnapshot:
    tier: str
    used: int
    limit: int
    remaining: int
    reset_at: str | None
    source: str

    @classmethod
    def from_usage(cls, quota: Mapping[str, Any]) -> "QuotaSnapshot":
        try:
            tier = str(quota["tier"])
            used = int(quota["used"])
            limit = int(quota["limit"])
            remaining = int(quota["remaining"])
        except (KeyError, TypeError, ValueError) as exc:
            raise StreamArchiveError("Zapi usage response has invalid quota") from exc
        if min(used, limit, remaining) < 0 or used + remaining > limit:
            raise StreamArchiveError("Zapi usage quota is inconsistent")
        return cls(tier, used, limit, remaining, quota.get("resetAt"), "MCP_GET_USAGE")

    @classmethod
    def from_headers(
        cls, headers: Mapping[str, str], previous: "QuotaSnapshot | None" = None
    ) -> "QuotaSnapshot | None":
        remaining = headers.get("x-ratelimit-remaining-month")
        limit = headers.get("x-ratelimit-limit-month")
        if remaining is None or limit is None:
            return previous
        try:
            remaining_i, limit_i = int(remaining), int(limit)
        except ValueError:
            return previous
        if remaining_i < 0 or limit_i <= 0 or remaining_i > limit_i:
            return previous
        used = limit_i - remaining_i
        return cls(previous.tier if previous else "UNKNOWN", used, limit_i, remaining_i, previous.reset_at if previous else None, "REST_HEADERS")


@dataclass(frozen=True)
class PutResult:
    key: str
    sha256: str
    created: bool


class ImmutableStore(Protocol):
    def put_if_absent(self, key: str, payload: bytes, content_type: str) -> PutResult: ...

    def read(self, key: str) -> bytes | None: ...


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _safe_key(key: str) -> str:
    if not key or key.startswith("/") or ".." in Path(key).parts:
        raise StreamArchiveError(f"unsafe archive key: {key!r}")
    return key.replace("\\", "/")


class LocalImmutableStore:
    """Test/local implementation; production uses S3-compatible storage."""

    def __init__(self, root: Path):
        self.root = root

    def _path(self, key: str) -> Path:
        return self.root / _safe_key(key)

    def read(self, key: str) -> bytes | None:
        path = self._path(key)
        return path.read_bytes() if path.exists() else None

    def put_if_absent(self, key: str, payload: bytes, content_type: str) -> PutResult:
        del content_type
        path = self._path(key)
        digest = sha256_bytes(payload)
        if path.exists():
            existing = path.read_bytes()
            existing_sha = sha256_bytes(existing)
            if existing_sha != digest:
                raise StorageImmutabilityConflict(f"immutable key changed: {key}")
            return PutResult(key, digest, False)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
        temporary.write_bytes(payload)
        temporary.replace(path)
        return PutResult(key, digest, True)


class S3ImmutableStore:
    """Private S3/R2-compatible immutable object store."""

    def __init__(self, endpoint_url: str, bucket: str, access_key_id: str, secret_access_key: str, prefix: str = ""):
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - exercised in deployment
            raise StorageConfigurationError("boto3 is required for S3 storage") from exc
        if not endpoint_url or not bucket or not access_key_id or not secret_access_key:
            raise StorageConfigurationError("S3 endpoint, bucket, and credentials are required")
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",
        )

    def _key(self, key: str) -> str:
        safe = _safe_key(key)
        return f"{self.prefix}/{safe}" if self.prefix else safe

    def read(self, key: str) -> bytes | None:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=self._key(key))
        except Exception as exc:  # boto3 exposes provider-specific not-found types
            response_metadata = getattr(exc, "response", {}) or {}
            code = str(response_metadata.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey", "NoSuchObject"}:
                return None
            raise StorageArchiveError(f"storage read failed for {key}") from exc
        return response["Body"].read()

    def put_if_absent(self, key: str, payload: bytes, content_type: str) -> PutResult:
        digest = sha256_bytes(payload)
        existing = self.read(key)
        if existing is not None:
            if sha256_bytes(existing) != digest:
                raise StorageImmutabilityConflict(f"immutable key changed: {key}")
            return PutResult(key, digest, False)
        self.client.put_object(Bucket=self.bucket, Key=self._key(key), Body=payload, ContentType=content_type)
        confirmed = self.read(key)
        if confirmed is None or sha256_bytes(confirmed) != digest:
            raise StorageArchiveError(f"storage write could not be verified for {key}")
        return PutResult(key, digest, True)


def build_store_from_env() -> ImmutableStore:
    backend = str(os.environ.get("STOCKBIT_STREAM_STORAGE_BACKEND", "s3")).lower()
    if backend == "local":
        root = os.environ.get("STOCKBIT_STREAM_LOCAL_ROOT")
        if not root:
            raise StorageConfigurationError("STOCKBIT_STREAM_LOCAL_ROOT is required for local storage")
        return LocalImmutableStore(Path(root))
    if backend != "s3":
        raise StorageConfigurationError(f"unsupported storage backend: {backend}")
    env = os.environ
    return S3ImmutableStore(
        env.get("STOCKBIT_STREAM_S3_ENDPOINT", ""),
        env.get("STOCKBIT_STREAM_S3_BUCKET", ""),
        env.get("STOCKBIT_STREAM_S3_ACCESS_KEY_ID", ""),
        env.get("STOCKBIT_STREAM_S3_SECRET_ACCESS_KEY", ""),
        env.get("STOCKBIT_STREAM_STORAGE_PREFIX", "stockbit-stream-v1"),
    )


def load_universe(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or tuple(rows[0].keys()) != UNIVERSE_COLUMNS:
        raise StreamArchiveError("universe schema mismatch")
    tickers: set[str] = set()
    for row in rows:
        ticker = row["ticker"]
        if not TICKER_RE.fullmatch(ticker) or ticker in tickers:
            raise StreamArchiveError(f"invalid or duplicate ticker in universe: {ticker!r}")
        tickers.add(ticker)
        if row["listed_to"].strip():
            raise StreamArchiveError(f"delisted ticker in prospective universe: {ticker}")
        if row["capture_broad"] not in {"0", "1"} or row["capture_high"] not in {"0", "1"}:
            raise StreamArchiveError(f"invalid capture flags for {ticker}")
        if row["capture_high"] == "1" and row["capture_broad"] != "1":
            raise StreamArchiveError(f"high-activity ticker is not in broad universe: {ticker}")
    if not any(row["capture_broad"] == "1" for row in rows):
        raise StreamArchiveError("universe has no broad capture rows")
    if not any(row["capture_high"] == "1" for row in rows):
        raise StreamArchiveError("universe has no high-activity capture rows")
    return rows


def universe_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def verify_universe_manifest(csv_path: Path, manifest_path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = manifest["output_sha256"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise StreamArchiveError("universe manifest is missing or malformed") from exc
    actual = universe_sha256(csv_path)
    if actual != expected:
        raise StreamArchiveError("universe CSV does not match its pinned manifest")
    return manifest


def symbols_for_slot(rows: Iterable[Mapping[str, str]], slot: str) -> list[tuple[str, str]]:
    if slot not in SLOTS:
        raise StreamArchiveError(f"unknown capture slot: {slot}")
    flag = "capture_high" if slot != "after_close" else "capture_broad"
    return [(row["ticker"], "HIGH_ACTIVITY" if row["capture_high"] == "1" else "BROAD") for row in rows if row[flag] == "1"]


def _safe_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {k: v for k, v in headers.items() if k.lower().startswith("x-ratelimit-") or k.lower() in {"content-type", "etag"}}


class ZapiClient:
    def __init__(self, api_key: str, timeout_seconds: float = 30.0, session: requests.Session | None = None):
        if not api_key:
            raise StreamArchiveError("ZAPI_API_KEY is required")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def get_usage(self) -> QuotaSnapshot:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        init = self.session.post(MCP_ENDPOINT, headers=headers, json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "idx-trade-stockbit-stream", "version": "1"}}}, timeout=self.timeout_seconds)
        if init.status_code != 200:
            raise StreamArchiveError(f"Zapi quota initialize failed: HTTP {init.status_code}")
        rpc_headers = dict(headers)
        if init.headers.get("mcp-session-id"):
            rpc_headers["Mcp-Session-Id"] = init.headers["mcp-session-id"]
        usage = self.session.post(MCP_ENDPOINT, headers=rpc_headers, json={"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "get_usage", "arguments": {}}}, timeout=self.timeout_seconds)
        if usage.status_code != 200:
            raise StreamArchiveError(f"Zapi quota usage failed: HTTP {usage.status_code}")
        parsed = _parse_sse_json(usage.text)
        try:
            quota = parsed["result"]["structuredContent"]["quota"]
        except (KeyError, TypeError) as exc:
            raise StreamArchiveError("Zapi quota response missing structured quota") from exc
        return QuotaSnapshot.from_usage(quota)

    def stream(self, symbol: str) -> tuple[requests.Response, bytes, datetime]:
        observed = datetime.now(timezone.utc)
        response = self.session.get(STREAM_ENDPOINT, params={"symbol": symbol, "count": STREAM_COUNT}, headers={"x-api-key": self.api_key}, timeout=self.timeout_seconds)
        return response, bytes(response.content), observed


def _parse_sse_json(text: str) -> dict[str, Any]:
    for line in text.splitlines():
        if line.startswith("data: "):
            try:
                value = json.loads(line[6:])
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
    raise StreamArchiveError("Zapi MCP response did not contain a JSON-RPC message")


def parse_stream_payload(raw: bytes, status_code: int, requested_symbol: str) -> tuple[str, dict[str, Any] | None, list[dict[str, Any]]]:
    if status_code != 200:
        return f"HTTP_{status_code}", None, []
    try:
        wrapper = json.loads(raw.decode("utf-8"))
        data = wrapper["data"]
        items = data["items"]
        symbol = data["symbol"]
        declared_count = int(data["count"])
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return "SCHEMA_ERROR", None, []
    if symbol != requested_symbol or not isinstance(items, list) or declared_count != len(items):
        return "PARTIAL_OR_SYMBOL_MISMATCH", None, []
    if not items:
        return "EMPTY_RESPONSE_FAIL_CLOSED", data, []
    if len({str(item.get("id")) for item in items if isinstance(item, dict)}) != len(items):
        return "DUPLICATE_POST_ID_FAIL_CLOSED", data, []
    for item in items:
        if not isinstance(item, dict) or item.get("id") in {None, ""} or not isinstance(item.get("createdAt"), str) or "content" not in item:
            return "ITEM_SCHEMA_ERROR", data, []
    return "OK", data, items


def _created_at_metadata(raw_value: str) -> tuple[str | None, str]:
    try:
        parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError:
        return None, "INVALID"
    if parsed.tzinfo is None:
        return None, "NAIVE_TIMEZONE_UNRESOLVED"
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"), "EXPLICIT_OFFSET"


def _mentioned_tickers(item: Mapping[str, Any]) -> list[str]:
    values: set[str] = set()
    raw_tickers = item.get("tickers")
    if isinstance(raw_tickers, list):
        for value in raw_tickers:
            if isinstance(value, str) and TICKER_RE.fullmatch(value.upper()):
                values.add(value.upper())
    content = item.get("content")
    if isinstance(content, str):
        values.update(match.group(1) for match in CASHTAG_RE.finditer(content.upper()))
    return sorted(values)


def normalize_post(item: Mapping[str, Any], requested_symbol: str, bucket: str, observed_at: datetime, hmac_salt: str) -> dict[str, Any]:
    post_id = str(item["id"])
    content = str(item.get("content", ""))
    identity = item.get("userId") or item.get("username") or item.get("fullName")
    author_pseudonym = None
    identity_kind = "NOT_PRESENT"
    if identity is not None and str(identity):
        identity_kind = "USER_ID" if item.get("userId") else ("USERNAME" if item.get("username") else "FULL_NAME")
        author_pseudonym = hmac.new(hmac_salt.encode("utf-8"), str(identity).encode("utf-8"), hashlib.sha256).hexdigest()
    source_created_at_utc, timezone_status = _created_at_metadata(str(item["createdAt"]))
    return {
        "post_id": post_id,
        "requested_symbol": requested_symbol,
        "capture_bucket": bucket,
        "source": "ZAPI_FINANCE_STOCKBIT_STREAM",
        "endpoint": STREAM_ENDPOINT,
        "source_created_at_raw": str(item["createdAt"]),
        "source_created_at_utc": source_created_at_utc,
        "source_created_at_timezone_status": timezone_status,
        "observed_available_at_utc": observed_at.isoformat().replace("+00:00", "Z"),
        "content": content,
        "content_sha256": sha256_bytes(content.encode("utf-8")),
        "mentioned_tickers": _mentioned_tickers(item),
        "author_pseudonym_hmac_sha256": author_pseudonym,
        "author_identity_kind": identity_kind,
        "likes": item.get("likes"),
        "dislikes": item.get("dislikes"),
        "replies": item.get("replies"),
        "reposts": item.get("reposts"),
        "shares": item.get("shares"),
        "views": item.get("views"),
        "flags": {key: item.get(key) for key in sorted(item) if key.startswith("is") or key in {"commenterType", "verifiedStatus", "userPrivilege"}},
    }


def _canonical_post_bytes(post: Mapping[str, Any], first_seen_at_utc: str) -> bytes:
    return canonical_json_bytes({
        "schema_version": "stockbit_stream_post_v1",
        "post_id": post["post_id"],
        "first_seen_at_utc": first_seen_at_utc,
        "source_created_at_raw": post["source_created_at_raw"],
        "source_created_at_utc": post["source_created_at_utc"],
        "source_created_at_timezone_status": post["source_created_at_timezone_status"],
        "content_sha256": post["content_sha256"],
        "author_pseudonym_hmac_sha256": post["author_pseudonym_hmac_sha256"],
    })


def capture_stream_run(
    *,
    client: ZapiClient,
    store: ImmutableStore,
    universe_rows: list[dict[str, str]],
    slot: str,
    capture_date: str,
    hmac_salt: str,
    universe_sha: str,
    monthly_reserve: int = MONTHLY_RESERVE,
) -> dict[str, Any]:
    if not hmac_salt:
        raise StreamArchiveError("STOCKBIT_STREAM_HMAC_SALT is required")
    planned = symbols_for_slot(universe_rows, slot)
    run_id = f"{capture_date}_{slot}_{universe_sha[:16]}"
    manifest_key = f"manifests/{run_id}.json"
    existing_manifest = store.read(manifest_key)
    if existing_manifest is not None:
        try:
            existing = json.loads(existing_manifest.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StorageArchiveError(f"existing manifest is malformed: {run_id}") from exc
        if any(existing.get(key) != expected for key, expected in {
            "run_id": run_id,
            "capture_date": capture_date,
            "slot": slot,
            "universe_sha256": universe_sha,
        }.items()):
            raise StorageImmutabilityConflict(f"existing manifest identity mismatch: {run_id}")
        existing["manifest_sha256"] = sha256_bytes(existing_manifest)
        existing["idempotent_replay"] = True
        return existing

    quota_before = client.get_usage()
    if quota_before.remaining < len(planned) + monthly_reserve:
        manifest = {
            "schema_version": "stockbit_stream_capture_manifest_v1",
            "status": "QUOTA_BLOCKED_BEFORE_REQUEST",
            "run_id": run_id,
            "slot": slot,
            "capture_date": capture_date,
            "planned_calls": len(planned),
            "completed_calls": 0,
            "quota_before": quota_before.__dict__,
            "monthly_reserve": monthly_reserve,
            "provider_calls": False,
            "storage_verification": {"immutable_put_and_readback": True},
            "outcome_accessed": False,
        }
        result = store.put_if_absent(manifest_key, canonical_json_bytes(manifest), "application/json")
        manifest["manifest_sha256"] = result.sha256
        return manifest

    request_records: list[dict[str, Any]] = []
    normalized_rows: list[dict[str, Any]] = []
    quota_current = quota_before
    for symbol, bucket in planned:
        if quota_current.remaining <= monthly_reserve:
            request_records.append({"ticker": symbol, "bucket": bucket, "status": "QUOTA_STOP_BEFORE_REQUEST"})
            break
        response, raw, observed_at = client.stream(symbol)
        raw_key = f"raw/{run_id}/{quote(symbol, safe='')}.json"
        raw_result = store.put_if_absent(raw_key, raw, response.headers.get("content-type", "application/json"))
        classification, data, items = parse_stream_payload(raw, response.status_code, symbol)
        record: dict[str, Any] = {
            "ticker": symbol,
            "bucket": bucket,
            "endpoint": STREAM_ENDPOINT,
            "params": {"symbol": symbol, "count": STREAM_COUNT},
            "http_status": response.status_code,
            "observed_available_at_utc": observed_at.isoformat().replace("+00:00", "Z"),
            "safe_headers": _safe_headers(response.headers),
            "response_classification": classification,
            "row_count": len(items),
            "raw_key": raw_key,
            "raw_sha256": raw_result.sha256,
        }
        if classification == "OK":
            rows_for_symbol: list[dict[str, Any]] = []
            for item in items:
                post = normalize_post(item, symbol, bucket, observed_at, hmac_salt)
                first_key = f"posts/{post['post_id']}.json"
                existing = store.read(first_key)
                first_seen = observed_at.isoformat().replace("+00:00", "Z")
                canonical = _canonical_post_bytes(post, first_seen)
                if existing is None:
                    store.put_if_absent(first_key, canonical, "application/json")
                    observation_type = "FIRST_SEEN"
                else:
                    existing_obj = json.loads(existing.decode("utf-8"))
                    if existing_obj.get("content_sha256") != post["content_sha256"]:
                        raise StorageImmutabilityConflict(f"post content changed for {post['post_id']}")
                    first_seen = str(existing_obj["first_seen_at_utc"])
                    observation_type = "REOBSERVATION"
                post["first_seen_at_utc"] = first_seen
                post["observation_type"] = observation_type
                rows_for_symbol.append(post)
            normalized_bytes = b"".join(canonical_json_bytes(row) for row in sorted(rows_for_symbol, key=lambda row: row["post_id"]))
            normalized_key = f"normalized/{run_id}/{quote(symbol, safe='')}.jsonl"
            normalized_result = store.put_if_absent(normalized_key, normalized_bytes, "application/jsonl")
            record["normalized_key"] = normalized_key
            record["normalized_sha256"] = normalized_result.sha256
            normalized_rows.extend(rows_for_symbol)
            dates = [row["source_created_at_raw"] for row in rows_for_symbol]
            record["source_created_at_min"] = min(dates)
            record["source_created_at_max"] = max(dates)
        quota_current = QuotaSnapshot.from_headers(response.headers, quota_current) or quota_current
        request_records.append(record)

    status = "DATA_READY" if request_records and all(record.get("response_classification") == "OK" for record in request_records) and len(request_records) == len(planned) else "PARTIAL_FAILURE"
    manifest = {
        "schema_version": "stockbit_stream_capture_manifest_v1",
        "status": status,
        "run_id": run_id,
        "capture_date": capture_date,
        "slot": slot,
        "endpoint": STREAM_ENDPOINT,
        "request_count": STREAM_COUNT,
        "planned_calls": len(planned),
        "completed_calls": len(request_records),
        "successful_responses": sum(record.get("response_classification") == "OK" for record in request_records),
        "normalized_post_rows": len(normalized_rows),
        "universe_sha256": universe_sha,
        "quota_before": quota_before.__dict__,
        "quota_after": quota_current.__dict__,
        "monthly_reserve": monthly_reserve,
        "requests": request_records,
        "privacy": {"raw_content_external_private_only": True, "author_identity_raw_persisted": False, "hmac_version": "HMAC_SHA256_SALT_V1"},
        "provider_calls": True,
        "outcome_accessed": False,
        "model_accessed": False,
        "counter_mutated": False,
        "storage_verification": {"immutable_put_and_readback": True},
    }
    result = store.put_if_absent(manifest_key, canonical_json_bytes(manifest), "application/json")
    manifest["manifest_sha256"] = result.sha256
    return manifest
