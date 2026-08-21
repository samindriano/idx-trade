import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

import idx_trade.forward_ca_attestation_v1 as forward_ca
from idx_trade.v4_x1_decision_v1_contract import DecisionV1Error
from idx_trade.v4_x1_execution_v1_verify import (
    verify_corporate_action_attestation,
    verify_eod_execution_inputs,
    verify_open_execution_inputs,
)


def _write_stub(path: Path, payload: bytes = b"stub") -> Path:
    path.write_bytes(payload)
    return path


def _write_json(path: Path, payload) -> str:
    body = (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")
    path.write_bytes(body)
    return hashlib.sha256(body).hexdigest()


def _calendar(path: Path) -> Path:
    path.write_text(
        "date\n2026-08-20\n2026-08-21\n2026-08-24\n2026-08-25\n",
        encoding="utf-8",
    )
    return path


def _eod_frames(close_aaa=1000.0):
    ohlcv = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "session_date": pd.to_datetime(["2026-08-21", "2026-08-21"]),
            "close": [close_aaa, 2000.0],
        }
    )
    model = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "date": pd.to_datetime(["2026-08-21", "2026-08-21"]),
            "close": [1000.0, 2000.0],
            "regular_market_value": [1_000_000_000.0, 2_000_000_000.0],
        }
    )
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
    assert verified.official_calendar_sha256 == hashlib.sha256(
        calendar_path.read_bytes()
    ).hexdigest()


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


def test_open_verifier_requires_exact_execution_date(monkeypatch, tmp_path):
    path = _write_stub(tmp_path / "session_ohlcv.parquet", b"open")
    good = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "session_date": pd.to_datetime(["2026-08-24", "2026-08-24"]),
            "open": [1010.0, 0.0],
        }
    )
    monkeypatch.setattr(pd, "read_parquet", lambda _: good.copy())
    verified = verify_open_execution_inputs(
        session_ohlcv_path=path,
        execution_session_date="2026-08-24",
    )
    assert verified.raw_open_prices == {"AAA": 1010.0}
    assert verified.available_tickers == frozenset({"AAA"})

    bad = good.copy()
    bad["session_date"] = pd.Timestamp("2026-08-25")
    monkeypatch.setattr(pd, "read_parquet", lambda _: bad.copy())
    with pytest.raises(DecisionV1Error, match="OPEN_ARTIFACT_DATE_MISMATCH"):
        verify_open_execution_inputs(
            session_ohlcv_path=path,
            execution_session_date="2026-08-24",
        )


def _phase_manifest(
    tmp_path: Path,
    phase: str,
    *,
    tickers=("AAA", "BBB"),
    relevant_event=False,
):
    root = tmp_path / phase.lower()
    raw = root / "raw"
    raw.mkdir(parents=True)

    issued_payload = {"data": []}
    if relevant_event:
        issued_payload = {
            "data": [
                {
                    "KodeEmiten": tickers[0],
                    "TanggalPencatatan": "2026-08-24T00:00:00",
                    "JenisTindakan": "stockSplit",
                }
            ]
        }
    announcement_payload = {"Items": []}
    calendar_payload = {
        "Results": [
            {
                "title": "ZZZZ",
                "start": "2026-08-24T00:00:00",
                "Jenis": "RUPS",
                "description": "Rapat umum pemegang saham ZZZZ",
            }
        ]
    }

    issued = raw / "issued.json"
    announcements = raw / "announcements.json"
    calendar = raw / "calendar.json"
    issued_sha = _write_json(issued, issued_payload)
    announcements_sha = _write_json(announcements, announcement_payload)
    calendar_sha = _write_json(calendar, calendar_payload)
    fingerprint = forward_ca._structural_fingerprint(calendar_payload)

    manifest = {
        "schema_version": forward_ca.PHASE_SCHEMA,
        "status": "COMPLETE",
        "phase": phase,
        "provider_repository": forward_ca.PROVIDER_REPOSITORY,
        "provider_commit": forward_ca.PROVIDER_COMMIT,
        "upstream_base_url": forward_ca.UPSTREAM_BASE_URL,
        "from_session_date": "2026-08-21",
        "through_session_date": "2026-08-24",
        "required_tickers": list(tickers),
        "calendar_capture_scope": forward_ca.CALENDAR_CAPTURE_SCOPE,
        "legs": {
            "issued_history": {"status": "COMPLETE"},
            "announcements": {"status": "COMPLETE"},
            "calendar": {"status": "COMPLETE"},
        },
        "calendar_schema_fingerprints": [fingerprint],
        "raw_artifacts": [
            {
                "leg": "issued_history",
                "endpoint": forward_ca.EXPECTED_ENDPOINT_BY_LEG["issued_history"],
                "path": "raw/issued.json",
                "sha256": issued_sha,
                "http_status": 200,
                "content_type": "application/json; charset=utf-8",
            },
            {
                "leg": "announcements",
                "endpoint": forward_ca.EXPECTED_ENDPOINT_BY_LEG["announcements"],
                "path": "raw/announcements.json",
                "sha256": announcements_sha,
                "http_status": 200,
                "content_type": "application/json; charset=utf-8",
            },
            {
                "leg": "calendar",
                "endpoint": forward_ca.EXPECTED_ENDPOINT_BY_LEG["calendar"],
                "path": "raw/calendar.json",
                "sha256": calendar_sha,
                "http_status": 200,
                "content_type": "application/json; charset=utf-8",
            },
        ],
    }
    manifest_path = root / "MANIFEST.json"
    _write_json(manifest_path, manifest)
    return manifest_path, fingerprint, issued


