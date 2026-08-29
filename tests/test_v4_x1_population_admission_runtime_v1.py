from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade import forward_monitoring
from idx_trade.forward_ohlcv import SESSION_OHLCV_COLUMNS
from idx_trade.providers.idx import IDX_DELISTING_URL, IDX_STOCK_LIST_URL
from idx_trade.provenance import sha256_file, write_manifest_atomic
from idx_trade.storage import write_parquet_atomic
from idx_trade.v4_x1_population_admission_v1 import (
    PROVEN_V1_POPULATION_COMPATIBLE,
    V1_POPULATION_NOT_PROVABLE,
    build_runtime_population_admission,
    classify_retained_population_attestation,
    persist_population_attestation,
)


SESSION = "2026-08-28"


def _write_runtime_fixture(
    tmp_path: Path,
    *,
    current_listed_to: str | None = None,
    point_state: str = "ACTIVE",
    tradability_state: str = "ACTIVE",
    include_model: bool = True,
    include_tradability: bool = True,
    refresh_overrides: dict[str, object] | None = None,
) -> dict[str, Path | str]:
    runtime_root = tmp_path / "runtime"
    paths = forward_monitoring.runtime_paths(runtime_root)
    session_root = paths.session_root / SESSION
    session_root.mkdir(parents=True)

    baseline = tmp_path / "frozen" / "security_master.csv"
    baseline.parent.mkdir(parents=True)
    baseline.write_text(
        "ticker,listed_from,listed_to,source\nAAAA,2020-01-01,,FROZEN\n",
        encoding="utf-8",
    )
    current = paths.listings_root / "security_master.csv"
    current.parent.mkdir(parents=True)
    listed_to = "" if current_listed_to is None else current_listed_to
    current.write_text(
        f"ticker,listed_from,listed_to,source\nAAAA,2020-01-01,{listed_to},RUNTIME\n",
        encoding="utf-8",
    )
    refresh_manifest = current.with_name("security_master_refresh_manifest.json")
    refresh_payload: dict[str, object] = {
        "schema_version": "idx_e2e_cloud_runtime_security_master_v1",
        "authority": "IDX",
        "semantics": "CURRENT_LISTING_IDENTITY_REFERENCE_WITH_POST_FREEZE_DELISTING_HISTORY",
        "observed_at_jakarta": "2026-08-28T18:35:00+07:00",
        "observed_date": SESSION,
        "freeze_local_date": "2026-08-20",
        "baseline_path": str(baseline.resolve()),
        "baseline_sha256": sha256_file(baseline),
        "active_source": IDX_STOCK_LIST_URL,
        "active_completeness": "RECORDS_TOTAL_EXACT_SINGLE_RESPONSE",
        "delisting_source": IDX_DELISTING_URL,
        "delisting_completeness": "MONTHLY_META_TOTAL_ITEMS_EXHAUSTIVE_PAGINATION",
        "security_master_path": str(current.resolve()),
        "security_master_sha256": sha256_file(current),
        "guards": {
            "outcome_accessed": False,
            "protected_forward_accessed": False,
            "model_refit": False,
            "paper_state_mutated": False,
            "retroactive_capture_authorized": False,
        },
    }
    refresh_payload.update(refresh_overrides or {})
    write_manifest_atomic(refresh_manifest, refresh_payload)

    if include_tradability:
        intervals = paths.tradability_root / "tradability_intervals.csv"
        anchors = paths.tradability_root / "idx_stock_summary_anchors.csv"
        intervals.parent.mkdir(parents=True, exist_ok=True)
        intervals.write_text(
            "ticker,market,state,effective_from,effective_to,announced_at,source,source_ref\n"
            f"AAAA,REGULAR,{tradability_state},2020-01-01,,,IDX,idx://interval\n",
            encoding="utf-8",
        )
        anchors.write_text(
            "ticker,market,as_of_date,state,source,source_ref,evidence_type\n"
            f"AAAA,REGULAR,{SESSION},{tradability_state},IDX,idx://anchor,OFFICIAL_STATUS_SNAPSHOT\n",
            encoding="utf-8",
        )

    snapshot = pd.DataFrame(
        {
            "ticker": ["AAAA"] if include_model else [],
            "date": [SESSION] if include_model else [],
            "high": [11.0] if include_model else [],
            "low": [9.0] if include_model else [],
            "close": [10.0] if include_model else [],
            "volume": [100.0] if include_model else [],
            "regular_market_value": [1000.0] if include_model else [],
        }
    )
    evidence = pd.DataFrame(
        {"ticker": ["AAAA"], "session_date": [SESSION], "point_state": [point_state]}
    )
    session_ohlcv = pd.DataFrame(
        {
            "ticker": ["AAAA"] if include_model else [],
            "session_date": [SESSION] if include_model else [],
            "open": [10.0] if include_model else [],
            "high": [11.0] if include_model else [],
            "low": [9.0] if include_model else [],
            "close": [10.0] if include_model else [],
            "volume": [100.0] if include_model else [],
            "source": ["TEST"] if include_model else [],
            "source_ref": ["test://ohlcv"] if include_model else [],
            "source_sha256": ["a" * 64] if include_model else [],
            "observed_retrieved_at_utc": [None] if include_model else [],
        }
    )
    snapshot_path = session_root / "model_input.parquet"
    evidence_path = session_root / "session_evidence.parquet"
    ohlcv_path = session_root / "session_ohlcv.parquet"
    write_parquet_atomic(snapshot, snapshot_path)
    write_parquet_atomic(evidence, evidence_path)
    write_parquet_atomic(session_ohlcv.loc[:, SESSION_OHLCV_COLUMNS], ohlcv_path)

    stock_raw = session_root / "idx_stock_summary.raw.json"
    stock = session_root / "idx_stock_summary.csv"
    index_raw = session_root / "idx_index_summary.raw.json"
    index = session_root / "idx_index_summary.csv"
    calendar = paths.calendar_root / "exchange_sessions.csv"
    stock_raw.write_text(json.dumps({"data": []}), encoding="utf-8")
    stock.write_text(f"ticker,as_of_date\nAAAA,{SESSION}\n", encoding="utf-8")
    index_raw.write_text(json.dumps({"data": []}), encoding="utf-8")
    index.write_text(f"index_code,session_date\nCOMPOSITE,{SESSION}\n", encoding="utf-8")
    calendar.parent.mkdir(parents=True, exist_ok=True)
    calendar.write_text(f"date\n{SESSION}\n", encoding="utf-8")

    manifest = {
        "schema_version": forward_monitoring.MONITOR_SCHEMA_VERSION,
        "status": "DATA_READY",
        "session_date": SESSION,
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
        "model_input_rows": int(len(snapshot)),
        "point_evidence_rows": int(len(evidence)),
        "snapshot_path": str(snapshot_path.resolve()),
        "snapshot_sha256": sha256_file(snapshot_path),
        "evidence_path": str(evidence_path.resolve()),
        "evidence_sha256": sha256_file(evidence_path),
        "session_ohlcv_path": str(ohlcv_path.resolve()),
        "session_ohlcv_sha256": sha256_file(ohlcv_path),
        "stock_summary_raw_path": str(stock_raw.resolve()),
        "stock_summary_raw_sha256": sha256_file(stock_raw),
        "stock_summary_path": str(stock.resolve()),
        "stock_summary_sha256": sha256_file(stock),
        "stock_summary_source": {"session_date": SESSION},
        "index_summary_raw_path": str(index_raw.resolve()),
        "index_summary_raw_sha256": sha256_file(index_raw),
        "index_summary_path": str(index.resolve()),
        "index_summary_sha256": sha256_file(index),
        "index_summary_source": {"session_date": SESSION},
        "calendar_path": str(calendar.resolve()),
        "calendar_sha256": sha256_file(calendar),
    }
    manifest_path = session_root / "manifest.json"
    write_manifest_atomic(manifest_path, manifest)

    connection = forward_monitoring._connect(paths)
    try:
        connection.execute(
            """
            INSERT INTO session_snapshots(
                session_date, state, snapshot_path, snapshot_sha256,
                evidence_path, evidence_sha256, manifest_path, manifest_sha256,
                updated_at
            ) VALUES (?, 'DATA_READY', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                SESSION,
                str(snapshot_path.resolve()),
                sha256_file(snapshot_path),
                str(evidence_path.resolve()),
                sha256_file(evidence_path),
                str(manifest_path.resolve()),
                sha256_file(manifest_path),
                "2026-08-28T18:35:00+00:00",
            ),
        )
    finally:
        connection.close()

    model_root = tmp_path / "models"
    model_root.mkdir()
    model_manifest = model_root / "MANIFEST.json"
    model_manifest.write_text('{"model": "frozen-test"}\n', encoding="utf-8")
    clean_panel = tmp_path / "clean_panel.parquet"
    write_parquet_atomic(
        pd.DataFrame({"ticker": ["AAAA"], "date": ["2026-08-19"], "close": [10.0]}),
        clean_panel,
    )
    runner = Path(__file__).resolve().parents[1] / "scripts" / "run_e2e_paper_cloud_v2.py"
    return {
        "runtime_root": runtime_root,
        "clean_panel": clean_panel,
        "clean_security_master": baseline,
        "model_root": model_root,
        "repo_root": Path(__file__).resolve().parents[1],
        "observed_by": "2026-08-28T11:35:00+00:00",
        "input_manifest_sha256": "b" * 64,
        "runner_path": runner,
        "expected_baseline_sha256": sha256_file(baseline),
        "expected_model_manifest_sha256": sha256_file(model_manifest),
    }


def test_build_runtime_population_admission_uses_real_data_ready_fixture(tmp_path: Path) -> None:
    fixture = _write_runtime_fixture(tmp_path)
    admission = build_runtime_population_admission(**fixture)

    assert admission.status == "SAFE_V1_POPULATION"
    assert admission.expected_identity_tickers == ("AAAA",)
    assert admission.observed_model_input_tickers == ("AAAA",)
    assert admission.metadata["population_proof_scope"] == "IDENTITY_TRADABILITY_COMPATIBILITY_ONLY"
    assert admission.metadata["final_scoring_population_attested"] is False
    paths = forward_monitoring.runtime_paths(fixture["runtime_root"])
    refresh_manifest = paths.listings_root / "security_master_refresh_manifest.json"
    assert admission.metadata["runtime_tradability_evidence_bound"] is True
    assert admission.metadata["security_master_refresh_manifest_sha256"] == sha256_file(
        refresh_manifest
    )
    assert admission.metadata["tradability_intervals_sha256"] == sha256_file(
        paths.tradability_root / "tradability_intervals.csv"
    )
    assert admission.metadata["tradability_anchors_sha256"] == sha256_file(
        paths.tradability_root / "idx_stock_summary_anchors.csv"
    )


def test_build_runtime_population_admission_vetoes_shared_listed_to_change(
    tmp_path: Path,
) -> None:
    fixture = _write_runtime_fixture(tmp_path, current_listed_to="2026-08-27")
    admission = build_runtime_population_admission(**fixture)

    assert admission.status == V1_POPULATION_NOT_PROVABLE
    assert "SHARED_IDENTITY_CURRENT_CONFLICT:AAAA" in admission.reason_codes
    assert admission.expected_identity_tickers == ("AAAA",)


def test_runtime_explicit_suspension_conflicts_with_active_stock_summary_point(
    tmp_path: Path,
) -> None:
    fixture = _write_runtime_fixture(
        tmp_path,
        point_state="ACTIVE",
        tradability_state="SUSPENDED",
    )
    admission = build_runtime_population_admission(**fixture)

    assert admission.status == V1_POPULATION_NOT_PROVABLE
    assert "TRADABILITY_CONFLICT:AAAA" in admission.reason_codes


def test_runtime_missing_canonical_tradability_artifact_fails_closed(
    tmp_path: Path,
) -> None:
    fixture = _write_runtime_fixture(tmp_path, include_tradability=False)
    admission = build_runtime_population_admission(**fixture)

    assert admission.status == V1_POPULATION_NOT_PROVABLE
    assert "TRADABILITY_INTERVAL_ARTIFACT_MISSING" in admission.reason_codes


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"observed_date": "2026-08-27"}, "CURRENT_IDENTITY_REFRESH_OBSERVED_DATE_MISMATCH"),
        ({"authority": "NOT_IDX"}, "CURRENT_IDENTITY_REFRESH_AUTHORITY_INVALID"),
        ({"active_completeness": "PARTIAL"}, "CURRENT_IDENTITY_REFRESH_ACTIVE_COMPLETENESS_INVALID"),
        ({"delisting_completeness": "PARTIAL"}, "CURRENT_IDENTITY_REFRESH_DELISTING_COMPLETENESS_INVALID"),
        ({"security_master_sha256": "0" * 64}, "CURRENT_IDENTITY_REFRESH_MASTER_HASH_MISMATCH"),
        ({"baseline_sha256": "1" * 64}, "CURRENT_IDENTITY_REFRESH_BASELINE_HASH_MISMATCH"),
    ],
)
def test_runtime_refresh_manifest_freshness_and_completeness_are_strict(
    tmp_path: Path,
    overrides: dict[str, object],
    reason: str,
) -> None:
    fixture = _write_runtime_fixture(tmp_path, refresh_overrides=overrides)
    admission = build_runtime_population_admission(**fixture)

    assert admission.status == V1_POPULATION_NOT_PROVABLE
    assert reason in admission.reason_codes


def test_runtime_same_bytes_fresh_manifest_is_idempotently_admissible(tmp_path: Path) -> None:
    fixture = _write_runtime_fixture(tmp_path)
    first = build_runtime_population_admission(**fixture)
    second = build_runtime_population_admission(**fixture)

    assert first.status == second.status == "SAFE_V1_POPULATION"
    assert first.metadata["security_master_refresh_manifest_sha256"] == second.metadata[
        "security_master_refresh_manifest_sha256"
    ]


def test_runtime_safe_attestation_binds_refresh_and_tradability_artifacts(
    tmp_path: Path,
) -> None:
    fixture = _write_runtime_fixture(tmp_path)
    admission = build_runtime_population_admission(**fixture)
    persisted = persist_population_attestation(fixture["runtime_root"], admission)
    payload = json.loads(Path(persisted.attestation_path).read_text(encoding="utf-8"))

    assert payload["metadata"]["runtime_tradability_evidence_bound"] is True
    assert payload["metadata"]["security_master_refresh_manifest_sha256"] == admission.metadata[
        "security_master_refresh_manifest_sha256"
    ]
    assert payload["metadata"]["tradability_intervals_sha256"] == admission.metadata[
        "tradability_intervals_sha256"
    ]
    assert payload["metadata"]["tradability_anchors_sha256"] == admission.metadata[
        "tradability_anchors_sha256"
    ]
    assert (
        classify_retained_population_attestation(
            payload,
            expected_session_date=SESSION,
            expected_baseline_sha256=fixture["expected_baseline_sha256"],
        )
        == PROVEN_V1_POPULATION_COMPATIBLE
    )
