from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from idx_trade.forward_price_trend_state import (
    ARTIFACT_FILENAME,
    MANIFEST_FILENAME,
    materialize_price_trend_state_for_session,
    produce_session_price_trend_state,
    verify_prospective_price_trend_state,
)
from idx_trade.provenance import sha256_file


def _history(periods: int = 80) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    sessions = pd.bdate_range("2025-01-02", periods=periods + 2)
    closes = np.full(periods, 100.0)
    frame = pd.DataFrame(
        {
            "ticker": "TEST",
            "date": sessions[:periods],
            "high": closes * 1.01,
            "low": closes * 0.99,
            "close": closes,
            "volume": 1_000_000.0,
        }
    )
    return frame, sessions


def _write_calendar(path: Path, sessions: pd.DatetimeIndex) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"date": sessions}).to_csv(path, index=False)
    return sha256_file(path)


def _write_canonical_session(
    runtime: Path,
    session: pd.Timestamp,
    forward_calendar: Path,
    *,
    close: float = 105.0,
    volume: float = 2_000_000.0,
) -> None:
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
            "volume": [volume],
            "regular_market_value": [10_000_000_000.0],
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
        "calendar_path": str(forward_calendar.resolve()),
        "calendar_sha256": sha256_file(forward_calendar),
    }
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _producer_fixture(tmp_path: Path) -> dict[str, object]:
    history, sessions = _history()
    historical_panel = tmp_path / "historical.parquet"
    history.to_parquet(historical_panel, index=False)
    historical_calendar = tmp_path / "historical_calendar.csv"
    historical_calendar_sha = _write_calendar(historical_calendar, sessions[: len(history)])
    forward_calendar = tmp_path / "forward_calendar.csv"
    forward_calendar_sha = _write_calendar(forward_calendar, sessions[len(history) :])
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    source = sessions[len(history)]
    target = sessions[len(history) + 1]
    _write_canonical_session(runtime, source, forward_calendar)
    return {
        "history": history,
        "sessions": sessions,
        "historical_panel": historical_panel,
        "historical_panel_sha": sha256_file(historical_panel),
        "historical_calendar": historical_calendar,
        "historical_calendar_sha": historical_calendar_sha,
        "forward_calendar": forward_calendar,
        "forward_calendar_sha": forward_calendar_sha,
        "runtime": runtime,
        "source": source,
        "target": target,
    }


def _produce(fixture: dict[str, object]) -> dict[str, object]:
    return produce_session_price_trend_state(
        runtime_root=fixture["runtime"],
        source_session=fixture["source"],
        historical_panel_path=fixture["historical_panel"],
        historical_panel_sha256=fixture["historical_panel_sha"],
        historical_calendar_path=fixture["historical_calendar"],
        historical_calendar_sha256=fixture["historical_calendar_sha"],
        forward_calendar_path=fixture["forward_calendar"],
        forward_calendar_sha256=fixture["forward_calendar_sha"],
    )


