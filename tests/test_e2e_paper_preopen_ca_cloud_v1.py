from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import idx_trade.e2e_paper_operational_controller_v1 as controller_v1
import idx_trade.e2e_paper_preopen_ca_cloud_v1 as preopen_ca
from idx_trade.e2e_operational_guard_v1 import JAKARTA
from idx_trade.e2e_paper_cloud_runtime_v1 import (
    LocalConditionalStore,
    build_runtime_snapshot,
)
from idx_trade.e2e_paper_operational_controller_v2 import OperationalControllerConfigV2
from idx_trade.e2e_paper_orchestration_v1 import bootstrap_t0
from idx_trade.stockbit_stream_archive import StorageImmutabilityConflict


CODE_SHA = "a" * 40
RUNNER_SHA = "9" * 64
SCHEDULE_SHA = "b" * 64
INPUT_SHA = "c" * 64


def _guards() -> dict[str, bool]:
    return {
        "outcome_accessed": False,
        "protected_forward_accessed": False,
        "model_refit": False,
        "paper_state_mutated": False,
        "order_created": False,
        "fill_created": False,
        "retroactive_execution_authorized": False,
    }


def _result(session: str = "2026-08-28", **extra) -> dict[str, object]:
    return {
        "schema_version": "idx_trade_e2e_paper_preopen_ca_result_v1",
        "session_date": session,
        "stage": preopen_ca.CHECKPOINT_STAGE,
        "controller_status": preopen_ca.CHECKPOINT_STATUS,
        **_guards(),
        **extra,
    }


def _code_identity() -> dict[str, str]:
    return {
        "repo": "samindriano/idx-trade",
        "commit": CODE_SHA,
        "runner_sha256": RUNNER_SHA,
    }


def _base_config(tmp_path: Path) -> controller_v1.OperationalControllerConfig:
    provider = tmp_path / "provider"
    (provider / "python").mkdir(parents=True)
    uv = tmp_path / "uv"
    python = tmp_path / "python"
    capture = tmp_path / "capture_ca.py"
    for path in (uv, python, capture):
        path.write_text("stub\n", encoding="utf-8")
    return controller_v1.OperationalControllerConfig(
        runtime_root=tmp_path / "runtime",
        forward_runtime_root=tmp_path / "forward",
        calendar_path=tmp_path / "calendar.csv",
        official_open_root=tmp_path / "open",
        repo_root=tmp_path,
        expected_branch="cloud-pinned-runtime",
        expected_commit=CODE_SHA,
        provider_checkout=provider,
        provider_expected_commit="d" * 40,
        uv_exe=uv,
        python_exe=python,
        ca_attestation_root=tmp_path / "ca",
        ca_capture_script=capture,
        ca_capture_script_sha256="e" * 64,
    )


def _snapshot(tmp_path: Path):
    runtime = tmp_path / "snapshot-runtime"
    runtime.mkdir()
    (runtime / "sentinel.txt").write_text("ca-ready\n", encoding="utf-8")
    return build_runtime_snapshot({"paper": runtime})


