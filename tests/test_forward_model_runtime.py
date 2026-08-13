from __future__ import annotations

from pathlib import Path
import json

import pandas as pd
import pytest

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


def test_o2_uses_existing_model_run_fanout_only_after_freeze_and_ohlcv_ready(tmp_path: Path) -> None:
    _ready_session(tmp_path, session="2026-08-12")
    paths = base.runtime_paths(tmp_path)
    session_dir = paths.session_root / "2026-08-12"
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "session_ohlcv.parquet").write_bytes(b"fixture")

    assert model_runtime.ensure_model_runs(paths) == 3
    connection = base._connect(paths)
    try:
        row = connection.execute(
            "SELECT state, error_code FROM model_runs WHERE session_date=? AND model_id=?",
            ("2026-08-12", model_runtime.O2_MODEL_ID),
        ).fetchone()
    finally:
        connection.close()
    assert tuple(row) == ("QUEUED", None)


def test_o2_mixed_session_retains_flat_row_and_scores_only_valid_geometry() -> None:
    frame = pd.DataFrame(
        {
            "ticker": ["VALID", "FLAT"],
            "session_date": ["2026-08-12", "2026-08-12"],
            "open": [10.0, 50.0],
            "high": [11.0, 50.0],
            "low": [9.0, 50.0],
        }
    )

    geometry = model_runtime._derive_o2_geometry(frame)

    assert geometry["o2_geometry_valid"].tolist() == [True, False]
    assert geometry.loc[1, "o2_geometry_reason"] == "FLAT_RANGE_ZERO_DENOMINATOR"
    assert pd.isna(geometry.loc[1, "open_position"])


def test_o2_counter_accepts_mixed_session_without_row_level_geometry_failure(tmp_path: Path) -> None:
    paths = base.runtime_paths(tmp_path)
    sessions = pd.DatetimeIndex(pd.to_datetime(["2026-08-11", "2026-08-12"]))

    before, after = model_runtime._register_o2_counter(paths, sessions, session_index=2)

    assert (before, after) == (0, 1)
    state = json.loads((paths.monitor_root / model_runtime.O2_COUNTER_FILENAME).read_text(encoding="utf-8"))
    assert state["session_count"] == 1
    assert state["last_session_index"] == 2
    assert state["outcomes_accessed"] is False


def test_o2_mixed_session_scores_valid_row_and_keeps_flat_row_unscored(tmp_path: Path, monkeypatch) -> None:
    paths = base.runtime_paths(tmp_path)
    session_key = "2026-08-12"
    ohlcv_path = paths.session_root / session_key / "session_ohlcv.parquet"
    ohlcv_path.parent.mkdir(parents=True, exist_ok=True)
    ohlcv_path.write_bytes(b"immutable-certified-ohlcv")
    features = pd.DataFrame(
        {
            "ticker": ["VALID", "FLAT"],
            "date": pd.to_datetime([session_key, session_key]),
            **{column: [0.1, 0.2] for column in model_runtime.O2_FEATURE_COLUMNS},
            "o2_eligible": [True, False],
            "o2_exclusion_reason": ["ELIGIBLE", "FLAT_RANGE_ZERO_DENOMINATOR"],
        }
    )
    spec = next(item for item in model_runtime.FROZEN_MODELS if item.model_id == model_runtime.O2_MODEL_ID)
    monkeypatch.setattr(
        model_runtime,
        "_verify_frozen_model",
        lambda paths_arg, spec_arg: (tmp_path / "model.joblib", tmp_path / "model-manifest.json", {"status": "FROZEN"}),
    )
    monkeypatch.setattr(model_runtime.joblib, "load", lambda path: object())
    monkeypatch.setattr(
        model_runtime,
        "pointwise_raw_score",
        lambda model, values: pd.Series(range(1, len(values) + 1), dtype=float).to_numpy(),
    )
    monkeypatch.setattr(model_runtime, "sha256_file", lambda path: "artifact-sha")
    monkeypatch.setattr(model_runtime, "_model_output_root", lambda paths_arg, date, model_id: tmp_path / "output")
    monkeypatch.setattr(model_runtime, "_official_sessions", lambda paths_arg, target: pd.DatetimeIndex(pd.to_datetime(["2026-08-11", session_key])))
    monkeypatch.setattr(model_runtime, "_o2_session_identity", lambda paths_arg, date: (2, pd.Timestamp("2026-08-12T08:45:00+07:00")))
    registrations: list[tuple[int, int]] = []

    def register(paths_arg, sessions_arg, session_index):
        registrations.append((len(sessions_arg), session_index))
        return (0, 1)

    monkeypatch.setattr(model_runtime, "_register_o2_counter", register)
    artifact_path, manifest_path, _, _ = model_runtime._score_frame(
        paths,
        spec,
        session_key,
        features,
        {
            "eligible_universe_size": 2,
            "snapshot_path": str(tmp_path / "snapshot.parquet"),
            "snapshot_sha256": "snapshot-sha",
        },
    )

    output = pd.read_parquet(artifact_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(output) == 2
    assert output.loc[output["ticker"] == "VALID", "score"].notna().all()
    assert output.loc[output["ticker"] == "FLAT", "score"].isna().all()
    assert output.loc[output["ticker"] == "FLAT", "o2_exclusion_reason"].iloc[0] == "FLAT_RANGE_ZERO_DENOMINATOR"
    assert manifest["score_rows"] == 2
    assert manifest["scored_rows"] == 1
    assert manifest["o2_eligible_rows"] == 1
    assert manifest["o2_excluded_rows"] == 1
    assert manifest["outcome_blind"] is True
    assert manifest["fresh_forward_outcomes_accessed"] is False
    assert manifest["forward_outcome_access_marker_written"] is False
    assert registrations == [(2, 2)]


@pytest.mark.parametrize(
    "dates, message",
    [
        (["2026-08-11", "2026-08-11"], "duplicate dates"),
        (["2026-08-11", "not-a-date"], "invalid date"),
    ],
)
def test_model_calendar_rejects_ambiguous_or_invalid_sessions(
    tmp_path: Path,
    dates: list[str],
    message: str,
) -> None:
    path = tmp_path / "exchange_sessions.csv"
    pd.DataFrame({"date": dates}).to_csv(path, index=False)

    with pytest.raises(RuntimeError, match=message):
        model_runtime._read_dates(path)
