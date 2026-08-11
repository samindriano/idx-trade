from __future__ import annotations

from pathlib import Path

import pandas as pd

from idx_trade import forward_model_runtime as model_runtime
from idx_trade import forward_monitoring as base
from idx_trade import forward_monitoring_runtime as runtime


def _ready_session(root: Path, session: str = "2026-08-10") -> None:
    paths = base.runtime_paths(root)
    paths.calendar_root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"date": [session]}).to_csv(paths.calendar_root / "exchange_sessions.csv", index=False)
    connection = base._connect(paths)
    try:
        connection.execute(
            """
            INSERT INTO session_snapshots(
                session_date, state, snapshot_path, snapshot_sha256,
                evidence_path, evidence_sha256, manifest_path, manifest_sha256,
                updated_at
            ) VALUES (?, 'DATA_READY', ?, 'snapshot', ?, 'evidence', ?, 'manifest', 'now')
            """,
            (session, str(root / "snapshot.parquet"), str(root / "evidence.parquet"), str(root / "manifest.json")),
        )
    finally:
        connection.close()


def test_ensure_model_runs_is_idempotent_and_queues_both_frozen_models(tmp_path: Path) -> None:
    _ready_session(tmp_path)
    paths = base.runtime_paths(tmp_path)

    assert model_runtime.ensure_model_runs(paths) == 2
    assert model_runtime.ensure_model_runs(paths) == 0

    connection = base._connect(paths)
    try:
        rows = connection.execute(
            "SELECT session_date, model_id, generation, state FROM model_runs ORDER BY model_id"
        ).fetchall()
    finally:
        connection.close()

    assert [tuple(row) for row in rows] == [
        ("2026-08-10", "HGB_XS_MARKET", "V2", "QUEUED"),
        ("2026-08-10", "V3-B-STRUCTURE-LITE-V1-CANDIDATE-005", "V3", "QUEUED"),
    ]


def test_capture_completion_requests_model_worker(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, list[str]]] = []

    monkeypatch.setattr(
        runtime.base,
        "capture_session",
        lambda *args, **kwargs: {"status": "DATA_READY", "session_date": "2026-08-10"},
    )
    monkeypatch.setattr(
        model_runtime,
        "request_model_worker",
        lambda root, dates: calls.append((str(root), list(dates))) or True,
    )

    result = runtime.capture_session(tmp_path, target_date="2026-08-10")

    assert result["status"] == "DATA_READY"
    assert calls == [(str(tmp_path), ["2026-08-10"])]


def test_status_requests_model_worker_for_existing_data_ready_session(tmp_path: Path, monkeypatch) -> None:
    _ready_session(tmp_path)
    calls: list[tuple[str, list[str]]] = []

    monkeypatch.setattr(
        model_runtime,
        "request_model_worker",
        lambda root, dates: calls.append((str(root), list(dates))) or True,
    )

    status = runtime.monitoring_status(tmp_path)

    assert status["data_ready_sessions"] == 1
    assert calls == [(str(tmp_path), ["2026-08-10"])]


def test_request_model_worker_does_not_spawn_without_queued_jobs(tmp_path: Path, monkeypatch) -> None:
    _ready_session(tmp_path)
    paths = base.runtime_paths(tmp_path)
    assert model_runtime.ensure_model_runs(paths) == 2

    connection = base._connect(paths)
    try:
        connection.execute("UPDATE model_runs SET state='DONE'")
        connection.commit()
    finally:
        connection.close()

    monkeypatch.setattr(
        model_runtime.subprocess,
        "Popen",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("worker must not spawn")),
    )

    assert model_runtime.request_model_worker(tmp_path) is False
