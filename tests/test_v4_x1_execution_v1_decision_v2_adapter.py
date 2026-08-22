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
    EXPECTED_ALPHA_MODEL_FINGERPRINT,
    EXPECTED_ALPHA_MODEL_ID,
    VerifiedScoreSession,
    _VERIFIED_TOKEN,
)
from idx_trade.v4_x1_decision_v2_minimal import (
    V4_X1_DECISION_V2_MINIMAL_PROFILE_V1,
    plan_v4_x1_decision_v2_minimal,
)
from idx_trade.v4_x1_execution_v1 import execute_open_v1
from idx_trade.v4_x1_execution_v1_contract import (
    PaperPortfolioState,
    PaperPosition,
    PendingPaperIntent,
)
from idx_trade.v4_x1_execution_v1_decision_v2_adapter import (
    prepare_execution_v1_from_decision_v2,
)
from idx_trade.v4_x1_execution_v1_verify import (
    VerifiedCorporateActionAttestation,
    VerifiedEODExecutionInputs,
    VerifiedOpenExecutionInputs,
    _CA_ATTESTATION_TOKEN,
    _EOD_INPUT_TOKEN,
    _OPEN_INPUT_TOKEN,
)
from idx_trade.v4_x1_sizing_v1_decision_v2_adapter import (
    VerifiedDecisionV2SizingPlan,
    _VERIFIED_DECISION_V2_SIZING_PLAN_TOKEN,
    verify_decision_v2_plan_for_sizing,
)


def _score(session_date, rows):
    return VerifiedScoreSession(
        session_date=session_date,
        model_id=EXPECTED_ALPHA_MODEL_ID,
        model_fingerprint=EXPECTED_ALPHA_MODEL_FINGERPRINT,
        artifact_path=Path(f"score-{session_date}.parquet"),
        artifact_sha256="a" * 64,
        manifest_path=Path(f"manifest-{session_date}.json"),
        manifest_sha256="b" * 64,
        scores=pd.DataFrame(rows, columns=["ticker", "rank_consensus"]),
        alpha_tie_rows=0,
        _verification_token=_VERIFIED_TOKEN,
    )


def _eod(date, next_date, closes, values=None):
    values = values or {ticker: 1_000_000_000_000.0 for ticker in closes}
    return VerifiedEODExecutionInputs(
        date,
        next_date,
        closes,
        values,
        Path("eod.parquet"),
        "c" * 64,
        Path("model.parquet"),
        "d" * 64,
        Path("calendar.csv"),
        "e" * 64,
        _verification_token=_EOD_INPUT_TOKEN,
    )


def _open(date, prices):
    return VerifiedOpenExecutionInputs(
        date,
        prices,
        frozenset(prices),
        Path("open.parquet"),
        "f" * 64,
        _verification_token=_OPEN_INPUT_TOKEN,
    )


def _ca(from_date, through_date, tickers):
    return VerifiedCorporateActionAttestation(
        from_date,
        through_date,
        frozenset(tickers),
        "NO_RELEVANT_EVENTS",
        Path("ca.json"),
        "1" * 64,
        Path("source.json"),
        "2" * 64,
        _verification_token=_CA_ATTESTATION_TOKEN,
    )


def _synthetic_verified(plan):
    return VerifiedDecisionV2SizingPlan(
        plan=plan,
        current_score_session_date=plan.decision_session_date,
        current_score_artifact_sha256="3" * 64,
        previous_score_session_date="2026-08-20",
        previous_score_artifact_sha256="4" * 64,
        _verification_token=_VERIFIED_DECISION_V2_SIZING_PLAN_TOKEN,
    )


def _plan(*, current_shadow, target, buys=(), sells=(), date="2026-08-21"):
    return DecisionV2Plan(
        decision_session_date=date,
        current_shadow_positions=tuple(current_shadow),
        target_positions=tuple(target),
        buy_intents=tuple(buys),
        sell_intents=tuple(sells),
        hold_tickers=tuple(ticker for ticker in target if ticker in current_shadow),
        incumbent_observations=(),
        challenger_observations=(),
        unfilled_slots=max(0, 10 - len(target)),
        capacity_state=("FULL" if len(target) == 10 else "UNFILLED_NO_QUALIFIED_CHALLENGER"),
        rule_id=V4_X1_DECISION_V2_MINIMAL_PROFILE_V1.rule_id,
        bootstrap=False,
    )


