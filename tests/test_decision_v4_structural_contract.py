from __future__ import annotations

from pathlib import Path

from idx_trade.decision_v4_structural_contract import (
    EXPECTED_PREREG_CANONICAL_SHA256,
    EXPECTED_RULE_ID,
    REQUIRED_DIAGNOSTICS,
    verify_frozen_v4_preregistration,
)
from idx_trade.v4_x1_decision_v4_refill_decoupling import (
    V4_X1_DECISION_V4_REFILL_DECOUPLING_PROFILE_V1,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_frozen_v4_preregistration_guard_accepts_exact_repository_spec() -> None:
    path, payload = verify_frozen_v4_preregistration(REPO_ROOT)
    assert path == REPO_ROOT / "docs/specs/decision_v4_refill_decoupling_v1.json"
    assert payload["rule_id"] == EXPECTED_RULE_ID
    assert payload["source"]["replay_authorized"] is False
    assert tuple(payload["required_descriptive_diagnostics"]) == REQUIRED_DIAGNOSTICS
    assert EXPECTED_PREREG_CANONICAL_SHA256 == (
        "aa8763bdebf7b3334016a651d0376b17d6c6d7aa3a2c2356bf126fd5de8396f7"
    )


def test_runtime_profile_remains_exact_frozen_v4_profile() -> None:
    profile = V4_X1_DECISION_V4_REFILL_DECOUPLING_PROFILE_V1
    assert profile.rule_id == EXPECTED_RULE_ID
    assert profile.target_count_max == 10
    assert profile.strong_zone_max_rank == 10
    assert profile.retention_zone_max_rank == 20
    assert profile.mild_deterioration_max_rank == 50
    assert profile.soft_replacement_min_rank_advantage == 5
    assert profile.allow_temporary_underfill is True
    assert profile.bootstrap_first_session_exact_top10 is True
