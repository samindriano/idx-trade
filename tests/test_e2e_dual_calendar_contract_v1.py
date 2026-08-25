import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from idx_trade import official_trading_schedule_v1 as schedule_module
from idx_trade.official_open_capture_runtime_v2 import (
    STATUS_ALREADY_CAPTURED,
    STATUS_CAPTURED,
    STATUS_HOLIDAY_NO_SESSION,
    STATUS_PARTIAL_EVIDENCE_FAIL_CLOSED,
    run_same_session_official_open_capture_v2,
)
from idx_trade.official_trading_schedule_v1 import (
    AUTHORITY,
    DERIVATION,
    SCHEMA_VERSION,
    SEMANTICS,
    OfficialTradingScheduleError,
    derive_planned_sessions,
    load_verified_official_trading_schedule,
    next_planned_session,
)
from idx_trade.v4_x1_execution_v1_verify_schedule_v1 import (
    verify_eod_execution_inputs_with_schedule,
)


JAKARTA = ZoneInfo("Asia/Jakarta")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_schedule(
    root: Path,
    *,
    coverage_start="2026-08-24",
    coverage_end="2026-08-28",
    holidays=("2026-08-25",),
):
    root.mkdir(parents=True, exist_ok=True)
    source = root / "official_source.pdf"
    source.write_bytes(b"synthetic official schedule fixture")
    sessions = derive_planned_sessions(
        coverage_start=coverage_start,
        coverage_end=coverage_end,
        holiday_dates=list(holidays),
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "authority": AUTHORITY,
        "semantics": SEMANTICS,
        "derivation": DERIVATION,
        "source_reference": "IDX_TEST_OFFICIAL_CALENDAR",
        "source_document_path": source.name,
        "source_document_sha256": _sha256(source),
        "coverage_start": coverage_start,
        "coverage_end": coverage_end,
        "holiday_dates": list(holidays),
        "session_dates": list(sessions),
        "outcome_access": False,
    }
    payload["payload_sha256"] = schedule_module._canonical_hash(payload)
    attestation = root / "execution_schedule_attestation.json"
    attestation.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return attestation, _sha256(attestation), source


def _write_eod_inputs(root: Path):
    observed = root / "exchange_sessions.csv"
    observed.write_text("date\n2026-08-21\n2026-08-24\n", encoding="utf-8")
    ohlcv = root / "session_ohlcv.parquet"
    model = root / "model_input.parquet"
    pd.DataFrame(
        [{"ticker": "AAA", "session_date": "2026-08-24", "close": 1000.0}]
    ).to_parquet(ohlcv, index=False)
    pd.DataFrame(
        [{
            "ticker": "AAA",
            "date": "2026-08-24",
            "close": 1000.0,
            "regular_market_value": 1_000_000_000.0,
        }]
    ).to_parquet(model, index=False)
    return observed, ohlcv, model


