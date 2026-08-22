from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import idx_trade.forward_dividend_v1 as fd
from idx_trade.v4_x1_decision_v1_contract import DecisionV1Error
from idx_trade.v4_x1_execution_v1_contract import (
    ExecutionOrderPlan,
    ExecutionResult,
    PaperPortfolioState,
    PaperPosition,
    paper_state_hash,
)
from idx_trade.v4_x1_sizing_v1 import SizingPlan, _SIZING_PLAN_TOKEN


def _event(event_id: str = "E1", *, ticker: str = "BBCA") -> fd.CertifiedCashDividend:
    return fd.CertifiedCashDividend(
        event_id=event_id,
        ticker=ticker,
        announcement_timestamp="2026-08-19T18:31:03",
        gross_dividend_per_share_idr=25.0,
        cum_date="2026-08-28",
        ex_date="2026-08-31",
        record_date="2026-09-01",
        payment_date="2026-09-16",
        source_evidence_sha256="a" * 64,
    )


def _base(session: str, *, cash: float = 1_000_000.0, shares: int = 0) -> PaperPortfolioState:
    positions = () if shares == 0 else (PaperPosition("BBCA", shares),)
    return PaperPortfolioState(session, cash, positions)


def _entitlement(*, shares: int = 200) -> fd.PaperDividendEntitlement:
    event = _event()
    return fd.PaperDividendEntitlement(
        event_id=event.event_id,
        ticker=event.ticker,
        entitled_shares=shares,
        gross_dividend_per_share_idr=event.gross_dividend_per_share_idr,
        cum_date=event.cum_date,
        ex_date=event.ex_date,
        record_date=event.record_date,
        payment_date=event.payment_date,
        source_evidence_sha256=event.source_evidence_sha256,
    )


def _receivable(*, shares: int = 200) -> fd.PaperDividendReceivable:
    ent = _entitlement(shares=shares)
    return fd.PaperDividendReceivable(
        event_id=ent.event_id,
        ticker=ent.ticker,
        entitled_shares=shares,
        gross_dividend_per_share_idr=ent.gross_dividend_per_share_idr,
        gross_amount_idr=shares * ent.gross_dividend_per_share_idr,
        payment_date=ent.payment_date,
        source_evidence_sha256=ent.source_evidence_sha256,
    )


