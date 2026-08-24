import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade import official_trading_schedule_v1 as schedule_module
from idx_trade.e2e_paper_orchestration_v1 import PREPARED_SCHEMA, _canonical_hash
from idx_trade.e2e_paper_schedule_binding_v1 import (
    verify_prepared_schedule_binding,
    write_prepared_schedule_binding,
)
from idx_trade.official_trading_schedule_v1 import (
    AUTHORITY,
    DERIVATION,
    SCHEMA_VERSION,
    SEMANTICS,
    derive_planned_sessions,
)
from idx_trade.v4_x1_execution_v1_verify_schedule_v1 import (
    verify_eod_execution_inputs_with_schedule,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _schedule(root: Path, source_bytes=b"source-a"):
    root.mkdir(parents=True, exist_ok=True)
    source = root / "official_source.pdf"
    source.write_bytes(source_bytes)
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
    path = root / "execution_schedule_attestation.json"
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    return path, _sha256(path)


def _eod(tmp_path: Path, schedule_path: Path, schedule_sha: str):
    observed = tmp_path / "observed.csv"
    observed.write_text("date\n2026-08-24\n")
    ohlcv = tmp_path / "ohlcv.parquet"
    model = tmp_path / "model.parquet"
    pd.DataFrame([
        {"ticker": "AAA", "session_date": "2026-08-24", "close": 100.0}
    ]).to_parquet(ohlcv, index=False)
    pd.DataFrame([
        {
            "ticker": "AAA",
            "date": "2026-08-24",
            "close": 100.0,
            "regular_market_value": 1_000_000.0,
        }
    ]).to_parquet(model, index=False)
    return verify_eod_execution_inputs_with_schedule(
        session_ohlcv_path=ohlcv,
        model_input_path=model,
        official_calendar_path=observed,
        execution_schedule_attestation_path=schedule_path,
        execution_schedule_attestation_sha256=schedule_sha,
        decision_session_date="2026-08-24",
        required_tickers=("AAA",),
    )


def _prepared(runtime: Path, eod):
    path = runtime / "prepared" / "2026-08-24.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": PREPARED_SCHEMA,
        "status": "PREPARED_EXECUTION",
        "decision_session_date": "2026-08-24",
        "execution_session_date": "2026-08-26",
        "eod_inputs": {
            "calendar": {
                "path": str(eod.official_calendar_path.resolve()),
                "sha256": eod.official_calendar_sha256,
            }
        },
    }
    payload["payload_sha256"] = _canonical_hash(payload)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    return path


def test_prepared_schedule_binding_is_immutable_and_reverified(tmp_path):
    schedule, schedule_sha = _schedule(tmp_path / "schedule")
    eod = _eod(tmp_path, schedule, schedule_sha)
    runtime = tmp_path / "runtime"
    prepared = _prepared(runtime, eod)

    first = write_prepared_schedule_binding(
        runtime, prepared_path=prepared, eod_inputs=eod
    )
    second = write_prepared_schedule_binding(
        runtime, prepared_path=prepared, eod_inputs=eod
    )
    assert first.path == second.path
    assert first.file_sha256 == second.file_sha256

    verified = verify_prepared_schedule_binding(
        runtime,
        prepared_path=prepared,
        expected_schedule_attestation_path=schedule,
        expected_schedule_attestation_sha256=schedule_sha,
    )
    assert verified.execution_session_date == "2026-08-26"
    assert verified.prepared_sha256 == _sha256(prepared)


def test_prepared_schedule_binding_rejects_schedule_revision(tmp_path):
    schedule, schedule_sha = _schedule(tmp_path / "schedule-a")
    eod = _eod(tmp_path, schedule, schedule_sha)
    runtime = tmp_path / "runtime"
    prepared = _prepared(runtime, eod)
    write_prepared_schedule_binding(runtime, prepared_path=prepared, eod_inputs=eod)

    revised, revised_sha = _schedule(tmp_path / "schedule-b", source_bytes=b"source-b")
    with pytest.raises(Exception, match="E2E_SCHEDULE_BINDING_ATTESTATION_PATH_MISMATCH"):
        verify_prepared_schedule_binding(
            runtime,
            prepared_path=prepared,
            expected_schedule_attestation_path=revised,
            expected_schedule_attestation_sha256=revised_sha,
        )
