from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade import forward_monitoring as monitor
from idx_trade import v4_x1_clean_eod_legacy_compat as calendar_compat
from idx_trade import v4_x1_eod_legacy_compat as calendar_verifier
from idx_trade.forward_ohlcv import SESSION_OHLCV_COLUMNS
from idx_trade.provenance import sha256_file, write_manifest_atomic
from idx_trade.storage import write_parquet_atomic
from scripts import run_e2e_paper_cloud_v1 as cloud_runner


EARLIER = "2026-08-10"
LATER = "2026-08-11"


def _write_modern_ready_fixture(tmp_path: Path) -> tuple[Path, monitor.RuntimePaths, Path]:
    runtime_root = tmp_path / "runtime"
    paths = monitor.runtime_paths(runtime_root)
    session_dir = paths.session_root / EARLIER
    session_dir.mkdir(parents=True)

    snapshot = pd.DataFrame(
        {
            "ticker": ["AAAA"],
            "date": [EARLIER],
            "high": [11.0],
            "low": [9.0],
            "close": [10.0],
            "volume": [100.0],
            "regular_market_value": [1_000.0],
        }
    )
    evidence = pd.DataFrame(
        {"ticker": ["AAAA"], "session_date": [EARLIER], "point_state": ["ACTIVE"]}
    )
    session_ohlcv = pd.DataFrame(
        {
            "ticker": ["AAAA"],
            "session_date": [EARLIER],
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

    snapshot_path = session_dir / "model_input.parquet"
    evidence_path = session_dir / "session_evidence.parquet"
    ohlcv_path = session_dir / "session_ohlcv.parquet"
    write_parquet_atomic(snapshot, snapshot_path)
    write_parquet_atomic(evidence, evidence_path)
    write_parquet_atomic(session_ohlcv.loc[:, SESSION_OHLCV_COLUMNS], ohlcv_path)

    stock_raw = session_dir / "idx_stock_summary.raw.json"
    stock = session_dir / "idx_stock_summary.csv"
    index_raw = session_dir / "idx_index_summary.raw.json"
    index = session_dir / "idx_index_summary.csv"
    stock_raw.write_text(json.dumps({"data": []}), encoding="utf-8")
    stock.write_text(f"ticker,as_of_date\nAAAA,{EARLIER}\n", encoding="utf-8")
    index_raw.write_text(json.dumps({"data": []}), encoding="utf-8")
    index.write_text(
        f"index_code,session_date\nCOMPOSITE,{EARLIER}\n", encoding="utf-8"
    )

    calendar = paths.calendar_root / "exchange_sessions.csv"
    calendar.parent.mkdir(parents=True)
    calendar.write_text(f"date\n{EARLIER}\n", encoding="utf-8")

    manifest = {
        "schema_version": monitor.MONITOR_SCHEMA_VERSION,
        "status": "DATA_READY",
        "session_date": EARLIER,
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
        "stock_summary_source": {
            "session_date": EARLIER,
            "completeness_status": "COMPLETE_RECORDS_TOTAL_SINGLE_RESPONSE",
        },
        "index_summary_raw_path": str(index_raw.resolve()),
        "index_summary_raw_sha256": sha256_file(index_raw),
        "index_summary_path": str(index.resolve()),
        "index_summary_sha256": sha256_file(index),
        "index_summary_source": {
            "session_date": EARLIER,
            "completeness_status": "COMPLETE_RECORDS_TOTAL_SINGLE_RESPONSE",
        },
        "calendar_path": str(calendar.resolve()),
        "calendar_sha256": sha256_file(calendar),
    }
    manifest_path = session_dir / "manifest.json"
    write_manifest_atomic(manifest_path, manifest)

    connection = monitor._connect(paths)
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
                EARLIER,
                str(snapshot_path.resolve()),
                sha256_file(snapshot_path),
                str(evidence_path.resolve()),
                sha256_file(evidence_path),
                str(manifest_path.resolve()),
                sha256_file(manifest_path),
                "2026-09-15T12:42:00+00:00",
            ),
        )
    finally:
        connection.close()
    return runtime_root, paths, calendar


def _ready_row(paths: monitor.RuntimePaths) -> dict[str, object]:
    row = monitor._existing_session(paths, pd.Timestamp(EARLIER))
    assert row is not None
    return dict(row)


