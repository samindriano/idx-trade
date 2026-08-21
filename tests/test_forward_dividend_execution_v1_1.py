from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import idx_trade.forward_dividend_execution_v1_1 as gate
import idx_trade.forward_dividend_v1 as fd
from idx_trade import forward_ca_attestation_v1 as ca
from idx_trade.v4_x1_decision_v1_contract import DecisionV1Error
from idx_trade.v4_x1_execution_v1_contract import (
    ExecutionResult,
    PaperPortfolioState,
    PaperPosition,
    paper_state_hash,
)


def _event(
    *,
    event_id: str = "CASH_DIVIDEND_BBCA_TEST",
    ticker: str = "BBCA",
    announcement_timestamp: str = "2026-08-19T18:31:03",
    cum_date: str = "2026-08-28",
    ex_date: str = "2026-08-31",
) -> fd.CertifiedCashDividend:
    return fd.CertifiedCashDividend(
        event_id=event_id,
        ticker=ticker,
        announcement_timestamp=announcement_timestamp,
        gross_dividend_per_share_idr=25.0,
        cum_date=cum_date,
        ex_date=ex_date,
        record_date="2026-09-01",
        payment_date="2026-09-16",
        source_evidence_sha256="a" * 64,
    )


def _verified_evidence(tmp_path: Path, event: fd.CertifiedCashDividend | None = None) -> gate.VerifiedCashDividendEvidence:
    review = tmp_path / f"review-{hash(event.event_id if event else 'default')}.json"
    review.write_text("{}", encoding="utf-8")
    return gate.VerifiedCashDividendEvidence(
        event=event or _event(),
        review_path=review,
        review_sha256=hashlib.sha256(review.read_bytes()).hexdigest(),
        announcement_id="20260819183103-005/CSG-IVR/2026_id-id",
        announcement_number="005/CSG-IVR/2026",
        _verification_token=gate._VERIFIED_DIVIDEND_EVIDENCE_TOKEN,
    )


def _write_attestation(
    tmp_path: Path,
    *,
    status: str = "RELEVANT_EVENT_DETECTED",
    row_status: str = ca.RELEVANT,
    reasons: list[str] | None = None,
) -> tuple[Path, Path]:
    source = tmp_path / "source.json"
    source.write_text("{}", encoding="utf-8")
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    attestation = tmp_path / "attestation.json"
    payload = {
        "schema_version": ca.ATTESTATION_SCHEMA,
        "from_session_date": "2026-08-19",
        "through_session_date": "2026-08-20",
        "status": status,
        "provider_repository": ca.PROVIDER_REPOSITORY,
        "provider_commit": ca.PROVIDER_COMMIT,
        "upstream_base_url": ca.UPSTREAM_BASE_URL,
        "calendar_schema_fingerprint": ca.EXPECTED_CALENDAR_SCHEMA_FINGERPRINT,
        "evidence_rows": [
            {
                "ticker": "BBCA",
                "status": row_status,
                "reasons": reasons if reasons is not None else [
                    "PREOPEN:ANNOUNCEMENT:20260819183103-005/CSG-IVR/2026_id-id"
                ],
            }
        ],
        "source_path": str(source),
        "source_sha256": source_sha,
    }
    attestation.write_text(json.dumps(payload), encoding="utf-8")
    return attestation, source


def _patch_source_manifest(monkeypatch: pytest.MonkeyPatch, source: Path) -> None:
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()

    def fake_verify(path):
        assert Path(path).resolve() == source.resolve()
        return (
            {
                "from_session_date": "2026-08-19",
                "through_session_date": "2026-08-20",
                "required_tickers": ["BBCA"],
                "calendar_schema_fingerprints": [ca.EXPECTED_CALENDAR_SCHEMA_FINGERPRINT],
                "_source_sha256": source_sha,
            },
            {"POST_EOD": {}, "PREOPEN": {}},
        )

    monkeypatch.setattr(ca, "verify_source_manifest", fake_verify)


def test_relevant_cash_dividend_is_admitted_only_after_verified_reconciliation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attestation, source = _write_attestation(tmp_path)
    _patch_source_manifest(monkeypatch, source)
    monkeypatch.setattr(gate, "_verify_relevant_ticker_cash_dividend_only", lambda *a, **k: None)
    evidence = _verified_evidence(
        tmp_path,
        _event(announcement_timestamp="2026-08-19T18:31:03"),
    )
    result = gate.reconcile_corporate_action_attestation_v1_1(
        attestation_path=attestation,
        expected_from_session_date="2026-08-19",
        expected_through_session_date="2026-08-20",
        required_tickers=["BBCA"],
        dividend_evidence=[evidence],
    )
    assert result.original_status == "RELEVANT_EVENT_DETECTED"
    assert result.relevant_tickers == frozenset({"BBCA"})
    assert result.legacy_attestation.status == "NO_RELEVANT_EVENTS"
    assert result.certified_events == (evidence.event,)


