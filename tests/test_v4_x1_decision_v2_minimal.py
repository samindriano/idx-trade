from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.decision_v2_minimal import DecisionV2Error, DecisionV2ShadowState
from idx_trade.v4_x1_decision_v1_contract import (
    EXPECTED_ALPHA_MODEL_FINGERPRINT,
    EXPECTED_ALPHA_MODEL_ID,
    VerifiedScoreSession,
    _VERIFIED_TOKEN,
)
from idx_trade.v4_x1_decision_v2_minimal import (
    V4_X1_DECISION_V2_MINIMAL_PROFILE_V1,
    plan_v4_x1_decision_v2_minimal,
    rank_session_from_v4_x1_verified,
)


def _verified(day: str, order: list[str], *, token: object = _VERIFIED_TOKEN) -> VerifiedScoreSession:
    frame = pd.DataFrame(
        {
            "ticker": order,
            "rank_consensus": range(1, len(order) + 1),
        }
    )
    return VerifiedScoreSession(
        session_date=day,
        model_id=EXPECTED_ALPHA_MODEL_ID,
        model_fingerprint=EXPECTED_ALPHA_MODEL_FINGERPRINT,
        artifact_path=Path("dummy.parquet"),
        artifact_sha256="x",
        manifest_path=Path("dummy.json"),
        manifest_sha256="y",
        scores=frame,
        alpha_tie_rows=0,
        _verification_token=token,
    )


def _order(*preferred: str, n: int = 30) -> list[str]:
    seen = set(preferred)
    fillers = [f"X{i:02d}" for i in range(1, n + 1) if f"X{i:02d}" not in seen]
    return list(preferred) + fillers[: n - len(preferred)]


def test_profile_constants_match_frozen_preregistration_json() -> None:
    payload = json.loads(
        Path("docs/specs/decision_v2_minimal_v4_x1_profile_v1.json").read_text(encoding="utf-8")
    )
    profile = payload["profile"]
    frozen = V4_X1_DECISION_V2_MINIMAL_PROFILE_V1

    assert profile["alpha_model_id"] == EXPECTED_ALPHA_MODEL_ID
    assert profile["target_count_max"] == frozen.target_count_max
    assert profile["strong_zone_max_rank"] == frozen.strong_zone_max_rank
    assert profile["retention_zone_max_rank"] == frozen.retention_zone_max_rank
    assert profile["soft_replacement_min_rank_advantage"] == frozen.soft_replacement_min_rank_advantage
    assert profile["entry_confirmation_previous_rank_max"] == frozen.entry_confirmation_previous_rank_max
    assert profile["exit_confirmation_consecutive_outside_retention"] == frozen.exit_confirmation_consecutive_outside_retention
    assert profile["universe_absence_exit_immediate"] is frozen.universe_absence_exit_immediate
    assert profile["allow_temporary_underfill"] is frozen.allow_temporary_underfill
    assert profile["bootstrap_first_session_exact_top10"] is frozen.bootstrap_first_session_exact_top10
    assert profile["bootstrap_preroll"] is False
    assert profile["fold_resets"] is False


def test_adapter_requires_verified_v4_x1_lineage() -> None:
    bad_token = _verified("2026-01-02", _order(*[f"A{i}" for i in range(1, 11)]), token=object())
    with pytest.raises(DecisionV2Error, match="VERIFIED_SCORE_SESSION_REQUIRED"):
        rank_session_from_v4_x1_verified(bad_token)

    good = _verified("2026-01-02", _order(*[f"A{i}" for i in range(1, 11)]))
    wrong_model = VerifiedScoreSession(
        **{**good.__dict__, "model_id": "OTHER_MODEL"}
    )
    with pytest.raises(DecisionV2Error, match="MODEL_ID_CHANGED"):
        rank_session_from_v4_x1_verified(wrong_model)


def test_adapter_normalizes_idx_tickers_and_is_row_order_independent() -> None:
    verified = _verified("2026-01-02", _order("BBCA.JK", "BBRI", "BMRI"))
    shuffled = VerifiedScoreSession(
        **{**verified.__dict__, "scores": verified.scores.sample(frac=1.0, random_state=7).reset_index(drop=True)}
    )

    a = rank_session_from_v4_x1_verified(verified)
    b = rank_session_from_v4_x1_verified(shuffled)
    assert a == b
    assert a.rows[0].ticker == "BBCA"


def test_adapter_runs_bootstrap_and_nonbootstrap_without_h5_h10_inputs() -> None:
    held = [f"A{i}" for i in range(1, 11)]
    first = _verified("2026-01-02", _order(*held))
    bootstrap = plan_v4_x1_decision_v2_minimal(first, None, DecisionV2ShadowState.empty())
    assert bootstrap.target_positions == tuple(held)

    previous = _verified(
        "2026-01-02",
        _order("A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "Z", "X01", "X02", "X03", "X04", "X05", "X06", "X07", "X08", "X09", "X10", "A1"),
    )
    current = _verified(
        "2026-01-03",
        _order("Z", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "X01", "X02", "X03", "X04", "X05", "X06", "X07", "X08", "X09", "X10", "X11", "A1"),
    )
    state = DecisionV2ShadowState(as_of_session_date="2026-01-02", positions=tuple(held))
    plan = plan_v4_x1_decision_v2_minimal(current, previous, state)
    assert any(intent.ticker == "A1" and intent.reason == "CONFIRMED_EXIT_GT20_2" for intent in plan.sell_intents)
    assert any(intent.ticker == "Z" for intent in plan.buy_intents)
