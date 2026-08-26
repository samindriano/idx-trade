from __future__ import annotations

import shutil

from idx_trade.e2e_paper_cloud_runtime_v1 import (
    LocalConditionalStore,
    build_runtime_snapshot,
    restore_runtime_snapshot,
)
from idx_trade.e2e_paper_orchestration_v1 import (
    bootstrap_t0,
    derive_required_execution_tickers,
    execute_preopen,
    load_score_manifest,
    prepare_post_eod,
)
from idx_trade.forward_dividend_execution_v1_1 import (
    reconcile_corporate_action_attestation_v1_2_journal,
    verify_cash_dividend_evidence_for_execution,
)
from idx_trade.v4_x1_execution_v1_verify import (
    verify_eod_execution_inputs,
    verify_open_execution_inputs,
)
import idx_trade.e2e_paper_preopen_ca_cloud_v1 as preopen_ca
from scripts import run_e2e_paper_production_replay_v1 as production


DECISION = "2026-08-27"
EXECUTION = "2026-08-28"
CODE_SHA = "a" * 40
RUNNER_SHA = "9" * 64
SCHEDULE_SHA = "b" * 64
INPUT_SHA = "c" * 64


def _guards() -> dict[str, bool]:
    return {
        "outcome_accessed": False,
        "protected_forward_accessed": False,
        "model_refit": False,
        "paper_state_mutated": False,
        "order_created": False,
        "fill_created": False,
        "retroactive_execution_authorized": False,
    }


def test_synthetic_fresh_runner_d_to_e_checkpoint_then_preopen_execution(tmp_path) -> None:
    """Exercise the D->E boundary with real artifact verifiers.

    Fixtures remain synthetic, but every score/EOD/Open/CA/dividend input is
    loaded through the public verifiers used by the production replay.  This
    acceptance path must not mint private-token Verified objects or monkeypatch
    a production verifier.
    """
    paper = (tmp_path / "paper-runtime").resolve()
    paper.mkdir(parents=True)
    bootstrap_t0(paper, session_date=DECISION)

    # Use the initial deterministic score fixture so the production CA fixture's
    # T00 evidence is inside the exact required execution universe.
    score_manifest = production._score_fixture(paper, DECISION, 0)
    current_score = load_score_manifest(score_manifest)
    ohlcv, model_input, calendar = production._eod_fixture(paper, DECISION, EXECUTION)
    eod = verify_eod_execution_inputs(
        session_ohlcv_path=ohlcv,
        model_input_path=model_input,
        official_calendar_path=calendar,
        decision_session_date=DECISION,
        required_tickers=production.TICKERS,
    )
    required = derive_required_execution_tickers(
        paper,
        current_score=current_score,
        previous_score=None,
        eod_inputs=eod,
    )
    post_attestation, post_journal, _ = production._ca_fixture(
        paper,
        DECISION,
        EXECUTION,
        required,
        include_event=False,
        capture_phase="POST_EOD",
    )
    prepared_ca = reconcile_corporate_action_attestation_v1_2_journal(
        attestation_path=post_attestation,
        journal_path=post_journal,
        expected_from_session_date=DECISION,
        expected_through_session_date=EXECUTION,
        required_tickers=required,
    )
    prepared = prepare_post_eod(
        paper,
        current_score=current_score,
        previous_score=None,
        eod_inputs=eod,
        ca_reconciliation=prepared_ca,
    )

    # Fresh PREOPEN evidence arrives on E and extends the D->E CA view.  It is
    # evidence only at checkpoint time; no execution/PaperState transition is
    # authorized before Official Open admission.
    preopen_attestation, preopen_journal, verified_dividend = production._ca_fixture(
        paper,
        DECISION,
        EXECUTION,
        required,
        include_event=True,
        capture_phase="PREOPEN",
        capture_timestamp_utc=f"{EXECUTION}T01:00:00+00:00",
        announcement="2026-08-27T18:00:00",
        event_schedule=("2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04"),
    )
    assert verified_dividend is not None
    current_ca = reconcile_corporate_action_attestation_v1_2_journal(
        attestation_path=preopen_attestation,
        journal_path=preopen_journal,
        expected_from_session_date=DECISION,
        expected_through_session_date=EXECUTION,
        required_tickers=required,
    )
    evidence = (
        verify_cash_dividend_evidence_for_execution(
            review_path=verified_dividend.review_path,
            attachment_dir=verified_dividend.review_path.parent,
        ),
    )
    assert evidence[0].event == current_ca.certified_events[0]
    execution_path = paper / "executions" / f"{EXECUTION}.json"
    assert not execution_path.exists()

    snapshot, snapshot_sha, metadata = build_runtime_snapshot({"paper": paper})
    store = LocalConditionalStore(tmp_path / "store")
    checkpoint = preopen_ca.commit_preopen_ca_checkpoint(
        store,
        session_date=EXECUTION,
        snapshot_bytes=snapshot,
        snapshot_metadata=metadata,
        result_payload={
            "schema_version": "idx_trade_e2e_paper_preopen_ca_result_v1",
            "session_date": EXECUTION,
            "stage": preopen_ca.CHECKPOINT_STAGE,
            "controller_status": preopen_ca.CHECKPOINT_STATUS,
            **_guards(),
        },
        schedule_attestation_sha256=SCHEDULE_SHA,
        input_manifest_sha256=INPUT_SHA,
        code_identity={
            "repo": "samindriano/idx-trade",
            "commit": CODE_SHA,
            "runner_sha256": RUNNER_SHA,
        },
    )
    assert checkpoint.snapshot_sha256 == snapshot_sha
    assert not execution_path.exists()

    # Fresh GitHub-hosted job: ephemeral disk is gone, then the checkpoint is
    # restored back to the same fixed absolute runtime path used by production.
    shutil.rmtree(paper)
    restored = preopen_ca.load_preopen_ca_checkpoint(
        store,
        session_date=EXECUTION,
        expected_schedule_sha256=SCHEDULE_SHA,
        expected_input_manifest_sha256=INPUT_SHA,
        expected_code_commit=CODE_SHA,
    )
    assert restored is not None
    restore_runtime_snapshot(
        restored.snapshot_bytes,
        {"paper": paper},
        expected_sha256=restored.snapshot_sha256,
    )
    assert prepared.path.is_file()
    assert not execution_path.exists()

    open_manifest = production._open_fixture(paper, EXECUTION)
    open_inputs = verify_open_execution_inputs(
        execution_session_date=EXECUTION,
        manifest_path=open_manifest,
    )
    result = execute_preopen(
        paper,
        prepared_path=prepared.path,
        current_score=current_score,
        previous_score=None,
        eod_inputs=eod,
        open_inputs=open_inputs,
        ca_reconciliation=current_ca,
    )
    rerun = execute_preopen(
        paper,
        prepared_path=prepared.path,
        current_score=current_score,
        previous_score=None,
        eod_inputs=eod,
        open_inputs=open_inputs,
        ca_reconciliation=current_ca,
    )

    assert result.status == "EXECUTION_COMPLETE"
    assert execution_path.is_file()
    assert rerun.status == "ALREADY_COMPLETE"
    assert rerun.file_sha256 == result.file_sha256
