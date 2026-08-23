from __future__ import annotations

from contextlib import nullcontext
import hashlib
import json
from pathlib import Path

import pytest

from idx_trade import e2e_paper_operational_controller_v1 as controller
from idx_trade.e2e_operational_guard_v1 import (
    DeploymentAttestation,
    E2EOperationalGuardError,
    JAKARTA,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_hash(payload: dict) -> str:
    return hashlib.sha256(
        (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()
    ).hexdigest()


def _config(tmp_path: Path) -> controller.OperationalControllerConfig:
    return controller.OperationalControllerConfig(
        runtime_root=tmp_path / "runtime",
        forward_runtime_root=tmp_path / "forward",
        calendar_path=tmp_path / "calendar.csv",
        official_open_root=tmp_path / "open",
        repo_root=tmp_path / "repo",
        expected_branch="integration/test",
        expected_commit="abc123",
    )


def test_score_pointer_requires_exact_manifest_hash_and_session(tmp_path: Path) -> None:
    manifest = tmp_path / "score.json"
    manifest.write_text("{}\n", encoding="utf-8")
    good = {
        "manifest_path": str(manifest),
        "manifest_sha256": _sha(manifest),
        "session_date": "2026-08-21",
    }
    assert controller._verify_score_pointer({"x1_score": good}, "2026-08-21") == good
    with pytest.raises(E2EOperationalGuardError, match="MANIFEST_HASH_MISMATCH"):
        controller._verify_score_pointer(
            {"x1_score": {**good, "manifest_sha256": "0" * 64}}, "2026-08-21"
        )
    with pytest.raises(E2EOperationalGuardError, match="SESSION_MISMATCH"):
        controller._verify_score_pointer({"x1_score": good}, "2026-08-20")


def test_prepared_selection_requires_schema_payload_and_eod_file_hashes(tmp_path: Path) -> None:
    config = _config(tmp_path)
    prepared_dir = config.runtime_root / "prepared"
    prepared_dir.mkdir(parents=True)
    eod = {}
    for key in ("ohlcv", "model_input", "calendar"):
        path = tmp_path / f"{key}.bin"
        path.write_bytes(key.encode())
        eod[key] = {"path": str(path), "sha256": _sha(path)}
    body = {
        "schema_version": "idx_trade_e2e_paper_prepared_execution_v1",
        "status": "PREPARED_EXECUTION",
        "execution_session_date": "2026-08-24",
        "eod_inputs": eod,
    }
    valid = {**body, "payload_sha256": _canonical_hash(body)}
    (prepared_dir / "valid.json").write_text(json.dumps(valid), encoding="utf-8")
    invalid = {**valid, "payload_sha256": "0" * 64}
    (prepared_dir / "invalid.json").write_text(json.dumps(invalid), encoding="utf-8")
    assert controller._prepared_for_session(config, "2026-08-24") == [prepared_dir / "valid.json"]
    eod["ohlcv"]["sha256"] = "0" * 64
    (prepared_dir / "changed.json").write_text(
        json.dumps({**body, "eod_inputs": eod, "payload_sha256": _canonical_hash({**body, "eod_inputs": eod})}),
        encoding="utf-8",
    )
    assert controller._prepared_for_session(config, "2026-08-24") == [prepared_dir / "valid.json"]


def test_sunday_controller_is_a_persisted_noop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _config(tmp_path)
    config.calendar_path.write_text("date\n2026-08-24\n", encoding="utf-8")
    monkeypatch.setattr(
        controller,
        "attest_deployment",
        lambda *args, **kwargs: DeploymentAttestation(
            config.repo_root, "integration/test", "abc123", "integration/test", "abc123", True
        ),
    )
    monkeypatch.setattr(controller, "exclusive_run_lock", lambda path: nullcontext())
    status = controller.run_operational_cycle(
        config,
        now=controller.datetime(2026, 8, 23, 12, 0, tzinfo=JAKARTA),
    )
    assert status["controller_status"] == "WEEKEND_OR_HOLIDAY_NOOP"
    assert status["provider_calls"] is False
    assert status["outcome_access"] is False
    assert (config.runtime_root / "operational" / "latest.json").is_file()
