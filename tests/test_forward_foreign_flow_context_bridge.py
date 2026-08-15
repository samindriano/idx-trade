from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

import idx_trade.forward_foreign_flow_context_bridge as bridge
import idx_trade.forward_foreign_flow_context_bridge_run as bridge_run
from idx_trade.provenance import sha256_file


def test_bridge_calendar_is_separate_from_operator_calendar_and_idempotent(tmp_path: Path) -> None:
    operator = tmp_path / "forward_monitoring" / "calendar" / "exchange_sessions.csv"
    operator.parent.mkdir(parents=True)
    operator.write_text("date\n2026-08-10\n2026-08-11\n", encoding="utf-8")
    operator_before = operator.read_bytes()

    def fake_month(year: int, month: int) -> pd.DatetimeIndex:
        assert (year, month) == (2026, 8)
        return pd.DatetimeIndex(
            pd.to_datetime(["2026-08-03", "2026-08-04", "2026-08-05", "2026-08-06", "2026-08-07", "2026-08-10"])
        )

    first = bridge.sync_context_bridge_calendar(
        tmp_path,
        "2026-08-01",
        "2026-08-10",
        fetch_month=fake_month,
    )
    second = bridge.sync_context_bridge_calendar(
        tmp_path,
        "2026-08-01",
        "2026-08-10",
        fetch_month=fake_month,
    )

    assert first["status"] == second["status"] == "BRIDGE_CALENDAR_READY"
    assert first["created"] is True
    assert second["created"] is False
    assert Path(first["calendar_path"]).parent != operator.parent
    assert operator.read_bytes() == operator_before
    assert first["calendar_sha256"] == second["calendar_sha256"]


def _market(day: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "BBCA",
                "session_date": day,
                "high": 101.0,
                "low": 99.0,
                "close": 100.0,
                "volume": 1_000_000.0,
                "regular_market_value": 10_000_000_000.0,
            }
        ]
    )


def _flow(day: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "security_code": "BBCA",
                "session_date": day,
                "unit": "SHARES",
                "foreign_buy": 1_000,
                "foreign_sell": 700,
                "foreign_net": 300,
                "knowledge_at_utc": "2026-08-10T11:00:00+00:00",
                "source": "IDX_OFFICIAL_STOCK_SUMMARY",
                "source_ref": "https://www.idx.id/",
                "source_sha256": "a" * 64,
            }
        ]
    )


def _calendar(tmp_path: Path) -> tuple[Path, str]:
    path = tmp_path / "calendar.csv"
    path.write_text("date\n2026-08-07\n2026-08-10\n2026-08-11\n", encoding="utf-8")
    return path.resolve(), sha256_file(path)


def test_resolver_uses_verified_bridge_without_repairing_invalid_canonical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    day = pd.Timestamp("2026-08-10")
    canonical = tmp_path / "forward_monitoring" / "sessions" / "2026-08-10"
    canonical.mkdir(parents=True)
    calendar, calendar_sha = _calendar(tmp_path)

    monkeypatch.setattr(
        bridge_run,
        "_read_verified_forward_market",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("partial canonical")),
    )
    monkeypatch.setattr(bridge_run, "verify_context_bridge_session", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        bridge_run,
        "load_context_bridge_session",
        lambda *_args, **_kwargs: (
            _market("2026-08-10"),
            _flow("2026-08-10"),
            {"kind": "BRIDGE_ONLY", "canonical_session_repair": False},
        ),
    )

    market, flow, meta = bridge_run._resolve_extension_session(
        tmp_path,
        day,
        calendar_path=calendar,
        calendar_sha256=calendar_sha,
    )

    assert len(market) == len(flow) == 1
    assert meta["kind"] == "BRIDGE_ONLY"
    assert meta["canonical_directory_present"] is True
    assert "partial canonical" in str(meta["canonical_validation_error"])
    assert meta["canonical_session_repair"] is False


