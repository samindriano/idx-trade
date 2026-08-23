"""Hash-pinned external configuration for the E2E PAPER controller.

The scheduler passes only the external runtime root.  All operational paths
remain outside Git, but are bound by an immutable config sidecar so a task
cannot silently drift to a different provider, calendar, or CA authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .e2e_paper_operational_controller_v1 import OperationalControllerConfig


CONFIG_SCHEMA = "idx_trade_e2e_paper_runtime_config_v1"
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_FORBIDDEN_KEY_PARTS = ("secret", "password", "token", "api_key", "credential")


class E2ERuntimeConfigError(RuntimeError):
    """Raised when external scheduler configuration is missing or unsafe."""


@dataclass(frozen=True)
class LoadedRuntimeConfig:
    config_path: Path
    config_sha256: str
    controller: OperationalControllerConfig


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _required_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise E2ERuntimeConfigError(f"E2E_RUNTIME_CONFIG_FIELD_MISSING:{key}")
    return value.strip()


def _absolute_path(payload: dict[str, Any], key: str) -> Path:
    value = _required_text(payload, key)
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise E2ERuntimeConfigError(f"E2E_RUNTIME_CONFIG_PATH_NOT_ABSOLUTE:{key}")
    return path.resolve()


def load_runtime_config(runtime_root: str | Path, *, expected_sha256: str | None = None) -> LoadedRuntimeConfig:
    root = Path(runtime_root).expanduser().resolve()
    config_path = root / "operational" / "config.json"
    digest_path = root / "operational" / "config.json.sha256"
    if not config_path.is_file() or not digest_path.is_file():
        raise E2ERuntimeConfigError("E2E_RUNTIME_CONFIG_MISSING")
    actual_sha = _sha256(config_path)
    declared_sha = digest_path.read_text(encoding="utf-8").strip().lower()
    if not _SHA_RE.fullmatch(declared_sha) or declared_sha != actual_sha:
        raise E2ERuntimeConfigError("E2E_RUNTIME_CONFIG_SHA_MISMATCH")
    if expected_sha256 is not None and declared_sha != expected_sha256.strip().lower():
        raise E2ERuntimeConfigError("E2E_RUNTIME_CONFIG_EXPECTED_SHA_MISMATCH")
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise E2ERuntimeConfigError("E2E_RUNTIME_CONFIG_INVALID_JSON") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != CONFIG_SCHEMA:
        raise E2ERuntimeConfigError("E2E_RUNTIME_CONFIG_SCHEMA_MISMATCH")
    for key in payload:
        lowered = str(key).lower()
        if any(part in lowered for part in _FORBIDDEN_KEY_PARTS):
            raise E2ERuntimeConfigError("E2E_RUNTIME_CONFIG_SECRET_FIELD_FORBIDDEN")

    expected_branch = _required_text(payload, "expected_branch")
    expected_commit = _required_text(payload, "expected_commit").lower()
    provider_commit = _required_text(payload, "provider_expected_commit").lower()
    if not _COMMIT_RE.fullmatch(expected_commit) or not _COMMIT_RE.fullmatch(provider_commit):
        raise E2ERuntimeConfigError("E2E_RUNTIME_CONFIG_COMMIT_INVALID")
    preopen_text = str(payload.get("preopen_capture_start") or "08:30")
    try:
        preopen_start = time.fromisoformat(preopen_text)
    except ValueError as exc:
        raise E2ERuntimeConfigError("E2E_RUNTIME_CONFIG_PREOPEN_TIME_INVALID") from exc
    ca_sha = _required_text(payload, "ca_attestation_sha256").lower()
    if not _SHA_RE.fullmatch(ca_sha):
        raise E2ERuntimeConfigError("E2E_RUNTIME_CONFIG_CA_SHA_INVALID")

    controller = OperationalControllerConfig(
        runtime_root=root,
        forward_runtime_root=_absolute_path(payload, "forward_runtime_root"),
        calendar_path=_absolute_path(payload, "calendar_path"),
        official_open_root=_absolute_path(payload, "official_open_root"),
        repo_root=_absolute_path(payload, "repo_root"),
        expected_branch=expected_branch,
        expected_commit=expected_commit,
        provider_checkout=_absolute_path(payload, "provider_checkout"),
        provider_expected_commit=provider_commit,
        uv_exe=_absolute_path(payload, "uv_exe"),
        python_exe=_absolute_path(payload, "python_exe"),
        ca_attestation_path=_absolute_path(payload, "ca_attestation_path"),
        ca_attestation_sha256=ca_sha,
        initial_journal_path=(
            _absolute_path(payload, "initial_journal_path")
            if payload.get("initial_journal_path") is not None
            else None
        ),
        initial_journal_sha256=(
            _required_text(payload, "initial_journal_sha256").lower()
            if payload.get("initial_journal_path") is not None
            else None
        ),
        preopen_capture_start=preopen_start,
    )
    if controller.initial_journal_path is not None:
        if controller.initial_journal_sha256 is None or not _SHA_RE.fullmatch(controller.initial_journal_sha256):
            raise E2ERuntimeConfigError("E2E_RUNTIME_CONFIG_INITIAL_JOURNAL_SHA_INVALID")
    return LoadedRuntimeConfig(config_path=config_path, config_sha256=actual_sha, controller=controller)


__all__ = ["CONFIG_SCHEMA", "E2ERuntimeConfigError", "LoadedRuntimeConfig", "load_runtime_config"]
