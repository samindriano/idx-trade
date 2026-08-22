from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

import idx_trade.forward_dividend_execution_v1_1 as gate
import idx_trade.forward_dividend_runtime_v1_1 as runtime
import idx_trade.forward_dividend_v1 as fd
from idx_trade.decision_v2_minimal import (
    DecisionV2ShadowState,
    RankObservation,
    RankSession,
    plan_decision_v2_minimal,
)
from idx_trade.v4_x1_decision_v1_contract import DecisionV1Error
from idx_trade.v4_x1_decision_v2_minimal import (
    V4_X1_DECISION_V2_MINIMAL_PROFILE_V1,
)
from idx_trade.v4_x1_execution_v1_contract import (
    PaperPortfolioState,
    PaperPosition,
    PendingPaperIntent,
)


def _event(
    *,
    event_id: str = "CASH_DIVIDEND_BBCA_RUNTIME_TEST",
    ticker: str = "BBCA",
    cum_date: str = "2026-08-28",
    source_sha: str = "a" * 64,
) -> fd.CertifiedCashDividend:
    return fd.CertifiedCashDividend(
        event_id=event_id,
        ticker=ticker,
        announcement_timestamp="2026-08-19T18:31:03",
        gross_dividend_per_share_idr=25.0,
        cum_date=cum_date,
        ex_date="2026-08-31",
        record_date="2026-09-01",
        payment_date="2026-09-16",
        source_evidence_sha256=source_sha,
    )


def _evidence(
    tmp_path: Path,
    event: fd.CertifiedCashDividend | None = None,
) -> gate.VerifiedCashDividendEvidence:
    review = tmp_path / f"review-{(event or _event()).event_id}.json"
    review.write_text('{"status":"synthetic"}\n', encoding="utf-8")
    return gate.VerifiedCashDividendEvidence(
        event=event or _event(),
        review_path=review,
        review_sha256=hashlib.sha256(review.read_bytes()).hexdigest(),
        announcement_id="20260819183103-005/CSG-IVR/2026_id-id",
        announcement_number="005/CSG-IVR/2026",
        _verification_token=gate._VERIFIED_DIVIDEND_EVIDENCE_TOKEN,
    )


def _patch_verifier(
    monkeypatch: pytest.MonkeyPatch,
    verified_rows: list[gate.VerifiedCashDividendEvidence],
) -> None:
    by_path = {row.review_path.resolve(): row for row in verified_rows}

    def verify(*, review_path, attachment_dir):
        path = Path(review_path).resolve()
        assert Path(attachment_dir).resolve().is_dir()
        row = by_path[path]
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != row.review_sha256:
            raise DecisionV1Error("SYNTHETIC_REVIEW_SHA_MISMATCH")
        return row

    monkeypatch.setattr(
        gate,
        "verify_cash_dividend_evidence_for_execution",
        verify,
    )


def _registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *events: fd.CertifiedCashDividend,
) -> tuple[runtime.RegisteredDividendEvidence, ...]:
    attachment_dir = tmp_path / "attachments"
    attachment_dir.mkdir(exist_ok=True)
    rows = [_evidence(tmp_path, event) for event in events or (_event(),)]
    _patch_verifier(monkeypatch, rows)
    registry: tuple[runtime.RegisteredDividendEvidence, ...] = ()
    for row in rows:
        registry = runtime.register_verified_cash_dividend_evidence(
            registry,
            row,
            attachment_dir=attachment_dir,
        )
    return registry


def _state(
    session_date: str,
    *,
    cash: float = 1_000_000.0,
    positions: tuple[PaperPosition, ...] = (),
    pending_buys: tuple[PendingPaperIntent, ...] = (),
    pending_sells: tuple[PendingPaperIntent, ...] = (),
    ledger: fd.DividendLedger | None = None,
) -> fd.DividendAwarePaperState:
    return fd.DividendAwarePaperState(
        base_state=PaperPortfolioState(
            as_of_session_date=session_date,
            cash_idr=cash,
            positions=positions,
            pending_buys=pending_buys,
            pending_sells=pending_sells,
        ),
        dividend_ledger=ledger or fd.DividendLedger(),
    )


