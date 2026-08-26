from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping, Sequence


SUCCESS = "SUCCESS"
SKIPPED_IDX_NO_ACTIVITY = "SKIPPED_IDX_NO_ACTIVITY"
REQUEST_ERROR = "REQUEST_ERROR"
NO_CHART_404 = "NO_CHART_404"
REQUEST_TERMINAL_ERROR = "REQUEST_TERMINAL_ERROR"
QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"

ADMISSIBLE_TERMINAL_STATUSES = frozenset(
    {
        SUCCESS,
        SKIPPED_IDX_NO_ACTIVITY,
    }
)

# REQUEST_ERROR is deliberately reserved for failures that can plausibly
# recover later in the same session (transport failure, exhausted bounded 5xx
# retries, bounded short-window 429, etc.). Permanent/session-terminal request
# failures have explicit blocking statuses below.
RETRYABLE_STATUSES = frozenset({REQUEST_ERROR})

BLOCKING_TERMINAL_STATUSES = frozenset(
    {
        NO_CHART_404,
        REQUEST_TERMINAL_ERROR,
        QUOTA_EXHAUSTED,
        "EMPTY_SESSION",
        "NO_VALID_POINTS",
        "NON_CURRENT_SESSION",
        "IDENTITY_OR_PAYLOAD_ERROR",
        "MULTI_SESSION_PAYLOAD",
        "TRADING_DATE_METADATA_MISMATCH",
        "DUPLICATE_TIMESTAMP_CONFLICT",
    }
)

KNOWN_STATUSES = ADMISSIBLE_TERMINAL_STATUSES | RETRYABLE_STATUSES | BLOCKING_TERMINAL_STATUSES


@dataclass(frozen=True)
class RecoveryPlan:
    retry: tuple[str, ...]
    admissible_terminal: tuple[str, ...]
    blocking_terminal: tuple[str, ...]
    unknown_blocking: tuple[str, ...]
    missing: tuple[str, ...]

    @property
    def pending(self) -> tuple[str, ...]:
        """Only never-attempted or explicitly transient-failure tickers."""
        return self.missing + self.retry


@dataclass(frozen=True)
class CompletionState:
    universe_count: int
    observed_count: int
    admissible_terminal_count: int
    retryable_count: int
    blocking_count: int
    missing_count: int
    all_observed: bool
    all_terminal: bool
    admissible_complete: bool


def _normalise_status(value: object) -> str:
    return str(value or "").strip().upper()


def build_recovery_plan(
    tickers: Sequence[str],
    status_by_ticker: Mapping[str, object],
) -> RecoveryPlan:
    ordered = [str(ticker).strip().upper() for ticker in tickers]
    if len(set(ordered)) != len(ordered):
        raise ValueError("duplicate ticker in frozen intraday universe")

    retry: list[str] = []
    admissible: list[str] = []
    blocking: list[str] = []
    unknown: list[str] = []
    missing: list[str] = []

    for ticker in ordered:
        if ticker not in status_by_ticker:
            missing.append(ticker)
            continue
        raw = status_by_ticker[ticker]
        status = _normalise_status(raw.get("status")) if isinstance(raw, Mapping) else _normalise_status(raw)
        if status in ADMISSIBLE_TERMINAL_STATUSES:
            admissible.append(ticker)
        elif status in RETRYABLE_STATUSES:
            retry.append(ticker)
        elif status in BLOCKING_TERMINAL_STATUSES:
            blocking.append(ticker)
        else:
            unknown.append(ticker)

    return RecoveryPlan(
        retry=tuple(retry),
        admissible_terminal=tuple(admissible),
        blocking_terminal=tuple(blocking),
        unknown_blocking=tuple(unknown),
        missing=tuple(missing),
    )


def completion_state(
    tickers: Sequence[str],
    status_by_ticker: Mapping[str, object],
) -> CompletionState:
    plan = build_recovery_plan(tickers, status_by_ticker)
    universe_count = len(tickers)
    missing_count = len(plan.missing)
    retryable_count = len(plan.retry)
    blocking_count = len(plan.blocking_terminal) + len(plan.unknown_blocking)
    admissible_count = len(plan.admissible_terminal)
    observed_count = universe_count - missing_count
    all_observed = missing_count == 0
    all_terminal = all_observed and retryable_count == 0
    admissible_complete = all_terminal and blocking_count == 0 and admissible_count == universe_count
    return CompletionState(
        universe_count=universe_count,
        observed_count=observed_count,
        admissible_terminal_count=admissible_count,
        retryable_count=retryable_count,
        blocking_count=blocking_count,
        missing_count=missing_count,
        all_observed=all_observed,
        all_terminal=all_terminal,
        admissible_complete=admissible_complete,
    )


