from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

import idx_trade.forward_price_trend_context_bridge as bridge_module
from idx_trade.canonical_eod_calendar_parent_attestation import (
    CALENDAR_BYTES_UNRECOVERED,
    audit_canonical_eod_calendar_parent,
    create_canonical_eod_calendar_parent_attestation,
    verify_canonical_eod_calendar_parent_attestation,
)
from idx_trade.forward_price_trend_context_bridge import _read_verified_canonical_market
from idx_trade.provenance import sha256_file


def _calendar(path: Path, sessions: list[str]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"date": sessions}).to_csv(path, index=False)
    return sha256_file(path)


def _canonical_session(runtime: Path, session: str, calendar: Path, calendar_sha: str) -> Path:
    directory = runtime / "forward_monitoring" / "sessions" / session
    directory.mkdir(parents=True, exist_ok=True)
    snapshot = directory / "model_input.parquet"
    pd.DataFrame(
        {
            "ticker": ["TEST"],
            "date": [pd.Timestamp(session)],
            "high": [101.0],
            "low": [99.0],
            "close": [100.0],
            "volume": [1000.0],
            "regular_market_value": [100000.0],
        }
    ).to_parquet(snapshot, index=False)
    evidence = directory / "session_evidence.parquet"
    pd.DataFrame(
        {
            "ticker": ["TEST"],
            "session_date": [pd.Timestamp(session)],
            "point_state": ["ACTIVE"],
        }
    ).to_parquet(evidence, index=False)
    manifest = {
        "status": "DATA_READY",
        "session_date": session,
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
        "snapshot_path": str(snapshot.resolve()),
        "snapshot_sha256": sha256_file(snapshot),
        "evidence_path": str(evidence.resolve()),
        "evidence_sha256": sha256_file(evidence),
        "calendar_path": str(calendar.resolve()),
        "calendar_sha256": calendar_sha,
    }
    manifest_path = directory / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def _fixture(tmp_path: Path) -> dict[str, object]:
    runtime = tmp_path / "runtime"
    current_calendar = runtime / "forward_monitoring" / "calendar" / "exchange_sessions.csv"
    current_sha = _calendar(current_calendar, ["2026-08-10", "2026-08-11", "2026-08-12"])
    old_calendar = tmp_path / "lost-capture-calendar.csv"
    old_sha = _calendar(old_calendar, ["2026-08-10", "2026-08-11"])
    old_calendar.unlink()
    bridge_calendar = tmp_path / "bridge-calendar.csv"
    bridge_sha = _calendar(
        bridge_calendar,
        ["2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13"],
    )
    manifest_11 = _canonical_session(runtime, "2026-08-11", current_calendar, old_sha)
    manifest_12 = _canonical_session(runtime, "2026-08-12", current_calendar, current_sha)
    return {
        "runtime": runtime,
        "current_calendar": current_calendar,
        "old_sha": old_sha,
        "bridge_calendar": bridge_calendar,
        "bridge_sha": bridge_sha,
        "manifest_11": manifest_11,
        "manifest_12": manifest_12,
    }


def _audit_11(fixture: dict[str, object]) -> dict[str, object]:
    return audit_canonical_eod_calendar_parent(
        runtime_root=fixture["runtime"],
        session="2026-08-11",
        accepted_bridge_calendar_path=fixture["bridge_calendar"],
        accepted_bridge_calendar_sha256=fixture["bridge_sha"],
    )


def _write_attestation(fixture: dict[str, object]) -> Path:
    return create_canonical_eod_calendar_parent_attestation(
        report=_audit_11(fixture),
        output_path=(
            fixture["runtime"]
            / "forward_monitoring"
            / "provenance_attestations"
            / "canonical_eod_calendar_parent_v1"
            / "2026-08-11"
            / "attestation.json"
        ),
    )


