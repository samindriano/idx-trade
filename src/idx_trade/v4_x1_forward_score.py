"""Outcome-blind immutable prospective score capture for frozen V4-X1.

This module is deliberately separate from the legacy V2/V3/O2 fan-out.  V4-X1
is a four-model bundle (CONTROL/CHALLENGER x H5/H10) with a frozen 50/50
consensus contract.  It may read only causal market/session inputs and the
frozen model bundle.  It never reads realized forward outcomes, refits a model,
retunes science, or calls a provider.
"""

from __future__ import annotations

from datetime import datetime, time
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import joblib
import numpy as np
import pandas as pd

from .forward_monitoring import (
    _connect,
    _immutable_bytes,
    _load_forward_calendar,
    _parse_utc,
    runtime_paths,
)
from .forward_ohlcv import (
    MODEL_INPUT_COLUMNS,
    SESSION_OHLCV_COLUMNS,
    validate_ohlcv_against_model_input,
)
from .provenance import sha256_file
from .ranking_v4_3_features import (
    V4_CONTROL_FEATURE_COLUMNS,
    build_v4_control_feature_table,
)
from .ranking_v4_3_preregistration import (
    SESSION_GEOMETRY_FEATURE_COLUMNS,
    build_session_geometry_features,
    normalized_percentile_rank,
)


MODEL_ID = "V4_X1_GEOMETRY3_PROSPECTIVE"
GENERATION = "V4-X1"
EXPECTED_MODEL_MANIFEST_SHA256 = (
    "3d5420dd69f348b7e712b6cca3b11f4673f02581c493e04be6ce9da693125094"
)
EXPECTED_MODEL_STATUS = "V4_X1_FINAL_REFIT_FROZEN_READY_FOR_FRESH_PROSPECTIVE_SCORING"
DEFAULT_OBSERVED_BY = "2026-08-19T14:37:16+07:00"
EXPECTED_FEATURE_BUILDER_BLOB_SHA1 = "59ad05f815870ae00480dc7945fe18371d8eff9c"
EXPECTED_PREREGISTRATION_BLOB_SHA1 = "cc1308feb51bbed16606bf7bded1ca0111644326"
CANONICAL_EOD_CAPTURE_HOUR_JAKARTA = 18
JAKARTA = ZoneInfo("Asia/Jakarta")
UTC = ZoneInfo("UTC")

CONTROL_FEATURES = tuple(V4_CONTROL_FEATURE_COLUMNS)
CHALLENGER_FEATURES = (*CONTROL_FEATURES, *SESSION_GEOMETRY_FEATURE_COLUMNS)
MODEL_FILES = {
    "control_h5": "v4_x1_control_h5_final.joblib",
    "control_h10": "v4_x1_control_h10_final.joblib",
    "challenger_h5": "v4_x1_challenger_h5_final.joblib",
    "challenger_h10": "v4_x1_challenger_h10_final.joblib",
}
MODEL_OUTPUT_KEYS = {key: f"model_{key}" for key in MODEL_FILES}
SIGNAL_COLUMNS = tuple(MODEL_INPUT_COLUMNS)


def _utcnow() -> str:
    return datetime.now(tz=UTC).isoformat()


def _normal_date(value: object) -> pd.Timestamp:
    date = pd.Timestamp(value)
    if date.tzinfo is not None:
        date = date.tz_localize(None)
    return date.normalize()


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("observed-by timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _session_eod_available_at_utc(session: pd.Timestamp) -> datetime:
    return datetime.combine(
        _normal_date(session).date(),
        time(hour=CANONICAL_EOD_CAPTURE_HOUR_JAKARTA),
        tzinfo=JAKARTA,
    ).astimezone(UTC)


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"{label}_MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{label}_NOT_OBJECT:{path}")
    return value


