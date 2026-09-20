from __future__ import annotations

import copy
from dataclasses import replace

import pytest

from idx_trade import forward_dividend_v1 as dividend
from idx_trade.v4_x1_ca_timing_matrix_v1 import (
    build_ca_timing_matrix_v1,
    verify_ca_timing_matrix_extension,
    verify_ca_timing_matrix_payload,
)
from idx_trade.v4_x1_decision_v1_contract import DecisionV1Error
from idx_trade.v4_x1_execution_v1_contract import PaperPortfolioState


def _event(payment_date: str) -> dividend.CertifiedCashDividend:
    return dividend.CertifiedCashDividend(
        event_id="DIV-1",
        ticker="BBCA",
        announcement_timestamp="2026-08-20T10:00:00",
        gross_dividend_per_share_idr=10.0,
        cum_date="2026-08-20",
        ex_date="2026-08-21",
        record_date="2026-08-22",
        payment_date=payment_date,
        source_evidence_sha256="a" * 64,
    )


def _state(
    cash: float,
    *,
    settlement: bool = False,
    payment_date: str = "2026-09-02",
) -> dividend.DividendAwarePaperState:
    ledger = dividend.DividendLedger()
    if settlement:
        entitlement = dividend.PaperDividendEntitlement(
            event_id="DIV-1",
            ticker="BBCA",
            entitled_shares=100,
            gross_dividend_per_share_idr=10.0,
            cum_date="2026-08-20",
            ex_date="2026-08-21",
            record_date="2026-08-22",
            payment_date=payment_date,
            source_evidence_sha256="a" * 64,
        )
        ledger = dividend.DividendLedger(
            entitlements=(entitlement,),
            settlements=(
                dividend.PaperDividendSettlement(
                    event_id="DIV-1",
                    ticker="BBCA",
                    entitled_shares=100,
                    gross_amount_idr=1_000.0,
                    payment_date=payment_date,
                    settled_on_session_date="2026-09-02",
                    source_evidence_sha256="a" * 64,
                ),
            )
        )
    return dividend.DividendAwarePaperState(
        base_state=PaperPortfolioState("2026-09-02", cash, ()),
        dividend_ledger=ledger,
    )


@pytest.mark.parametrize(
    ("payment_date", "raw_settled", "sizing_settled", "timing_class"),
    (
        ("2026-09-01", True, True, "PAYMENT_BEFORE_DECISION"),
        ("2026-09-02", False, True, "PAYMENT_ON_DECISION"),
        ("2026-09-03", False, False, "PAYMENT_ON_EXECUTION"),
    ),
)
def test_ca_timing_matrix_covers_three_payment_boundaries(
    payment_date: str,
    raw_settled: bool,
    sizing_settled: bool,
    timing_class: str,
) -> None:
    event = _event(payment_date)
    raw = _state(
        2_000.0 if raw_settled else 1_000.0,
        settlement=raw_settled,
        payment_date=payment_date,
    )
    sizing = _state(
        2_000.0 if sizing_settled else 1_000.0,
        settlement=sizing_settled,
        payment_date=payment_date,
    )
    matrix = build_ca_timing_matrix_v1(
        (event,),
        decision_session_date="2026-09-02",
        execution_session_date="2026-09-03",
        raw_state=raw,
        sizing_state=sizing,
    )
    assert matrix["rows"][0]["timing_class"] == timing_class
    assert verify_ca_timing_matrix_payload(matrix) == matrix


def test_ca_timing_matrix_rejects_early_settlement_projection() -> None:
    raw = _state(2_000.0, settlement=True)
    sizing = replace(raw, base_state=replace(raw.base_state, cash_idr=2_000.0))
    with pytest.raises(DecisionV1Error, match="ON_DECISION_PROJECTION_MISMATCH"):
        build_ca_timing_matrix_v1(
            (_event("2026-09-02"),),
            decision_session_date="2026-09-02",
            execution_session_date="2026-09-03",
            raw_state=raw,
            sizing_state=sizing,
        )


def test_ca_timing_matrix_allows_only_additive_preopen_event_extension() -> None:
    raw = _state(1_000.0)
    parent = build_ca_timing_matrix_v1(
        (),
        decision_session_date="2026-09-02",
        execution_session_date="2026-09-03",
        raw_state=raw,
        sizing_state=raw,
    )
    current = build_ca_timing_matrix_v1(
        (_event("2026-09-04"),),
        decision_session_date="2026-09-02",
        execution_session_date="2026-09-03",
        raw_state=raw,
        sizing_state=raw,
    )
    assert verify_ca_timing_matrix_extension(parent, current) == current


@pytest.mark.parametrize("tamper_kind", ("extra_field", "timing_semantics"))
def test_hash_valid_noncanonical_ca_timing_payload_fails_closed(
    tamper_kind: str,
) -> None:
    import idx_trade.v4_x1_ca_timing_matrix_v1 as timing

    raw = _state(1_000.0)
    matrix = build_ca_timing_matrix_v1(
        (_event("2026-09-04"),),
        decision_session_date="2026-09-02",
        execution_session_date="2026-09-03",
        raw_state=raw,
        sizing_state=replace(raw, base_state=replace(raw.base_state, cash_idr=1_000.0)),
    )
    tampered = copy.deepcopy(matrix)
    if tamper_kind == "extra_field":
        tampered["unexpected_extension"] = "accepted-by-hash-only"
    else:
        tampered["rows"][0]["execution_boundary_action"] = (
            "SETTLE_AT_EXECUTION_BOUNDARY"
        )
    body = dict(tampered)
    body.pop("payload_sha256")
    tampered["payload_sha256"] = timing._canonical_hash(body)

    with pytest.raises(DecisionV1Error, match="CA_TIMING_MATRIX_"):
        verify_ca_timing_matrix_payload(tampered)
