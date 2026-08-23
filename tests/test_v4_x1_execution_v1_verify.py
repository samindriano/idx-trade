import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.v4_x1_decision_v1_contract import DecisionV1Error
from idx_trade.v4_x1_execution_v1_verify import (
    verify_corporate_action_attestation,
    verify_eod_execution_inputs,
    verify_open_execution_inputs,
)


def _write_stub(path: Path, payload: bytes = b"stub") -> Path:
    path.write_bytes(payload)
    return path


def _calendar(path: Path) -> Path:
    path.write_text("date\n2026-08-20\n2026-08-21\n2026-08-24\n2026-08-25\n", encoding="utf-8")
    return path


def _eod_frames(close_aaa=1000.0):
    ohlcv = pd.DataFrame({
        "ticker": ["AAA", "BBB"],
        "session_date": pd.to_datetime(["2026-08-21", "2026-08-21"]),
        "close": [close_aaa, 2000.0],
    })
    model = pd.DataFrame({
        "ticker": ["AAA", "BBB"],
        "date": pd.to_datetime(["2026-08-21", "2026-08-21"]),
        "close": [1000.0, 2000.0],
        "regular_market_value": [1_000_000_000.0, 2_000_000_000.0],
    })
    return ohlcv, model


def test_eod_verifier_derives_immediate_next_official_session(monkeypatch, tmp_path):
    ohlcv_path = _write_stub(tmp_path / "session_ohlcv.parquet", b"eod")
    model_path = _write_stub(tmp_path / "model_input.parquet", b"model")
    calendar_path = _calendar(tmp_path / "calendar.csv")
    ohlcv, model = _eod_frames()

    def fake_read(path):
        return ohlcv.copy() if Path(path) == ohlcv_path else model.copy()

    monkeypatch.setattr(pd, "read_parquet", fake_read)
    verified = verify_eod_execution_inputs(
        session_ohlcv_path=ohlcv_path,
        model_input_path=model_path,
        official_calendar_path=calendar_path,
        decision_session_date="2026-08-21",
        required_tickers=["AAA", "BBB"],
    )
    assert verified.session_date == "2026-08-21"
    assert verified.next_official_session_date == "2026-08-24"
    assert verified.raw_close_prices == {"AAA": 1000.0, "BBB": 2000.0}
    assert verified.regular_market_values["AAA"] == 1_000_000_000.0
    assert verified.official_calendar_sha256 == hashlib.sha256(calendar_path.read_bytes()).hexdigest()


def test_eod_verifier_rejects_weekend_as_official_session(monkeypatch, tmp_path):
    ohlcv_path = _write_stub(tmp_path / "session_ohlcv.parquet", b"eod")
    model_path = _write_stub(tmp_path / "model_input.parquet", b"model")
    calendar_path = tmp_path / "calendar.csv"
    calendar_path.write_text(
        "date\n2026-08-21\n2026-08-22\n2026-08-24\n", encoding="utf-8"
    )
    ohlcv, model = _eod_frames()

    def fake_read(path):
        return ohlcv.copy() if Path(path) == ohlcv_path else model.copy()

    monkeypatch.setattr(pd, "read_parquet", fake_read)
    with pytest.raises(DecisionV1Error, match="WEEKEND_SESSION"):
        verify_eod_execution_inputs(
            session_ohlcv_path=ohlcv_path,
            model_input_path=model_path,
            official_calendar_path=calendar_path,
            decision_session_date="2026-08-21",
            required_tickers=["AAA", "BBB"],
        )


def test_eod_close_mismatch_fails_closed(monkeypatch, tmp_path):
    ohlcv_path = _write_stub(tmp_path / "session_ohlcv.parquet")
    model_path = _write_stub(tmp_path / "model_input.parquet")
    calendar_path = _calendar(tmp_path / "calendar.csv")
    ohlcv, model = _eod_frames(close_aaa=999.0)

    def fake_read(path):
        return ohlcv.copy() if Path(path) == ohlcv_path else model.copy()

    monkeypatch.setattr(pd, "read_parquet", fake_read)
    with pytest.raises(DecisionV1Error, match="CLOSE_PROVENANCE_MISMATCH"):
        verify_eod_execution_inputs(
            session_ohlcv_path=ohlcv_path,
            model_input_path=model_path,
            official_calendar_path=calendar_path,
            decision_session_date="2026-08-21",
            required_tickers=["AAA"],
        )


