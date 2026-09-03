from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Protocol
import zipfile

FORBIDDEN_SNAPSHOT_PARTS = {
    ".env", "credentials", "secrets", "tokens", "outcomes",
    "outcome_vault", "realized_outcomes",
}


class IntradayCloudStorageError(RuntimeError):
    pass


class CloudObjectStore(Protocol):
    def read(self, key: str) -> bytes | None: ...
    def put_if_absent(self, key: str, payload: bytes, content_type: str) -> PutResult: ...
    def list_keys(self, prefix: str) -> list[str]: ...


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _raw_parts(value: str) -> list[str]:
    return value.replace("\\", "/").split("/") if value else []


def _safe_key(key: str) -> str:
    value = str(key).replace("\\", "/")
    path = PurePosixPath(value)
    if (
        not value
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in _raw_parts(value))
    ):
        raise IntradayCloudStorageError("STOCKBIT_INTRADAY_CLOUD_KEY_UNSAFE")
    return value


def _safe_relative(value: object, *, label: str) -> str:
    raw = str(value or "").replace("\\", "/")
    path = PurePosixPath(raw)
    if (
        not raw
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in _raw_parts(raw))
    ):
        raise IntradayCloudStorageError(f"{label}_PATH_INVALID")
    return raw


class LocalConditionalStore:
    """Atomic create-only local store used by unit/integration tests."""

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()

    def _path(self, key: str) -> Path:
        safe = _safe_key(key)
        return self.root.joinpath(*safe.split("/"))

    def read(self, key: str) -> bytes | None:
        path = self._path(key)
        try:
            return path.read_bytes()
        except FileNotFoundError:
            return None

    def put_if_absent(self, key: str, payload: bytes, content_type: str) -> PutResult:
        # Keep the read-only completion probe free of the Stream provider
        # dependency. Write paths retain the existing shared exception/result
        # types without importing Stream during module import.
        from .stockbit_stream_archive import PutResult, StorageImmutabilityConflict

        del content_type
        path = self._path(key)
        digest = sha256_bytes(payload)
        path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        flags |= getattr(os, "O_BINARY", 0)
        try:
            fd = os.open(path, flags)
        except FileExistsError:
            existing = self.read(key)
            if existing is None or sha256_bytes(existing) != digest:
                raise StorageImmutabilityConflict(f"immutable intraday cloud key changed: {key}")
            return PutResult(key, digest, False)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return PutResult(key, digest, True)

    def list_keys(self, prefix: str) -> list[str]:
        safe_prefix = str(prefix).replace("\\", "/")
        if safe_prefix and any(part in {"", ".", ".."} for part in _raw_parts(safe_prefix.rstrip("/"))):
            raise IntradayCloudStorageError("STOCKBIT_INTRADAY_CLOUD_PREFIX_UNSAFE")
        if safe_prefix.startswith("/"):
            raise IntradayCloudStorageError("STOCKBIT_INTRADAY_CLOUD_PREFIX_UNSAFE")
        if not self.root.exists():
            return []
        result: list[str] = []
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue
            key = path.relative_to(self.root).as_posix()
            if key.startswith(safe_prefix):
                result.append(key)
        return sorted(result)


class ConditionalS3Store:
    """R2/S3 store requiring create-only If-None-Match semantics."""

    def __init__(self, endpoint_url: str, bucket: str, access_key_id: str, secret_access_key: str, prefix: str = ""):
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - deployment only
            from .stockbit_stream_archive import StorageConfigurationError

            raise StorageConfigurationError("boto3 is required for Stockbit Intraday cloud storage") from exc
        if not endpoint_url or not bucket or not access_key_id or not secret_access_key:
            from .stockbit_stream_archive import StorageConfigurationError

            raise StorageConfigurationError("Stockbit Intraday cloud storage credentials are incomplete")
        self.bucket = bucket
        self.prefix = str(prefix).strip("/")
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
        from .stockbit_stream_archive import StorageArchiveError

        try:
            response = self.client.get_object(Bucket=self.bucket, Key=self._key(key))
        except Exception as exc:
            error = getattr(exc, "response", {}) or {}
            code = str(error.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey", "NoSuchObject", "NotFound"}:
                return None
            raise StorageArchiveError(f"Stockbit Intraday cloud read failed: {key}") from exc
        return response["Body"].read()

    def put_if_absent(self, key: str, payload: bytes, content_type: str) -> PutResult:
        from .stockbit_stream_archive import PutResult, StorageImmutabilityConflict

        digest = sha256_bytes(payload)
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=self._key(key),
                Body=payload,
                ContentType=content_type,
                IfNoneMatch="*",
            )
        except Exception as exc:
            error = getattr(exc, "response", {}) or {}
            code = str(error.get("Error", {}).get("Code", ""))
            status = str(error.get("ResponseMetadata", {}).get("HTTPStatusCode", ""))
            if code not in {"PreconditionFailed", "412", "ConditionalRequestConflict"} and status != "412":
                raise IntradayCloudStorageError("STOCKBIT_INTRADAY_CONDITIONAL_WRITE_UNAVAILABLE") from exc
            existing = self.read(key)
            if existing is None or sha256_bytes(existing) != digest:
                raise StorageImmutabilityConflict(f"immutable intraday cloud key changed: {key}")
            return PutResult(key, digest, False)
        confirmed = self.read(key)
        if confirmed is None or sha256_bytes(confirmed) != digest:
            raise IntradayCloudStorageError("STOCKBIT_INTRADAY_CLOUD_WRITE_VERIFICATION_FAILED")
        return PutResult(key, digest, True)

    def list_keys(self, prefix: str) -> list[str]:
        safe_prefix = str(prefix).strip("/")
        if safe_prefix:
            _safe_key(safe_prefix)
        result: list[str] = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=self._key(safe_prefix) if safe_prefix else f"{self.prefix}/"):
            for item in page.get("Contents") or []:
                key = str(item.get("Key") or "")
                prefix_text = f"{self.prefix}/" if self.prefix else ""
                if prefix_text and key.startswith(prefix_text):
                    key = key[len(prefix_text):]
                if key.startswith(safe_prefix):
                    result.append(key)
        return sorted(set(result))


