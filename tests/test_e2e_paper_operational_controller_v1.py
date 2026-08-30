from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

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


def test_score_pointer_verifies_artifact_when_declared(tmp_path: Path) -> None:
    manifest = tmp_path / "score.json"
    artifact = tmp_path / "scores.parquet"
    manifest.write_text("{}\n", encoding="utf-8")
    artifact.write_bytes(b"score")
    good = {
        "manifest_path": str(manifest),
        "manifest_sha256": _sha(manifest),
        "artifact_path": str(artifact),
        "artifact_sha256": _sha(artifact),
        "session_date": "2026-08-21",
    }
    assert controller._verify_score_pointer({"x1_score": good}, "2026-08-21") == good
    with pytest.raises(E2EOperationalGuardError, match="ARTIFACT_HASH_MISMATCH"):
        controller._verify_score_pointer(
            {"x1_score": {**good, "artifact_sha256": "0" * 64}}, "2026-08-21"
        )


def test_previous_score_requires_verified_immediate_predecessor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)
    meta_dir = config.runtime_root / "state" / "decisions"
    meta_dir.mkdir(parents=True)
    manifests: dict[Path, SimpleNamespace] = {}

    def add_metadata(filename: str, session: str, label: str) -> Path:
        manifest = tmp_path / f"score-{label}.json"
        manifest.write_text("{}\n", encoding="utf-8")
        manifest_sha = _sha(manifest)
        manifests[manifest.resolve()] = SimpleNamespace(
            manifest_sha256=manifest_sha,
            session_date=session,
        )
        body = {
            "last_score_session_date": session,
            "last_score_manifest_path": str(manifest.resolve()),
            "last_score_manifest_sha256": manifest_sha,
        }
        (meta_dir / filename).write_text(
            json.dumps({**body, "payload_sha256": _canonical_hash(body)}) + "\n",
            encoding="utf-8",
        )
        return manifest

    monkeypatch.setattr(
        controller,
        "load_score_manifest",
        lambda path: manifests[Path(path).resolve()],
    )

    old = add_metadata("z-old.json", "2026-08-25", "old")
    with pytest.raises(E2EOperationalGuardError, match="PREVIOUS_SCORE_MISSING"):
        controller._previous_score_manifest(
            config,
            "2026-08-27",
            expected_previous_session="2026-08-26",
        )

    exact = add_metadata("a-exact.json", "2026-08-26", "exact")
    assert controller._previous_score_manifest(
        config,
        "2026-08-27",
        expected_previous_session="2026-08-26",
    ) == exact.resolve()
    assert controller._previous_score_manifest(
        config,
        "2026-08-26",
        expected_previous_session="2026-08-25",
    ) == old.resolve()

    conflicting = add_metadata("m-conflict.json", "2026-08-26", "conflict")
    assert conflicting != exact
    with pytest.raises(E2EOperationalGuardError, match="PREVIOUS_SCORE_AMBIGUOUS"):
        controller._previous_score_manifest(
            config,
            "2026-08-27",
            expected_previous_session="2026-08-26",
        )


def test_first_decision_mid_schedule_does_not_require_market_predecessor(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    controller.bootstrap_t0(config.runtime_root, session_date="2026-08-24")
    sessions = ("2026-08-21", "2026-08-24")

    assert controller._expected_previous_score_session(
        config, sessions, "2026-08-24"
    ) is None
    assert controller._previous_score_manifest(
        config,
        "2026-08-24",
        expected_previous_session=None,
    ) is None


def test_missing_operational_config_fails_closed_without_provider_call(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert controller._config_missing(config) == (
        "MISSING_OPERATIONAL_CONFIG:provider_checkout,provider_expected_commit,uv_exe,"
        "python_exe,ca_attestation_path,ca_attestation_sha256"
    )


def test_reused_ca_sidecar_is_bound_to_exact_through_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)
    sidecar = controller._phase_sidecar_path(config, "2026-08-24", "POST_EOD")
    sidecar.parent.mkdir(parents=True)
    sidecar.write_text("placeholder\n", encoding="utf-8")
    seen: dict[str, str] = {}

    def verify(_config, session, phase, *, through_session):
        seen.update(session=session, phase=phase, through_session=through_session)
        return {"required_tickers": ["BBCA"], "finished_at_jakarta": ""}

    monkeypatch.setattr(controller, "_verify_phase_sidecar", verify)
    assert controller._ensure_ca_phase(
        config,
        session="2026-08-24",
        through_session="2026-08-25",
        phase="POST_EOD",
        required_tickers=["BBCA"],
        now=datetime(2026, 8, 24, 18, tzinfo=JAKARTA),
    ) == "REUSED"
    assert seen == {
        "session": "2026-08-24",
        "phase": "POST_EOD",
        "through_session": "2026-08-25",
    }


def test_phase_sidecar_rejects_stale_through_session(tmp_path: Path) -> None:
    config = _config(tmp_path)
    sidecar = controller._phase_sidecar_path(config, "2026-08-24", "POST_EOD")
    sidecar.parent.mkdir(parents=True)
    body = {
        "schema_version": "idx_trade_e2e_operational_ca_phase_v1",
        "phase": "POST_EOD",
        "session_date": "2026-08-24",
        "through_session_date": "2026-08-26",
    }
    sidecar.write_text(
        json.dumps({**body, "payload_sha256": _canonical_hash(body)}),
        encoding="utf-8",
    )
    with pytest.raises(E2EOperationalGuardError, match="CA_PHASE_SIDECAR_PARENT_MISMATCH"):
        controller._verify_phase_sidecar(
            config,
            "2026-08-24",
            "POST_EOD",
            through_session="2026-08-25",
        )


def test_child_failure_is_redacted_to_hash_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _config(tmp_path)

    class Failed:
        returncode = 7
        stdout = "safe stdout"
        stderr = "safe stderr"

    monkeypatch.setattr(controller.subprocess, "run", lambda *args, **kwargs: Failed())
    with pytest.raises(E2EOperationalGuardError, match="CHILD_PROCESS_FAILED:test"):
        controller._run_child(config, "test", ["python", "script.py"])
    logs = list((config.runtime_root / "operational" / "processes").glob("*.json"))
    assert len(logs) == 1
    payload = json.loads(logs[0].read_text(encoding="utf-8"))
    assert "safe stdout" not in json.dumps(payload)
    assert payload["stdout_sha256"] == _sha256_text("safe stdout")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


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
