from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .official_trading_schedule_v1 import VerifiedOfficialTradingSchedule
from .stockbit_intraday_cloud_archive import (
    IntradaySlotCommit,
    StockbitIntradayCloudArchive,
    StockbitIntradayCloudError,
)
from .stockbit_intraday_cloud_storage import build_runtime_snapshot, restore_runtime_snapshot
from .stockbit_intraday_daily_v2 import DailyCycleResult, default_policy, run_daily_cycle
from .stockbit_intraday_eod_context import VerifiedIntradayEodContext
from .stockbit_intraday_runtime import SessionJournal


INTRADAY_ROOT_NAME = "intraday"


def _slot_result_payload(archive: StockbitIntradayCloudArchive, commit: IntradaySlotCommit) -> dict[str, Any]:
    raw = archive.store.read(commit.result_key)
    if raw is None:
        raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_RESULT_MISSING")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_RESULT_INVALID") from exc
    if not isinstance(payload, dict):
        raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_RESULT_INVALID")
    return payload


def restore_intraday_snapshot(
    archive: StockbitIntradayCloudArchive,
    commit: IntradaySlotCommit,
    journal_root: str | Path,
) -> None:
    raw = archive.store.read(commit.snapshot_key)
    if raw is None:
        raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_SNAPSHOT_MISSING")
    restore_runtime_snapshot(
        raw,
        {INTRADAY_ROOT_NAME: Path(journal_root).resolve()},
        expected_sha256=commit.snapshot_sha256,
    )


def _policy_for_session(
    archive: StockbitIntradayCloudArchive,
    schedule_dates: Sequence[str],
    session_date: date,
) -> dict[str, Any]:
    checkpoint = archive.latest_policy_checkpoint(
        schedule_dates,
        before_or_equal=session_date.isoformat(),
    )
    if checkpoint is None:
        return default_policy()
    return dict(checkpoint["policy"])


def _repair_policy_from_existing_final(
    archive: StockbitIntradayCloudArchive,
    commit: IntradaySlotCommit,
) -> None:
    if commit.status != "ADMISSIBLE_COMPLETE":
        return
    result = _slot_result_payload(archive, commit)
    manifest_sha = result.get("session_manifest_sha256")
    policy = result.get("policy")
    if not isinstance(policy, dict) or not isinstance(manifest_sha, str) or len(manifest_sha) != 64:
        raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_FINAL_SLOT_POLICY_EVIDENCE_INVALID")
    archive.commit_policy_checkpoint(
        session_date=commit.session_date,
        session_manifest_sha256=manifest_sha,
        policy=policy,
    )


def run_cloud_slot(
    *,
    expected_date: date,
    slot: str,
    now: datetime,
    schedule: VerifiedOfficialTradingSchedule,
    context: VerifiedIntradayEodContext | None,
    archive: StockbitIntradayCloudArchive,
    journal_root: str | Path,
    requester: Callable[[str], tuple[object | None, Mapping[str, Any]]],
    code_identity: Mapping[str, Any],
    max_new_tickers: int = 1_200,
    monthly_quota_reserve: int = 3_000,
    shadow_sessions_required: int = 3,
    recheck_every: int = 10,
) -> IntradaySlotCommit:
    """Run one prospective cloud slot with deterministic restart semantics."""

    if now.tzinfo is None or now.utcoffset() is None:
        raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_CLOUD_CLOCK_NOT_TIMEZONE_AWARE")

    existing = archive.existing_slot(expected_date, slot)
    if existing is not None:
        _repair_policy_from_existing_final(archive, existing)
        return existing

    # Do not permit a delayed/manual earlier slot to run after a later slot has
    # already committed. That would create an alternate provider-call history.
    later = archive.later_committed_slot_after(expected_date, slot)
    if later is not None:
        raise StockbitIntradayCloudError(
            f"STOCKBIT_INTRADAY_LATER_SLOT_ALREADY_COMMITTED:{later.slot}"
        )

    root = Path(journal_root).resolve()
    prior = archive.latest_committed_slot_before(expected_date, slot)
    if prior is not None:
        restore_intraday_snapshot(archive, prior, root)

    policy = _policy_for_session(archive, schedule.session_dates, expected_date)
    journal: SessionJournal | None = None
    if context is not None or (root / "session_manifest.json").exists() or (root / "day_metadata.json").exists():
        journal = SessionJournal(root, expected_date=expected_date)

    result: DailyCycleResult = run_daily_cycle(
        expected_date=expected_date,
        now=now,
        schedule=schedule,
        context=context,
        journal=journal,
        policy=policy,
        requester=requester,
        max_new_tickers=max_new_tickers,
        monthly_quota_reserve=monthly_quota_reserve,
        shadow_sessions_required=shadow_sessions_required,
        recheck_every=recheck_every,
    )
    root.mkdir(parents=True, exist_ok=True)
    snapshot_bytes, _, _ = build_runtime_snapshot({INTRADAY_ROOT_NAME: root})
    result_payload = asdict(result)
    commit = archive.commit_slot(
        session_date=expected_date,
        slot=slot,
        status=result.status,
        snapshot_bytes=snapshot_bytes,
        result_payload=result_payload,
        code_identity=code_identity,
        eod_manifest_sha256=context.eod_manifest_sha256 if context is not None else None,
        session_manifest_sha256=result.session_manifest_sha256,
    )
    if result.status == "ADMISSIBLE_COMPLETE":
        if not result.session_manifest_sha256:
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_FINAL_SESSION_MANIFEST_SHA_MISSING")
        archive.commit_policy_checkpoint(
            session_date=expected_date,
            session_manifest_sha256=result.session_manifest_sha256,
            policy=result.policy,
        )
    return commit
