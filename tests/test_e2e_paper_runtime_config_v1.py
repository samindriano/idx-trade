from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from idx_trade.e2e_paper_runtime_config_v1 import (
    CONFIG_SCHEMA,
    E2ERuntimeConfigError,
    load_runtime_config,
)


def _write_config(tmp_path: Path, **updates: object) -> Path:
    root = tmp_path / "runtime"
    config_path = root / "operational" / "config.json"
    root.joinpath("operational").mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "schema_version": CONFIG_SCHEMA,
        "expected_branch": "integration/idx-e2e-baseline-paper-v1",
        "expected_commit": "a" * 40,
        "provider_expected_commit": "b" * 40,
        "repo_root": str(tmp_path / "repo"),
        "forward_runtime_root": str(tmp_path / "forward"),
        "calendar_path": str(tmp_path / "calendar.csv"),
        "official_open_root": str(tmp_path / "open"),
        "provider_checkout": str(tmp_path / "provider"),
        "uv_exe": str(tmp_path / "uv.exe"),
        "python_exe": str(tmp_path / "python.exe"),
        "ca_attestation_path": str(tmp_path / "ca-attestation.json"),
        "ca_attestation_sha256": "c" * 64,
        "preopen_capture_start": "08:30",
    }
    payload.update(updates)
    encoded = (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode()
    config_path.write_bytes(encoded)
    config_path.with_name("config.json.sha256").write_text(hashlib.sha256(encoded).hexdigest() + "\n")
    return root


def test_loads_hash_pinned_external_config(tmp_path: Path) -> None:
    root = _write_config(tmp_path)
    loaded = load_runtime_config(root)
    assert loaded.controller.runtime_root == root.resolve()
    assert loaded.controller.expected_commit == "a" * 40


def test_missing_or_changed_sidecar_fails_closed(tmp_path: Path) -> None:
    root = _write_config(tmp_path)
    sidecar = root / "operational" / "config.json.sha256"
    sidecar.write_text("0" * 64)
    with pytest.raises(E2ERuntimeConfigError, match="SHA_MISMATCH"):
        load_runtime_config(root)


def test_task_pinned_expected_sha_is_checked(tmp_path: Path) -> None:
    root = _write_config(tmp_path)
    with pytest.raises(E2ERuntimeConfigError, match="EXPECTED_SHA_MISMATCH"):
        load_runtime_config(root, expected_sha256="0" * 64)


def test_relative_path_and_secret_field_fail_closed(tmp_path: Path) -> None:
    root = _write_config(tmp_path, repo_root="repo")
    with pytest.raises(E2ERuntimeConfigError, match="NOT_ABSOLUTE"):
        load_runtime_config(root)
    root = _write_config(tmp_path, api_key="must-not-be-configured")
    with pytest.raises(E2ERuntimeConfigError, match="SECRET_FIELD"):
        load_runtime_config(root)
