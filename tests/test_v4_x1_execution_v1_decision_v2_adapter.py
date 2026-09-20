from pathlib import Path

import pandas as pd
import pytest

import idx_trade.forward_dividend_runtime_v1_1 as runtime
import idx_trade.forward_dividend_v1 as fd
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
from idx_trade.v4_x1_decision_seat_policy_v1 import (
    DecisionSeatClosePolicyV1,
    SEAT_POLICY_SCHEMA,
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
    close_obligation_explicitly,
    pending_intents_from_obligations,
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
from idx_trade.v4_x1_quantity_obligation_v1 import (
    apply_fill,
    plan_obligation,
)


def _seat_policy() -> DecisionSeatClosePolicyV1:
    return DecisionSeatClosePolicyV1(
        schema_version=SEAT_POLICY_SCHEMA,
        policy_id="synthetic-seat-close-policy",
        authorization_ref="synthetic-test-authority",
        allowed_close_statuses=("CANCELED", "RELINQUISHED"),
        allowed_close_reasons=("EXPLICIT_DECISION_REVERSAL_CLOSE",),
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


def test_pending_buy_resolves_when_replacement_peer_was_sold_on_prior_session():
    state = PaperPortfolioState(
        "2026-08-21",
        50_000_000,
        (),
        pending_buys=(
            PendingPaperIntent(
                "BUY", "BBB", 1, "MARKET_ENTRY_UNAVAILABLE", "AAA"
            ),
        ),
    )
    plan = _plan(
        current_shadow=("BBB",),
        target=("BBB",),
    )
    order = prepare_execution_v1_from_decision_v2(
        _synthetic_verified(plan),
        state,
        eod_inputs=_eod("2026-08-21", "2026-08-24", {"BBB": 1000.0}),
    )

    assert order.effective_buy_intents[0].ticker == "BBB"
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
    assert [(row.ticker, row.shares) for row in result.state_after.positions] == [
        ("BBB", 5000)
    ]
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


@pytest.mark.parametrize(
    "side, target, current_shadow, positions, pending, error",
    (
        (
            "BUY",
            ("BBB",),
            ("AAA",),
            (("AAA", 2400),),
            (PendingPaperIntent("BUY", "AAA", None, "PARTIAL"),),
            "ACTIVE_BUY_OBLIGATION_REVERSAL_REQUIRES_EXPLICIT_CANCELLATION",
        ),
        (
            "SELL",
            ("AAA",),
            (),
            (('AAA', 5000),),
            (PendingPaperIntent("SELL", "AAA", None, "PARTIAL"),),
            "ACTIVE_SELL_OBLIGATION_REVERSAL_REQUIRES_EXPLICIT_CANCELLATION",
        ),
    ),
)
def test_active_obligation_reversal_fails_closed_without_explicit_cancellation(
    tmp_path,
    side,
    target,
    current_shadow,
    positions,
    pending,
    error,
):
    planned = plan_obligation(
        obligation_id=f"{side}-REVERSAL-01",
        ticker="AAA",
        side=side,
        planned_shares=5000,
        session_date="2026-08-21",
    )
    partial = apply_fill(
        planned,
        event_id=f"{side}-FILL-01",
        session_date="2026-08-24",
        filled_shares=2400 if side == "BUY" else 2500,
        reason="PARTIAL",
    )
    state = PaperPortfolioState(
        "2026-08-24",
        47_500_000,
        tuple(PaperPosition(ticker, shares) for ticker, shares in positions),
        pending_buys=pending if side == "BUY" else (),
        pending_sells=pending if side == "SELL" else (),
        obligations=(partial,),
    )
    runtime.write_runtime_snapshot(
        tmp_path / "runtime",
        fd.DividendAwarePaperState(base_state=state),
    )
    state = runtime.load_latest_runtime_snapshot(
        tmp_path / "runtime"
    ).state.base_state
    plan = _plan(
        current_shadow=current_shadow,
        target=target,
            buys=(
                DecisionV2Intent(
                    "BUY_INTENT", "BBB", 1, "SOFT_RANK_GAP_REPLACEMENT", "AAA"
                ),
            ) if side == "BUY" else (),
            sells=(
                DecisionV2Intent(
                    "SELL_INTENT", "AAA", 21, "SOFT_RANK_GAP_REPLACEMENT", "BBB"
                ),
            ) if side == "BUY" else (),
        date="2026-08-24",
    )

    with pytest.raises(DecisionV2Error, match=error):
        prepare_execution_v1_from_decision_v2(
            _synthetic_verified(plan),
            state,
            eod_inputs=_eod(
                "2026-08-24",
                "2026-08-25",
                {"AAA": 1000.0, "BBB": 1000.0},
            ),
        )


@pytest.mark.parametrize("status", ["CANCELED", "RELINQUISHED"])
def test_explicit_obligation_close_allows_decision_reversal(tmp_path, status):
    planned = plan_obligation(
        obligation_id=f"BUY-EXPLICIT-CLOSE-{status}",
        ticker="AAA",
        side="BUY",
        planned_shares=5_000,
        session_date="2026-08-21",
    )
    partial = apply_fill(
        planned,
        event_id=f"FILL-EXPLICIT-CLOSE-{status}",
        session_date="2026-08-24",
        filled_shares=2_400,
        reason="PARTIAL",
    )
    pending_buys, pending_sells = pending_intents_from_obligations((partial,))
    partial_state = PaperPortfolioState(
        "2026-08-24",
        50_000_000,
        (PaperPosition("AAA", 2_400),),
        pending_buys=pending_buys,
        pending_sells=pending_sells,
        obligations=(partial,),
    )
    closed_state = close_obligation_explicitly(
        partial_state,
        obligation_id=partial.obligation_id,
        event_id=f"CLOSE-EXPLICIT-{status}",
        session_date="2026-08-24",
        reason="EXPLICIT_DECISION_REVERSAL_CLOSE",
        status=status,
        seat_policy=_seat_policy(),
    )
    closed = closed_state.obligations[0]
    assert closed.status == status
    assert closed.remaining_shares == 0
    assert closed.filled_shares + closed.relinquished_shares == 5_000
    assert closed.event_history[-1].policy_payload == _seat_policy().payload()
    assert closed.event_history[-1].policy_sha256 == _seat_policy().payload()[
        "policy_sha256"
    ]

    state = closed_state
    runtime.write_runtime_snapshot(
        tmp_path / f"runtime-{status}",
        fd.DividendAwarePaperState(base_state=state),
    )
    state = runtime.load_latest_runtime_snapshot(
        tmp_path / f"runtime-{status}"
    ).state.base_state
    plan = _plan(
        current_shadow=("AAA",),
        target=("BBB",),
        buys=(DecisionV2Intent("BUY_INTENT", "BBB", 1, "EXPLICIT_REVERSAL"),),
        sells=(DecisionV2Intent("SELL_INTENT", "AAA", 21, "EXPLICIT_REVERSAL"),),
        date="2026-08-24",
    )

    order = prepare_execution_v1_from_decision_v2(
        _synthetic_verified(plan),
        state,
        eod_inputs=_eod(
            "2026-08-24",
            "2026-08-25",
            {"AAA": 1_000.0, "BBB": 1_000.0},
            {"AAA": 1_000_000_000.0, "BBB": 1_000_000_000.0},
        ),
    )
    assert [row.ticker for row in order.effective_buy_intents] == ["BBB"]
    assert [row.ticker for row in order.sells] == ["AAA"]

    result = execute_open_v1(
        order,
        state,
        open_inputs=_open("2026-08-25", {"AAA": 1_000.0, "BBB": 1_000.0}),
        ca_attestation=_ca("2026-08-24", "2026-08-25", ["AAA", "BBB"]),
    )
    assert [(row.ticker, row.shares) for row in result.state_after.positions] == [
        ("BBB", 5_200)
    ]
    assert not result.state_after.pending_buys
    assert not result.state_after.pending_sells
    assert all(row.remaining_shares == 0 for row in result.state_after.obligations)
    assert {
        row.status for row in result.state_after.obligations
    } >= {status, "FILLED"}


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


def test_partial_buy_obligation_is_retried_even_when_actual_position_exists():
    planned = plan_obligation(
        obligation_id="BUY-AAA-DECISION-V2-01",
        ticker="AAA",
        side="BUY",
        planned_shares=5_000,
        session_date="2026-08-21",
        rank_consensus=1,
    )
    partial = apply_fill(
        planned,
        event_id="FILL-AAA-DECISION-V2-01",
        session_date="2026-08-24",
        filled_shares=2_400,
        reason="OPEN_CAPACITY_PARTIAL",
    )
    state = PaperPortfolioState(
        "2026-08-24",
        47_500_000,
        (PaperPosition("AAA", 2_400),),
        pending_buys=(
            PendingPaperIntent("BUY", "AAA", 1, "OPEN_CAPACITY_PARTIAL"),
        ),
        obligations=(partial,),
    )
    plan = _plan(
        current_shadow=("AAA",),
        target=("AAA",),
        date="2026-08-24",
    )

    order = prepare_execution_v1_from_decision_v2(
        _synthetic_verified(plan),
        state,
        eod_inputs=_eod(
            "2026-08-24",
            "2026-08-25",
            {"AAA": 1000.0},
            {"AAA": 300_000_000.0},
        ),
    )
    assert [intent.ticker for intent in order.effective_buy_intents] == ["AAA"]
    assert order.effective_buy_intents[0].reason.startswith("PAPER_RETRY_")

    result = execute_open_v1(
        order,
        state,
        open_inputs=_open("2026-08-25", {"AAA": 1000.0}),
        ca_attestation=_ca("2026-08-24", "2026-08-25", ["AAA"]),
    )
    assert [(row.ticker, row.shares) for row in result.state_after.positions] == [
        ("AAA", 5000)
    ]
    assert not result.state_after.pending_buys
    assert result.state_after.obligations[0].status == "FILLED"