def test_relevant_ticker_without_verified_dividend_stays_blocked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attestation, source = _write_attestation(tmp_path)
    _patch_source_manifest(monkeypatch, source)
    monkeypatch.setattr(gate, "_verify_relevant_ticker_cash_dividend_only", lambda *a, **k: None)
    with pytest.raises(DecisionV1Error, match="WITHOUT_CERTIFIED_DIVIDEND"):
        gate.reconcile_corporate_action_attestation_v1_1(
            attestation_path=attestation,
            expected_from_session_date="2026-08-19",
            expected_through_session_date="2026-08-20",
            required_tickers=["BBCA"],
            dividend_evidence=[],
        )


def test_issued_history_reason_can_never_be_reconciled_as_cash_dividend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attestation, source = _write_attestation(
        tmp_path,
        reasons=["PREOPEN:ISSUED_HISTORY:stockSplit:2026-08-20"],
    )
    _patch_source_manifest(monkeypatch, source)
    evidence = _verified_evidence(tmp_path, _event())
    with pytest.raises(DecisionV1Error, match="NON_CASH_CA_REASON_ISSUED_HISTORY"):
        gate.reconcile_corporate_action_attestation_v1_1(
            attestation_path=attestation,
            expected_from_session_date="2026-08-19",
            expected_through_session_date="2026-08-20",
            required_tickers=["BBCA"],
            dividend_evidence=[evidence],
        )


def test_certified_dividend_outside_ca_window_does_not_explain_relevant_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attestation, source = _write_attestation(tmp_path)
    _patch_source_manifest(monkeypatch, source)
    monkeypatch.setattr(gate, "_verify_relevant_ticker_cash_dividend_only", lambda *a, **k: None)
    evidence = _verified_evidence(
        tmp_path,
        _event(
            announcement_timestamp="2026-08-01T12:00:00",
            cum_date="2026-08-28",
            ex_date="2026-08-31",
        ),
    )
    with pytest.raises(DecisionV1Error, match="OUTSIDE_CA_WINDOW"):
        gate.reconcile_corporate_action_attestation_v1_1(
            attestation_path=attestation,
            expected_from_session_date="2026-08-19",
            expected_through_session_date="2026-08-20",
            required_tickers=["BBCA"],
            dividend_evidence=[evidence],
        )


def test_source_rescan_rejects_rights_announcement_even_if_dividend_evidence_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    announcement = {
        "Items": [
            {
                "Code": "BBCA",
                "Date": "2026-08-20",
                "Title": "HMETD rights issue BBCA",
            }
        ]
    }

    def artifacts(phase, leg):
        if leg == "announcements":
            return [announcement]
        if leg == "calendar":
            return [{"Results": []}]
        if leg == "issued_history":
            return [{"data": []}]
        raise AssertionError(leg)

    monkeypatch.setattr(ca, "_artifact_payloads", artifacts)
    with pytest.raises(DecisionV1Error, match="NON_CASH_CA_ANNOUNCEMENT"):
        gate._verify_relevant_ticker_cash_dividend_only(
            "BBCA",
            from_date="2026-08-19",
            through_date="2026-08-20",
            phases={"PREOPEN": {}},
        )


def test_source_rescan_accepts_cash_dividend_only(monkeypatch: pytest.MonkeyPatch) -> None:
    announcement = {
        "Items": [
            {
                "Code": "BBCA",
                "Date": "2026-08-20",
                "Title": "Jadwal Dividen Tunai Interim BBCA",
            }
        ]
    }

    def artifacts(phase, leg):
        if leg == "announcements":
            return [announcement]
        if leg == "calendar":
            return [{"Results": []}]
        if leg == "issued_history":
            return [{"data": []}]
        raise AssertionError(leg)

    monkeypatch.setattr(ca, "_artifact_payloads", artifacts)
    gate._verify_relevant_ticker_cash_dividend_only(
        "BBCA",
        from_date="2026-08-19",
        through_date="2026-08-20",
        phases={"PREOPEN": {}},
    )


