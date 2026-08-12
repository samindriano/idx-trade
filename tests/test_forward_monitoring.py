from __future__ import annotations

from datetime import datetime, timedelta
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from idx_trade import forward_monitoring as monitor
from idx_trade.providers.idx_index_summary import IndexSummaryFetchMeta, IndexSummaryPayloadCapture
from idx_trade.providers.idx_stock_summary import StockSummaryFetchMeta, StockSummaryPayloadCapture
from idx_trade.provenance import sha256_file, write_manifest_atomic
from idx_trade.storage import write_parquet_atomic


SESSION = pd.Timestamp("2026-08-03")


def _security_master(root: Path) -> None:
    directory = root / "listings"
    directory.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "security_id": "IDX:AAAA:20200101",
                "ticker": "AAAA",
                "company_name": "A",
                "listed_from": "2020-01-01",
                "listed_to": None,
                "source": "TEST",
            },
            {
                "security_id": "IDX:BBBB:20200101",
                "ticker": "BBBB",
                "company_name": "B",
                "listed_from": "2020-01-01",
                "listed_to": None,
                "source": "TEST",
            },
        ]
    ).to_csv(directory / "security_master.csv", index=False)


def _raw_price(root: Path) -> None:
    directory = root / "prices" / "raw"
    directory.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "ticker": "AAAA",
                "date": SESSION,
                "raw_open": 100.0,
                "raw_high": 105.0,
                "raw_low": 99.0,
                "raw_close": 103.0,
                "raw_volume": 1000.0,
            }
        ]
    ).to_parquet(directory / "AAAA.parquet", index=False)


def _stock_summary(*, unresolved: bool = False) -> tuple[pd.DataFrame, StockSummaryFetchMeta]:
    frame = pd.DataFrame(
        [
            {
                "ticker": "AAAA",
                "as_of_date": SESSION,
                "remarks": "",
                "volume": None if unresolved else 1000,
                "frequency": 12,
                "regular_value": 103000,
                "nonregular_volume": 0,
                "nonregular_frequency": 0,
                "security_status_raw": "",
                "security_status_field": "",
                "source": "IDX_PUBLIC_STOCK_SUMMARY",
                "source_ref": "https://example.test/summary",
            },
            {
                "ticker": "BBBB",
                "as_of_date": SESSION,
                "remarks": "",
                "volume": 0,
                "frequency": 0,
                "regular_value": 0,
                "nonregular_volume": 0,
                "nonregular_frequency": 0,
                "security_status_raw": "",
                "security_status_field": "",
                "source": "IDX_PUBLIC_STOCK_SUMMARY",
                "source_ref": "https://example.test/summary",
            },
        ]
    )
    return frame, StockSummaryFetchMeta(
        requested_date=SESSION.date().isoformat(),
        source_ref="https://example.test/summary",
        records_total=2,
        rows=2,
        explicit_security_status_rows=0,
        regular_trade_evidence_rows=1,
    )


def _index_summary() -> tuple[pd.DataFrame, IndexSummaryFetchMeta, IndexSummaryPayloadCapture]:
    frame = pd.DataFrame(
        {
            "session_date": [SESSION],
            "index_code": ["COMPOSITE"],
            "close": [100.0],
            "source": ["IDX_OFFICIAL"],
        }
    )
    raw = b'{"data":[{"IndexCode":"COMPOSITE"}]}'
    capture = IndexSummaryPayloadCapture(
        payload={"data": []},
        source_ref="https://example.test/index-summary",
        raw_bytes=raw,
        endpoint="https://example.test/index-summary",
        params={"date": SESSION.strftime("%Y%m%d")},
        retrieval_started_at_utc="2026-08-03T10:00:00+00:00",
        observed_available_at_utc="2026-08-03T10:00:01+00:00",
        records_total=1,
        records_filtered=1,
        row_count=1,
        completeness_status="COMPLETE_RECORDS_TOTAL_SINGLE_RESPONSE",
    )
    meta = IndexSummaryFetchMeta(
        requested_date=SESSION.date().isoformat(),
        source_ref=capture.source_ref,
        records_total=1,
        rows=1,
        records_filtered=1,
        retrieval_started_at_utc=capture.retrieval_started_at_utc,
        observed_available_at_utc=capture.observed_available_at_utc,
        raw_sha256=capture.raw_sha256,
        completeness_status=capture.completeness_status,
    )
    return frame, meta, capture


