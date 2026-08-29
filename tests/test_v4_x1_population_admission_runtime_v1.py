from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from idx_trade import forward_monitoring
from idx_trade.forward_ohlcv import SESSION_OHLCV_COLUMNS
from idx_trade.provenance import sha256_file, write_manifest_atomic
from idx_trade.storage import write_parquet_atomic
from idx_trade.v4_x1_population_admission_v1 import (
    V1_POPULATION_NOT_PROVABLE,
    build_runtime_population_admission,
)


SESSION = "2026-08-28"


def _write_runtime_fixture(tmp_path: Path, *, current_listed_to: str | None = None) -> dict[str, Path | str]:
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
    write_manifest_atomic(
        refresh_manifest,
        {
            "security_master_path": str(current.resolve()),
            "security_master_sha256": sha256_file(current),
            "baseline_sha256": sha256_file(baseline),
            "guards": {
                "outcome_accessed": False,
                "protected_forward_accessed": False,
            },
        },
    )

    snapshot = pd.DataFrame(
        {
            "ticker": ["AAAA"],
            "date": [SESSION],
            "high": [11.0],
            "low": [9.0],
            "close": [10.0],
            "volume": [100.0],
            "regular_market_value": [1000.0],
        }
    )
    evidence = pd.DataFrame(
        {"ticker": ["AAAA"], "session_date": [SESSION], "point_state": ["ACTIVE"]}
    )
    session_ohlcv = pd.DataFrame(
        {
            "ticker": ["AAAA"],
            "session_date": [SESSION],
            "open": [10.0],
            "high": [11.0],
            "low": [9.0],
            "close": [10.0],
            "volume": [100.0],
            "source": ["TEST"],
            "source_ref": ["test://ohlcv"],
            "source_sha256": ["a" * 64],
            "observed_retrieved_at_utc": [None],
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
        "model_input_rows": 1,
        "point_evidence_rows": 1,
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


def test_build_runtime_population_admission_vetoes_shared_listed_to_change(
    tmp_path: Path,
) -> None:
    fixture = _write_runtime_fixture(tmp_path, current_listed_to="2026-08-27")
    admission = build_runtime_population_admission(**fixture)

    assert admission.status == V1_POPULATION_NOT_PROVABLE
    assert "SHARED_IDENTITY_CURRENT_CONFLICT:AAAA" in admission.reason_codes
    assert admission.expected_identity_tickers == ("AAAA",)
