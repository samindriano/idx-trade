"""Outcome-blind per-model fan-out for the local forward monitor.

The session capture runtime owns immutable input snapshots.  This module owns
the next layer: enqueueing the frozen V2 and V3-B models, scoring the same
snapshot, and committing independently verifiable result artifacts.  It never
loads labels, outcomes, or the one-shot outcome-access marker.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import joblib
import numpy as np
import pandas as pd

from .provenance import sha256_file, write_manifest_atomic
from .ranking_v2_forward_runtime import (
    FRESH_FORWARD_CUTOFF,
    build_outcome_blind_forward_features,
)
from .research_v2_features import V2_FULL_FEATURE_COLUMNS
from .research_v2_models import pointwise_raw_score
from .research_v3_structure_lite import (
    STRUCTURE_LITE_FEATURE_COLUMNS,
    build_structure_lite_features,
)
from .session_backfill import run_exchange_session_backfill
from .storage import write_parquet_atomic


MODEL_WORKER_LOCK = "model_worker.lock"
MODEL_WORKER_STALE_MINUTES = 30
CAUSAL_HISTORY_SESSIONS = 120
V3_FEATURE_ORDER_SHA256 = "100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e"
V3_FEATURE_COLUMNS = (*V2_FULL_FEATURE_COLUMNS, *STRUCTURE_LITE_FEATURE_COLUMNS)


@dataclass(frozen=True)
class FrozenModelSpec:
    model_id: str
    generation: str
    model_relative_path: str
    manifest_relative_path: str
    model_sha256: str
    manifest_sha256: str
    feature_columns: tuple[str, ...]
    feature_order_sha256: str | None = None


FROZEN_MODELS = (
    FrozenModelSpec(
        model_id="HGB_XS_MARKET",
        generation="V2",
        model_relative_path="ranking_v2_final_refit_20260810/ranking_v2_hgb_xs_market_final.joblib",
        manifest_relative_path="ranking_v2_final_refit_20260810/ranking_v2_hgb_xs_market_final_manifest.json",
        model_sha256="5c9e3d0207baa27310937ff97c92e7561e8e1134152ae011668ad97515cb9ace",
        manifest_sha256="f483450026a9550f31b7d5873825079a2e307c1b24db87ce06dc500d17c3ace9",
        feature_columns=tuple(V2_FULL_FEATURE_COLUMNS),
    ),
    FrozenModelSpec(
        model_id="V3-B-STRUCTURE-LITE-V1-CANDIDATE-005",
        generation="V3",
        model_relative_path="ranking_v3_b_final_refit_20260810_001/ranking_v3_b_structure_lite_final.joblib",
        manifest_relative_path="ranking_v3_b_final_refit_20260810_001/ranking_v3_b_structure_lite_final_manifest.json",
        model_sha256="1a702031113ff75f38158aa35d1c2bac477cd424d7f14b83d7a89e6c74fef0f6",
        manifest_sha256="4e84ce02c6ee856c0f260dd6099b2a479723c53da82131ae669e0bf7e4d384f9",
        feature_columns=tuple(V3_FEATURE_COLUMNS),
        feature_order_sha256=V3_FEATURE_ORDER_SHA256,
    ),
)


def _utcnow() -> str:
    return datetime.now(tz=ZoneInfo("UTC")).isoformat()


def _normal_date(value: object) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_localize(None)
    return timestamp.normalize()


def _feature_order_hash(columns: Iterable[str]) -> str:
    import hashlib

    payload = json.dumps(list(columns), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _paths(runtime_root: str | Path):
    from .forward_monitoring import runtime_paths

    return runtime_paths(runtime_root)


def _connection(paths):
    from .forward_monitoring import _connect

    return _connect(paths)


def _model_output_root(paths, session_key: str, model_id: str) -> Path:
    safe_id = model_id.lower().replace("/", "_")
    return paths.monitor_root / "model_runs" / session_key / safe_id


def _spec_paths(paths, spec: FrozenModelSpec) -> tuple[Path, Path]:
    return paths.runtime_root / spec.model_relative_path, paths.runtime_root / spec.manifest_relative_path


def _verify_frozen_model(paths, spec: FrozenModelSpec) -> tuple[Path, Path, dict[str, Any]]:
    model_path, manifest_path = _spec_paths(paths, spec)
    if not model_path.exists() or not manifest_path.exists():
        raise FileNotFoundError(f"frozen {spec.model_id} artifact pair is missing")
    actual_model = sha256_file(model_path)
    actual_manifest = sha256_file(manifest_path)
    if actual_model != spec.model_sha256:
        raise RuntimeError(
            f"frozen {spec.model_id} model hash mismatch: expected={spec.model_sha256} actual={actual_model}"
        )
    if actual_manifest != spec.manifest_sha256:
        raise RuntimeError(
            f"frozen {spec.model_id} manifest hash mismatch: expected={spec.manifest_sha256} actual={actual_manifest}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("fresh_forward_outcomes_accessed") is not False:
        raise RuntimeError(f"frozen {spec.model_id} manifest has invalid outcome-access flag")
    if manifest.get("forward_outcome_access_marker_written") is not False:
        raise RuntimeError(f"frozen {spec.model_id} manifest has invalid outcome-marker flag")
    if spec.feature_order_sha256 is not None and manifest.get("feature_order_sha256") != spec.feature_order_sha256:
        raise RuntimeError(f"frozen {spec.model_id} feature-order hash mismatch")
    if spec.feature_order_sha256 is None:
        manifest_columns = tuple(manifest.get("feature_columns", ()))
        if manifest_columns != spec.feature_columns:
            raise RuntimeError(f"frozen {spec.model_id} feature order differs from the V2 contract")
    return model_path, manifest_path, manifest


def _read_dates(path: Path) -> pd.DatetimeIndex:
    if not path.exists():
        return pd.DatetimeIndex([])
    frame = pd.read_csv(path)
    if "date" not in frame.columns:
        raise RuntimeError(f"official session artifact has no date column: {path}")
    dates = pd.to_datetime(frame["date"], errors="coerce").dropna()
    return pd.DatetimeIndex(dates).tz_localize(None).normalize().unique().sort_values()


def _official_sessions(paths, target: pd.Timestamp) -> pd.DatetimeIndex:
    """Load the certified prefix and extend only the missing official tail."""

    prefix_candidates = (
        paths.runtime_root / "research_feasibility_1260_20260809" / "official_exchange_sessions_1260.csv",
        paths.runtime_root / "sessions" / "exchange_sessions.csv",
    )
    prefix_path = next((path for path in prefix_candidates if path.exists()), None)
    if prefix_path is None:
        raise FileNotFoundError("certified official exchange-session calendar is missing")
    sessions = _read_dates(prefix_path)
    if not len(sessions):
        raise RuntimeError("official exchange-session calendar is empty")
    if target <= sessions.max():
        return sessions

    tail_dir = paths.monitor_root / "model_calendar"
    tail_path = tail_dir / "exchange_sessions.csv"
    tail_sessions = _read_dates(tail_path)
    if not len(tail_sessions) or tail_sessions.max() < target:
        result = run_exchange_session_backfill(sessions.max() + pd.Timedelta(days=1), target, tail_dir)
        if not bool(result.get("complete")):
            raise RuntimeError(f"official forward calendar extension incomplete: {result}")
        tail_sessions = _read_dates(tail_path)
    combined = pd.DatetimeIndex(sorted(set(sessions).union(set(tail_sessions))))
    if target not in combined:
        raise RuntimeError(f"target {target.date().isoformat()} is not in the official exchange calendar")
    return combined


def _panel_path(paths) -> Path:
    candidates = (
        paths.runtime_root
        / "research_feasibility_1260_20260809"
        / "unknown_state_diagnostic_1260_20260809"
        / "model_safe_signal_research_panel_1260.parquet",
    )
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("model-safe signal research panel is missing")


def _security_master_path(paths) -> Path:
    candidates = (
        paths.listings_root / "security_master.csv",
        paths.runtime_root / "research_feasibility_1260_20260809" / "security_master_1260.csv",
    )
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("canonical PIT security master is missing")


def _listed_from(paths) -> dict[str, pd.Timestamp]:
    frame = pd.read_csv(_security_master_path(paths))
    frame["ticker"] = frame["ticker"].astype(str).str.upper().str.strip()
    frame["listed_from"] = pd.to_datetime(frame["listed_from"], errors="coerce").dt.normalize()
    return {
        str(row.ticker): row.listed_from
        for row in frame.dropna(subset=["ticker", "listed_from"])
        .sort_values(["ticker", "listed_from"])
        .drop_duplicates("ticker", keep="first")
        .itertuples()
    }


def _load_model_panel(paths, session_key: str) -> tuple[pd.DataFrame, pd.DatetimeIndex, Path, Path]:
    from .forward_monitoring import _existing_session

    session = _normal_date(session_key)
    row = _existing_session(paths, session)
    if row is None or row["state"] != "DATA_READY":
        raise RuntimeError(f"model fan-out requires DATA_READY session {session_key}")
    snapshot_path = Path(row["snapshot_path"])
    if not snapshot_path.exists():
        raise FileNotFoundError(f"DATA_READY snapshot missing for {session_key}")

    panel_path = _panel_path(paths)
    panel_columns = ["ticker", "date", "high", "low", "close", "volume", "regular_market_value"]
    panel = pd.read_parquet(panel_path, columns=panel_columns)
    panel["date"] = pd.to_datetime(panel["date"], errors="coerce").dt.normalize()
    panel = panel[panel["date"].notna() & (panel["date"] <= session)].copy()

    snapshot = pd.read_parquet(snapshot_path)
    required = set(panel_columns)
    missing = required - set(snapshot.columns)
    if missing:
        raise RuntimeError(f"DATA_READY snapshot missing model columns: {sorted(missing)}")
    snapshot = snapshot.loc[:, panel_columns].copy()
    snapshot["date"] = session
    snapshot["ticker"] = snapshot["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    snapshot = snapshot.drop_duplicates(["ticker", "date"], keep="last")
    panel = pd.concat([panel, snapshot], ignore_index=True, sort=False)
    panel["ticker"] = panel["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    panel = panel.drop_duplicates(["ticker", "date"], keep="last").sort_values(["date", "ticker"]).reset_index(drop=True)
    sessions = _official_sessions(paths, session)
    return panel, sessions, snapshot_path, panel_path


def _build_features(paths, session_key: str) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    panel, sessions, snapshot_path, panel_path = _load_model_panel(paths, session_key)
    session = _normal_date(session_key)
    target_index = int(sessions.get_loc(session))
    history_start = max(0, target_index - CAUSAL_HISTORY_SESSIONS)
    causal_dates = set(sessions[history_start : target_index + 1])
    panel = panel[panel["date"].isin(causal_dates)].copy()
    if panel.empty:
        raise RuntimeError(f"no causal model panel rows were produced for {session_key}")
    listed_from = _listed_from(paths)
    v2 = build_outcome_blind_forward_features(
        panel,
        sessions,
        listed_from=listed_from,
        cutoff_date=FRESH_FORWARD_CUTOFF,
    )
    session_index_by_date = {pd.Timestamp(day): index + 1 for index, day in enumerate(sessions)}
    v2["signal_session_index"] = v2["date"].map(session_index_by_date).astype(int)
    v2 = v2[v2["date"].eq(session)].copy().reset_index(drop=True)
    if v2.empty:
        raise RuntimeError(f"no V2 outcome-blind feature rows were produced for {session_key}")

    structure_input = panel[["ticker", "date", "high", "low", "close", "volume"]].copy()
    structure = build_structure_lite_features(
        structure_input,
        sessions,
        max_signal_session_index=len(sessions),
    )
    structure = structure[structure["date"].eq(session)].copy()
    structure["__structure_row_present"] = True
    joined = v2.merge(structure, on=["ticker", "date", "signal_session_index"], how="left", validate="one_to_one")
    if structure.empty or len(joined) != len(v2) or not joined["__structure_row_present"].fillna(False).all():
        raise RuntimeError(f"no V3-B Structure-Lite rows were produced for {session_key}")
    joined = joined.drop(columns=["__structure_row_present"])
    metadata = {
        "session_date": session_key,
        "official_sessions": int(len(sessions)),
        "causal_history_sessions": int(min(CAUSAL_HISTORY_SESSIONS + 1, target_index + 1)),
        "panel_path": str(panel_path),
        "panel_sha256": sha256_file(panel_path),
        "snapshot_path": str(snapshot_path),
        "snapshot_sha256": sha256_file(snapshot_path),
        "v2_feature_rows": int(len(v2)),
        "v3_feature_rows": int(len(joined)),
        "eligible_universe_size": int(len(joined)),
        "outcome_blind": True,
    }
    return v2, joined, metadata


def _score_frame(paths, spec: FrozenModelSpec, session_key: str, features: pd.DataFrame, metadata: dict[str, Any]) -> tuple[Path, Path, str, str]:
    model_path, model_manifest_path, model_manifest = _verify_frozen_model(paths, spec)
    source = features.loc[:, ["ticker", "date", *spec.feature_columns]].copy()
    if source.duplicated(["ticker", "date"]).any():
        raise RuntimeError(f"{spec.model_id} feature rows contain duplicate ticker/date keys")
    model = joblib.load(model_path)
    score = pointwise_raw_score(model, source.loc[:, list(spec.feature_columns)])
    if not np.isfinite(score).all():
        raise RuntimeError(f"{spec.model_id} produced non-finite outcome-blind scores")
    output = source[["ticker", "date"]].copy()
    output["score"] = np.asarray(score, dtype=float)
    output = output.sort_values(["score", "ticker"], ascending=[False, True], kind="mergesort").reset_index(drop=True)
    output["rank"] = np.arange(1, len(output) + 1, dtype=int)
    output["score_percentile"] = 1.0 - ((output["rank"] - 1.0) / max(len(output), 1))
    output["session_date"] = session_key
    output["model_id"] = spec.model_id
    output["generation"] = spec.generation
    output["model_sha256"] = spec.model_sha256
    output["feature_order_sha256"] = spec.feature_order_sha256 or _feature_order_hash(spec.feature_columns)
    output = output[
        [
            "ticker", "session_date", "score", "rank", "score_percentile",
            "model_id", "generation", "model_sha256", "feature_order_sha256",
        ]
    ]

    output_dir = _model_output_root(paths, session_key, spec.model_id)
    artifact_path = output_dir / "score_artifact.parquet"
    manifest_path = output_dir / "manifest.json"
    write_parquet_atomic(output, artifact_path)
    artifact_sha = sha256_file(artifact_path)
    payload = {
        "schema_version": 1,
        "status": "DONE",
        "session_date": session_key,
        "model_id": spec.model_id,
        "generation": spec.generation,
        "model_sha256": spec.model_sha256,
        "model_manifest_path": str(model_manifest_path),
        "model_manifest_sha256": spec.manifest_sha256,
        "feature_order_sha256": spec.feature_order_sha256 or _feature_order_hash(spec.feature_columns),
        "feature_columns": list(spec.feature_columns),
        "score_artifact_path": str(artifact_path),
        "score_artifact_sha256": artifact_sha,
        "score_rows": int(len(output)),
        "eligible_universe_size": int(metadata["eligible_universe_size"]),
        "data_snapshot_path": metadata["snapshot_path"],
        "data_snapshot_sha256": metadata["snapshot_sha256"],
        "outcome_blind": True,
        "fresh_forward_outcomes_accessed": False,
        "forward_outcome_access_marker_written": False,
        "model_manifest_status": model_manifest.get("status"),
        "generated_at_utc": _utcnow(),
    }
    write_manifest_atomic(manifest_path, payload)
    return artifact_path, manifest_path, artifact_sha, sha256_file(manifest_path)


def _update_run(paths, session_key: str, spec: FrozenModelSpec, **fields: object) -> None:
    if not fields:
        return
    assignments = ", ".join(f"{key}=?" for key in fields)
    values = list(fields.values()) + [session_key, spec.model_id, spec.model_sha256]
    connection = _connection(paths)
    try:
        connection.execute(
            f"UPDATE model_runs SET {assignments} WHERE session_date=? AND model_id=? AND model_fingerprint=?",
            values,
        )
    finally:
        connection.close()


def _artifact_verified(row: Any) -> bool:
    try:
        artifact = Path(row["artifact_path"])
        manifest = Path(row["manifest_path"])
        return (
            artifact.exists()
            and manifest.exists()
            and sha256_file(artifact) == row["artifact_sha256"]
            and sha256_file(manifest) == row["manifest_sha256"]
        )
    except (OSError, TypeError):
        return False


def ensure_model_runs(paths, session_dates: Iterable[object] | None = None) -> int:
    """Idempotently enqueue both frozen models for DATA_READY sessions."""

    requested = None if session_dates is None else {_normal_date(value).date().isoformat() for value in session_dates}
    connection = _connection(paths)
    created = 0
    try:
        rows = connection.execute(
            "SELECT session_date FROM session_snapshots WHERE state='DATA_READY' ORDER BY session_date"
        ).fetchall()
        for session_row in rows:
            session_key = str(session_row["session_date"])
            if requested is not None and session_key not in requested:
                continue
            for spec in FROZEN_MODELS:
                existing = connection.execute(
                    "SELECT * FROM model_runs WHERE session_date=? AND model_id=? AND model_fingerprint=?",
                    (session_key, spec.model_id, spec.model_sha256),
                ).fetchone()
                now = _utcnow()
                if existing is None:
                    connection.execute(
                        """
                        INSERT INTO model_runs(
                            session_date, model_id, model_fingerprint, generation, state,
                            progress_fraction, updated_at, heartbeat_at
                        ) VALUES (?, ?, ?, ?, 'QUEUED', 0, ?, ?)
                        """,
                        (session_key, spec.model_id, spec.model_sha256, spec.generation, now, now),
                    )
                    created += 1
                elif existing["state"] == "DONE" and not _artifact_verified(existing):
                    connection.execute(
                        """
                        UPDATE model_runs SET state='FAILED', progress_fraction=0,
                            updated_at=?, completed_at=?, error_code='ARTIFACT_HASH_MISMATCH',
                            error_message='canonical model result artifact failed hash verification'
                        WHERE session_date=? AND model_id=? AND model_fingerprint=?
                        """,
                        (now, now, session_key, spec.model_id, spec.model_sha256),
                    )
                elif existing["state"] == "INTERRUPTED":
                    connection.execute(
                        """
                        UPDATE model_runs SET state='QUEUED', progress_fraction=0,
                            updated_at=?, completed_at=NULL, error_code=NULL, error_message=NULL
                        WHERE session_date=? AND model_id=? AND model_fingerprint=?
                        """,
                        (now, session_key, spec.model_id, spec.model_sha256),
                    )
    finally:
        connection.close()
    return created


def _claim_queued(paths, session_key: str, spec: FrozenModelSpec) -> bool:
    now = _utcnow()
    connection = _connection(paths)
    try:
        connection.execute("BEGIN IMMEDIATE")
        changed = connection.execute(
            """
            UPDATE model_runs SET state='PREPARING', progress_fraction=0.05,
                started_at=COALESCE(started_at, ?), updated_at=?, heartbeat_at=?,
                lease_owner=?, error_code=NULL, error_message=NULL
            WHERE session_date=? AND model_id=? AND model_fingerprint=? AND state='QUEUED'
            """,
            (now, now, now, f"model-{os.getpid()}", session_key, spec.model_id, spec.model_sha256),
        ).rowcount
        connection.commit()
        return changed == 1
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


def _fail_model(paths, session_key: str, spec: FrozenModelSpec, error: Exception) -> None:
    now = _utcnow()
    _update_run(
        paths,
        session_key,
        spec,
        state="FAILED",
        progress_fraction=0,
        updated_at=now,
        completed_at=now,
        heartbeat_at=now,
        error_code=type(error).__name__.upper(),
        error_message=str(error)[:4000],
    )


def _finish_model(paths, session_key: str, spec: FrozenModelSpec, artifact: Path, manifest: Path, artifact_sha: str, manifest_sha: str) -> None:
    now = _utcnow()
    _update_run(
        paths,
        session_key,
        spec,
        state="DONE",
        progress_fraction=1,
        artifact_path=str(artifact),
        artifact_sha256=artifact_sha,
        manifest_path=str(manifest),
        manifest_sha256=manifest_sha,
        updated_at=now,
        completed_at=now,
        heartbeat_at=now,
        error_code=None,
        error_message=None,
    )


def _run_session(paths, session_key: str) -> None:
    connection = _connection(paths)
    try:
        queued = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM model_runs WHERE session_date=? AND state='QUEUED' ORDER BY generation, model_id",
                (session_key,),
            ).fetchall()
        ]
    finally:
        connection.close()
    if not queued:
        return

    specs = [spec for spec in FROZEN_MODELS if any(row["model_id"] == spec.model_id for row in queued)]
    claimed = [spec for spec in specs if _claim_queued(paths, session_key, spec)]
    if not claimed:
        return
    try:
        v2_features, v3_features, metadata = _build_features(paths, session_key)
    except Exception as error:
        for spec in claimed:
            _fail_model(paths, session_key, spec, error)
        return

    for spec in claimed:
        try:
            _update_run(paths, session_key, spec, state="SCORING", progress_fraction=0.55, updated_at=_utcnow(), heartbeat_at=_utcnow())
            features = v2_features if spec.generation == "V2" else v3_features
            artifact, manifest, artifact_sha, manifest_sha = _score_frame(paths, spec, session_key, features, metadata)
            _update_run(paths, session_key, spec, state="WRITING", progress_fraction=0.9, updated_at=_utcnow(), heartbeat_at=_utcnow())
            _finish_model(paths, session_key, spec, artifact, manifest, artifact_sha, manifest_sha)
        except Exception as error:
            _fail_model(paths, session_key, spec, error)


def run_queued_model_jobs(runtime_root: str | Path, session_dates: Iterable[object] | None = None) -> dict[str, Any]:
    paths = _paths(runtime_root)
    ensure_model_runs(paths, session_dates=session_dates)
    requested = None if session_dates is None else {_normal_date(value).date().isoformat() for value in session_dates}
    connection = _connection(paths)
    try:
        sessions = [
            str(row["session_date"])
            for row in connection.execute("SELECT session_date FROM session_snapshots WHERE state='DATA_READY' ORDER BY session_date").fetchall()
            if requested is None or str(row["session_date"]) in requested
        ]
    finally:
        connection.close()
    for session_key in sessions:
        _run_session(paths, session_key)
    return {"status": "MODEL_RUNS_RECONCILED", "sessions": sessions, "outcome_access": "LOCKED"}


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        process_query_limited_information = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def request_model_worker(runtime_root: str | Path, session_dates: Iterable[object] | None = None) -> bool:
    paths = _paths(runtime_root)
    date_values = None if session_dates is None else tuple(session_dates)
    ensure_model_runs(paths, session_dates=date_values)
    requested = None if date_values is None else {_normal_date(value).date().isoformat() for value in date_values}
    if requested is not None and not requested:
        return False
    connection = _connection(paths)
    try:
        queued = connection.execute(
            "SELECT 1 FROM model_runs WHERE state='QUEUED'"
            + (" AND session_date IN (" + ",".join("?" for _ in requested) + ")" if requested else "")
            + " LIMIT 1",
            tuple(sorted(requested)) if requested else (),
        ).fetchone()
    finally:
        connection.close()
    if queued is None:
        return False
    lock_path = paths.monitor_root / MODEL_WORKER_LOCK
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    acquired = False
    try:
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(descriptor, str(os.getpid()).encode("ascii"))
            os.close(descriptor)
            acquired = True
        except FileExistsError:
            try:
                pid = int(lock_path.read_text(encoding="utf-8").strip())
            except (OSError, ValueError):
                pid = 0
            if _pid_alive(pid):
                return False
            if pid == 0 and datetime.now().timestamp() - lock_path.stat().st_mtime < MODEL_WORKER_STALE_MINUTES * 60:
                return False
            lock_path.unlink(missing_ok=True)
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(descriptor, str(os.getpid()).encode("ascii"))
            os.close(descriptor)
            acquired = True

        args = [sys.executable, "-m", "idx_trade.forward_monitoring_runtime", "run-models", "--runtime-root", str(paths.runtime_root)]
        if date_values is not None:
            dates = [_normal_date(value).date().isoformat() for value in date_values]
            args.extend(["--dates", *dates])
        child = subprocess.Popen(
            args,
            cwd=str(Path(__file__).resolve().parents[2]),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
        )
        lock_path.write_text(str(child.pid), encoding="utf-8")
        return True
    except Exception:
        if acquired:
            lock_path.unlink(missing_ok=True)
        raise


def reconcile_and_request_worker(runtime_root: str | Path, session_dates: Iterable[object] | None = None) -> bool:
    return request_model_worker(runtime_root, session_dates=session_dates)


def release_worker_lock(runtime_root: str | Path) -> None:
    paths = _paths(runtime_root)
    (paths.monitor_root / MODEL_WORKER_LOCK).unlink(missing_ok=True)
