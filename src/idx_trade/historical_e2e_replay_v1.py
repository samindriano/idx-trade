"""Artifact-driven historical E2E paper replay adapter.

The adapter is deliberately thin: the production score, EOD, Open, CA, and
dividend verifiers remain the trust boundary, while the existing E2E
orchestrator remains the state machine.  This module does not fetch data,
read labels/outcomes, fit/rescore a model, or modify the live runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Sequence

from . import forward_dividend_v1 as dividend
from . import forward_dividend_runtime_v1_1 as dividend_runtime
from .e2e_paper_orchestration_v1 import (
    CompletedExecutionResult,
    derive_required_execution_tickers,
    execute_preopen,
    load_score_manifest,
    prepare_post_eod,
)
from .forward_dividend_execution_v1_1 import (
    reconcile_corporate_action_attestation_v1_2_journal,
)
from .historical_e2e_scope_validator_v1 import (
    STRICT_SCOPE_FROZEN,
    load_replay_scope,
)
from .v4_x1_execution_v1_verify import (
    verify_eod_execution_inputs,
    verify_open_execution_inputs,
)


class HistoricalE2EReplayError(RuntimeError):
    """Raised when a replay input is not a verified, compatible artifact."""


@dataclass(frozen=True)
class HistoricalReplayArtifacts:
    """Paths for one decision-session -> next execution-session transition."""

    decision_session_date: str
    score_manifest_path: Path
    previous_score_manifest_path: Path | None
    session_ohlcv_path: Path
    model_input_path: Path
    official_calendar_path: Path
    open_manifest_path: Path
    ca_attestation_path: Path
    ca_journal_path: Path


@dataclass(frozen=True)
class HistoricalReplayResult:
    decision_session_date: str
    execution_session_date: str
    status: str
    execution_path: Path
    execution_sha256: str
    runtime_snapshot_path: Path
    runtime_snapshot_sha256: str
    runtime_state_sha256: str
    cash_idr: float
    position_count: int
    outcome_access: bool = False


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_path(path: Path, code: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise HistoricalE2EReplayError(f"{code}:{resolved}")
    return resolved


def _assert_accounting_invariants(
    state: dividend.DividendAwarePaperState,
    *,
    execution_date: str,
) -> None:
    base = state.base_state
    if base.as_of_session_date != execution_date:
        raise HistoricalE2EReplayError("HISTORICAL_REPLAY_STATE_SESSION_MISMATCH")
    if base.cash_idr < -1e-6:
        raise HistoricalE2EReplayError("HISTORICAL_REPLAY_NEGATIVE_CASH")
    tickers = [row.ticker for row in base.positions]
    if len(tickers) != len(set(tickers)):
        raise HistoricalE2EReplayError("HISTORICAL_REPLAY_DUPLICATE_POSITION")
    if any(int(row.shares) <= 0 for row in base.positions):
        raise HistoricalE2EReplayError("HISTORICAL_REPLAY_NONPOSITIVE_POSITION")
    pending = [row.ticker for row in (*base.pending_buys, *base.pending_sells)]
    if len(pending) != len(set(pending)):
        raise HistoricalE2EReplayError("HISTORICAL_REPLAY_DUPLICATE_PENDING_TICKER")
    if set(tickers) & set(pending):
        raise HistoricalE2EReplayError("HISTORICAL_REPLAY_POSITION_PENDING_OVERLAP")


def replay_verified_session(
    runtime_root: str | Path,
    artifacts: HistoricalReplayArtifacts,
    *,
    scope_manifest_path: str | Path,
) -> HistoricalReplayResult:
    """Replay one transition through public artifact verifiers and production orchestration."""

    scope = load_replay_scope(scope_manifest_path)
    if scope.get("status") != STRICT_SCOPE_FROZEN:
        raise HistoricalE2EReplayError("HISTORICAL_REPLAY_SCOPE_NOT_FROZEN")

    score_manifest = _assert_path(artifacts.score_manifest_path, "SCORE_MANIFEST_MISSING")
    previous_manifest = (
        None
        if artifacts.previous_score_manifest_path is None
        else _assert_path(artifacts.previous_score_manifest_path, "PREVIOUS_SCORE_MANIFEST_MISSING")
    )
    current_score = load_score_manifest(score_manifest)
    previous_score = None if previous_manifest is None else load_score_manifest(previous_manifest)
    if current_score.session_date != artifacts.decision_session_date:
        raise HistoricalE2EReplayError("HISTORICAL_REPLAY_SCORE_DATE_MISMATCH")

    eod = verify_eod_execution_inputs(
        session_ohlcv_path=_assert_path(artifacts.session_ohlcv_path, "EOD_OHLCV_MISSING"),
        model_input_path=_assert_path(artifacts.model_input_path, "EOD_MODEL_INPUT_MISSING"),
        official_calendar_path=_assert_path(artifacts.official_calendar_path, "CALENDAR_MISSING"),
        decision_session_date=artifacts.decision_session_date,
        required_tickers=(),
    )
    strict_indices = {
        int(value) for value in scope.get("strict_session_indices", [])
    }
    scope_rows = scope.get("open", {}).get("per_session", [])
    allowed_pairs = {
        (str(row["decision_session_date"]), str(row["execution_session_date"]))
        for row in scope_rows
        if isinstance(row, dict) and int(row.get("session_index", -1)) in strict_indices
    }
    if (
        artifacts.decision_session_date,
        eod.next_official_session_date,
    ) not in allowed_pairs:
        raise HistoricalE2EReplayError("HISTORICAL_REPLAY_SESSION_OUT_OF_SCOPE")
    runtime = Path(runtime_root).expanduser().resolve()
    required = derive_required_execution_tickers(
        runtime,
        current_score=current_score,
        previous_score=previous_score,
        eod_inputs=eod,
    )
    reconciliation = reconcile_corporate_action_attestation_v1_2_journal(
        attestation_path=_assert_path(artifacts.ca_attestation_path, "CA_ATTESTATION_MISSING"),
        journal_path=_assert_path(artifacts.ca_journal_path, "CA_JOURNAL_MISSING"),
        expected_from_session_date=artifacts.decision_session_date,
        expected_through_session_date=eod.next_official_session_date,
        required_tickers=required,
    )
    prepared = prepare_post_eod(
        runtime,
        current_score=current_score,
        previous_score=previous_score,
        eod_inputs=eod,
        ca_reconciliation=reconciliation,
    )
    open_inputs = verify_open_execution_inputs(
        execution_session_date=eod.next_official_session_date,
        manifest_path=_assert_path(artifacts.open_manifest_path, "OPEN_MANIFEST_MISSING"),
    )
    result: CompletedExecutionResult = execute_preopen(
        runtime,
        prepared_path=prepared.path,
        current_score=current_score,
        previous_score=previous_score,
        eod_inputs=eod,
        open_inputs=open_inputs,
        ca_reconciliation=reconciliation,
    )
    snapshot = dividend_runtime.load_latest_runtime_snapshot(runtime)
    _assert_accounting_invariants(snapshot.state, execution_date=eod.next_official_session_date)
    return HistoricalReplayResult(
        decision_session_date=artifacts.decision_session_date,
        execution_session_date=eod.next_official_session_date,
        status=result.status,
        execution_path=result.path,
        execution_sha256=_sha256(result.path),
        runtime_snapshot_path=snapshot.path,
        runtime_snapshot_sha256=snapshot.file_sha256,
        runtime_state_sha256=snapshot.runtime_state_sha256,
        cash_idr=float(snapshot.state.base_state.cash_idr),
        position_count=len(snapshot.state.base_state.positions),
    )


def replay_scope_manifest(path: str | Path) -> dict[str, object]:
    """Load and strictly validate an outcome-blind replay scope manifest."""

    try:
        return load_replay_scope(path)
    except Exception as exc:
        if isinstance(exc, HistoricalE2EReplayError):
            raise
        raise HistoricalE2EReplayError(str(exc)) from exc


__all__ = [
    "HistoricalE2EReplayError",
    "HistoricalReplayArtifacts",
    "HistoricalReplayResult",
    "replay_scope_manifest",
    "replay_verified_session",
]
