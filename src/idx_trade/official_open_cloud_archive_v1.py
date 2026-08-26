"""Cloud archival layer for certified Official Open evidence.

This module is intentionally evidence-only. It captures the already-frozen
Official Open source contract, archives the resulting certified artifacts to an
immutable store, and records timing provenance. It does not read model state,
orders, PaperState, outcomes, or forward counters, and cloud evidence is never
execution-admitted by this module.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Callable, Mapping

from .official_open_evidence_v1 import (
    AUTHORITY,
    FIELD_SEMANTICS,
    JAKARTA,
    TRANSPORT_POLICY,
    UPSTREAM_PATH,
    capture_official_open_with_transport_fallback,
)
from .stockbit_stream_archive import (
    ImmutableStore,
    LocalImmutableStore,
    S3ImmutableStore,
    StorageConfigurationError,
    canonical_json_bytes,
    sha256_bytes,
)


SCHEMA_VERSION = "idx_official_open_cloud_archive_v1"
EXECUTION_ADMISSION = "CAPTURE_ONLY_NOT_EXECUTION_ADMITTED"
DEFAULT_STORAGE_PREFIX = "official-open-v1"
SLOT_TIMES = {
    "0902": time(9, 2),
    "0912": time(9, 12),
    "0922": time(9, 22),
}


class OfficialOpenCloudArchiveError(RuntimeError):
    """Fail-closed cloud archive contract error."""


CaptureFunction = Callable[..., Path]


def _session(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise OfficialOpenCloudArchiveError("OFFICIAL_OPEN_CLOUD_SESSION_INVALID") from exc


def _slot(value: str) -> str:
    slot = str(value).strip()
    if slot not in SLOT_TIMES:
        raise OfficialOpenCloudArchiveError(f"OFFICIAL_OPEN_CLOUD_SLOT_INVALID:{slot}")
    return slot


def _json_object(payload: bytes, *, label: str) -> dict[str, object]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OfficialOpenCloudArchiveError(f"{label}_JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise OfficialOpenCloudArchiveError(f"{label}_NOT_OBJECT")
    return value


def _safe_artifact_path(folder: Path, name: object, *, label: str) -> Path:
    text = str(name or "")
    candidate = Path(text)
    if not text or candidate.name != text or candidate.is_absolute():
        raise OfficialOpenCloudArchiveError(f"{label}_PATH_INVALID")
    path = folder / candidate
    if not path.is_file():
        raise OfficialOpenCloudArchiveError(f"{label}_MISSING")
    return path


def _verify_source_bundle(manifest_path: Path, *, expected_session: str) -> dict[str, object]:
    source_manifest_bytes = manifest_path.read_bytes()
    manifest = _json_object(source_manifest_bytes, label="OFFICIAL_OPEN_SOURCE_MANIFEST")
    expected = {
        "session_date": expected_session,
        "authority": AUTHORITY,
        "upstream_path": UPSTREAM_PATH,
        "field_semantics": FIELD_SEMANTICS,
        "transport_policy": TRANSPORT_POLICY,
        "execution_grade": True,
    }
    for field, value in expected.items():
        if manifest.get(field) != value:
            raise OfficialOpenCloudArchiveError(
                f"OFFICIAL_OPEN_SOURCE_MANIFEST_CONTRACT_MISMATCH:{field}"
            )

    folder = manifest_path.parent
    raw_path = _safe_artifact_path(
        folder, manifest.get("raw_artifact_path"), label="OFFICIAL_OPEN_SOURCE_RAW"
    )
    normalized_path = _safe_artifact_path(
        folder,
        manifest.get("normalized_artifact_path"),
        label="OFFICIAL_OPEN_SOURCE_NORMALIZED",
    )
    raw_bytes = raw_path.read_bytes()
    normalized_bytes = normalized_path.read_bytes()
    raw_sha = sha256_bytes(raw_bytes)
    normalized_sha = sha256_bytes(normalized_bytes)
    if raw_sha != manifest.get("raw_artifact_sha256"):
        raise OfficialOpenCloudArchiveError("OFFICIAL_OPEN_SOURCE_RAW_SHA_MISMATCH")
    if normalized_sha != manifest.get("normalized_artifact_sha256"):
        raise OfficialOpenCloudArchiveError("OFFICIAL_OPEN_SOURCE_NORMALIZED_SHA_MISMATCH")

    capture_timestamp = str(manifest.get("capture_timestamp_jakarta") or "")
    try:
        captured = datetime.fromisoformat(capture_timestamp)
    except ValueError as exc:
        raise OfficialOpenCloudArchiveError(
            "OFFICIAL_OPEN_SOURCE_CAPTURE_TIMESTAMP_INVALID"
        ) from exc
    if captured.tzinfo is None:
        raise OfficialOpenCloudArchiveError(
            "OFFICIAL_OPEN_SOURCE_CAPTURE_TIMESTAMP_NAIVE"
        )

    return {
        "manifest": manifest,
        "manifest_bytes": source_manifest_bytes,
        "manifest_sha256": sha256_bytes(source_manifest_bytes),
        "raw_bytes": raw_bytes,
        "raw_sha256": raw_sha,
        "normalized_bytes": normalized_bytes,
        "normalized_sha256": normalized_sha,
        "captured_at": captured.astimezone(JAKARTA),
    }


def build_official_open_store_from_env(
    env: Mapping[str, str] | None = None,
) -> ImmutableStore:
    """Build local test storage or private S3/R2 storage from dedicated env vars."""

    values = os.environ if env is None else env
    backend = str(values.get("OFFICIAL_OPEN_STORAGE_BACKEND", "s3")).strip().lower()
    if backend == "local":
        root = str(values.get("OFFICIAL_OPEN_LOCAL_ROOT", "")).strip()
        if not root:
            raise StorageConfigurationError(
                "OFFICIAL_OPEN_LOCAL_ROOT is required for local storage"
            )
        return LocalImmutableStore(Path(root))
    if backend != "s3":
        raise StorageConfigurationError(
            f"unsupported Official Open storage backend: {backend}"
        )
    return S3ImmutableStore(
        str(values.get("OFFICIAL_OPEN_S3_ENDPOINT", "")),
        str(values.get("OFFICIAL_OPEN_S3_BUCKET", "")),
        str(values.get("OFFICIAL_OPEN_S3_ACCESS_KEY_ID", "")),
        str(values.get("OFFICIAL_OPEN_S3_SECRET_ACCESS_KEY", "")),
        str(values.get("OFFICIAL_OPEN_STORAGE_PREFIX", DEFAULT_STORAGE_PREFIX)),
    )


def _existing_commit(
    store: ImmutableStore, *, session: str, slot: str
) -> dict[str, object] | None:
    key = f"session_date={session}/slot={slot}/slot_manifest.json"
    payload = store.read(key)
    if payload is None:
        return None
    manifest = _json_object(payload, label="OFFICIAL_OPEN_CLOUD_COMMIT")
    expected = {
        "schema_version": SCHEMA_VERSION,
        "commit_state": "COMMITTED",
        "session_date": session,
        "slot": slot,
        "execution_admission": EXECUTION_ADMISSION,
    }
    for field, value in expected.items():
        if manifest.get(field) != value:
            raise OfficialOpenCloudArchiveError(
                f"OFFICIAL_OPEN_CLOUD_COMMIT_CONTRACT_MISMATCH:{field}"
            )
    return manifest


def capture_and_archive_official_open(
    *,
    session_date: str,
    slot: str,
    store: ImmutableStore,
    zapi_api_key: str | None,
    timeout_seconds: float = 30.0,
    capture_fn: CaptureFunction = capture_official_open_with_transport_fallback,
    runner_provenance: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Capture one slot and commit its certified evidence bundle immutably.

    The deterministic slot commit marker is checked before any provider call.
    Artifact payloads live under a unique capture prefix and the slot manifest is
    written last, so incomplete uploads never become committed slot evidence.
    """

    session = _session(session_date)
    slot_name = _slot(slot)
    existing = _existing_commit(store, session=session, slot=slot_name)
    if existing is not None:
        return {
            "status": "ALREADY_CAPTURED",
            "session_date": session,
            "slot": slot_name,
            "slot_manifest_sha256": sha256_bytes(
                store.read(
                    f"session_date={session}/slot={slot_name}/slot_manifest.json"
                )
                or b""
            ),
            "capture_id": existing.get("capture_id"),
            "source_transport": existing.get("source_transport"),
            "execution_admission": EXECUTION_ADMISSION,
        }

    with tempfile.TemporaryDirectory(prefix="idx-official-open-cloud-") as temp_root:
        source_manifest_path = capture_fn(
            session,
            output_root=Path(temp_root),
            zapi_api_key=zapi_api_key,
            timeout_seconds=timeout_seconds,
        )
        bundle = _verify_source_bundle(
            Path(source_manifest_path), expected_session=session
        )

        source_manifest = bundle["manifest"]
        captured_at = bundle["captured_at"]
        assert isinstance(captured_at, datetime)
        scheduled_at = datetime.combine(
            date.fromisoformat(session), SLOT_TIMES[slot_name], tzinfo=JAKARTA
        )
        capture_lag_seconds = (captured_at - scheduled_at).total_seconds()
        capture_id = (
            captured_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            + "-"
            + str(bundle["manifest_sha256"])[:16]
        )
        capture_root = (
            f"session_date={session}/slot={slot_name}/captures/{capture_id}"
        )

        artifact_specs = (
            (
                "raw_response",
                f"{capture_root}/raw_response.json",
                bundle["raw_bytes"],
                "application/json",
                bundle["raw_sha256"],
            ),
            (
                "open_prices",
                f"{capture_root}/open_prices.parquet",
                bundle["normalized_bytes"],
                "application/octet-stream",
                bundle["normalized_sha256"],
            ),
            (
                "source_manifest",
                f"{capture_root}/source_manifest.json",
                bundle["manifest_bytes"],
                "application/json",
                bundle["manifest_sha256"],
            ),
        )
        archived: dict[str, dict[str, object]] = {}
        for name, key, payload, content_type, expected_sha in artifact_specs:
            if not isinstance(payload, bytes):
                raise OfficialOpenCloudArchiveError(
                    f"OFFICIAL_OPEN_CLOUD_ARTIFACT_BYTES_INVALID:{name}"
                )
            result = store.put_if_absent(key, payload, content_type)
            if result.sha256 != expected_sha:
                raise OfficialOpenCloudArchiveError(
                    f"OFFICIAL_OPEN_CLOUD_ARCHIVE_SHA_MISMATCH:{name}"
                )
            archived[name] = {
                "key": key,
                "sha256": result.sha256,
                "created": result.created,
            }

        cloud_manifest: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "commit_state": "COMMITTED",
            "session_date": session,
            "slot": slot_name,
            "capture_id": capture_id,
            "scheduled_capture_timestamp_jakarta": scheduled_at.isoformat(),
            "source_capture_timestamp_jakarta": captured_at.isoformat(),
            "capture_lag_seconds": capture_lag_seconds,
            "authority": AUTHORITY,
            "upstream_path": UPSTREAM_PATH,
            "field_semantics": FIELD_SEMANTICS,
            "source_transport": source_manifest.get("transport"),
            "source_transport_policy": source_manifest.get("transport_policy"),
            "source_execution_grade": source_manifest.get("execution_grade"),
            "execution_admission": EXECUTION_ADMISSION,
            "artifacts": archived,
            "runner_provenance": dict(runner_provenance or {}),
            "guards": {
                "model_accessed": False,
                "outcome_accessed": False,
                "paper_state_mutated": False,
                "forward_counter_mutated": False,
                "order_created": False,
                "fill_created": False,
                "retroactive_execution_authorized": False,
            },
        }
        cloud_manifest_bytes = canonical_json_bytes(cloud_manifest)
        commit_key = f"session_date={session}/slot={slot_name}/slot_manifest.json"
        commit_result = store.put_if_absent(
            commit_key, cloud_manifest_bytes, "application/json"
        )
        if commit_result.sha256 != sha256_bytes(cloud_manifest_bytes):
            raise OfficialOpenCloudArchiveError(
                "OFFICIAL_OPEN_CLOUD_COMMIT_SHA_MISMATCH"
            )

    return {
        "status": "CAPTURED" if commit_result.created else "ALREADY_CAPTURED",
        "session_date": session,
        "slot": slot_name,
        "capture_id": capture_id,
        "capture_timestamp_jakarta": captured_at.isoformat(),
        "capture_lag_seconds": capture_lag_seconds,
        "source_transport": source_manifest.get("transport"),
        "source_manifest_sha256": bundle["manifest_sha256"],
        "slot_manifest_sha256": commit_result.sha256,
        "execution_admission": EXECUTION_ADMISSION,
    }


__all__ = [
    "DEFAULT_STORAGE_PREFIX",
    "EXECUTION_ADMISSION",
    "OfficialOpenCloudArchiveError",
    "SCHEMA_VERSION",
    "SLOT_TIMES",
    "build_official_open_store_from_env",
    "capture_and_archive_official_open",
]
