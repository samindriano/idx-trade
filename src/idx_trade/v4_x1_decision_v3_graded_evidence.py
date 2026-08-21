from __future__ import annotations

import pandas as pd

from .decision_v3_graded_evidence import (
    DecisionV3Error,
    DecisionV3Plan,
    DecisionV3Profile,
    DecisionV3ShadowState,
    RankObservation,
    RankSession,
    plan_decision_v3_graded_evidence,
)
from .v4_x1_decision_v1_contract import (
    EXPECTED_ALPHA_MODEL_FINGERPRINT,
    EXPECTED_ALPHA_MODEL_ID,
    VerifiedScoreSession,
    _VERIFIED_TOKEN,
    _normalize_ticker,
)


V4_X1_DECISION_V3_GRADED_EVIDENCE_PROFILE_V2 = DecisionV3Profile(
    rule_id="V4_X1_DECISION_V3_GRADED_EVIDENCE_V2",
    target_count_max=10,
    strong_zone_max_rank=10,
    retention_zone_max_rank=20,
    mild_deterioration_max_rank=50,
    soft_replacement_min_rank_advantage=5,
    universe_absence_exit_immediate=True,
    allow_temporary_underfill=True,
    bootstrap_first_session_exact_top10=True,
)


def rank_session_from_v4_x1_verified(verified: VerifiedScoreSession) -> RankSession:
    if (
        not isinstance(verified, VerifiedScoreSession)
        or verified._verification_token is not _VERIFIED_TOKEN
    ):
        raise DecisionV3Error("DECISION_V3_V4_X1_VERIFIED_SCORE_SESSION_REQUIRED")
    if verified.model_id != EXPECTED_ALPHA_MODEL_ID:
        raise DecisionV3Error("DECISION_V3_V4_X1_MODEL_ID_CHANGED")
    if verified.model_fingerprint != EXPECTED_ALPHA_MODEL_FINGERPRINT:
        raise DecisionV3Error("DECISION_V3_V4_X1_MODEL_FINGERPRINT_CHANGED")
    if not isinstance(verified.scores, pd.DataFrame):
        raise DecisionV3Error("DECISION_V3_V4_X1_SCORE_FRAME_REQUIRED")

    required = {"ticker", "rank_consensus"}
    missing = required - set(verified.scores.columns)
    if missing:
        raise DecisionV3Error(
            f"DECISION_V3_V4_X1_SCORE_COLUMNS_MISSING:{sorted(missing)}"
        )

    # Scientific boundary: Decision V3 reads rank_consensus only. Head-specific
    # ranks/scores and every other score-frame column remain unused here.
    frame = verified.scores.loc[:, ["ticker", "rank_consensus"]].copy()
    frame["ticker"] = frame["ticker"].map(_normalize_ticker)
    if frame["ticker"].duplicated().any():
        raise DecisionV3Error("DECISION_V3_V4_X1_DUPLICATE_TICKER")

    numeric = pd.to_numeric(frame["rank_consensus"], errors="coerce")
    if numeric.isna().any():
        raise DecisionV3Error("DECISION_V3_V4_X1_RANK_NONNUMERIC")
    if not numeric.mod(1).eq(0).all():
        raise DecisionV3Error("DECISION_V3_V4_X1_RANK_NONINTEGER")
    frame["rank_consensus"] = numeric.astype(int)
    if frame["rank_consensus"].duplicated().any():
        raise DecisionV3Error("DECISION_V3_V4_X1_DUPLICATE_RANK")

    frame = frame.sort_values(["rank_consensus", "ticker"], kind="mergesort")
    rows = tuple(
        RankObservation(ticker=str(row.ticker), rank=int(row.rank_consensus))
        for row in frame.itertuples(index=False)
    )
    return RankSession(session_date=verified.session_date, rows=rows)


def plan_v4_x1_decision_v3_graded_evidence(
    current_verified: VerifiedScoreSession,
    previous_verified: VerifiedScoreSession | None,
    shadow_state: DecisionV3ShadowState,
) -> DecisionV3Plan:
    profile = V4_X1_DECISION_V3_GRADED_EVIDENCE_PROFILE_V2
    if not isinstance(shadow_state, DecisionV3ShadowState):
        raise DecisionV3Error("DECISION_V3_V4_X1_SHADOW_STATE_REQUIRED")
    if (
        shadow_state.as_of_session_date is not None
        and shadow_state.rule_id != profile.rule_id
    ):
        raise DecisionV3Error("DECISION_V3_V4_X1_BOUND_SHADOW_STATE_REQUIRED")

    current = rank_session_from_v4_x1_verified(current_verified)
    previous = (
        None
        if previous_verified is None
        else rank_session_from_v4_x1_verified(previous_verified)
    )
    return plan_decision_v3_graded_evidence(
        current_session=current,
        previous_session=previous,
        shadow_state=shadow_state,
        profile=profile,
    )
