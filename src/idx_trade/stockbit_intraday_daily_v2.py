from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
import hashlib
import io
import json
from pathlib import Path
from typing import Any, Callable, Mapping

import pandas as pd

from .official_trading_schedule_v1 import VerifiedOfficialTradingSchedule
from .stockbit_intraday_admission import load_verified_session_manifest
from .stockbit_intraday_eod_context import VerifiedIntradayEodContext
from .stockbit_intraday_eod_gate import gate_skip_evidence
from .stockbit_intraday_recovery import (
    NO_CHART_404,
    SUCCESS,
    apply_policy_event_once,
    build_recovery_plan,
)
from .stockbit_intraday_runtime import (
    BatchResult,
    SessionJournal,
    run_recovery_batch,
    validate_capture_window,
)
from .stockbit_intraday_session_v2 import (
    StockbitIntradaySessionError,
    bind_gate_snapshot,
    bind_run_contract,
    finalize_admissible_session,
    load_run_contract,
)


@dataclass(frozen=True)
class ShadowMetrics:
    false_negative: int
    false_positive: int
    actual_success: int
    actual_no_chart_404: int
    certification_eligible: bool


@dataclass(frozen=True)
class DailyCycleResult:
    status: str
    session_date: str
    run_mode: str | None
    provider_calls_attempted: int
    summary: dict[str, Any] | None
    shadow_metrics: dict[str, Any] | None
    session_manifest_sha256: str | None
    policy: dict[str, Any]
    policy_event_applied: bool
    stop_reason: str | None


def default_policy() -> dict[str, Any]:
    return {
        "mode": "SHADOW",
        "consecutive_zero_fn_shadow_sessions": 0,
        "enforced_sessions_since_recheck": 0,
        "history": [],
    }


def resolve_run_mode(policy: Mapping[str, Any], *, recheck_every: int = 10) -> str:
    if recheck_every <= 0:
        raise ValueError("recheck_every must be positive")
    mode = str(policy.get("mode") or "SHADOW").upper()
    if mode == "SHADOW":
        return "SHADOW"
    if mode != "ENFORCE":
        raise ValueError("invalid Stockbit intraday policy mode")
    enforced = int(policy.get("enforced_sessions_since_recheck") or 0)
    return "SHADOW_RECHECK" if enforced >= recheck_every else "ENFORCE"


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
        + "\n"
    ).encode("utf-8")


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    stream = io.StringIO()
    frame.to_csv(stream, index=False, lineterminator="\n")
    return stream.getvalue().encode("utf-8")