def _prepare(monkeypatch: pytest.MonkeyPatch, root: Path, *, unresolved: bool = False) -> list[int]:
    _security_master(root)
    _raw_price(root)
    calls: list[int] = []

    def fake_calendar(paths: monitor.RuntimePaths, *, through=None):
        paths.calendar_root.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"date": [SESSION]}).to_csv(paths.calendar_root / "exchange_sessions.csv", index=False)
        pd.DataFrame({"status": ["PARSED"]}).to_csv(paths.calendar_root / "exchange_session_sources.csv", index=False)
        write_manifest_atomic(
            paths.calendar_root / "exchange_session_summary.json",
            {"complete": True, "exchange_sessions": 1},
        )
        return pd.DatetimeIndex([SESSION])

    def fake_summary(date, *, include_capture=False):
        calls.append(1)
        frame, meta = _stock_summary(unresolved=unresolved)
        raw = b'{"data":[{"StockCode":"AAAA"},{"StockCode":"BBBB"}]}'
        capture = StockSummaryPayloadCapture(
            payload={"data": []},
            source_ref=meta.source_ref,
            raw_bytes=raw,
            endpoint=meta.source_ref,
            params={"date": SESSION.strftime("%Y%m%d")},
            retrieval_started_at_utc="2026-08-03T10:00:00+00:00",
            observed_available_at_utc="2026-08-03T10:00:01+00:00",
            records_total=meta.records_total or len(frame),
            records_filtered=meta.records_total or len(frame),
            row_count=len(frame),
            completeness_status="COMPLETE_RECORDS_TOTAL_SINGLE_RESPONSE",
        )
        return (frame, meta, capture) if include_capture else (frame, meta)

    monkeypatch.setattr(monitor, "sync_forward_calendar", fake_calendar)
    monkeypatch.setattr(monitor, "fetch_stock_summary_snapshot", fake_summary)
    monkeypatch.setattr(
        monitor,
        "fetch_index_summary_snapshot",
        lambda date, *, include_capture=False: _index_summary(),
    )
    return calls


def test_capture_is_idempotent_and_does_not_refetch_ready_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _prepare(monkeypatch, tmp_path)

    first = monitor.capture_session(tmp_path, target_date=SESSION)
    second = monitor.capture_session(tmp_path, target_date=SESSION)

    assert first["status"] == "DATA_READY"
    assert first["model_input_rows"] == 1
    assert second == {
        "status": "DATA_READY",
        "session_date": SESSION.date().isoformat(),
        "idempotent": True,
    }
    assert len(calls) == 1

    status = monitor.monitoring_status(tmp_path)
    assert status["data_ready_sessions"] == 1
    assert status["next_missing_session"] is None
    assert status["sessions"][0]["state"] == "DATA_READY"


def test_successful_capture_manifest_declares_complete_stock_and_index_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare(monkeypatch, tmp_path)

    result = monitor.capture_session(tmp_path, target_date=SESSION)

    assert result["status"] == "DATA_READY"
    paths = monitor.runtime_paths(tmp_path)
    manifest_path = paths.session_root / SESSION.date().isoformat() / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    for prefix in ("stock_summary", "index_summary"):
        source = manifest[f"{prefix}_source"]
        assert source["endpoint"]
        assert source["params"] == {"date": SESSION.strftime("%Y%m%d")}
        assert source["session_date"] == SESSION.date().isoformat()
        assert source["retrieval_started_at_utc"].endswith("+00:00")
        assert source["observed_available_at_utc"].endswith("+00:00")
        assert source["row_count"] > 0
        assert source["records_total"] == source["row_count"]
        assert source["records_filtered"] == source["records_total"]
        assert source["completeness_status"] == "COMPLETE_RECORDS_TOTAL_SINGLE_RESPONSE"

        raw_path = Path(manifest[f"{prefix}_raw_path"])
        normalized_path = Path(manifest[f"{prefix}_path"])
        assert raw_path.read_bytes()
        assert normalized_path.exists()
        assert manifest[f"{prefix}_raw_sha256"] == sha256_file(raw_path)
        assert manifest[f"{prefix}_sha256"] == sha256_file(normalized_path)


