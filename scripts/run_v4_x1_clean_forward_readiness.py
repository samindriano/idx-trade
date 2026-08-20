"""Read-only readiness audit for accepted clean V4-X1 prospective scoring."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade import v4_x1_clean_forward_score as clean  # noqa: E402
from idx_trade import v4_x1_forward_score as legacy  # noqa: E402
from idx_trade.forward_monitoring import _connect, _parse_utc, runtime_paths  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--x1-model-root", type=Path, required=True)
    parser.add_argument("--clean-panel", type=Path, required=True)
    parser.add_argument("--clean-security-master", type=Path, required=True)
    parser.add_argument("--observed-by", default=clean.DEFAULT_OBSERVED_BY)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    clean.configure_clean_inputs(args.clean_panel, args.clean_security_master)
    model = clean._verify_model_bundle(args.x1_model_root)
    paths = runtime_paths(args.runtime_root)
    freeze = legacy._parse_timestamp(args.observed_by)

    panel = pd.read_parquet(args.clean_panel, columns=["date"])
    dates = pd.to_datetime(panel["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if dates.isna().any() or dates.empty:
        raise RuntimeError("V4_X1_CLEAN_READINESS_PANEL_DATES_INVALID")
    historical_end = pd.Timestamp(dates.max()).normalize()

    rows = legacy._snapshot_rows(paths)
    ready = {
        legacy._normal_date(row["session_date"]): row
        for row in rows
        if row.get("state") == "DATA_READY"
    }
    ignored: list[dict[str, object]] = []
    post_freeze: list[pd.Timestamp] = []
    for session, row in sorted(ready.items()):
        completed = _parse_utc(row.get("completed_at"))
        if completed is None or completed <= freeze:
            continue
        eod = legacy._session_eod_available_at_utc(session)
        if eod <= freeze:
            ignored.append(
                {
                    "session_date": session.date().isoformat(),
                    "completed_at": row.get("completed_at"),
                    "reason": "SESSION_EOD_PREDATES_CLEAN_MODEL_FREEZE",
                }
            )
            continue
        if session <= historical_end:
            raise RuntimeError("V4_X1_CLEAN_READINESS_POST_FREEZE_NOT_AFTER_HISTORY")
        post_freeze.append(session)

    with _connect(paths) as connection:
        done_rows = connection.execute(
            """
            SELECT * FROM model_runs
            WHERE model_id=? AND model_fingerprint=? AND state='DONE'
            ORDER BY session_date
            """,
            (clean.MODEL_ID, clean.EXPECTED_MODEL_MANIFEST_SHA256),
        ).fetchall()
    verified_done = [clean._verify_existing_done(dict(row)) for row in done_rows]
    if len(verified_done) > 100:
        raise RuntimeError("V4_X1_CLEAN_READINESS_COUNTER_EXCEEDS_100")

    candidate = post_freeze[0] if post_freeze else None
    missing_history: list[str] = []
    if candidate is not None:
        forward_calendar = legacy._load_forward_calendar(paths)
        if candidate not in forward_calendar:
            raise RuntimeError("V4_X1_CLEAN_READINESS_CANDIDATE_NOT_IN_FORWARD_CALENDAR")
        required = forward_calendar[(forward_calendar > historical_end) & (forward_calendar <= candidate)]
        missing_history = [
            day.date().isoformat()
            for day in required
            if legacy._normal_date(day) not in ready
        ]

    status = "V4_X1_CLEAN_FORWARD_READYNESS_WAITING_FIRST_POST_FREEZE_SESSION"
    if candidate is not None and missing_history:
        status = "V4_X1_CLEAN_FORWARD_READYNESS_BLOCKED_CANONICAL_HISTORY_GAP"
    elif candidate is not None:
        status = "V4_X1_CLEAN_FORWARD_READYNESS_CANDIDATE_AVAILABLE_SCORE_NOT_RUN"

    result = {
        "schema_version": "v4_x1_clean_forward_readiness_v1",
        "status": status,
        "model_id": clean.MODEL_ID,
        "generation": clean.GENERATION,
        "model_manifest_sha256": model["manifest_sha256"],
        "freeze_boundary": args.observed_by,
        "clean_panel_sha256": clean.EXPECTED_CLEAN_PANEL_SHA256,
        "clean_security_master_sha256": clean.EXPECTED_CLEAN_SECURITY_MASTER_SHA256,
        "historical_clean_panel_last_date": historical_end.date().isoformat(),
        "counter_completed": len(verified_done),
        "counter_target": 100,
        "counter_remaining": 100 - len(verified_done),
        "counter_sessions": [row["session_date"] for row in verified_done],
        "candidate_first_score_session": candidate.date().isoformat() if candidate is not None else None,
        "missing_canonical_history_sessions": missing_history,
        "ignored_post_freeze_backfills": ignored,
        "provider_calls": False,
        "network_calls": False,
        "model_scored": False,
        "registry_mutated": False,
        "protected_outcome_accessed": False,
        "realized_forward_outcome_loaded": False,
        "model_refit": False,
        "next": (
            "DEPLOY_EXISTING_CANONICAL_EOD_TASK_TO_CLEAN_PIPELINE; SCORE ONLY WHEN SAME-DAY POST-FREEZE SESSION IS AVAILABLE"
            if not missing_history
            else "CLOSE_CANONICAL_EOD_HISTORY_GAP_ONLY; DO_NOT BACKSCORE"
        ),
    }
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if not missing_history else 2


if __name__ == "__main__":
    raise SystemExit(main())