def event_fingerprint(event: Mapping[str, Any]) -> str:
    canonical = json.dumps(event, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _existing_session_event(history: Sequence[Mapping[str, Any]], session_date: str) -> Mapping[str, Any] | None:
    matches = [row for row in history if str(row.get("session_date") or "") == session_date]
    if len(matches) > 1:
        raise ValueError(f"multiple Stockbit intraday policy events already recorded for {session_date}")
    return matches[0] if matches else None


def apply_policy_event_once(
    policy: Mapping[str, Any],
    *,
    session_date: date,
    run_mode: str,
    complete: bool,
    false_negative: int | None,
    certification_eligible: bool | None,
    manifest_sha256: str,
    shadow_sessions_required: int = 3,
    recheck_every: int = 10,
) -> tuple[dict[str, Any], bool]:
    """Apply at most one rollout transition per *admitted complete* session.

    Intermediate 18:30/19:30 retry states are not policy events and return a
    no-op without requiring a final manifest. Once complete, an identical
    `(session_date, manifest_sha256, event)` replay is a no-op; conflicting
    evidence for the same session is a hard error.
    """

    if shadow_sessions_required <= 0 or recheck_every <= 0:
        raise ValueError("shadow/recheck thresholds must be positive")
    if false_negative is not None and false_negative < 0:
        raise ValueError("false_negative must be non-negative")
    if run_mode not in {"SHADOW", "SHADOW_RECHECK", "ENFORCE"}:
        raise ValueError(f"invalid Stockbit intraday run mode: {run_mode}")

    updated = copy.deepcopy(dict(policy))
    updated.setdefault("mode", "SHADOW")
    updated.setdefault("consecutive_zero_fn_shadow_sessions", 0)
    updated.setdefault("enforced_sessions_since_recheck", 0)
    updated.setdefault("history", [])
    if updated["mode"] not in {"SHADOW", "ENFORCE"}:
        raise ValueError("invalid Stockbit intraday policy mode")

    # A retry slot is operational state, not a scientific/policy observation.
    # Do not consume the date before the final admissible session exists.
    if not complete:
        return updated, False

    if not manifest_sha256 or len(manifest_sha256) < 16:
        raise ValueError("manifest_sha256 is required for policy idempotency")

    session_text = session_date.isoformat()
    event_core = {
        "session_date": session_text,
        "run_mode": run_mode,
        "complete": True,
        "false_negative": false_negative,
        "certification_eligible": certification_eligible,
        "manifest_sha256": manifest_sha256,
    }
    fingerprint = event_fingerprint(event_core)
    prior = _existing_session_event(updated["history"], session_text)
    if prior is not None:
        if prior.get("event_fingerprint") == fingerprint and prior.get("manifest_sha256") == manifest_sha256:
            return updated, False
        raise ValueError(f"conflicting Stockbit intraday policy event for {session_text}")

    prior_mode = str(updated["mode"])
    reason = "COMPLETE_NO_TRANSITION"

    if run_mode in {"SHADOW", "SHADOW_RECHECK"} and certification_eligible is True:
        if false_negative == 0:
            if run_mode == "SHADOW":
                updated["consecutive_zero_fn_shadow_sessions"] = int(
                    updated.get("consecutive_zero_fn_shadow_sessions") or 0
                ) + 1
                if updated["consecutive_zero_fn_shadow_sessions"] >= shadow_sessions_required:
                    updated["mode"] = "ENFORCE"
                    updated["enforced_sessions_since_recheck"] = 0
                    reason = "SHADOW_PROMOTED_ZERO_FN"
                else:
                    reason = "SHADOW_ZERO_FN_PROGRESS"
            else:
                updated["mode"] = "ENFORCE"
                updated["enforced_sessions_since_recheck"] = 0
                reason = "PERIODIC_RECHECK_ZERO_FN"
        else:
            updated["mode"] = "SHADOW"
            updated["consecutive_zero_fn_shadow_sessions"] = 0
            updated["enforced_sessions_since_recheck"] = 0
            reason = "FALSE_NEGATIVE_REVERT_TO_SHADOW"
    elif run_mode == "ENFORCE":
        updated["enforced_sessions_since_recheck"] = int(updated.get("enforced_sessions_since_recheck") or 0) + 1
        reason = "ENFORCE_SESSION_COMPLETE"
    elif certification_eligible is False:
        if run_mode in {"SHADOW", "SHADOW_RECHECK"}:
            updated["mode"] = "SHADOW"
            updated["consecutive_zero_fn_shadow_sessions"] = 0
            updated["enforced_sessions_since_recheck"] = 0
        reason = "SHADOW_NOT_CERTIFICATION_ELIGIBLE"

    history = list(updated.get("history") or [])
    history.append(
        {
            **event_core,
            "event_fingerprint": fingerprint,
            "prior_policy_mode": prior_mode,
            "new_policy_mode": updated["mode"],
            "reason": reason,
        }
    )
    updated["history"] = history[-100:]
    updated["shadow_sessions_required"] = int(shadow_sessions_required)
    updated["recheck_every"] = int(recheck_every)
    return updated, True
