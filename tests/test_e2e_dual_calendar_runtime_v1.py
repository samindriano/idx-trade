import hashlib
import json
import py_compile
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from idx_trade import official_trading_schedule_v1 as schedule_module
from idx_trade.e2e_paper_operational_controller_v1 import OperationalControllerConfig
from idx_trade.e2e_paper_operational_controller_v2 import (
    OperationalControllerConfigV2,
    run_operational_cycle_v2,
)
from idx_trade.e2e_paper_runtime_config_v2 import load_runtime_config_v2
from idx_trade.official_trading_schedule_v1 import (
    AUTHORITY,
    DERIVATION,
    SCHEMA_VERSION,
    SEMANTICS,
    derive_planned_sessions,
)


JAKARTA = ZoneInfo("Asia/Jakarta")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_schedule(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    source = root / "official_source.pdf"
    source.write_bytes(b"official schedule fixture")
    sessions = derive_planned_sessions(
        coverage_start="2026-08-24",
        coverage_end="2026-08-28",
        holiday_dates=["2026-08-25"],
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "authority": AUTHORITY,
        "semantics": SEMANTICS,
        "derivation": DERIVATION,
        "source_reference": "IDX_TEST_OFFICIAL_CALENDAR",
        "source_document_path": source.name,
        "source_document_sha256": _sha256(source),
        "coverage_start": "2026-08-24",
        "coverage_end": "2026-08-28",
        "holiday_dates": ["2026-08-25"],
        "session_dates": list(sessions),
        "outcome_access": False,
    }
    payload["payload_sha256"] = schedule_module._canonical_hash(payload)
    attestation = root / "execution_schedule_attestation.json"
    attestation.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    return attestation, _sha256(attestation)


def _base_config(tmp_path: Path, observed: Path):
    return OperationalControllerConfig(
        runtime_root=tmp_path / "paper",
        forward_runtime_root=tmp_path / "forward",
        calendar_path=observed,
        official_open_root=tmp_path / "paper" / "official_open",
        repo_root=tmp_path / "repo",
        expected_branch="test-branch",
        expected_commit="1" * 40,
    )


def test_controller_uses_planned_schedule_for_holiday_and_next_trading_day(tmp_path, monkeypatch):
    observed = tmp_path / "exchange_sessions.csv"
    observed.write_text("date\n2026-08-24\n", encoding="utf-8")
    attestation, attestation_sha = _write_schedule(tmp_path / "schedule")
    config = OperationalControllerConfigV2(
        base=_base_config(tmp_path, observed),
        execution_schedule_attestation_path=attestation,
        execution_schedule_attestation_sha256=attestation_sha,
    )

    monkeypatch.setattr(
        "idx_trade.e2e_paper_operational_controller_v2.attest_deployment",
        lambda *args, **kwargs: SimpleNamespace(
            repo_root=config.repo_root,
            branch=config.expected_branch,
            head=config.expected_commit,
            expected_commit=config.expected_commit,
            clean=True,
        ),
    )

    holiday = run_operational_cycle_v2(
        config, now=datetime(2026, 8, 25, 9, 7, tzinfo=JAKARTA)
    )
    assert holiday["controller_status"] == "WEEKEND_OR_HOLIDAY_NOOP"

    next_session = run_operational_cycle_v2(
        config, now=datetime(2026, 8, 26, 8, 45, tzinfo=JAKARTA)
    )
    assert next_session["controller_status"] == "WAITING_PREPARED_EXECUTION"
    assert next_session["execution_session_date"] == "2026-08-26"


def test_runtime_config_v2_requires_and_verifies_schedule(tmp_path):
    attestation, attestation_sha = _write_schedule(tmp_path / "schedule")
    operational = tmp_path / "runtime" / "operational"
    operational.mkdir(parents=True)
    payload = {
        "schema_version": "idx_trade_e2e_paper_runtime_config_v1",
        "operational_contract_version": "DUAL_CALENDAR_V1",
        "forward_runtime_root": str((tmp_path / "forward").resolve()),
        "calendar_path": str((tmp_path / "calendar.csv").resolve()),
        "execution_schedule_attestation_path": str(attestation.resolve()),
        "execution_schedule_attestation_sha256": attestation_sha,
        "official_open_root": str((tmp_path / "open").resolve()),
        "repo_root": str((tmp_path / "repo").resolve()),
        "expected_branch": "test-branch",
        "expected_commit": "1" * 40,
        "provider_checkout": str((tmp_path / "provider").resolve()),
        "provider_expected_commit": "2" * 40,
        "uv_exe": str((tmp_path / "uv.exe").resolve()),
        "python_exe": str((tmp_path / "python.exe").resolve()),
        "ca_attestation_path": str((tmp_path / "ca.json").resolve()),
        "ca_attestation_sha256": "3" * 64,
        "preopen_capture_start": "08:30",
        "runner_sha256": "4" * 64,
    }
    config_path = operational / "config.json"
    config_path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    digest = _sha256(config_path)
    (operational / "config.json.sha256").write_text(digest + "\n")

    loaded = load_runtime_config_v2(tmp_path / "runtime", expected_sha256=digest)
    assert loaded.controller.calendar_path == (tmp_path / "calendar.csv").resolve()
    assert loaded.controller.execution_schedule_attestation_path == attestation.resolve()
    assert loaded.controller.execution_schedule_attestation_sha256 == attestation_sha


def test_new_python_entrypoints_compile():
    root = Path(__file__).resolve().parents[1]
    paths = [
        root / "scripts" / "build_official_trading_schedule_v1.py",
        root / "scripts" / "run_e2e_paper_post_eod_v2.py",
        root / "scripts" / "run_e2e_paper_preopen_v2.py",
        root / "scripts" / "run_e2e_paper_scheduled_v2.py",
    ]
    for path in paths:
        py_compile.compile(str(path), doraise=True)