def test_checkpoint_roundtrip_is_identity_bound_and_immutable(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    snapshot, snapshot_sha, metadata = _snapshot(tmp_path)
    created = preopen_ca.commit_preopen_ca_checkpoint(
        store,
        session_date="2026-08-28",
        snapshot_bytes=snapshot,
        snapshot_metadata=metadata,
        result_payload=_result(),
        schedule_attestation_sha256=SCHEDULE_SHA,
        input_manifest_sha256=INPUT_SHA,
        code_identity=_code_identity(),
    )
    assert created.snapshot_sha256 == snapshot_sha
    replay = preopen_ca.load_preopen_ca_checkpoint(
        store,
        session_date="2026-08-28",
        expected_schedule_sha256=SCHEDULE_SHA,
        expected_input_manifest_sha256=INPUT_SHA,
        expected_code_commit=CODE_SHA,
    )
    assert replay is not None
    assert replay.commit_sha256 == created.commit_sha256
    assert replay.payload["snapshot"]["metadata"]["snapshot_sha256"] == snapshot_sha
    with pytest.raises(Exception, match="CODE_MISMATCH"):
        preopen_ca.load_preopen_ca_checkpoint(
            store,
            session_date="2026-08-28",
            expected_schedule_sha256=SCHEDULE_SHA,
            expected_input_manifest_sha256=INPUT_SHA,
            expected_code_commit="f" * 40,
        )


def test_checkpoint_rejects_unbound_snapshot_metadata_before_write(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    snapshot, _, metadata = _snapshot(tmp_path)
    metadata = dict(metadata)
    metadata["snapshot_sha256"] = "f" * 64
    with pytest.raises(Exception, match="SNAPSHOT_METADATA_SHA_MISMATCH"):
        preopen_ca.commit_preopen_ca_checkpoint(
            store,
            session_date="2026-08-28",
            snapshot_bytes=snapshot,
            snapshot_metadata=metadata,
            result_payload=_result(),
            schedule_attestation_sha256=SCHEDULE_SHA,
            input_manifest_sha256=INPUT_SHA,
            code_identity=_code_identity(),
        )
    assert store.read(preopen_ca.checkpoint_commit_key("2026-08-28")) is None


def test_checkpoint_rejects_result_that_claims_paper_mutation(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    snapshot, _, metadata = _snapshot(tmp_path)
    bad = _result()
    bad["paper_state_mutated"] = True
    with pytest.raises(Exception, match="RESULT_GUARD_INVALID"):
        preopen_ca.commit_preopen_ca_checkpoint(
            store,
            session_date="2026-08-28",
            snapshot_bytes=snapshot,
            snapshot_metadata=metadata,
            result_payload=bad,
            schedule_attestation_sha256=SCHEDULE_SHA,
            input_manifest_sha256=INPUT_SHA,
            code_identity=_code_identity(),
        )


def test_divergent_checkpoint_rerun_fails_closed(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    snapshot, _, metadata = _snapshot(tmp_path)
    kwargs = dict(
        store=store,
        session_date="2026-08-28",
        snapshot_bytes=snapshot,
        snapshot_metadata=metadata,
        schedule_attestation_sha256=SCHEDULE_SHA,
        input_manifest_sha256=INPUT_SHA,
        code_identity=_code_identity(),
    )
    preopen_ca.commit_preopen_ca_checkpoint(result_payload=_result(marker="first"), **kwargs)
    with pytest.raises(StorageImmutabilityConflict):
        preopen_ca.commit_preopen_ca_checkpoint(result_payload=_result(marker="different"), **kwargs)


def test_loader_detects_tampered_snapshot_metadata_binding(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    snapshot, _, metadata = _snapshot(tmp_path)
    preopen_ca.commit_preopen_ca_checkpoint(
        store,
        session_date="2026-08-28",
        snapshot_bytes=snapshot,
        snapshot_metadata=metadata,
        result_payload=_result(),
        schedule_attestation_sha256=SCHEDULE_SHA,
        input_manifest_sha256=INPUT_SHA,
        code_identity=_code_identity(),
    )
    commit_path = store._path(preopen_ca.checkpoint_commit_key("2026-08-28"))
    payload = json.loads(commit_path.read_text(encoding="utf-8"))
    payload["snapshot"]["metadata"]["snapshot_sha256"] = "0" * 64
    commit_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(Exception, match="SNAPSHOT_METADATA_SHA_MISMATCH"):
        preopen_ca.load_preopen_ca_checkpoint(
            store,
            session_date="2026-08-28",
            expected_schedule_sha256=SCHEDULE_SHA,
            expected_input_manifest_sha256=INPUT_SHA,
            expected_code_commit=CODE_SHA,
        )


def test_existing_t0_stays_anchored_across_multiple_later_sessions(tmp_path: Path) -> None:
    root = tmp_path / "paper"
    first = bootstrap_t0(root, session_date="2026-08-27")
    first_bytes = first.read_bytes()
    for later in ("2026-08-28", "2026-08-31"):
        replay = preopen_ca.validate_existing_t0_or_bootstrap(
            root,
            session_date=later,
            original_bootstrap=bootstrap_t0,
        )
        assert replay == first
        assert replay.read_bytes() == first_bytes
    payload = json.loads(first.read_text(encoding="utf-8"))
    assert payload["session_date"] == "2026-08-27"


def test_existing_t0_from_future_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "paper"
    bootstrap_t0(root, session_date="2026-08-28")
    with pytest.raises(Exception, match="T0_EXISTING_ROOT_FROM_FUTURE"):
        preopen_ca.validate_existing_t0_or_bootstrap(
            root,
            session_date="2026-08-27",
            original_bootstrap=bootstrap_t0,
        )


def _schedule(*sessions: str):
    return SimpleNamespace(
        session_dates=sessions,
        coverage_start=min(sessions),
        coverage_end=max(sessions),
    )


def test_preopen_ca_cycle_uses_prepared_decision_to_execution_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _base_config(tmp_path)
    prepared = base.runtime_root / "prepared" / "2026-08-27.json"
    prepared.parent.mkdir(parents=True)
    prepared.write_text(
        json.dumps(
            {
                "schema_version": "idx_trade_e2e_paper_prepared_execution_v1",
                "decision_session_date": "2026-08-27",
                "execution_session_date": "2026-08-28",
                "required_tickers": ["BBCA", "BBRI"],
            }
        ),
        encoding="utf-8",
    )
    config = OperationalControllerConfigV2(
        base=base,
        execution_schedule_attestation_path=tmp_path / "schedule.json",
        execution_schedule_attestation_sha256=SCHEDULE_SHA,
    )
    monkeypatch.setattr(
        preopen_ca,
        "attest_deployment",
        lambda *a, **k: SimpleNamespace(
            branch="cloud-pinned-runtime",
            head=CODE_SHA,
            expected_commit=CODE_SHA,
            clean=True,
        ),
    )
    monkeypatch.setattr(preopen_ca, "exclusive_run_lock", lambda path: nullcontext())
    monkeypatch.setattr(
        preopen_ca,
        "load_verified_official_trading_schedule",
        lambda *a, **k: _schedule("2026-08-27", "2026-08-28"),
    )
    monkeypatch.setattr(
        preopen_ca.v2,
        "_verified_prepared_for_session",
        lambda *a, **k: ([prepared], []),
    )
    seen = {}

    def fake_ensure(_config, **kwargs):
        seen.update(kwargs)
        return "CAPTURED"

    monkeypatch.setattr(preopen_ca, "_ensure_preopen_ca_phase", fake_ensure)
    result = preopen_ca.run_preopen_ca_cycle(
        config,
        now=datetime(2026, 8, 28, 8, 40, tzinfo=JAKARTA),
    )
    assert result["controller_status"] == preopen_ca.CHECKPOINT_STATUS
    assert seen["phase_session"] == "2026-08-28"
    assert seen["from_session"] == "2026-08-27"
    assert seen["through_session"] == "2026-08-28"
    assert seen["required_tickers"] == ("BBCA", "BBRI")


def test_first_cloud_morning_without_prepared_order_waits_without_capture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _base_config(tmp_path)
    config = OperationalControllerConfigV2(
        base=base,
        execution_schedule_attestation_path=tmp_path / "schedule.json",
        execution_schedule_attestation_sha256=SCHEDULE_SHA,
    )
    monkeypatch.setattr(
        preopen_ca,
        "attest_deployment",
        lambda *a, **k: SimpleNamespace(
            branch="cloud-pinned-runtime",
            head=CODE_SHA,
            expected_commit=CODE_SHA,
            clean=True,
        ),
    )
    monkeypatch.setattr(preopen_ca, "exclusive_run_lock", lambda path: nullcontext())
    monkeypatch.setattr(
        preopen_ca,
        "load_verified_official_trading_schedule",
        lambda *a, **k: _schedule("2026-08-27"),
    )
    monkeypatch.setattr(
        preopen_ca.v2,
        "_verified_prepared_for_session",
        lambda *a, **k: ([], []),
    )
    monkeypatch.setattr(
        preopen_ca,
        "_ensure_preopen_ca_phase",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not capture without prepared")),
    )
    result = preopen_ca.run_preopen_ca_cycle(
        config,
        now=datetime(2026, 8, 27, 8, 40, tzinfo=JAKARTA),
    )
    assert result["controller_status"] == "WAITING_PREPARED_EXECUTION"
    assert result["provider_calls"] is False


def test_preopen_ca_capture_wires_d_post_eod_parent_and_d_to_e_attestation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _base_config(tmp_path)
    decision = "2026-08-27"
    execution = "2026-08-28"
    prior = controller_v1._journal_paths(config, decision, "POST_EOD")[1]
    prior.parent.mkdir(parents=True)
    prior.write_text("prior\n", encoding="utf-8")

    def fake_journal(path):
        text = str(path)
        if text.endswith(f"{decision}_POST_EOD.json"):
            journal = SimpleNamespace(as_of_date=decision, capture_phase="POST_EOD")
        else:
            journal = SimpleNamespace(as_of_date=execution, capture_phase="PREOPEN")
        return SimpleNamespace(journal=journal)

    monkeypatch.setattr(preopen_ca, "load_journal_document", fake_journal)
    monkeypatch.setattr(preopen_ca.v1, "_config_missing", lambda cfg: None)
    monkeypatch.setattr(
        preopen_ca,
        "_load_and_verify_post_eod_attestation_v1_2",
        lambda **kwargs: None,
    )
    commands = []

    def fake_run_child(cfg, label, command, **kwargs):
        commands.append((label, list(command)))
        if label == "ca_capture_preopen_cloud":
            output = Path(command[command.index("--output-dir") + 1])
            attestation = Path(command[command.index("--attestation-output") + 1])
            output.mkdir(parents=True)
            attestation.parent.mkdir(parents=True, exist_ok=True)
            attestation.write_text("attestation\n", encoding="utf-8")
        elif label == "ca_preopen_cloud":
            batch, journal = controller_v1._journal_paths(cfg, execution, "PREOPEN")
            batch.mkdir(parents=True)
            journal.parent.mkdir(parents=True, exist_ok=True)
            journal.write_text("journal\n", encoding="utf-8")

    monkeypatch.setattr(preopen_ca.v1, "_run_child", fake_run_child)
    monkeypatch.setattr(
        preopen_ca.v1,
        "_verify_phase_sidecar",
        lambda cfg, session, phase, through_session: json.loads(
            controller_v1._phase_sidecar_path(cfg, session, phase).read_text(encoding="utf-8")
        ),
    )
    result = preopen_ca._ensure_preopen_ca_phase(
        config,
        phase_session=execution,
        from_session=decision,
        through_session=execution,
        required_tickers=("BBCA", "BBRI"),
        now=datetime(2026, 8, 28, 8, 40, tzinfo=JAKARTA),
        clock=lambda: datetime(2026, 8, 28, 8, 50, tzinfo=JAKARTA),
    )
    assert result == "CAPTURED"
    assert [label for label, _ in commands] == ["ca_capture_preopen_cloud", "ca_preopen_cloud"]
    capture = commands[0][1]
    assert capture[capture.index("--from-session") + 1] == decision
    assert capture[capture.index("--through-session") + 1] == execution
    acquisition = commands[1][1]
    assert acquisition[acquisition.index("--as-of-date") + 1] == execution
    assert acquisition[acquisition.index("--prior-journal") + 1] == str(prior.resolve())
    sidecar = json.loads(
        controller_v1._phase_sidecar_path(config, execution, "PREOPEN").read_text(encoding="utf-8")
    )
    assert sidecar["from_session_date"] == decision
    assert sidecar["through_session_date"] == execution
    assert not (config.runtime_root / "executions" / f"{execution}.json").exists()
