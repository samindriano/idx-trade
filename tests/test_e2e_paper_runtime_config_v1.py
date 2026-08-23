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
        "runner_sha256": "d" * 64,
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


def test_loads_dynamic_per_window_ca_capture_config(tmp_path: Path) -> None:
    root = _write_config(
        tmp_path,
        ca_attestation_path=None,
        ca_attestation_sha256=None,
        ca_attestation_root=str(tmp_path / "ca-runtime"),
        ca_capture_script=str(tmp_path / "capture_ca.py"),
        ca_capture_script_sha256="e" * 64,
    )
    loaded = load_runtime_config(root)
    assert loaded.controller.ca_attestation_path is None
    assert loaded.controller.ca_attestation_root == (tmp_path / "ca-runtime").resolve()
    assert loaded.controller.ca_capture_script == (tmp_path / "capture_ca.py").resolve()
    assert loaded.controller.ca_capture_script_sha256 == "e" * 64


def test_dynamic_ca_fields_are_all_or_none(tmp_path: Path) -> None:
    root = _write_config(
        tmp_path,
        ca_attestation_path=None,
        ca_attestation_sha256=None,
        ca_attestation_root=str(tmp_path / "ca-runtime"),
        ca_capture_script=None,
        ca_capture_script_sha256=None,
    )
    with pytest.raises(E2ERuntimeConfigError, match="DYNAMIC_CA_FIELDS_INCOMPLETE"):
        load_runtime_config(root)


def test_static_and_dynamic_ca_sources_cannot_be_ambiguous(tmp_path: Path) -> None:
    root = _write_config(
        tmp_path,
        ca_attestation_root=str(tmp_path / "ca-runtime"),
        ca_capture_script=str(tmp_path / "capture_ca.py"),
        ca_capture_script_sha256="e" * 64,
    )
    with pytest.raises(E2ERuntimeConfigError, match="CA_SOURCE_AMBIGUOUS"):
        load_runtime_config(root)


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


def test_hash_and_parse_share_one_config_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _write_config(tmp_path)
    config_path = (root / "operational" / "config.json").resolve()
    original_read_text = Path.read_text

    def reject_second_config_read(path: Path, *args: object, **kwargs: object) -> str:
        if path.resolve() == config_path:
            raise AssertionError("config.json must be parsed from the hashed byte snapshot")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", reject_second_config_read)
    loaded = load_runtime_config(root)
    assert loaded.config_sha256 == hashlib.sha256(config_path.read_bytes()).hexdigest()


def test_relative_path_and_secret_field_fail_closed(tmp_path: Path) -> None:
    root = _write_config(tmp_path, repo_root="repo")
    with pytest.raises(E2ERuntimeConfigError, match="NOT_ABSOLUTE"):
        load_runtime_config(root)
    root = _write_config(tmp_path, api_key="must-not-be-configured")
    with pytest.raises(E2ERuntimeConfigError, match="SECRET_FIELD"):
        load_runtime_config(root)


@pytest.mark.parametrize("preopen", ["00:00", "08:29", "09:02"])
def test_preopen_time_cannot_expand_authorized_window(tmp_path: Path, preopen: str) -> None:
    root = _write_config(tmp_path, preopen_capture_start=preopen)
    with pytest.raises(E2ERuntimeConfigError, match="PREOPEN_TIME_UNAUTHORIZED"):
        load_runtime_config(root)
