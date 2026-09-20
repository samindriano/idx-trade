from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from idx_trade import forward_dividend_v1 as dividend
from idx_trade import forward_dividend_runtime_v1_1 as dividend_runtime
from idx_trade.e2e_paper_orchestration_v1 import (
    E2EPaperOrchestrationError,
    INITIAL_NAV_IDR,
    _reconciliation_payload,
    _verify_prepared_ca_parent,
    _load_latest_state,
    E2EPaperPaths,
    execute_preopen,
    bootstrap_t0,
    prepare_post_eod,
)
from idx_trade.e2e_paper_continuity_v1 import (
    MISSED_STATUS,
    advance_missed_execution_no_certified_open,
)
from idx_trade.forward_dividend_execution_v1_1 import (
    VerifiedCashDividendEvidence,
    VerifiedDividendCAReconciliation,
    _VERIFIED_DIVIDEND_EVIDENCE_TOKEN,
)
from idx_trade.v4_x1_decision_v1_contract import (
    EXPECTED_ALPHA_MODEL_FINGERPRINT,
    EXPECTED_ALPHA_MODEL_ID,
    VerifiedScoreSession,
    _VERIFIED_TOKEN,
)
from idx_trade.v4_x1_execution_v1_verify import (
    VerifiedCorporateActionAttestation,
    VerifiedEODExecutionInputs,
    VerifiedOpenExecutionInputs,
    _CA_ATTESTATION_TOKEN,
    _EOD_INPUT_TOKEN,
    _OPEN_INPUT_TOKEN,
)
from idx_trade.v4_x1_identity_contract_v1 import SecurityIdentityV1
from idx_trade.forward_dividend_execution_v1_1 import _DIVIDEND_RECONCILIATION_TOKEN
from idx_trade.official_open_evidence_v1 import (
    AUTHORITY as OFFICIAL_OPEN_AUTHORITY,
    FALLBACK_POLICY as OFFICIAL_OPEN_FALLBACK_POLICY,
    FIELD_SEMANTICS as OFFICIAL_OPEN_FIELD_SEMANTICS,
    TRANSPORT_POLICY as OFFICIAL_OPEN_TRANSPORT_POLICY,
    UPSTREAM_PATH as OFFICIAL_OPEN_UPSTREAM_PATH,
)
from idx_trade.e2e_operational_guard_v1 import JAKARTA


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_hash(value: object) -> str:
    raw = (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _score(tmp_path: Path, session: str, offset: int) -> VerifiedScoreSession:
    tickers = [f"T{index:02d}" for index in range(11)]
    frame = pd.DataFrame(
        {
            "ticker": tickers,
            "date": [session] * len(tickers),
            "alpha_h5": [float(11 - index) for index in range(11)],
            "alpha_h10": [float(11 - index) for index in range(11)],
            "alpha_consensus": [float(11 - index) for index in range(11)],
            "rank_consensus": list(range(1, 12)),
        }
    )
    artifact = tmp_path / f"score-{offset}.parquet"
    manifest = tmp_path / f"score-{offset}.json"
    frame.to_parquet(artifact, index=False)
    manifest.write_text("{}\n", encoding="utf-8")
    return VerifiedScoreSession(
        session_date=session,
        model_id=EXPECTED_ALPHA_MODEL_ID,
        model_fingerprint=EXPECTED_ALPHA_MODEL_FINGERPRINT,
        artifact_path=artifact,
        artifact_sha256=_sha(artifact),
        manifest_path=manifest,
        manifest_sha256=_sha(manifest),
        scores=frame,
        alpha_tie_rows=0,
        _verification_token=_VERIFIED_TOKEN,
    )


def _eod(tmp_path: Path, session: str, next_session: str, tickers: list[str]) -> VerifiedEODExecutionInputs:
    ohlcv = tmp_path / f"ohlcv-{session}.parquet"
    model = tmp_path / f"model-{session}.parquet"
    calendar = tmp_path / f"calendar-{session}.csv"
    closes = {ticker: 1000.0 + index for index, ticker in enumerate(tickers)}
    pd.DataFrame(
        {
            "ticker": tickers,
            "session_date": [session] * len(tickers),
            "close": [closes[ticker] for ticker in tickers],
        }
    ).to_parquet(ohlcv, index=False)
    pd.DataFrame(
        {
            "ticker": tickers,
            "date": [session] * len(tickers),
            "close": [closes[ticker] for ticker in tickers],
            "regular_market_value": [1_000_000_000.0] * len(tickers),
        }
    ).to_parquet(model, index=False)
    pd.DataFrame({"date": [session, next_session]}).to_csv(calendar, index=False)
    return VerifiedEODExecutionInputs(
        session_date=session,
        next_official_session_date=next_session,
        raw_close_prices=closes,
        regular_market_values={ticker: 1_000_000_000.0 for ticker in tickers},
        ohlcv_artifact_path=ohlcv,
        ohlcv_artifact_sha256=_sha(ohlcv),
        model_input_path=model,
        model_input_sha256=_sha(model),
        official_calendar_path=calendar,
        official_calendar_sha256=_sha(calendar),
        _verification_token=_EOD_INPUT_TOKEN,
    )


def _ca(tmp_path: Path, session: str, next_session: str, tickers: list[str]) -> VerifiedDividendCAReconciliation:
    attestation = tmp_path / f"ca-{session}.json"
    source = tmp_path / f"ca-source-{session}.json"
    attestation.write_text("{}\n", encoding="utf-8")
    source.write_text("{}\n", encoding="utf-8")
    legacy = VerifiedCorporateActionAttestation(
        from_session_date=session,
        through_session_date=next_session,
        covered_tickers=frozenset(tickers),
        status="NO_RELEVANT_EVENTS",
        attestation_path=attestation,
        attestation_sha256=_sha(attestation),
        source_path=source,
        source_sha256=_sha(source),
        _verification_token=_CA_ATTESTATION_TOKEN,
    )
    return VerifiedDividendCAReconciliation(
        from_session_date=session,
        through_session_date=next_session,
        covered_tickers=frozenset(tickers),
        original_status="NO_RELEVANT_EVENTS",
        relevant_tickers=frozenset(),
        certified_events=(),
        legacy_attestation=legacy,
        attestation_path=attestation,
        attestation_sha256=_sha(attestation),
        source_path=source,
        source_sha256=_sha(source),
        _verification_token=_DIVIDEND_RECONCILIATION_TOKEN,
    )


def _ca_with_event(
    tmp_path: Path,
    session: str,
    next_session: str,
    tickers: list[str],
) -> VerifiedDividendCAReconciliation:
    base = _ca(tmp_path, session, next_session, tickers)
    event = dividend.CertifiedCashDividend(
        event_id="DIV-T00",
        ticker="T00",
        announcement_timestamp="2026-08-20T10:00:00",
        gross_dividend_per_share_idr=25.0,
        cum_date="2026-08-25",
        ex_date="2026-08-26",
        record_date="2026-08-27",
        payment_date="2026-08-27",
        source_evidence_sha256="d" * 64,
    )
    return replace(
        base,
        original_status="CERTIFIED_LIVE",
        relevant_tickers=frozenset({"T00"}),
        certified_events=(event,),
    )


def _open(tmp_path: Path, session: str, tickers: list[str]) -> VerifiedOpenExecutionInputs:
    artifact = tmp_path / f"open-{session}.parquet"
    artifact.write_bytes(b"certified-open")
    return VerifiedOpenExecutionInputs(
        session_date=session,
        raw_open_prices={ticker: 1000.0 for ticker in tickers},
        available_tickers=frozenset(tickers),
        ohlcv_artifact_path=artifact,
        ohlcv_artifact_sha256=_sha(artifact),
        _verification_token=_OPEN_INPUT_TOKEN,
        authority=OFFICIAL_OPEN_AUTHORITY,
        upstream_path=OFFICIAL_OPEN_UPSTREAM_PATH,
        field_semantics=OFFICIAL_OPEN_FIELD_SEMANTICS,
        fallback_policy=OFFICIAL_OPEN_FALLBACK_POLICY,
        transport="DIRECT_IDX_HTTPS",
        transport_policy=OFFICIAL_OPEN_TRANSPORT_POLICY,
    )


def test_t0_post_eod_preopen_is_atomic_and_idempotent(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    tickers = [f"T{index:02d}" for index in range(11)]
    current = _score(tmp_path, "2026-08-24", 0)
    eod = _eod(tmp_path, "2026-08-24", "2026-08-25", tickers)
    ca = _ca(tmp_path, "2026-08-24", "2026-08-25", tickers)
    prepared = prepare_post_eod(root, current_score=current, previous_score=None, eod_inputs=eod, ca_reconciliation=ca)
    prepared_payload = json.loads(prepared.path.read_text(encoding="utf-8"))
    assert prepared_payload["runtime_lineage"]["role"] == "PREPARED_EXECUTION"
    assert prepared_payload["runtime_lineage"]["binding_status"] == "LOCAL_UNBOUND"
    result = execute_preopen(root, prepared_path=prepared.path, current_score=current, previous_score=None, eod_inputs=eod, open_inputs=_open(tmp_path, "2026-08-25", tickers), ca_reconciliation=ca)
    assert result.status == "EXECUTION_COMPLETE"
    execution_payload = json.loads(result.path.read_text(encoding="utf-8"))
    assert execution_payload["runtime_lineage"]["role"] == "EXECUTION_RESULT"
    assert execution_payload["execution_evidence"]["schema_version"] == "idx_trade_execution_evidence_v2"
    assert execution_payload["reconciliation_result"]["status"] == "PASS_INTERNAL_PAPER"
    rerun = execute_preopen(root, prepared_path=prepared.path, current_score=current, previous_score=None, eod_inputs=eod, open_inputs=_open(tmp_path, "2026-08-25", tickers), ca_reconciliation=ca)
    assert rerun.status == "ALREADY_COMPLETE"
    assert result.file_sha256 == rerun.file_sha256


def test_bound_runtime_lineage_survives_execution_and_rejects_config_mismatch(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    tickers = [f"T{index:02d}" for index in range(11)]
    current = _score(tmp_path, "2026-08-24", 0)
    eod = _eod(tmp_path, "2026-08-24", "2026-08-25", tickers)
    ca = _ca(tmp_path, "2026-08-24", "2026-08-25", tickers)
    bound = {
        "implementation_branch": "codex/runtime-bound-test",
        "implementation_commit": "a" * 40,
        "runtime_config_sha256": "b" * 64,
        "entrypoint_sha256": "c" * 64,
    }
    prepared = prepare_post_eod(
        root,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        ca_reconciliation=ca,
        **bound,
    )
    prepared_payload = json.loads(prepared.path.read_text(encoding="utf-8"))
    assert prepared_payload["runtime_lineage"]["binding_status"] == "BOUND"
    result = execute_preopen(
        root,
        prepared_path=prepared.path,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        open_inputs=_open(tmp_path, "2026-08-25", tickers),
        ca_reconciliation=ca,
        **bound,
    )
    execution_payload = json.loads(result.path.read_text(encoding="utf-8"))
    assert execution_payload["runtime_lineage"]["binding_status"] == "BOUND"
    with pytest.raises(E2EPaperOrchestrationError, match="RUNTIME_LINEAGE_CONFIG_MISMATCH"):
        execute_preopen(
            root,
            prepared_path=prepared.path,
            current_score=current,
            previous_score=None,
            eod_inputs=eod,
            open_inputs=_open(tmp_path, "2026-08-25", tickers),
            ca_reconciliation=ca,
            **{**bound, "runtime_config_sha256": "d" * 64},
        )


def test_identity_evidence_is_required_and_revalidated_on_orchestration_replay(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    tickers = [f"T{index:02d}" for index in range(11)]
    identities = tuple(
        SecurityIdentityV1(
            canonical_security_id=f"ISSUER-{ticker}",
            ticker=ticker,
            instrument_class="COMMON_SHARE",
            effective_from="2020-01-01",
            effective_to=None,
            identity_revision="R1",
            source_ref=f"synthetic://identity/{ticker}",
            source_evidence_sha256="a" * 64,
        )
        for ticker in tickers
    )
    current = _score(tmp_path, "2026-08-24", 0)
    eod = _eod(tmp_path, "2026-08-24", "2026-08-25", tickers)
    ca = _ca(tmp_path, "2026-08-24", "2026-08-25", tickers)
    prepared = prepare_post_eod(
        root,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        ca_reconciliation=ca,
        security_identities=identities,
    )
    prepared_payload = json.loads(prepared.path.read_text(encoding="utf-8"))
    assert prepared_payload["decision_identity_binding"]["binding_type"] == (
        "DECISION_IDENTITY"
    )
    execute_preopen(
        root,
        prepared_path=prepared.path,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        open_inputs=_open(tmp_path, "2026-08-25", tickers),
        ca_reconciliation=ca,
        security_identities=identities,
    )
    with pytest.raises(
        E2EPaperOrchestrationError,
        match="E2E_DECISION_IDENTITY_EVIDENCE_REQUIRED_FOR_REPLAY",
    ):
        execute_preopen(
            root,
            prepared_path=prepared.path,
            current_score=current,
            previous_score=None,
            eod_inputs=eod,
            open_inputs=_open(tmp_path, "2026-08-25", tickers),
            ca_reconciliation=ca,
        )
    tampered = list(identities)
    tampered[0] = replace(tampered[0], source_evidence_sha256="b" * 64)
    with pytest.raises(
        E2EPaperOrchestrationError,
        match="E2E_DECISION_IDENTITY_BINDING_INVALID",
    ):
        execute_preopen(
            root,
            prepared_path=prepared.path,
            current_score=current,
            previous_score=None,
            eod_inputs=eod,
            open_inputs=_open(tmp_path, "2026-08-25", tickers),
            ca_reconciliation=ca,
            security_identities=tuple(tampered),
        )


def test_orchestration_state_loader_recovers_verified_snapshot_ancestor(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    first = dividend_runtime.load_latest_runtime_snapshot(root)
    second_state = replace(
        first.state,
        base_state=replace(first.state.base_state, as_of_session_date="2026-08-25"),
    )
    second = dividend_runtime.write_runtime_snapshot(
        root,
        second_state,
        (),
        previous_snapshot=first,
    )
    tampered = json.loads(second.path.read_text(encoding="utf-8"))
    tampered["state"]["base_paper_state"]["cash_idr"] = 1.0
    second.path.write_text(json.dumps(tampered), encoding="utf-8")

    recovered = _load_latest_state(E2EPaperPaths.from_root(root))
    assert recovered.base_state.as_of_session_date == "2026-08-24"
    quarantine_manifest = (
        root
        / dividend_runtime.RUNTIME_DIRNAME
        / dividend_runtime.SNAPSHOT_DIRNAME
        / dividend_runtime.QUARANTINE_DIRNAME
        / dividend_runtime.QUARANTINE_MANIFEST_FILENAME
    )
    assert quarantine_manifest.is_file()


def test_existing_execution_rejects_forged_ca_reconciliation_token(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    tickers = [f"T{index:02d}" for index in range(11)]
    current = _score(tmp_path, "2026-08-24", 0)
    eod = _eod(tmp_path, "2026-08-24", "2026-08-25", tickers)
    ca = _ca(tmp_path, "2026-08-24", "2026-08-25", tickers)
    prepared = prepare_post_eod(
        root,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        ca_reconciliation=ca,
    )
    execute_preopen(
        root,
        prepared_path=prepared.path,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        open_inputs=_open(tmp_path, "2026-08-25", tickers),
        ca_reconciliation=ca,
    )
    forged = replace(ca, _verification_token=object())
    with pytest.raises(
        E2EPaperOrchestrationError,
        match="VERIFIED_CA_RECONCILIATION_TOKEN_INVALID",
    ):
        execute_preopen(
            root,
            prepared_path=prepared.path,
            current_score=current,
            previous_score=None,
            eod_inputs=eod,
            open_inputs=_open(tmp_path, "2026-08-25", tickers),
            ca_reconciliation=forged,
        )


def test_t0_is_idempotent_and_rejects_divergent_inputs(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    first = bootstrap_t0(root, session_date="2026-08-24")
    first_bytes = first.read_bytes()
    second = bootstrap_t0(root, session_date="2026-08-24")
    assert second == first
    assert second.read_bytes() == first_bytes
    with pytest.raises(E2EPaperOrchestrationError, match="T0_INITIAL_NAV_CHANGED"):
        bootstrap_t0(root, session_date="2026-08-24", initial_nav_idr=1.0)


def test_t0_fails_before_mutation_when_runtime_snapshot_preexists(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    snapshot_dir = root / "forward_execution_v1_1" / "state_snapshots"
    snapshot_dir.mkdir(parents=True)
    sentinel = snapshot_dir / "2026-08-24.json"
    sentinel.write_bytes(b"preexisting-runtime-state\n")
    with pytest.raises(E2EPaperOrchestrationError, match="T0_PREEXISTING_RUNTIME_STATE"):
        bootstrap_t0(root, session_date="2026-08-24")
    assert not (root / "state" / "T0.json").exists()
    assert sentinel.read_bytes() == b"preexisting-runtime-state\n"


def test_t0_conflict_does_not_mutate_canonical_root(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    snapshot = root / "forward_execution_v1_1" / "state_snapshots" / "2026-08-24.json"
    before = snapshot.read_bytes()
    with pytest.raises(E2EPaperOrchestrationError, match="T0_ROOT_CONFLICT"):
        bootstrap_t0(root, session_date="2026-08-25")
    assert snapshot.read_bytes() == before


def test_next_session_uses_persisted_score_parent_and_shadow(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    tickers = [f"T{index:02d}" for index in range(11)]
    first = _score(tmp_path, "2026-08-24", 0)
    eod_first = _eod(tmp_path, "2026-08-24", "2026-08-25", tickers)
    ca_first = _ca(tmp_path, "2026-08-24", "2026-08-25", tickers)
    prepared_first = prepare_post_eod(root, current_score=first, previous_score=None, eod_inputs=eod_first, ca_reconciliation=ca_first)
    execute_preopen(root, prepared_path=prepared_first.path, current_score=first, previous_score=None, eod_inputs=eod_first, open_inputs=_open(tmp_path, "2026-08-25", tickers), ca_reconciliation=ca_first)

    second = _score(tmp_path, "2026-08-25", 1)
    eod_second = _eod(tmp_path, "2026-08-25", "2026-08-26", tickers)
    ca_second = _ca(tmp_path, "2026-08-25", "2026-08-26", tickers)
    prepared_second = prepare_post_eod(root, current_score=second, previous_score=first, eod_inputs=eod_second, ca_reconciliation=ca_second)
    result = execute_preopen(root, prepared_path=prepared_second.path, current_score=second, previous_score=first, eod_inputs=eod_second, open_inputs=_open(tmp_path, "2026-08-26", tickers), ca_reconciliation=ca_second)
    assert result.status == "EXECUTION_COMPLETE"


def test_next_session_rejects_tampered_previous_score_sha(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    tickers = [f"T{index:02d}" for index in range(11)]
    first = _score(tmp_path, "2026-08-24", 0)
    eod_first = _eod(tmp_path, "2026-08-24", "2026-08-25", tickers)
    ca_first = _ca(tmp_path, "2026-08-24", "2026-08-25", tickers)
    prepared_first = prepare_post_eod(
        root,
        current_score=first,
        previous_score=None,
        eod_inputs=eod_first,
        ca_reconciliation=ca_first,
    )
    execute_preopen(
        root,
        prepared_path=prepared_first.path,
        current_score=first,
        previous_score=None,
        eod_inputs=eod_first,
        open_inputs=_open(tmp_path, "2026-08-25", tickers),
        ca_reconciliation=ca_first,
    )
    meta_path = next((root / "state" / "decisions").glob("*.json"))
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["last_score_manifest_sha256"] = "0" * 64
    body = dict(meta)
    body.pop("payload_sha256", None)
    meta["payload_sha256"] = _canonical_hash(body)
    meta_path.write_text(json.dumps(meta, sort_keys=True) + "\n", encoding="utf-8")

    second = _score(tmp_path, "2026-08-25", 1)
    with pytest.raises(E2EPaperOrchestrationError, match="PREVIOUS_SCORE_SHA_MISMATCH"):
        prepare_post_eod(
            root,
            current_score=second,
            previous_score=first,
            eod_inputs=_eod(tmp_path, "2026-08-25", "2026-08-26", tickers),
            ca_reconciliation=_ca(tmp_path, "2026-08-25", "2026-08-26", tickers),
        )


def test_next_session_rejects_deleted_previous_execution_artifact(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    tickers = [f"T{index:02d}" for index in range(11)]
    first_score = _score(tmp_path, "2026-08-24", 0)
    first_eod = _eod(tmp_path, "2026-08-24", "2026-08-25", tickers)
    first_ca = _ca(tmp_path, "2026-08-24", "2026-08-25", tickers)
    first_prepared = prepare_post_eod(
        root,
        current_score=first_score,
        previous_score=None,
        eod_inputs=first_eod,
        ca_reconciliation=first_ca,
    )
    first_result = execute_preopen(
        root,
        prepared_path=first_prepared.path,
        current_score=first_score,
        previous_score=None,
        eod_inputs=first_eod,
        open_inputs=_open(tmp_path, "2026-08-25", tickers),
        ca_reconciliation=first_ca,
    )
    first_result.path.unlink()

    second_score = _score(tmp_path, "2026-08-25", 1)
    second_eod = _eod(tmp_path, "2026-08-25", "2026-08-26", tickers)
    second_ca = _ca(tmp_path, "2026-08-25", "2026-08-26", tickers)
    with pytest.raises(
        E2EPaperOrchestrationError,
        match="PREVIOUS_EXECUTION_PARENT_MISSING_OR_TAMPERED",
    ):
        prepare_post_eod(
            root,
            current_score=second_score,
            previous_score=first_score,
            eod_inputs=second_eod,
            ca_reconciliation=second_ca,
        )


def test_preopen_rejects_open_provenance_tamper(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    tickers = [f"T{index:02d}" for index in range(11)]
    current = _score(tmp_path, "2026-08-24", 0)
    eod = _eod(tmp_path, "2026-08-24", "2026-08-25", tickers)
    ca = _ca(tmp_path, "2026-08-24", "2026-08-25", tickers)
    prepared = prepare_post_eod(
        root,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        ca_reconciliation=ca,
    )
    tampered = replace(_open(tmp_path, "2026-08-25", tickers), authority="OTHER")
    with pytest.raises(E2EPaperOrchestrationError, match="E2E_OPEN_PROVENANCE_INVALID:authority"):
        execute_preopen(
            root,
            prepared_path=prepared.path,
            current_score=current,
            previous_score=None,
            eod_inputs=eod,
            open_inputs=tampered,
            ca_reconciliation=ca,
        )


def test_preopen_rejects_changed_eod_parent(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    tickers = [f"T{index:02d}" for index in range(11)]
    current = _score(tmp_path, "2026-08-24", 0)
    eod = _eod(tmp_path, "2026-08-24", "2026-08-25", tickers)
    ca = _ca(tmp_path, "2026-08-24", "2026-08-25", tickers)
    prepared = prepare_post_eod(
        root,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        ca_reconciliation=ca,
    )
    eod.ohlcv_artifact_path.write_bytes(b"changed-after-prepare")
    with pytest.raises(E2EPaperOrchestrationError, match="E2E_EOD_OHLCV_SHA_MISMATCH"):
        execute_preopen(
            root,
            prepared_path=prepared.path,
            current_score=current,
            previous_score=None,
            eod_inputs=eod,
            open_inputs=_open(tmp_path, "2026-08-25", tickers),
            ca_reconciliation=ca,
        )


def test_preopen_recovers_after_snapshot_before_execution_commit(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    tickers = [f"T{index:02d}" for index in range(11)]
    current = _score(tmp_path, "2026-08-24", 0)
    eod = _eod(tmp_path, "2026-08-24", "2026-08-25", tickers)
    ca = _ca(tmp_path, "2026-08-24", "2026-08-25", tickers)
    prepared = prepare_post_eod(
        root,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        ca_reconciliation=ca,
    )
    completed = execute_preopen(
        root,
        prepared_path=prepared.path,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        open_inputs=_open(tmp_path, "2026-08-25", tickers),
        ca_reconciliation=ca,
    )
    completed.path.unlink()
    recovered = execute_preopen(
        root,
        prepared_path=prepared.path,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        open_inputs=_open(tmp_path, "2026-08-25", tickers),
        ca_reconciliation=ca,
    )
    assert recovered.status == "RECOVERED_STAGED_EXECUTION"
    assert recovered.file_sha256 == completed.file_sha256


def test_preopen_replay_rejects_nested_evidence_parent_tamper(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    tickers = [f"T{index:02d}" for index in range(11)]
    current = _score(tmp_path, "2026-08-24", 0)
    eod = _eod(tmp_path, "2026-08-24", "2026-08-25", tickers)
    ca = _ca(tmp_path, "2026-08-24", "2026-08-25", tickers)
    prepared = prepare_post_eod(
        root,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        ca_reconciliation=ca,
    )
    completed = execute_preopen(
        root,
        prepared_path=prepared.path,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        open_inputs=_open(tmp_path, "2026-08-25", tickers),
        ca_reconciliation=ca,
    )
    payload = json.loads(completed.path.read_text(encoding="utf-8"))
    payload["execution_evidence"]["gross_turnover_idr"] = 1.0
    body = dict(payload)
    body.pop("payload_sha256", None)
    payload["payload_sha256"] = _canonical_hash(body)
    completed.path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    with pytest.raises(
        E2EPaperOrchestrationError,
        match="E2E_EXISTING_EXECUTION_EVIDENCE_PARENT_HASH_MISMATCH",
    ):
        execute_preopen(
            root,
            prepared_path=prepared.path,
            current_score=current,
            previous_score=None,
            eod_inputs=eod,
            open_inputs=_open(tmp_path, "2026-08-25", tickers),
            ca_reconciliation=ca,
        )


def test_preopen_replay_rejects_rehashed_lineage_contract_tamper(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    tickers = [f"T{index:02d}" for index in range(11)]
    current = _score(tmp_path, "2026-08-24", 0)
    eod = _eod(tmp_path, "2026-08-24", "2026-08-25", tickers)
    ca = _ca(tmp_path, "2026-08-24", "2026-08-25", tickers)
    prepared = prepare_post_eod(
        root,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        ca_reconciliation=ca,
    )
    completed = execute_preopen(
        root,
        prepared_path=prepared.path,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        open_inputs=_open(tmp_path, "2026-08-25", tickers),
        ca_reconciliation=ca,
    )
    payload = json.loads(completed.path.read_text(encoding="utf-8"))
    lineage = payload["runtime_lineage"]
    lineage["contracts"]["ca_timing_matrix_sha256"] = "0" * 64
    lineage_body = dict(lineage)
    lineage_body.pop("lineage_sha256", None)
    lineage["lineage_sha256"] = _canonical_hash(lineage_body)
    body = dict(payload)
    body.pop("payload_sha256", None)
    payload["payload_sha256"] = _canonical_hash(body)
    completed.path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    with pytest.raises(
        E2EPaperOrchestrationError,
        match="E2E_EXISTING_EXECUTION_RUNTIME_LINEAGE_CONTRACT_MISMATCH:ca_timing_matrix_sha256",
    ):
        execute_preopen(
            root,
            prepared_path=prepared.path,
            current_score=current,
            previous_score=None,
            eod_inputs=eod,
            open_inputs=_open(tmp_path, "2026-08-25", tickers),
            ca_reconciliation=ca,
        )


def test_preopen_replay_rejects_rehashed_reconciliation_ca_tamper(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    tickers = [f"T{index:02d}" for index in range(11)]
    current = _score(tmp_path, "2026-08-24", 0)
    eod = _eod(tmp_path, "2026-08-24", "2026-08-25", tickers)
    ca = _ca(tmp_path, "2026-08-24", "2026-08-25", tickers)
    prepared = prepare_post_eod(
        root,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        ca_reconciliation=ca,
    )
    completed = execute_preopen(
        root,
        prepared_path=prepared.path,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        open_inputs=_open(tmp_path, "2026-08-25", tickers),
        ca_reconciliation=ca,
    )
    payload = json.loads(completed.path.read_text(encoding="utf-8"))
    reconciliation = payload["reconciliation_result"]
    reconciliation["ca_source_sha256"] = "0" * 64
    reconciliation_body = dict(reconciliation)
    reconciliation_body.pop("payload_sha256", None)
    reconciliation["payload_sha256"] = _canonical_hash(reconciliation_body)
    lineage = payload["runtime_lineage"]
    lineage["artifacts"]["reconciliation_result"]["sha256"] = reconciliation[
        "payload_sha256"
    ]
    lineage_body = dict(lineage)
    lineage_body.pop("lineage_sha256", None)
    lineage["lineage_sha256"] = _canonical_hash(lineage_body)
    body = dict(payload)
    body.pop("payload_sha256", None)
    payload["payload_sha256"] = _canonical_hash(body)
    completed.path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    with pytest.raises(
        E2EPaperOrchestrationError,
        match="E2E_EXISTING_EXECUTION_RECONCILIATION_CA_PARENT_MISMATCH:ca_source_sha256",
    ):
        execute_preopen(
            root,
            prepared_path=prepared.path,
            current_score=current,
            previous_score=None,
            eod_inputs=eod,
            open_inputs=_open(tmp_path, "2026-08-25", tickers),
            ca_reconciliation=ca,
        )


@pytest.mark.parametrize(
    ("tamper_kind", "expected_error"),
    (
        ("cause_id", "E2E_EXISTING_EXECUTION_CAUSE_BINDING_ROWS_MISMATCH"),
        ("join_content", "E2E_EXISTING_EXECUTION_CAUSE_BINDING_CONTENT_MISMATCH"),
        (
            "obligation_payload",
            "E2E_EXISTING_EXECUTION_CAUSE_BINDING_CONTENT_MISMATCH",
        ),
    ),
)
def test_preopen_replay_rejects_rehashed_cause_binding_tamper(
    tmp_path: Path,
    tamper_kind: str,
    expected_error: str,
) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    tickers = [f"T{index:02d}" for index in range(11)]
    current = _score(tmp_path, "2026-08-24", 0)
    eod = _eod(tmp_path, "2026-08-24", "2026-08-25", tickers)
    ca = _ca(tmp_path, "2026-08-24", "2026-08-25", tickers)
    prepared = prepare_post_eod(
        root,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        ca_reconciliation=ca,
    )
    completed = execute_preopen(
        root,
        prepared_path=prepared.path,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        open_inputs=_open(tmp_path, "2026-08-25", tickers),
        ca_reconciliation=ca,
    )
    payload = json.loads(completed.path.read_text(encoding="utf-8"))
    evidence = payload["execution_evidence"]
    assert evidence["causes"]
    binding = evidence["cause_obligation_binding"]
    assert binding["joins"]
    if tamper_kind == "cause_id":
        evidence["causes"][0]["cause_id"] = "0" * 64
    elif tamper_kind == "join_content":
        binding["joins"][0]["remaining_shares"] = (
            int(binding["joins"][0]["remaining_shares"]) + 1
        )
    else:
        evidence["state_after"]["obligations"][0][
            "unexpected_extension"
        ] = "accepted-by-hash-only"
    binding_body = dict(binding)
    binding_body.pop("payload_sha256", None)
    binding["payload_sha256"] = _canonical_hash(binding_body)
    evidence_body = dict(evidence)
    evidence_body.pop("payload_sha256", None)
    evidence["payload_sha256"] = _canonical_hash(evidence_body)
    reconciliation = payload["reconciliation_result"]
    reconciliation["execution_evidence_sha256"] = _canonical_hash(evidence)
    reconciliation_body = dict(reconciliation)
    reconciliation_body.pop("payload_sha256", None)
    reconciliation["payload_sha256"] = _canonical_hash(reconciliation_body)
    lineage = payload["runtime_lineage"]
    lineage["artifacts"]["execution_evidence"]["sha256"] = evidence[
        "payload_sha256"
    ]
    lineage["artifacts"]["reconciliation_result"]["sha256"] = reconciliation[
        "payload_sha256"
    ]
    lineage_body = dict(lineage)
    lineage_body.pop("lineage_sha256", None)
    lineage["lineage_sha256"] = _canonical_hash(lineage_body)
    body = dict(payload)
    body.pop("payload_sha256", None)
    payload["payload_sha256"] = _canonical_hash(body)
    completed.path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    with pytest.raises(
        E2EPaperOrchestrationError,
        match=expected_error,
    ):
        execute_preopen(
            root,
            prepared_path=prepared.path,
            current_score=current,
            previous_score=None,
            eod_inputs=eod,
            open_inputs=_open(tmp_path, "2026-08-25", tickers),
            ca_reconciliation=ca,
        )


def test_preopen_recovers_when_execution_and_snapshot_are_missing(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    tickers = [f"T{index:02d}" for index in range(11)]
    current = _score(tmp_path, "2026-08-24", 0)
    eod = _eod(tmp_path, "2026-08-24", "2026-08-25", tickers)
    ca = _ca(tmp_path, "2026-08-24", "2026-08-25", tickers)
    prepared = prepare_post_eod(
        root,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        ca_reconciliation=ca,
    )
    completed = execute_preopen(
        root,
        prepared_path=prepared.path,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        open_inputs=_open(tmp_path, "2026-08-25", tickers),
        ca_reconciliation=ca,
    )
    completed.path.unlink()
    completed.runtime_snapshot_path.unlink()
    recovered = execute_preopen(
        root,
        prepared_path=prepared.path,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        open_inputs=_open(tmp_path, "2026-08-25", tickers),
        ca_reconciliation=ca,
    )
    assert recovered.status == "RECOVERED_STAGED_EXECUTION"
    assert recovered.file_sha256 == completed.file_sha256
    assert recovered.runtime_snapshot_sha256 == completed.runtime_snapshot_sha256


def test_existing_execution_rejects_changed_open_parent(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    tickers = [f"T{index:02d}" for index in range(11)]
    current = _score(tmp_path, "2026-08-24", 0)
    eod = _eod(tmp_path, "2026-08-24", "2026-08-25", tickers)
    ca = _ca(tmp_path, "2026-08-24", "2026-08-25", tickers)
    prepared = prepare_post_eod(
        root,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        ca_reconciliation=ca,
    )
    original_open = _open(tmp_path, "2026-08-25", tickers)
    execute_preopen(
        root,
        prepared_path=prepared.path,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        open_inputs=original_open,
        ca_reconciliation=ca,
    )
    changed_path = tmp_path / "changed-open.parquet"
    changed_path.write_bytes(b"different-certified-open")
    changed_open = replace(
        original_open,
        ohlcv_artifact_path=changed_path,
        ohlcv_artifact_sha256=_sha(changed_path),
    )
    with pytest.raises(
        E2EPaperOrchestrationError,
        match="EXISTING_EXECUTION_OPEN_PARENT_MISMATCH",
    ):
        execute_preopen(
            root,
            prepared_path=prepared.path,
            current_score=current,
            previous_score=None,
            eod_inputs=eod,
            open_inputs=changed_open,
            ca_reconciliation=ca,
        )


def test_existing_execution_rejects_changed_dividend_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    tickers = [f"T{index:02d}" for index in range(11)]
    current = _score(tmp_path, "2026-08-24", 0)
    eod = _eod(tmp_path, "2026-08-24", "2026-08-25", tickers)
    ca = _ca_with_event(tmp_path, "2026-08-24", "2026-08-25", tickers)
    review_path = tmp_path / "DIV-T00-ATTACHMENT_REVIEW.json"
    review_path.write_text('{"event_id":"DIV-T00"}\n', encoding="utf-8")
    evidence = VerifiedCashDividendEvidence(
        event=ca.certified_events[0],
        review_path=review_path,
        review_sha256=_sha(review_path),
        announcement_id="DIV-T00",
        announcement_number="DIV-T00",
        _verification_token=_VERIFIED_DIVIDEND_EVIDENCE_TOKEN,
    )
    monkeypatch.setattr(
        dividend_runtime.gate,
        "verify_cash_dividend_evidence_for_execution",
        lambda **_: evidence,
    )
    prepared = prepare_post_eod(
        root,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        ca_reconciliation=ca,
    )
    execute_preopen(
        root,
        prepared_path=prepared.path,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        open_inputs=_open(tmp_path, "2026-08-25", tickers),
        ca_reconciliation=ca,
        dividend_evidence=(evidence,),
    )
    altered_event = replace(
        evidence.event,
        gross_dividend_per_share_idr=999.0,
    )
    altered_evidence = replace(evidence, event=altered_event)
    with pytest.raises(
        E2EPaperOrchestrationError,
        match="DIVIDEND_EVIDENCE_EVENT_BINDING_MISMATCH",
    ):
        execute_preopen(
            root,
            prepared_path=prepared.path,
            current_score=current,
            previous_score=None,
            eod_inputs=eod,
            open_inputs=_open(tmp_path, "2026-08-25", tickers),
            ca_reconciliation=ca,
            dividend_evidence=(altered_evidence,),
        )
    forged_evidence = replace(evidence, _verification_token=object())
    with pytest.raises(
        E2EPaperOrchestrationError,
        match="DIVIDEND_EVIDENCE_TOKEN_INVALID",
    ):
        execute_preopen(
            root,
            prepared_path=prepared.path,
            current_score=current,
            previous_score=None,
            eod_inputs=eod,
            open_inputs=_open(tmp_path, "2026-08-25", tickers),
            ca_reconciliation=ca,
            dividend_evidence=(forged_evidence,),
        )


def test_preopen_accepts_fresh_ca_capture_without_semantic_delta(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    tickers = [f"T{index:02d}" for index in range(11)]
    current = _score(tmp_path, "2026-08-24", 0)
    eod = _eod(tmp_path, "2026-08-24", "2026-08-25", tickers)
    ca = _ca(tmp_path, "2026-08-24", "2026-08-25", tickers)
    prepared = prepare_post_eod(
        root,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        ca_reconciliation=ca,
    )
    changed_root = tmp_path / "changed-ca"
    changed_root.mkdir()
    changed_ca = _ca(changed_root, "2026-08-24", "2026-08-25", tickers)
    result = execute_preopen(
        root,
        prepared_path=prepared.path,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        open_inputs=_open(tmp_path, "2026-08-25", tickers),
        ca_reconciliation=changed_ca,
    )
    assert result.status == "EXECUTION_COMPLETE"


def test_preopen_allows_ca_extension_only_with_verified_new_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    tickers = [f"T{index:02d}" for index in range(11)]
    current = _score(tmp_path, "2026-08-24", 0)
    eod = _eod(tmp_path, "2026-08-24", "2026-08-25", tickers)
    prepared_ca = _ca(tmp_path, "2026-08-24", "2026-08-25", tickers)
    current_ca = _ca_with_event(tmp_path, "2026-08-24", "2026-08-25", tickers)
    review_path = tmp_path / "DIV-T00-ATTACHMENT_REVIEW.json"
    review_path.write_text('{"event_id":"DIV-T00"}\n', encoding="utf-8")
    evidence = VerifiedCashDividendEvidence(
        event=current_ca.certified_events[0],
        review_path=review_path,
        review_sha256=_sha(review_path),
        announcement_id="DIV-T00",
        announcement_number="DIV-T00",
        _verification_token=_VERIFIED_DIVIDEND_EVIDENCE_TOKEN,
    )
    monkeypatch.setattr(
        dividend_runtime.gate,
        "verify_cash_dividend_evidence_for_execution",
        lambda **_: evidence,
    )
    prepared = prepare_post_eod(
        root,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        ca_reconciliation=prepared_ca,
    )
    result = execute_preopen(
        root,
        prepared_path=prepared.path,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        open_inputs=_open(tmp_path, "2026-08-25", tickers),
        ca_reconciliation=current_ca,
        dividend_evidence=(evidence,),
    )
    assert result.status == "EXECUTION_COMPLETE"


def test_preopen_rejects_replacement_journal_identity_for_preserved_event(
    tmp_path: Path,
) -> None:
    tickers = [f"T{index:02d}" for index in range(11)]
    base = _ca(tmp_path, "2026-08-24", "2026-08-25", tickers)
    journal_a = tmp_path / "journal-a.json"
    journal_b = tmp_path / "journal-b.json"
    row_a = {
        "event_id": "DIV-T00",
        "review_sha256": "a" * 64,
        "event_sha256": "d" * 64,
        "ticker": "T00",
    }
    row_b = {**row_a, "review_sha256": "b" * 64}
    for path, row in ((journal_a, row_a), (journal_b, row_b)):
        path.write_text(
            json.dumps({
                "journal": {
                    "certified_events": [row],
                    "certified_history": [],
                    "blocker_resolution_history": [],
                }
            }) + "\n",
            encoding="utf-8",
        )
    parent = _reconciliation_payload(
        replace(base, v12_journal_path=journal_a, v12_journal_sha256=_sha(journal_a))
    )
    current = replace(
        base,
        v12_journal_path=journal_b,
        v12_journal_sha256=_sha(journal_b),
    )
    with pytest.raises(
        E2EPaperOrchestrationError,
        match="E2E_CA_PREOPEN_JOURNAL_ENTRY_CHANGED:DIV-T00",
    ):
        _verify_prepared_ca_parent(
            {"ca_reconciliation": parent},
            current,
            dividend_evidence=(),
        )


def test_integrated_dividend_cum_ex_payment_is_exactly_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    tickers = [f"T{index:02d}" for index in range(11)]
    previous_score = None
    for index, (decision_date, execution_date) in enumerate(
        (("2026-08-24", "2026-08-25"), ("2026-08-25", "2026-08-26"), ("2026-08-26", "2026-08-27"))
    ):
        current = _score(tmp_path, decision_date, index)
        eod = _eod(tmp_path, decision_date, execution_date, tickers)
        ca = _ca_with_event(tmp_path, decision_date, execution_date, tickers)
        review_path = tmp_path / "DIV-T00-ATTACHMENT_REVIEW.json"
        review_path.write_text('{"event_id":"DIV-T00"}\n', encoding="utf-8")
        evidence = VerifiedCashDividendEvidence(
            event=ca.certified_events[0],
            review_path=review_path,
            review_sha256=_sha(review_path),
            announcement_id="DIV-T00",
            announcement_number="DIV-T00",
            _verification_token=_VERIFIED_DIVIDEND_EVIDENCE_TOKEN,
        )
        monkeypatch.setattr(
            dividend_runtime.gate,
            "verify_cash_dividend_evidence_for_execution",
            lambda **_: evidence,
        )
        prepared = prepare_post_eod(
            root,
            current_score=current,
            previous_score=previous_score,
            eod_inputs=eod,
            ca_reconciliation=ca,
        )
        result = execute_preopen(
            root,
            prepared_path=prepared.path,
            current_score=current,
            previous_score=previous_score,
            eod_inputs=eod,
            open_inputs=_open(tmp_path, execution_date, tickers),
            ca_reconciliation=ca,
            dividend_evidence=(evidence,),
        )
        assert result.status == "EXECUTION_COMPLETE"
        previous_score = current

    final_snapshot = dividend_runtime.load_latest_runtime_snapshot(root)
    ledger = final_snapshot.state.dividend_ledger
    assert tuple(row.event_id for row in ledger.entitlements) == ("DIV-T00",)
    assert ledger.receivables == ()
    assert tuple(row.event_id for row in ledger.settlements) == ("DIV-T00",)
    assert ledger.settlements[0].gross_amount_idr == 125_000.0


def test_pending_buy_resolves_on_next_official_open(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    tickers = [f"T{index:02d}" for index in range(11)]
    first = _score(tmp_path, "2026-08-24", 0)
    first_eod = _eod(tmp_path, "2026-08-24", "2026-08-25", tickers)
    first_ca = _ca(tmp_path, "2026-08-24", "2026-08-25", tickers)
    first_prepared = prepare_post_eod(
        root,
        current_score=first,
        previous_score=None,
        eod_inputs=first_eod,
        ca_reconciliation=first_ca,
    )
    incomplete_open = replace(
        _open(tmp_path, "2026-08-25", tickers),
        raw_open_prices={ticker: 1000.0 for ticker in tickers if ticker != "T00"},
        available_tickers=frozenset(ticker for ticker in tickers if ticker != "T00"),
    )
    first_result = execute_preopen(
        root,
        prepared_path=first_prepared.path,
        current_score=first,
        previous_score=None,
        eod_inputs=first_eod,
        open_inputs=incomplete_open,
        ca_reconciliation=first_ca,
    )
    assert first_result.status == "EXECUTION_COMPLETE"
    after_first = dividend_runtime.load_latest_runtime_snapshot(root).state
    assert "T00" in {row.ticker for row in after_first.base_state.pending_buys}

    second = _score(tmp_path, "2026-08-25", 1)
    second_eod = _eod(tmp_path, "2026-08-25", "2026-08-26", tickers)
    second_ca = _ca(tmp_path, "2026-08-25", "2026-08-26", tickers)
    second_prepared = prepare_post_eod(
        root,
        current_score=second,
        previous_score=first,
        eod_inputs=second_eod,
        ca_reconciliation=second_ca,
    )
    second_result = execute_preopen(
        root,
        prepared_path=second_prepared.path,
        current_score=second,
        previous_score=first,
        eod_inputs=second_eod,
        open_inputs=_open(tmp_path, "2026-08-26", tickers),
        ca_reconciliation=second_ca,
    )
    assert second_result.status == "EXECUTION_COMPLETE"
    after_second = dividend_runtime.load_latest_runtime_snapshot(root).state
    assert "T00" not in {row.ticker for row in after_second.base_state.pending_buys}


def test_missing_official_open_advances_state_without_execution_or_cash_movement(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    tickers = [f"T{index:02d}" for index in range(11)]
    current = _score(tmp_path, "2026-08-24", 0)
    eod = _eod(tmp_path, "2026-08-24", "2026-08-25", tickers)
    ca = _ca(tmp_path, "2026-08-24", "2026-08-25", tickers)
    prepared = prepare_post_eod(
        root,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        ca_reconciliation=ca,
    )

    result = advance_missed_execution_no_certified_open(
        root,
        prepared_path=prepared.path,
        official_calendar_path=eod.official_calendar_path,
        ca_reconciliation=ca,
        official_open_root=tmp_path / "official_open",
        issued_at=datetime(2026, 8, 25, 10, tzinfo=JAKARTA),
    )

    assert result.status == MISSED_STATUS
    assert result.path.is_file()
    assert not (root / "executions" / "2026-08-25.json").exists()
    snapshot = dividend_runtime.load_latest_runtime_snapshot(root)
    assert snapshot.state.base_state.as_of_session_date == "2026-08-25"
    assert snapshot.state.base_state.cash_idr == INITIAL_NAV_IDR
    assert snapshot.state.base_state.positions == ()
    assert snapshot.state.base_state.pending_buys == ()
    assert snapshot.state.base_state.pending_sells == ()
    payload = json.loads(result.path.read_text(encoding="utf-8"))
    assert payload["fills"] == 0
    assert payload["costs_idr"] == 0.0
    assert payload["prepared_order_expired"] is True
    assert payload["no_retroactive_execution"] is True

    rerun = advance_missed_execution_no_certified_open(
        root,
        prepared_path=prepared.path,
        official_calendar_path=eod.official_calendar_path,
        ca_reconciliation=ca,
        official_open_root=tmp_path / "official_open",
    )
    assert rerun.file_sha256 == result.file_sha256
    assert rerun.runtime_snapshot_sha256 == result.runtime_snapshot_sha256

    next_score = _score(tmp_path, "2026-08-25", 1)
    next_eod = _eod(tmp_path, "2026-08-25", "2026-08-26", tickers)
    next_ca = _ca(tmp_path, "2026-08-25", "2026-08-26", tickers)
    next_prepared = prepare_post_eod(
        root,
        current_score=next_score,
        previous_score=current,
        eod_inputs=next_eod,
        ca_reconciliation=next_ca,
    )
    next_payload = json.loads(next_prepared.path.read_text(encoding="utf-8"))
    assert next_payload["previous_execution"]["status"] == MISSED_STATUS


def test_missing_open_transition_rejects_late_certified_open(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    bootstrap_t0(root, session_date="2026-08-24")
    tickers = [f"T{index:02d}" for index in range(11)]
    current = _score(tmp_path, "2026-08-24", 0)
    eod = _eod(tmp_path, "2026-08-24", "2026-08-25", tickers)
    ca = _ca(tmp_path, "2026-08-24", "2026-08-25", tickers)
    prepared = prepare_post_eod(
        root,
        current_score=current,
        previous_score=None,
        eod_inputs=eod,
        ca_reconciliation=ca,
    )
    open_manifest = tmp_path / "official_open" / "2026-08-25" / "manifest.json"
    open_manifest.parent.mkdir(parents=True)
    open_manifest.write_text("certified\n", encoding="utf-8")

    with pytest.raises(E2EPaperOrchestrationError, match="CERTIFIED_OPEN_EXISTS"):
        advance_missed_execution_no_certified_open(
            root,
            prepared_path=prepared.path,
            official_calendar_path=eod.official_calendar_path,
            ca_reconciliation=ca,
            official_open_root=tmp_path / "official_open",
        )
