"""Cloud-first durability and orchestration adapter for the existing E2E PAPER.

The existing E2E controller remains the scientific and PaperState authority.
This module supplies the missing cloud boundary only: immutable R2 objects,
hash-pinned input materialisation, deterministic runtime snapshots, and
stage commit records.  A stage is never considered committed until its
runtime snapshot and result are readable and hash-verified.

The production runner deliberately uses a fixed ephemeral filesystem layout.
Existing E2E payloads contain absolute paths, so a snapshot can only be
rehydrated safely when those paths are stable across GitHub-hosted jobs.  The
workflow contract sets these paths explicitly; no machine-local Windows path
is accepted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
from typing import Any, Iterable, Mapping, Protocol
import zipfile

from .official_trading_schedule_v1 import (
    OfficialTradingScheduleError,
    VerifiedOfficialTradingSchedule,
    load_verified_official_trading_schedule,
)
from .stockbit_stream_archive import (
    PutResult,
    StorageArchiveError,
    StorageConfigurationError,
    StorageImmutabilityConflict,
)


SCHEMA_VERSION = "idx_trade_e2e_paper_cloud_runtime_v1"
INPUT_SCHEMA_VERSION = "idx_trade_e2e_paper_cloud_inputs_v1"
SNAPSHOT_SCHEMA_VERSION = "idx_trade_e2e_paper_cloud_snapshot_v1"
STAGE_COMMIT_SCHEMA_VERSION = "idx_trade_e2e_paper_cloud_stage_commit_v1"
CONTRACT_VERSION = "CLOUD_FIRST_E2E_PAPER_V1"
UTC = timezone.utc
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
STAGE_NAMES = ("NOOP", "POST_EOD", "PREOPEN")
TERMINAL_STAGE_STATUSES = {
    "NOOP": {"WEEKEND_OR_HOLIDAY_NOOP"},
    "POST_EOD": {"POST_EOD_PREPARED", "MISSED_EXECUTION_NO_CERTIFIED_OPEN"},
    "PREOPEN": {"EXECUTION_COMPLETE", "ALREADY_COMPLETE", "MISSED_EXECUTION_NO_CERTIFIED_OPEN"},
}
REQUIRED_INPUT_ROLES = {
    "execution_schedule",
    "execution_schedule_source",
    "clean_panel",
    "clean_security_master",
    "model_manifest",
    "model_control_h5",
    "model_control_h10",
    "model_challenger_h5",
    "model_challenger_h10",
    "model_fit_log",
}
FORBIDDEN_SNAPSHOT_PARTS = {
    ".env",
    "credentials",
    "secrets",
    "tokens",
    "outcomes",
    "outcome_vault",
    "realized_outcomes",
}


class CloudPaperRuntimeError(RuntimeError):
    """Raised when the cloud runtime cannot prove safe continuation."""


class CloudObjectStore(Protocol):
    def read(self, key: str) -> bytes | None: ...

    def put_if_absent(self, key: str, payload: bytes, content_type: str) -> PutResult: ...


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _safe_key(key: str) -> str:
    value = str(key).replace("\\", "/")
    path = PurePosixPath(value)
    if not value or value.startswith("/") or ".." in path.parts:
        raise CloudPaperRuntimeError("CLOUD_OBJECT_KEY_UNSAFE")
    return str(path)


def _safe_relative(value: object, *, label: str) -> str:
    raw = str(value or "").replace("\\", "/")
    path = PurePosixPath(raw)
    if not raw or path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise CloudPaperRuntimeError(f"{label}_PATH_INVALID")
    return str(path)


def _required_sha(value: object, *, label: str) -> str:
    digest = str(value or "").strip().lower()
    if not SHA_RE.fullmatch(digest):
        raise CloudPaperRuntimeError(f"{label}_SHA_INVALID")
    return digest


def _required_git_sha(value: object, *, label: str) -> str:
    digest = str(value or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", digest):
        raise CloudPaperRuntimeError(f"{label}_GIT_SHA_INVALID")
    return digest


def _require_aware_timestamp(value: object, *, label: str) -> None:
    try:
        parsed = datetime.fromisoformat(str(value or ""))
    except ValueError as exc:
        raise CloudPaperRuntimeError(f"{label}_TIMESTAMP_INVALID") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CloudPaperRuntimeError(f"{label}_TIMESTAMP_NOT_TIMEZONE_AWARE")


def _json_object(payload: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CloudPaperRuntimeError(f"{label}_JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise CloudPaperRuntimeError(f"{label}_NOT_OBJECT")
    return value


class LocalConditionalStore:
    """Local test store with atomic create-only semantics."""

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
                raise StorageImmutabilityConflict(f"immutable cloud key changed: {key}")
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


class ConditionalS3Store:
    """S3/R2 store using create-only writes for cloud commit objects.

    R2 exposes the S3 conditional ``If-None-Match: *`` operation.  If the
    backend rejects conditional writes, the runtime fails closed rather than
    silently falling back to a racy read-then-write operation.
    """

    def __init__(
        self,
        endpoint_url: str,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        prefix: str = "",
    ):
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - deployment only
            raise StorageConfigurationError("boto3 is required for cloud E2E storage") from exc
        if not endpoint_url or not bucket or not access_key_id or not secret_access_key:
            raise StorageConfigurationError("cloud E2E storage credentials are incomplete")
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
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=self._key(key))
        except Exception as exc:
            error = getattr(exc, "response", {}) or {}
            code = str(error.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey", "NoSuchObject", "NotFound"}:
                return None
            raise StorageArchiveError(f"cloud E2E read failed: {key}") from exc
        return response["Body"].read()

    def put_if_absent(self, key: str, payload: bytes, content_type: str) -> PutResult:
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
                raise CloudPaperRuntimeError("CLOUD_CONDITIONAL_WRITE_UNAVAILABLE") from exc
            existing = self.read(key)
            if existing is None or sha256_bytes(existing) != digest:
                raise StorageImmutabilityConflict(f"immutable cloud key changed: {key}")
            return PutResult(key, digest, False)
        confirmed = self.read(key)
        if confirmed is None or sha256_bytes(confirmed) != digest:
            raise CloudPaperRuntimeError("CLOUD_WRITE_VERIFICATION_FAILED")
        return PutResult(key, digest, True)


def build_cloud_store_from_env(
    env: Mapping[str, str] | None = None,
    *,
    prefix_key: str = "E2E_CLOUD_STORAGE_PREFIX",
) -> CloudObjectStore:
    values = os.environ if env is None else env
    backend = str(values.get("E2E_CLOUD_STORAGE_BACKEND", "s3")).strip().lower()
    if backend == "local":
        root = str(values.get("E2E_CLOUD_LOCAL_ROOT", "")).strip()
        if not root:
            raise StorageConfigurationError("E2E_CLOUD_LOCAL_ROOT is required")
        return LocalConditionalStore(root)
    if backend != "s3":
        raise StorageConfigurationError(f"unsupported E2E cloud storage backend: {backend}")
    return ConditionalS3Store(
        str(values.get("E2E_CLOUD_S3_ENDPOINT", "")).strip(),
        str(values.get("E2E_CLOUD_S3_BUCKET", "")).strip(),
        str(values.get("E2E_CLOUD_S3_ACCESS_KEY_ID", "")).strip(),
        str(values.get("E2E_CLOUD_S3_SECRET_ACCESS_KEY", "")).strip(),
        str(values.get(prefix_key, "e2e-paper-v1")),
    )


@dataclass(frozen=True)
class CloudInputRef:
    role: str
    key: str
    relative_path: str
    sha256: str
    content_type: str


@dataclass(frozen=True)
class CloudInputBundle:
    manifest_key: str
    manifest_sha256: str
    roles: dict[str, Path]
    refs: tuple[CloudInputRef, ...]
    payload: dict[str, Any]

    @classmethod
    def load(cls, store: CloudObjectStore, manifest_key: str) -> "CloudInputBundle":
        key = _safe_key(manifest_key)
        raw = store.read(key)
        if raw is None:
            raise CloudPaperRuntimeError("CLOUD_INPUT_MANIFEST_MISSING")
        payload = _json_object(raw, label="CLOUD_INPUT_MANIFEST")
        if payload.get("schema_version") != INPUT_SCHEMA_VERSION:
            raise CloudPaperRuntimeError("CLOUD_INPUT_MANIFEST_SCHEMA_MISMATCH")
        if payload.get("contract_version") != CONTRACT_VERSION:
            raise CloudPaperRuntimeError("CLOUD_INPUT_MANIFEST_CONTRACT_MISMATCH")
        raw_refs = payload.get("files")
        raw_roles = payload.get("roles")
        if not isinstance(raw_refs, list) or not isinstance(raw_roles, dict):
            raise CloudPaperRuntimeError("CLOUD_INPUT_MANIFEST_STRUCTURE_INVALID")
        refs: list[CloudInputRef] = []
        seen_roles: set[str] = set()
        seen_paths: set[str] = set()
        for item in raw_refs:
            if not isinstance(item, dict):
                raise CloudPaperRuntimeError("CLOUD_INPUT_REF_INVALID")
            role = str(item.get("role") or "").strip()
            if not role or role in seen_roles:
                raise CloudPaperRuntimeError("CLOUD_INPUT_ROLE_DUPLICATE")
            relative = _safe_relative(item.get("relative_path"), label="CLOUD_INPUT")
            if relative in seen_paths:
                raise CloudPaperRuntimeError("CLOUD_INPUT_PATH_DUPLICATE")
            ref = CloudInputRef(
                role=role,
                key=_safe_key(str(item.get("key") or "")),
                relative_path=relative,
                sha256=_required_sha(item.get("sha256"), label="CLOUD_INPUT"),
                content_type=str(item.get("content_type") or "application/octet-stream"),
            )
            refs.append(ref)
            seen_roles.add(role)
            seen_paths.add(relative)
        missing_roles = REQUIRED_INPUT_ROLES - set(seen_roles)
        if missing_roles:
            raise CloudPaperRuntimeError(
                "CLOUD_INPUT_REQUIRED_ROLE_MISSING:" + ",".join(sorted(missing_roles))
            )
        role_paths: dict[str, Path] = {}
        for role, raw_path in raw_roles.items():
            role_name = str(role).strip()
            path_text = _safe_relative(raw_path, label="CLOUD_INPUT_ROLE")
            if role_name not in seen_roles:
                raise CloudPaperRuntimeError("CLOUD_INPUT_ROLE_NOT_DECLARED")
            role_paths[role_name] = Path(path_text)
        for required in REQUIRED_INPUT_ROLES:
            if required not in role_paths:
                raise CloudPaperRuntimeError("CLOUD_INPUT_ROLE_PATH_MISSING:" + required)
        expected_payload_sha = payload.get("manifest_payload_sha256")
        if expected_payload_sha is not None:
            declared = _required_sha(expected_payload_sha, label="CLOUD_INPUT_PAYLOAD")
            body = dict(payload)
            body.pop("manifest_payload_sha256", None)
            if sha256_bytes(canonical_json_bytes(body)) != declared:
                raise CloudPaperRuntimeError("CLOUD_INPUT_MANIFEST_PAYLOAD_SHA_MISMATCH")
        return cls(key, sha256_bytes(raw), role_paths, tuple(refs), payload)

    def materialize(self, store: CloudObjectStore, root: str | Path) -> dict[str, Path]:
        destination = Path(root).expanduser().resolve()
        destination.mkdir(parents=True, exist_ok=True)
        by_role = {ref.role: ref for ref in self.refs}
        output: dict[str, Path] = {}
        for ref in self.refs:
            raw = store.read(ref.key)
            if raw is None or sha256_bytes(raw) != ref.sha256:
                raise CloudPaperRuntimeError("CLOUD_INPUT_ARTIFACT_SHA_MISMATCH:" + ref.role)
            path = destination / Path(ref.relative_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                if not path.is_file() or sha256_bytes(path.read_bytes()) != ref.sha256:
                    raise CloudPaperRuntimeError("CLOUD_INPUT_LOCAL_COLLISION:" + ref.role)
            else:
                path.write_bytes(raw)
            output[ref.role] = path
        for role, relative in self.roles.items():
            if role not in by_role:
                raise CloudPaperRuntimeError("CLOUD_INPUT_ROLE_REF_MISSING:" + role)
            expected = (destination / relative).resolve()
            if expected != (destination / by_role[role].relative_path).resolve():
                raise CloudPaperRuntimeError("CLOUD_INPUT_ROLE_PATH_MISMATCH:" + role)
        return output


def _blocked_snapshot_path(path: str) -> bool:
    parts = {part.lower() for part in PurePosixPath(path).parts}
    return bool(parts & FORBIDDEN_SNAPSHOT_PARTS) or any(
        part.lower().endswith(('.pem', '.key')) for part in PurePosixPath(path).parts
    )


def build_runtime_snapshot(roots: Mapping[str, str | Path]) -> tuple[bytes, str, dict[str, Any]]:
    """Build a deterministic ZIP snapshot from named runtime roots."""

    if not roots:
        raise CloudPaperRuntimeError("CLOUD_RUNTIME_SNAPSHOT_ROOTS_EMPTY")
    names: set[str] = set()
    entries: list[tuple[str, bytes]] = []
    for name, raw_root in sorted(roots.items()):
        root_name = _safe_relative(name, label="CLOUD_SNAPSHOT_ROOT")
        root = Path(raw_root).expanduser().resolve()
        if not root.exists():
            continue
        if not root.is_dir():
            raise CloudPaperRuntimeError("CLOUD_RUNTIME_SNAPSHOT_ROOT_NOT_DIRECTORY:" + name)
        for path in sorted(root.rglob("*"), key=lambda value: value.as_posix()):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(root).as_posix()
            archive_name = f"{root_name}/{relative}"
            if _blocked_snapshot_path(archive_name):
                raise CloudPaperRuntimeError("CLOUD_RUNTIME_SNAPSHOT_FORBIDDEN_PATH:" + archive_name)
            if archive_name in names:
                raise CloudPaperRuntimeError("CLOUD_RUNTIME_SNAPSHOT_PATH_COLLISION:" + archive_name)
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
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
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
    if actual != _required_sha(expected_sha256, label="CLOUD_SNAPSHOT"):
        raise CloudPaperRuntimeError("CLOUD_RUNTIME_SNAPSHOT_SHA_MISMATCH")
    resolved_roots = {str(name): Path(value).expanduser().resolve() for name, value in roots.items()}
    counts = {name: 0 for name in resolved_roots}
    seen_entries: set[str] = set()
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload), "r")
    except zipfile.BadZipFile as exc:
        raise CloudPaperRuntimeError("CLOUD_RUNTIME_SNAPSHOT_ZIP_INVALID") from exc
    with archive:
        for info in archive.infolist():
            name = _safe_relative(info.filename, label="CLOUD_SNAPSHOT_ENTRY")
            if name in seen_entries:
                raise CloudPaperRuntimeError("CLOUD_RUNTIME_SNAPSHOT_DUPLICATE_ENTRY")
            seen_entries.add(name)
            if info.is_dir() or _blocked_snapshot_path(name):
                raise CloudPaperRuntimeError("CLOUD_RUNTIME_SNAPSHOT_ENTRY_INVALID")
            root_name, _, relative = name.partition("/")
            if root_name not in resolved_roots or not relative:
                raise CloudPaperRuntimeError("CLOUD_RUNTIME_SNAPSHOT_ROOT_UNKNOWN")
            relative_safe = _safe_relative(relative, label="CLOUD_SNAPSHOT_ENTRY")
            target = (resolved_roots[root_name] / Path(relative_safe)).resolve()
            if resolved_roots[root_name] not in target.parents:
                raise CloudPaperRuntimeError("CLOUD_RUNTIME_SNAPSHOT_ESCAPE")
            raw = archive.read(info)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                if not target.is_file() or target.read_bytes() != raw:
                    raise CloudPaperRuntimeError("CLOUD_RUNTIME_SNAPSHOT_LOCAL_COLLISION")
            else:
                target.write_bytes(raw)
            counts[root_name] += 1
    return counts


@dataclass(frozen=True)
class CloudStageCommit:
    session_date: str
    stage: str
    status: str
    commit_key: str
    commit_sha256: str
    snapshot_key: str | None
    snapshot_sha256: str | None
    result_key: str
    result_sha256: str
    payload: dict[str, Any]


class CloudPaperArchive:
    """Known-key cloud archive for one canonical E2E Paper transaction."""

    def __init__(self, store: CloudObjectStore):
        self.store = store

    @staticmethod
    def commit_key(session_date: str, stage: str) -> str:
        return f"sessions/{date.fromisoformat(session_date).isoformat()}/stages/{stage}/commit.json"

    @staticmethod
    def attempt_key(session_date: str, stage: str, run_id: str) -> str:
        return f"sessions/{date.fromisoformat(session_date).isoformat()}/stages/{stage}/attempts/{_safe_key(run_id)}.json"

    def _load_commit(self, session_date: str, stage: str) -> CloudStageCommit | None:
        key = self.commit_key(session_date, stage)
        raw = self.store.read(key)
        if raw is None:
            return None
        payload = _json_object(raw, label="CLOUD_STAGE_COMMIT")
        if payload.get("schema_version") != STAGE_COMMIT_SCHEMA_VERSION:
            raise CloudPaperRuntimeError("CLOUD_STAGE_COMMIT_SCHEMA_MISMATCH")
        if payload.get("commit_state") != "COMMITTED":
            raise CloudPaperRuntimeError("CLOUD_STAGE_COMMIT_NOT_COMMITTED")
        if payload.get("contract_version") != CONTRACT_VERSION:
            raise CloudPaperRuntimeError("CLOUD_STAGE_COMMIT_CONTRACT_MISMATCH")
        if payload.get("session_date") != session_date or payload.get("stage") != stage:
            raise CloudPaperRuntimeError("CLOUD_STAGE_COMMIT_IDENTITY_MISMATCH")
        stage_status = str(payload.get("stage_status") or "")
        if stage_status not in TERMINAL_STAGE_STATUSES[stage]:
            raise CloudPaperRuntimeError("CLOUD_STAGE_COMMIT_STATUS_INVALID")
        _required_sha(
            payload.get("schedule_attestation_sha256"),
            label="CLOUD_STAGE_COMMIT_SCHEDULE",
        )
        _required_sha(payload.get("input_manifest_sha256"), label="CLOUD_STAGE_COMMIT_INPUT")
        code_identity = payload.get("code_identity")
        if not isinstance(code_identity, dict):
            raise CloudPaperRuntimeError("CLOUD_STAGE_COMMIT_CODE_IDENTITY_INVALID")
        _required_git_sha(code_identity.get("commit"), label="CLOUD_STAGE_COMMIT")
        commit_sha = sha256_bytes(raw)
        snapshot = payload.get("snapshot")
        result = payload.get("result")
        if not isinstance(result, dict) or not result.get("key") or not result.get("sha256"):
            raise CloudPaperRuntimeError("CLOUD_STAGE_COMMIT_RESULT_REF_MISSING")
        result_key = _safe_key(str(result["key"]))
        result_sha = _required_sha(result["sha256"], label="CLOUD_STAGE_COMMIT_RESULT")
        result_raw = self.store.read(result_key)
        if result_raw is None or sha256_bytes(result_raw) != result_sha:
            raise CloudPaperRuntimeError("CLOUD_STAGE_COMMIT_RESULT_INVALID")
        result_payload = _json_object(result_raw, label="CLOUD_STAGE_RESULT")
        if (
            result_payload.get("schema_version") != SCHEMA_VERSION
            or result_payload.get("session_date") != session_date
            or result_payload.get("stage") != stage
            or result_payload.get("stage_status") != stage_status
            or result_payload.get("observed_availability_only") is not True
            or result_payload.get("outcome_accessed") is not False
            or result_payload.get("protected_forward_accessed") is not False
            or result_payload.get("model_refit") is not False
        ):
            raise CloudPaperRuntimeError("CLOUD_STAGE_RESULT_GUARDS_INVALID")
        _require_aware_timestamp(
            result_payload.get("observed_started_at_utc"),
            label="CLOUD_STAGE_RESULT_STARTED",
        )
        _require_aware_timestamp(
            result_payload.get("observed_finished_at_utc"),
            label="CLOUD_STAGE_RESULT_FINISHED",
        )
        snapshot_key: str | None = None
        snapshot_sha: str | None = None
        if not isinstance(snapshot, dict) or not snapshot.get("key") or not snapshot.get("sha256"):
            raise CloudPaperRuntimeError("CLOUD_STAGE_COMMIT_SNAPSHOT_REF_INVALID")
        snapshot_key = _safe_key(str(snapshot["key"]))
        snapshot_sha = _required_sha(snapshot["sha256"], label="CLOUD_STAGE_COMMIT_SNAPSHOT")
        snapshot_raw = self.store.read(snapshot_key)
        if snapshot_raw is None or sha256_bytes(snapshot_raw) != snapshot_sha:
            raise CloudPaperRuntimeError("CLOUD_STAGE_COMMIT_SNAPSHOT_INVALID")
        guards = payload.get("guards")
        if (
            not isinstance(guards, dict)
            or guards.get("outcome_accessed") is not False
            or guards.get("protected_forward_accessed") is not False
            or guards.get("model_refit") is not False
            or guards.get("retroactive_execution_authorized") is not False
        ):
            raise CloudPaperRuntimeError("CLOUD_STAGE_COMMIT_GUARDS_INVALID")
        return CloudStageCommit(
            session_date=session_date,
            stage=stage,
            status=stage_status,
            commit_key=key,
            commit_sha256=commit_sha,
            snapshot_key=snapshot_key,
            snapshot_sha256=snapshot_sha,
            result_key=result_key,
            result_sha256=result_sha,
            payload=payload,
        )

    @staticmethod
    def verify_existing_identity(
        commit: CloudStageCommit,
        *,
        schedule_attestation_sha256: str,
        input_manifest_sha256: str,
    ) -> None:
        expected_schedule = _required_sha(
            schedule_attestation_sha256, label="CLOUD_STAGE_EXPECTED_SCHEDULE"
        )
        expected_input = _required_sha(
            input_manifest_sha256, label="CLOUD_STAGE_EXPECTED_INPUT"
        )
        if commit.payload.get("schedule_attestation_sha256") != expected_schedule:
            raise CloudPaperRuntimeError("CLOUD_STAGE_EXISTING_SCHEDULE_IDENTITY_CONFLICT")
        if commit.payload.get("input_manifest_sha256") != expected_input:
            raise CloudPaperRuntimeError("CLOUD_STAGE_EXISTING_INPUT_IDENTITY_CONFLICT")

    def existing_commit(self, session_date: str, stage: str) -> CloudStageCommit | None:
        if stage not in STAGE_NAMES:
            raise CloudPaperRuntimeError("CLOUD_STAGE_INVALID")
        return self._load_commit(date.fromisoformat(session_date).isoformat(), stage)

    def record_attempt(self, *, session_date: str, stage: str, run_id: str, payload: Mapping[str, Any]) -> str:
        body = {
            "schema_version": SCHEMA_VERSION,
            "session_date": date.fromisoformat(session_date).isoformat(),
            "stage": stage,
            "run_id": _safe_key(run_id),
            "recorded_at_utc": datetime.now(UTC).isoformat(),
            **dict(payload),
        }
        encoded = canonical_json_bytes(body)
        result = self.store.put_if_absent(
            self.attempt_key(session_date, stage, run_id), encoded, "application/json"
        )
        if result.sha256 != sha256_bytes(encoded):
            raise CloudPaperRuntimeError("CLOUD_ATTEMPT_SHA_MISMATCH")
        return result.sha256

    def commit_stage(
        self,
        *,
        session_date: str,
        stage: str,
        status: str,
        run_id: str,
        snapshot_bytes: bytes,
        snapshot_sha256: str,
        snapshot_metadata: Mapping[str, Any],
        result_payload: Mapping[str, Any],
        schedule_attestation_sha256: str,
        input_manifest_sha256: str,
        code_identity: Mapping[str, Any],
    ) -> CloudStageCommit:
        session = date.fromisoformat(session_date).isoformat()
        if stage not in STAGE_NAMES:
            raise CloudPaperRuntimeError("CLOUD_STAGE_INVALID")
        if status not in TERMINAL_STAGE_STATUSES[stage]:
            raise CloudPaperRuntimeError("CLOUD_STAGE_STATUS_NOT_TERMINAL")
        snapshot_sha = _required_sha(snapshot_sha256, label="CLOUD_STAGE_SNAPSHOT")
        schedule_sha = _required_sha(schedule_attestation_sha256, label="CLOUD_STAGE_SCHEDULE")
        input_sha = _required_sha(input_manifest_sha256, label="CLOUD_STAGE_INPUT")
        if sha256_bytes(snapshot_bytes) != snapshot_sha:
            raise CloudPaperRuntimeError("CLOUD_STAGE_SNAPSHOT_SHA_MISMATCH")
        if not isinstance(code_identity, Mapping):
            raise CloudPaperRuntimeError("CLOUD_STAGE_CODE_IDENTITY_INVALID")
        _required_git_sha(code_identity.get("commit"), label="CLOUD_STAGE_CODE_IDENTITY")
        existing = self._load_commit(session, stage)
        if existing is not None:
            if existing.status != status:
                raise CloudPaperRuntimeError("CLOUD_STAGE_EXISTING_STATUS_CONFLICT")
            self.verify_existing_identity(
                existing,
                schedule_attestation_sha256=schedule_sha,
                input_manifest_sha256=input_sha,
            )
            return existing
        result_body = {
            "schema_version": SCHEMA_VERSION,
            "session_date": session,
            "stage": stage,
            "stage_status": status,
            "run_id": _safe_key(run_id),
            "observed_started_at_utc": str(result_payload.get("observed_started_at_utc") or ""),
            "observed_finished_at_utc": str(result_payload.get("observed_finished_at_utc") or ""),
            "observed_availability_only": True,
            "controller_result": dict(result_payload),
            "outcome_accessed": False,
            "protected_forward_accessed": False,
            "model_refit": False,
        }
        _require_aware_timestamp(
            result_body["observed_started_at_utc"], label="CLOUD_STAGE_RESULT_STARTED"
        )
        _require_aware_timestamp(
            result_body["observed_finished_at_utc"], label="CLOUD_STAGE_RESULT_FINISHED"
        )
        result_bytes = canonical_json_bytes(result_body)
        result_key = f"sessions/{session}/stages/{stage}/runs/{_safe_key(run_id)}/result.json"
        result_ref = self.store.put_if_absent(result_key, result_bytes, "application/json")
        if result_ref.sha256 != sha256_bytes(result_bytes):
            raise CloudPaperRuntimeError("CLOUD_STAGE_RESULT_SHA_MISMATCH")
        snapshot_key = f"sessions/{session}/stages/{stage}/snapshots/{snapshot_sha}.zip"
        snapshot_ref = self.store.put_if_absent(snapshot_key, snapshot_bytes, "application/zip")
        if snapshot_ref.sha256 != snapshot_sha:
            raise CloudPaperRuntimeError("CLOUD_STAGE_SNAPSHOT_UPLOAD_SHA_MISMATCH")
        body: dict[str, Any] = {
            "schema_version": STAGE_COMMIT_SCHEMA_VERSION,
            "commit_state": "COMMITTED",
            "contract_version": CONTRACT_VERSION,
            "session_date": session,
            "stage": stage,
            "stage_status": status,
            "run_id": _safe_key(run_id),
            "committed_at_utc": datetime.now(UTC).isoformat(),
            "schedule_attestation_sha256": schedule_sha,
            "input_manifest_sha256": input_sha,
            "code_identity": dict(code_identity),
            "snapshot": {"key": snapshot_key, "sha256": snapshot_sha, "metadata": dict(snapshot_metadata)},
            "result": {"key": result_key, "sha256": result_ref.sha256},
            "guards": {
                "outcome_accessed": False,
                "protected_forward_accessed": False,
                "model_refit": False,
                "provider_calls_allowed_only_by_existing_stage": True,
                "paper_state_changes_only_by_existing_controller": True,
                "retroactive_execution_authorized": False,
            },
        }
        commit_bytes = canonical_json_bytes(body)
        commit_key = self.commit_key(session, stage)
        commit_ref = self.store.put_if_absent(commit_key, commit_bytes, "application/json")
        if commit_ref.sha256 != sha256_bytes(commit_bytes):
            raise CloudPaperRuntimeError("CLOUD_STAGE_COMMIT_SHA_MISMATCH")
        existing = self._load_commit(session, stage)
        if existing is None:
            raise CloudPaperRuntimeError("CLOUD_STAGE_COMMIT_NOT_READABLE")
        return existing

    def latest_snapshot(
        self,
        planned_sessions: Iterable[str],
        *,
        before_or_equal: str,
    ) -> tuple[bytes, str, dict[str, Any]] | None:
        cutoff = date.fromisoformat(before_or_equal)
        sessions = sorted(
            (date.fromisoformat(value).isoformat() for value in planned_sessions),
            reverse=True,
        )
        for session in sessions:
            if date.fromisoformat(session) > cutoff:
                continue
            for stage in ("PREOPEN", "POST_EOD"):
                commit = self._load_commit(session, stage)
                if commit is None or commit.snapshot_key is None or commit.snapshot_sha256 is None:
                    continue
                raw = self.store.read(commit.snapshot_key)
                if raw is None or sha256_bytes(raw) != commit.snapshot_sha256:
                    raise CloudPaperRuntimeError("CLOUD_LATEST_SNAPSHOT_INVALID")
                return raw, commit.snapshot_sha256, commit.payload
        return None


def load_schedule_from_bundle(
    bundle: CloudInputBundle,
    materialized: Mapping[str, Path],
) -> VerifiedOfficialTradingSchedule:
    path = materialized.get("execution_schedule")
    if path is None:
        raise CloudPaperRuntimeError("CLOUD_EXECUTION_SCHEDULE_MISSING")
    schedule_ref = next(
        (ref for ref in bundle.refs if ref.role == "execution_schedule"), None
    )
    declared = str(
        bundle.payload.get("execution_schedule_sha256")
        or (schedule_ref.sha256 if schedule_ref is not None else "")
    ).strip().lower()
    if schedule_ref is None or declared != schedule_ref.sha256:
        raise CloudPaperRuntimeError("CLOUD_EXECUTION_SCHEDULE_MANIFEST_SHA_MISMATCH")
    if not SHA_RE.fullmatch(declared) or sha256_bytes(path.read_bytes()) != declared:
        raise CloudPaperRuntimeError("CLOUD_EXECUTION_SCHEDULE_SHA_MISMATCH")
    source_path = materialized.get("execution_schedule_source")
    if source_path is None:
        raise CloudPaperRuntimeError("CLOUD_EXECUTION_SCHEDULE_SOURCE_MISSING")
    try:
        schedule_payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CloudPaperRuntimeError("CLOUD_EXECUTION_SCHEDULE_JSON_INVALID") from exc
    raw_source = schedule_payload.get("source_document_path")
    if not isinstance(raw_source, str) or Path(raw_source).is_absolute():
        raise CloudPaperRuntimeError("CLOUD_EXECUTION_SCHEDULE_SOURCE_PATH_NOT_PORTABLE")
    declared_source = (
        path.parent / Path(_safe_relative(raw_source, label="CLOUD_SCHEDULE_SOURCE"))
    ).resolve()
    if declared_source != source_path.resolve():
        raise CloudPaperRuntimeError("CLOUD_EXECUTION_SCHEDULE_SOURCE_PATH_MISMATCH")
    try:
        return load_verified_official_trading_schedule(path, expected_sha256=declared)
    except OfficialTradingScheduleError as exc:
        raise CloudPaperRuntimeError("CLOUD_EXECUTION_SCHEDULE_INVALID:" + str(exc)) from exc


def materialize_official_open_from_cloud(
    store: CloudObjectStore,
    *,
    session_date: str,
    target_root: str | Path,
) -> dict[str, Any] | None:
    """Copy the first valid committed Official Open slot to the local consumer root."""

    session = date.fromisoformat(session_date).isoformat()
    for slot in ("0902", "0912", "0922"):
        commit_key = f"session_date={session}/slot={slot}/slot_manifest.json"
        raw_commit = store.read(commit_key)
        if raw_commit is None:
            continue
        commit = _json_object(raw_commit, label="OFFICIAL_OPEN_CLOUD_COMMIT")
        if commit.get("commit_state") != "COMMITTED" or commit.get("session_date") != session or commit.get("slot") != slot:
            raise CloudPaperRuntimeError("OFFICIAL_OPEN_CLOUD_COMMIT_INVALID")
        artifacts = commit.get("artifacts")
        if not isinstance(artifacts, dict):
            raise CloudPaperRuntimeError("OFFICIAL_OPEN_CLOUD_ARTIFACT_REFS_MISSING")
        loaded: dict[str, bytes] = {}
        for name in ("raw_response", "open_prices", "source_manifest"):
            ref = artifacts.get(name)
            if not isinstance(ref, dict):
                raise CloudPaperRuntimeError("OFFICIAL_OPEN_CLOUD_ARTIFACT_REF_INVALID:" + name)
            key = _safe_key(str(ref.get("key") or ""))
            expected = _required_sha(ref.get("sha256"), label="OFFICIAL_OPEN_CLOUD_ARTIFACT")
            payload = store.read(key)
            if payload is None or sha256_bytes(payload) != expected:
                raise CloudPaperRuntimeError("OFFICIAL_OPEN_CLOUD_ARTIFACT_SHA_MISMATCH:" + name)
            loaded[name] = payload
        source = _json_object(loaded["source_manifest"], label="OFFICIAL_OPEN_SOURCE_MANIFEST")
        if source.get("session_date") != session or source.get("execution_grade") is not True:
            raise CloudPaperRuntimeError("OFFICIAL_OPEN_SOURCE_MANIFEST_INVALID")
        target = Path(target_root).expanduser().resolve() / session
        target.mkdir(parents=True, exist_ok=True)
        filenames = {
            "raw_response": "raw_response.json",
            "open_prices": "open_prices.parquet",
            "source_manifest": "manifest.json",
        }
        for name, filename in filenames.items():
            destination = target / filename
            payload = loaded[name]
            if destination.exists() and destination.read_bytes() != payload:
                raise CloudPaperRuntimeError("OFFICIAL_OPEN_LOCAL_COLLISION:" + name)
            if not destination.exists():
                destination.write_bytes(payload)
        try:
            from .official_open_cloud_archive_v1 import _verify_source_bundle

            _verify_source_bundle(target / "manifest.json", expected_session=session)
        except Exception as exc:
            raise CloudPaperRuntimeError("OFFICIAL_OPEN_SOURCE_BUNDLE_INVALID") from exc
        return {
            "session_date": session,
            "slot": slot,
            "slot_manifest_sha256": sha256_bytes(raw_commit),
            "source_manifest_sha256": sha256_bytes(loaded["source_manifest"]),
            "local_manifest": str((target / "manifest.json").resolve()),
        }
    return None


__all__ = [
    "CONTRACT_VERSION",
    "CloudInputBundle",
    "CloudInputRef",
    "CloudObjectStore",
    "CloudPaperArchive",
    "CloudPaperRuntimeError",
    "CloudStageCommit",
    "ConditionalS3Store",
    "INPUT_SCHEMA_VERSION",
    "LocalConditionalStore",
    "SNAPSHOT_SCHEMA_VERSION",
    "STAGE_COMMIT_SCHEMA_VERSION",
    "build_cloud_store_from_env",
    "build_runtime_snapshot",
    "canonical_json_bytes",
    "load_schedule_from_bundle",
    "materialize_official_open_from_cloud",
    "restore_runtime_snapshot",
    "sha256_bytes",
]