def test_resolver_rejects_two_valid_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    day = pd.Timestamp("2026-08-10")
    (tmp_path / "forward_monitoring" / "sessions" / "2026-08-10").mkdir(parents=True)
    calendar, calendar_sha = _calendar(tmp_path)
    monkeypatch.setattr(bridge_run, "_read_verified_forward_market", lambda *_a, **_k: (_market("2026-08-10"), {}))
    monkeypatch.setattr(bridge_run, "_read_verified_forward_flow", lambda *_a, **_k: (_flow("2026-08-10").rename(columns={"security_code": "ticker"}), {}))
    monkeypatch.setattr(bridge_run, "verify_context_bridge_session", lambda *_a, **_k: True)

    with pytest.raises(RuntimeError, match="AMBIGUOUS_CONTEXT_SOURCES"):
        bridge_run._resolve_extension_session(
            tmp_path,
            day,
            calendar_path=calendar,
            calendar_sha256=calendar_sha,
        )


def test_bridge_adapter_keeps_operator_counter_out_of_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    historical_calendar = tmp_path / "historical-calendar.csv"
    historical_calendar.write_text("date\n2026-07-30\n2026-07-31\n", encoding="utf-8")
    bridge_calendar = tmp_path / "bridge-calendar.csv"
    bridge_calendar.write_text("date\n2026-07-31\n2026-08-03\n2026-08-04\n", encoding="utf-8")
    panel = pd.DataFrame(
        [
            {
                "ticker": "BBCA",
                "date": "2026-07-31",
                "high": 101.0,
                "low": 99.0,
                "close": 100.0,
                "volume": 1_000_000.0,
                "regular_market_value": 10_000_000_000.0,
            }
        ]
    )
    panel_path = tmp_path / "panel.parquet"
    panel.to_parquet(panel_path, index=False)
    master = tmp_path / "master.csv"
    pd.DataFrame([{"ticker": "BBCA", "listed_from": "2020-01-01", "listed_to": ""}]).to_csv(master, index=False)
    archive = tmp_path / "archive"
    archive.mkdir()
    archive_flow = _flow("2026-07-31")

    monkeypatch.setattr(
        bridge_run,
        "read_verified_flow_archive",
        lambda *_a, **_k: (
            archive_flow,
            {
                "archive_root": str(archive),
                "archive_manifest_path": str(archive / "manifest.json"),
                "archive_manifest_sha256": "a" * 64,
                "archive_normalized_session_count": 1,
                "archive_normalized_row_count": 1,
                "archive_normalized_artifact_count": 1,
                "archive_normalized_first_session": "2026-07-31",
                "archive_normalized_last_session": "2026-07-31",
            },
        ),
    )
    monkeypatch.setattr(
        bridge_run,
        "_resolve_extension_session",
        lambda *_a, **_k: (
            _market("2026-08-03"),
            _flow("2026-08-03"),
            {"kind": "BRIDGE_ONLY", "canonical_session_repair": False},
        ),
    )

    captured: dict[str, object] = {}

    def fake_materialize(**kwargs):
        captured.update(kwargs)
        output = Path(kwargs["output_directory"])
        output.mkdir(parents=True, exist_ok=True)
        artifact = output / "foreign_flow_representation_v2.parquet"
        manifest = output / "foreign_flow_representation_v2.manifest.json"
        pd.DataFrame([{"ticker": "BBCA"}]).to_parquet(artifact, index=False)
        manifest.write_text(json.dumps({"stub": True}), encoding="utf-8")
        return {"artifact_path": str(artifact), "manifest_path": str(manifest)}

    monkeypatch.setattr(bridge_run, "materialize_representation_v2_for_session", fake_materialize)
    monkeypatch.setattr(
        bridge_run,
        "enrich_prospective_foreign_flow_setup",
        lambda *_a, **_k: {"status": "FOREIGN_FLOW_SETUP_STATE_PROSPECTIVE_READY"},
    )

    result = bridge_run.produce_with_context_bridge(
        runtime_root=runtime,
        source_session="2026-08-03",
        archive_root=archive,
        archive_manifest_sha256="a" * 64,
        historical_panel_path=panel_path,
        historical_panel_sha256=sha256_file(panel_path),
        historical_sessions_path=historical_calendar,
        historical_sessions_sha256=sha256_file(historical_calendar),
        bridge_sessions_path=bridge_calendar,
        bridge_sessions_sha256=sha256_file(bridge_calendar),
        security_master_path=master,
        security_master_sha256=sha256_file(master),
    )

    provenance = captured["input_provenance"]
    assert provenance["operator_calendar_mutated"] is False
    assert provenance["operator_counter_modified"] is False
    assert provenance["canonical_session_repair"] is False
    assert provenance["historical_sessions_path"] == str(historical_calendar.resolve())
    assert provenance["bridge_sessions_path"] == str(bridge_calendar.resolve())
    assert provenance["official_sessions_path"] == str(bridge_calendar.resolve())
    assert len(provenance["combined_session_set_sha256"]) == 64
    assert captured["official_sessions"][-1] == pd.Timestamp("2026-08-04")
    assert result["context_bridge"]["operator_counter_modified"] is False
    assert result["prospective_setup_state"]["status"] == "FOREIGN_FLOW_SETUP_STATE_PROSPECTIVE_READY"