def _source_manifest(tmp_path: Path, *, tickers=("AAA", "BBB"), relevant_event=False):
    post, fingerprint, issued = _phase_manifest(
        tmp_path,
        "POST_EOD",
        tickers=tickers,
        relevant_event=relevant_event,
    )
    pre, _, _ = _phase_manifest(
        tmp_path,
        "PREOPEN",
        tickers=tickers,
        relevant_event=relevant_event,
    )
    source = tmp_path / "SOURCE_MANIFEST.json"
    forward_ca.merge_phase_manifests(
        post_eod_manifest_path=post,
        preopen_manifest_path=pre,
        output_path=source,
    )
    return source, fingerprint, issued


def _valid_attestation(
    monkeypatch,
    tmp_path: Path,
    *,
    tickers=("AAA", "BBB"),
    relevant_event=False,
):
    source, fingerprint, issued = _source_manifest(
        tmp_path,
        tickers=tickers,
        relevant_event=relevant_event,
    )
    monkeypatch.setattr(
        forward_ca,
        "EXPECTED_CALENDAR_SCHEMA_FINGERPRINT",
        fingerprint,
    )
    attestation = tmp_path / "ca_attestation.json"
    forward_ca.build_attestation(
        source_manifest_path=source,
        output_path=attestation,
    )
    return attestation, source, fingerprint, issued


def test_ca_attestation_fails_closed_if_calendar_schema_freeze_missing(monkeypatch, tmp_path):
    path = tmp_path / "ca_attestation.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": forward_ca.ATTESTATION_SCHEMA,
                "provider_repository": forward_ca.PROVIDER_REPOSITORY,
                "provider_commit": forward_ca.PROVIDER_COMMIT,
                "upstream_base_url": forward_ca.UPSTREAM_BASE_URL,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(forward_ca, "EXPECTED_CALENDAR_SCHEMA_FINGERPRINT", None)
    with pytest.raises(DecisionV1Error, match="CA_CALENDAR_SCHEMA_NOT_FROZEN"):
        verify_corporate_action_attestation(
            attestation_path=path,
            expected_from_session_date="2026-08-21",
            expected_through_session_date="2026-08-24",
            required_tickers=["AAA"],
        )


def test_ca_attestation_accepts_only_verified_forward_ca_source_chain(monkeypatch, tmp_path):
    path, source, _, _ = _valid_attestation(monkeypatch, tmp_path)
    verified = verify_corporate_action_attestation(
        attestation_path=path,
        expected_from_session_date="2026-08-21",
        expected_through_session_date="2026-08-24",
        required_tickers=["AAA", "BBB"],
    )
    assert verified.status == "NO_RELEVANT_EVENTS"
    assert verified.covered_tickers == frozenset({"AAA", "BBB"})
    assert verified.source_path == source.resolve()
    assert verified.source_sha256 == hashlib.sha256(source.read_bytes()).hexdigest()


def test_ca_attestation_rejects_relevant_event(monkeypatch, tmp_path):
    path, _, _, _ = _valid_attestation(
        monkeypatch,
        tmp_path,
        tickers=("AAA",),
        relevant_event=True,
    )
    with pytest.raises(DecisionV1Error, match="CA_RECONCILIATION_REQUIRED"):
        verify_corporate_action_attestation(
            attestation_path=path,
            expected_from_session_date="2026-08-21",
            expected_through_session_date="2026-08-24",
            required_tickers=["AAA"],
        )


def test_ca_attestation_rejects_incomplete_ticker_coverage(monkeypatch, tmp_path):
    path, _, _, _ = _valid_attestation(monkeypatch, tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["evidence_rows"] = [payload["evidence_rows"][0]]
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    with pytest.raises(DecisionV1Error, match="CA_COVERAGE_INCOMPLETE"):
        verify_corporate_action_attestation(
            attestation_path=path,
            expected_from_session_date="2026-08-21",
            expected_through_session_date="2026-08-24",
            required_tickers=["AAA", "BBB"],
        )


def test_ca_attestation_rejects_source_hash_mismatch(monkeypatch, tmp_path):
    path, _, _, _ = _valid_attestation(monkeypatch, tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["source_sha256"] = "0" * 64
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    with pytest.raises(DecisionV1Error, match="CA_SOURCE_SHA_MISMATCH"):
        verify_corporate_action_attestation(
            attestation_path=path,
            expected_from_session_date="2026-08-21",
            expected_through_session_date="2026-08-24",
            required_tickers=["AAA", "BBB"],
        )


def test_ca_attestation_rejects_raw_source_chain_mutation(monkeypatch, tmp_path):
    path, _, _, issued = _valid_attestation(monkeypatch, tmp_path)
    issued.write_text('{"data":[{"tampered":true}]}\n', encoding="utf-8")
    with pytest.raises(DecisionV1Error, match="CA_SOURCE_CHAIN_INVALID"):
        verify_corporate_action_attestation(
            attestation_path=path,
            expected_from_session_date="2026-08-21",
            expected_through_session_date="2026-08-24",
            required_tickers=["AAA", "BBB"],
        )
