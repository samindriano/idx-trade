from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, time, timezone
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
import uuid

from .official_trading_schedule_v1 import VerifiedOfficialTradingSchedule
from .stockbit_intraday_cloud_archive import (
    IntradaySlotCommit,
    SLOTS,
    StockbitIntradayCloudArchive,
    StockbitIntradayCloudError,
)
from .stockbit_intraday_cloud_storage import build_runtime_snapshot, restore_runtime_snapshot
from .stockbit_intraday_daily_v2 import DailyCycleResult, default_policy, run_daily_cycle
from .stockbit_intraday_eod_context import VerifiedIntradayEodContext
from .stockbit_intraday_runtime import JAKARTA, SessionJournal


INTRADAY_ROOT_NAME = "intraday"
SLOT_DUE_TIMES = {
    "1830": time(18, 30),
    "1930": time(19, 30),
    "2030": time(20, 30),
}


def validate_intraday_capture_window(
    *, expected_date: date, slot: str, now: datetime
) -> None:
    """Admit only a current-session intraday recovery objective.

    Intraday completion is a session recovery objective with slot provenance,
    not a second instantaneous observation at the scheduler's nominal wake-up.
    A delayed same-day retry may therefore resume residual work, but a future
    or prior Jakarta date is retroactive/ambiguous and is rejected before any
    provider stage.  The observation contract closes at the end of the current
    Jakarta session date; Cloudflare ``latest`` values are dispatch wake-up
    bounds, not this runner's semantic admission rule.
    """

    if slot not in SLOT_DUE_TIMES:
        raise StockbitIntradayCloudError(f"STOCKBIT_INTRADAY_SLOT_INVALID:{slot}")
    if now.tzinfo is None or now.utcoffset() is None:
        raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_CLOUD_CLOCK_NOT_TIMEZONE_AWARE")
    local = now.astimezone(JAKARTA)
    if local.date() != expected_date:
        raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_RETROACTIVE_SESSION_FORBIDDEN")
    if local.timetz().replace(tzinfo=None) < SLOT_DUE_TIMES[slot]:
        raise StockbitIntradayCloudError(f"STOCKBIT_INTRADAY_SLOT_TOO_EARLY:{slot}")


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


def restore_progress_snapshot(
    progress: tuple[dict[str, Any], bytes],
    journal_root: str | Path,
) -> None:
    payload, raw = progress
    snapshot = payload.get("snapshot")
    if not isinstance(snapshot, dict):
        raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_PROGRESS_SNAPSHOT_INVALID")
    expected_sha256 = str(snapshot.get("sha256") or "").lower()
    if len(expected_sha256) != 64:
        raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_PROGRESS_SNAPSHOT_INVALID")
    restore_runtime_snapshot(
        raw,
        {INTRADAY_ROOT_NAME: Path(journal_root).resolve()},
        expected_sha256=expected_sha256,
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
    validate_intraday_capture_window(expected_date=expected_date, slot=slot, now=now)

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
    current_claim = archive.existing_claim(expected_date, slot)
    current_progress = archive.latest_progress(expected_date, slot)
    prior = archive.latest_committed_slot_before(expected_date, slot)
    progress_source_slot = slot
    progress = current_progress
    if current_claim is not None:
        claim_payload, current_claim_sha = current_claim
        if claim_payload.get("code_identity") != dict(code_identity):
            raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_SLOT_CLAIM_CODE_IDENTITY_MISMATCH")
        if progress is not None:
            if progress[0].get("claim_sha256") != current_claim_sha:
                raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_PROGRESS_CLAIM_MISMATCH")
        progress_source_slot = slot
    elif progress is None and prior is None:
        prior_progress = archive.latest_progress_before(expected_date, slot)
        if prior_progress is not None:
            progress = prior_progress
            progress_source_slot = str(progress[0].get("slot") or "")
            if progress_source_slot not in SLOTS:
                raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_PROGRESS_SOURCE_SLOT_INVALID")
            source_claim = archive.existing_claim(expected_date, progress_source_slot)
            if source_claim is None or source_claim[1] != str(progress[0].get("claim_sha256") or ""):
                raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_PROGRESS_SOURCE_CLAIM_MISMATCH")
            if progress[0].get("code_identity") != dict(code_identity):
                raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_PROGRESS_CODE_IDENTITY_MISMATCH")
    if progress is not None:
        restore_progress_snapshot(progress, root)
    elif prior is not None:
        restore_intraday_snapshot(archive, prior, root)

    policy = _policy_for_session(archive, schedule.session_dates, expected_date)
    claim_sha256 = archive.claim_slot(
        session_date=expected_date,
        slot=slot,
        claimed_at_utc=now.astimezone(timezone.utc).isoformat(),
        code_identity=code_identity,
        claim_id=uuid.uuid4().hex,
        resume_if_stale=current_claim is not None,
    )
    evidence_slot = progress_source_slot
    evidence_claim_sha256 = (
        str(progress[0].get("claim_sha256") or "") if progress is not None else claim_sha256
    )
    next_progress_sequence = int(progress[0].get("sequence") or -1) + 1 if progress is not None and progress_source_slot == slot else 0

    def checkpoint() -> None:
        nonlocal next_progress_sequence
        root.mkdir(parents=True, exist_ok=True)
        snapshot_bytes, _, _ = build_runtime_snapshot({INTRADAY_ROOT_NAME: root})
        archive.persist_progress(
            session_date=expected_date,
            slot=slot,
            snapshot_bytes=snapshot_bytes,
            sequence=next_progress_sequence,
            captured_at_utc=now.astimezone(timezone.utc).isoformat(),
            claim_sha256=claim_sha256,
            code_identity=code_identity,
            source_slot=slot,
        )
        next_progress_sequence += 1

    def durable_requester(ticker: str):
        nonlocal evidence_slot, evidence_claim_sha256
        saved = archive.latest_provider_evidence(
            expected_date,
            evidence_slot,
            ticker,
            claim_sha256=evidence_claim_sha256,
            code_identity=code_identity,
        )
        if saved is not None:
            return saved.get("payload"), dict(saved.get("request_meta") or {})
        payload, request_meta = requester(ticker)
        archive.persist_provider_evidence(
            session_date=expected_date,
            slot=slot,
            ticker=ticker,
            payload=payload,
            request_meta=request_meta,
            captured_at_utc=now.astimezone(timezone.utc).isoformat(),
            claim_sha256=claim_sha256,
            code_identity=code_identity,
        )
        evidence_slot = slot
        evidence_claim_sha256 = claim_sha256
        return payload, request_meta

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
        requester=durable_requester,
        max_new_tickers=max_new_tickers,
        monthly_quota_reserve=monthly_quota_reserve,
        shadow_sessions_required=shadow_sessions_required,
        recheck_every=recheck_every,
        checkpoint=checkpoint,
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
        claim_sha256=claim_sha256,
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