def test_producer_writes_t_plus_one_without_target_session_directory(tmp_path: Path) -> None:
    fixture = _producer_fixture(tmp_path)
    target_dir = (
        fixture["runtime"]
        / "forward_monitoring"
        / "sessions"
        / fixture["target"].date().isoformat()
    )
    assert not target_dir.exists()

    result = _produce(fixture)

    assert result["created"] is True
    assert result["source_session"] == fixture["source"].date().isoformat()
    assert result["feature_session"] == fixture["target"].date().isoformat()
    assert result["provider_calls"] == 0
    assert result["outcome_blind"] is True
    assert result["forward_outcomes_accessed"] is False
    assert not target_dir.exists()

    prospective = (
        fixture["runtime"]
        / "forward_monitoring"
        / "prospective"
        / "price_trend_confirmation_state_v1"
        / fixture["target"].date().isoformat()
    )
    artifact = pd.read_parquet(prospective / ARTIFACT_FILENAME)
    manifest = json.loads((prospective / MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert artifact["source_session"].eq(fixture["source"]).all()
    assert artifact["feature_session"].eq(fixture["target"]).all()
    assert artifact.iloc[0]["confirmation_state"] == "BREAKOUT_CONFIRMED"
    assert manifest["model_fit"] is False
    assert manifest["trade_recommendation"] is False
    assert verify_prospective_price_trend_state(fixture["runtime"], fixture["target"]) is True


def test_producer_is_idempotent_for_identical_context(tmp_path: Path) -> None:
    fixture = _producer_fixture(tmp_path)
    first = _produce(fixture)
    second = _produce(fixture)

    assert first["created"] is True
    assert second["created"] is False
    assert first["artifact_sha256"] == second["artifact_sha256"]
    assert first["manifest_sha256"] == second["manifest_sha256"]


def test_materializer_rejects_immutable_state_revision(tmp_path: Path) -> None:
    history, sessions = _history()
    source = sessions[len(history)]
    target = sessions[len(history) + 1]
    source_row = pd.DataFrame(
        {
            "ticker": ["TEST"],
            "session_date": [source],
            "raw_high": [106.05],
            "raw_low": [103.95],
            "raw_close": [105.0],
            "raw_volume": [2_000_000.0],
        }
    )
    market = pd.concat(
        [
            history.rename(
                columns={
                    "date": "session_date",
                    "high": "raw_high",
                    "low": "raw_low",
                    "close": "raw_close",
                    "volume": "raw_volume",
                }
            ),
            source_row,
        ],
        ignore_index=True,
    )
    output = tmp_path / "out"
    materialize_price_trend_state_for_session(
        market_history=market,
        official_sessions=sessions,
        source_session=source,
        output_directory=output,
        input_provenance={"fixture": "one"},
    )

    revised = market.copy()
    revised.loc[revised["session_date"].eq(source), "raw_close"] = 104.0
    revised.loc[revised["session_date"].eq(source), "raw_high"] = 105.04
    revised.loc[revised["session_date"].eq(source), "raw_low"] = 102.96
    with pytest.raises(RuntimeError, match="immutable price-state artifact revision conflict"):
        materialize_price_trend_state_for_session(
            market_history=revised,
            official_sessions=sessions,
            source_session=source,
            output_directory=output,
            input_provenance={"fixture": "one"},
        )


def test_verifier_fails_after_pinned_historical_input_changes(tmp_path: Path) -> None:
    fixture = _producer_fixture(tmp_path)
    _produce(fixture)
    assert verify_prospective_price_trend_state(fixture["runtime"], fixture["target"]) is True

    changed = pd.read_parquet(fixture["historical_panel"])
    changed.loc[0, "close"] = 99.0
    changed.loc[0, "high"] = 100.0
    changed.loc[0, "low"] = 98.0
    changed.to_parquet(fixture["historical_panel"], index=False)

    assert verify_prospective_price_trend_state(fixture["runtime"], fixture["target"]) is False


def test_source_must_exist_as_canonical_forward_session(tmp_path: Path) -> None:
    fixture = _producer_fixture(tmp_path)
    source_key = fixture["source"].date().isoformat()
    session_dir = fixture["runtime"] / "forward_monitoring" / "sessions" / source_key
    for path in session_dir.iterdir():
        path.unlink()
    session_dir.rmdir()

    with pytest.raises(RuntimeError, match="source session is not present"):
        _produce(fixture)


def test_canonical_snapshot_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    fixture = _producer_fixture(tmp_path)
    source_key = fixture["source"].date().isoformat()
    snapshot_path = fixture["runtime"] / "forward_monitoring" / "sessions" / source_key / "model_input.parquet"
    frame = pd.read_parquet(snapshot_path)
    frame.loc[0, "close"] = 104.0
    frame.loc[0, "high"] = 105.04
    frame.loc[0, "low"] = 102.96
    frame.to_parquet(snapshot_path, index=False)

    with pytest.raises(RuntimeError, match="snapshot hash mismatch"):
        _produce(fixture)


def test_outcome_like_historical_context_is_rejected(tmp_path: Path) -> None:
    fixture = _producer_fixture(tmp_path)
    history = pd.read_parquet(fixture["historical_panel"])
    history["binary_target"] = 1
    history.to_parquet(fixture["historical_panel"], index=False)
    fixture["historical_panel_sha"] = sha256_file(fixture["historical_panel"])

    with pytest.raises(ValueError, match="outcome-like"):
        _produce(fixture)


def test_forward_calendar_must_contain_next_session(tmp_path: Path) -> None:
    fixture = _producer_fixture(tmp_path)
    _write_calendar(fixture["forward_calendar"], pd.DatetimeIndex([fixture["source"]]))
    fixture["forward_calendar_sha"] = sha256_file(fixture["forward_calendar"])
    source_key = fixture["source"].date().isoformat()
    manifest_path = fixture["runtime"] / "forward_monitoring" / "sessions" / source_key / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["calendar_sha256"] = fixture["forward_calendar_sha"]
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with pytest.raises(RuntimeError, match="no next official session"):
        _produce(fixture)