def _sha_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_once(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise StockbitIntradaySessionError(f"DAILY_UNIVERSE_IMMUTABILITY_CONFLICT:{path}")
        return
    try:
        with path.open("xb") as handle:
            handle.write(payload)
    except FileExistsError:
        if path.read_bytes() != payload:
            raise StockbitIntradaySessionError(f"DAILY_UNIVERSE_IMMUTABILITY_CONFLICT:{path}")


def freeze_context_universe(
    journal: SessionJournal,
    context: VerifiedIntradayEodContext,
    *,
    captured_at: datetime,
) -> pd.DataFrame:
    """Freeze the canonical EOD listed universe without a second provider call."""

    if context.session_date != journal.expected_date.isoformat():
        raise StockbitIntradaySessionError("DAILY_EOD_CONTEXT_SESSION_MISMATCH")
    universe = context.universe[["ticker"]].copy().sort_values("ticker").reset_index(drop=True)
    universe.insert(0, "as_of_date", context.session_date)
    encoded = _csv_bytes(universe)
    metadata = {
        "expected_date": context.session_date,
        "captured_universe_at": captured_at.isoformat(),
        "universe_source": "CANONICAL_EOD_SESSION_EVIDENCE",
        "universe_rows": len(universe),
        "ticker_list_sha256": _sha_bytes(("\n".join(universe["ticker"].astype(str)) + "\n").encode("utf-8")),
        "universe_snapshot_sha256": _sha_bytes(encoded),
        "source_eod_manifest_sha256": context.eod_manifest_sha256,
        "source_session_evidence_sha256": context.universe_evidence_sha256,
        "journal_layout_version": 2,
    }
    if journal.universe_path.exists() or journal.metadata_path.exists():
        existing = journal.load_universe()
        if existing["ticker"].astype(str).tolist() != universe["ticker"].astype(str).tolist():
            raise StockbitIntradaySessionError("DAILY_FROZEN_UNIVERSE_IDENTITY_MISMATCH")
        existing_meta = json.loads(journal.metadata_path.read_text(encoding="utf-8"))
        if existing_meta.get("source_eod_manifest_sha256") != context.eod_manifest_sha256:
            raise StockbitIntradaySessionError("DAILY_FROZEN_UNIVERSE_EOD_IDENTITY_MISMATCH")
        if existing_meta.get("source_session_evidence_sha256") != context.universe_evidence_sha256:
            raise StockbitIntradaySessionError("DAILY_FROZEN_UNIVERSE_EVIDENCE_IDENTITY_MISMATCH")
        return existing
    _write_once(journal.universe_path, encoded)
    _write_once(journal.metadata_path, _canonical_json_bytes(metadata))
    return journal.load_universe()


def _shadow_metrics(
    decisions: pd.DataFrame,
    provider_statuses: Mapping[str, Mapping[str, Any]],
) -> ShadowMetrics:
    indexed = decisions.set_index("ticker")
    false_negative = false_positive = actual_success = actual_404 = 0
    eligible = True
    for ticker, row in indexed.iterrows():
        status = str((provider_statuses.get(str(ticker)) or {}).get("status") or "")
        predicted_fetch = bool(row["would_fetch_stockbit"])
        success = status == SUCCESS
        if success:
            actual_success += 1
        elif status == NO_CHART_404:
            actual_404 += 1
        else:
            eligible = False
        if not predicted_fetch and success:
            false_negative += 1
        if predicted_fetch and not success:
            false_positive += 1
    if len(provider_statuses) != len(indexed):
        eligible = False
    return ShadowMetrics(
        false_negative=false_negative,
        false_positive=false_positive,
        actual_success=actual_success,
        actual_no_chart_404=actual_404,
        certification_eligible=eligible,
    )


def _apply_enforced_skips(
    journal: SessionJournal,
    context: VerifiedIntradayEodContext,
    *,
    now: datetime,
) -> None:
    for _, row in context.gate.decisions.iterrows():
        if str(row["gate_decision"]) != "SKIP_NO_ACTIVITY":
            continue
        journal.record_gate_skip(
            str(row["ticker"]),
            captured_at=now,
            gate_evidence=gate_skip_evidence(context.gate, row.to_dict()),
        )


def _reconcile_shadow_404s(
    journal: SessionJournal,
    context: VerifiedIntradayEodContext,
    *,
    statuses: Mapping[str, Mapping[str, Any]],
    now: datetime,
) -> None:
    for _, row in context.gate.decisions.iterrows():
        if str(row["gate_decision"]) != "SKIP_NO_ACTIVITY":
            continue
        ticker = str(row["ticker"])
        observed = str((statuses.get(ticker) or {}).get("status") or "")
        if observed != NO_CHART_404:
            continue
        journal.record_gate_skip(
            ticker,
            captured_at=now,
            gate_evidence=gate_skip_evidence(context.gate, row.to_dict()),
        )


def _replay_verified_final(
    *,
    journal: SessionJournal,
    schedule: VerifiedOfficialTradingSchedule,
    context: VerifiedIntradayEodContext | None,
    policy: Mapping[str, Any],
    expected_date: date,
    shadow_sessions_required: int,
    recheck_every: int,
) -> DailyCycleResult | None:
    loaded = load_verified_session_manifest(journal)
    if loaded is None:
        return None
    payload, session_manifest_sha = loaded
    if payload.get("schedule_attestation_sha256") != schedule.attestation_sha256:
        raise StockbitIntradaySessionError("FINAL_SESSION_SCHEDULE_IDENTITY_MISMATCH")
    if context is not None and payload.get("eod_manifest_sha256") != context.eod_manifest_sha256:
        raise StockbitIntradaySessionError("FINAL_SESSION_EOD_IDENTITY_MISMATCH")

    run_mode = str(payload["run_mode"])
    metrics_payload = payload.get("shadow_metrics")
    false_negative: int | None = None
    certification_eligible: bool | None = None
    if run_mode in {"SHADOW", "SHADOW_RECHECK"}:
        if not isinstance(metrics_payload, dict):
            raise StockbitIntradaySessionError("FINAL_SESSION_SHADOW_METRICS_MISSING")
        try:
            false_negative = int(metrics_payload["false_negative"])
        except (KeyError, TypeError, ValueError) as exc:
            raise StockbitIntradaySessionError("FINAL_SESSION_FALSE_NEGATIVE_INVALID") from exc
        certification_eligible = metrics_payload.get("certification_eligible")
        if certification_eligible not in {True, False}:
            raise StockbitIntradaySessionError("FINAL_SESSION_CERTIFICATION_ELIGIBLE_INVALID")
    elif metrics_payload is not None:
        raise StockbitIntradaySessionError("FINAL_SESSION_ENFORCE_SHADOW_METRICS_PRESENT")

    updated_policy, policy_applied = apply_policy_event_once(
        policy,
        session_date=expected_date,
        run_mode=run_mode,
        complete=True,
        false_negative=false_negative,
        certification_eligible=certification_eligible,
        manifest_sha256=session_manifest_sha,
        shadow_sessions_required=shadow_sessions_required,
        recheck_every=recheck_every,
    )
    completion = payload.get("completion")
    if not isinstance(completion, dict):
        raise StockbitIntradaySessionError("FINAL_SESSION_COMPLETION_INVALID")
    return DailyCycleResult(
        status="ADMISSIBLE_COMPLETE",
        session_date=expected_date.isoformat(),
        run_mode=run_mode,
        provider_calls_attempted=0,
        summary=dict(completion),
        shadow_metrics=dict(metrics_payload) if isinstance(metrics_payload, dict) else None,
        session_manifest_sha256=session_manifest_sha,
        policy=updated_policy,
        policy_event_applied=policy_applied,
        stop_reason="ALREADY_FINALIZED_VERIFIED",
    )


def run_daily_cycle(
    *,
    expected_date: date,
    now: datetime,
    schedule: VerifiedOfficialTradingSchedule,
    context: VerifiedIntradayEodContext | None,
    journal: SessionJournal | None,
    policy: Mapping[str, Any],
    requester: Callable[[str], tuple[object | None, Mapping[str, Any]]],
    max_new_tickers: int = 1_200,
    monthly_quota_reserve: int = 3_000,
    shadow_sessions_required: int = 3,
    recheck_every: int = 10,
) -> DailyCycleResult:
    session = expected_date.isoformat()
    policy_copy = json.loads(json.dumps(dict(policy)))
    if session < schedule.coverage_start or session > schedule.coverage_end:
        raise ValueError("Stockbit intraday session is outside verified official schedule coverage")
    if session not in schedule.session_dates:
        return DailyCycleResult(
            status="WEEKEND_OR_HOLIDAY_NOOP",
            session_date=session,
            run_mode=None,
            provider_calls_attempted=0,
            summary=None,
            shadow_metrics=None,
            session_manifest_sha256=None,
            policy=policy_copy,
            policy_event_applied=False,
            stop_reason="NO_PLANNED_OFFICIAL_SESSION_TODAY",
        )

    validate_capture_window(expected_date=expected_date, now=now)
    if journal is not None:
        if journal.expected_date != expected_date:
            raise ValueError("Stockbit intraday journal session mismatch")
        replay = _replay_verified_final(
            journal=journal,
            schedule=schedule,
            context=context,
            policy=policy_copy,
            expected_date=expected_date,
            shadow_sessions_required=shadow_sessions_required,
            recheck_every=recheck_every,
        )
        if replay is not None:
            return replay

    if context is None:
        return DailyCycleResult(
            status="WAITING_CANONICAL_EOD_GATE",
            session_date=session,
            run_mode=None,
            provider_calls_attempted=0,
            summary=None,
            shadow_metrics=None,
            session_manifest_sha256=None,
            policy=policy_copy,
            policy_event_applied=False,
            stop_reason="CANONICAL_EOD_DATA_READY_NOT_AVAILABLE",
        )
    if journal is None:
        raise ValueError("journal is required once canonical EOD context is available")
    if context.session_date != session:
        raise ValueError("Stockbit intraday daily identity mismatch")

    freeze_context_universe(journal, context, captured_at=now)
    gate_sha = bind_gate_snapshot(journal, context)

    contract_path = journal.root / "session_contract.json"
    if contract_path.exists():
        run_mode = str(load_run_contract(journal)["run_mode"])
    else:
        run_mode = resolve_run_mode(policy_copy, recheck_every=recheck_every)
    bind_run_contract(
        journal,
        run_mode=run_mode,
        schedule_attestation_sha256=schedule.attestation_sha256,
        gate_manifest_sha256=gate_sha,
    )

    if run_mode == "ENFORCE":
        _apply_enforced_skips(journal, context, now=now)

    batch: BatchResult = run_recovery_batch(
        journal,
        requester=requester,
        now=now,
        max_new_tickers=max_new_tickers,
        monthly_quota_reserve=monthly_quota_reserve,
    )

    metrics: ShadowMetrics | None = None
    if run_mode in {"SHADOW", "SHADOW_RECHECK"}:
        pre_reconcile = journal.latest_status_by_ticker()
        plan = build_recovery_plan(
            journal.load_universe()["ticker"].astype(str).tolist(),
            pre_reconcile,
        )
        if plan.missing or plan.retry:
            return DailyCycleResult(
                status="WAITING_RECOVERY_RETRY",
                session_date=session,
                run_mode=run_mode,
                provider_calls_attempted=len(batch.attempted),
                summary=journal.summary(),
                shadow_metrics=None,
                session_manifest_sha256=None,
                policy=policy_copy,
                policy_event_applied=False,
                stop_reason=batch.stop_reason,
            )
        metrics = _shadow_metrics(context.gate.decisions, pre_reconcile)
        _reconcile_shadow_404s(journal, context, statuses=pre_reconcile, now=now)

    summary = journal.summary()
    if summary.get("admissible_complete") is not True:
        plan = journal.recovery_plan()
        status = "WAITING_RECOVERY_RETRY" if (plan.missing or plan.retry) else "BLOCKED_NON_ADMISSIBLE_TERMINAL"
        return DailyCycleResult(
            status=status,
            session_date=session,
            run_mode=run_mode,
            provider_calls_attempted=len(batch.attempted),
            summary=summary,
            shadow_metrics=asdict(metrics) if metrics is not None else None,
            session_manifest_sha256=None,
            policy=policy_copy,
            policy_event_applied=False,
            stop_reason=batch.stop_reason,
        )

    metrics_payload = asdict(metrics) if metrics is not None else None
    _, session_manifest_sha = finalize_admissible_session(
        journal,
        shadow_metrics=metrics_payload,
    )
    updated_policy, policy_applied = apply_policy_event_once(
        policy_copy,
        session_date=expected_date,
        run_mode=run_mode,
        complete=True,
        false_negative=None if metrics is None else metrics.false_negative,
        certification_eligible=None if metrics is None else metrics.certification_eligible,
        manifest_sha256=session_manifest_sha,
        shadow_sessions_required=shadow_sessions_required,
        recheck_every=recheck_every,
    )
    return DailyCycleResult(
        status="ADMISSIBLE_COMPLETE",
        session_date=session,
        run_mode=run_mode,
        provider_calls_attempted=len(batch.attempted),
        summary=summary,
        shadow_metrics=metrics_payload,
        session_manifest_sha256=session_manifest_sha,
        policy=updated_policy,
        policy_event_applied=policy_applied,
        stop_reason=batch.stop_reason,
    )
