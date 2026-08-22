from __future__ import annotations

from .decision_v3_graded_evidence import (
    DecisionV3Error,
    DecisionV3Plan,
    DecisionV3Profile,
    DecisionV3ShadowState,
)
from .decision_v4_refill_decoupling import plan_decision_v4_refill_decoupling
from .v4_x1_decision_v1_contract import VerifiedScoreSession
from .v4_x1_decision_v3_graded_evidence import rank_session_from_v4_x1_verified


V4_X1_DECISION_V4_REFILL_DECOUPLING_PROFILE_V1 = DecisionV3Profile(
    rule_id="V4_X1_DECISION_V4_REFILL_DECOUPLING_V1",
    target_count_max=10,
    strong_zone_max_rank=10,
    retention_zone_max_rank=20,
    mild_deterioration_max_rank=50,
    soft_replacement_min_rank_advantage=5,
    universe_absence_exit_immediate=True,
    allow_temporary_underfill=True,
    bootstrap_first_session_exact_top10=True,
)


def plan_v4_x1_decision_v4_refill_decoupling(
    current_verified: VerifiedScoreSession,
    previous_verified: VerifiedScoreSession | None,
    shadow_state: DecisionV3ShadowState,
) -> DecisionV3Plan:
    profile = V4_X1_DECISION_V4_REFILL_DECOUPLING_PROFILE_V1
    if not isinstance(shadow_state, DecisionV3ShadowState):
        raise DecisionV3Error("DECISION_V4_V4_X1_SHADOW_STATE_REQUIRED")
    if (
        shadow_state.as_of_session_date is not None
        and shadow_state.rule_id != profile.rule_id
    ):
        raise DecisionV3Error("DECISION_V4_V4_X1_BOUND_SHADOW_STATE_REQUIRED")

    current = rank_session_from_v4_x1_verified(current_verified)
    previous = (
        None
        if previous_verified is None
        else rank_session_from_v4_x1_verified(previous_verified)
    )
    return plan_decision_v4_refill_decoupling(
        current_session=current,
        previous_session=previous,
        shadow_state=shadow_state,
        profile=profile,
    )