def test_combined_calendar_rejects_non_seam_overlap() -> None:
    historical = pd.DatetimeIndex(pd.to_datetime(["2026-07-30", "2026-07-31"]))
    bridge = pd.DatetimeIndex(pd.to_datetime(["2026-07-31", "2026-08-03", "2026-07-30"]))
    with pytest.raises(RuntimeError, match="duplicated|overlap|out of order"):
        bridge_run._combined_session_index(
            historical,
            bridge,
            historical_cutoff=pd.Timestamp("2026-07-31"),
            source_session=pd.Timestamp("2026-08-03"),
        )


def test_combined_calendar_requires_exact_seam_and_source_target() -> None:
    historical = pd.DatetimeIndex(pd.to_datetime(["2026-07-30", "2026-07-31"]))
    with pytest.raises(RuntimeError, match="seam"):
        bridge_run._combined_session_index(
            historical,
            pd.DatetimeIndex(pd.to_datetime(["2026-08-03", "2026-08-04"])),
            historical_cutoff=pd.Timestamp("2026-07-31"),
            source_session=pd.Timestamp("2026-08-03"),
        )
    with pytest.raises(RuntimeError, match="source"):
        bridge_run._combined_session_index(
            historical,
            pd.DatetimeIndex(pd.to_datetime(["2026-07-31", "2026-08-03"])),
            historical_cutoff=pd.Timestamp("2026-07-31"),
            source_session=pd.Timestamp("2026-08-03"),
        )