def test_cloud_path_preserves_ready_row_across_canonical_calendar_extension(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime_root, paths, calendar = _write_modern_ready_fixture(tmp_path)
    row = _ready_row(paths)
    original_verifier = monitor._verify_ready_row
    assert original_verifier(row) is True

    original_calendar_sha = str(
        json.loads(Path(str(row["manifest_path"])).read_text(encoding="utf-8"))[
            "calendar_sha256"
        ]
    )
    calendar.write_text(f"date\n{EARLIER}\n{LATER}\n", encoding="utf-8")
    sessions = monitor._read_sessions(calendar)

    assert sha256_file(calendar) != original_calendar_sha
    assert calendar_verifier._db_core_artifacts_still_exact(row) is True
    assert original_verifier(row) is False
    assert monitor._earliest_missing(paths, sessions) == pd.Timestamp(EARLIER)

    monkeypatch.setattr(
        monitor, "sync_forward_calendar", lambda paths_arg, *, through=None: sessions
    )
    monkeypatch.setattr(
        monitor, "_claim_session", lambda paths_arg, session: ("ALREADY_FETCHING", None)
    )
    with pytest.raises(
        ValueError,
        match=f"earliest={EARLIER} requested={LATER}",
    ):
        monitor.capture_session(runtime_root, target_date=LATER)

    observed: dict[str, object] = {}

    def fake_clean_pipeline(runtime_root_arg, model_root_arg, **kwargs):
        del model_root_arg, kwargs
        observed["earliest_missing"] = monitor._earliest_missing(paths, sessions)
        return monitor.capture_session(runtime_root_arg, target_date=LATER)

    monkeypatch.setattr(
        calendar_compat.clean_pipeline,
        "run_clean_eod_pipeline",
        fake_clean_pipeline,
    )
    result = cloud_runner.run_clean_eod_pipeline(
        runtime_root,
        tmp_path / "models",
        clean_panel=tmp_path / "clean-panel.parquet",
        clean_security_master=tmp_path / "security-master.csv",
        repo_root=tmp_path,
        observed_by="2026-09-15T12:42:00+00:00",
    )

    assert result == {
        "status": "FETCHING",
        "session_date": LATER,
        "idempotent": True,
    }
    assert observed["earliest_missing"] == pd.Timestamp(LATER)
    assert monitor._verify_ready_row is original_verifier
    assert monitor._earliest_missing(paths, sessions) == pd.Timestamp(EARLIER)


@pytest.mark.parametrize(
    "mutation",
    (
        "substituted_calendar_path",
        "removed_ready_session",
        "duplicate_calendar",
        "malformed_calendar",
        "snapshot",
        "evidence",
        "manifest",
    ),
)
def test_scoped_calendar_extension_rejects_non_append_or_core_mutation(
    tmp_path: Path,
    mutation: str,
) -> None:
    _, paths, calendar = _write_modern_ready_fixture(tmp_path)
    calendar.write_text(f"date\n{EARLIER}\n{LATER}\n", encoding="utf-8")
    row = _ready_row(paths)

    if mutation == "substituted_calendar_path":
        substituted = tmp_path / "substituted-calendar.csv"
        substituted.write_text(f"date\n{EARLIER}\n{LATER}\n", encoding="utf-8")
        manifest_path = Path(str(row["manifest_path"]))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["calendar_path"] = str(substituted.resolve())
        write_manifest_atomic(manifest_path, manifest)
        row["manifest_sha256"] = sha256_file(manifest_path)
    elif mutation == "removed_ready_session":
        calendar.write_text(f"date\n{LATER}\n", encoding="utf-8")
    elif mutation == "duplicate_calendar":
        calendar.write_text(
            f"date\n{EARLIER}\n{EARLIER}\n{LATER}\n", encoding="utf-8"
        )
    elif mutation == "malformed_calendar":
        calendar.write_text(f"date\n{EARLIER}\nnot-a-date\n", encoding="utf-8")
    elif mutation == "snapshot":
        Path(str(row["snapshot_path"])).write_bytes(b"tampered")
    elif mutation == "evidence":
        Path(str(row["evidence_path"])).write_bytes(b"tampered")
    elif mutation == "manifest":
        manifest_path = Path(str(row["manifest_path"]))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["unexpected_mutation"] = True
        write_manifest_atomic(manifest_path, manifest)
    else:  # pragma: no cover - parameter list is closed above
        raise AssertionError(mutation)

    verify = calendar_verifier.build_scoped_ready_verifier(
        paths.runtime_root, monitor._verify_ready_row
    )
    assert verify(row) is False


def test_cloud_calendar_compat_restores_verifier_after_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_verifier = monitor._verify_ready_row

    def fail_pipeline(*args, **kwargs):
        del args, kwargs
        assert monitor._verify_ready_row is not original_verifier
        raise RuntimeError("synthetic pipeline failure")

    monkeypatch.setattr(
        calendar_compat.clean_pipeline,
        "run_clean_eod_pipeline",
        fail_pipeline,
    )

    with pytest.raises(RuntimeError, match="synthetic pipeline failure"):
        cloud_runner.run_clean_eod_pipeline(
            tmp_path / "runtime",
            tmp_path / "models",
            clean_panel=tmp_path / "clean-panel.parquet",
            clean_security_master=tmp_path / "security-master.csv",
            repo_root=tmp_path,
        )

    assert monitor._verify_ready_row is original_verifier
