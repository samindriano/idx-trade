from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.decision_v3_graded_evidence import DecisionV3Error, DecisionV3ShadowState
from idx_trade.v4_x1_decision_v1_contract import (
    EXPECTED_ALPHA_MODEL_FINGERPRINT,
    EXPECTED_ALPHA_MODEL_ID,
    VerifiedScoreSession,
    _VERIFIED_TOKEN,
)
from idx_trade.v4_x1_decision_v3_graded_evidence import (
    V4_X1_DECISION_V3_GRADED_EVIDENCE_PROFILE_V2,
    plan_v4_x1_decision_v3_graded_evidence,
    rank_session_from_v4_x1_verified,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = (
    REPO_ROOT / "docs/specs/decision_v3_graded_evidence_v4_x1_profile_v2.json"
)


def _verified(day: str, order: list[str]) -> VerifiedScoreSession:
    frame = pd.DataFrame(
        {
            "ticker": order,
            "rank_consensus": list(range(1, len(order) + 1)),
            "alpha_h5": [object() for _ in order],
            "alpha_h10": [object() for _ in order],
            "irrelevant_extra": ["UNREAD"] * len(order),
        }
    )
    return VerifiedScoreSession(
        session_date=day,
        model_id=EXPECTED_ALPHA_MODEL_ID,
        model_fingerprint=EXPECTED_ALPHA_MODEL_FINGERPRINT,
        artifact_path=Path("unused.parquet"),
        artifact_sha256="unused",
        manifest_path=Path("unused.json"),
        manifest_sha256="unused",
        scores=frame,
        alpha_tie_rows=0,
        _verification_token=_VERIFIED_TOKEN,
    )


def test_runtime_profile_matches_frozen_machine_profile() -> None:
    payload = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    profile = V4_X1_DECISION_V3_GRADED_EVIDENCE_PROFILE_V2
    assert payload["status"] == "PREREGISTERED_V2_NOT_IMPLEMENTED_NOT_REPLAYED"
    assert profile.rule_id == payload["rule_id"]
    assert profile.target_count_max == payload["target_count_max"]
    assert profile.strong_zone_max_rank == payload["strong_zone_max_rank"]
    assert profile.retention_zone_max_rank == payload["retention_zone_max_rank"]
    assert profile.mild_deterioration_max_rank == payload["mild_deterioration_max_rank"]
    assert (
        profile.mild_deterioration_max_rank + 1
        == payload["severe_deterioration_min_rank"]
    )
    assert (
        profile.soft_replacement_min_rank_advantage
        == payload["soft_replacement_min_rank_advantage"]
    )
    assert payload["vacancy_priority"] == ["A_CORE", "B_NEAR", "C_DISTANT"]
    assert payload["tier_D_allowed_after_bootstrap"] is False
    assert payload["source"]["replay_authorized"] is False


def test_v4_adapter_projects_only_ticker_and_consensus_rank() -> None:
    order = [f"A{i:02d}" for i in range(1, 21)]
    verified = _verified("2026-01-02", order)
    session = rank_session_from_v4_x1_verified(verified)
    assert session.session_date == "2026-01-02"
    assert [row.ticker for row in session.rows] == order
    assert [row.rank for row in session.rows] == list(range(1, 21))


def test_v4_adapter_bootstrap_uses_frozen_profile() -> None:
    order = [f"A{i:02d}" for i in range(1, 21)]
    plan = plan_v4_x1_decision_v3_graded_evidence(
        _verified("2026-01-02", order),
        None,
        DecisionV3ShadowState.empty(),
    )
    assert plan.rule_id == "V4_X1_DECISION_V3_GRADED_EVIDENCE_V2"
    assert plan.target_positions == tuple(order[:10])
    assert plan.bootstrap is True


def test_v4_runtime_rejects_unbound_nonbootstrap_shadow_state() -> None:
    previous_order = [f"A{i:02d}" for i in range(1, 21)]
    current_order = previous_order.copy()
    state = DecisionV3ShadowState(
        as_of_session_date="2026-01-02",
        positions=tuple(previous_order[:10]),
        rule_id=None,
    )
    with pytest.raises(DecisionV3Error, match="BOUND_SHADOW_STATE_REQUIRED"):
        plan_v4_x1_decision_v3_graded_evidence(
            _verified("2026-01-03", current_order),
            _verified("2026-01-02", previous_order),
            state,
        )


def test_machine_profile_keeps_v2_acceptance_gates_unchanged() -> None:
    payload = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    gates = payload["gates"]
    assert gates["mean_replacements_max"] == 2.25
    assert gates["turnover_vs_naive_max"] == 0.50
    assert gates["share_ge3_replacements_max"] == 0.35
    assert gates["median_holding_min"] == 3
    assert gates["one_session_holding_share_max"] == 0.35
    assert gates["mean_full_target_top10_overlap_min"] == 6.0
    assert gates["mean_target_rank_max"] == 12.0
    assert gates["mean_target_size_min"] == 9.0
    assert gates["share_target_size_10_min"] == 0.70
    assert gates["share_target_size_le8_max"] == 0.10
    assert gates["target_rank_gt50_after_processing_max_count"] == 0
    assert gates["second_consecutive_rank21_50_retained_max_count"] == 0
    assert gates["post_bootstrap_previous_absent_entrant_max_count"] == 0