def test_source_0812_materializes_target_0813_without_target_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real seam case must not inspect any target-session directory/data."""

    runtime = tmp_path / "runtime"
    runtime.mkdir()
    historical_calendar = tmp_path / "historical-calendar.csv"
    historical_calendar.write_text("date\n2026-07-30\n2026-07-31\n", encoding="utf-8")
    bridge_calendar = tmp_path / "bridge-calendar.csv"
    bridge_calendar.write_text(
        "date\n2026-07-31\n2026-08-03\n2026-08-04\n2026-08-05\n2026-08-06\n2026-08-07\n2026-08-10\n2026-08-11\n2026-08-12\n2026-08-13\n",
        encoding="utf-8",
    )
    panel = pd.DataFrame(
        [
            {
                "ticker": "BBCA",
                "date": "2026-07-31",
                "high": 101.0,
                "low": 99.0,
                "close": 100.0,
                "volume": 1_000_000.0,
                "regular_market_value": 10_000_000_000.0,
            }
        ]
    )
    panel_path = tmp_path / "panel.parquet"
    panel.to_parquet(panel_path, index=False)
    master = tmp_path / "master.csv"
    pd.DataFrame([{"ticker": "BBCA", "listed_from": "2020-01-01", "listed_to": ""}]).to_csv(
        master, index=False
    )
    archive = tmp_path / "archive"
    archive.mkdir()

    monkeypatch.setattr(
        bridge_run,
        "read_verified_flow_archive",
        lambda *_a, **_k: (
            _flow("2026-07-31"),
            {
                "archive_root": str(archive),
                "archive_manifest_path": str(archive / "manifest.json"),
                "archive_manifest_sha256": "a" * 64,
                "archive_normalized_session_count": 1,
                "archive_normalized_row_count": 1,
                "archive_normalized_artifact_count": 1,
                "archive_normalized_first_session": "2026-07-31",
                "archive_normalized_last_session": "2026-07-31",
            },
        ),
    )
    requested: list[str] = []

    def fake_resolve(*_args, **kwargs):
        day = pd.Timestamp(_args[1]).date().isoformat()
        requested.append(day)
        assert kwargs["calendar_path"] == bridge_calendar.resolve()
        assert kwargs["calendar_sha256"] == sha256_file(bridge_calendar)
        return _market(day), _flow(day), {"kind": "BRIDGE_ONLY", "canonical_session_repair": False}

    monkeypatch.setattr(bridge_run, "_resolve_extension_session", fake_resolve)
    captured: dict[str, object] = {}

    def fake_materialize(**kwargs):
        captured.update(kwargs)
        assert kwargs["official_sessions"][-2:].equals(
            pd.DatetimeIndex(pd.to_datetime(["2026-08-12", "2026-08-13"]))
        )
        output = Path(kwargs["output_directory"])
        output.mkdir(parents=True, exist_ok=True)
        artifact = output / "foreign_flow_representation_v2.parquet"
        manifest = output / "foreign_flow_representation_v2.manifest.json"
        pd.DataFrame([{"ticker": "BBCA"}]).to_parquet(artifact, index=False)
        manifest.write_text(json.dumps({"stub": True}), encoding="utf-8")
        return {"artifact_path": str(artifact), "manifest_path": str(manifest)}

    monkeypatch.setattr(bridge_run, "materialize_representation_v2_for_session", fake_materialize)
    monkeypatch.setattr(
        bridge_run,
        "enrich_prospective_foreign_flow_setup",
        lambda *_a, **_k: {"status": "FOREIGN_FLOW_SETUP_STATE_PROSPECTIVE_READY"},
    )

    result = bridge_run.produce_with_context_bridge(
        runtime_root=runtime,
        source_session="2026-08-12",
        archive_root=archive,
        archive_manifest_sha256="a" * 64,
        historical_panel_path=panel_path,
        historical_panel_sha256=sha256_file(panel_path),
        historical_sessions_path=historical_calendar,
        historical_sessions_sha256=sha256_file(historical_calendar),
        bridge_sessions_path=bridge_calendar,
        bridge_sessions_sha256=sha256_file(bridge_calendar),
        security_master_path=master,
        security_master_sha256=sha256_file(master),
    )

    assert requested == ["2026-08-03", "2026-08-04", "2026-08-05", "2026-08-06", "2026-08-07", "2026-08-10", "2026-08-11", "2026-08-12"]
    provenance = captured["input_provenance"]
    assert provenance["source_session"] == "2026-08-12"
    assert provenance["feature_session"] == "2026-08-13"
    assert provenance["historical_sessions_sha256"] == sha256_file(historical_calendar)
    assert provenance["bridge_sessions_sha256"] == sha256_file(bridge_calendar)
    assert provenance["combined_session_count"] == 11
    assert result["context_bridge"]["combined_session_count"] == 11
