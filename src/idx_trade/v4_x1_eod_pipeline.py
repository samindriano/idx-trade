"""Operational EOD -> frozen V4-X1 score pipeline.

The canonical EOD engine remains the only market-data capture path. This
orchestrator runs it first and, only after a successful catch-up, invokes the
already frozen V4-X1 prospective scorer. It never opens outcomes, fits a
model, changes science, or creates a second provider path.

Deployment adds one deliberately conservative prospective guard: a new X1
score may only be committed on the same Jakarta calendar date as its signal
session and its canonical DATA_READY completion. Late catch-up remains useful
for causal history/continuity but cannot be promoted retroactively into the X1
prospective counter.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4
from zoneinfo import ZoneInfo

import pandas as pd

from .forward_eod_runner import run_eod_catchup
from .forward_monitoring import _connect, _parse_utc, runtime_paths
from .provenance import sha256_file, write_manifest_atomic
from . import v4_x1_forward_score as x1


JAKARTA = ZoneInfo("Asia/Jakarta")
UTC = ZoneInfo("UTC")
PIPELINE_SCHEMA_VERSION = 1
X1_FORWARD_TARGET = 100
NO_SCORE_ERRORS = {
    "V4_X1_NO_GENUINELY_FRESH_DATA_READY_SESSION",
    "V4_X1_NO_PENDING_FRESH_SESSION",
}


def _now_jakarta() -> datetime:
    return datetime.now(tz=JAKARTA)


def _normal_date(value: object) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_localize(None)
    return timestamp.normalize()


def _filter_same_day_pending(
    pending: list[tuple[pd.Timestamp, dict[str, Any]]],
    *,
    now: datetime,
) -> tuple[list[tuple[pd.Timestamp, dict[str, Any]]], list[dict[str, Any]]]:
    """Keep only genuinely same-day operational candidates.

    This is stricter than the model-freeze gate and is intentionally an
    operational anti-backfill rule. It guarantees that a laptop waking days
    later can repair canonical history without manufacturing a retrospective
    X1 prospective observation.
    """

    local_day = _normal_date(now.astimezone(JAKARTA).date())
    eligible: list[tuple[pd.Timestamp, dict[str, Any]]] = []
    ignored: list[dict[str, Any]] = []
    for session, row in pending:
        session = _normal_date(session)
        completed = _parse_utc(row.get("completed_at"))
        reason: str | None = None
        if session != local_day:
            reason = "X1_SCORE_WINDOW_EXPIRED_NOT_SAME_JAKARTA_DATE"
        elif completed is None:
            reason = "X1_DATA_READY_COMPLETION_TIMESTAMP_MISSING"
        elif _normal_date(completed.astimezone(JAKARTA).date()) != session:
            reason = "X1_DATA_READY_COMPLETED_AFTER_SESSION_DATE"

        if reason is None:
            eligible.append((session, row))
            continue
        ignored.append(
            {
                "session_date": session.date().isoformat(),
                "completed_at": row.get("completed_at"),
                "reason": reason,
                "prospective_counter_eligible": False,
                "continuity_history_eligible": True,
            }
        )
    return eligible, ignored


def _verified_x1_counter(runtime_root: str | Path) -> dict[str, Any]:
    """Count only DONE X1 rows whose immutable files still match the registry."""

    paths = runtime_paths(runtime_root)
    fingerprint = x1.EXPECTED_MODEL_MANIFEST_SHA256
    with _connect(paths) as connection:
        rows = connection.execute(
            """
            SELECT * FROM model_runs
            WHERE model_id=? AND model_fingerprint=? AND state='DONE'
            ORDER BY session_date
            """,
            (x1.MODEL_ID, fingerprint),
        ).fetchall()
    sessions: list[str] = []
    for row in rows:
        verified = x1._verify_existing_done(dict(row))
        sessions.append(str(verified["session_date"]))
    if len(sessions) > X1_FORWARD_TARGET:
        raise RuntimeError(
            f"V4_X1_COUNTER_EXCEEDS_FROZEN_TARGET:{len(sessions)}>{X1_FORWARD_TARGET}"
        )
    return {
        "model_id": x1.MODEL_ID,
        "model_fingerprint": fingerprint,
        "completed": len(sessions),
        "target": X1_FORWARD_TARGET,
        "remaining": X1_FORWARD_TARGET - len(sessions),
        "sessions": sessions,
        "artifact_verification": "PASS_ALL_DONE_ROWS",
        "protected_outcome_accessed": False,
    }


def _pipeline_log_paths(runtime_root: str | Path, run_id: str) -> tuple[Path, Path]:
    root = runtime_paths(runtime_root).monitor_root / "eod_automation" / "v4_x1_pipeline"
    return root / "runs" / f"{run_id}.json", root / "latest.json"


def _persist(runtime_root: str | Path, run_id: str, result: dict[str, Any]) -> None:
    run_path, latest_path = _pipeline_log_paths(runtime_root, run_id)
    write_manifest_atomic(run_path, result)
    write_manifest_atomic(
        latest_path,
        result
        | {
            "run_log_path": str(run_path),
            "run_log_sha256": sha256_file(run_path),
        },
    )


def run_eod_v4_x1_pipeline(
    runtime_root: str | Path,
    x1_model_root: str | Path,
    *,
    repo_root: str | Path,
    batch_size: int = 100,
    observed_by: str = x1.DEFAULT_OBSERVED_BY,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Run canonical EOD catch-up, then one safe X1 score/verification step."""

    started = (now or _now_jakarta()).astimezone(JAKARTA)
    run_id = f"{started.astimezone(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
    result: dict[str, Any] = {
        "schema_version": PIPELINE_SCHEMA_VERSION,
        "run_id": run_id,
        "status": "RUNNING",
        "started_at_jakarta": started.isoformat(),
        "runtime_root": str(Path(runtime_root).expanduser().resolve()),
        "x1_model_root": str(Path(x1_model_root).expanduser().resolve()),
        "provider_calls_from_x1": False,
        "protected_outcome_accessed": False,
        "model_refit": False,
        "model_retuned": False,
        "same_day_prospective_score_required": True,
        "late_backfill_counter_policy": "CONTINUITY_ONLY_NOT_X1_COUNTER",
    }

    try:
        eod = run_eod_catchup(runtime_root, batch_size=batch_size)
        result["eod"] = eod
        if eod.get("status") != "NO_MISSING_SESSION":
            result["status"] = "EOD_FAILED_X1_NOT_RUN"
            result["finished_at_jakarta"] = _now_jakarta().isoformat()
            _persist(runtime_root, run_id, result)
            return result

        if not bool(eod.get("today_capture_allowed")):
            result["status"] = "PIPELINE_OK_PRIOR_SESSION_CATCHUP_ONLY_BEFORE_EOD"
            result["x1_score_attempted"] = False
            result["x1_counter"] = _verified_x1_counter(runtime_root)
            result["finished_at_jakarta"] = _now_jakarta().isoformat()
            _persist(runtime_root, run_id, result)
            return result

        original_fresh_sessions: Callable[..., Any] = x1._fresh_sessions
        operational_ignored: list[dict[str, Any]] = []

        def same_day_fresh_sessions(*args, **kwargs):
            pending, ignored, ready_by_date = original_fresh_sessions(*args, **kwargs)
            eligible, late = _filter_same_day_pending(pending, now=started)
            operational_ignored.extend(late)
            return eligible, [*ignored, *late], ready_by_date

        x1._fresh_sessions = same_day_fresh_sessions
        try:
            try:
                score = x1.score_v4_x1_session(
                    runtime_root,
                    x1_model_root,
                    repo_root=repo_root,
                    session_date=None,
                    observed_by=observed_by,
                )
            except RuntimeError as error:
                if str(error) not in NO_SCORE_ERRORS:
                    raise
                score = {
                    "status": "V4_X1_NO_ELIGIBLE_SAME_DAY_SCORE",
                    "reason": str(error),
                    "provider_calls": False,
                    "protected_outcome_accessed": False,
                    "model_refit": False,
                    "model_retuned": False,
                }
        finally:
            x1._fresh_sessions = original_fresh_sessions

        result["x1_score_attempted"] = True
        result["x1_score"] = score
        result["operationally_ignored_late_sessions"] = operational_ignored
        score_status = str(score.get("status") or "")
        if score_status == "V4_X1_PROSPECTIVE_SCORE_DONE":
            result["status"] = "PIPELINE_OK_X1_NEW_SCORE_COMMITTED"
        elif score_status == "V4_X1_SCORE_ALREADY_DONE_VERIFIED":
            result["status"] = "PIPELINE_OK_X1_EXISTING_SCORE_VERIFIED"
        elif score_status == "V4_X1_NO_ELIGIBLE_SAME_DAY_SCORE":
            result["status"] = "PIPELINE_OK_NO_ELIGIBLE_SAME_DAY_X1_SCORE"
        else:
            raise RuntimeError(f"V4_X1_PIPELINE_UNEXPECTED_SCORE_STATUS:{score_status}")

        result["x1_counter"] = _verified_x1_counter(runtime_root)
        result["finished_at_jakarta"] = _now_jakarta().isoformat()
        _persist(runtime_root, run_id, result)
        return result
    except Exception as error:
        result.update(
            {
                "status": "PIPELINE_FAILED",
                "error_code": type(error).__name__.upper(),
                "error_message": str(error),
                "finished_at_jakarta": _now_jakarta().isoformat(),
            }
        )
        _persist(runtime_root, run_id, result)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Canonical EOD + frozen V4-X1 pipeline")
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--x1-model-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--observed-by", default=x1.DEFAULT_OBSERVED_BY)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_eod_v4_x1_pipeline(
        args.runtime_root,
        args.x1_model_root,
        repo_root=args.repo_root,
        batch_size=args.batch_size,
        observed_by=args.observed_by,
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, default=str))
    return 0 if str(result.get("status", "")).startswith("PIPELINE_OK_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
