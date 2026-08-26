from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .e2e_paper_cloud_runtime_v1 import (
    CloudObjectStore,
    CloudPaperArchive,
    build_runtime_snapshot,
    restore_runtime_snapshot,
)
from .official_trading_schedule_v1 import VerifiedOfficialTradingSchedule
from .stockbit_intraday_cloud_archive import (
    IntradaySlotCommit,
    StockbitIntradayCloudArchive,
    StockbitIntradayCloudError,
)
from .stockbit_intraday_daily_v2 import DailyCycleResult, default_policy, run_daily_cycle
from .stockbit_intraday_eod_context import VerifiedIntradayEodContext, load_verified_intraday_eod_context
from .stockbit_intraday_runtime import SessionJournal


INTRADAY_ROOT_NAME = "intraday"
E2E_SNAPSHOT_ROOTS = ("paper", "forward", "official_open", "ca")


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


def materialize_eod_context_from_e2e(
    *,
    store: CloudObjectStore,
    session_date: date,
    target_root: str | Path,
) -> VerifiedIntradayEodContext | None:
    """Read only the already-committed canonical E2E POST_EOD snapshot."""

    archive = CloudPaperArchive(store)
    commit = archive.existing_commit(session_date.isoformat(), "POST_EOD")
    if commit is None:
        return None
    if commit.snapshot_key is None or commit.snapshot_sha256 is None:
        raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_E2E_POST_EOD_SNAPSHOT_MISSING")
    raw = store.read(commit.snapshot_key)
    if raw is None:
        raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_E2E_POST_EOD_SNAPSHOT_MISSING")

    root = Path(target_root).resolve()
    roots = {name: root / name for name in E2E_SNAPSHOT_ROOTS}
    restore_runtime_snapshot(raw, roots, expected_sha256=commit.snapshot_sha256)
    session_dir = roots["forward"] / "forward_monitoring" / "sessions" / session_date.isoformat()
    if not session_dir.is_dir():
        raise StockbitIntradayCloudError("STOCKBIT_INTRADAY_CANONICAL_EOD_SESSION_MISSING")
    return load_verified_intraday_eod_context(session_dir, expected_date=session_date)


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

    existing = archive.existing_slot(expected_date, slot)
    if existing is not None:
        _repair_policy_from_existing_final(archive, existing)
        return existing

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
