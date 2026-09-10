from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pandas as pd
import pytest

from idx_trade import forward_monitoring as monitor
from idx_trade import v4_x1_forward_score as v4_score
from idx_trade.providers.idx_index_summary import (
    IndexSummaryFetchMeta,
    IndexSummaryPayloadCapture,
)
from idx_trade.providers.idx_stock_summary import (
    StockSummaryFetchMeta,
    StockSummaryPayloadCapture,
)
from idx_trade.provenance import write_manifest_atomic
from idx_trade.e2e_paper_cloud_runtime_v1 import (
    CONTRACT_VERSION,
    CALENDAR_BINDING_SCHEMA_VERSION,
    OFFICIAL_CALENDAR_AUTHORITY,
    INPUT_SCHEMA_VERSION,
    CloudInputBundle,
    CloudPaperArchive,
    CloudPaperRuntimeError,
    LocalConditionalStore,
    OFFICIAL_OPEN_EXECUTION_END,
    build_runtime_snapshot,
    canonical_json_bytes,
    load_schedule_from_bundle,
    materialize_forward_observed_session_calendar,
    materialize_historical_official_calendar,
    materialize_official_open_from_cloud,
    restore_runtime_snapshot,
    sha256_bytes,
)
from scripts import run_e2e_paper_cloud_v1 as cloud_runner
from idx_trade.official_open_evidence_v1 import (
    AUTHORITY,
    FIELD_SEMANTICS,
    TRANSPORT_POLICY,
    UPSTREAM_PATH,
)
from idx_trade.official_open_cloud_archive_v1 import (
    EXECUTION_ADMISSION as OPEN_CLOUD_EXECUTION_ADMISSION,
    SCHEMA_VERSION as OPEN_CLOUD_SCHEMA_VERSION,
    SLOT_TIMES as OPEN_CLOUD_SLOT_TIMES,
)


PRODUCER_CAPTURE_CODE_REF = "4" * 40
SESSION = pd.Timestamp("2026-08-03")
AUTHORITATIVE_EVIDENCE_ROOT = Path(
    os.getenv(
        "IDX_TRADE_OFFICIAL_CALENDAR_EVIDENCE_ROOT",
        r"D:\Documents\Project\idx-trade-data-gate-20260909-official-calendar-retrieval-v1",
    )
)
AUTHORITATIVE_HISTORICAL_ROOT = Path(
    r"D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809"
)


def _write_schedule(
    tmp_path: Path,
    *,
    session_dates: tuple[str, ...] | None = None,
) -> tuple[bytes, str]:
    source = tmp_path / "official-source.pdf"
    source.write_bytes(b"official source")
    sessions = list(session_dates or ("2026-08-24", "2026-08-26"))
    coverage_start = sessions[0]
    coverage_end = sessions[-1]
    holidays = ["2026-08-25"] if session_dates is None else []
    body = {
        "schema_version": "idx_official_trading_schedule_v1",
        "authority": "IDX",
        "semantics": "PLANNED_OFFICIAL_TRADING_SCHEDULE",
        "derivation": "WEEKDAYS_MINUS_PUBLISHED_BURSA_HOLIDAYS",
        "source_reference": "official-test-source",
        "source_document_path": source.name,
        "source_document_sha256": sha256_bytes(source.read_bytes()),
        "coverage_start": coverage_start,
        "coverage_end": coverage_end,
        "holiday_dates": holidays,
        "session_dates": sessions,
    }
    payload = dict(body)
    payload["payload_sha256"] = sha256_bytes(canonical_json_bytes(body))
    return canonical_json_bytes(payload), payload["payload_sha256"]


