from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from idx_trade.forward_price_trend_context_bridge import (
    BRIDGE_SCHEMA,
    BRIDGE_STATUS,
    RuntimeContextPins,
    _session_set_sha256,
    produce_price_trend_state_with_context_bridge,
    verify_price_trend_state_context_bridge_strict,
)
from idx_trade.provenance import sha256_file


def _calendar(path: Path, sessions: pd.DatetimeIndex) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"date": sessions}).to_csv(path, index=False)
    return sha256_file(path)


def _historical_panel(path: Path, sessions: pd.DatetimeIndex) -> str:
    closes = np.linspace(90.0, 100.0, len(sessions))
    frame = pd.DataFrame(
        {
            "ticker": "TEST",
            "date": sessions,
            "high": closes * 1.01,
            "low": closes * 0.99,
            "close": closes,
            "volume": 1_000_000.0,
            "regular_market_value": 10_000_000_000.0,
        }
    )
    frame.to_parquet(path, index=False)
    return sha256_file(path)


def _write_bridge_session(
    runtime: Path,
    session: pd.Timestamp,
    bridge_calendar: Path,
    *,
    close: float,
) -> Path:
    key = session.date().isoformat()
    directory = runtime / "forward_monitoring" / "context_bridge" / "sessions" / key
    directory.mkdir(parents=True, exist_ok=True)
    raw = {
        "recordsTotal": 1,
        "recordsFiltered": 1,
        "data": [{"StockCode": "TEST", "Date": key}],
    }
    raw_path = directory / "idx_stock_summary.raw.json"
    raw_path.write_text(json.dumps(raw), encoding="utf-8")
    market = pd.DataFrame(
        {
            "ticker": ["TEST"],
            "session_date": [session],
            "high": [close * 1.01],
            "low": [close * 0.99],
            "close": [close],
            "volume": [1_100_000.0],
            "regular_market_value": [10_500_000_000.0],
        }
    )
    market_path = directory / "market_context.parquet"
    market.to_parquet(market_path, index=False)
    flow = pd.DataFrame(
        {
            "security_code": ["TEST"],
            "session_date": [session],
            "unit": ["SHARES"],
            "foreign_buy": [100],
            "foreign_sell": [50],
            "foreign_net": [50],
        }
    )
    flow_path = directory / "foreign_flow.parquet"
    flow.to_parquet(flow_path, index=False)
    manifest = {
        "status": BRIDGE_STATUS,
        "schema": BRIDGE_SCHEMA,
        "bridge_only": True,
        "canonical_session_repair": False,
        "session_date": key,
        "calendar_path": str(bridge_calendar.resolve()),
        "calendar_sha256": sha256_file(bridge_calendar),
        "source_raw_path": str(raw_path.resolve()),
        "source_raw_sha256": sha256_file(raw_path),
        "market_context_path": str(market_path.resolve()),
        "market_context_sha256": sha256_file(market_path),
        "foreign_flow_path": str(flow_path.resolve()),
        "foreign_flow_sha256": sha256_file(flow_path),
        "stock_summary_source": {
            "records_total": 1,
            "row_count": 1,
            "completeness_status": "COMPLETE_RECORDS_TOTAL_SINGLE_RESPONSE",
        },
        "foreign_flow_rows": 1,
        "market_rows": 1,
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
        "outcomes_or_labels_accessed": False,
        "model_fit": False,
        "model_scoring": False,
    }
    manifest_path = directory / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def _write_canonical_session(
    runtime: Path,
    session: pd.Timestamp,
    operator_calendar: Path,
    *,
    close: float,
) -> Path:
    key = session.date().isoformat()
    directory = runtime / "forward_monitoring" / "sessions" / key
    directory.mkdir(parents=True, exist_ok=True)
    snapshot = pd.DataFrame(
        {
            "ticker": ["TEST"],
            "date": [session],
            "high": [close * 1.01],
            "low": [close * 0.99],
            "close": [close],
            "volume": [1_200_000.0],
            "regular_market_value": [11_000_000_000.0],
        }
    )
    snapshot_path = directory / "model_input.parquet"
    snapshot.to_parquet(snapshot_path, index=False)
    manifest = {
        "status": "DATA_READY",
        "session_date": key,
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
        "snapshot_path": str(snapshot_path.resolve()),
        "snapshot_sha256": sha256_file(snapshot_path),
        "calendar_path": str(operator_calendar.resolve()),
        "calendar_sha256": sha256_file(operator_calendar),
    }
    manifest_path = directory / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def _fixture(tmp_path: Path) -> dict[str, object]:
    # 80 historical observations are enough for the required MA50/swing/volume
    # axes; MA200 correctly remains optional/unavailable.
    historical_sessions = pd.bdate_range(end="2026-07-31", periods=80)
    bridge_sessions = pd.DatetimeIndex(
        [
            pd.Timestamp("2026-07-31"),
            pd.Timestamp("2026-08-03"),
            pd.Timestamp("2026-08-04"),
            pd.Timestamp("2026-08-05"),
            pd.Timestamp("2026-08-06"),
            pd.Timestamp("2026-08-07"),
            pd.Timestamp("2026-08-10"),
            pd.Timestamp("2026-08-11"),
            pd.Timestamp("2026-08-12"),
            pd.Timestamp("2026-08-13"),
        ]
    )
    historical_calendar = tmp_path / "historical_calendar.csv"
    bridge_calendar = tmp_path / "bridge_calendar.csv"
    historical_sha = _calendar(historical_calendar, historical_sessions)
    bridge_sha = _calendar(bridge_calendar, bridge_sessions)
    combined = pd.DatetimeIndex(list(historical_sessions) + list(bridge_sessions[1:]))

    historical_panel = tmp_path / "historical.parquet"
    panel_sha = _historical_panel(historical_panel, historical_sessions)
    runtime = tmp_path / "runtime"
    runtime.mkdir()

    bridge_dates = bridge_sessions[1:7]
    for index, day in enumerate(bridge_dates, start=1):
        _write_bridge_session(runtime, day, bridge_calendar, close=100.0 + index * 0.25)

    operator_calendar = tmp_path / "operator_calendar.csv"
    _calendar(
        operator_calendar,
        pd.DatetimeIndex(
            [pd.Timestamp("2026-08-10"), pd.Timestamp("2026-08-11"), pd.Timestamp("2026-08-12")]
        ),
    )
    _write_canonical_session(runtime, pd.Timestamp("2026-08-11"), operator_calendar, close=103.0)
    _write_canonical_session(runtime, pd.Timestamp("2026-08-12"), operator_calendar, close=105.0)

    pins = RuntimeContextPins(
        historical_panel_path=historical_panel,
        historical_panel_sha256=panel_sha,
        historical_calendar_path=historical_calendar,
        historical_calendar_sha256=historical_sha,
        bridge_calendar_path=bridge_calendar,
        bridge_calendar_sha256=bridge_sha,
        expected_combined_session_set_sha256=_session_set_sha256(combined),
    )
    return {
        "runtime": runtime,
        "pins": pins,
        "source": pd.Timestamp("2026-08-12"),
        "target": pd.Timestamp("2026-08-13"),
        "bridge_calendar": bridge_calendar,
        "operator_calendar": operator_calendar,
    }