def _git_blob(repo_root: Path, relative: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", f"HEAD:{relative}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _feature_order_hash(columns: Iterable[str]) -> str:
    payload = json.dumps(list(columns), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _verify_scientific_sources(repo_root: Path) -> dict[str, str]:
    expected = {
        "src/idx_trade/ranking_v4_3_features.py": EXPECTED_FEATURE_BUILDER_BLOB_SHA1,
        "src/idx_trade/ranking_v4_3_preregistration.py": EXPECTED_PREREGISTRATION_BLOB_SHA1,
    }
    actual: dict[str, str] = {}
    for relative, expected_blob in expected.items():
        blob = _git_blob(repo_root, relative)
        if blob != expected_blob:
            raise RuntimeError(
                f"V4_X1_FROZEN_SCIENCE_BLOB_MISMATCH:{relative}:{blob}!={expected_blob}"
            )
        actual[relative] = blob
    return actual


def _verify_model_bundle(root: Path) -> dict[str, Any]:
    root = root.resolve()
    manifest_path = root / "MANIFEST.json"
    actual_manifest_sha = sha256_file(manifest_path)
    if actual_manifest_sha != EXPECTED_MODEL_MANIFEST_SHA256:
        raise RuntimeError(
            "V4_X1_MODEL_MANIFEST_SHA_MISMATCH:"
            f"{actual_manifest_sha}!={EXPECTED_MODEL_MANIFEST_SHA256}"
        )
    manifest = _read_json(manifest_path, "V4_X1_MODEL_MANIFEST")
    if manifest.get("status") != EXPECTED_MODEL_STATUS:
        raise RuntimeError("V4_X1_MODEL_MANIFEST_STATUS_CHANGED")
    for key in (
        "historical_prediction_generated",
        "historical_performance_computed",
        "protected_forward_accessed",
        "provider_calls",
    ):
        if manifest.get(key) is not False:
            raise RuntimeError(f"V4_X1_MODEL_GUARD_CHANGED:{key}")
    if int(manifest.get("required_fit_count", -1)) != 4:
        raise RuntimeError("V4_X1_MODEL_FIT_COUNT_CHANGED")

    outputs = manifest.get("output_hashes") or {}
    model_paths: dict[str, Path] = {}
    model_hashes: dict[str, str] = {}
    for key, filename in MODEL_FILES.items():
        output_key = MODEL_OUTPUT_KEYS[key]
        expected = str(outputs.get(output_key) or "")
        if not expected:
            raise RuntimeError(f"V4_X1_MODEL_OUTPUT_HASH_MISSING:{output_key}")
        path = root / filename
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(
                f"V4_X1_MODEL_FILE_SHA_MISMATCH:{output_key}:{actual}!={expected}"
            )
        model_paths[key] = path
        model_hashes[key] = actual

    fit_log_path = root / "v4_x1_final_refit_log.json"
    expected_fit_log = str(outputs.get("fit_log") or "")
    actual_fit_log = sha256_file(fit_log_path)
    if not expected_fit_log or actual_fit_log != expected_fit_log:
        raise RuntimeError(
            f"V4_X1_FIT_LOG_SHA_MISMATCH:{actual_fit_log}!={expected_fit_log}"
        )
    fit_log = json.loads(fit_log_path.read_text(encoding="utf-8"))
    if not isinstance(fit_log, list) or len(fit_log) != 4:
        raise RuntimeError("V4_X1_FIT_LOG_STRUCTURE_CHANGED")
    expected_features = {
        ("CONTROL", "H5"): CONTROL_FEATURES,
        ("CONTROL", "H10"): CONTROL_FEATURES,
        ("CHALLENGER", "H5"): CHALLENGER_FEATURES,
        ("CHALLENGER", "H10"): CHALLENGER_FEATURES,
    }
    seen: set[tuple[str, str]] = set()
    for row in fit_log:
        identity = (str(row.get("mode") or ""), str(row.get("head") or ""))
        if identity not in expected_features or identity in seen:
            raise RuntimeError(f"V4_X1_FIT_LOG_IDENTITY_CHANGED:{identity}")
        columns = tuple(row.get("feature_columns") or ())
        if columns != expected_features[identity]:
            raise RuntimeError(f"V4_X1_FIT_LOG_FEATURE_ORDER_CHANGED:{identity}")
        if int(row.get("feature_count", -1)) != len(columns):
            raise RuntimeError(f"V4_X1_FIT_LOG_FEATURE_COUNT_CHANGED:{identity}")
        seen.add(identity)
    if seen != set(expected_features):
        raise RuntimeError("V4_X1_FIT_LOG_INCOMPLETE")

    return {
        "root": root,
        "manifest_path": manifest_path,
        "manifest_sha256": actual_manifest_sha,
        "manifest": manifest,
        "model_paths": model_paths,
        "model_hashes": model_hashes,
        "fit_log_path": fit_log_path,
        "fit_log_sha256": actual_fit_log,
    }


def _historical_panel_path(paths) -> Path:
    path = (
        paths.runtime_root
        / "research_feasibility_1260_20260809"
        / "unknown_state_diagnostic_1260_20260809"
        / "model_safe_signal_research_panel_1260.parquet"
    )
    if not path.is_file():
        raise FileNotFoundError("model-safe signal research panel is missing")
    return path


def _security_master_path(paths) -> Path:
    candidates = (
        paths.listings_root / "security_master.csv",
        paths.runtime_root / "research_feasibility_1260_20260809" / "security_master_1260.csv",
    )
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError("canonical PIT security master is missing")


def _model_output_root(paths, session_key: str) -> Path:
    return paths.monitor_root / "model_runs" / session_key / MODEL_ID.lower()


def _read_session_csv(path: Path) -> pd.DatetimeIndex:
    frame = pd.read_csv(path)
    if "date" not in frame.columns:
        raise RuntimeError(f"V4_X1_CALENDAR_DATE_COLUMN_MISSING:{path}")
    values = pd.to_datetime(frame["date"], errors="coerce")
    if values.isna().any():
        raise RuntimeError(f"V4_X1_CALENDAR_INVALID_DATE:{path}")
    return pd.DatetimeIndex(values).tz_localize(None).normalize().unique().sort_values()


def _local_official_sessions(paths, target: pd.Timestamp) -> tuple[pd.DatetimeIndex, list[dict[str, str]]]:
    historical_candidates = (
        paths.runtime_root / "research_feasibility_1260_20260809" / "official_exchange_sessions_1260.csv",
        paths.runtime_root / "sessions" / "exchange_sessions.csv",
    )
    historical_path = next((path for path in historical_candidates if path.is_file()), None)
    if historical_path is None:
        raise FileNotFoundError("V4_X1_LOCAL_HISTORICAL_CALENDAR_MISSING")
    historical = _read_session_csv(historical_path)
    forward = _load_forward_calendar(paths)
    combined = pd.DatetimeIndex(sorted(set(historical).union(set(forward))))
    target = _normal_date(target)
    if target not in combined:
        raise RuntimeError(f"V4_X1_TARGET_NOT_IN_LOCAL_OFFICIAL_CALENDAR:{target.date()}")
    sources = [{"path": str(historical_path), "sha256": sha256_file(historical_path)}]
    forward_path = paths.calendar_root / "exchange_sessions.csv"
    if forward_path.is_file():
        sources.append({"path": str(forward_path), "sha256": sha256_file(forward_path)})
    return combined[combined <= target], sources


def _snapshot_rows(paths) -> list[dict[str, Any]]:
    with _connect(paths) as connection:
        rows = connection.execute(
            """
            SELECT session_date, state, snapshot_path, snapshot_sha256,
                   manifest_path, manifest_sha256, completed_at, updated_at,
                   error_code, error_message
            FROM session_snapshots
            ORDER BY session_date
            """
        ).fetchall()
    return [dict(row) for row in rows]


def _verify_snapshot(paths, row: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    if row.get("state") != "DATA_READY":
        raise RuntimeError("V4_X1_INTERNAL_NON_READY_ROW")
    session = _normal_date(row["session_date"])
    snapshot_path = Path(str(row.get("snapshot_path") or ""))
    if not snapshot_path.is_file():
        raise RuntimeError(f"V4_X1_DATA_READY_SNAPSHOT_MISSING:{snapshot_path}")
    actual_snapshot_sha = sha256_file(snapshot_path)
    expected_snapshot_sha = str(row.get("snapshot_sha256") or "")
    if not expected_snapshot_sha or actual_snapshot_sha != expected_snapshot_sha:
        raise RuntimeError(f"V4_X1_DATA_READY_SNAPSHOT_SHA_MISMATCH:{session.date()}")
    snapshot = pd.read_parquet(snapshot_path)
    missing = set(SIGNAL_COLUMNS) - set(snapshot.columns)
    if missing:
        raise RuntimeError(
            f"V4_X1_DATA_READY_SNAPSHOT_COLUMNS_MISSING:{session.date()}:{sorted(missing)}"
        )
    snapshot = snapshot.loc[:, list(SIGNAL_COLUMNS)].copy()
    snapshot["ticker"] = snapshot["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    snapshot["date"] = pd.to_datetime(snapshot["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if snapshot["date"].isna().any() or not snapshot["date"].eq(session).all():
        raise RuntimeError(f"V4_X1_DATA_READY_SNAPSHOT_DATE_MISMATCH:{session.date()}")
    if snapshot["ticker"].eq("").any() or snapshot["ticker"].duplicated().any():
        raise RuntimeError(f"V4_X1_DATA_READY_SNAPSHOT_TICKER_INVALID:{session.date()}")

    ohlcv_path = paths.session_root / session.date().isoformat() / "session_ohlcv.parquet"
    if not ohlcv_path.is_file():
        raise RuntimeError(f"V4_X1_SESSION_OHLCV_MISSING:{ohlcv_path}")
    ohlcv = pd.read_parquet(ohlcv_path)
    missing_ohlcv = set(SESSION_OHLCV_COLUMNS) - set(ohlcv.columns)
    if missing_ohlcv:
        raise RuntimeError(
            f"V4_X1_SESSION_OHLCV_COLUMNS_MISSING:{session.date()}:{sorted(missing_ohlcv)}"
        )
    validate_ohlcv_against_model_input(ohlcv, snapshot, session.date().isoformat())
    return snapshot, ohlcv, {
        "session_date": session.date().isoformat(),
        "snapshot_path": str(snapshot_path),
        "snapshot_sha256": actual_snapshot_sha,
        "session_ohlcv_path": str(ohlcv_path),
        "session_ohlcv_sha256": sha256_file(ohlcv_path),
        "rows": int(len(snapshot)),
        "completed_at": row.get("completed_at"),
        "canonical_eod_available_at": _session_eod_available_at_utc(session).astimezone(JAKARTA).isoformat(),
    }


def _existing_run(paths, session_key: str, fingerprint: str) -> dict[str, Any] | None:
    with _connect(paths) as connection:
        row = connection.execute(
            """
            SELECT * FROM model_runs
            WHERE session_date=? AND model_id=? AND model_fingerprint=?
            """,
            (session_key, MODEL_ID, fingerprint),
        ).fetchone()
    return dict(row) if row is not None else None


def _verify_existing_done(row: dict[str, Any]) -> dict[str, Any]:
    artifact_path = Path(str(row.get("artifact_path") or ""))
    manifest_path = Path(str(row.get("manifest_path") or ""))
    if not artifact_path.is_file() or not manifest_path.is_file():
        raise RuntimeError("V4_X1_DONE_REGISTRY_ARTIFACT_MISSING")
    artifact_sha = sha256_file(artifact_path)
    manifest_sha = sha256_file(manifest_path)
    if artifact_sha != str(row.get("artifact_sha256") or ""):
        raise RuntimeError("V4_X1_DONE_ARTIFACT_SHA_MISMATCH")
    if manifest_sha != str(row.get("manifest_sha256") or ""):
        raise RuntimeError("V4_X1_DONE_MANIFEST_SHA_MISMATCH")
    return {
        "status": "V4_X1_SCORE_ALREADY_DONE_VERIFIED",
        "session_date": row["session_date"],
        "model_id": MODEL_ID,
        "model_fingerprint": row["model_fingerprint"],
        "artifact_path": str(artifact_path),
        "artifact_sha256": artifact_sha,
        "manifest_path": str(manifest_path),
        "manifest_sha256": manifest_sha,
        "provider_calls": False,
        "protected_outcome_accessed": False,
        "model_refit": False,
        "model_retuned": False,
    }


def _set_run_state(
    paths,
    session_key: str,
    fingerprint: str,
    state: str,
    progress: float,
    *,
    error_code: str | None = None,
    error_message: str | None = None,
    artifact_path: Path | None = None,
    artifact_sha256: str | None = None,
    manifest_path: Path | None = None,
    manifest_sha256: str | None = None,
    completed: bool = False,
) -> None:
    now = _utcnow()
    with _connect(paths) as connection:
        existing = connection.execute(
            """
            SELECT state FROM model_runs
            WHERE session_date=? AND model_id=? AND model_fingerprint=?
            """,
            (session_key, MODEL_ID, fingerprint),
        ).fetchone()
        if existing is None:
            connection.execute(
                """
                INSERT INTO model_runs(
                    session_date, model_id, model_fingerprint, generation,
                    state, progress_fraction, artifact_path, artifact_sha256,
                    manifest_path, manifest_sha256, started_at, updated_at,
                    completed_at, error_code, error_message
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    session_key, MODEL_ID, fingerprint, GENERATION,
                    state, float(progress),
                    str(artifact_path) if artifact_path else None,
                    artifact_sha256,
                    str(manifest_path) if manifest_path else None,
                    manifest_sha256,
                    now, now, now if completed else None,
                    error_code, error_message,
                ),
            )
        else:
            connection.execute(
                """
                UPDATE model_runs
                SET state=?, progress_fraction=?, artifact_path=?, artifact_sha256=?,
                    manifest_path=?, manifest_sha256=?, updated_at=?,
                    completed_at=?, error_code=?, error_message=?
                WHERE session_date=? AND model_id=? AND model_fingerprint=?
                """,
                (
                    state, float(progress),
                    str(artifact_path) if artifact_path else None,
                    artifact_sha256,
                    str(manifest_path) if manifest_path else None,
                    manifest_sha256,
                    now, now if completed else None,
                    error_code, error_message,
                    session_key, MODEL_ID, fingerprint,
                ),
            )


def _fresh_sessions(
    paths,
    observed_by: datetime,
    historical_end: pd.Timestamp,
    fingerprint: str,
) -> tuple[list[tuple[pd.Timestamp, dict[str, Any]]], list[dict[str, Any]], dict[pd.Timestamp, dict[str, Any]]]:
    rows = _snapshot_rows(paths)
    ready_by_date = {
        _normal_date(row["session_date"]): row
        for row in rows
        if row.get("state") == "DATA_READY"
    }
    fresh: list[tuple[pd.Timestamp, dict[str, Any]]] = []
    ignored: list[dict[str, Any]] = []
    for session, row in sorted(ready_by_date.items()):
        completed = _parse_utc(row.get("completed_at"))
        if completed is None or completed <= observed_by:
            continue
        eod = _session_eod_available_at_utc(session)
        if eod <= observed_by:
            ignored.append(
                {
                    "session_date": session.date().isoformat(),
                    "completed_at": row.get("completed_at"),
                    "canonical_eod_available_at": eod.astimezone(JAKARTA).isoformat(),
                    "reason": "SESSION_EOD_PREDATES_MODEL_FREEZE",
                }
            )
            continue
        if session <= historical_end:
            raise RuntimeError("V4_X1_FRESH_SESSION_NOT_AFTER_HISTORICAL_PANEL")
        fresh.append((session, row))

    if not fresh:
        raise RuntimeError("V4_X1_NO_GENUINELY_FRESH_DATA_READY_SESSION")

    # Preserve chronology: choose the first genuinely fresh session that has
    # not already been immutably completed for this exact frozen bundle.
    pending: list[tuple[pd.Timestamp, dict[str, Any]]] = []
    for session, row in fresh:
        existing = _existing_run(paths, session.date().isoformat(), fingerprint)
        if existing is None or existing.get("state") != "DONE":
            pending.append((session, row))
    return pending, ignored, ready_by_date


def _score_one(model: Any, frame: pd.DataFrame) -> tuple[np.ndarray, pd.Series]:
    raw = np.asarray(model.predict(frame), dtype=float)
    if len(raw) != len(frame) or not np.isfinite(raw).all():
        raise RuntimeError("V4_X1_MODEL_PRODUCED_NONFINITE_OR_MISALIGNED_SCORE")
    raw_series = pd.Series(raw, index=frame.index, dtype=float)
    alpha = normalized_percentile_rank(raw_series)
    if alpha.isna().any():
        raise RuntimeError("V4_X1_WITHIN_DATE_ALPHA_RANK_MISSING")
    return raw, alpha


def score_v4_x1_session(
    runtime_root: str | Path,
    model_root: str | Path,
    *,
    repo_root: str | Path,
    session_date: str | None = None,
    observed_by: str = DEFAULT_OBSERVED_BY,
) -> dict[str, Any]:
    """Score exactly one clean prospective session and commit immutable evidence."""

    paths = runtime_paths(runtime_root)
    repo = Path(repo_root).resolve()
    model_bundle = _verify_model_bundle(Path(model_root))
    scientific_blobs = _verify_scientific_sources(repo)
    fingerprint = model_bundle["manifest_sha256"]
    freeze = _parse_timestamp(observed_by)

    historical_path = _historical_panel_path(paths)
    historical = pd.read_parquet(historical_path)
    missing_historical = set(SIGNAL_COLUMNS) - set(historical.columns)
    if missing_historical:
        raise RuntimeError(f"V4_X1_HISTORICAL_PANEL_COLUMNS_MISSING:{sorted(missing_historical)}")
    historical = historical.loc[:, list(SIGNAL_COLUMNS)].copy()
    historical["ticker"] = historical["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    historical["date"] = pd.to_datetime(historical["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if historical["date"].isna().any() or historical.duplicated(["ticker", "date"]).any():
        raise RuntimeError("V4_X1_HISTORICAL_PANEL_IDENTITY_INVALID")
    historical_end = _normal_date(historical["date"].max())

    pending, ignored_backfills, ready_by_date = _fresh_sessions(
        paths, freeze, historical_end, fingerprint
    )
    if not pending:
        # All genuinely fresh sessions currently present have already been
        # completed. Verify the latest one rather than creating a new artifact.
        fresh_done = [
            (day, _existing_run(paths, day.date().isoformat(), fingerprint))
            for day in sorted(ready_by_date)
            if _session_eod_available_at_utc(day) > freeze
            and (_parse_utc(ready_by_date[day].get("completed_at")) or datetime.min.replace(tzinfo=UTC)) > freeze
        ]
        fresh_done = [(day, row) for day, row in fresh_done if row and row.get("state") == "DONE"]
        if fresh_done:
            return _verify_existing_done(fresh_done[-1][1])
        raise RuntimeError("V4_X1_NO_PENDING_FRESH_SESSION")

    candidate, candidate_row = pending[0]
    if session_date is not None and _normal_date(session_date) != candidate:
        raise RuntimeError(
            f"V4_X1_SESSION_NOT_NEXT_CLEAN_PROSPECTIVE:{session_date}!={candidate.date().isoformat()}"
        )
    session_key = candidate.date().isoformat()

    existing = _existing_run(paths, session_key, fingerprint)
    if existing is not None:
        if existing.get("state") == "DONE":
            return _verify_existing_done(existing)
        if existing.get("state") not in {"FAILED", "INTERRUPTED", "NOT_STARTED"}:
            raise RuntimeError(f"V4_X1_EXISTING_ACTIVE_RUN:{existing.get('state')}")

    forward_calendar = _load_forward_calendar(paths)
    if candidate not in forward_calendar:
        raise RuntimeError(f"V4_X1_CANDIDATE_NOT_IN_LOCAL_FORWARD_CALENDAR:{session_key}")
    required_sessions = forward_calendar[
        (forward_calendar > historical_end) & (forward_calendar <= candidate)
    ]
    missing_ready = [
        day.date().isoformat()
        for day in required_sessions
        if _normal_date(day) not in ready_by_date
    ]
    if missing_ready:
        raise RuntimeError(f"V4_X1_CANONICAL_HISTORY_GAP:{missing_ready}")

    _set_run_state(paths, session_key, fingerprint, "PREPARING", 0.10)
    try:
        verified: list[dict[str, Any]] = []
        forward_frames: list[pd.DataFrame] = []
        candidate_ohlcv: pd.DataFrame | None = None
        for day in required_sessions:
            day = _normal_date(day)
            snapshot, ohlcv, evidence = _verify_snapshot(paths, ready_by_date[day])
            verified.append(evidence)
            forward_frames.append(snapshot)
            if day == candidate:
                candidate_ohlcv = ohlcv.copy()
        if candidate_ohlcv is None:
            raise RuntimeError("V4_X1_CANDIDATE_OHLCV_NOT_VERIFIED")

        signal_panel = pd.concat([historical, *forward_frames], ignore_index=True, sort=False)
        if signal_panel.duplicated(["ticker", "date"]).any():
            raise RuntimeError("V4_X1_SIGNAL_PANEL_DUPLICATE_IDENTITY")
        if _normal_date(signal_panel["date"].max()) != candidate:
            raise RuntimeError("V4_X1_SIGNAL_PANEL_END_MISMATCH")

        official_sessions, calendar_sources = _local_official_sessions(paths, candidate)
        panel_dates = pd.DatetimeIndex(signal_panel["date"].unique()).sort_values()
        outside_calendar = panel_dates.difference(official_sessions)
        if len(outside_calendar):
            raise RuntimeError(
                f"V4_X1_SIGNAL_PANEL_DATE_OUTSIDE_LOCAL_CALENDAR:{[d.date().isoformat() for d in outside_calendar]}"
            )

        security_path = _security_master_path(paths)
        security_master = pd.read_csv(security_path)
        features, diagnostics = build_v4_control_feature_table(
            signal_panel,
            official_sessions,
            security_master,
        )
        scoring = features.loc[
            features["date"].eq(candidate)
            & features["universe_primary_liquid"].astype(bool)
        ].copy()
        if scoring.empty:
            raise RuntimeError("V4_X1_NO_PRIMARY_LIQUID_SCORING_ROWS")

        geometry_input = candidate_ohlcv.loc[:, ["ticker", "session_date", "open", "high", "low", "close"]].copy()
        geometry_input = geometry_input.rename(columns={"session_date": "date"})
        geometry_input["ticker"] = geometry_input["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
        geometry_input["date"] = pd.to_datetime(geometry_input["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
        geometry = build_session_geometry_features(geometry_input)
        scoring = scoring.merge(
            geometry,
            on=["ticker", "date"],
            how="left",
            validate="one_to_one",
        )
        missing_geometry_identity = scoring[list(SESSION_GEOMETRY_FEATURE_COLUMNS)].isna().all(axis=1)
        # All three geometry values may legitimately be NaN only for a fully
        # unusable bar, but canonical OHLCV validation should make that rare;
        # the frozen challenger imputer owns the numeric missing-value policy.
        if int(missing_geometry_identity.sum()) == len(scoring):
            raise RuntimeError("V4_X1_ALL_GEOMETRY_FEATURES_MISSING")

        missing_control = set(CONTROL_FEATURES) - set(scoring.columns)
        missing_challenger = set(CHALLENGER_FEATURES) - set(scoring.columns)
        if missing_control or missing_challenger:
            raise RuntimeError(
                f"V4_X1_SCORING_FEATURES_MISSING:control={sorted(missing_control)}:challenger={sorted(missing_challenger)}"
            )

        _set_run_state(paths, session_key, fingerprint, "SCORING", 0.55)
        models = {
            key: joblib.load(path)
            for key, path in model_bundle["model_paths"].items()
        }
        raw_control_h5, alpha_control_h5 = _score_one(models["control_h5"], scoring)
        raw_control_h10, alpha_control_h10 = _score_one(models["control_h10"], scoring)
        raw_challenger_h5, alpha_challenger_h5 = _score_one(models["challenger_h5"], scoring)
        raw_challenger_h10, alpha_challenger_h10 = _score_one(models["challenger_h10"], scoring)

        artifact = scoring[["ticker", "date"]].copy()
        artifact["raw_control_h5"] = raw_control_h5
        artifact["alpha_control_h5"] = alpha_control_h5.to_numpy(dtype=float)
        artifact["raw_control_h10"] = raw_control_h10
        artifact["alpha_control_h10"] = alpha_control_h10.to_numpy(dtype=float)
        artifact["alpha_control_consensus"] = (
            0.5 * artifact["alpha_control_h5"] + 0.5 * artifact["alpha_control_h10"]
        )
        artifact["raw_challenger_h5"] = raw_challenger_h5
        artifact["alpha_h5"] = alpha_challenger_h5.to_numpy(dtype=float)
        artifact["raw_challenger_h10"] = raw_challenger_h10
        artifact["alpha_h10"] = alpha_challenger_h10.to_numpy(dtype=float)
        artifact["alpha_consensus"] = 0.5 * artifact["alpha_h5"] + 0.5 * artifact["alpha_h10"]
        artifact = artifact.sort_values(
            ["alpha_consensus", "ticker"],
            ascending=[False, True],
            kind="mergesort",
        ).reset_index(drop=True)
        artifact["rank_consensus"] = np.arange(1, len(artifact) + 1, dtype=np.int64)
        control_order = artifact.sort_values(
            ["alpha_control_consensus", "ticker"],
            ascending=[False, True],
            kind="mergesort",
        ).index
        control_ranks = pd.Series(np.arange(1, len(artifact) + 1, dtype=np.int64), index=control_order)
        artifact["rank_control_consensus"] = control_ranks.reindex(artifact.index).to_numpy(dtype=np.int64)

        if artifact[["alpha_h5", "alpha_h10", "alpha_consensus"]].isna().any().any():
            raise RuntimeError("V4_X1_CHALLENGER_ALPHA_MISSING")
        if artifact["ticker"].duplicated().any() or not artifact["date"].eq(candidate).all():
            raise RuntimeError("V4_X1_OUTPUT_IDENTITY_INVALID")

        output_root = _model_output_root(paths, session_key)
        artifact_path = output_root / "score_artifact.parquet"
        manifest_path = output_root / "manifest.json"
        artifact_bytes = artifact.to_parquet(index=False)
        artifact_sha = hashlib.sha256(artifact_bytes).hexdigest()

        candidate_evidence = next(row for row in verified if row["session_date"] == session_key)
        manifest = {
            "schema_version": "v4_x1_prospective_score_manifest_v1",
            "model_id": MODEL_ID,
            "generation": GENERATION,
            "model_fingerprint": fingerprint,
            "session_date": session_key,
            "status": "DONE",
            "science": {
                "control_feature_columns": list(CONTROL_FEATURES),
                "control_feature_order_sha256": _feature_order_hash(CONTROL_FEATURES),
                "challenger_feature_columns": list(CHALLENGER_FEATURES),
                "challenger_feature_order_sha256": _feature_order_hash(CHALLENGER_FEATURES),
                "consensus_formula": "0.5*H5_WITHIN_DATE_PERCENTILE_RANK+0.5*H10_WITHIN_DATE_PERCENTILE_RANK",
                "frozen_scientific_git_blobs": scientific_blobs,
            },
            "model_bundle": {
                "root": str(model_bundle["root"]),
                "manifest_sha256": fingerprint,
                "model_hashes": model_bundle["model_hashes"],
                "fit_log_sha256": model_bundle["fit_log_sha256"],
            },
            "freshness": {
                "model_freeze_observed_by": observed_by,
                "canonical_eod_available_at": candidate_evidence["canonical_eod_available_at"],
                "data_ready_completed_at": candidate_row.get("completed_at"),
                "rule": "CANONICAL_SESSION_EOD_AND_DATA_READY_COMPLETION_BOTH_STRICTLY_AFTER_MODEL_FREEZE",
                "ignored_post_freeze_backfills": ignored_backfills,
            },
            "inputs": {
                "historical_panel_path": str(historical_path),
                "historical_panel_sha256": sha256_file(historical_path),
                "historical_panel_last_date": historical_end.date().isoformat(),
                "security_master_path": str(security_path),
                "security_master_sha256": sha256_file(security_path),
                "calendar_sources": calendar_sources,
                "verified_forward_history": verified,
                "candidate_snapshot_sha256": candidate_evidence["snapshot_sha256"],
                "candidate_session_ohlcv_sha256": candidate_evidence["session_ohlcv_sha256"],
            },
            "rows": int(len(artifact)),
            "pit_diagnostics": diagnostics.__dict__,
            "geometry_all_missing_rows": int(missing_geometry_identity.sum()),
            "output": {
                "artifact_path": str(artifact_path),
                "artifact_sha256": artifact_sha,
                "columns": list(artifact.columns),
            },
            "guards": {
                "provider_calls": False,
                "protected_outcome_accessed": False,
                "realized_forward_outcome_loaded": False,
                "historical_prediction_generated": False,
                "model_refit": False,
                "model_retuned": False,
                "science_changed": False,
            },
        }
        manifest_bytes = (
            json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        ).encode("utf-8")
        manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()

        _set_run_state(paths, session_key, fingerprint, "WRITING", 0.90)
        _immutable_bytes(artifact_path, artifact_bytes)
        if sha256_file(artifact_path) != artifact_sha:
            raise RuntimeError("V4_X1_WRITTEN_ARTIFACT_SHA_MISMATCH")
        _immutable_bytes(manifest_path, manifest_bytes)
        if sha256_file(manifest_path) != manifest_sha:
            raise RuntimeError("V4_X1_WRITTEN_MANIFEST_SHA_MISMATCH")

        _set_run_state(
            paths,
            session_key,
            fingerprint,
            "DONE",
            1.0,
            artifact_path=artifact_path,
            artifact_sha256=artifact_sha,
            manifest_path=manifest_path,
            manifest_sha256=manifest_sha,
            completed=True,
        )
        return {
            "status": "V4_X1_PROSPECTIVE_SCORE_DONE",
            "session_date": session_key,
            "model_id": MODEL_ID,
            "model_fingerprint": fingerprint,
            "rows": int(len(artifact)),
            "artifact_path": str(artifact_path),
            "artifact_sha256": artifact_sha,
            "manifest_path": str(manifest_path),
            "manifest_sha256": manifest_sha,
            "provider_calls": False,
            "protected_outcome_accessed": False,
            "realized_forward_outcome_loaded": False,
            "model_refit": False,
            "model_retuned": False,
        }
    except Exception as error:
        _set_run_state(
            paths,
            session_key,
            fingerprint,
            "FAILED",
            0.0,
            error_code=type(error).__name__.upper(),
            error_message=str(error),
        )
        raise
