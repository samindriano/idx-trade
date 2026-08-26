from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import Any, Mapping

from .stockbit_intraday_cloud_storage import ConditionalS3Store, sha256_bytes
from .stockbit_stream_archive import StorageImmutabilityConflict


SMOKE_SCHEMA_VERSION = "idx_trade_stockbit_intraday_r2_smoke_v1"
SMOKE_ROOT_PREFIX = "stockbit-intraday-smoke-v1"
RESERVED_PRODUCTION_PREFIXES = (
    "stockbit-intraday-v1",
    "e2e-paper-v1",
    "official-open-v1",
    "stockbit-stream-v1",
    "stockbit-stream-v2",
)


class StockbitIntradayR2SmokeError(RuntimeError):
    pass


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def safe_smoke_prefix(value: object) -> str:
    prefix = str(value or "").strip().strip("/").replace("\\", "/")
    path = PurePosixPath(prefix)
    if not prefix or path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise StockbitIntradayR2SmokeError("STOCKBIT_INTRADAY_SMOKE_PREFIX_UNSAFE")
    if prefix == SMOKE_ROOT_PREFIX or not prefix.startswith(SMOKE_ROOT_PREFIX + "/"):
        raise StockbitIntradayR2SmokeError("STOCKBIT_INTRADAY_SMOKE_PREFIX_OUTSIDE_ROOT")
    run_id = prefix[len(SMOKE_ROOT_PREFIX) + 1 :]
    if not run_id or "/" in run_id:
        raise StockbitIntradayR2SmokeError("STOCKBIT_INTRADAY_SMOKE_RUN_ID_INVALID")
    if any(prefix == reserved or prefix.startswith(reserved + "/") for reserved in RESERVED_PRODUCTION_PREFIXES):
        raise StockbitIntradayR2SmokeError("STOCKBIT_INTRADAY_SMOKE_PREFIX_COLLIDES_WITH_PRODUCTION")
    return prefix


def _required_storage_env(values: Mapping[str, str]) -> tuple[str, str, str, str]:
    names = (
        "STOCKBIT_INTRADAY_S3_ENDPOINT",
        "STOCKBIT_INTRADAY_S3_BUCKET",
        "STOCKBIT_INTRADAY_S3_ACCESS_KEY_ID",
        "STOCKBIT_INTRADAY_S3_SECRET_ACCESS_KEY",
    )
    missing = [name for name in names if not str(values.get(name, "")).strip()]
    if missing:
        raise StockbitIntradayR2SmokeError(
            "STOCKBIT_INTRADAY_SMOKE_STORAGE_ENV_MISSING:" + ",".join(missing)
        )
    return tuple(str(values[name]).strip() for name in names)  # type: ignore[return-value]


def build_smoke_store(values: Mapping[str, str], *, prefix: str) -> ConditionalS3Store:
    endpoint, bucket, access_key, secret = _required_storage_env(values)
    return ConditionalS3Store(
        endpoint,
        bucket,
        access_key,
        secret,
        safe_smoke_prefix(prefix),
    )


def run_r2_smoke(
    *,
    values: Mapping[str, str],
    prefix: str,
    store: Any | None = None,
) -> dict[str, Any]:
    smoke_prefix = safe_smoke_prefix(prefix)
    target = store if store is not None else build_smoke_store(values, prefix=smoke_prefix)
    key = "conditional-write-probe.json"
    payload = _canonical_json_bytes(
        {
            "schema_version": SMOKE_SCHEMA_VERSION,
            "throwaway_prefix": smoke_prefix,
            "provider_calls": 0,
            "production_prefix_written": False,
            "outcome_accessed": False,
            "retroactive_capture_used": False,
            "synthetic_fill_used": False,
        }
    )
    digest = sha256_bytes(payload)

    first = target.put_if_absent(key, payload, "application/json")
    replay = target.put_if_absent(key, payload, "application/json")

    conflict_rejected = False
    try:
        target.put_if_absent(
            key,
            payload + b"conflicting-smoke-write\n",
            "application/json",
        )
    except StorageImmutabilityConflict:
        conflict_rejected = True

    readback = target.read(key)
    if (
        not first.created
        or replay.created
        or not conflict_rejected
        or readback is None
        or sha256_bytes(readback) != digest
    ):
        raise StockbitIntradayR2SmokeError("STOCKBIT_INTRADAY_R2_SMOKE_CONTRACT_FAILED")

    return {
        "status": "STOCKBIT_INTRADAY_R2_CONDITIONAL_SMOKE_PASS",
        "schema_version": SMOKE_SCHEMA_VERSION,
        "throwaway_prefix": smoke_prefix,
        "object_key": key,
        "sha256": digest,
        "first_write_created": first.created,
        "identical_replay_created": replay.created,
        "conflicting_write_rejected": conflict_rejected,
        "readback_sha256": sha256_bytes(readback),
        "provider_calls": 0,
        "production_prefix_written": False,
        "outcome_accessed": False,
        "retroactive_capture_used": False,
        "synthetic_fill_used": False,
    }