@pytest.mark.parametrize("tamper", ["missing", "hash_mismatch"])
def test_stale_recovery_rejects_declared_context_artifact_tampering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tamper: str,
) -> None:
    _prepare(monkeypatch, tmp_path)
    monitor.capture_session(tmp_path, target_date=SESSION)

    paths = monitor.runtime_paths(tmp_path)
    final_dir = paths.session_root / SESSION.date().isoformat()
    index_raw = final_dir / "idx_index_summary.raw.json"
    if tamper == "missing":
        index_raw.unlink()
    else:
        index_raw.write_bytes(b"tampered")

    stale = (datetime.now(tz=ZoneInfo("UTC")) - timedelta(hours=2)).isoformat()
    connection = monitor._connect(paths)
    try:
        connection.execute(
            """
            UPDATE session_snapshots
            SET state='FETCHING', heartbeat_at=?, updated_at=?
            WHERE session_date=?
            """,
            (stale, stale, SESSION.date().isoformat()),
        )
    finally:
        connection.close()

    monitor._reconcile_stale(paths)
    row = monitor._existing_session(paths, SESSION)
    assert row is not None
    assert row["state"] == "DATA_FAILED"
    assert row["error_code"] == "INCOMPLETE_ARTIFACTS"


def test_unresolved_point_evidence_fails_closed_and_is_retryable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _prepare(monkeypatch, tmp_path, unresolved=True)

    with pytest.raises(RuntimeError, match="point evidence unresolved"):
        monitor.capture_session(tmp_path, target_date=SESSION)

    paths = monitor.runtime_paths(tmp_path)
    row = monitor._existing_session(paths, SESSION)
    assert row is not None
    assert row["state"] == "DATA_FAILED"
    assert row["error_code"] == "RUNTIMEERROR"


def test_stale_fetch_with_complete_final_artifacts_reconciles_without_refetch(tmp_path: Path) -> None:
    paths = monitor.runtime_paths(tmp_path)
    session_key = SESSION.date().isoformat()
    final_dir = paths.session_root / session_key
    final_dir.mkdir(parents=True)
    snapshot = final_dir / "model_input.parquet"
    evidence = final_dir / "session_evidence.parquet"
    manifest = final_dir / "manifest.json"
    write_parquet_atomic(pd.DataFrame({"ticker": ["AAAA"], "date": [SESSION]}), snapshot)
    write_parquet_atomic(pd.DataFrame({"ticker": ["AAAA"], "session_date": [SESSION]}), evidence)
    write_manifest_atomic(manifest, {"status": "DATA_READY", "session_date": session_key})

    stale = (datetime.now(tz=ZoneInfo("UTC")) - timedelta(hours=2)).isoformat()
    connection = monitor._connect(paths)
    try:
        connection.execute(
            """
            INSERT INTO session_snapshots(
                session_date, state, started_at, updated_at, lease_owner, heartbeat_at
            ) VALUES (?, 'FETCHING', ?, ?, 'dead-worker', ?)
            """,
            (session_key, stale, stale, stale),
        )
    finally:
        connection.close()

    monitor._reconcile_stale(paths)
    row = monitor._existing_session(paths, SESSION)
    assert row is not None
    assert row["state"] == "DATA_READY"
    assert row["snapshot_sha256"] == sha256_file(snapshot)
    assert row["evidence_sha256"] == sha256_file(evidence)
    assert row["manifest_sha256"] == sha256_file(manifest)


def test_stale_fetch_without_canonical_artifacts_becomes_interrupted_failure(tmp_path: Path) -> None:
    paths = monitor.runtime_paths(tmp_path)
    stale = (datetime.now(tz=ZoneInfo("UTC")) - timedelta(hours=2)).isoformat()
    connection = monitor._connect(paths)
    try:
        connection.execute(
            """
            INSERT INTO session_snapshots(
                session_date, state, started_at, updated_at, lease_owner, heartbeat_at
            ) VALUES (?, 'FETCHING', ?, ?, 'dead-worker', ?)
            """,
            (SESSION.date().isoformat(), stale, stale, stale),
        )
    finally:
        connection.close()

    monitor._reconcile_stale(paths)
    row = monitor._existing_session(paths, SESSION)
    assert row is not None
    assert row["state"] == "DATA_FAILED"
    assert row["error_code"] == "INTERRUPTED"


def test_later_session_cannot_skip_earlier_missing_date(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _security_master(tmp_path)
    _raw_price(tmp_path)
    later = SESSION + pd.Timedelta(days=1)

    def fake_calendar(paths: monitor.RuntimePaths, *, through=None):
        paths.calendar_root.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"date": [SESSION, later]}).to_csv(paths.calendar_root / "exchange_sessions.csv", index=False)
        return pd.DatetimeIndex([SESSION, later])

    monkeypatch.setattr(monitor, "sync_forward_calendar", fake_calendar)

    with pytest.raises(ValueError, match="cannot skip an earlier missing session"):
        monitor.capture_session(tmp_path, target_date=later)