def _idx_payload(date="2026-08-26"):
    rows = [
        {
            "StockCode": "AAA",
            "Date": f"{date}T00:00:00",
            "OpenPrice": 1000,
            "FirstTrade": 1010,
        }
    ]
    return json.dumps(
        {"data": rows, "recordsTotal": 1, "recordsFiltered": 1},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


class _Response:
    def __init__(self, content, status_code=200):
        self.content = content
        self.status_code = status_code


def test_schedule_derives_holiday_and_future_successor():
    sessions = derive_planned_sessions(
        coverage_start="2026-08-24",
        coverage_end="2026-08-28",
        holiday_dates=["2026-08-25"],
    )
    assert sessions == (
        "2026-08-24",
        "2026-08-26",
        "2026-08-27",
        "2026-08-28",
    )


def test_verified_schedule_rejects_source_document_tamper(tmp_path):
    attestation, sha, source = _write_schedule(tmp_path / "schedule")
    loaded = load_verified_official_trading_schedule(attestation, expected_sha256=sha)
    assert next_planned_session(loaded, "2026-08-24") == "2026-08-26"
    source.write_bytes(b"tampered")
    with pytest.raises(
        OfficialTradingScheduleError,
        match="OFFICIAL_SCHEDULE_SOURCE_DOCUMENT_SHA_MISMATCH",
    ):
        load_verified_official_trading_schedule(attestation, expected_sha256=sha)


def test_observed_calendar_can_end_at_decision_while_schedule_proves_successor(tmp_path):
    observed, ohlcv, model = _write_eod_inputs(tmp_path)
    observed_before = _sha256(observed)
    attestation, attestation_sha, _ = _write_schedule(tmp_path / "schedule")

    verified = verify_eod_execution_inputs_with_schedule(
        session_ohlcv_path=ohlcv,
        model_input_path=model,
        official_calendar_path=observed,
        execution_schedule_attestation_path=attestation,
        execution_schedule_attestation_sha256=attestation_sha,
        decision_session_date="2026-08-24",
        required_tickers=("AAA",),
    )

    assert verified.session_date == "2026-08-24"
    assert verified.next_official_session_date == "2026-08-26"
    assert verified.official_calendar_sha256 == observed_before
    assert _sha256(observed) == observed_before
    assert verified.execution_schedule_attestation_sha256 == attestation_sha


def test_observed_session_conflicting_with_planned_holiday_fails_closed(tmp_path):
    observed, ohlcv, model = _write_eod_inputs(tmp_path)
    attestation, attestation_sha, _ = _write_schedule(
        tmp_path / "schedule",
        holidays=("2026-08-24", "2026-08-25"),
    )
    with pytest.raises(Exception, match="EXECUTION_V1_OBSERVED_PLANNED_SESSION_CONFLICT"):
        verify_eod_execution_inputs_with_schedule(
            session_ohlcv_path=ohlcv,
            model_input_path=model,
            official_calendar_path=observed,
            execution_schedule_attestation_path=attestation,
            execution_schedule_attestation_sha256=attestation_sha,
            decision_session_date="2026-08-24",
            required_tickers=("AAA",),
        )


def test_official_open_uses_planned_schedule_not_observed_calendar(tmp_path):
    attestation, attestation_sha, _ = _write_schedule(tmp_path / "schedule")
    called = False

    def must_not_call(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("network must not be called on planned Bursa holiday")

    holiday = run_same_session_official_open_capture_v2(
        runtime_root=tmp_path / "runtime",
        execution_schedule_attestation_path=attestation,
        execution_schedule_attestation_sha256=attestation_sha,
        now=datetime(2026, 8, 25, 9, 7, tzinfo=JAKARTA),
        get=must_not_call,
    )
    assert holiday["status"] == STATUS_HOLIDAY_NO_SESSION
    assert called is False

    calls = 0

    def next_session_get(url, *, params, headers, timeout):
        nonlocal calls
        calls += 1
        assert params["date"] == "20260826"
        return _Response(_idx_payload())

    captured = run_same_session_official_open_capture_v2(
        runtime_root=tmp_path / "runtime",
        execution_schedule_attestation_path=attestation,
        execution_schedule_attestation_sha256=attestation_sha,
        now=datetime(2026, 8, 26, 9, 7, tzinfo=JAKARTA),
        get=next_session_get,
    )
    assert captured["status"] == STATUS_CAPTURED
    assert calls == 1


def test_official_open_existing_manifest_is_reverified_before_idempotent_status(tmp_path):
    attestation, attestation_sha, _ = _write_schedule(tmp_path / "schedule")

    def direct_get(url, *, params, headers, timeout):
        return _Response(_idx_payload("2026-08-26"))

    runtime = tmp_path / "runtime"
    first = run_same_session_official_open_capture_v2(
        runtime_root=runtime,
        execution_schedule_attestation_path=attestation,
        execution_schedule_attestation_sha256=attestation_sha,
        now=datetime(2026, 8, 26, 9, 7, tzinfo=JAKARTA),
        get=direct_get,
    )
    assert first["status"] == STATUS_CAPTURED
    manifest = runtime / "official_open" / "2026-08-26" / "manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["authority"] = "TAMPERED"
    manifest.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")

    network_calls = 0

    def must_not_call(*args, **kwargs):
        nonlocal network_calls
        network_calls += 1
        raise AssertionError("tampered existing evidence must not recapture")

    second = run_same_session_official_open_capture_v2(
        runtime_root=runtime,
        execution_schedule_attestation_path=attestation,
        execution_schedule_attestation_sha256=attestation_sha,
        now=datetime(2026, 8, 26, 9, 7, tzinfo=JAKARTA),
        get=must_not_call,
    )
    assert second["status"] == STATUS_PARTIAL_EVIDENCE_FAIL_CLOSED
    assert "EXISTING_OFFICIAL_OPEN_MANIFEST_INVALID" in second["provider_error"]
    assert network_calls == 0
