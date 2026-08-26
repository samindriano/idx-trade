from __future__ import annotations

import shutil

from idx_trade import forward_dividend_runtime_v1_1 as dividend_runtime
from idx_trade.e2e_paper_cloud_runtime_v1 import (
    LocalConditionalStore,
    build_runtime_snapshot,
    restore_runtime_snapshot,
)
from idx_trade.e2e_paper_orchestration_v1 import (
    bootstrap_t0,
    execute_preopen,
    prepare_post_eod,
)
import idx_trade.e2e_paper_preopen_ca_cloud_v1 as preopen_ca
from scripts import run_e2e_paper_synthetic_replay_v1 as synthetic


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
    paper = (tmp_path / "paper-runtime").resolve()
    paper.mkdir(parents=True)
    (paper / "fixtures").mkdir()
    bootstrap_t0(paper, session_date=DECISION)

    current_score = synthetic._score(paper, DECISION, 3)
    eod = synthetic._eod(paper, DECISION, EXECUTION)
    prepared_ca = synthetic._ca(paper, DECISION, EXECUTION, event=False)
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
    current_ca = synthetic._ca(
        paper,
        DECISION,
        EXECUTION,
        event=True,
        event_id="DIV-T01",
    )
    evidence = tuple(synthetic._evidence(paper, event) for event in current_ca.certified_events)
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

    open_inputs = synthetic._open(paper, EXECUTION, missing=set())
    evidence_by_path = {
        str(row.review_path.resolve()): row
        for row in evidence
    }
    original_gate = dividend_runtime.gate.verify_cash_dividend_evidence_for_execution
    try:
        dividend_runtime.gate.verify_cash_dividend_evidence_for_execution = (
            lambda **kwargs: evidence_by_path[
                str(__import__("pathlib").Path(kwargs["review_path"]).expanduser().resolve())
            ]
        )
        result = execute_preopen(
            paper,
            prepared_path=prepared.path,
            current_score=current_score,
            previous_score=None,
            eod_inputs=eod,
            open_inputs=open_inputs,
            ca_reconciliation=current_ca,
            dividend_evidence=evidence,
        )
        rerun = execute_preopen(
            paper,
            prepared_path=prepared.path,
            current_score=current_score,
            previous_score=None,
            eod_inputs=eod,
            open_inputs=open_inputs,
            ca_reconciliation=current_ca,
            dividend_evidence=evidence,
        )
    finally:
        dividend_runtime.gate.verify_cash_dividend_evidence_for_execution = original_gate

    assert result.status == "EXECUTION_COMPLETE"
    assert execution_path.is_file()
    assert rerun.status == "ALREADY_COMPLETE"
    assert rerun.file_sha256 == result.file_sha256
