"""Execute one prepared E2E PAPER session with dual-calendar proof."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from idx_trade.e2e_operational_guard_v1 import (
    JAKARTA,
    attest_deployment,
    exclusive_run_lock,
    require_phase_attestation,
    require_phase_window,
)
from idx_trade.e2e_paper_orchestration_v1 import (
    derive_required_execution_tickers,
    execute_preopen,
    load_score_manifest,
)
from idx_trade.e2e_paper_schedule_binding_v1 import verify_prepared_schedule_binding
from idx_trade.forward_dividend_execution_v1_1 import (
    reconcile_corporate_action_attestation_v1_1,
    reconcile_corporate_action_attestation_v1_2_journal,
    verify_cash_dividend_evidence_for_execution,
)
from idx_trade.official_trading_schedule_v1 import load_verified_official_trading_schedule
from idx_trade.v4_x1_execution_v1_verify import verify_open_execution_inputs
from idx_trade.v4_x1_execution_v1_verify_schedule_v1 import (
    verify_eod_execution_inputs_with_schedule,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--prepared", required=True)
    parser.add_argument("--current-score-manifest", required=True)
    parser.add_argument("--previous-score-manifest")
    parser.add_argument("--session-ohlcv", required=True)
    parser.add_argument("--model-input", required=True)
    parser.add_argument("--calendar", required=True, help="Observed closed-session IDX calendar")
    parser.add_argument("--execution-schedule-attestation", required=True)
    parser.add_argument("--execution-schedule-attestation-sha256", required=True)
    parser.add_argument("--open-manifest", required=True)
    parser.add_argument("--ca-attestation", required=True)
    parser.add_argument("--expected-branch", required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--phase-attestation")
    parser.add_argument("--ca-journal")
    parser.add_argument("--dividend-review", action="append", default=[])
    parser.add_argument("--attachment-dir")
    return parser


def _run(args: argparse.Namespace) -> int:
    current = load_score_manifest(args.current_score_manifest)
    previous = (
        None
        if args.previous_score_manifest is None
        else load_score_manifest(args.previous_score_manifest)
    )
    required = tuple(
        sorted({str(value).strip().upper() for value in current.scores["ticker"].tolist()})
    )
    eod = verify_eod_execution_inputs_with_schedule(
        session_ohlcv_path=args.session_ohlcv,
        model_input_path=args.model_input,
        official_calendar_path=args.calendar,
        execution_schedule_attestation_path=args.execution_schedule_attestation,
        execution_schedule_attestation_sha256=args.execution_schedule_attestation_sha256,
        decision_session_date=current.session_date,
        required_tickers=required,
    )
    schedule = load_verified_official_trading_schedule(
        args.execution_schedule_attestation,
        expected_sha256=args.execution_schedule_attestation_sha256,
    )
    require_phase_window(
        phase="PREOPEN",
        session_date=eod.next_official_session_date,
        official_session_dates=schedule.session_dates,
        now=datetime.now(tz=JAKARTA),
    )
    verify_prepared_schedule_binding(
        args.runtime_root,
        prepared_path=args.prepared,
        expected_schedule_attestation_path=args.execution_schedule_attestation,
        expected_schedule_attestation_sha256=args.execution_schedule_attestation_sha256,
    )
    open_inputs = verify_open_execution_inputs(
        execution_session_date=eod.next_official_session_date,
        manifest_path=args.open_manifest,
    )
    evidence = tuple(
        verify_cash_dividend_evidence_for_execution(
            review_path=path,
            attachment_dir=(
                args.attachment_dir
                if args.attachment_dir
                else Path(path).expanduser().resolve().parent
            ),
        )
        for path in args.dividend_review
    )
    execution_universe = derive_required_execution_tickers(
        args.runtime_root,
        current_score=current,
        previous_score=previous,
        eod_inputs=eod,
        current_bootstrap_prepared_path=args.prepared,
    )
    if args.ca_journal:
        if evidence:
            raise SystemExit("DIVIDEND_V1_2_JOURNAL_EVIDENCE_MUST_BE_INLINE")
        ca = reconcile_corporate_action_attestation_v1_2_journal(
            attestation_path=args.ca_attestation,
            journal_path=args.ca_journal,
            expected_from_session_date=eod.session_date,
            expected_through_session_date=eod.next_official_session_date,
            required_tickers=execution_universe,
        )
    else:
        ca = reconcile_corporate_action_attestation_v1_1(
            attestation_path=args.ca_attestation,
            expected_from_session_date=eod.session_date,
            expected_through_session_date=eod.next_official_session_date,
            required_tickers=execution_universe,
            dividend_evidence=evidence,
        )
    result = execute_preopen(
        args.runtime_root,
        prepared_path=args.prepared,
        current_score=current,
        previous_score=previous,
        eod_inputs=eod,
        open_inputs=open_inputs,
        ca_reconciliation=ca,
        dividend_evidence=evidence,
    )
    print(
        {
            "status": result.status,
            "execution_path": str(result.path),
            "execution_sha256": result.file_sha256,
            "runtime_snapshot_path": str(result.runtime_snapshot_path),
            "runtime_snapshot_sha256": result.runtime_snapshot_sha256,
            "execution_session_date": result.execution_session_date,
            "outcome_access": False,
        }
    )
    return 0


def main() -> int:
    args = _parser().parse_args()
    attest_deployment(
        REPO_ROOT,
        expected_branch=args.expected_branch,
        expected_commit=args.expected_commit,
    )
    try:
        prepared_payload = json.loads(Path(args.prepared).read_text(encoding="utf-8"))
        execution_session = str(prepared_payload.get("execution_session_date") or "")
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit("E2E_PREPARED_ATTESTATION_SESSION_INVALID") from exc
    require_phase_attestation(
        args.runtime_root,
        phase="PREOPEN",
        session_date=execution_session,
        expected_branch=args.expected_branch,
        expected_commit=args.expected_commit,
        attestation_path=args.phase_attestation,
    )
    with exclusive_run_lock(Path(args.runtime_root) / "operational" / "phase.lock"):
        return _run(args)


if __name__ == "__main__":
    raise SystemExit(main())
