"""Outcome-blind driver for a frozen contiguous historical replay scope.

The driver owns only scope/sequence control.  The existing T0 bootstrap and
single-transition replay remain injectable boundaries so synthetic callers can
exercise the sequencing rules without touching a runtime root.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from .e2e_paper_orchestration_v1 import bootstrap_t0
from .historical_e2e_replay_v1 import (
    HistoricalE2EReplayError,
    HistoricalReplayArtifacts,
    replay_verified_session,
)
from .historical_e2e_scope_validator_v1 import (
    STRICT_SCOPE_FROZEN,
    load_replay_scope,
)


RUN_SCHEMA_VERSION = "idx_trade_historical_e2e_replay_run_v1"


class HistoricalE2EReplayRunnerError(HistoricalE2EReplayError):
    """Raised when a frozen replay cannot be started safely."""


# Keep the shorter spelling available to callers that use the replay module's
# existing ``...ReplayError`` convention.
HistoricalE2EReplayRunError = HistoricalE2EReplayRunnerError


BootstrapCallback = Callable[..., object]
TransitionCallback = Callable[..., object]


@dataclass(frozen=True)
class HistoricalReplayTransitionSummary:
    """Outcome-blind, path-independent evidence for one transition."""

    session_index: int
    decision_session_date: str
    execution_session_date: str
    status: str
    execution_sha256: str
    runtime_snapshot_sha256: str
    runtime_state_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "session_index": self.session_index,
            "decision_session_date": self.decision_session_date,
            "execution_session_date": self.execution_session_date,
            "status": self.status,
            "execution_sha256": self.execution_sha256,
            "runtime_snapshot_sha256": self.runtime_snapshot_sha256,
            "runtime_state_sha256": self.runtime_state_sha256,
        }

    as_dict = to_dict


@dataclass(frozen=True)
class HistoricalReplayRunSummary:
    """Deterministic run evidence without runtime/accounting measurements."""

    status: str
    scope_payload_sha256: str
    strict_session_count: int
    transitions: tuple[HistoricalReplayTransitionSummary, ...]
    summary_sha256: str
    outcome_access: bool = False
    model_fit: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": RUN_SCHEMA_VERSION,
            "status": self.status,
            "scope_payload_sha256": self.scope_payload_sha256,
            "strict_session_count": self.strict_session_count,
            "transition_count": len(self.transitions),
            "outcome_access": self.outcome_access,
            "model_fit": self.model_fit,
            "transitions": [item.to_dict() for item in self.transitions],
            "summary_sha256": self.summary_sha256,
        }

    as_dict = to_dict

    def __getitem__(self, key: str) -> object:
        """Allow summary consumers to use either attributes or a mapping view."""

        return self.to_dict()[key]

    def get(self, key: str, default: object = None) -> object:
        return self.to_dict().get(key, default)


def _canonical_bytes(value: Mapping[str, object]) -> bytes:
    try:
        encoded = json.dumps(
            dict(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    except (TypeError, ValueError, UnicodeError) as exc:
        raise HistoricalE2EReplayRunnerError(
            "HISTORICAL_REPLAY_RUN_SUMMARY_NOT_SERIALIZABLE"
        ) from exc
    return (encoded + "\n").encode("utf-8")


def canonical_summary_sha256(summary: Mapping[str, object]) -> str:
    """Hash a summary body after removing its self-declared hash."""

    body = dict(summary)
    body.pop("summary_sha256", None)
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _error(code: str, detail: object | None = None) -> None:
    if detail is None:
        raise HistoricalE2EReplayRunnerError(code)
    raise HistoricalE2EReplayRunnerError(f"{code}:{detail}")


def _scope_pairs(scope: Mapping[str, object]) -> tuple[tuple[int, str, str], ...]:
    if scope.get("status") != STRICT_SCOPE_FROZEN:
        _error(
            "HISTORICAL_REPLAY_RUN_SCOPE_NOT_FROZEN",
            scope.get("status", "MISSING"),
        )

    strict_indices = scope.get("strict_session_indices")
    if not isinstance(strict_indices, list) or not strict_indices:
        _error("HISTORICAL_REPLAY_RUN_STRICT_SCOPE_COUNT_OR_ORDER_INVALID")
    expected_indices = strict_indices

    open_payload = scope.get("open")
    if not isinstance(open_payload, Mapping):
        _error("HISTORICAL_REPLAY_RUN_SCOPE_SESSIONS_MISSING")
    raw_rows = open_payload.get("per_session")
    if not isinstance(raw_rows, list):
        _error("HISTORICAL_REPLAY_RUN_SCOPE_SESSIONS_MISSING")

    rows_by_index: dict[int, Mapping[str, object]] = {}
    for raw_row in raw_rows:
        if not isinstance(raw_row, Mapping):
            _error("HISTORICAL_REPLAY_RUN_SCOPE_SESSION_ROW_INVALID")
        raw_index = raw_row.get("session_index")
        if type(raw_index) is not int or raw_index in rows_by_index:
            _error("HISTORICAL_REPLAY_RUN_SCOPE_SESSION_INDEX_INVALID")
        rows_by_index[raw_index] = raw_row

    pairs: list[tuple[int, str, str]] = []
    for position, session_index in enumerate(expected_indices):
        if type(session_index) is not int or (
            position and session_index != expected_indices[position - 1] + 1
        ):
            _error(
                "HISTORICAL_REPLAY_RUN_STRICT_SCOPE_COUNT_OR_ORDER_INVALID",
                position,
            )
        row = rows_by_index.get(session_index)
        if row is None:
            _error(
                "HISTORICAL_REPLAY_RUN_SCOPE_SESSION_INDEX_MISSING",
                session_index,
            )
        decision = row.get("decision_session_date")
        execution = row.get("execution_session_date")
        if not isinstance(decision, str) or not isinstance(execution, str):
            _error(
                "HISTORICAL_REPLAY_RUN_SCOPE_SESSION_PAIR_INVALID",
                session_index,
            )
        pairs.append((session_index, decision, execution))
    return tuple(pairs)


def _artifact_value(
    artifact: HistoricalReplayArtifacts,
    field_name: str,
    *,
    default: object = None,
) -> object:
    return getattr(artifact, field_name, default)


def _validate_artifacts(
    artifacts: Sequence[HistoricalReplayArtifacts],
    scope_pairs: Sequence[tuple[int, str, str]],
) -> None:
    expected_count = len(scope_pairs)
    if len(artifacts) != expected_count:
        _error(
            "HISTORICAL_REPLAY_RUN_ARTIFACT_COUNT_MISMATCH",
            f"expected={expected_count},actual={len(artifacts)}",
        )

    expected_positions = {
        decision: position for position, (_, decision, _) in enumerate(scope_pairs)
    }
    seen_dates: set[str] = set()
    seen_indices: set[int] = set()
    for position, artifact in enumerate(artifacts):
        if not isinstance(artifact, HistoricalReplayArtifacts):
            _error("HISTORICAL_REPLAY_RUN_ARTIFACT_TYPE_INVALID", position)

        expected_index, expected_decision, expected_execution = scope_pairs[position]
        raw_index = _artifact_value(artifact, "session_index", default=expected_index)
        if raw_index is None:
            raw_index = expected_index
        if type(raw_index) is not int:
            _error("HISTORICAL_REPLAY_RUN_ARTIFACT_SESSION_INDEX_INVALID", position)
        if raw_index in seen_indices:
            _error("HISTORICAL_REPLAY_RUN_ARTIFACT_SESSION_INDEX_DUPLICATE", raw_index)
        seen_indices.add(raw_index)

        decision = _artifact_value(artifact, "decision_session_date")
        if not isinstance(decision, str) or not decision:
            _error("HISTORICAL_REPLAY_RUN_ARTIFACT_DECISION_DATE_INVALID", position)
        if decision in seen_dates:
            _error("HISTORICAL_REPLAY_RUN_ARTIFACT_DECISION_DATE_DUPLICATE", decision)
        seen_dates.add(decision)

        # A valid scope date appearing at a different position is specifically
        # an ordering failure; an unknown date is an exact-pair failure.
        if decision in expected_positions and expected_positions[decision] != position:
            _error("HISTORICAL_REPLAY_RUN_ARTIFACT_ORDER_INVALID", position)
        if raw_index != expected_index:
            _error("HISTORICAL_REPLAY_RUN_ARTIFACT_ORDER_INVALID", position)
        if decision != expected_decision:
            _error("HISTORICAL_REPLAY_RUN_ARTIFACT_SCOPE_PAIR_MISMATCH", position)

        optional_execution = _artifact_value(
            artifact,
            "execution_session_date",
            default=None,
        )
        if optional_execution is not None and optional_execution != expected_execution:
            _error("HISTORICAL_REPLAY_RUN_ARTIFACT_SCOPE_PAIR_MISMATCH", position)


def _result_value(result: object, field_name: str, *, default: object = None) -> object:
    if isinstance(result, Mapping):
        return result.get(field_name, default)
    return getattr(result, field_name, default)


def _required_text(result: object, field_name: str, *, position: int) -> str:
    value = _result_value(result, field_name)
    if not isinstance(value, str) or not value:
        _error("HISTORICAL_REPLAY_RUN_TRANSITION_HASH_MISSING", f"{position}.{field_name}")
    return value


def _transition_summary(
    result: object,
    *,
    session_index: int,
    decision_session_date: str,
    execution_session_date: str,
) -> HistoricalReplayTransitionSummary:
    result_decision = _result_value(result, "decision_session_date")
    if result_decision is not None and result_decision != decision_session_date:
        _error("HISTORICAL_REPLAY_RUN_TRANSITION_SCOPE_PAIR_MISMATCH", session_index)
    result_execution = _result_value(result, "execution_session_date")
    if result_execution is not None and result_execution != execution_session_date:
        _error("HISTORICAL_REPLAY_RUN_TRANSITION_SCOPE_PAIR_MISMATCH", session_index)
    if _result_value(result, "outcome_access", default=False) is True:
        _error("HISTORICAL_REPLAY_RUN_OUTCOME_ACCESS_FLAG_INVALID", session_index)

    status = _result_value(result, "status", default="REPLAYED")
    if not isinstance(status, str) or not status:
        _error("HISTORICAL_REPLAY_RUN_TRANSITION_STATUS_INVALID", session_index)
    return HistoricalReplayTransitionSummary(
        session_index=session_index,
        decision_session_date=decision_session_date,
        execution_session_date=execution_session_date,
        status=status,
        execution_sha256=_required_text(result, "execution_sha256", position=session_index),
        runtime_snapshot_sha256=_required_text(
            result,
            "runtime_snapshot_sha256",
            position=session_index,
        ),
        runtime_state_sha256=_required_text(
            result,
            "runtime_state_sha256",
            position=session_index,
        ),
    )


def _default_bootstrap_callback(
    runtime_root: str | Path,
    *,
    session_date: str,
) -> object:
    return bootstrap_t0(runtime_root, session_date=session_date)


def _default_transition_callback(
    runtime_root: str | Path,
    artifacts: HistoricalReplayArtifacts,
    *,
    scope_manifest_path: str | Path,
) -> object:
    return replay_verified_session(
        runtime_root,
        artifacts,
        scope_manifest_path=scope_manifest_path,
    )


def run_historical_e2e_replay(
    runtime_root: str | Path,
    artifacts: Sequence[HistoricalReplayArtifacts],
    *,
    scope_manifest_path: str | Path,
    bootstrap_callback: BootstrapCallback | None = None,
    transition_callback: TransitionCallback | None = None,
) -> HistoricalReplayRunSummary:
    """Run all frozen transitions in order after complete preflight validation."""

    scope = load_replay_scope(scope_manifest_path)
    scope_pairs = _scope_pairs(scope)
    try:
        artifact_sequence = tuple(artifacts)
    except TypeError as exc:
        raise HistoricalE2EReplayRunnerError(
            "HISTORICAL_REPLAY_RUN_ARTIFACT_SEQUENCE_INVALID"
        ) from exc
    _validate_artifacts(artifact_sequence, scope_pairs)

    bootstrap = bootstrap_callback or _default_bootstrap_callback
    transition = transition_callback or _default_transition_callback

    # All guards above are intentionally complete before this first mutation.
    bootstrap(runtime_root, session_date=scope_pairs[0][1])
    summaries: list[HistoricalReplayTransitionSummary] = []
    for position, (session_index, decision_date, execution_date) in enumerate(scope_pairs):
        result = transition(
            runtime_root,
            artifact_sequence[position],
            scope_manifest_path=scope_manifest_path,
        )
        summaries.append(
            _transition_summary(
                result,
                session_index=session_index,
                decision_session_date=decision_date,
                execution_session_date=execution_date,
            )
        )

    body: dict[str, object] = {
        "schema_version": RUN_SCHEMA_VERSION,
        "status": "HISTORICAL_E2E_REPLAY_COMPLETE",
        "scope_payload_sha256": str(scope["scope_payload_sha256"]),
        "strict_session_count": len(summaries),
        "transition_count": len(summaries),
        "outcome_access": False,
        "model_fit": False,
        "transitions": [item.to_dict() for item in summaries],
    }
    summary_sha256 = canonical_summary_sha256(body)
    return HistoricalReplayRunSummary(
        status=str(body["status"]),
        scope_payload_sha256=str(body["scope_payload_sha256"]),
        strict_session_count=len(summaries),
        transitions=tuple(summaries),
        summary_sha256=summary_sha256,
    )


run_historical_e2e_replay_v1 = run_historical_e2e_replay


__all__ = [
    "BootstrapCallback",
    "HistoricalE2EReplayRunError",
    "HistoricalE2EReplayRunnerError",
    "HistoricalReplayRunSummary",
    "HistoricalReplayTransitionSummary",
    "RUN_SCHEMA_VERSION",
    "TransitionCallback",
    "canonical_summary_sha256",
    "run_historical_e2e_replay",
    "run_historical_e2e_replay_v1",
]