def _reconciliation(
    *,
    from_date: str,
    through_date: str,
    events: tuple[fd.CertifiedCashDividend, ...],
) -> gate.VerifiedDividendCAReconciliation:
    return gate.VerifiedDividendCAReconciliation(
        from_session_date=from_date,
        through_session_date=through_date,
        covered_tickers=frozenset({"BBCA"}),
        original_status="RELEVANT_EVENT_DETECTED",
        relevant_tickers=frozenset({"BBCA"}),
        certified_events=events,
        legacy_attestation=SimpleNamespace(),
        attestation_path=Path("attestation.json"),
        attestation_sha256="a" * 64,
        source_path=Path("source.json"),
        source_sha256="b" * 64,
        _verification_token=gate._DIVIDEND_RECONCILIATION_TOKEN,
    )


def test_reconciled_execution_snapshots_cum_entitlement_after_same_session_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = _event(cum_date="2026-08-28", ex_date="2026-08-31")
    before = fd.DividendAwarePaperState(
        PaperPortfolioState("2026-08-27", 1_000_000.0, ())
    )
    after_base = PaperPortfolioState(
        "2026-08-28",
        1_000_000.0,
        (PaperPosition("BBCA", 200),),
    )
    base_result = ExecutionResult(
        execution_session_date="2026-08-28",
        state_before_hash=paper_state_hash(before.base_state),
        state_after=after_base,
        fills=(),
        stamp_duty_idr=0.0,
        gross_turnover_idr=0.0,
        pending_transition_count=0,
        reconciliation_required=False,
    )
    monkeypatch.setattr(
        fd,
        "execute_open_v1_1",
        lambda *a, **k: fd.DividendAwareExecutionResult(
            base_result=base_result,
            state_after=fd.DividendAwarePaperState(after_base),
        ),
    )
    plan = SimpleNamespace(
        base_plan=SimpleNamespace(
            decision_session_date="2026-08-27",
            execution_session_date="2026-08-28",
        )
    )
    result = gate.execute_open_v1_1_reconciled(
        plan,
        before,
        open_inputs=SimpleNamespace(session_date="2026-08-28"),
        reconciliation=_reconciliation(
            from_date="2026-08-27",
            through_date="2026-08-28",
            events=(event,),
        ),
    )
    assert len(result.state_after.dividend_ledger.entitlements) == 1
    assert result.state_after.dividend_ledger.entitlements[0].entitled_shares == 200


def test_reconciled_execution_creates_ex_date_receivable_after_sell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = _event(cum_date="2026-08-28", ex_date="2026-08-31")
    entitlement = fd.PaperDividendEntitlement(
        event_id=event.event_id,
        ticker=event.ticker,
        entitled_shares=200,
        gross_dividend_per_share_idr=event.gross_dividend_per_share_idr,
        cum_date=event.cum_date,
        ex_date=event.ex_date,
        record_date=event.record_date,
        payment_date=event.payment_date,
        source_evidence_sha256=event.source_evidence_sha256,
    )
    before = fd.DividendAwarePaperState(
        PaperPortfolioState("2026-08-28", 1_000_000.0, (PaperPosition("BBCA", 200),)),
        fd.DividendLedger(entitlements=(entitlement,)),
    )
    after_base = PaperPortfolioState("2026-08-31", 3_000_000.0, ())
    base_result = ExecutionResult(
        execution_session_date="2026-08-31",
        state_before_hash=paper_state_hash(before.base_state),
        state_after=after_base,
        fills=(),
        stamp_duty_idr=0.0,
        gross_turnover_idr=0.0,
        pending_transition_count=0,
        reconciliation_required=False,
    )
    monkeypatch.setattr(
        fd,
        "execute_open_v1_1",
        lambda *a, **k: fd.DividendAwareExecutionResult(
            base_result=base_result,
            state_after=fd.DividendAwarePaperState(after_base, before.dividend_ledger),
        ),
    )
    plan = SimpleNamespace(
        base_plan=SimpleNamespace(
            decision_session_date="2026-08-28",
            execution_session_date="2026-08-31",
        )
    )
    result = gate.execute_open_v1_1_reconciled(
        plan,
        before,
        open_inputs=SimpleNamespace(session_date="2026-08-31"),
        reconciliation=_reconciliation(
            from_date="2026-08-28",
            through_date="2026-08-31",
            events=(event,),
        ),
    )
    assert result.state_after.base_state.positions == ()
    assert len(result.state_after.dividend_ledger.receivables) == 1
    assert result.state_after.dividend_ledger.receivables[0].gross_amount_idr == 5_000.0
