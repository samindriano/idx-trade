import dataclasses
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.decision_v2_minimal import (
    DecisionV2Error,
    DecisionV2Intent,
    DecisionV2Plan,
    DecisionV2ShadowState,
)
from idx_trade.v4_x1_decision_v1_contract import (
    DecisionPlan,
    EXPECTED_ALPHA_MODEL_FINGERPRINT,
    EXPECTED_ALPHA_MODEL_ID,
    TradeIntent,
    VerifiedScoreSession,
    _VERIFIED_TOKEN,
)
from idx_trade.v4_x1_decision_v2_minimal import (
    V4_X1_DECISION_V2_MINIMAL_PROFILE_V1,
    plan_v4_x1_decision_v2_minimal,
)
from idx_trade.v4_x1_sizing_v1 import (
    VerifiedDecisionPlan,
    _VERIFIED_DECISION_PLAN_TOKEN,
    size_decision_v1_entries,
)
from idx_trade.v4_x1_sizing_v1_decision_v2_adapter import (
    VerifiedDecisionV2SizingPlan,
    _VERIFIED_DECISION_V2_SIZING_PLAN_TOKEN,
    size_decision_v2_entries,
    verify_decision_v2_plan_for_sizing,
)


def _score(session_date, rows):
    frame = pd.DataFrame(rows, columns=["ticker", "rank_consensus"])
    return VerifiedScoreSession(
        session_date=session_date,
        model_id=EXPECTED_ALPHA_MODEL_ID,
        model_fingerprint=EXPECTED_ALPHA_MODEL_FINGERPRINT,
        artifact_path=Path(f"score-{session_date}.parquet"),
        artifact_sha256=("a" if session_date.endswith("21") else "b") * 64,
        manifest_path=Path(f"manifest-{session_date}.json"),
        manifest_sha256=("c" if session_date.endswith("21") else "d") * 64,
        scores=frame,
        alpha_tie_rows=0,
        _verification_token=_VERIFIED_TOKEN,
    )


def _bootstrap_v2():
    tickers = tuple(f"T{i:02d}" for i in range(1, 11))
    current = _score("2026-08-21", [(ticker, i) for i, ticker in enumerate(tickers, 1)])
    shadow = DecisionV2ShadowState.empty()
    plan = plan_v4_x1_decision_v2_minimal(current, None, shadow)
    verified = verify_decision_v2_plan_for_sizing(plan, current, None, shadow)
    return tickers, current, shadow, plan, verified


def test_v2_bootstrap_provenance_and_equal_lot_sizing():
    tickers, _, _, plan, verified = _bootstrap_v2()
    assert plan.rule_id == "V4_X1_DECISION_V2_MINIMAL_V1"
    out = size_decision_v2_entries(
        verified,
        nav_idr=50_000_000,
        available_cash_idr=50_000_000,
        reference_prices={ticker: 1000 for ticker in tickers},
    )
    assert [entry.lots for entry in out.entries] == [50] * 10
    assert out.total_sized_notional == 50_000_000
    assert out.residual_cash_after_sizing_reference == 0


def test_forged_v2_plan_is_rejected_before_sizing():
    _, current, shadow, plan, _ = _bootstrap_v2()
    forged = dataclasses.replace(
        plan,
        target_positions=tuple(reversed(plan.target_positions)),
    )
    with pytest.raises(DecisionV2Error, match="PROVENANCE_MISMATCH"):
        verify_decision_v2_plan_for_sizing(forged, current, None, shadow)


def test_v2_adapter_math_is_exactly_equivalent_to_legacy_v1_for_same_buy_set():
    tickers, _, _, v2_plan, v2_verified = _bootstrap_v2()
    prices = {
        ticker: price
        for ticker, price in zip(
            tickers,
            (905, 1010, 1325, 2480, 3890, 5125, 7775, 9800, 12650, 17425),
            strict=True,
        )
    }
    v2_out = size_decision_v2_entries(
        v2_verified,
        nav_idr=50_000_000,
        available_cash_idr=50_000_000,
        reference_prices=prices,
    )

    v1_plan = DecisionPlan(
        "2026-08-21",
        "OFFICIAL_OPEN_T_PLUS_1",
        (),
        tickers,
        tuple(
            TradeIntent("BUY_INTENT", intent.ticker, intent.rank_consensus, "EQUIVALENCE")
            for intent in v2_plan.buy_intents
        ),
        (),
        (),
        0,
    )
    v1_verified = VerifiedDecisionPlan(
        v1_plan,
        v1_plan.decision_session_date,
        "legacy-equivalence-score-sha",
        _verification_token=_VERIFIED_DECISION_PLAN_TOKEN,
    )
    v1_out = size_decision_v1_entries(
        v1_verified,
        nav_idr=50_000_000,
        available_cash_idr=50_000_000,
        reference_prices=prices,
    )

    assert v2_out.entries == v1_out.entries
    assert v2_out.total_sized_notional == v1_out.total_sized_notional
    assert (
        v2_out.residual_cash_after_sizing_reference
        == v1_out.residual_cash_after_sizing_reference
    )


def test_v2_underfill_does_not_renormalize_remaining_entries_above_ten_percent():
    intents = (
        DecisionV2Intent("BUY_INTENT", "AAA", 1, "QUALIFIED_VACANCY_FILL"),
        DecisionV2Intent("BUY_INTENT", "BBB", 2, "QUALIFIED_VACANCY_FILL"),
    )
    plan = DecisionV2Plan(
        decision_session_date="2026-08-21",
        current_shadow_positions=(),
        target_positions=("AAA", "BBB"),
        buy_intents=intents,
        sell_intents=(),
        hold_tickers=(),
        incumbent_observations=(),
        challenger_observations=(),
        unfilled_slots=8,
        capacity_state="UNFILLED_NO_QUALIFIED_CHALLENGER",
        rule_id=V4_X1_DECISION_V2_MINIMAL_PROFILE_V1.rule_id,
        bootstrap=False,
    )
    verified = VerifiedDecisionV2SizingPlan(
        plan=plan,
        current_score_session_date=plan.decision_session_date,
        current_score_artifact_sha256="e" * 64,
        previous_score_session_date="2026-08-20",
        previous_score_artifact_sha256="f" * 64,
        _verification_token=_VERIFIED_DECISION_V2_SIZING_PLAN_TOKEN,
    )
    out = size_decision_v2_entries(
        verified,
        nav_idr=50_000_000,
        available_cash_idr=50_000_000,
        reference_prices={"AAA": 1000, "BBB": 1000},
    )
    assert [entry.lots for entry in out.entries] == [50, 50]
    assert all(entry.sized_weight == 0.10 for entry in out.entries)
    assert out.total_sized_notional == 10_000_000
    assert out.residual_cash_after_sizing_reference == 40_000_000


def test_raw_v2_plan_cannot_bypass_verified_adapter():
    _, _, _, plan, _ = _bootstrap_v2()
    with pytest.raises(DecisionV2Error, match="VERIFIED_DECISION_V2"):
        size_decision_v2_entries(
            plan,
            nav_idr=50_000_000,
            available_cash_idr=50_000_000,
            reference_prices={ticker: 1000 for ticker in plan.target_positions},
        )
