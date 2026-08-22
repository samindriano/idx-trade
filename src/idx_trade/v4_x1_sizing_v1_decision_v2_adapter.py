from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .decision_v2_minimal import (
    DecisionV2Error,
    DecisionV2Plan,
    DecisionV2ShadowState,
)
from .v4_x1_decision_v1_contract import TradeIntent, VerifiedScoreSession
from .v4_x1_decision_v2_minimal import (
    V4_X1_DECISION_V2_MINIMAL_PROFILE_V1,
    plan_v4_x1_decision_v2_minimal,
)
from .v4_x1_sizing_v1 import SizingPlan, _size_entries_core

_VERIFIED_DECISION_V2_SIZING_PLAN_TOKEN = object()


@dataclass(frozen=True)
class VerifiedDecisionV2SizingPlan:
    plan: DecisionV2Plan
    current_score_session_date: str
    current_score_artifact_sha256: str
    previous_score_session_date: str | None
    previous_score_artifact_sha256: str | None
    _verification_token: object = field(repr=False, compare=False)


def verify_decision_v2_plan_for_sizing(
    decision_plan: DecisionV2Plan,
    current_verified: VerifiedScoreSession,
    previous_verified: VerifiedScoreSession | None,
    shadow_state: DecisionV2ShadowState,
) -> VerifiedDecisionV2SizingPlan:
    """Verify exact Decision V2 provenance before Sizing V1 consumes BUY intents."""

    if not isinstance(decision_plan, DecisionV2Plan):
        raise DecisionV2Error("SIZING_V1_DECISION_V2_PLAN_REQUIRED")

    expected = plan_v4_x1_decision_v2_minimal(
        current_verified=current_verified,
        previous_verified=previous_verified,
        shadow_state=shadow_state,
    )
    if decision_plan != expected:
        raise DecisionV2Error("SIZING_V1_DECISION_V2_PLAN_PROVENANCE_MISMATCH")

    expected_rule = V4_X1_DECISION_V2_MINIMAL_PROFILE_V1.rule_id
    if decision_plan.rule_id != expected_rule:
        raise DecisionV2Error("SIZING_V1_DECISION_V2_RULE_CHANGED")
    if current_verified.session_date != decision_plan.decision_session_date:
        raise DecisionV2Error("SIZING_V1_DECISION_V2_SCORE_SESSION_MISMATCH")

    previous_date = None if previous_verified is None else previous_verified.session_date
    previous_sha = None if previous_verified is None else previous_verified.artifact_sha256

    return VerifiedDecisionV2SizingPlan(
        plan=decision_plan,
        current_score_session_date=current_verified.session_date,
        current_score_artifact_sha256=current_verified.artifact_sha256,
        previous_score_session_date=previous_date,
        previous_score_artifact_sha256=previous_sha,
        _verification_token=_VERIFIED_DECISION_V2_SIZING_PLAN_TOKEN,
    )


def _require_verified_v2(
    verified_plan: VerifiedDecisionV2SizingPlan,
) -> DecisionV2Plan:
    if not isinstance(verified_plan, VerifiedDecisionV2SizingPlan):
        raise DecisionV2Error("SIZING_V1_VERIFIED_DECISION_V2_PLAN_REQUIRED")
    if (
        verified_plan._verification_token
        is not _VERIFIED_DECISION_V2_SIZING_PLAN_TOKEN
    ):
        raise DecisionV2Error("SIZING_V1_VERIFIED_DECISION_V2_PLAN_REQUIRED")

    plan = verified_plan.plan
    if not isinstance(plan, DecisionV2Plan):
        raise DecisionV2Error("SIZING_V1_VERIFIED_DECISION_V2_PLAN_REQUIRED")
    if plan.rule_id != V4_X1_DECISION_V2_MINIMAL_PROFILE_V1.rule_id:
        raise DecisionV2Error("SIZING_V1_DECISION_V2_RULE_CHANGED")
    if verified_plan.current_score_session_date != plan.decision_session_date:
        raise DecisionV2Error("SIZING_V1_DECISION_V2_SCORE_SESSION_MISMATCH")
    return plan


def size_decision_v2_entries(
    verified_plan: VerifiedDecisionV2SizingPlan,
    *,
    nav_idr: float,
    available_cash_idr: float,
    reference_prices: Mapping[str, float],
) -> SizingPlan:
    """Run unchanged Sizing V1 math on a provenance-verified Decision V2 plan."""

    plan = _require_verified_v2(verified_plan)
    adapted_buys = tuple(
        TradeIntent(
            side=intent.side,
            ticker=intent.ticker,
            rank_consensus=intent.rank_consensus,
            reason=intent.reason,
            replacement_peer=intent.replacement_peer,
        )
        for intent in plan.buy_intents
    )
    return _size_entries_core(
        decision_session_date=plan.decision_session_date,
        target_positions=plan.target_positions,
        intents=adapted_buys,
        nav_idr=nav_idr,
        available_cash_idr=available_cash_idr,
        reference_prices=reference_prices,
    )


__all__ = [
    "VerifiedDecisionV2SizingPlan",
    "verify_decision_v2_plan_for_sizing",
    "size_decision_v2_entries",
]