def test_runtime_snapshot_roundtrip_binds_state_registry_and_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = _registry(tmp_path, monkeypatch, _event())
    first = runtime.write_runtime_snapshot(
        tmp_path / "runtime",
        _state("2026-08-20"),
        registry,
    )
    second_state = _state(
        "2026-08-21",
        positions=(PaperPosition("BBCA", 200),),
    )
    second = runtime.write_runtime_snapshot(
        tmp_path / "runtime",
        second_state,
        registry,
        previous_snapshot=first,
    )
    loaded = runtime.load_latest_runtime_snapshot(tmp_path / "runtime")
    assert loaded.file_sha256 == second.file_sha256
    assert loaded.previous_snapshot_sha256 == first.file_sha256
    assert loaded.runtime_state_sha256 == runtime.runtime_state_hash(
        second_state,
        registry,
    )
    assert runtime.registered_certified_events(
        loaded.certified_dividend_registry
    ) == (_event(),)


def test_same_session_identical_snapshot_is_idempotent_but_divergence_blocks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = _registry(tmp_path, monkeypatch, _event())
    state = _state("2026-08-20")
    one = runtime.write_runtime_snapshot(tmp_path / "runtime", state, registry)
    two = runtime.write_runtime_snapshot(tmp_path / "runtime", state, registry)
    assert one.file_sha256 == two.file_sha256
    with pytest.raises(DecisionV1Error, match="SNAPSHOT_SESSION_CONFLICT"):
        runtime.write_runtime_snapshot(
            tmp_path / "runtime",
            _state("2026-08-20", cash=999_000.0),
            registry,
        )


def test_snapshot_payload_tamper_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = _registry(tmp_path, monkeypatch, _event())
    snapshot = runtime.write_runtime_snapshot(
        tmp_path / "runtime",
        _state("2026-08-20"),
        registry,
    )
    payload = json.loads(snapshot.path.read_text(encoding="utf-8"))
    payload["state"]["base_paper_state"]["cash_idr"] = 2_000_000.0
    snapshot.path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(DecisionV1Error, match="PAYLOAD_SHA_MISMATCH"):
        runtime.load_runtime_snapshot(snapshot.path)


def test_parent_bytes_tamper_invalidates_child_chain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = _registry(tmp_path, monkeypatch, _event())
    first = runtime.write_runtime_snapshot(
        tmp_path / "runtime",
        _state("2026-08-20"),
        registry,
    )
    second = runtime.write_runtime_snapshot(
        tmp_path / "runtime",
        _state("2026-08-21"),
        registry,
        previous_snapshot=first,
    )
    first.path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(DecisionV1Error, match="PARENT_SHA_MISMATCH"):
        runtime.load_runtime_snapshot(second.path)


def test_review_tamper_invalidates_persisted_event_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = _registry(tmp_path, monkeypatch, _event())
    snapshot = runtime.write_runtime_snapshot(
        tmp_path / "runtime",
        _state("2026-08-20"),
        registry,
    )
    registry[0].review_path.write_text('{"tampered":true}\n', encoding="utf-8")
    with pytest.raises(DecisionV1Error, match="REVIEW_SHA_MISMATCH"):
        runtime.load_runtime_snapshot(snapshot.path)


def test_registry_event_survives_until_later_cum_session_and_creates_entitlement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = _event()
    registry = _registry(tmp_path, monkeypatch, event)
    announced = runtime.write_runtime_snapshot(
        tmp_path / "runtime",
        _state("2026-08-20"),
        registry,
    )
    cum_state = _state(
        "2026-08-28",
        positions=(PaperPosition("BBCA", 200),),
    )
    cum_snapshot = runtime.write_runtime_snapshot(
        tmp_path / "runtime",
        cum_state,
        registry,
        previous_snapshot=announced,
    )
    loaded = runtime.load_runtime_snapshot(cum_snapshot.path)
    processed = fd.process_dividend_eod(
        loaded.state,
        runtime.registered_certified_events(
            loaded.certified_dividend_registry
        ),
        session_date="2026-08-28",
    )
    assert len(processed.dividend_ledger.entitlements) == 1
    assert processed.dividend_ledger.entitlements[0].entitled_shares == 200