def _blocked_snapshot_path(path: str) -> bool:
    parts = {part.lower() for part in PurePosixPath(path).parts}
    return bool(parts & FORBIDDEN_SNAPSHOT_PARTS) or any(
        part.lower().endswith((".pem", ".key")) for part in PurePosixPath(path).parts
    )


def build_runtime_snapshot(roots: Mapping[str, str | Path]) -> tuple[bytes, str, dict[str, Any]]:
    if not roots:
        raise IntradayCloudStorageError("STOCKBIT_INTRADAY_SNAPSHOT_ROOTS_EMPTY")
    names: set[str] = set()
    entries: list[tuple[str, bytes]] = []
    for name, raw_root in sorted(roots.items()):
        root_name = _safe_relative(name, label="STOCKBIT_INTRADAY_SNAPSHOT_ROOT")
        root = Path(raw_root).expanduser().resolve()
        if not root.exists():
            continue
        if not root.is_dir():
            raise IntradayCloudStorageError("STOCKBIT_INTRADAY_SNAPSHOT_ROOT_NOT_DIRECTORY")
        for path in sorted(root.rglob("*"), key=lambda value: value.as_posix()):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(root).as_posix()
            archive_name = f"{root_name}/{relative}"
            if _blocked_snapshot_path(archive_name):
                raise IntradayCloudStorageError("STOCKBIT_INTRADAY_SNAPSHOT_FORBIDDEN_PATH")
            if archive_name in names:
                raise IntradayCloudStorageError("STOCKBIT_INTRADAY_SNAPSHOT_PATH_COLLISION")
            names.add(archive_name)
            entries.append((archive_name, path.read_bytes()))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for archive_name, payload in sorted(entries):
            info = zipfile.ZipInfo(archive_name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, payload)
    encoded = buffer.getvalue()
    metadata = {
        "roots": sorted(str(key) for key in roots),
        "file_count": len(entries),
        "snapshot_sha256": sha256_bytes(encoded),
    }
    return encoded, metadata["snapshot_sha256"], metadata


def restore_runtime_snapshot(
    payload: bytes,
    roots: Mapping[str, str | Path],
    *,
    expected_sha256: str,
) -> dict[str, int]:
    actual = sha256_bytes(payload)
    if actual != str(expected_sha256).strip().lower():
        raise IntradayCloudStorageError("STOCKBIT_INTRADAY_SNAPSHOT_SHA_MISMATCH")
    resolved_roots = {str(name): Path(value).expanduser().resolve() for name, value in roots.items()}
    counts = {name: 0 for name in resolved_roots}
    seen_entries: set[str] = set()
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload), "r")
    except zipfile.BadZipFile as exc:
        raise IntradayCloudStorageError("STOCKBIT_INTRADAY_SNAPSHOT_ZIP_INVALID") from exc
    with archive:
        for info in archive.infolist():
            name = _safe_relative(info.filename, label="STOCKBIT_INTRADAY_SNAPSHOT_ENTRY")
            if name in seen_entries:
                raise IntradayCloudStorageError("STOCKBIT_INTRADAY_SNAPSHOT_DUPLICATE_ENTRY")
            seen_entries.add(name)
            if info.is_dir() or _blocked_snapshot_path(name):
                raise IntradayCloudStorageError("STOCKBIT_INTRADAY_SNAPSHOT_ENTRY_INVALID")
            root_name, _, relative = name.partition("/")
            if root_name not in resolved_roots or not relative:
                raise IntradayCloudStorageError("STOCKBIT_INTRADAY_SNAPSHOT_ROOT_UNKNOWN")
            relative_safe = _safe_relative(relative, label="STOCKBIT_INTRADAY_SNAPSHOT_ENTRY")
            target = (resolved_roots[root_name] / Path(relative_safe)).resolve()
            if resolved_roots[root_name] not in target.parents:
                raise IntradayCloudStorageError("STOCKBIT_INTRADAY_SNAPSHOT_ESCAPE")
            raw = archive.read(info)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                if not target.is_file() or target.read_bytes() != raw:
                    raise IntradayCloudStorageError("STOCKBIT_INTRADAY_SNAPSHOT_LOCAL_COLLISION")
            else:
                target.write_bytes(raw)
            counts[root_name] += 1
    return counts
