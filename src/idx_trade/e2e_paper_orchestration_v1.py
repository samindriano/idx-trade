"""Canonical, outcome-blind E2E paper orchestration for V4-X1.

This module composes the already-frozen Decision V2, Sizing V1, Execution V1,
official Open, and dividend-aware runtime contracts.  It intentionally does
not fetch market data or own a second provider/runtime hierarchy: callers hand
in verified score, EOD, Open, and corporate-action evidence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Callable, Mapping, Sequence

from . import forward_dividend_v1 as dividend
from . import forward_dividend_runtime_v1_1 as dividend_runtime
from .official_open_evidence_v1 import (
    ALLOWED_TRANSPORTS as OFFICIAL_OPEN_ALLOWED_TRANSPORTS,
    AUTHORITY as OFFICIAL_OPEN_AUTHORITY,
    FALLBACK_POLICY as OFFICIAL_OPEN_FALLBACK_POLICY,
    FIELD_SEMANTICS as OFFICIAL_OPEN_FIELD_SEMANTICS,
    TRANSPORT_POLICY as OFFICIAL_OPEN_TRANSPORT_POLICY,
    UPSTREAM_PATH as OFFICIAL_OPEN_UPSTREAM_PATH,
)
from .forward_dividend_execution_v1_1 import (
    _DIVIDEND_RECONCILIATION_TOKEN,
    _VERIFIED_DIVIDEND_EVIDENCE_TOKEN,
    VerifiedCashDividendEvidence,
    VerifiedDividendCAReconciliation,
    execute_open_v1_1_reconciled,
)
from .v4_x1_decision_v1_contract import VerifiedScoreSession
from .v4_x1_decision_v1_verify import verify_v4_x1_score_artifact
from .v4_x1_decision_v2_minimal import plan_v4_x1_decision_v2_minimal
from .v4_x1_execution_v1_contract import (
    ExecutionOrderPlan,
    PaperPortfolioState,
    PendingPaperIntent,
    PaperPosition,
)
from .v4_x1_execution_v1_decision_v2_adapter import (
    prepare_execution_v1_from_decision_v2,
)
from .v4_x1_execution_v1_verify import (
    VerifiedEODExecutionInputs,
    VerifiedOpenExecutionInputs,
)
from .v4_x1_sizing_v1_decision_v2_adapter import (
    VerifiedDecisionV2SizingPlan,
    verify_decision_v2_plan_for_sizing,
)
from .decision_v2_minimal import DecisionV2Plan, DecisionV2ShadowState


SCHEMA = "idx_trade_e2e_paper_orchestration_v1"
T0_SCHEMA = "idx_trade_e2e_paper_t0_v1"
PREPARED_SCHEMA = "idx_trade_e2e_paper_prepared_execution_v1"
EXECUTION_SCHEMA = "idx_trade_e2e_paper_execution_v1"
EXECUTION_TXN_SCHEMA = "idx_trade_e2e_paper_execution_transaction_v1"
META_SCHEMA = "idx_trade_e2e_paper_meta_v1"
INITIAL_NAV_IDR = 50_000_000.0


class E2EPaperOrchestrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class E2EPaperPaths:
    root: Path
    t0_path: Path
    meta_path: Path
    prepared_dir: Path
    execution_dir: Path

    @classmethod
    def from_root(cls, root: str | Path) -> "E2EPaperPaths":
        base = Path(root).expanduser().resolve()
        return cls(
            root=base,
            t0_path=base / "t0" / "T0.json",
            meta_path=base / "state" / "decisions",
            prepared_dir=base / "prepared",
            execution_dir=base / "executions",
        )


@dataclass(frozen=True)
class PreparedExecutionResult:
    path: Path
    file_sha256: str
    decision_session_date: str
    execution_session_date: str
    status: str


@dataclass(frozen=True)
class CompletedExecutionResult:
    path: Path
    file_sha256: str
    runtime_snapshot_path: Path
    runtime_snapshot_sha256: str
    execution_session_date: str
    status: str


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _canonical_hash(value: object) -> str:
    return _sha256_bytes(_canonical_bytes(value))


def _pretty_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _atomic_write(path: Path, value: Mapping[str, Any]) -> tuple[Path, str]:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = _pretty_json_bytes(value)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".partial", dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            if path.read_bytes() != raw:
                raise E2EPaperOrchestrationError(f"E2E_IMMUTABLE_ARTIFACT_CONFLICT:{path}")
            temp.unlink(missing_ok=True)
        else:
            os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)
    if path.read_bytes() != raw:
        raise E2EPaperOrchestrationError(f"E2E_ARTIFACT_WRITE_MISMATCH:{path}")
    return path, _sha256_bytes(raw)


def _read_verified_json(path: Path, schema: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise E2EPaperOrchestrationError(f"E2E_JSON_INVALID:{path}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != schema:
        raise E2EPaperOrchestrationError(f"E2E_SCHEMA_INVALID:{path}")
    return payload


def _date(value: object, code: str = "E2E_DATE_INVALID") -> str:
    text = str(value or "")[:10]
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise E2EPaperOrchestrationError(code) from exc
    if parsed.isoformat() != text:
        raise E2EPaperOrchestrationError(code)
    return text


def _path_sha(path: str | Path, code: str) -> dict[str, str]:
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise E2EPaperOrchestrationError(f"{code}:{resolved}")
    return {"path": str(resolved), "sha256": _sha256_file(resolved)}


def _verify_declared_file_ref(
    payload: Mapping[str, Any],
    key: str,
    actual_path: str | Path,
    code: str,
) -> None:
    declared = payload.get(key)
    if not isinstance(declared, Mapping):
        raise E2EPaperOrchestrationError(f"{code}_REFERENCE_MISSING")
    actual = _path_sha(actual_path, code)
    if str(declared.get("path") or "") != actual["path"]:
        raise E2EPaperOrchestrationError(f"{code}_PATH_MISMATCH")
    if str(declared.get("sha256") or "") != actual["sha256"]:
        raise E2EPaperOrchestrationError(f"{code}_SHA_MISMATCH")


def _score_ref(verified: VerifiedScoreSession) -> dict[str, str]:
    if not isinstance(verified, VerifiedScoreSession):
        raise E2EPaperOrchestrationError("E2E_VERIFIED_SCORE_REQUIRED")
    return {
        "manifest_path": str(verified.manifest_path.resolve()),
        "manifest_sha256": verified.manifest_sha256,
        "artifact_path": str(verified.artifact_path.resolve()),
        "artifact_sha256": verified.artifact_sha256,
        "session_date": verified.session_date,
        "model_id": verified.model_id,
        "model_fingerprint": verified.model_fingerprint,
    }


def _state_payload(state: dividend.DividendAwarePaperState) -> dict[str, Any]:
    base = state.base_state
    return {
        "as_of_session_date": base.as_of_session_date,
        "cash_idr": base.cash_idr,
        "positions": [asdict(x) for x in base.positions],
        "pending_buys": [asdict(x) for x in base.pending_buys],
        "pending_sells": [asdict(x) for x in base.pending_sells],
        "reconciliation_required": bool(base.reconciliation_required),
        "source": base.source,
        "dividend_ledger_sha256": dividend.dividend_ledger_hash(state.dividend_ledger),
        "dividend_aware_state_sha256": dividend.dividend_aware_state_hash(state),
    }


def _intent_payload(row: object) -> dict[str, Any]:
    return {
        "side": row.side,
        "ticker": row.ticker,
        "rank_consensus": row.rank_consensus,
        "reason": row.reason,
        "replacement_peer": row.replacement_peer,
    }


def _decision_payload(plan: DecisionV2Plan) -> dict[str, Any]:
    return {
        "decision_session_date": plan.decision_session_date,
        "current_shadow_positions": list(plan.current_shadow_positions),
        "target_positions": list(plan.target_positions),
        "buy_intents": [_intent_payload(x) for x in plan.buy_intents],
        "sell_intents": [_intent_payload(x) for x in plan.sell_intents],
        "hold_tickers": list(plan.hold_tickers),
        "incumbent_observations": [asdict(x) for x in plan.incumbent_observations],
        "challenger_observations": [asdict(x) for x in plan.challenger_observations],
        "unfilled_slots": plan.unfilled_slots,
        "capacity_state": plan.capacity_state,
        "rule_id": plan.rule_id,
        "bootstrap": plan.bootstrap,
    }


def _sizing_payload(plan: ExecutionOrderPlan) -> dict[str, Any]:
    sizing = plan.sizing_plan
    return {
        "decision_session_date": sizing.decision_session_date,
        "nav_idr": sizing.nav_idr,
        "available_cash_idr": sizing.available_cash_idr,
        "target_weight_per_name": sizing.target_weight_per_name,
        "max_entry_weight_per_name": sizing.max_entry_weight_per_name,
        "entries": [asdict(x) for x in sizing.entries],
        "total_sized_notional": sizing.total_sized_notional,
        "residual_cash_after_sizing_reference": sizing.residual_cash_after_sizing_reference,
        "rule_id": sizing.rule_id,
    }


def _execution_plan_payload(plan: ExecutionOrderPlan) -> dict[str, Any]:
    return {
        "decision_session_date": plan.decision_session_date,
        "execution_session_date": plan.execution_session_date,
        "state_hash": plan.state_hash,
        "eod_nav_idr": plan.eod_nav_idr,
        "projected_cash_for_sizing_idr": plan.projected_cash_for_sizing_idr,
        "sizing_plan": _sizing_payload(plan),
        "sells": [asdict(x) for x in plan.sells],
        "effective_buy_intents": [_intent_payload(x) for x in plan.effective_buy_intents],
        "target_positions": list(plan.target_positions),
        "regular_market_values_t": dict(sorted(plan.regular_market_values_t.items())),
        "eod_ohlcv_sha256": plan.eod_ohlcv_sha256,
        "eod_model_input_sha256": plan.eod_model_input_sha256,
        "official_calendar_sha256": plan.official_calendar_sha256,
        "rule_id": plan.rule_id,
    }


def _reconciliation_payload(value: VerifiedDividendCAReconciliation) -> dict[str, Any]:
    if not isinstance(value, VerifiedDividendCAReconciliation):
        raise E2EPaperOrchestrationError("E2E_VERIFIED_CA_RECONCILIATION_REQUIRED")
    return {
        "from_session_date": value.from_session_date,
        "through_session_date": value.through_session_date,
        "covered_tickers": sorted(value.covered_tickers),
        "original_status": value.original_status,
        "relevant_tickers": sorted(value.relevant_tickers),
        "certified_events": [asdict(x) for x in value.certified_events],
        "attestation_path": str(value.attestation_path.resolve()),
        "attestation_sha256": value.attestation_sha256,
        "source_path": str(value.source_path.resolve()),
        "source_sha256": value.source_sha256,
    }


def _open_input_values_sha256(value: VerifiedOpenExecutionInputs) -> str:
    return _canonical_hash(
        {
            "session_date": value.session_date,
            "raw_open_prices": {
                str(key): float(number)
                for key, number in sorted(value.raw_open_prices.items())
            },
            "available_tickers": sorted(value.available_tickers),
        }
    )


def _open_parent_payload(value: VerifiedOpenExecutionInputs) -> dict[str, Any]:
    return {
        "open_manifest_path": (
            str(value.manifest_path.resolve())
            if value.manifest_path is not None
            else None
        ),
        "open_manifest_sha256": value.manifest_sha256,
        "open_normalized_path": str(value.ohlcv_artifact_path.resolve()),
        "open_normalized_sha256": value.ohlcv_artifact_sha256,
        "open_raw_source_path": (
            str(value.raw_source_path.resolve())
            if value.raw_source_path is not None
            else None
        ),
        "open_raw_source_sha256": value.raw_source_sha256,
        "open_input_values_sha256": _open_input_values_sha256(value),
        "transport": value.transport,
    }


def _verify_reconciliation(
    value: VerifiedDividendCAReconciliation,
    *,
    decision_date: str,
    execution_date: str,
    required_tickers: Sequence[str],
) -> None:
    if not isinstance(value, VerifiedDividendCAReconciliation):
        raise E2EPaperOrchestrationError("E2E_VERIFIED_CA_RECONCILIATION_REQUIRED")
    if value._verification_token is not _DIVIDEND_RECONCILIATION_TOKEN:
        raise E2EPaperOrchestrationError(
            "E2E_VERIFIED_CA_RECONCILIATION_TOKEN_INVALID"
        )
    if value.from_session_date != decision_date or value.through_session_date != execution_date:
        raise E2EPaperOrchestrationError("E2E_CA_RECONCILIATION_SCOPE_MISMATCH")
    if not set(required_tickers).issubset(value.covered_tickers):
        raise E2EPaperOrchestrationError("E2E_CA_RECONCILIATION_COVERAGE_MISMATCH")
    if value.original_status != "NO_RELEVANT_EVENTS" and not value.certified_events:
        raise E2EPaperOrchestrationError("E2E_CA_UNRESOLVED_LIVE_BLOCKER")


def _verify_persisted_reconciliation_payload(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise E2EPaperOrchestrationError("E2E_PREPARED_CA_PAYLOAD_MISSING")
    payload = dict(value)
    for path_key, sha_key, code in (
        ("attestation_path", "attestation_sha256", "E2E_CA_ATTESTATION"),
        ("source_path", "source_sha256", "E2E_CA_SOURCE"),
    ):
        path = Path(str(payload.get(path_key) or "")).expanduser().resolve()
        declared_sha = str(payload.get(sha_key) or "")
        if not path.is_file() or _sha256_file(path) != declared_sha:
            raise E2EPaperOrchestrationError(f"{code}_PARENT_HASH_MISMATCH")
        payload[path_key] = str(path)
    return payload


def _verify_prepared_ca_parent(
    prepared_payload: Mapping[str, Any],
    current: VerifiedDividendCAReconciliation,
    *,
    dividend_evidence: Sequence[VerifiedCashDividendEvidence],
) -> dict[str, Any]:
    parent = _verify_persisted_reconciliation_payload(
        prepared_payload.get("ca_reconciliation")
    )
    current_payload = _reconciliation_payload(current)
    _verify_persisted_reconciliation_payload(current_payload)
    if parent == current_payload:
        return current_payload

    if (
        parent.get("from_session_date") != current_payload.get("from_session_date")
        or parent.get("through_session_date") != current_payload.get("through_session_date")
        or not set(parent.get("covered_tickers", []))
        <= set(current_payload.get("covered_tickers", []))
    ):
        raise E2EPaperOrchestrationError("E2E_CA_PREPARED_PARENT_SCOPE_CHANGED")

    parent_events = {
        str(row.get("event_id")): row
        for row in parent.get("certified_events", [])
        if isinstance(row, Mapping)
    }
    current_events = {
        str(row.get("event_id")): row
        for row in current_payload.get("certified_events", [])
        if isinstance(row, Mapping)
    }
    for event_id, row in parent_events.items():
        if current_events.get(event_id) != row:
            raise E2EPaperOrchestrationError(
                "E2E_CA_PREPARED_EVENT_PARENT_CHANGED:" + event_id
            )
    new_event_ids = set(current_events) - set(parent_events)
    if not new_event_ids:
        raise E2EPaperOrchestrationError(
            "E2E_CA_PREPARED_PARENT_CHANGED_WITHOUT_EXTENSION"
        )
    evidence_ids = {
        row.event.event_id
        for row in dividend_evidence
    }
    if not new_event_ids.issubset(evidence_ids):
        raise E2EPaperOrchestrationError(
            "E2E_CA_PREOPEN_NEW_EVENT_EVIDENCE_MISSING"
        )
    return current_payload


def _verify_open_contract(value: VerifiedOpenExecutionInputs) -> None:
    if not isinstance(value, VerifiedOpenExecutionInputs):
        raise E2EPaperOrchestrationError("E2E_VERIFIED_OPEN_REQUIRED")
    expected = {
        "authority": OFFICIAL_OPEN_AUTHORITY,
        "upstream_path": OFFICIAL_OPEN_UPSTREAM_PATH,
        "field_semantics": OFFICIAL_OPEN_FIELD_SEMANTICS,
        "fallback_policy": OFFICIAL_OPEN_FALLBACK_POLICY,
        "transport_policy": OFFICIAL_OPEN_TRANSPORT_POLICY,
    }
    for field_name, expected_value in expected.items():
        if getattr(value, field_name, None) != expected_value:
            raise E2EPaperOrchestrationError(
                f"E2E_OPEN_PROVENANCE_INVALID:{field_name}"
            )
    if value.transport not in OFFICIAL_OPEN_ALLOWED_TRANSPORTS:
        raise E2EPaperOrchestrationError("E2E_OPEN_TRANSPORT_UNCERTIFIED")


def _verify_dividend_evidence_bindings(
    evidence: Sequence[VerifiedCashDividendEvidence],
    reconciliation: VerifiedDividendCAReconciliation,
) -> None:
    expected_events = {
        event.event_id: event
        for event in reconciliation.certified_events
    }
    seen: set[str] = set()
    for row in evidence:
        if not isinstance(row, VerifiedCashDividendEvidence):
            raise E2EPaperOrchestrationError(
                "E2E_DIVIDEND_EVIDENCE_OBJECT_INVALID"
            )
        if row._verification_token is not _VERIFIED_DIVIDEND_EVIDENCE_TOKEN:
            raise E2EPaperOrchestrationError(
                "E2E_DIVIDEND_EVIDENCE_TOKEN_INVALID"
            )
        review_path = row.review_path.expanduser().resolve()
        if not review_path.is_file() or _sha256_file(review_path) != row.review_sha256:
            raise E2EPaperOrchestrationError(
                "E2E_DIVIDEND_EVIDENCE_REVIEW_SHA_MISMATCH"
            )
        expected = expected_events.get(row.event.event_id)
        if expected is None or expected != row.event:
            raise E2EPaperOrchestrationError(
                "E2E_DIVIDEND_EVIDENCE_EVENT_BINDING_MISMATCH"
                + ":"
                + row.event.event_id
            )
        try:
            reverified = dividend_runtime.gate.verify_cash_dividend_evidence_for_execution(
                review_path=review_path,
                attachment_dir=review_path.parent,
            )
        except Exception as exc:
            raise E2EPaperOrchestrationError(
                "E2E_DIVIDEND_EVIDENCE_REVERIFY_FAILED"
            ) from exc
        if (
            reverified.event != row.event
            or reverified.review_sha256 != row.review_sha256
            or reverified.announcement_id != row.announcement_id
            or reverified.announcement_number != row.announcement_number
        ):
            raise E2EPaperOrchestrationError(
                "E2E_DIVIDEND_EVIDENCE_REVERIFY_MISMATCH"
                + ":"
                + row.event.event_id
            )
        if row.event.event_id in seen:
            raise E2EPaperOrchestrationError(
                "E2E_DIVIDEND_EVIDENCE_DUPLICATE"
                + ":"
                + row.event.event_id
            )
        seen.add(row.event.event_id)


def _load_latest_state(paths: E2EPaperPaths) -> dividend.DividendAwarePaperState:
    try:
        snapshot = dividend_runtime.load_latest_runtime_snapshot(paths.root)
    except Exception as exc:
        raise E2EPaperOrchestrationError("E2E_RUNTIME_STATE_MISSING") from exc
    return snapshot.state


def _load_meta(paths: E2EPaperPaths) -> dict[str, Any] | None:
    if not paths.meta_path.is_dir():
        return None
    candidates = sorted(paths.meta_path.glob("*.json"))
    if not candidates:
        return None
    payload = _read_verified_json(candidates[-1], META_SCHEMA)
    declared = str(payload.get("payload_sha256") or "")
    body = dict(payload)
    body.pop("payload_sha256", None)
    if _canonical_hash(body) != declared:
        raise E2EPaperOrchestrationError("E2E_META_HASH_MISMATCH")
    return payload


def _write_meta(paths: E2EPaperPaths, payload: Mapping[str, Any]) -> tuple[Path, str]:
    body = {"schema_version": META_SCHEMA, **dict(payload)}
    body["payload_sha256"] = _canonical_hash(body)
    session = _date(body.get("last_score_session_date"), "E2E_META_SESSION_INVALID")
    return _atomic_write(paths.meta_path / f"{session}.json", body)


def bootstrap_t0(
    runtime_root: str | Path,
    *,
    session_date: str,
    initial_nav_idr: float = INITIAL_NAV_IDR,
) -> Path:
    """Create the explicit zero-holding T0 state; identical reruns are safe."""
    paths = E2EPaperPaths.from_root(runtime_root)
    session = _date(session_date)
    if float(initial_nav_idr) != INITIAL_NAV_IDR:
        raise E2EPaperOrchestrationError("E2E_T0_INITIAL_NAV_CHANGED")
    state = dividend.DividendAwarePaperState(
        base_state=PaperPortfolioState(
            as_of_session_date=session,
            cash_idr=INITIAL_NAV_IDR,
            positions=(),
            pending_buys=(),
            pending_sells=(),
        ),
        dividend_ledger=dividend.DividendLedger(),
    )
    snapshot = dividend_runtime.write_runtime_snapshot(paths.root, state, ())
    body = {
        "schema_version": T0_SCHEMA,
        "session_date": session,
        "initial_nav_idr": INITIAL_NAV_IDR,
        "historical_dividend_credit": False,
        "zero_holdings": True,
        "zero_pending_buys": True,
        "zero_pending_sells": True,
        "zero_receivables": True,
        "runtime_snapshot_path": str(snapshot.path.resolve()),
        "runtime_snapshot_sha256": snapshot.file_sha256,
        "state_sha256": dividend.dividend_aware_state_hash(state),
    }
    body["payload_sha256"] = _canonical_hash(body)
    _atomic_write(paths.t0_path, body)
    return paths.t0_path


def _resolve_scores(
    current: VerifiedScoreSession,
    previous: VerifiedScoreSession | None,
    *,
    state: dividend.DividendAwarePaperState,
    meta: dict[str, Any] | None,
    current_date: str,
) -> tuple[DecisionV2Plan, bool]:
    if current.session_date != current_date:
        raise E2EPaperOrchestrationError("E2E_SCORE_SESSION_MISMATCH")
    if meta is None:
        if previous is not None:
            raise E2EPaperOrchestrationError("E2E_BOOTSTRAP_PREVIOUS_SCORE_FORBIDDEN")
        shadow = DecisionV2ShadowState.empty()
        bootstrap = True
    else:
        if previous is None:
            raise E2EPaperOrchestrationError("E2E_PREVIOUS_SCORE_REQUIRED")
        expected_previous = str(meta.get("last_score_manifest_path") or "")
        if expected_previous != str(previous.manifest_path.resolve()):
            raise E2EPaperOrchestrationError("E2E_PREVIOUS_SCORE_PARENT_MISMATCH")
        expected_previous_sha = str(meta.get("last_score_manifest_sha256") or "")
        if expected_previous_sha != previous.manifest_sha256:
            raise E2EPaperOrchestrationError("E2E_PREVIOUS_SCORE_SHA_MISMATCH")
        shadow = dividend_runtime.reconstruct_decision_shadow_state(state)
        # The paper state is already post-execution for the decision session,
        # while Decision V2's lineage date must remain the previous score date.
        shadow = replace(shadow, as_of_session_date=previous.session_date)
        bootstrap = False
    plan = plan_v4_x1_decision_v2_minimal(current, previous, shadow)
    if plan.bootstrap != bootstrap:
        raise E2EPaperOrchestrationError("E2E_BOOTSTRAP_STATE_MISMATCH")
    return plan, bootstrap


def prepare_post_eod(
    runtime_root: str | Path,
    *,
    current_score: VerifiedScoreSession,
    previous_score: VerifiedScoreSession | None,
    eod_inputs: VerifiedEODExecutionInputs,
    ca_reconciliation: VerifiedDividendCAReconciliation,
) -> PreparedExecutionResult:
    """Build one immutable PREPARED_EXECUTION artifact without accessing Open."""
    paths = E2EPaperPaths.from_root(runtime_root)
    session = _date(current_score.session_date)
    if eod_inputs.session_date != session:
        raise E2EPaperOrchestrationError("E2E_EOD_SESSION_MISMATCH")
    state = _load_latest_state(paths)
    if state.base_state.as_of_session_date != session:
        raise E2EPaperOrchestrationError("E2E_PAPER_STATE_SESSION_MISMATCH")
    meta = _load_meta(paths)
    plan, bootstrap = _resolve_scores(
        current_score, previous_score, state=state, meta=meta, current_date=session
    )
    required = tuple(sorted(set(state.base_state.positions[i].ticker for i in range(len(state.base_state.positions))) | set(plan.target_positions) | {x.ticker for x in state.base_state.pending_buys} | {x.ticker for x in state.base_state.pending_sells}))
    if not set(required).issubset(eod_inputs.raw_close_prices):
        raise E2EPaperOrchestrationError("E2E_EOD_REQUIRED_TICKER_MISSING")
    _verify_reconciliation(
        ca_reconciliation,
        decision_date=session,
        execution_date=eod_inputs.next_official_session_date,
        required_tickers=required,
    )
    _verify_persisted_reconciliation_payload(
        _reconciliation_payload(ca_reconciliation)
    )
    snapshot = dividend_runtime.load_latest_runtime_snapshot(paths.root)
    decision_shadow = (
        DecisionV2ShadowState.empty()
        if bootstrap
        else replace(
            dividend_runtime.reconstruct_decision_shadow_state(state),
            as_of_session_date=previous_score.session_date,
        )
    )
    verified_sizing = verify_decision_v2_plan_for_sizing(
        plan, current_score, previous_score, decision_shadow
    )
    base_plan = prepare_execution_v1_from_decision_v2(verified_sizing, state.base_state, eod_inputs=eod_inputs)
    order_payload = _execution_plan_payload(base_plan)
    payload = {
        "schema_version": PREPARED_SCHEMA,
        "status": "PREPARED_EXECUTION",
        "decision_session_date": session,
        "execution_session_date": eod_inputs.next_official_session_date,
        "bootstrap": bootstrap,
        "required_tickers": list(required),
        "state": {
            "snapshot_path": str(snapshot.path.resolve()),
            "snapshot_sha256": snapshot.file_sha256,
            "state_sha256": dividend.dividend_aware_state_hash(state),
        },
        "current_score": _score_ref(current_score),
        "previous_score": None if previous_score is None else _score_ref(previous_score),
        "decision_plan": _decision_payload(plan),
        "decision_plan_sha256": _canonical_hash(_decision_payload(plan)),
        "execution_plan": order_payload,
        "execution_plan_sha256": _canonical_hash(order_payload),
        "eod_inputs": {
            "ohlcv": _path_sha(eod_inputs.ohlcv_artifact_path, "E2E_EOD_OHLCV_MISSING"),
            "model_input": _path_sha(eod_inputs.model_input_path, "E2E_EOD_MODEL_INPUT_MISSING"),
            "calendar": _path_sha(eod_inputs.official_calendar_path, "E2E_CALENDAR_MISSING"),
        },
        "ca_reconciliation": _reconciliation_payload(ca_reconciliation),
        "outcome_access": False,
    }
    payload["payload_sha256"] = _canonical_hash(payload)
    target = paths.prepared_dir / f"{session}.json"
    path, sha = _atomic_write(target, payload)
    return PreparedExecutionResult(path, sha, session, eod_inputs.next_official_session_date, "PREPARED_EXECUTION")


def _recover_staged_execution(
    paths: E2EPaperPaths,
    *,
    prepared: Path,
    execution_date: str,
    expected_ca_reconciliation: Mapping[str, Any],
    expected_open_parent: Mapping[str, Any],
) -> CompletedExecutionResult | None:
    stage_path = paths.execution_dir / ".transactions" / f"{execution_date}.json"
    if not stage_path.is_file():
        return None
    stage = _read_verified_json(stage_path, EXECUTION_TXN_SCHEMA)
    stage_body = dict(stage)
    declared_stage_sha = str(stage_body.pop("payload_sha256") or "")
    if _canonical_hash(stage_body) != declared_stage_sha:
        raise E2EPaperOrchestrationError("E2E_TRANSACTION_STAGE_HASH_MISMATCH")
    if _date(stage.get("execution_session_date")) != execution_date:
        raise E2EPaperOrchestrationError("E2E_TRANSACTION_SESSION_MISMATCH")
    prepared_sha = _sha256_file(prepared)
    if (
        str(stage.get("prepared_path") or "") != str(prepared)
        or str(stage.get("prepared_sha256") or "") != prepared_sha
    ):
        raise E2EPaperOrchestrationError("E2E_TRANSACTION_PREPARED_PARENT_MISMATCH")

    snapshot_payload = stage.get("snapshot_payload")
    if not isinstance(snapshot_payload, dict):
        raise E2EPaperOrchestrationError("E2E_TRANSACTION_SNAPSHOT_PAYLOAD_MISSING")
    declared_snapshot_payload_sha = str(
        snapshot_payload.get("snapshot_payload_sha256") or ""
    )
    snapshot_hash_input = dict(snapshot_payload)
    snapshot_hash_input.pop("snapshot_payload_sha256", None)
    if _canonical_hash(snapshot_hash_input) != declared_snapshot_payload_sha:
        raise E2EPaperOrchestrationError("E2E_TRANSACTION_SNAPSHOT_PAYLOAD_HASH_MISMATCH")
    snapshot_path = Path(str(stage.get("snapshot_path") or "")).expanduser().resolve()
    snapshot_bytes = _pretty_json_bytes(snapshot_payload)
    snapshot_sha = _sha256_bytes(snapshot_bytes)
    if snapshot_sha != str(stage.get("snapshot_file_sha256") or ""):
        raise E2EPaperOrchestrationError("E2E_TRANSACTION_SNAPSHOT_SHA_MISMATCH")
    if snapshot_path.exists() and snapshot_path.read_bytes() != snapshot_bytes:
        raise E2EPaperOrchestrationError("E2E_TRANSACTION_SNAPSHOT_CONFLICT")
    if not snapshot_path.exists():
        _atomic_write(snapshot_path, snapshot_payload)
    snapshot = dividend_runtime.load_runtime_snapshot(snapshot_path)
    if snapshot.file_sha256 != snapshot_sha:
        raise E2EPaperOrchestrationError("E2E_TRANSACTION_SNAPSHOT_VERIFY_MISMATCH")

    execution_body = stage.get("execution_body")
    if not isinstance(execution_body, dict):
        raise E2EPaperOrchestrationError("E2E_TRANSACTION_EXECUTION_PAYLOAD_MISSING")
    if execution_body.get("ca_reconciliation") != expected_ca_reconciliation:
        raise E2EPaperOrchestrationError("E2E_TRANSACTION_CA_PARENT_MISMATCH")
    for key, expected in expected_open_parent.items():
        if execution_body.get(key) != expected:
            raise E2EPaperOrchestrationError(
                "E2E_TRANSACTION_OPEN_PARENT_MISMATCH:" + key
            )
    execution_hash_input = dict(execution_body)
    declared_execution_sha = str(execution_hash_input.pop("payload_sha256") or "")
    if _canonical_hash(execution_hash_input) != declared_execution_sha:
        raise E2EPaperOrchestrationError("E2E_TRANSACTION_EXECUTION_PAYLOAD_HASH_MISMATCH")
    target = paths.execution_dir / f"{execution_date}.json"
    if (
        str(execution_body.get("prepared_path") or "") != str(prepared)
        or str(execution_body.get("prepared_sha256") or "") != prepared_sha
        or str(execution_body.get("runtime_snapshot_path") or "")
        != str(snapshot.path.resolve())
        or str(execution_body.get("runtime_snapshot_sha256") or "")
        != snapshot.file_sha256
    ):
        raise E2EPaperOrchestrationError("E2E_TRANSACTION_EXECUTION_PARENT_MISMATCH")
    path, sha = _atomic_write(target, execution_body)
    return CompletedExecutionResult(
        path,
        sha,
        snapshot.path,
        snapshot.file_sha256,
        execution_date,
        "RECOVERED_STAGED_EXECUTION",
    )


def execute_preopen(
    runtime_root: str | Path,
    *,
    prepared_path: str | Path,
    current_score: VerifiedScoreSession,
    previous_score: VerifiedScoreSession | None,
    eod_inputs: VerifiedEODExecutionInputs,
    open_inputs: VerifiedOpenExecutionInputs,
    ca_reconciliation: VerifiedDividendCAReconciliation,
    dividend_evidence: Sequence[VerifiedCashDividendEvidence] = (),
) -> CompletedExecutionResult:
    """Verify one prepared parent and execute exactly once at official Open."""
    paths = E2EPaperPaths.from_root(runtime_root)
    prepared = Path(prepared_path).expanduser().resolve()
    payload = _read_verified_json(prepared, PREPARED_SCHEMA)
    body = dict(payload)
    declared = str(body.pop("payload_sha256", ""))
    if _canonical_hash(body) != declared:
        raise E2EPaperOrchestrationError("E2E_PREPARED_PAYLOAD_SHA_MISMATCH")
    if payload.get("status") != "PREPARED_EXECUTION":
        raise E2EPaperOrchestrationError("E2E_PREPARED_STATUS_INVALID")
    decision_date = _date(payload.get("decision_session_date"))
    execution_date = _date(payload.get("execution_session_date"))
    if current_score.session_date != decision_date or eod_inputs.session_date != decision_date or open_inputs.session_date != execution_date:
        raise E2EPaperOrchestrationError("E2E_PREOPEN_SESSION_MISMATCH")
    if eod_inputs.next_official_session_date != execution_date:
        raise E2EPaperOrchestrationError("E2E_NEXT_SESSION_MISMATCH")
    if _score_ref(current_score) != payload.get("current_score"):
        raise E2EPaperOrchestrationError("E2E_CURRENT_SCORE_PARENT_MISMATCH")
    expected_previous = payload.get("previous_score")
    if (None if previous_score is None else _score_ref(previous_score)) != expected_previous:
        raise E2EPaperOrchestrationError("E2E_PREVIOUS_SCORE_PARENT_MISMATCH")
    eod_ref = payload.get("eod_inputs")
    if not isinstance(eod_ref, Mapping):
        raise E2EPaperOrchestrationError("E2E_PREPARED_EOD_REFERENCE_MISSING")
    _verify_declared_file_ref(
        eod_ref,
        "ohlcv",
        eod_inputs.ohlcv_artifact_path,
        "E2E_EOD_OHLCV",
    )
    _verify_declared_file_ref(
        eod_ref,
        "model_input",
        eod_inputs.model_input_path,
        "E2E_EOD_MODEL_INPUT",
    )
    _verify_declared_file_ref(
        eod_ref,
        "calendar",
        eod_inputs.official_calendar_path,
        "E2E_EOD_CALENDAR",
    )
    _verify_open_contract(open_inputs)
    current_ca_payload = _verify_prepared_ca_parent(
        payload,
        ca_reconciliation,
        dividend_evidence=dividend_evidence,
    )
    required = tuple(str(x) for x in payload.get("required_tickers", []))
    current_event_ids = {
        event.event_id for event in ca_reconciliation.certified_events
    }
    evidence_ids = {row.event.event_id for row in dividend_evidence}
    if evidence_ids != current_event_ids:
        raise E2EPaperOrchestrationError(
            "E2E_DIVIDEND_EVIDENCE_COVERAGE_MISMATCH"
        )
    _verify_dividend_evidence_bindings(
        dividend_evidence,
        ca_reconciliation,
    )
    _verify_reconciliation(
        ca_reconciliation,
        decision_date=decision_date,
        execution_date=execution_date,
        required_tickers=required,
    )
    target = paths.execution_dir / f"{execution_date}.json"
    if not target.exists():
        recovered = _recover_staged_execution(
            paths,
            prepared=prepared,
            execution_date=execution_date,
            expected_ca_reconciliation=current_ca_payload,
            expected_open_parent=_open_parent_payload(open_inputs),
        )
        if recovered is not None:
            _write_meta(paths, {
                "last_score_manifest_path": str(current_score.manifest_path.resolve()),
                "last_score_manifest_sha256": current_score.manifest_sha256,
                "last_score_session_date": decision_date,
                "last_execution_session_date": execution_date,
                "last_execution_path": str(recovered.path),
                "last_execution_sha256": recovered.file_sha256,
                "runtime_snapshot_path": str(recovered.runtime_snapshot_path),
                "runtime_snapshot_sha256": recovered.runtime_snapshot_sha256,
            })
            return recovered
    if target.exists():
        snapshot_path = (
            paths.root
            / dividend_runtime.RUNTIME_DIRNAME
            / dividend_runtime.SNAPSHOT_DIRNAME
            / f"{execution_date}.json"
        )
        existing_snapshot = dividend_runtime.load_runtime_snapshot(snapshot_path)
        if existing_snapshot.previous_snapshot_path is None:
            raise E2EPaperOrchestrationError("E2E_EXISTING_EXECUTION_PARENT_MISSING")
        existing_body = _read_verified_json(target, EXECUTION_SCHEMA)
        existing_hash = str(existing_body.pop("payload_sha256", ""))
        if not existing_hash or _canonical_hash(existing_body) != existing_hash:
            raise E2EPaperOrchestrationError("E2E_EXISTING_EXECUTION_HASH_MISMATCH")
        if (
            str(existing_body.get("prepared_path") or "") != str(prepared)
            or str(existing_body.get("prepared_sha256") or "")
            != _sha256_file(prepared)
        ):
            raise E2EPaperOrchestrationError("E2E_EXISTING_EXECUTION_PARENT_MISMATCH")
        if existing_body.get("ca_reconciliation") != current_ca_payload:
            raise E2EPaperOrchestrationError(
                "E2E_EXISTING_EXECUTION_CA_PARENT_MISMATCH"
            )
        expected_open = _open_parent_payload(open_inputs)
        for key, expected in expected_open.items():
            if existing_body.get(key) != expected:
                raise E2EPaperOrchestrationError(
                    "E2E_EXISTING_EXECUTION_OPEN_PARENT_MISMATCH:" + key
                )
        declared_state = payload.get("state")
        if (
            not isinstance(declared_state, Mapping)
            or str(existing_snapshot.previous_snapshot_path.resolve())
            != str(declared_state.get("snapshot_path") or "")
        ):
            raise E2EPaperOrchestrationError("E2E_EXISTING_EXECUTION_STATE_PARENT_MISMATCH")
        if (
            str(existing_body.get("runtime_snapshot_path") or "")
            != str(existing_snapshot.path.resolve())
            or str(existing_body.get("runtime_snapshot_sha256") or "")
            != existing_snapshot.file_sha256
        ):
            raise E2EPaperOrchestrationError(
                "E2E_EXISTING_EXECUTION_SNAPSHOT_PARENT_MISMATCH"
            )
        _write_meta(paths, {
            "last_score_manifest_path": str(current_score.manifest_path.resolve()),
            "last_score_manifest_sha256": current_score.manifest_sha256,
            "last_score_session_date": decision_date,
            "last_execution_session_date": execution_date,
            "last_execution_path": str(target),
            "last_execution_sha256": _sha256_file(target),
            "runtime_snapshot_path": str(existing_snapshot.path),
            "runtime_snapshot_sha256": existing_snapshot.file_sha256,
        })
        return CompletedExecutionResult(
            target,
            _sha256_file(target),
            existing_snapshot.path,
            existing_snapshot.file_sha256,
            execution_date,
            "ALREADY_COMPLETE",
        )
    state = _load_latest_state(paths)
    state_ref = payload.get("state")
    snapshot = dividend_runtime.load_latest_runtime_snapshot(paths.root)
    if not isinstance(state_ref, dict) or str(state_ref.get("snapshot_path")) != str(snapshot.path.resolve()) or str(state_ref.get("snapshot_sha256")) != snapshot.file_sha256 or str(state_ref.get("state_sha256")) != dividend.dividend_aware_state_hash(state):
        raise E2EPaperOrchestrationError("E2E_PREPARED_STATE_PARENT_MISMATCH")
    plan, _ = _resolve_scores(current_score, previous_score, state=state, meta=_load_meta(paths), current_date=decision_date)
    if _canonical_hash(_decision_payload(plan)) != payload.get("decision_plan_sha256"):
        raise E2EPaperOrchestrationError("E2E_DECISION_PARENT_MISMATCH")
    _verify_reconciliation(ca_reconciliation, decision_date=decision_date, execution_date=execution_date, required_tickers=required)
    shadow = (
        DecisionV2ShadowState.empty()
        if bool(payload.get("bootstrap"))
        else replace(
            dividend_runtime.reconstruct_decision_shadow_state(state),
            as_of_session_date=previous_score.session_date,
        )
    )
    verified_sizing = verify_decision_v2_plan_for_sizing(plan, current_score, previous_score, shadow)
    base_plan = prepare_execution_v1_from_decision_v2(verified_sizing, state.base_state, eod_inputs=eod_inputs)
    if _canonical_hash(_execution_plan_payload(base_plan)) != payload.get("execution_plan_sha256"):
        raise E2EPaperOrchestrationError("E2E_EXECUTION_PARENT_MISMATCH")
    evidence = tuple(dividend_evidence)
    for row in evidence:
        if row.event not in ca_reconciliation.certified_events:
            raise E2EPaperOrchestrationError("E2E_DIVIDEND_EVIDENCE_NOT_IN_RECONCILIATION")
    registry = snapshot.certified_dividend_registry
    for row in evidence:
        registry = dividend_runtime.register_verified_cash_dividend_evidence(
            registry,
            row,
            attachment_dir=row.review_path.parent,
        )
    result = execute_open_v1_1_reconciled(
        _dividend_order_plan(base_plan, state, eod_inputs.raw_close_prices),
        state,
        open_inputs=open_inputs,
        reconciliation=ca_reconciliation,
    )
    snapshot_payload = dividend_runtime._snapshot_payload(
        result.state_after,
        registry,
        snapshot,
    )
    snapshot_path = (
        paths.root
        / dividend_runtime.RUNTIME_DIRNAME
        / dividend_runtime.SNAPSHOT_DIRNAME
        / f"{execution_date}.json"
    ).resolve()
    snapshot_bytes = _pretty_json_bytes(snapshot_payload)
    snapshot_file_sha = _sha256_bytes(snapshot_bytes)
    prepared_sha = _sha256_file(prepared)
    execution_body = {
        "schema_version": EXECUTION_SCHEMA,
        "status": "EXECUTION_COMPLETE",
        "decision_session_date": decision_date,
        "execution_session_date": execution_date,
        "prepared_path": str(prepared),
        "prepared_sha256": prepared_sha,
        "open_manifest_path": str((open_inputs.manifest_path or Path("" )).resolve()) if open_inputs.manifest_path else None,
        "open_manifest_sha256": open_inputs.manifest_sha256,
        "open_normalized_path": str(open_inputs.ohlcv_artifact_path.resolve()),
        "open_normalized_sha256": open_inputs.ohlcv_artifact_sha256,
        "open_raw_source_path": (
            str(open_inputs.raw_source_path.resolve())
            if open_inputs.raw_source_path is not None
            else None
        ),
        "open_raw_source_sha256": open_inputs.raw_source_sha256,
        "open_input_values_sha256": _open_input_values_sha256(open_inputs),
        "authority": open_inputs.authority,
        "upstream_path": open_inputs.upstream_path,
        "field_semantics": open_inputs.field_semantics,
        "fallback_policy": open_inputs.fallback_policy,
        "transport_policy": open_inputs.transport_policy,
        "transport": open_inputs.transport,
        "ca_reconciliation": current_ca_payload,
        "runtime_snapshot_path": str(snapshot_path),
        "runtime_snapshot_sha256": snapshot_file_sha,
        "runtime_state_sha256": snapshot_payload["hashes"]["runtime_state_sha256"],
        "registry_sha256": dividend_runtime.certified_registry_hash(registry),
        "fills": [asdict(x) for x in result.base_result.fills],
        "gross_turnover_idr": result.base_result.gross_turnover_idr,
        "stamp_duty_idr": result.base_result.stamp_duty_idr,
        "pending_transition_count": result.base_result.pending_transition_count,
        "outcome_access": False,
    }
    execution_body["payload_sha256"] = _canonical_hash(execution_body)
    transaction = {
        "schema_version": EXECUTION_TXN_SCHEMA,
        "execution_session_date": execution_date,
        "prepared_path": str(prepared),
        "prepared_sha256": prepared_sha,
        "snapshot_path": str(snapshot_path),
        "snapshot_file_sha256": snapshot_file_sha,
        "snapshot_payload": snapshot_payload,
        "execution_body": execution_body,
        "outcome_access": False,
    }
    transaction["payload_sha256"] = _canonical_hash(transaction)
    _atomic_write(
        paths.execution_dir / ".transactions" / f"{execution_date}.json",
        transaction,
    )
    _atomic_write(snapshot_path, snapshot_payload)
    new_snapshot = dividend_runtime.load_runtime_snapshot(snapshot_path)
    if new_snapshot.file_sha256 != snapshot_file_sha:
        raise E2EPaperOrchestrationError("E2E_RUNTIME_SNAPSHOT_EXPECTED_SHA_MISMATCH")
    path, sha = _atomic_write(target, execution_body)
    _write_meta(paths, {
        "last_score_manifest_path": str(current_score.manifest_path.resolve()),
        "last_score_manifest_sha256": current_score.manifest_sha256,
        "last_score_session_date": decision_date,
        "last_execution_session_date": execution_date,
        "last_execution_path": str(path),
        "last_execution_sha256": sha,
        "runtime_snapshot_path": str(new_snapshot.path),
        "runtime_snapshot_sha256": new_snapshot.file_sha256,
    })
    return CompletedExecutionResult(path, sha, new_snapshot.path, new_snapshot.file_sha256, execution_date, "EXECUTION_COMPLETE")


def _dividend_order_plan(
    base_plan: ExecutionOrderPlan,
    state: dividend.DividendAwarePaperState,
    close_prices: Mapping[str, float],
) -> dividend.DividendAwareExecutionOrderPlan:
    nav = dividend.paper_total_return_nav_idr(state, close_prices)
    return dividend.DividendAwareExecutionOrderPlan(
        base_plan=base_plan,
        dividend_state_hash=dividend.dividend_aware_state_hash(state),
        dividend_ledger_hash=dividend.dividend_ledger_hash(state.dividend_ledger),
        total_return_nav_idr=float(nav),
    )


def load_score_manifest(path: str | Path) -> VerifiedScoreSession:
    return verify_v4_x1_score_artifact(path)


__all__ = [
    "E2EPaperOrchestrationError",
    "E2EPaperPaths",
    "PreparedExecutionResult",
    "CompletedExecutionResult",
    "bootstrap_t0",
    "prepare_post_eod",
    "execute_preopen",
    "load_score_manifest",
]
