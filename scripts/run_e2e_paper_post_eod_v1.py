"""Prepare one outcome-blind E2E paper execution from verified local artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from idx_trade.e2e_paper_orchestration_v1 import (
    load_score_manifest,
    prepare_post_eod,
)
from idx_trade.forward_dividend_execution_v1_1 import (
    reconcile_corporate_action_attestation_v1_1,
    verify_cash_dividend_evidence_for_execution,
)
from idx_trade.v4_x1_execution_v1_verify import verify_eod_execution_inputs


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--current-score-manifest", required=True)
    parser.add_argument("--previous-score-manifest")
    parser.add_argument("--session-ohlcv", required=True)
    parser.add_argument("--model-input", required=True)
    parser.add_argument("--calendar", required=True)
    parser.add_argument("--ca-attestation", required=True)
    parser.add_argument(
        "--dividend-review",
        action="append",
        default=[],
        help="Already captured and reviewed local V1.2 evidence; repeatable.",
    )
    parser.add_argument(
        "--attachment-dir",
        help="Directory containing the immutable attachments for reviews.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    current = load_score_manifest(args.current_score_manifest)
    previous = (
        None
        if args.previous_score_manifest is None
        else load_score_manifest(args.previous_score_manifest)
    )
    required = tuple(
        sorted(
            {
                str(value).strip().upper()
                for value in current.scores["ticker"].tolist()
            }
        )
    )
    eod = verify_eod_execution_inputs(
        session_ohlcv_path=args.session_ohlcv,
        model_input_path=args.model_input,
        official_calendar_path=args.calendar,
        decision_session_date=current.session_date,
        required_tickers=required,
    )
    if args.dividend_review and not args.attachment_dir:
        raise SystemExit("--attachment-dir is required with --dividend-review")
    evidence = tuple(
        verify_cash_dividend_evidence_for_execution(
            review_path=path,
            attachment_dir=args.attachment_dir,
        )
        for path in args.dividend_review
    )
    ca = reconcile_corporate_action_attestation_v1_1(
        attestation_path=args.ca_attestation,
        expected_from_session_date=eod.session_date,
        expected_through_session_date=eod.next_official_session_date,
        required_tickers=required,
        dividend_evidence=evidence,
    )
    result = prepare_post_eod(
        args.runtime_root,
        current_score=current,
        previous_score=previous,
        eod_inputs=eod,
        ca_reconciliation=ca,
    )
    print(
        {
            "status": result.status,
            "prepared_path": str(result.path),
            "prepared_sha256": result.file_sha256,
            "decision_session_date": result.decision_session_date,
            "execution_session_date": result.execution_session_date,
            "outcome_access": False,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