def test_real_verified_v2_bootstrap_prepares_execution_without_rule_projection():
    tickers = tuple(f"T{i:02d}" for i in range(1, 11))
    current = _score(
        "2026-08-21",
        [(ticker, rank) for rank, ticker in enumerate(tickers, 1)],
    )
    shadow = DecisionV2ShadowState.empty()
    plan = plan_v4_x1_decision_v2_minimal(current, None, shadow)
    verified = verify_decision_v2_plan_for_sizing(plan, current, None, shadow)
    state = PaperPortfolioState("2026-08-21", 50_000_000, ())

    order = prepare_execution_v1_from_decision_v2(
        verified,
        state,
        eod_inputs=_eod(
            "2026-08-21",
            "2026-08-24",
            {ticker: 1000.0 for ticker in tickers},
        ),
    )

    assert order.target_positions == tickers
    assert not order.sells
    assert [row.ticker for row in order.effective_buy_intents] == list(tickers)
    assert [row.lots for row in order.sizing_plan.entries] == [50] * 10


def test_wrong_session_paper_state_fails_closed_before_execution_prepare():
    plan = _plan(
        current_shadow=(),
        target=("AAA",),
        buys=(DecisionV2Intent("BUY_INTENT", "AAA", 1, "QUALIFIED_VACANCY_FILL"),),
    )
    state = PaperPortfolioState("2026-08-20", 50_000_000, ())
    with pytest.raises(DecisionV2Error, match="PAPER_STATE_SESSION_MISMATCH"):
        prepare_execution_v1_from_decision_v2(
            _synthetic_verified(plan),
            state,
            eod_inputs=_eod("2026-08-21", "2026-08-24", {"AAA": 1000.0}),
        )


def test_pending_buy_reversal_cancels_impossible_sell_and_unblocks_paired_buy():
    state = PaperPortfolioState(
        "2026-08-21",
        50_000_000,
        (),
        pending_buys=(
            PendingPaperIntent("BUY", "AAA", 5, "MARKET_ENTRY_UNAVAILABLE"),
        ),
    )
    plan = _plan(
        current_shadow=("AAA",),
        target=("BBB",),
        buys=(
            DecisionV2Intent(
                "BUY_INTENT", "BBB", 1, "SOFT_RANK_GAP_REPLACEMENT", "AAA"
            ),
        ),
        sells=(
            DecisionV2Intent(
                "SELL_INTENT", "AAA", 21, "SOFT_RANK_GAP_REPLACEMENT", "BBB"
            ),
        ),
    )
    order = prepare_execution_v1_from_decision_v2(
        _synthetic_verified(plan),
        state,
        eod_inputs=_eod("2026-08-21", "2026-08-24", {"BBB": 1000.0}),
    )

    assert order.sells == ()
    assert [row.ticker for row in order.effective_buy_intents] == ["BBB"]
    assert order.effective_buy_intents[0].replacement_peer is None
    assert order.effective_buy_intents[0].reason.startswith(
        "PAPER_PAIR_SELL_ALREADY_ABSENT_"
    )

    result = execute_open_v1(
        order,
        state,
        open_inputs=_open("2026-08-24", {"BBB": 1000.0}),
        ca_attestation=_ca("2026-08-21", "2026-08-24", ["BBB"]),
    )
    assert {row.ticker for row in result.state_after.positions} == {"BBB"}
    assert not result.state_after.pending_buys
    assert not result.state_after.pending_sells


def test_pending_sell_reversal_cancels_impossible_buy_and_keeps_actual_holding():
    state = PaperPortfolioState(
        "2026-08-21",
        45_000_000,
        (PaperPosition("AAA", 5000),),
        pending_sells=(
            PendingPaperIntent("SELL", "AAA", 21, "MARKET_EXIT_UNAVAILABLE"),
        ),
    )
    plan = _plan(
        current_shadow=(),
        target=("AAA",),
        buys=(DecisionV2Intent("BUY_INTENT", "AAA", 1, "QUALIFIED_VACANCY_FILL"),),
    )
    order = prepare_execution_v1_from_decision_v2(
        _synthetic_verified(plan),
        state,
        eod_inputs=_eod("2026-08-21", "2026-08-24", {"AAA": 1000.0}),
    )

    assert order.sells == ()
    assert order.effective_buy_intents == ()
    assert order.sizing_plan.entries == ()

    result = execute_open_v1(
        order,
        state,
        open_inputs=_open("2026-08-24", {}),
        ca_attestation=_ca("2026-08-21", "2026-08-24", ["AAA"]),
    )
    assert [(row.ticker, row.shares) for row in result.state_after.positions] == [
        ("AAA", 5000)
    ]
    assert not result.state_after.pending_buys
    assert not result.state_after.pending_sells


def test_decision_v2_shadow_must_match_paper_plus_pending_lineage():
    state = PaperPortfolioState(
        "2026-08-21",
        50_000_000,
        (),
        pending_buys=(PendingPaperIntent("BUY", "AAA", 1, "PENDING"),),
    )
    plan = _plan(current_shadow=(), target=())
    with pytest.raises(DecisionV2Error, match="SHADOW_PAPER_LINEAGE_MISMATCH"):
        prepare_execution_v1_from_decision_v2(
            _synthetic_verified(plan),
            state,
            eod_inputs=_eod("2026-08-21", "2026-08-24", {}),
        )
