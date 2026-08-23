from __future__ import annotations

from pathlib import Path

import pytest

from idx_trade.e2e_replay_boundary_v1 import replay_boundary_static_audit_v1


def test_replay_boundary_audit_derives_zero_counts_and_hashes_source(tmp_path: Path) -> None:
    source = tmp_path / "safe.py"
    source.write_text("from pathlib import Path\nPath('x')\n", encoding="utf-8")
    result = replay_boundary_static_audit_v1((source,), source_kind="synthetic")
    assert result["provider_call_count"] == 0
    assert result["protected_outcome_read_count"] == 0
    assert result["model_refit_count"] == 0
    assert result["model_rescore_count"] == 0
    assert result["by_construction"] is True
    assert result["audited_files"][0]["sha256"]
    assert result["audit_sha256"]


def test_replay_boundary_audit_rejects_provider_import(tmp_path: Path) -> None:
    source = tmp_path / "unsafe.py"
    source.write_text("import requests\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="E2E_REPLAY_BOUNDARY_STATIC_AUDIT_FAILED"):
        replay_boundary_static_audit_v1((source,), source_kind="synthetic")