def test_open_verifier_rejects_generic_ohlcv_without_certified_manifest(tmp_path):
    path = _write_stub(tmp_path / "session_ohlcv.parquet", b"open")
    with pytest.raises(DecisionV1Error, match="OPEN_CERTIFIED_MANIFEST_REQUIRED"):
        verify_open_execution_inputs(
            session_ohlcv_path=path,
            execution_session_date="2026-08-24",
        )


def _write_ca(tmp_path: Path, *, rows, status="NO_RELEVANT_EVENTS", source_bytes=b"ca-source", declared_sha=None):
    source = tmp_path / "ca_source.csv"
    source.write_bytes(source_bytes)
    source_sha = hashlib.sha256(source_bytes).hexdigest()
    payload = {
        "schema_version": "v4_x1_paper_ca_attestation_v1",
        "from_session_date": "2026-08-21",
        "through_session_date": "2026-08-24",
        "status": status,
        "evidence_rows": rows,
        "source_path": str(source),
        "source_sha256": declared_sha or source_sha,
    }
    path = tmp_path / "ca_attestation.json"
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path, source, source_sha


def test_ca_attestation_accepts_only_hash_verified_no_event_coverage(tmp_path):
    path, source, source_sha = _write_ca(
        tmp_path,
        rows=[
            {"ticker": "AAA", "status": "NO_RELEVANT_EVENT"},
            {"ticker": "BBB", "status": "NO_RELEVANT_EVENT"},
        ],
    )
    verified = verify_corporate_action_attestation(
        attestation_path=path,
        expected_from_session_date="2026-08-21",
        expected_through_session_date="2026-08-24",
        required_tickers=["AAA", "BBB"],
    )
    assert verified.status == "NO_RELEVANT_EVENTS"
    assert verified.covered_tickers == frozenset({"AAA", "BBB"})
    assert verified.source_path == source
    assert verified.source_sha256 == source_sha


def test_ca_attestation_rejects_relevant_event(tmp_path):
    path, _, _ = _write_ca(
        tmp_path,
        status="RELEVANT_EVENT_PRESENT",
        rows=[{"ticker": "AAA", "status": "RELEVANT_EVENT"}],
    )
    with pytest.raises(DecisionV1Error, match="CA_RECONCILIATION_REQUIRED"):
        verify_corporate_action_attestation(
            attestation_path=path,
            expected_from_session_date="2026-08-21",
            expected_through_session_date="2026-08-24",
            required_tickers=["AAA"],
        )


def test_ca_attestation_rejects_incomplete_ticker_coverage(tmp_path):
    path, _, _ = _write_ca(
        tmp_path,
        rows=[{"ticker": "AAA", "status": "NO_RELEVANT_EVENT"}],
    )
    with pytest.raises(DecisionV1Error, match="CA_COVERAGE_INCOMPLETE"):
        verify_corporate_action_attestation(
            attestation_path=path,
            expected_from_session_date="2026-08-21",
            expected_through_session_date="2026-08-24",
            required_tickers=["AAA", "BBB"],
        )


def test_ca_attestation_rejects_source_hash_mismatch(tmp_path):
    path, _, _ = _write_ca(
        tmp_path,
        rows=[{"ticker": "AAA", "status": "NO_RELEVANT_EVENT"}],
        declared_sha="0" * 64,
    )
    with pytest.raises(DecisionV1Error, match="CA_SOURCE_SHA_MISMATCH"):
        verify_corporate_action_attestation(
            attestation_path=path,
            expected_from_session_date="2026-08-21",
            expected_through_session_date="2026-08-24",
            required_tickers=["AAA"],
        )
