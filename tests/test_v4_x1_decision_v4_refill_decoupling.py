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
from idx_trade.v4_x1_decision_v4_refill_decoupling import (
    V4_X1_DECISION_V4_REFILL_DECOUPLING_PROFILE_V1,
    plan_v4_x1_decision_v4_refill_decoupling,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = REPO_ROOT / "docs/specs/decision_v4_refill_decoupling_v1.json"


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


def test_runtime_profile_matches_frozen_v4_preregistration() -> None:
    payload = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    profile = V4_X1_DECISION_V4_REFILL_DECOUPLING_PROFILE_V1

    assert payload["status"] == "PREREGISTERED_NOT_IMPLEMENTED_NOT_REPLAYED"
    assert profile.rule_id == payload["rule_id"]
    assert profile.target_count_max == payload["target_count_max"]
    assert profile.strong_zone_max_rank == payload["strong_zone_max_rank"]
    assert profile.retention_zone_max_rank == payload["retention_zone_max_rank"]
    assert profile.mild_deterioration_max_rank == payload["mild_deterioration_max_rank"]
    assert profile.mild_deterioration_max_rank + 1 == payload["severe_deterioration_min_rank"]
    assert (
        profile.soft_replacement_min_rank_advantage
        == payload["soft_replacement_min_rank_advantage"]
    )
    assert payload["refill_decoupling"]["on_severe_exit_session_vacancy_priority"] == [
        "A_CORE"
    ]
    assert payload["refill_decoupling"]["on_nonsevere_session_vacancy_priority"] == [
        "A_CORE",
        "B_NEAR",
        "C_DISTANT",
    ]
    assert payload["refill_decoupling"]["soft_replacement_semantics_unchanged_from_v3"] is True
    assert payload["source"]["replay_authorized"] is False


def test_v4_x1_bootstrap_uses_v4_rule_id_and_exact_top10() -> None:
    order = [f"A{i:02d}" for i in range(1, 21)]
    plan = plan_v4_x1_decision_v4_refill_decoupling(
        _verified("2026-01-02", order),
        None,
        DecisionV3ShadowState.empty(),
    )
    assert plan.rule_id == "V4_X1_DECISION_V4_REFILL_DECOUPLING_V1"
    assert plan.target_positions == tuple(order[:10])
    assert plan.bootstrap is True


def test_v4_x1_rejects_unbound_nonbootstrap_shadow_state() -> None:
    previous_order = [f"A{i:02d}" for i in range(1, 21)]
    state = DecisionV3ShadowState(
        as_of_session_date="2026-01-02",
        positions=tuple(previous_order[:10]),
        rule_id=None,
    )
    with pytest.raises(DecisionV3Error, match="BOUND_SHADOW_STATE_REQUIRED"):
        plan_v4_x1_decision_v4_refill_decoupling(
            _verified("2026-01-03", previous_order),
            _verified("2026-01-02", previous_order),
            state,
        )


def test_v4_x1_accepts_correctly_bound_nonbootstrap_shadow_state() -> None:
    previous_order = [f"A{i:02d}" for i in range(1, 21)]
    state = DecisionV3ShadowState(
        as_of_session_date="2026-01-02",
        positions=tuple(previous_order[:10]),
        rule_id="V4_X1_DECISION_V4_REFILL_DECOUPLING_V1",
    )
    plan = plan_v4_x1_decision_v4_refill_decoupling(
        _verified("2026-01-03", previous_order),
        _verified("2026-01-02", previous_order),
        state,
    )
    assert plan.target_positions == tuple(previous_order[:10])
    assert plan.buy_intents == ()
    assert plan.sell_intents == ()
    assert plan.rule_id == "V4_X1_DECISION_V4_REFILL_DECOUPLING_V1"