def test_bridge_aware_producer_uses_bridge_then_canonical_without_target_dir(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    target_dir = fixture["runtime"] / "forward_monitoring" / "sessions" / "2026-08-13"
    assert not target_dir.exists()

    result = produce_price_trend_state_with_context_bridge(
        runtime_root=fixture["runtime"],
        source_session=fixture["source"],
        pins=fixture["pins"],
    )

    assert result["feature_session"] == "2026-08-13"
    assert result["provider_calls"] == 0
    assert result["outcome_blind"] is True
    assert result["runtime_context"]["source_kinds"] == [
        "BRIDGE_ONLY",
        "BRIDGE_ONLY",
        "BRIDGE_ONLY",
        "BRIDGE_ONLY",
        "BRIDGE_ONLY",
        "BRIDGE_ONLY",
        "CANONICAL_EOD",
        "CANONICAL_EOD",
    ]
    assert not target_dir.exists()
    assert verify_price_trend_state_context_bridge_strict(
        fixture["runtime"], fixture["target"], pins=fixture["pins"]
    ) is True


def test_missing_bridge_gap_session_fails_closed(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    missing_dir = fixture["runtime"] / "forward_monitoring" / "context_bridge" / "sessions" / "2026-08-05"
    for path in missing_dir.iterdir():
        path.unlink()
    missing_dir.rmdir()

    with pytest.raises(RuntimeError, match="MISSING_CONTEXT_SESSION"):
        produce_price_trend_state_with_context_bridge(
            runtime_root=fixture["runtime"],
            source_session=fixture["source"],
            pins=fixture["pins"],
        )


def test_valid_canonical_and_bridge_on_eligible_date_is_ambiguous(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    _write_canonical_session(
        fixture["runtime"],
        pd.Timestamp("2026-08-10"),
        fixture["operator_calendar"],
        close=102.0,
    )

    with pytest.raises(RuntimeError, match="AMBIGUOUS_CONTEXT_SOURCES"):
        produce_price_trend_state_with_context_bridge(
            runtime_root=fixture["runtime"],
            source_session=fixture["source"],
            pins=fixture["pins"],
        )


def test_post_monitor_session_cannot_use_bridge_fallback(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    canonical = fixture["runtime"] / "forward_monitoring" / "sessions" / "2026-08-11"
    for path in canonical.iterdir():
        path.unlink()
    canonical.rmdir()
    _write_bridge_session(
        fixture["runtime"],
        pd.Timestamp("2026-08-11"),
        fixture["bridge_calendar"],
        close=103.0,
    )

    with pytest.raises(RuntimeError, match="POST_MONITOR_SESSION_REQUIRES_CANONICAL_EOD"):
        produce_price_trend_state_with_context_bridge(
            runtime_root=fixture["runtime"],
            source_session=fixture["source"],
            pins=fixture["pins"],
        )


def test_strict_verifier_rejects_canonical_parent_semantic_tamper(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    result = produce_price_trend_state_with_context_bridge(
        runtime_root=fixture["runtime"], source_session=fixture["source"], pins=fixture["pins"]
    )
    assert verify_price_trend_state_context_bridge_strict(
        fixture["runtime"], fixture["target"], pins=fixture["pins"]
    ) is True

    parent = fixture["runtime"] / "forward_monitoring" / "sessions" / "2026-08-12" / "manifest.json"
    payload = json.loads(parent.read_text(encoding="utf-8"))
    payload["status"] = "DATA_FAILED"
    parent.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Tamper the stored provenance hashes/fingerprint consistently. Semantic
    # re-validation must still fail.
    manifest_path = Path(result["manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    provenance = manifest["input_provenance"]
    source_meta = provenance["extension_session_sources"][-1]
    source_meta["parent_manifest_sha256"] = sha256_file(parent)
    from idx_trade.forward_price_trend_state import _context_fingerprint

    provenance["input_fingerprint"] = _context_fingerprint(
        {key: value for key, value in provenance.items() if key != "input_fingerprint"}
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    assert verify_price_trend_state_context_bridge_strict(
        fixture["runtime"], fixture["target"], pins=fixture["pins"]
    ) is False


def test_strict_verifier_rejects_bridge_manifest_semantic_tamper(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    result = produce_price_trend_state_with_context_bridge(
        runtime_root=fixture["runtime"], source_session=fixture["source"], pins=fixture["pins"]
    )
    bridge_manifest = (
        fixture["runtime"]
        / "forward_monitoring"
        / "context_bridge"
        / "sessions"
        / "2026-08-03"
        / "manifest.json"
    )
    payload = json.loads(bridge_manifest.read_text(encoding="utf-8"))
    payload["canonical_session_repair"] = True
    bridge_manifest.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    manifest_path = Path(result["manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    provenance = manifest["input_provenance"]
    source_meta = provenance["extension_session_sources"][0]
    source_meta["manifest_sha256"] = sha256_file(bridge_manifest)
    from idx_trade.forward_price_trend_state import _context_fingerprint

    provenance["input_fingerprint"] = _context_fingerprint(
        {key: value for key, value in provenance.items() if key != "input_fingerprint"}
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    assert verify_price_trend_state_context_bridge_strict(
        fixture["runtime"], fixture["target"], pins=fixture["pins"]
    ) is False


def test_combined_session_set_pin_is_enforced(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    pins = fixture["pins"]
    wrong = RuntimeContextPins(
        historical_panel_path=pins.historical_panel_path,
        historical_panel_sha256=pins.historical_panel_sha256,
        historical_calendar_path=pins.historical_calendar_path,
        historical_calendar_sha256=pins.historical_calendar_sha256,
        bridge_calendar_path=pins.bridge_calendar_path,
        bridge_calendar_sha256=pins.bridge_calendar_sha256,
        expected_combined_session_set_sha256="0" * 64,
    )
    with pytest.raises(RuntimeError, match="combined official session-set hash mismatch"):
        produce_price_trend_state_with_context_bridge(
            runtime_root=fixture["runtime"], source_session=fixture["source"], pins=wrong
        )
