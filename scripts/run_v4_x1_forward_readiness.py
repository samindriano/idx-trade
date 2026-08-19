"""Read-only readiness audit for V4-X1 prospective score capture.

This script never calls a provider, scores a model, opens an outcome, mutates the
canonical forward registry, or creates a second EOD capture path. It verifies
the frozen V4-X1 model bundle and inspects the existing IDXTrade-ForwardEOD
runtime for the first canonical DATA_READY session that is genuinely fresh:
its canonical EOD availability and its actual DATA_READY completion must both
be strictly after the conservative model-freeze observed-by timestamp.
"""

from __future__ import annotations

import argparse
from datetime import datetime, time
import json
from pathlib import Path
import sys
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.forward_monitoring import (  # noqa: E402
    _connect,
    _load_forward_calendar,
    _parse_utc,
    runtime_paths,
)
from idx_trade.forward_model_runtime import _panel_path  # noqa: E402
from idx_trade.forward_ohlcv import (  # noqa: E402
    SESSION_OHLCV_COLUMNS,
    validate_ohlcv_against_model_input,
)
from idx_trade.provenance import sha256_file  # noqa: E402


EXPECTED_MODEL_MANIFEST_SHA256 = (
    "3d5420dd69f348b7e712b6cca3b11f4673f02581c493e04be6ce9da693125094"
)
EXPECTED_STATUS = "V4_X1_FINAL_REFIT_FROZEN_READY_FOR_FRESH_PROSPECTIVE_SCORING"
DEFAULT_OBSERVED_BY = "2026-08-19T14:37:16+07:00"
CANONICAL_EOD_CAPTURE_HOUR_JAKARTA = 18
JAKARTA = ZoneInfo("Asia/Jakarta")
UTC = ZoneInfo("UTC")
REQUIRED_MODEL_OUTPUTS = (
    "model_control_h5",
    "model_control_h10",
    "model_challenger_h5",
    "model_challenger_h10",
)
REQUIRED_SNAPSHOT_COLUMNS = {
    "ticker",
    "date",
    "high",
    "low",
    "close",
    "volume",
    "regular_market_value",
}


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("observed-by timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _session_eod_available_at_utc(session: pd.Timestamp) -> datetime:
    """Conservative canonical EOD availability for one official IDX session."""

    day = pd.Timestamp(session).normalize().date()
    return datetime.combine(
        day,
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


def _verify_model_bundle(root: Path) -> dict[str, Any]:
    manifest_path = root / "MANIFEST.json"
    actual_manifest_sha = sha256_file(manifest_path)
    if actual_manifest_sha != EXPECTED_MODEL_MANIFEST_SHA256:
        raise RuntimeError(
            "V4_X1_MODEL_MANIFEST_SHA_MISMATCH:"
            f"{actual_manifest_sha}!={EXPECTED_MODEL_MANIFEST_SHA256}"
        )
    manifest = _read_json(manifest_path, "V4_X1_MODEL_MANIFEST")
    if manifest.get("status") != EXPECTED_STATUS:
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
    model_hashes: dict[str, str] = {}
    for key in REQUIRED_MODEL_OUTPUTS:
        expected = str(outputs.get(key) or "")
        if not expected:
            raise RuntimeError(f"V4_X1_MODEL_OUTPUT_HASH_MISSING:{key}")
        filename = {
            "model_control_h5": "v4_x1_control_h5_final.joblib",
            "model_control_h10": "v4_x1_control_h10_final.joblib",
            "model_challenger_h5": "v4_x1_challenger_h5_final.joblib",
            "model_challenger_h10": "v4_x1_challenger_h10_final.joblib",
        }[key]
        path = root / filename
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"V4_X1_MODEL_FILE_SHA_MISMATCH:{key}:{actual}!={expected}")
        model_hashes[key] = actual
    return {
        "manifest_sha256": actual_manifest_sha,
        "model_hashes": model_hashes,
    }


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


def _verify_snapshot_row(paths, row: dict[str, Any]) -> dict[str, Any]:
    if row.get("state") != "DATA_READY":
        raise RuntimeError("V4_X1_INTERNAL_NON_READY_ROW")
    session = pd.Timestamp(row["session_date"]).normalize()
    snapshot_path = Path(str(row.get("snapshot_path") or ""))
    if not snapshot_path.is_file():
        raise RuntimeError(f"V4_X1_DATA_READY_SNAPSHOT_MISSING:{snapshot_path}")
    actual_snapshot_sha = sha256_file(snapshot_path)
    expected_snapshot_sha = str(row.get("snapshot_sha256") or "")
    if not expected_snapshot_sha or actual_snapshot_sha != expected_snapshot_sha:
        raise RuntimeError(
            f"V4_X1_DATA_READY_SNAPSHOT_SHA_MISMATCH:{session.date()}"
        )
    snapshot = pd.read_parquet(snapshot_path)
    missing = REQUIRED_SNAPSHOT_COLUMNS - set(snapshot.columns)
    if missing:
        raise RuntimeError(
            f"V4_X1_DATA_READY_SNAPSHOT_COLUMNS_MISSING:{session.date()}:{sorted(missing)}"
        )
    snapshot_dates = pd.to_datetime(snapshot["date"], errors="coerce").dt.normalize()
    if snapshot_dates.isna().any() or not snapshot_dates.eq(session).all():
        raise RuntimeError(f"V4_X1_DATA_READY_SNAPSHOT_DATE_MISMATCH:{session.date()}")

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
    return {
        "session_date": session.date().isoformat(),
        "snapshot_path": str(snapshot_path),
        "snapshot_sha256": actual_snapshot_sha,
        "session_ohlcv_path": str(ohlcv_path),
        "session_ohlcv_sha256": sha256_file(ohlcv_path),
        "rows": int(len(snapshot)),
        "completed_at": row.get("completed_at"),
        "canonical_eod_available_at": _session_eod_available_at_utc(session).astimezone(JAKARTA).isoformat(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--x1-model-root", type=Path, required=True)
    parser.add_argument("--observed-by", default=DEFAULT_OBSERVED_BY)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = runtime_paths(args.runtime_root)
    model_root = args.x1_model_root.resolve()
    observed_by = _parse_timestamp(args.observed_by)
    model_bundle = _verify_model_bundle(model_root)

    panel_path = _panel_path(paths)
    panel_dates = pd.to_datetime(
        pd.read_parquet(panel_path, columns=["date"])["date"], errors="coerce"
    ).dropna().dt.normalize()
    if panel_dates.empty:
        raise RuntimeError("V4_X1_HISTORICAL_PANEL_HAS_NO_DATES")
    historical_end = pd.Timestamp(panel_dates.max()).normalize()

    calendar = _load_forward_calendar(paths)
    rows = _snapshot_rows(paths)
    ready_by_date = {
        pd.Timestamp(row["session_date"]).normalize(): row
        for row in rows
        if row.get("state") == "DATA_READY"
    }

    post_freeze: list[tuple[pd.Timestamp, dict[str, Any]]] = []
    ignored_post_freeze_backfills: list[dict[str, Any]] = []
    for session, row in sorted(ready_by_date.items()):
        completed = _parse_utc(row.get("completed_at"))
        if completed is None or completed <= observed_by:
            continue
        session_eod = _session_eod_available_at_utc(session)
        if session_eod <= observed_by:
            ignored_post_freeze_backfills.append(
                {
                    "session_date": session.date().isoformat(),
                    "completed_at": row.get("completed_at"),
                    "canonical_eod_available_at": session_eod.astimezone(JAKARTA).isoformat(),
                    "reason": "SESSION_EOD_PREDATES_MODEL_FREEZE",
                }
            )
            continue
        post_freeze.append((session, row))

    base = {
        "schema_version": "v4_x1_forward_readiness_v2",
        "generation_id": "V4_X1_GEOMETRY3_PROSPECTIVE",
        "model_manifest_sha256": model_bundle["manifest_sha256"],
        "model_freeze_observed_by": args.observed_by,
        "canonical_eod_capture_hour_jakarta": CANONICAL_EOD_CAPTURE_HOUR_JAKARTA,
        "fresh_session_rule": "CANONICAL_SESSION_EOD_AND_DATA_READY_COMPLETION_BOTH_STRICTLY_AFTER_MODEL_FREEZE",
        "ignored_post_freeze_backfills": ignored_post_freeze_backfills,
        "runtime_root": str(paths.runtime_root),
        "registry_path": str(paths.registry_path),
        "historical_panel_path": str(panel_path),
        "historical_panel_sha256": sha256_file(panel_path),
        "historical_panel_last_date": historical_end.date().isoformat(),
        "provider_calls": False,
        "protected_outcome_accessed": False,
        "model_scored": False,
        "registry_mutated": False,
    }

    if not post_freeze:
        print(json.dumps({
            **base,
            "status": "V4_X1_FORWARD_READYNESS_WAITING_NO_POST_FREEZE_DATA_READY",
            "candidate_first_score_session": None,
            "next": "WAIT_FOR_EXISTING_CANONICAL_EOD_RUNTIME_TO_PRODUCE_A_GENUINELY_FRESH_POST_FREEZE_DATA_READY_SESSION",
        }, indent=2, sort_keys=True))
        return 0

    candidate, candidate_row = post_freeze[0]
    if candidate not in calendar:
        raise RuntimeError(
            f"V4_X1_CANDIDATE_NOT_IN_LOCAL_CERTIFIED_FORWARD_CALENDAR:{candidate.date()}"
        )

    required_sessions = calendar[(calendar > historical_end) & (calendar <= candidate)]
    missing_ready = [
        day.date().isoformat()
        for day in required_sessions
        if pd.Timestamp(day).normalize() not in ready_by_date
    ]
    if missing_ready:
        print(json.dumps({
            **base,
            "status": "V4_X1_FORWARD_READYNESS_BLOCKED_CANONICAL_HISTORY_GAP",
            "candidate_first_score_session": candidate.date().isoformat(),
            "candidate_canonical_eod_available_at": _session_eod_available_at_utc(candidate).astimezone(JAKARTA).isoformat(),
            "required_forward_history_sessions": int(len(required_sessions)),
            "missing_data_ready_sessions": missing_ready,
            "next": "USE_ONLY_THE_EXISTING_CANONICAL_FORWARD_EOD_CATCHUP_TO_CLOSE_THE_LISTED_SESSION_GAPS_THEN_RERUN_READINESS",
        }, indent=2, sort_keys=True))
        return 2

    verified_history = [
        _verify_snapshot_row(paths, ready_by_date[pd.Timestamp(day).normalize()])
        for day in required_sessions
    ]
    candidate_verified = next(
        row for row in verified_history if row["session_date"] == candidate.date().isoformat()
    )
    print(json.dumps({
        **base,
        "status": "V4_X1_FORWARD_READYNESS_PASS_FIRST_SCORE_SESSION_IDENTIFIED",
        "candidate_first_score_session": candidate.date().isoformat(),
        "candidate_completed_at": candidate_row.get("completed_at"),
        "candidate_canonical_eod_available_at": _session_eod_available_at_utc(candidate).astimezone(JAKARTA).isoformat(),
        "required_forward_history_sessions": int(len(required_sessions)),
        "verified_forward_history_sessions": int(len(verified_history)),
        "candidate_artifacts": candidate_verified,
        "next": "RUN_ONE_IMMUTABLE_V4_X1_SCORE_ONLY_CAPTURE_FOR_THE_IDENTIFIED_SESSION_WITH_NO_OUTCOME_ACCESS",
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())