def test_both_canonical_sessions_are_audited_and_only_lost_parent_needs_attestation(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    report_11 = _audit_11(fixture)
    report_12 = audit_canonical_eod_calendar_parent(
        runtime_root=fixture["runtime"],
        session="2026-08-12",
        accepted_bridge_calendar_path=fixture["bridge_calendar"],
        accepted_bridge_calendar_sha256=fixture["bridge_sha"],
    )
    assert report_11["declared_capture_time_calendar_status"] == CALENDAR_BYTES_UNRECOVERED
    assert report_11["declared_capture_time_calendar_bytes_recovered"] is False
    assert report_12["declared_capture_time_calendar_status"] == "RECOVERED"
    assert report_12["declared_capture_time_calendar_bytes_recovered"] is True
    assert report_11["predecessor_session"] == "2026-08-10"
    assert report_11["successor_session"] == "2026-08-12"
    assert report_12["predecessor_session"] == "2026-08-11"
    assert report_12["successor_session"] == "2026-08-13"


def test_attestation_is_strict_and_immutable(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    attestation = _write_attestation(fixture)
    assert verify_canonical_eod_calendar_parent_attestation(
        attestation,
        expected_session="2026-08-11",
        expected_bridge_calendar_path=fixture["bridge_calendar"],
        expected_bridge_calendar_sha256=fixture["bridge_sha"],
    ) is True
    assert _write_attestation(fixture) == attestation
    changed_report = dict(_audit_11(fixture))
    changed_report["canonical_manifest_sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="immutable"):
        create_canonical_eod_calendar_parent_attestation(
            report=changed_report,
            output_path=attestation,
        )


def test_current_mutable_calendar_cannot_substitute_old_parent(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    attestation = _write_attestation(fixture)
    fixture["current_calendar"].write_text("date\n2026-08-10\n2026-08-11\n", encoding="utf-8")
    assert verify_canonical_eod_calendar_parent_attestation(
        attestation,
        expected_bridge_calendar_path=fixture["bridge_calendar"],
        expected_bridge_calendar_sha256=fixture["bridge_sha"],
    ) is False


def test_arbitrary_bridge_and_wrong_order_are_rejected(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    arbitrary = tmp_path / "arbitrary.csv"
    arbitrary_sha = _calendar(arbitrary, ["2026-08-10", "2026-08-13", "2026-08-11"])
    with pytest.raises(RuntimeError, match="unordered|ordering proof"):
        audit_canonical_eod_calendar_parent(
            runtime_root=fixture["runtime"],
            session="2026-08-11",
            accepted_bridge_calendar_path=arbitrary,
            accepted_bridge_calendar_sha256=arbitrary_sha,
        )
    with pytest.raises(RuntimeError, match="hash-mismatched"):
        audit_canonical_eod_calendar_parent(
            runtime_root=fixture["runtime"],
            session="2026-08-11",
            accepted_bridge_calendar_path=fixture["bridge_calendar"],
            accepted_bridge_calendar_sha256="0" * 64,
        )


def test_tampered_manifest_snapshot_or_declared_sha_cannot_be_rescued(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    attestation = _write_attestation(fixture)
    manifest = Path(fixture["manifest_11"])
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["status"] = "DATA_FAILED"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    assert verify_canonical_eod_calendar_parent_attestation(
        attestation,
        expected_bridge_calendar_path=fixture["bridge_calendar"],
        expected_bridge_calendar_sha256=fixture["bridge_sha"],
    ) is False

    fixture = _fixture(tmp_path / "snapshot")
    attestation = _write_attestation(fixture)
    snapshot = Path(json.loads(Path(fixture["manifest_11"]).read_text())["snapshot_path"])
    snapshot.write_bytes(snapshot.read_bytes() + b"tamper")
    assert verify_canonical_eod_calendar_parent_attestation(
        attestation,
        expected_bridge_calendar_path=fixture["bridge_calendar"],
        expected_bridge_calendar_sha256=fixture["bridge_sha"],
    ) is False

    fixture = _fixture(tmp_path / "evidence")
    attestation = _write_attestation(fixture)
    evidence = Path(json.loads(Path(fixture["manifest_11"]).read_text())["evidence_path"])
    evidence.write_bytes(evidence.read_bytes() + b"tamper")
    assert verify_canonical_eod_calendar_parent_attestation(
        attestation,
        expected_bridge_calendar_path=fixture["bridge_calendar"],
        expected_bridge_calendar_sha256=fixture["bridge_sha"],
    ) is False


def test_declared_old_sha_change_and_missing_attestation_fail_closed(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    assert verify_canonical_eod_calendar_parent_attestation(
        fixture["runtime"]
        / "forward_monitoring"
        / "provenance_attestations"
        / "canonical_eod_calendar_parent_v1"
        / "2026-08-11"
        / "attestation.json",
        expected_bridge_calendar_path=fixture["bridge_calendar"],
        expected_bridge_calendar_sha256=fixture["bridge_sha"],
    ) is False
    with pytest.raises(RuntimeError, match="calendar missing or hash-mismatched"):
        _read_verified_canonical_market(fixture["runtime"], pd.Timestamp("2026-08-11"))

    attestation = _write_attestation(fixture)
    manifest = Path(fixture["manifest_11"])
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["calendar_sha256"] = "f" * 64
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    assert verify_canonical_eod_calendar_parent_attestation(
        attestation,
        expected_bridge_calendar_path=fixture["bridge_calendar"],
        expected_bridge_calendar_sha256=fixture["bridge_sha"],
    ) is False


def test_price_trend_parent_path_accepts_only_verified_attestation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    attestation = _write_attestation(fixture)
    monkeypatch.setattr(bridge_module, "APPROVED_BRIDGE_CALENDAR", str(fixture["bridge_calendar"]))
    monkeypatch.setattr(bridge_module, "ACCEPTED_BRIDGE_CALENDAR_SHA256", fixture["bridge_sha"])
    assert bridge_module._read_verified_canonical_market(
        fixture["runtime"], pd.Timestamp("2026-08-11")
    )[1]["calendar_parent_attestation_path"] == str(attestation)
