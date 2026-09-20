from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from idx_trade import e2e_paper_phase_binding_v1 as phase_binding
from idx_trade.e2e_paper_phase_binding_v1 import load_phase_runtime_binding
from idx_trade.e2e_paper_runtime_config_v1 import (
    CONFIG_SCHEMA,
    E2ERuntimeConfigError,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_config(tmp_path: Path, **updates: object) -> Path:
    root = tmp_path / "runtime"
    operational = root / "operational"
    operational.mkdir(parents=True)
    payload: dict[str, object] = {
        "schema_version": CONFIG_SCHEMA,
        "expected_branch": "codex/phase-binding-test",
        "expected_commit": "a" * 40,
        "provider_expected_commit": "b" * 40,
        "repo_root": str(tmp_path / "repo"),
        "forward_runtime_root": str(tmp_path / "forward"),
        "calendar_path": str(tmp_path / "calendar.csv"),
        "official_open_root": str(tmp_path / "open"),
        "provider_checkout": str(tmp_path / "provider"),
        "uv_exe": str(tmp_path / "uv.exe"),
        "python_exe": str(tmp_path / "python.exe"),
        "ca_attestation_path": str(tmp_path / "ca.json"),
        "ca_attestation_sha256": "c" * 64,
        "runner_sha256": "d" * 64,
        "preopen_capture_start": "08:30",
    }
    payload.update(updates)
    encoded = (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode()
    config = operational / "config.json"
    config.write_bytes(encoded)
    (operational / "config.json.sha256").write_text(
        hashlib.sha256(encoded).hexdigest() + "\n",
        encoding="utf-8",
    )
    return root


def test_phase_binding_requires_hash_pinned_config_and_matching_identity(
    tmp_path: Path,
) -> None:
    root = _write_config(tmp_path)
    expected = hashlib.sha256(
        (root / "operational" / "config.json").read_bytes()
    ).hexdigest()
    assert load_phase_runtime_binding(
        root,
        expected_branch="codex/phase-binding-test",
        expected_commit="a" * 40,
    ) == expected
    with pytest.raises(E2ERuntimeConfigError, match="REPO_IDENTITY_MISMATCH"):
        load_phase_runtime_binding(
            root,
            expected_branch="codex/wrong-parent",
            expected_commit="a" * 40,
        )


def test_phase_binding_rejects_missing_external_config(tmp_path: Path) -> None:
    with pytest.raises(E2ERuntimeConfigError, match="CONFIG_MISSING"):
        load_phase_runtime_binding(
            tmp_path / "missing-runtime",
            expected_branch="codex/phase-binding-test",
            expected_commit="a" * 40,
        )


def test_dual_calendar_phase_binding_uses_v2_loader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: list[Path] = []

    def fake_loader(runtime_root: str | Path):
        observed.append(Path(runtime_root))
        return SimpleNamespace(
            config_sha256="e" * 64,
            controller=SimpleNamespace(
                expected_branch="codex/phase-binding-test",
                expected_commit="a" * 40,
            ),
        )

    monkeypatch.setattr(phase_binding, "load_runtime_config_v2", fake_loader)
    assert load_phase_runtime_binding(
        tmp_path / "dual",
        expected_branch="codex/phase-binding-test",
        expected_commit="a" * 40,
        dual_calendar=True,
    ) == "e" * 64
    assert observed == [tmp_path / "dual"]


def test_all_phase_scripts_use_mandatory_runtime_binding() -> None:
    scripts = (
        ("run_e2e_paper_post_eod_v1.py", "prepare_post_eod", False),
        ("run_e2e_paper_preopen_v1.py", "execute_preopen", False),
        ("run_e2e_paper_post_eod_v2.py", "prepare_post_eod", True),
        ("run_e2e_paper_preopen_v2.py", "execute_preopen", True),
    )
    for name, orchestration_function, is_v2 in scripts:
        tree = ast.parse(
            (REPO_ROOT / "scripts" / name).read_text(encoding="utf-8")
        )
        binding_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "load_phase_runtime_binding"
        ]
        assert len(binding_calls) == 1
        if is_v2:
            assert any(
                keyword.arg == "dual_calendar"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
                for keyword in binding_calls[0].keywords
            )
        orchestration_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == orchestration_function
        ]
        assert len(orchestration_calls) == 1
        runtime_keyword = next(
            keyword
            for keyword in orchestration_calls[0].keywords
            if keyword.arg == "runtime_config_sha256"
        )
        assert isinstance(runtime_keyword.value, ast.Name)
        assert runtime_keyword.value.id == "runtime_config_sha256"
