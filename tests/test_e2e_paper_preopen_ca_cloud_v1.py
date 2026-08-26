from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from idx_trade import e2e_paper_operational_controller_v1 as controller_v1
from idx_trade.e2e_operational_guard_v1 import JAKARTA
from idx_trade.e2e_paper_cloud_runtime_v1 import (
    LocalConditionalStore,
    build_runtime_snapshot,
)
from idx_trade.e2e_paper_operational_controller_v2 import OperationalControllerConfigV2
from idx_trade.e2e_paper_orchestration_v1 import bootstrap_t0
from idx_trade import e2e_paper_preopen_ca_cloud_v1 as preopen_ca


CODE_SHA = "a" * 40
SCHEDULE_SHA = "b" * 64
INPUT_SHA = "c" * 64


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


def test_checkpoint_roundtrip_is_identity_bound_and_immutable(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "sentinel.txt").write_text("ca-ready\n", encoding="utf-8")
    snapshot, snapshot_sha, metadata = build_runtime_snapshot({"paper": runtime})
    result = {
        "schema_version": "idx_trade_e2e_paper_preopen_ca_result_v1",
        "session_date": "2026-08-28",
        "stage": preopen_ca.CHECKPOINT_STAGE,
        "controller_status": preopen_ca.CHECKPOINT_STATUS,
    }
    created = preopen_ca.commit_preopen_ca_checkpoint(
        store,
        session_date="2026-08-28",
        snapshot_bytes=snapshot,
        snapshot_metadata=metadata,
        result_payload=result,
        schedule_attestation_sha256=SCHEDULE_SHA,
        input_manifest_sha256=INPUT_SHA,
        code_identity={"commit": CODE_SHA},
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
    with pytest.raises(Exception, match="CODE_MISMATCH"):
        preopen_ca.load_preopen_ca_checkpoint(
            store,
            session_date="2026-08-28",
            expected_schedule_sha256=SCHEDULE_SHA,
            expected_input_manifest_sha256=INPUT_SHA,
            expected_code_commit="f" * 40,
        )


def test_existing_t0_stays_anchored_to_original_bootstrap_session(tmp_path: Path) -> None:
    root = tmp_path / "paper"
    first = bootstrap_t0(root, session_date="2026-08-27")
    first_bytes = first.read_bytes()
    replay = preopen_ca.validate_existing_t0_or_bootstrap(
        root,
        session_date="2026-08-28",
        original_bootstrap=bootstrap_t0,
    )
    assert replay == first
    assert replay.read_bytes() == first_bytes
    payload = json.loads(replay.read_text(encoding="utf-8"))
    assert payload["session_date"] == "2026-08-27"


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
        lambda *a, **k: SimpleNamespace(session_dates=("2026-08-27", "2026-08-28")),
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
        lambda *a, **k: SimpleNamespace(session_dates=("2026-08-27",)),
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