def test_shadow_reconstruction_uses_actual_minus_pending_sell_plus_pending_buy() -> None:
    state = _state(
        "2026-08-21",
        positions=(
            PaperPosition("AAA", 100),
            PaperPosition("BBB", 100),
        ),
        pending_sells=(
            PendingPaperIntent(
                "SELL",
                "AAA",
                21,
                "PARTIAL_EXIT_CAPACITY",
                "CCC",
            ),
        ),
        pending_buys=(
            PendingPaperIntent(
                "BUY",
                "CCC",
                1,
                "BLOCKED_BY_UNRESOLVED_PAIRED_SELL",
                "AAA",
            ),
        ),
    )
    shadow = runtime.reconstruct_decision_shadow_state(state)
    assert isinstance(shadow, DecisionV2ShadowState)
    assert shadow.as_of_session_date == "2026-08-21"
    assert shadow.positions == ("BBB", "CCC")
    assert shadow.rule_id == V4_X1_DECISION_V2_MINIMAL_PROFILE_V1.rule_id
    assert shadow.source == "DECISION_V2_MINIMAL_SHADOW_ONLY"


def test_registry_rejects_conflicting_event_for_same_ticker_and_cum(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_event = _event()
    second_event = replace(
        first_event,
        event_id="CASH_DIVIDEND_BBCA_CONFLICT",
        source_evidence_sha256="b" * 64,
    )
    attachment_dir = tmp_path / "attachments"
    attachment_dir.mkdir()
    first = _evidence(tmp_path, first_event)
    second = _evidence(tmp_path, second_event)
    _patch_verifier(monkeypatch, [first, second])
    registry = runtime.register_verified_cash_dividend_evidence(
        (),
        first,
        attachment_dir=attachment_dir,
    )
    with pytest.raises(DecisionV1Error, match="CONFLICTING_EVENT_SAME_TICKER_CUM"):
        runtime.register_verified_cash_dividend_evidence(
            registry,
            second,
            attachment_dir=attachment_dir,
        )


def test_latest_loader_rejects_forked_snapshot_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = _registry(tmp_path, monkeypatch, _event())
    first = runtime.write_runtime_snapshot(
        tmp_path / "runtime",
        _state("2026-08-20"),
        registry,
    )
    runtime.write_runtime_snapshot(
        tmp_path / "runtime",
        _state("2026-08-21"),
        registry,
        previous_snapshot=first,
    )
    # A later snapshot without the existing chain is a fork. Writing is allowed
    # as an immutable artifact, but selecting it as "latest" must fail closed.
    runtime.write_runtime_snapshot(
        tmp_path / "runtime",
        _state("2026-08-24"),
        registry,
        previous_snapshot=None,
    )
    with pytest.raises(DecisionV1Error, match="SNAPSHOT_CHAIN_FORK"):
        runtime.load_latest_runtime_snapshot(tmp_path / "runtime")


def _entitlement(event: fd.CertifiedCashDividend, shares: int = 200) -> fd.PaperDividendEntitlement:
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


def test_child_snapshot_cannot_drop_registered_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = _event()
    registry = _registry(tmp_path, monkeypatch, event)
    first = runtime.write_runtime_snapshot(
        tmp_path / "runtime",
        _state("2026-08-20"),
        registry,
    )
    with pytest.raises(DecisionV1Error, match="REGISTRY_NOT_APPEND_ONLY"):
        runtime.write_runtime_snapshot(
            tmp_path / "runtime",
            _state("2026-08-21"),
            (),
            previous_snapshot=first,
        )


def test_ledger_entitlement_requires_matching_registered_event(
    tmp_path: Path,
) -> None:
    event = _event()
    state = _state(
        "2026-08-28",
        positions=(PaperPosition("BBCA", 200),),
        ledger=fd.DividendLedger(entitlements=(_entitlement(event),)),
    )
    with pytest.raises(DecisionV1Error, match="LEDGER_EVENT_NOT_REGISTERED"):
        runtime.write_runtime_snapshot(tmp_path / "runtime", state, ())


def test_receivable_cannot_disappear_between_parent_and_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = _event()
    registry = _registry(tmp_path, monkeypatch, event)
    entitlement = _entitlement(event)
    receivable = fd.PaperDividendReceivable(
        event_id=event.event_id,
        ticker=event.ticker,
        entitled_shares=200,
        gross_dividend_per_share_idr=25.0,
        gross_amount_idr=5_000.0,
        payment_date=event.payment_date,
        source_evidence_sha256=event.source_evidence_sha256,
    )
    parent = runtime.write_runtime_snapshot(
        tmp_path / "runtime",
        _state(
            "2026-08-31",
            ledger=fd.DividendLedger(
                entitlements=(entitlement,),
                receivables=(receivable,),
            ),
        ),
        registry,
    )
    with pytest.raises(DecisionV1Error, match="RECEIVABLE_DISAPPEARED"):
        runtime.write_runtime_snapshot(
            tmp_path / "runtime",
            _state(
                "2026-09-01",
                ledger=fd.DividendLedger(entitlements=(entitlement,)),
            ),
            registry,
            previous_snapshot=parent,
        )


def test_receivable_may_progress_exactly_once_to_settlement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = _event()
    registry = _registry(tmp_path, monkeypatch, event)
    entitlement = _entitlement(event)
    receivable = fd.PaperDividendReceivable(
        event_id=event.event_id,
        ticker=event.ticker,
        entitled_shares=200,
        gross_dividend_per_share_idr=25.0,
        gross_amount_idr=5_000.0,
        payment_date=event.payment_date,
        source_evidence_sha256=event.source_evidence_sha256,
    )
    parent = runtime.write_runtime_snapshot(
        tmp_path / "runtime",
        _state(
            "2026-08-31",
            ledger=fd.DividendLedger(
                entitlements=(entitlement,),
                receivables=(receivable,),
            ),
        ),
        registry,
    )
    settlement = fd.PaperDividendSettlement(
        event_id=event.event_id,
        ticker=event.ticker,
        entitled_shares=200,
        gross_amount_idr=5_000.0,
        payment_date=event.payment_date,
        settled_on_session_date="2026-09-16",
        source_evidence_sha256=event.source_evidence_sha256,
    )
    child = runtime.write_runtime_snapshot(
        tmp_path / "runtime",
        _state(
            "2026-09-16",
            cash=1_005_000.0,
            ledger=fd.DividendLedger(
                entitlements=(entitlement,),
                settlements=(settlement,),
            ),
        ),
        registry,
        previous_snapshot=parent,
    )
    loaded = runtime.load_runtime_snapshot(child.path)
    assert len(loaded.state.dividend_ledger.receivables) == 0
    assert len(loaded.state.dividend_ledger.settlements) == 1



def _decision_rank_session(
    session_date: str,
    ordered_tickers: tuple[str, ...],
) -> RankSession:
    return RankSession(
        session_date=session_date,
        rows=tuple(
            RankObservation(ticker=ticker, rank=rank)
            for rank, ticker in enumerate(ordered_tickers, start=1)
        ),
    )


def test_reconstructed_shadow_is_accepted_by_decision_v2_planner() -> None:
    state = _state(
        "2026-08-21",
        positions=(
            PaperPosition("BBB", 100),
            PaperPosition("CCC", 100),
        ),
    )

    shadow = runtime.reconstruct_decision_shadow_state(state)

    previous = _decision_rank_session(
        "2026-08-21",
        (
            "BBB",
            "DDD",
            "EEE",
            "FFF",
            "GGG",
            "HHH",
            "III",
            "JJJ",
            "KKK",
            "CCC",
            "LLL",
            "MMM",
        ),
    )
    current = _decision_rank_session(
        "2026-08-24",
        (
            "BBB",
            "DDD",
            "EEE",
            "FFF",
            "GGG",
            "HHH",
            "III",
            "JJJ",
            "KKK",
            "CCC",
            "LLL",
            "MMM",
        ),
    )

    plan = plan_decision_v2_minimal(
        current,
        previous,
        shadow,
        V4_X1_DECISION_V2_MINIMAL_PROFILE_V1,
    )

    assert plan.current_shadow_positions == ("BBB", "CCC")
    assert plan.rule_id == V4_X1_DECISION_V2_MINIMAL_PROFILE_V1.rule_id
    assert plan.bootstrap is False


def test_reconstructed_shadow_fails_closed_above_v2_target_count() -> None:
    positions = tuple(
        PaperPosition(f"T{i:02d}", 100)
        for i in range(10)
    )
    state = _state(
        "2026-08-21",
        positions=positions,
        pending_buys=(
            PendingPaperIntent(
                "BUY",
                "T10",
                1,
                "TEST_PENDING_BUY",
                None,
            ),
        ),
    )

    with pytest.raises(
        DecisionV1Error,
        match="DIVIDEND_V1_1_RUNTIME_SHADOW_OVER_TARGET",
    ):
        runtime.reconstruct_decision_shadow_state(state)