def _input_manifest(
    store: LocalConditionalStore,
    tmp_path: Path,
    *,
    authoritative_root: Path | None = None,
    schedule_sessions: tuple[str, ...] | None = None,
) -> tuple[str, dict[str, Path]]:
    schedule_bytes, _ = _write_schedule(tmp_path, session_dates=schedule_sessions)
    historical_calendar = b"date\n2026-08-20\n2026-08-21\n"
    observed_calendar = b"date\n2026-08-24\n2026-08-26\n"
    source_identity = "IDX_DIGITAL_STATISTICS_DAILY_TRADING_TABLE"
    historical_source_ref = "https://www.idx.id/primary/DigitalStatistic/GetApiData?fixture=historical"
    observed_source_ref = "https://www.idx.id/primary/DigitalStatistic/GetApiData?fixture=observed"
    def calendar_sha(payload: bytes) -> str:
        return sha256_bytes("\n".join(payload.decode().splitlines()[1:]).encode())

    historical_sha = calendar_sha(historical_calendar)
    observed_sha = calendar_sha(observed_calendar)
    historical_summary = json.dumps(
        {
            "start": "2026-08-20",
            "end": "2026-08-21",
            "count": 2,
            "sessions_sha256": historical_sha,
            "complete": True,
            "error_months": 0,
            "source": OFFICIAL_CALENDAR_AUTHORITY,
            "source_identities": [source_identity],
        },
        sort_keys=True,
    ).encode()
    observed_summary = json.dumps(
        {
            "start": "2026-08-24",
            "end": "2026-08-26",
            "exchange_sessions": 2,
            "sessions_sha256": observed_sha,
            "complete": True,
            "error_months": 0,
            "source": OFFICIAL_CALENDAR_AUTHORITY,
            "source_identities": [source_identity],
        },
        sort_keys=True,
    ).encode()
    source_header = "year,month,source_identity,source_ref,status,sessions_in_requested_range,error\n"
    historical_sources = (
        source_header + f"2026,8,{source_identity},{historical_source_ref},PARSED,2,\n"
    ).encode()
    observed_sources = (
        source_header + f"2026,8,{source_identity},{observed_source_ref},PARSED,2,\n"
    ).encode()
    historical_binding = {
        "calendar_role": "historical_official_calendar",
        "summary_role": "historical_official_calendar_summary",
        "source_report_role": "historical_official_calendar_sources",
        "coverage_start": "2026-08-20",
        "coverage_end": "2026-08-21",
        "session_count": 2,
        "sessions_sha256": historical_sha,
        "authority": OFFICIAL_CALENDAR_AUTHORITY,
        "lineage_status": "OFFICIAL_SINGLE_SOURCE_RESOLVED",
        "source_identities": [source_identity],
        "source_references": [historical_source_ref],
    }
    observed_binding = {
        "calendar_role": "forward_observed_session_calendar",
        "summary_role": "forward_observed_session_calendar_summary",
        "source_report_role": "forward_observed_session_calendar_sources",
        "coverage_start": "2026-08-24",
        "coverage_end": "2026-08-26",
        "session_count": 2,
        "sessions_sha256": observed_sha,
        "authority": OFFICIAL_CALENDAR_AUTHORITY,
        "lineage_status": "OFFICIAL_SINGLE_SOURCE_RESOLVED",
        "source_identities": [source_identity],
        "source_references": [observed_source_ref],
    }
    if authoritative_root is not None:
        def _calendar_payload(path: Path) -> tuple[bytes, list[str], str]:
            payload = path.read_bytes()
            with path.open(encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                assert reader.fieldnames == ["date"]
                dates = [str(row["date"]).strip() for row in reader]
            return payload, dates, sha256_bytes("\n".join(dates).encode())

        def _source_report_info(payload: bytes) -> tuple[list[dict[str, str]], list[str], list[str]]:
            reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline=""))
            rows = list(reader)
            return rows, sorted({row["source_identity"] for row in rows}), sorted(
                {row["source_ref"] for row in rows}
            )

        historical_path = AUTHORITATIVE_HISTORICAL_ROOT / "official_exchange_sessions_1260.csv"
        historical_summary_path = AUTHORITATIVE_HISTORICAL_ROOT / "official_exchange_session_summary_1260.json"
        historical_source_path = AUTHORITATIVE_HISTORICAL_ROOT / "official_exchange_session_sources_1260.csv"
        april_source_path = AUTHORITATIVE_HISTORICAL_ROOT / "calendar_older_april_2021" / "exchange_session_sources.csv"
        observed_path = authoritative_root / "forward_monitoring" / "calendar" / "exchange_sessions.csv"
        observed_summary_path = authoritative_root / "forward_monitoring" / "calendar" / "exchange_session_summary.json"
        observed_source_path = authoritative_root / "forward_monitoring" / "calendar" / "exchange_session_sources.csv"
        assert all(
            path.is_file()
            for path in (
                historical_path,
                historical_summary_path,
                historical_source_path,
                april_source_path,
                observed_path,
                observed_summary_path,
                observed_source_path,
            )
        )
        historical_calendar, historical_dates, historical_sha = _calendar_payload(historical_path)
        observed_calendar, observed_dates, observed_sha = _calendar_payload(observed_path)
        historical_summary = historical_summary_path.read_bytes()
        observed_summary = observed_summary_path.read_bytes()
        historical_rows, _, _ = _source_report_info(historical_source_path.read_bytes())
        # The 1,260-row historical CSV starts on 2021-04-29, while its
        # companion report starts in May.  Add the exact clipped April row
        # from its separate official companion so this derived fixture is
        # explicit about the source coverage it binds.  The exact-root
        # un-reconciled report is tested separately and must fail closed.
        with april_source_path.open(encoding="utf-8-sig", newline="") as handle:
            april_reader = csv.DictReader(handle)
            april_row = next(april_reader)
            fieldnames = list(april_reader.fieldnames or [])
        april_row["sessions_in_requested_range"] = "2"
        historical_rows.insert(0, april_row)
        historical_buffer = io.StringIO(newline="")
        writer = csv.DictWriter(historical_buffer, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(historical_rows)
        historical_sources = historical_buffer.getvalue().encode("utf-8")
        observed_sources = observed_source_path.read_bytes()
        _, historical_ids, historical_refs = _source_report_info(historical_sources)
        _, observed_ids, observed_refs = _source_report_info(observed_sources)
        historical_binding = {
            **historical_binding,
            "coverage_start": historical_dates[0],
            "coverage_end": historical_dates[-1],
            "session_count": len(historical_dates),
            "sessions_sha256": historical_sha,
            "lineage_status": "OFFICIAL_MULTI_SOURCE_RESOLVED" if len(historical_ids) > 1 else "OFFICIAL_SINGLE_SOURCE_RESOLVED",
            "source_identities": historical_ids,
            "source_references": historical_refs,
        }
        observed_binding = {
            **observed_binding,
            "coverage_start": observed_dates[0],
            "coverage_end": observed_dates[-1],
            "session_count": len(observed_dates),
            "sessions_sha256": observed_sha,
            "lineage_status": "OFFICIAL_MULTI_SOURCE_RESOLVED" if len(observed_ids) > 1 else "OFFICIAL_SINGLE_SOURCE_RESOLVED",
            "source_identities": observed_ids,
            "source_references": observed_refs,
        }
    files = [
        ("execution_schedule", "schedule.json", schedule_bytes),
        ("execution_schedule_source", "official-source.pdf", b"official source"),
        (
            "historical_official_calendar",
            "historical_calendar/official_exchange_sessions_1260.csv",
            historical_calendar,
        ),
        (
            "historical_official_calendar_summary",
            "historical_calendar/exchange_session_summary.json",
            historical_summary,
        ),
        (
            "historical_official_calendar_sources",
            "historical_calendar/exchange_session_sources.csv",
            historical_sources,
        ),
        (
            "forward_observed_session_calendar",
            "forward_monitoring/calendar/exchange_sessions.csv",
            observed_calendar,
        ),
        (
            "forward_observed_session_calendar_summary",
            "forward_monitoring/calendar/exchange_session_summary.json",
            observed_summary,
        ),
        (
            "forward_observed_session_calendar_sources",
            "forward_monitoring/calendar/exchange_session_sources.csv",
            observed_sources,
        ),
        ("clean_panel", "panel.parquet", b"panel"),
        ("clean_security_master", "security_master.csv", b"ticker,listed_from,listed_to\nAAA,2020-01-01,\n"),
        ("model_manifest", "model/MANIFEST.json", b"{}"),
        ("model_control_h5", "model/v4_x1_clean_control_h5_final.joblib", b"control-h5"),
        ("model_control_h10", "model/v4_x1_clean_control_h10_final.joblib", b"control-h10"),
        ("model_challenger_h5", "model/v4_x1_clean_challenger_h5_final.joblib", b"challenger-h5"),
        ("model_challenger_h10", "model/v4_x1_clean_challenger_h10_final.joblib", b"challenger-h10"),
        ("model_fit_log", "model/v4_x1_clean_final_refit_log.json", b"[]"),
    ]
    refs = []
    roles = {}
    for role, relative, payload in files:
        key = "inputs/" + relative.replace("\\", "/")
        store.put_if_absent(key, payload, "application/octet-stream")
        refs.append(
            {
                "role": role,
                "key": key,
                "relative_path": relative,
                "sha256": sha256_bytes(payload),
                "content_type": (
                    "application/json"
                    if role.endswith("_summary")
                    else "text/csv"
                    if role.endswith("_calendar") or role.endswith("_sources")
                    else "application/octet-stream"
                ),
            }
        )
        roles[role] = relative
    body = {
        "schema_version": INPUT_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "execution_schedule_sha256": refs[0]["sha256"],
        "files": refs,
        "roles": roles,
        "calendar_contract": {
            "schema_version": CALENDAR_BINDING_SCHEMA_VERSION,
            "bindings": {
                "historical_official_calendar": historical_binding,
                "forward_observed_session_calendar": observed_binding,
            },
        },
    }
    body["manifest_payload_sha256"] = sha256_bytes(
        canonical_json_bytes({k: v for k, v in body.items() if k != "manifest_payload_sha256"})
    )
    raw = canonical_json_bytes(body)
    store.put_if_absent("inputs/manifest.json", raw, "application/json")
    manifest = CloudInputBundle.load(store, "inputs/manifest.json")
    return manifest.manifest_sha256, manifest.materialize(store, tmp_path / "materialized")


def _prepare_authoritative_reader(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    evidence_root: Path,
) -> None:
    listings = root / "listings"
    listings.mkdir(parents=True)
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
    ).to_csv(listings / "security_master.csv", index=False)
    prices = root / "prices" / "raw"
    prices.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "ticker": "AAAA",
                "date": pd.Timestamp("2026-08-03"),
                "raw_open": 100.0,
                "raw_high": 105.0,
                "raw_low": 99.0,
                "raw_close": 103.0,
                "raw_volume": 1000.0,
            }
        ]
    ).to_parquet(prices / "AAAA.parquet", index=False)

    def authoritative_calendar(paths: monitor.RuntimePaths, *, through=None):
        paths.calendar_root.mkdir(parents=True, exist_ok=True)
        for name in (
            "exchange_sessions.csv",
            "exchange_session_sources.csv",
            "exchange_session_summary.json",
        ):
            (paths.calendar_root / name).write_bytes(
                (evidence_root / name).read_bytes()
            )
        return pd.DatetimeIndex(pd.to_datetime(["2026-08-03"]))

    def fake_stock_summary(session, *, include_capture=False):
        session = pd.Timestamp(session).normalize()
        frame = pd.DataFrame(
            [
                {
                    "ticker": "AAAA",
                    "as_of_date": session,
                    "remarks": "",
                    "volume": 1000,
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
                    "as_of_date": session,
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
        raw_bytes = (
            b'{"data":[{"StockCode":"AAAA","Date":"2026-08-03"},'
            b'{"StockCode":"BBBB","Date":"2026-08-03"}],'
            b'"recordsTotal":2,"recordsFiltered":2}'
        )
        meta = StockSummaryFetchMeta(
            requested_date=session.date().isoformat(),
            source_ref="https://example.test/summary",
            records_total=2,
            rows=2,
            explicit_security_status_rows=0,
            regular_trade_evidence_rows=1,
            records_filtered=2,
            raw_sha256=sha256_bytes(raw_bytes),
            completeness_status="COMPLETE_RECORDS_TOTAL_SINGLE_RESPONSE",
        )
        capture = StockSummaryPayloadCapture(
            payload={"data": []},
            source_ref=meta.source_ref,
            raw_bytes=raw_bytes,
            endpoint=meta.source_ref,
            params={"date": session.strftime("%Y%m%d")},
            retrieval_started_at_utc="2026-08-03T10:00:00+00:00",
            observed_available_at_utc="2026-08-03T10:00:01+00:00",
            records_total=2,
            records_filtered=2,
            row_count=2,
            completeness_status="COMPLETE_RECORDS_TOTAL_SINGLE_RESPONSE",
        )
        return (frame, meta, capture) if include_capture else (frame, meta)

    def fake_index_summary(session, *, include_capture=False):
        session = pd.Timestamp(session).normalize()
        frame = pd.DataFrame(
            {
                "session_date": [session],
                "index_code": ["COMPOSITE"],
                "close": [100.0],
                "source": ["IDX_OFFICIAL"],
            }
        )
        capture = IndexSummaryPayloadCapture(
            payload={"data": []},
            source_ref="https://example.test/index-summary",
            raw_bytes=b'{"data":[{"IndexCode":"COMPOSITE"}]}',
            endpoint="https://example.test/index-summary",
            params={"date": session.strftime("%Y%m%d")},
            retrieval_started_at_utc="2026-08-03T10:00:00+00:00",
            observed_available_at_utc="2026-08-03T10:00:01+00:00",
            records_total=1,
            records_filtered=1,
            row_count=1,
            completeness_status="COMPLETE_RECORDS_TOTAL_SINGLE_RESPONSE",
        )
        meta = IndexSummaryFetchMeta(
            requested_date=session.date().isoformat(),
            source_ref=capture.source_ref,
            records_total=1,
            rows=1,
            records_filtered=1,
            retrieval_started_at_utc=capture.retrieval_started_at_utc,
            observed_available_at_utc=capture.observed_available_at_utc,
            raw_sha256=capture.raw_sha256,
            completeness_status=capture.completeness_status,
        )
        return (frame, meta, capture) if include_capture else (frame, meta)

    monkeypatch.setattr(monitor, "sync_forward_calendar", authoritative_calendar)
    monkeypatch.setattr(monitor, "fetch_stock_summary_snapshot", fake_stock_summary)
    monkeypatch.setattr(monitor, "fetch_index_summary_snapshot", fake_index_summary)


def _write_official_open_cloud_slot(
    store: LocalConditionalStore,
    *,
    session: str = "2026-08-24",
    slot: str = "0912",
    capture_at: datetime | None = None,
    commit_overrides: dict[str, object] | None = None,
    source_overrides: dict[str, object] | None = None,
    corrupt_child: str | None = None,
) -> dict[str, object]:
    raw = b"{}\n"
    open_prices = b"parquet-placeholder"
    if capture_at is None:
        capture_at = datetime.fromisoformat(f"{session}T09:13:00+07:00")
    source = {
        "session_date": session,
        "authority": AUTHORITY,
        "upstream_path": UPSTREAM_PATH,
        "field_semantics": FIELD_SEMANTICS,
        "transport": "DIRECT_IDX",
        "transport_policy": TRANSPORT_POLICY,
        "execution_grade": True,
        "raw_artifact_path": "raw_response.json",
        "normalized_artifact_path": "open_prices.parquet",
        "raw_artifact_sha256": sha256_bytes(raw),
        "normalized_artifact_sha256": sha256_bytes(open_prices),
        "capture_timestamp_jakarta": capture_at.isoformat(),
    }
    source.update(source_overrides or {})
    source_bytes = canonical_json_bytes(source)
    capture_root = f"session_date={session}/slot={slot}/captures/c1"
    artifacts: dict[str, dict[str, object]] = {}
    for name, payload in (
        ("raw_response", raw),
        ("open_prices", open_prices),
        ("source_manifest", source_bytes),
    ):
        key = f"{capture_root}/{name}.bin"
        store.put_if_absent(key, payload, "application/octet-stream")
        artifacts[name] = {"key": key, "sha256": sha256_bytes(payload)}
    if corrupt_child is not None:
        store._path(str(artifacts[corrupt_child]["key"])).write_bytes(b"corrupt")
    scheduled = datetime.combine(
        date.fromisoformat(session), OPEN_CLOUD_SLOT_TIMES[slot], tzinfo=cloud_runner.JAKARTA
    )
    commit: dict[str, object] = {
        "schema_version": OPEN_CLOUD_SCHEMA_VERSION,
        "commit_state": "COMMITTED",
        "session_date": session,
        "slot": slot,
        "capture_id": "20260824T091300Z-c1",
        "scheduled_capture_timestamp_jakarta": scheduled.isoformat(),
        "source_capture_timestamp_jakarta": capture_at.isoformat(),
        "capture_lag_seconds": (capture_at - scheduled).total_seconds(),
        "authority": AUTHORITY,
        "upstream_path": UPSTREAM_PATH,
        "field_semantics": FIELD_SEMANTICS,
        "source_transport": "DIRECT_IDX",
        "source_transport_policy": TRANSPORT_POLICY,
        "source_execution_grade": True,
        "execution_admission": OPEN_CLOUD_EXECUTION_ADMISSION,
        "artifacts": artifacts,
        "runner_provenance": {
            "runner": "GITHUB_ACTIONS",
            "github_event_name": "schedule",
            "capture_code_ref": PRODUCER_CAPTURE_CODE_REF,
        },
        "guards": {
            "model_accessed": False,
            "outcome_accessed": False,
            "paper_state_mutated": False,
            "forward_counter_mutated": False,
            "order_created": False,
            "fill_created": False,
            "retroactive_execution_authorized": False,
        },
    }
    commit.update(commit_overrides or {})
    key = f"session_date={session}/slot={slot}/slot_manifest.json"
    store.put_if_absent(key, canonical_json_bytes(commit), "application/json")
    return commit


def _run_synthetic_preopen_capture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[LocalConditionalStore, dict[str, object], object]:
    store = LocalConditionalStore(tmp_path / "store")
    _input_manifest(store, tmp_path)
    _write_official_open_cloud_slot(store)
    admission = materialize_official_open_from_cloud(
        store,
        session_date="2026-08-24",
        target_root=tmp_path / "admitted-open",
        eligibility_now=datetime.fromisoformat("2026-08-24T09:14:00+07:00"),
        expected_capture_code_ref=PRODUCER_CAPTURE_CODE_REF,
    )
    assert admission is not None
    monkeypatch.setenv("E2E_CLOUD_STORAGE_BACKEND", "local")
    monkeypatch.setenv("E2E_CLOUD_LOCAL_ROOT", str(tmp_path / "store"))
    monkeypatch.setenv("E2E_CLOUD_INPUT_MANIFEST_KEY", "inputs/manifest.json")
    monkeypatch.setenv("E2E_CLOUD_INPUT_ROOT", str(tmp_path / "inputs"))
    monkeypatch.setattr(cloud_runner, "build_cloud_store_from_env", lambda *a, **k: store)
    monkeypatch.setattr(
        cloud_runner,
        "_roots",
        lambda: {
            "paper": tmp_path / "paper",
            "forward": tmp_path / "forward",
            "official_open": tmp_path / "official-open",
            "ca": tmp_path / "ca",
        },
    )
    monkeypatch.setattr(
        cloud_runner,
        "wait_for_official_open_from_cloud",
        lambda *a, **k: dict(admission),
    )
    monkeypatch.setattr(
        cloud_runner,
        "_controller_config",
        lambda **kwargs: SimpleNamespace(base=object()),
    )
    monkeypatch.setattr(cloud_runner, "_config_missing", lambda config: None)
    monkeypatch.setattr(
        cloud_runner,
        "_now",
        lambda: datetime(2026, 8, 24, 9, 14, tzinfo=cloud_runner.JAKARTA),
    )
    monkeypatch.setattr(
        cloud_runner,
        "run_operational_cycle_v2",
        lambda *a, **k: {"controller_status": "EXECUTION_COMPLETE"},
    )
    result = cloud_runner.run_once(phase="PREOPEN", session_date="2026-08-24")
    assert result["status"] == "COMMITTED"
    commit = CloudPaperArchive(store).existing_commit("2026-08-24", "PREOPEN")
    assert commit is not None
    return store, admission, commit


def test_local_conditional_store_is_create_only(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    first = store.put_if_absent("a/b.bin", b"one", "application/octet-stream")
    second = store.put_if_absent("a/b.bin", b"one", "application/octet-stream")
    assert first.created is True
    assert second.created is False
    with pytest.raises(Exception):
        store.put_if_absent("a/b.bin", b"two", "application/octet-stream")


def test_input_bundle_requires_hashes_and_materializes_roles(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    manifest_sha, paths = _input_manifest(store, tmp_path)
    assert len(manifest_sha) == 64
    assert paths["execution_schedule"].is_file()
    bundle = CloudInputBundle.load(store, "inputs/manifest.json")
    schedule = load_schedule_from_bundle(bundle, paths)
    assert schedule.session_dates == ("2026-08-24", "2026-08-26")

    manifest = json.loads(store.read("inputs/manifest.json").decode("utf-8"))
    manifest["files"][1]["sha256"] = "0" * 64
    manifest["manifest_payload_sha256"] = sha256_bytes(
        canonical_json_bytes(
            {k: v for k, v in manifest.items() if k != "manifest_payload_sha256"}
        )
    )
    store.put_if_absent("bad.json", canonical_json_bytes(manifest), "application/json")
    bad = CloudInputBundle.load(store, "bad.json")
    with pytest.raises(CloudPaperRuntimeError, match="ARTIFACT_SHA_MISMATCH"):
        bad.materialize(store, tmp_path / "bad-materialized")


def test_historical_calendar_materialization_is_create_only(tmp_path: Path) -> None:
    source = tmp_path / "historical.csv"
    source.write_bytes(b"date\n2026-08-24\n2026-08-26\n")
    runtime_root = tmp_path / "forward"

    destination = materialize_historical_official_calendar(source, runtime_root)
    assert destination == runtime_root / "sessions" / "exchange_sessions.csv"
    assert destination.read_bytes() == source.read_bytes()
    assert materialize_historical_official_calendar(source, runtime_root) == destination

    destination.write_bytes(b"date\n2026-08-25\n")
    with pytest.raises(CloudPaperRuntimeError, match="LOCAL_COLLISION"):
        materialize_historical_official_calendar(source, runtime_root)


def test_forward_observed_calendar_materialization_is_create_only(tmp_path: Path) -> None:
    source = tmp_path / "observed.csv"
    source.write_bytes(b"date\n2026-08-24\n2026-08-26\n")
    runtime_root = tmp_path / "forward"

    destination = materialize_forward_observed_session_calendar(source, runtime_root)
    assert destination == runtime_root / "forward_monitoring" / "calendar" / "exchange_sessions.csv"
    assert destination.read_bytes() == source.read_bytes()
    assert materialize_forward_observed_session_calendar(source, runtime_root) == destination

    destination.write_bytes(b"date\n2026-08-25\n")
    with pytest.raises(CloudPaperRuntimeError, match="LOCAL_COLLISION"):
        materialize_forward_observed_session_calendar(source, runtime_root)


def _republish_manifest(
    store: LocalConditionalStore, key: str, manifest: dict[str, object]
) -> None:
    manifest["manifest_payload_sha256"] = sha256_bytes(
        canonical_json_bytes(
            {k: v for k, v in manifest.items() if k != "manifest_payload_sha256"}
        )
    )
    store.put_if_absent(key, canonical_json_bytes(manifest), "application/json")


def test_input_bundle_rejects_calendar_role_confusion(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    _input_manifest(store, tmp_path)
    manifest = json.loads(store.read("inputs/manifest.json").decode("utf-8"))
    manifest["calendar_contract"]["bindings"]["historical_official_calendar"]["calendar_role"] = (
        "forward_observed_session_calendar"
    )
    _republish_manifest(store, "inputs/role-confused.json", manifest)
    with pytest.raises(CloudPaperRuntimeError, match="ROLE_CONFUSION"):
        CloudInputBundle.load(store, "inputs/role-confused.json")


def test_input_bundle_rejects_stale_calendar_summary(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    _input_manifest(store, tmp_path)
    manifest = json.loads(store.read("inputs/manifest.json").decode("utf-8"))
    summary_ref = next(
        item
        for item in manifest["files"]
        if item["role"] == "forward_observed_session_calendar_summary"
    )
    stale = json.loads(store.read(summary_ref["key"]).decode("utf-8"))
    stale["exchange_sessions"] = 3
    stale_key = "inputs/forward_monitoring/calendar/stale-summary.json"
    stale_bytes = json.dumps(stale, sort_keys=True).encode()
    store.put_if_absent(stale_key, stale_bytes, "application/json")
    summary_ref["key"] = stale_key
    summary_ref["sha256"] = sha256_bytes(stale_bytes)
    _republish_manifest(store, "inputs/stale-summary.json", manifest)

    bundle = CloudInputBundle.load(store, "inputs/stale-summary.json")
    with pytest.raises(CloudPaperRuntimeError, match="SUMMARY_STALE"):
        bundle.materialize(store, tmp_path / "stale-materialized")


def test_input_bundle_rejects_unresolved_calendar_lineage(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    _input_manifest(store, tmp_path)
    manifest = json.loads(store.read("inputs/manifest.json").decode("utf-8"))
    binding = manifest["calendar_contract"]["bindings"]["forward_observed_session_calendar"]
    binding["lineage_status"] = "MULTI_SOURCE_OR_UNRESOLVED"
    _republish_manifest(store, "inputs/unresolved-lineage.json", manifest)
    with pytest.raises(CloudPaperRuntimeError, match="LINEAGE_UNRESOLVED"):
        CloudInputBundle.load(store, "inputs/unresolved-lineage.json")


def test_input_bundle_requires_every_model_child_artifact(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    _input_manifest(store, tmp_path)
    manifest = json.loads(store.read("inputs/manifest.json").decode("utf-8"))
    manifest["files"] = [
        item for item in manifest["files"] if item["role"] != "model_control_h5"
    ]
    manifest["roles"].pop("model_control_h5")
    manifest["manifest_payload_sha256"] = sha256_bytes(
        canonical_json_bytes(
            {k: v for k, v in manifest.items() if k != "manifest_payload_sha256"}
        )
    )
    store.put_if_absent("inputs/missing-model.json", canonical_json_bytes(manifest), "application/json")
    with pytest.raises(CloudPaperRuntimeError, match="REQUIRED_ROLE_MISSING"):
        CloudInputBundle.load(store, "inputs/missing-model.json")


def test_input_bundle_requires_historical_calendar_artifact(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    _input_manifest(store, tmp_path)
    manifest = json.loads(store.read("inputs/manifest.json").decode("utf-8"))
    manifest["files"] = [
        item for item in manifest["files"] if item["role"] != "historical_official_calendar"
    ]
    manifest["roles"].pop("historical_official_calendar")
    manifest["manifest_payload_sha256"] = sha256_bytes(
        canonical_json_bytes(
            {k: v for k, v in manifest.items() if k != "manifest_payload_sha256"}
        )
    )
    store.put_if_absent(
        "inputs/missing-historical-calendar.json",
        canonical_json_bytes(manifest),
        "application/json",
    )
    with pytest.raises(CloudPaperRuntimeError, match="REQUIRED_ROLE_MISSING"):
        CloudInputBundle.load(store, "inputs/missing-historical-calendar.json")


def test_input_bundle_requires_observed_calendar_artifact(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    _input_manifest(store, tmp_path)
    manifest = json.loads(store.read("inputs/manifest.json").decode("utf-8"))
    manifest["files"] = [
        item
        for item in manifest["files"]
        if item["role"] != "forward_observed_session_calendar"
    ]
    manifest["roles"].pop("forward_observed_session_calendar")
    _republish_manifest(store, "inputs/missing-observed-calendar.json", manifest)
    with pytest.raises(CloudPaperRuntimeError, match="REQUIRED_ROLE_MISSING"):
        CloudInputBundle.load(store, "inputs/missing-observed-calendar.json")


def test_input_bundle_rejects_stale_calendar_hash(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    _input_manifest(store, tmp_path)
    manifest = json.loads(store.read("inputs/manifest.json").decode("utf-8"))
    calendar_ref = next(
        item
        for item in manifest["files"]
        if item["role"] == "forward_observed_session_calendar"
    )
    calendar_ref["sha256"] = "0" * 64
    _republish_manifest(store, "inputs/stale-calendar-hash.json", manifest)
    bundle = CloudInputBundle.load(store, "inputs/stale-calendar-hash.json")
    with pytest.raises(CloudPaperRuntimeError, match="ARTIFACT_SHA_MISMATCH"):
        bundle.materialize(store, tmp_path / "stale-calendar-hash-materialized")


def test_input_bundle_rejects_source_report_month_mismatch(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    _input_manifest(store, tmp_path)
    manifest = json.loads(store.read("inputs/manifest.json").decode("utf-8"))
    source_ref = next(
        item
        for item in manifest["files"]
        if item["role"] == "historical_official_calendar_sources"
    )
    source_key = source_ref["key"]
    source_bytes = store.read(source_key)
    assert source_bytes is not None
    source_text = source_bytes.decode("utf-8")
    source_text = source_text.replace("2026,8,IDX_DIGITAL", "2026,9,IDX_DIGITAL", 1)
    mismatched = source_text.encode("utf-8")
    mismatched_key = "inputs/historical_calendar/month-mismatch.csv"
    store.put_if_absent(mismatched_key, mismatched, "text/csv")
    source_ref["key"] = mismatched_key
    source_ref["sha256"] = sha256_bytes(mismatched)
    _republish_manifest(store, "inputs/month-mismatch.json", manifest)

    bundle = CloudInputBundle.load(store, "inputs/month-mismatch.json")
    with pytest.raises(CloudPaperRuntimeError, match="SOURCE_REPORT_DATE_SCOPE_INVALID"):
        bundle.materialize(store, tmp_path / "month-mismatch-materialized")


def test_input_bundle_rejects_discontinuous_calendar_union(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    _input_manifest(store, tmp_path)
    manifest = json.loads(store.read("inputs/manifest.json").decode("utf-8"))
    binding = manifest["calendar_contract"]["bindings"][
        "forward_observed_session_calendar"
    ]
    binding["coverage_start"] = "2026-08-31"
    binding["coverage_end"] = "2026-09-02"
    _republish_manifest(store, "inputs/discontinuous-calendar.json", manifest)
    with pytest.raises(CloudPaperRuntimeError, match="COVERAGE_DISCONTINUOUS"):
        CloudInputBundle.load(store, "inputs/discontinuous-calendar.json")


def test_authoritative_calendar_payloads_bind_exact_roles_and_hashes(
    tmp_path: Path,
) -> None:
    if not AUTHORITATIVE_EVIDENCE_ROOT.is_dir():
        pytest.skip("authoritative calendar evidence root is unavailable")
    store = LocalConditionalStore(tmp_path / "store")
    _, paths = _input_manifest(
        store,
        tmp_path,
        authoritative_root=AUTHORITATIVE_EVIDENCE_ROOT,
        schedule_sessions=("2026-09-09",),
    )
    historical_source = AUTHORITATIVE_HISTORICAL_ROOT / "official_exchange_sessions_1260.csv"
    observed_source = (
        AUTHORITATIVE_EVIDENCE_ROOT
        / "forward_monitoring"
        / "calendar"
        / "exchange_sessions.csv"
    )
    assert paths["historical_official_calendar"].read_bytes() == historical_source.read_bytes()
    assert paths["forward_observed_session_calendar"].read_bytes() == observed_source.read_bytes()
    assert len(paths["historical_official_calendar"].read_text().splitlines()) - 1 == 1260
    assert len(paths["forward_observed_session_calendar"].read_text().splitlines()) - 1 == 26
    with paths["historical_official_calendar_sources"].open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        reconciled_rows = list(csv.DictReader(handle))
    assert len(reconciled_rows) == 64
    assert sum(int(row["sessions_in_requested_range"]) for row in reconciled_rows) == 1260
    assert {
        (row["year"], row["month"], row["sessions_in_requested_range"])
        for row in reconciled_rows
        if row["year"] == "2021" and row["month"] == "4"
    } == {("2021", "4", "2")}


def test_authoritative_root_rejects_unreconciled_historical_source_report(
    tmp_path: Path,
) -> None:
    if not AUTHORITATIVE_EVIDENCE_ROOT.is_dir():
        pytest.skip("authoritative calendar evidence root is unavailable")
    store = LocalConditionalStore(tmp_path / "store")
    _input_manifest(
        store,
        tmp_path,
        authoritative_root=AUTHORITATIVE_EVIDENCE_ROOT,
        schedule_sessions=("2026-09-09",),
    )
    manifest = json.loads(store.read("inputs/manifest.json").decode("utf-8"))
    exact_source = (
        AUTHORITATIVE_HISTORICAL_ROOT
        / "official_exchange_session_sources_1260.csv"
    ).read_bytes()
    exact_key = "inputs/exact-historical-source-report.csv"
    store.put_if_absent(exact_key, exact_source, "text/csv")
    source_ref = next(
        item
        for item in manifest["files"]
        if item["role"] == "historical_official_calendar_sources"
    )
    source_ref["key"] = exact_key
    source_ref["sha256"] = sha256_bytes(exact_source)
    exact_rows = list(
        csv.DictReader(io.StringIO(exact_source.decode("utf-8-sig"), newline=""))
    )
    manifest["calendar_contract"]["bindings"]["historical_official_calendar"][
        "source_references"
    ] = sorted({str(row["source_ref"]).strip() for row in exact_rows})
    _republish_manifest(store, "inputs/exact-root-unreconciled.json", manifest)

    bundle = CloudInputBundle.load(store, "inputs/exact-root-unreconciled.json")
    with pytest.raises(CloudPaperRuntimeError, match="SOURCE_REPORT_COVERAGE_MISMATCH"):
        bundle.materialize(store, tmp_path / "exact-root-materialized")


def test_authoritative_calendar_payloads_allow_post_eod_gate_offline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if not AUTHORITATIVE_EVIDENCE_ROOT.is_dir():
        pytest.skip("authoritative calendar evidence root is unavailable")
    store = LocalConditionalStore(tmp_path / "store")
    _input_manifest(
        store,
        tmp_path,
        authoritative_root=AUTHORITATIVE_EVIDENCE_ROOT,
        schedule_sessions=("2026-09-09",),
    )
    monkeypatch.setenv("E2E_CLOUD_STORAGE_BACKEND", "local")
    monkeypatch.setenv("E2E_CLOUD_LOCAL_ROOT", str(tmp_path / "store"))
    monkeypatch.setenv("E2E_CLOUD_INPUT_ROOT", str(tmp_path / "inputs"))
    roots = {
        "paper": tmp_path / "paper",
        "forward": tmp_path / "forward",
        "official_open": tmp_path / "official-open",
        "ca": tmp_path / "ca",
    }
    monkeypatch.setattr(cloud_runner, "build_cloud_store_from_env", lambda *a, **k: store)
    monkeypatch.setattr(cloud_runner, "_roots", lambda: roots)
    monkeypatch.setattr(
        cloud_runner,
        "_controller_config",
        lambda **kwargs: SimpleNamespace(base=object()),
    )
    monkeypatch.setattr(cloud_runner, "_config_missing", lambda config: None)
    monkeypatch.setattr(
        cloud_runner,
        "_now",
        lambda: datetime(2026, 9, 9, 18, 0, tzinfo=cloud_runner.JAKARTA),
    )
    calendar_probe: dict[str, object] = {}

    def fake_clean_pipeline(runtime_root: Path, *args, **kwargs):
        score_paths = SimpleNamespace(
            runtime_root=Path(runtime_root),
            calendar_root=Path(runtime_root) / "forward_monitoring" / "calendar",
        )
        sessions, sources = v4_score._local_official_sessions(
            score_paths, pd.Timestamp("2026-09-09")
        )
        calendar_probe.update(
            {
                "count": len(sessions),
                "first": sessions[0].date().isoformat(),
                "last": sessions[-1].date().isoformat(),
                "gap_dates_present": all(
                    pd.Timestamp(value) in set(sessions)
                    for value in (
                        "2026-08-03",
                        "2026-08-04",
                        "2026-08-05",
                        "2026-08-06",
                        "2026-08-07",
                    )
                ),
                "source_count": len(sources),
            }
        )
        return {
            "status": "PIPELINE_OK_NO_ELIGIBLE_SAME_DAY_X1_SCORE",
            "provider_calls": False,
            "protected_outcome_accessed": False,
            "model_refit": False,
        }

    monkeypatch.setattr(cloud_runner, "run_clean_eod_pipeline", fake_clean_pipeline)
    monkeypatch.setattr(
        cloud_runner,
        "run_operational_cycle_v2",
        lambda *a, **k: {"controller_status": "WAITING_UPSTREAM_EOD_SCORE"},
    )
    result = cloud_runner.run_once(phase="POST_EOD", session_date="2026-09-09")

    assert result["status"] == "WAITING"
    assert result["controller_status"] == "WAITING_UPSTREAM_EOD_SCORE"
    assert calendar_probe == {
        "count": 1286,
        "first": "2021-04-29",
        "last": "2026-09-09",
        "gap_dates_present": True,
        "source_count": 2,
    }
    assert "V4_X1_LOCAL_HISTORICAL_CALENDAR_MISSING" not in json.dumps(result)
    assert result["historical_official_calendar_sha256"] == sha256_bytes(
        (AUTHORITATIVE_HISTORICAL_ROOT / "official_exchange_sessions_1260.csv").read_bytes()
    )
    assert result["forward_observed_session_calendar_sha256"] == sha256_bytes(
        (
            AUTHORITATIVE_EVIDENCE_ROOT
            / "forward_monitoring"
            / "calendar"
            / "exchange_sessions.csv"
        ).read_bytes()
    )
    assert CloudPaperArchive(store).existing_commit("2026-09-09", "POST_EOD") is None


def test_authoritative_post_eod_artifact_is_accepted_by_intraday_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if not AUTHORITATIVE_EVIDENCE_ROOT.is_dir():
        pytest.skip("authoritative calendar evidence root is unavailable")
    eod_root = tmp_path / "eod"
    evidence_root = AUTHORITATIVE_EVIDENCE_ROOT / "forward_monitoring" / "calendar"
    _prepare_authoritative_reader(monkeypatch, eod_root, evidence_root)
    result = monitor.capture_session(eod_root, target_date=SESSION)
    assert result["status"] == "DATA_READY"
    paths = monitor.runtime_paths(eod_root)
    final_dir = paths.session_root / SESSION.date().isoformat()
    manifest_path = final_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["calendar_sha256"] == sha256_bytes(
        (paths.calendar_root / "exchange_sessions.csv").read_bytes()
    )
    assert monitor._verify_ready_artifacts(
        final_dir / "model_input.parquet",
        final_dir / "session_evidence.parquet",
        manifest_path,
        expected_session=SESSION.date().isoformat(),
        snapshot_sha256=manifest["snapshot_sha256"],
        evidence_sha256=manifest["evidence_sha256"],
        manifest_sha256=sha256_bytes(manifest_path.read_bytes()),
    )


def test_snapshot_is_deterministic_and_restore_is_fail_closed(tmp_path: Path) -> None:
    paper = tmp_path / "paper"
    forward = tmp_path / "forward"
    paper.mkdir()
    forward.mkdir()
    (paper / "state.json").write_text("state", encoding="utf-8")
    (forward / "calendar.csv").write_text("date\n2026-08-24\n", encoding="utf-8")
    roots = {"paper": paper, "forward": forward}
    first, first_sha, metadata = build_runtime_snapshot(roots)
    second, second_sha, _ = build_runtime_snapshot(roots)
    assert first == second
    assert first_sha == second_sha
    target_paper = tmp_path / "restored-paper"
    target_forward = tmp_path / "restored-forward"
    counts = restore_runtime_snapshot(
        first,
        {"paper": target_paper, "forward": target_forward},
        expected_sha256=first_sha,
    )
    assert counts == {"paper": 1, "forward": 1}
    assert (target_paper / "state.json").read_text(encoding="utf-8") == "state"
    with pytest.raises(CloudPaperRuntimeError):
        restore_runtime_snapshot(b"bad", {"paper": target_paper}, expected_sha256=first_sha)
    assert metadata["file_count"] == 2


def test_stage_commit_is_idempotent_and_replay_verifies_children(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    archive = CloudPaperArchive(store)
    snapshot, snapshot_sha, metadata = build_runtime_snapshot({"paper": tmp_path / "empty"})
    result = {
        "observed_started_at_utc": "2026-08-24T11:00:00+00:00",
        "observed_finished_at_utc": "2026-08-24T11:01:00+00:00",
        "controller_status": "POST_EOD_PREPARED",
    }
    commit = archive.commit_stage(
        session_date="2026-08-24",
        stage="POST_EOD",
        status="POST_EOD_PREPARED",
        run_id="run-1",
        snapshot_bytes=snapshot,
        snapshot_sha256=snapshot_sha,
        snapshot_metadata=metadata,
        result_payload=result,
        schedule_attestation_sha256="1" * 64,
        input_manifest_sha256="2" * 64,
        code_identity={"commit": "3" * 40},
    )
    replay = archive.existing_commit("2026-08-24", "POST_EOD")
    assert replay is not None
    assert replay.commit_sha256 == commit.commit_sha256
    result_path = store._path(replay.result_key)
    result_path.write_bytes(b"tampered")
    with pytest.raises(CloudPaperRuntimeError, match="RESULT_INVALID"):
        archive.existing_commit("2026-08-24", "POST_EOD")


def test_stage_commit_rejects_existing_schedule_or_input_identity_conflict(
    tmp_path: Path,
) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    archive = CloudPaperArchive(store)
    snapshot, snapshot_sha, metadata = build_runtime_snapshot({"paper": tmp_path / "empty"})
    common = {
        "session_date": "2026-08-24",
        "stage": "POST_EOD",
        "status": "POST_EOD_PREPARED",
        "snapshot_bytes": snapshot,
        "snapshot_sha256": snapshot_sha,
        "snapshot_metadata": metadata,
        "result_payload": {
            "observed_started_at_utc": "2026-08-24T11:00:00+00:00",
            "observed_finished_at_utc": "2026-08-24T11:01:00+00:00",
        },
        "schedule_attestation_sha256": "1" * 64,
        "input_manifest_sha256": "2" * 64,
        "code_identity": {"commit": "3" * 40},
    }
    archive.commit_stage(run_id="run-1", **common)
    with pytest.raises(CloudPaperRuntimeError, match="SCHEDULE_IDENTITY_CONFLICT"):
        archive.commit_stage(
            run_id="run-2",
            **{**common, "schedule_attestation_sha256": "4" * 64},
        )
    with pytest.raises(CloudPaperRuntimeError, match="INPUT_IDENTITY_CONFLICT"):
        archive.commit_stage(
            run_id="run-3",
            **{**common, "input_manifest_sha256": "5" * 64},
        )


def test_latest_snapshot_prefers_later_post_eod_state_for_next_preopen_restore(
    tmp_path: Path,
) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    archive = CloudPaperArchive(store)
    common = {
        "schedule_attestation_sha256": "1" * 64,
        "input_manifest_sha256": "2" * 64,
        "code_identity": {"commit": "3" * 40},
    }
    snapshots: dict[str, tuple[bytes, str]] = {}

    def commit_snapshot(stage: str, marker: str) -> str:
        root = tmp_path / marker
        root.mkdir()
        (root / "state.txt").write_text(marker, encoding="utf-8")
        snapshot, snapshot_sha, metadata = build_runtime_snapshot({"paper": root})
        committed = archive.commit_stage(
            session_date="2026-08-24",
            stage=stage,
            status="EXECUTION_COMPLETE" if stage == "PREOPEN" else "POST_EOD_PREPARED",
            run_id=marker,
            snapshot_bytes=snapshot,
            snapshot_sha256=snapshot_sha,
            snapshot_metadata=metadata,
            result_payload={
                "observed_started_at_utc": "2026-08-24T02:00:00+00:00",
                "observed_finished_at_utc": "2026-08-24T02:01:00+00:00",
            },
            **common,
        )
        snapshots[stage] = (snapshot, snapshot_sha)
        return committed.snapshot_sha256 or ""

    pre_sha = commit_snapshot("PREOPEN", "d0-preopen")
    post_sha = commit_snapshot("POST_EOD", "d0-post-eod")
    replay = archive.commit_stage(
        session_date="2026-08-24",
        stage="POST_EOD",
        status="POST_EOD_PREPARED",
        run_id="d0-post-eod-retry",
        snapshot_bytes=snapshots["POST_EOD"][0],
        snapshot_sha256=snapshots["POST_EOD"][1],
        snapshot_metadata={},
        result_payload={
            "observed_started_at_utc": "2026-08-24T02:00:00+00:00",
            "observed_finished_at_utc": "2026-08-24T02:01:00+00:00",
        },
        **common,
    )
    assert replay.snapshot_sha256 == post_sha
    assert post_sha != pre_sha

    # This is the D+1 PREOPEN restore point: D1 has no committed state yet,
    # so D0 POST_EOD must be the newest lifecycle state.
    restored = archive.latest_snapshot(
        ["2026-08-24", "2026-08-25"], before_or_equal="2026-08-25"
    )
    assert restored is not None
    restored_bytes, restored_sha, _ = restored
    assert restored_sha == post_sha
    with zipfile.ZipFile(io.BytesIO(restored_bytes)) as bundle:
        names = bundle.namelist()
        assert any(name.endswith("state.txt") for name in names)
        state_name = next(name for name in names if name.endswith("state.txt"))
        assert bundle.read(state_name) == b"d0-post-eod"


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("wrong_schema", "ADMISSION_INVALID:schema_version"),
        ("wrong_admission", "ADMISSION_INVALID:execution_admission"),
        ("missing_guards", "ADMISSION_GUARDS_INVALID"),
        ("source_session_mismatch", "SOURCE_MANIFEST_INVALID"),
        ("malformed_capture_timestamp", "SOURCE_CAPTURE_TIMESTAMP_INVALID"),
        ("outside_window", "OUTSIDE_PROSPECTIVE_WINDOW"),
        ("corrupt_child", "ARTIFACT_SHA_MISMATCH:open_prices"),
        ("manual_capture", "MANUAL_CAPTURE_FORBIDDEN"),
        ("old_provenance", "MANUAL_CAPTURE_FORBIDDEN"),
        ("missing_capture_code_ref", "CAPTURE_CODE_REF_GIT_SHA_INVALID"),
        ("malformed_capture_code_ref", "CAPTURE_CODE_REF_GIT_SHA_INVALID"),
        ("wrong_capture_code_ref", "CAPTURE_CODE_REF_MISMATCH"),
        ("future_capture", "FUTURE_CAPTURE"),
    ],
)
def test_official_open_cloud_admission_rejects_invalid_outer_or_timing_contract(
    tmp_path: Path, kind: str, expected: str
) -> None:
    store = LocalConditionalStore(tmp_path / "official")
    overrides: dict[str, object] = {}
    source_overrides: dict[str, object] = {}
    capture_at = datetime.fromisoformat("2026-08-24T09:13:00+07:00")
    now = datetime.fromisoformat("2026-08-24T09:14:00+07:00")
    corrupt_child = None
    if kind == "wrong_schema":
        overrides["schema_version"] = "wrong-schema"
    elif kind == "wrong_admission":
        overrides["execution_admission"] = "EXECUTION_ADMITTED"
    elif kind == "missing_guards":
        overrides["guards"] = {}
    elif kind == "source_session_mismatch":
        source_overrides["session_date"] = "2026-08-23"
    elif kind == "malformed_capture_timestamp":
        source_overrides["capture_timestamp_jakarta"] = "not-a-timestamp"
    elif kind == "outside_window":
        capture_at = datetime.fromisoformat("2026-08-24T09:23:00+07:00")
        overrides["slot"] = "0922"
    elif kind == "corrupt_child":
        corrupt_child = "open_prices"
    elif kind == "manual_capture":
        overrides["runner_provenance"] = {
            "runner": "GITHUB_ACTIONS",
            "github_event_name": "workflow_dispatch",
        }
    elif kind == "old_provenance":
        overrides["runner_provenance"] = {
            "runner": "GITHUB_ACTIONS",
            "capture_code_ref": "8a96a3d9caebfbd2c0235234e9394afc04693efa",
        }
    elif kind == "missing_capture_code_ref":
        overrides["runner_provenance"] = {
            "runner": "GITHUB_ACTIONS",
            "github_event_name": "schedule",
        }
    elif kind == "malformed_capture_code_ref":
        overrides["runner_provenance"] = {
            "runner": "GITHUB_ACTIONS",
            "github_event_name": "schedule",
            "capture_code_ref": "not-a-commit-sha",
        }
    elif kind == "wrong_capture_code_ref":
        overrides["runner_provenance"] = {
            "runner": "GITHUB_ACTIONS",
            "github_event_name": "schedule",
            "capture_code_ref": "5" * 40,
        }
    elif kind == "future_capture":
        now = datetime.fromisoformat("2026-08-24T09:12:30+07:00")

    _write_official_open_cloud_slot(
        store,
        slot=str(overrides.pop("slot", "0912")),
        capture_at=capture_at,
        commit_overrides=overrides,
        source_overrides=source_overrides,
        corrupt_child=corrupt_child,
    )
    with pytest.raises(CloudPaperRuntimeError, match=expected):
        materialize_official_open_from_cloud(
            store,
            session_date="2026-08-24",
            target_root=tmp_path / "local-open",
            eligibility_now=now,
            expected_capture_code_ref=PRODUCER_CAPTURE_CODE_REF,
        )


def test_old_1800_capture_is_not_execution_admissible(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "official")
    _write_official_open_cloud_slot(
        store,
        capture_at=datetime.fromisoformat("2026-08-24T18:00:00+07:00"),
    )
    with pytest.raises(CloudPaperRuntimeError, match="EXECUTION_WINDOW_CLOSED"):
        materialize_official_open_from_cloud(
            store,
            session_date="2026-08-24",
            target_root=tmp_path / "local-open",
            eligibility_now=datetime.fromisoformat("2026-08-24T18:01:00+07:00"),
            expected_capture_code_ref=PRODUCER_CAPTURE_CODE_REF,
        )


def test_valid_scheduled_official_open_cloud_capture_is_admitted(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "official")
    _write_official_open_cloud_slot(store)
    result = materialize_official_open_from_cloud(
        store,
        session_date="2026-08-24",
        target_root=tmp_path / "local-open",
        eligibility_now=datetime.fromisoformat("2026-08-24T09:14:00+07:00"),
        expected_capture_code_ref=PRODUCER_CAPTURE_CODE_REF,
    )
    assert result is not None
    assert result["execution_admitted"] is True


def test_official_open_cloud_materialization_verifies_referenced_artifacts(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "official")
    commit = _write_official_open_cloud_slot(store)
    artifacts = commit["artifacts"]
    assert isinstance(artifacts, dict)
    slot = "0912"
    result = materialize_official_open_from_cloud(
        store,
        session_date="2026-08-24",
        target_root=tmp_path / "local-open",
        eligibility_now=datetime.fromisoformat("2026-08-24T09:14:00+07:00"),
        expected_capture_code_ref=PRODUCER_CAPTURE_CODE_REF,
    )
    assert result is not None
    assert result["slot"] == slot
    assert (tmp_path / "local-open" / "2026-08-24" / "manifest.json").is_file()

    store._path(artifacts["open_prices"]["key"]).write_bytes(b"changed")
    with pytest.raises(CloudPaperRuntimeError, match="ARTIFACT_SHA_MISMATCH"):
        materialize_official_open_from_cloud(
            store,
            session_date="2026-08-24",
            target_root=tmp_path / "other-open",
            eligibility_now=datetime.fromisoformat("2026-08-24T09:14:00+07:00"),
            expected_capture_code_ref=PRODUCER_CAPTURE_CODE_REF,
        )


def test_official_open_cloud_admission_requires_expected_producer_pin(tmp_path: Path) -> None:
    store = LocalConditionalStore(tmp_path / "official")
    _write_official_open_cloud_slot(store)
    with pytest.raises(CloudPaperRuntimeError, match="EXPECTED_CAPTURE_CODE_REF_GIT_SHA_INVALID"):
        materialize_official_open_from_cloud(
            store,
            session_date="2026-08-24",
            target_root=tmp_path / "local-open",
            eligibility_now=datetime.fromisoformat("2026-08-24T09:14:00+07:00"),
            expected_capture_code_ref="",
        )


def test_holiday_commits_noop_without_invoking_existing_engines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    _input_manifest(store, tmp_path)
    monkeypatch.setenv("E2E_CLOUD_STORAGE_BACKEND", "local")
    monkeypatch.setenv("E2E_CLOUD_LOCAL_ROOT", str(tmp_path / "store"))
    monkeypatch.setenv("E2E_CLOUD_INPUT_MANIFEST_KEY", "inputs/manifest.json")
    monkeypatch.setenv("E2E_CLOUD_INPUT_ROOT", str(tmp_path / "inputs"))
    monkeypatch.setattr(
        cloud_runner,
        "_roots",
        lambda: {
            "paper": tmp_path / "paper",
            "forward": tmp_path / "forward",
            "official_open": tmp_path / "official-open",
            "ca": tmp_path / "ca",
        },
    )
    monkeypatch.setattr(cloud_runner, "run_clean_eod_pipeline", lambda *a, **k: (_ for _ in ()).throw(AssertionError("engine invoked")))
    monkeypatch.setattr(cloud_runner, "run_operational_cycle_v2", lambda *a, **k: (_ for _ in ()).throw(AssertionError("controller invoked")))
    monkeypatch.setattr(
        cloud_runner,
        "_now",
        lambda: datetime(2026, 8, 25, 18, 0, tzinfo=cloud_runner.JAKARTA),
    )

    first = cloud_runner.run_once(phase="POST_EOD", session_date="2026-08-25")
    second = cloud_runner.run_once(phase="POST_EOD", session_date="2026-08-25")
    assert first["status"] == "COMMITTED"
    assert first["controller_status"] == "WEEKEND_OR_HOLIDAY_NOOP"
    assert second["status"] == "ALREADY_COMMITTED"


def test_waiting_upstream_does_not_create_terminal_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    _input_manifest(store, tmp_path)
    monkeypatch.setenv("E2E_CLOUD_STORAGE_BACKEND", "local")
    monkeypatch.setenv("E2E_CLOUD_LOCAL_ROOT", str(tmp_path / "store"))
    monkeypatch.setenv("E2E_CLOUD_INPUT_ROOT", str(tmp_path / "inputs"))
    monkeypatch.setattr(
        cloud_runner,
        "_roots",
        lambda: {
            "paper": tmp_path / "paper",
            "forward": tmp_path / "forward",
            "official_open": tmp_path / "official-open",
            "ca": tmp_path / "ca",
        },
    )
    monkeypatch.setattr(cloud_runner, "run_clean_eod_pipeline", lambda *a, **k: None)
    monkeypatch.setattr(
        cloud_runner,
        "_controller_config",
        lambda **kwargs: SimpleNamespace(base=object()),
    )
    monkeypatch.setattr(cloud_runner, "_config_missing", lambda config: None)
    monkeypatch.setattr(
        cloud_runner,
        "_now",
        lambda: datetime(2026, 8, 24, 18, 0, tzinfo=cloud_runner.JAKARTA),
    )
    monkeypatch.setattr(
        cloud_runner,
        "run_operational_cycle_v2",
        lambda *a, **k: {"controller_status": "WAITING_UPSTREAM_EOD_SCORE"},
    )

    result = cloud_runner.run_once(phase="POST_EOD", session_date="2026-08-24")
    assert result["status"] == "WAITING"
    assert (
        tmp_path / "forward" / "sessions" / "exchange_sessions.csv"
    ).read_bytes() == b"date\n2026-08-20\n2026-08-21\n"
    assert CloudPaperArchive(store).existing_commit("2026-08-24", "POST_EOD") is None


def test_open_unavailable_keeps_preopen_outcome_uncommitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    _input_manifest(store, tmp_path)
    monkeypatch.setenv("E2E_CLOUD_STORAGE_BACKEND", "local")
    monkeypatch.setenv("E2E_CLOUD_LOCAL_ROOT", str(tmp_path / "store"))
    monkeypatch.setenv("E2E_CLOUD_INPUT_ROOT", str(tmp_path / "inputs"))
    monkeypatch.setenv("E2E_CLOUD_OFFICIAL_OPEN_PREFIX", "official-open-v1")
    monkeypatch.setattr(
        cloud_runner,
        "_roots",
        lambda: {
            "paper": tmp_path / "paper",
            "forward": tmp_path / "forward",
            "official_open": tmp_path / "official-open",
            "ca": tmp_path / "ca",
        },
    )
    monkeypatch.setattr(cloud_runner, "build_cloud_store_from_env", lambda *a, **k: store)
    monkeypatch.setattr(cloud_runner, "materialize_official_open_from_cloud", lambda *a, **k: None)
    monkeypatch.setattr(cloud_runner, "wait_for_official_open_from_cloud", lambda *a, **k: None)
    monkeypatch.setattr(
        cloud_runner,
        "_controller_config",
        lambda **kwargs: SimpleNamespace(base=object()),
    )
    monkeypatch.setattr(cloud_runner, "_config_missing", lambda config: None)
    monkeypatch.setattr(
        cloud_runner,
        "_now",
        lambda: datetime(2026, 8, 24, 9, 12, tzinfo=cloud_runner.JAKARTA),
    )
    monkeypatch.setattr(
        cloud_runner,
        "run_operational_cycle_v2",
        lambda *a, **k: {"controller_status": "WAITING_OFFICIAL_OPEN"},
    )

    result = cloud_runner.run_once(phase="PREOPEN", session_date="2026-08-24")
    assert result["status"] == "WAITING"
    assert result["official_open_cloud_admission"] is None
    assert CloudPaperArchive(store).existing_commit("2026-08-24", "PREOPEN") is None


def test_preopen_commit_persists_and_replays_exact_official_open_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, admission, commit = _run_synthetic_preopen_capture(tmp_path, monkeypatch)
    raw_result = store.read(commit.result_key)
    assert raw_result is not None
    result_payload = json.loads(raw_result.decode("utf-8"))
    persisted = result_payload["controller_result"]["official_open_cloud_admission"]
    assert persisted == admission
    assert persisted["session_date"] == "2026-08-24"
    assert persisted["slot"] == "0912"
    assert persisted["execution_admitted"] is True
    assert persisted["expected_producer_capture_code_ref"] == PRODUCER_CAPTURE_CODE_REF
    assert persisted["actual_producer_capture_code_ref"] == PRODUCER_CAPTURE_CODE_REF
    assert persisted["scheduled_capture_timestamp_jakarta"] == "2026-08-24T09:12:00+07:00"
    assert persisted["source_capture_timestamp_jakarta"] == "2026-08-24T09:13:00+07:00"
    assert persisted["capture_lag_seconds"] == 60.0
    replay = CloudPaperArchive(store).existing_commit("2026-08-24", "PREOPEN")
    assert replay is not None
    replay_result = json.loads(store.read(replay.result_key).decode("utf-8"))
    assert replay_result["controller_result"]["official_open_cloud_admission"] == persisted

    retry = cloud_runner.run_once(phase="PREOPEN", session_date="2026-08-24")
    assert retry["status"] == "ALREADY_COMMITTED"
    assert retry["commit_sha256"] == commit.commit_sha256


def test_preopen_admission_identity_tampering_fails_closed_on_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, _, commit = _run_synthetic_preopen_capture(tmp_path, monkeypatch)
    raw_result = store.read(commit.result_key)
    assert raw_result is not None
    result_payload = json.loads(raw_result.decode("utf-8"))
    result_payload["controller_result"]["official_open_cloud_admission"]["slot"] = "0902"
    store._path(commit.result_key).write_bytes(canonical_json_bytes(result_payload))
    with pytest.raises(CloudPaperRuntimeError, match="CLOUD_STAGE_COMMIT_RESULT_INVALID"):
        CloudPaperArchive(store).existing_commit("2026-08-24", "PREOPEN")


def test_runner_rejects_retroactive_explicit_session_without_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cloud_runner,
        "_now",
        lambda: datetime(2026, 8, 26, 18, 0, tzinfo=cloud_runner.JAKARTA),
    )
    with pytest.raises(CloudPaperRuntimeError, match="RETROACTIVE_SESSION_FORBIDDEN"):
        cloud_runner.run_once(phase="POST_EOD", session_date="2026-08-25")


def test_runner_preflights_operational_dependencies_before_eod_engine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    _input_manifest(store, tmp_path)
    monkeypatch.setenv("E2E_CLOUD_STORAGE_BACKEND", "local")
    monkeypatch.setenv("E2E_CLOUD_LOCAL_ROOT", str(tmp_path / "store"))
    monkeypatch.setenv("E2E_CLOUD_INPUT_ROOT", str(tmp_path / "inputs"))
    monkeypatch.setattr(
        cloud_runner,
        "_roots",
        lambda: {
            "paper": tmp_path / "paper",
            "forward": tmp_path / "forward",
            "official_open": tmp_path / "official-open",
            "ca": tmp_path / "ca",
        },
    )
    monkeypatch.setattr(
        cloud_runner,
        "_now",
        lambda: datetime(2026, 8, 24, 18, 0, tzinfo=cloud_runner.JAKARTA),
    )
    monkeypatch.setattr(
        cloud_runner,
        "_controller_config",
        lambda **kwargs: SimpleNamespace(base=object()),
    )
    monkeypatch.setattr(
        cloud_runner,
        "_config_missing",
        lambda config: "MISSING_OPERATIONAL_CONFIG:provider_checkout",
    )
    monkeypatch.setattr(
        cloud_runner,
        "run_clean_eod_pipeline",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("EOD engine must not run before preflight")
        ),
    )
    with pytest.raises(CloudPaperRuntimeError, match="OPERATIONAL_PREREQUISITE"):
        cloud_runner.run_once(phase="POST_EOD", session_date="2026-08-24")


def test_controller_failure_does_not_create_terminal_stage_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = LocalConditionalStore(tmp_path / "store")
    _input_manifest(store, tmp_path)
    monkeypatch.setenv("E2E_CLOUD_STORAGE_BACKEND", "local")
    monkeypatch.setenv("E2E_CLOUD_LOCAL_ROOT", str(tmp_path / "store"))
    monkeypatch.setenv("E2E_CLOUD_INPUT_ROOT", str(tmp_path / "inputs"))
    monkeypatch.setattr(
        cloud_runner,
        "_roots",
        lambda: {
            "paper": tmp_path / "paper",
            "forward": tmp_path / "forward",
            "official_open": tmp_path / "official-open",
            "ca": tmp_path / "ca",
        },
    )
    monkeypatch.setattr(
        cloud_runner,
        "_now",
        lambda: datetime(2026, 8, 24, 18, 0, tzinfo=cloud_runner.JAKARTA),
    )
    monkeypatch.setattr(cloud_runner, "run_clean_eod_pipeline", lambda *a, **k: None)
    monkeypatch.setattr(
        cloud_runner,
        "_controller_config",
        lambda **kwargs: SimpleNamespace(base=object()),
    )
    monkeypatch.setattr(cloud_runner, "_config_missing", lambda config: None)
    monkeypatch.setattr(
        cloud_runner,
        "run_operational_cycle_v2",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("controller crash")),
    )
    with pytest.raises(RuntimeError, match="controller crash"):
        cloud_runner.run_once(phase="POST_EOD", session_date="2026-08-24")
    assert CloudPaperArchive(store).existing_commit("2026-08-24", "POST_EOD") is None


def test_preopen_wait_accepts_producer_commit_after_consumer_starts(
    tmp_path: Path,
) -> None:
    current = [datetime.fromisoformat("2026-08-24T09:12:00+07:00")]
    calls = {"materialize": 0}

    def now() -> datetime:
        return current[0]

    def sleep(seconds: float) -> None:
        current[0] += timedelta(seconds=seconds)

    def materialize(*args: object, **kwargs: object) -> dict[str, object] | None:
        del args, kwargs
        calls["materialize"] += 1
        if calls["materialize"] == 1:
            return None
        return {"execution_admitted": True}

    original = cloud_runner.materialize_official_open_from_cloud
    cloud_runner.materialize_official_open_from_cloud = materialize  # type: ignore[assignment]
    try:
        result = cloud_runner.wait_for_official_open_from_cloud(
            LocalConditionalStore(tmp_path / "store"),
            session_date="2026-08-24",
            target_root=tmp_path / "open",
            expected_capture_code_ref=PRODUCER_CAPTURE_CODE_REF,
            now_fn=now,
            sleep_fn=sleep,
            poll_interval_seconds=5,
            max_wait_seconds=30,
        )
    finally:
        cloud_runner.materialize_official_open_from_cloud = original
    assert result == {"execution_admitted": True}
    assert calls["materialize"] == 2
    assert current[0] == datetime.fromisoformat("2026-08-24T09:12:05+07:00")


def test_preopen_final_slot_wait_accepts_commit_before_hard_deadline(
    tmp_path: Path,
) -> None:
    current = [datetime.fromisoformat("2026-08-24T09:22:55+07:00")]
    calls = {"materialize": 0}

    def now() -> datetime:
        return current[0]

    def sleep(seconds: float) -> None:
        current[0] += timedelta(seconds=seconds)

    def materialize(*args: object, **kwargs: object) -> dict[str, object] | None:
        del args, kwargs
        calls["materialize"] += 1
        return None if calls["materialize"] == 1 else {"execution_admitted": True}

    original = cloud_runner.materialize_official_open_from_cloud
    cloud_runner.materialize_official_open_from_cloud = materialize  # type: ignore[assignment]
    try:
        result = cloud_runner.wait_for_official_open_from_cloud(
            LocalConditionalStore(tmp_path / "store"),
            session_date="2026-08-24",
            target_root=tmp_path / "open",
            expected_capture_code_ref=PRODUCER_CAPTURE_CODE_REF,
            now_fn=now,
            sleep_fn=sleep,
            poll_interval_seconds=5,
            max_wait_seconds=30,
        )
    finally:
        cloud_runner.materialize_official_open_from_cloud = original
    assert result == {"execution_admitted": True}
    assert current[0] == datetime.fromisoformat("2026-08-24T09:22:59+07:00")


def test_preopen_wait_does_not_poll_after_hard_deadline(tmp_path: Path) -> None:
    current = [datetime.fromisoformat("2026-08-24T09:22:58+07:00")]
    calls = {"materialize": 0}

    def now() -> datetime:
        return current[0]

    def sleep(seconds: float) -> None:
        current[0] += timedelta(seconds=seconds)

    def materialize(*args: object, **kwargs: object) -> None:
        del args, kwargs
        calls["materialize"] += 1
        return None

    original = cloud_runner.materialize_official_open_from_cloud
    cloud_runner.materialize_official_open_from_cloud = materialize  # type: ignore[assignment]
    try:
        result = cloud_runner.wait_for_official_open_from_cloud(
            LocalConditionalStore(tmp_path / "store"),
            session_date="2026-08-24",
            target_root=tmp_path / "open",
            expected_capture_code_ref=PRODUCER_CAPTURE_CODE_REF,
            now_fn=now,
            sleep_fn=sleep,
            poll_interval_seconds=5,
            max_wait_seconds=30,
        )
    finally:
        cloud_runner.materialize_official_open_from_cloud = original
    assert result is None
    assert calls["materialize"] == 2
    assert current[0].time().isoformat() == OFFICIAL_OPEN_EXECUTION_END.isoformat()


def test_producer_commit_after_hard_deadline_is_not_consumed(tmp_path: Path) -> None:
    current = [datetime.fromisoformat("2026-08-24T09:23:00+07:00")]
    calls = {"materialize": 0}

    def now() -> datetime:
        return current[0]

    def materialize(*args: object, **kwargs: object) -> dict[str, object]:
        del args, kwargs
        calls["materialize"] += 1
        return {"execution_admitted": True}

    original = cloud_runner.materialize_official_open_from_cloud
    cloud_runner.materialize_official_open_from_cloud = materialize  # type: ignore[assignment]
    try:
        result = cloud_runner.wait_for_official_open_from_cloud(
            LocalConditionalStore(tmp_path / "store"),
            session_date="2026-08-24",
            target_root=tmp_path / "open",
            expected_capture_code_ref=PRODUCER_CAPTURE_CODE_REF,
            now_fn=now,
            sleep_fn=lambda _: None,
        )
    finally:
        cloud_runner.materialize_official_open_from_cloud = original
    assert result is None
    assert calls["materialize"] == 0


def test_preopen_wait_stops_when_producer_never_commits(tmp_path: Path) -> None:
    current = [datetime.fromisoformat("2026-08-24T09:13:00+07:00")]
    calls = {"materialize": 0}

    def now() -> datetime:
        return current[0]

    def sleep(seconds: float) -> None:
        current[0] += timedelta(seconds=seconds)

    def materialize(*args: object, **kwargs: object) -> None:
        del args, kwargs
        calls["materialize"] += 1
        return None

    original = cloud_runner.materialize_official_open_from_cloud
    cloud_runner.materialize_official_open_from_cloud = materialize  # type: ignore[assignment]
    try:
        result = cloud_runner.wait_for_official_open_from_cloud(
            LocalConditionalStore(tmp_path / "store"),
            session_date="2026-08-24",
            target_root=tmp_path / "open",
            expected_capture_code_ref=PRODUCER_CAPTURE_CODE_REF,
            now_fn=now,
            sleep_fn=sleep,
            poll_interval_seconds=5,
            max_wait_seconds=10,
        )
    finally:
        cloud_runner.materialize_official_open_from_cloud = original
    assert result is None
    assert calls["materialize"] == 3
    assert current[0] == datetime.fromisoformat("2026-08-24T09:13:10+07:00")