def _write_review(tmp_path: Path) -> tuple[Path, Path]:
    attachment_dir = tmp_path / "attachments"
    attachment_dir.mkdir()
    docs = []
    for idx, payload in enumerate((b"pdf-one", b"pdf-two", b"pdf-three"), start=1):
        name = f"doc{idx}.pdf"
        (attachment_dir / name).write_bytes(payload)
        docs.append(
            {
                "pdf_filename": name,
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    review = {
        "status": fd.REVIEW_STATUS,
        "authority_recommendation": fd.AUTHORITY,
        "semantic_matches": {
            "ticker": True,
            "dividend_subject": True,
            "dividend_per_share": True,
            "cum_regular_negotiated": True,
            "ex_regular_negotiated": True,
            "record_date": True,
            "payment_date": True,
        },
        "source_announcement_raw_sha256": "b" * 64,
        "documents": docs,
        "announcement": {"date": "2026-08-19T18:31:03"},
        "expected_event": {
            "ticker": "BBCA",
            "gross_dividend_per_share_idr": "25",
            "cum_regular_negotiated": "28 Agustus 2026",
            "ex_regular_negotiated": "31 Agustus 2026",
            "record_date": "1 September 2026",
            "payment_date": "16 September 2026",
        },
    }
    review_path = tmp_path / "ATTACHMENT_REVIEW.json"
    review_path.write_text(json.dumps(review), encoding="utf-8")
    return review_path, attachment_dir


def test_certify_review_verifies_hash_chain_and_is_deterministic(tmp_path: Path) -> None:
    review, attachment_dir = _write_review(tmp_path)
    first = fd.certify_direct_idx_dividend_from_attachment_review(review, attachment_dir)
    second = fd.certify_direct_idx_dividend_from_attachment_review(review, attachment_dir)
    assert first == second
    assert first.ticker == "BBCA"
    assert first.gross_dividend_per_share_idr == 25.0
    assert first.cum_date == "2026-08-28"
    assert first.ex_date == "2026-08-31"
    assert first.record_date == "2026-09-01"
    assert first.payment_date == "2026-09-16"
    assert first.event_id.startswith("CASH_DIVIDEND_BBCA_")
    assert len(first.source_evidence_sha256) == 64


def test_certify_review_fails_on_attachment_tamper(tmp_path: Path) -> None:
    review, attachment_dir = _write_review(tmp_path)
    (attachment_dir / "doc2.pdf").write_bytes(b"tampered")
    with pytest.raises(DecisionV1Error, match="DOCUMENT_SHA_MISMATCH"):
        fd.certify_direct_idx_dividend_from_attachment_review(review, attachment_dir)


def test_cum_date_held_or_bought_position_gets_entitlement_and_replay_is_idempotent() -> None:
    state = fd.DividendAwarePaperState(_base("2026-08-28", shares=200))
    once = fd.snapshot_cum_date_entitlements(state, (_event(),), session_date="2026-08-28")
    twice = fd.snapshot_cum_date_entitlements(once, (_event(),), session_date="2026-08-28")
    assert twice == once
    assert len(once.dividend_ledger.entitlements) == 1
    assert once.dividend_ledger.entitlements[0].entitled_shares == 200


def test_cum_date_sold_position_gets_no_entitlement() -> None:
    state = fd.DividendAwarePaperState(_base("2026-08-28", shares=0))
    result = fd.snapshot_cum_date_entitlements(state, (_event(),), session_date="2026-08-28")
    assert result.dividend_ledger.entitlements == ()


def test_ex_date_sell_keeps_entitlement_and_creates_receivable() -> None:
    ledger = fd.DividendLedger(entitlements=(_entitlement(shares=200),))
    state = fd.DividendAwarePaperState(_base("2026-08-31", shares=0), ledger)
    result = fd.advance_dividend_lifecycle(state, session_date="2026-08-31")
    assert result.base_state.positions == ()
    assert len(result.dividend_ledger.receivables) == 1
    assert result.dividend_ledger.receivables[0].gross_amount_idr == 5_000.0


def test_first_buy_on_ex_date_does_not_receive_prior_dividend() -> None:
    state = fd.DividendAwarePaperState(_base("2026-08-31", shares=100))
    result = fd.advance_dividend_lifecycle(state, session_date="2026-08-31")
    assert result.dividend_ledger.entitlements == ()
    assert result.dividend_ledger.receivables == ()


def test_receivable_is_in_total_return_nav_but_not_cash() -> None:
    ledger = fd.DividendLedger(
        entitlements=(_entitlement(shares=200),),
        receivables=(_receivable(shares=200),),
    )
    state = fd.DividendAwarePaperState(_base("2026-08-31", cash=1_000_000.0, shares=200), ledger)
    nav = fd.paper_total_return_nav_idr(state, {"BBCA": 10_000.0})
    assert nav == 3_005_000.0
    assert state.base_state.cash_idr == 1_000_000.0


def test_payment_settles_receivable_into_cash_once() -> None:
    ledger = fd.DividendLedger(
        entitlements=(_entitlement(shares=200),),
        receivables=(_receivable(shares=200),),
    )
    state = fd.DividendAwarePaperState(_base("2026-09-16", cash=1_000_000.0), ledger)
    once = fd.advance_dividend_lifecycle(state, session_date="2026-09-16")
    twice = fd.advance_dividend_lifecycle(once, session_date="2026-09-16")
    assert once == twice
    assert once.base_state.cash_idr == 1_005_000.0
    assert once.dividend_ledger.receivables == ()
    assert len(once.dividend_ledger.settlements) == 1
    assert once.dividend_ledger.settlements[0].tax_treatment == fd.TAX_TREATMENT


def test_conflicting_event_same_ticker_cum_fails_closed() -> None:
    state = fd.DividendAwarePaperState(_base("2026-08-28", shares=100))
    with pytest.raises(DecisionV1Error, match="CONFLICTING_EVENT_SAME_TICKER_CUM"):
        fd.snapshot_cum_date_entitlements(
            state,
            (_event("E1"), _event("E2")),
            session_date="2026-08-28",
        )


def test_dividend_aware_hash_changes_without_changing_legacy_paper_hash() -> None:
    base = _base("2026-08-28", shares=100)
    legacy_hash = paper_state_hash(base)
    empty = fd.DividendAwarePaperState(base)
    ledgered = fd.DividendAwarePaperState(
        base,
        fd.DividendLedger(entitlements=(_entitlement(shares=100),)),
    )
    assert paper_state_hash(base) == legacy_hash
    assert fd.dividend_aware_state_hash(empty) != fd.dividend_aware_state_hash(ledgered)


def test_prepare_v1_1_uses_receivable_in_nav_not_available_cash(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = fd.DividendLedger(
        entitlements=(_entitlement(shares=100),),
        receivables=(_receivable(shares=100),),
    )
    state = fd.DividendAwarePaperState(_base("2026-08-31", cash=1_000_000.0, shares=100), ledger)
    initial_sizing = SizingPlan(
        decision_session_date="2026-08-31",
        nav_idr=2_000_000.0,
        available_cash_idr=1_000_000.0,
        target_weight_per_name=0.10,
        max_entry_weight_per_name=0.15,
        entries=(),
        total_sized_notional=0.0,
        residual_cash_after_sizing_reference=1_000_000.0,
        _verification_token=_SIZING_PLAN_TOKEN,
    )
    base_plan = ExecutionOrderPlan(
        decision_session_date="2026-08-31",
        execution_session_date="2026-09-01",
        state_hash=paper_state_hash(state.base_state),
        eod_nav_idr=2_000_000.0,
        projected_cash_for_sizing_idr=1_000_000.0,
        sizing_plan=initial_sizing,
        sells=(),
        effective_buy_intents=(),
        target_positions=("BBCA",),
        regular_market_values_t={"BBCA": 1_000_000_000.0},
        eod_ohlcv_sha256="c" * 64,
        eod_model_input_sha256="d" * 64,
        official_calendar_sha256="e" * 64,
    )
    monkeypatch.setattr(fd, "prepare_execution_v1", lambda *args, **kwargs: base_plan)
    captured = {}

    def fake_size(verified_plan, intents, *, nav_idr, available_cash_idr, reference_prices):
        captured.update(nav=nav_idr, cash=available_cash_idr)
        return replace(
            initial_sizing,
            nav_idr=nav_idr,
            available_cash_idr=available_cash_idr,
        )

    monkeypatch.setattr(fd, "_size_entries_for_intents", fake_size)
    inputs = SimpleNamespace(raw_close_prices={"BBCA": 10_000.0})
    result = fd.prepare_execution_v1_1(object(), state, eod_inputs=inputs)
    assert result.total_return_nav_idr == 2_002_500.0
    assert captured == {"nav": 2_002_500.0, "cash": 1_000_000.0}
    assert result.base_plan.eod_nav_idr == 2_002_500.0


def test_execute_v1_1_preserves_dividend_ledger(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = fd.DividendLedger(entitlements=(_entitlement(shares=100),))
    state = fd.DividendAwarePaperState(_base("2026-08-28", shares=100), ledger)
    sizing = SizingPlan(
        decision_session_date="2026-08-28",
        nav_idr=2_000_000.0,
        available_cash_idr=1_000_000.0,
        target_weight_per_name=0.10,
        max_entry_weight_per_name=0.15,
        entries=(),
        total_sized_notional=0.0,
        residual_cash_after_sizing_reference=1_000_000.0,
        _verification_token=_SIZING_PLAN_TOKEN,
    )
    base_plan = ExecutionOrderPlan(
        decision_session_date="2026-08-28",
        execution_session_date="2026-08-31",
        state_hash=paper_state_hash(state.base_state),
        eod_nav_idr=2_000_000.0,
        projected_cash_for_sizing_idr=1_000_000.0,
        sizing_plan=sizing,
        sells=(),
        effective_buy_intents=(),
        target_positions=("BBCA",),
        regular_market_values_t={"BBCA": 1.0},
        eod_ohlcv_sha256="c" * 64,
        eod_model_input_sha256="d" * 64,
        official_calendar_sha256="e" * 64,
    )
    wrapped = fd.DividendAwareExecutionOrderPlan(
        base_plan=base_plan,
        dividend_state_hash=fd.dividend_aware_state_hash(state),
        dividend_ledger_hash=fd.dividend_ledger_hash(ledger),
        total_return_nav_idr=2_000_000.0,
    )
    next_base = replace(state.base_state, as_of_session_date="2026-08-31")
    fake_result = ExecutionResult(
        execution_session_date="2026-08-31",
        state_before_hash=paper_state_hash(state.base_state),
        state_after=next_base,
        fills=(),
        stamp_duty_idr=0.0,
        gross_turnover_idr=0.0,
        pending_transition_count=0,
        reconciliation_required=False,
    )
    monkeypatch.setattr(fd, "execute_open_v1", lambda *args, **kwargs: fake_result)
    result = fd.execute_open_v1_1(wrapped, state, open_inputs=object(), ca_attestation=object())
    assert result.state_after.base_state == next_base
    assert result.state_after.dividend_ledger == fd.normalize_dividend_ledger(ledger)
