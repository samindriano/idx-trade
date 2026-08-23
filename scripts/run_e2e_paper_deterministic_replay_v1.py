"""Run the outcome-blind deterministic dividend/state-machine acceptance.

This companion replay is intentionally smaller than the artifact replay.  It
states the economic oracle directly and proves the pure lifecycle transitions,
late-known entitlement recovery, one-time settlement, and T0 immutability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from idx_trade import forward_dividend_v1 as dividend
from idx_trade import forward_dividend_runtime_v1_1 as runtime
from idx_trade.e2e_paper_orchestration_v1 import (
    E2EPaperPaths,
    _canonical_hash,
    bootstrap_t0,
)
from idx_trade.v4_x1_execution_v1_contract import PaperPortfolioState, PaperPosition


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _event() -> dividend.CertifiedCashDividend:
    return dividend.CertifiedCashDividend(
        event_id="CASH_DIVIDEND_T00_DETERMINISTIC_001",
        ticker="T00",
        announcement_timestamp="2026-08-25T12:00:00+07:00",
        knowledge_at_timestamp="2026-08-25T12:00:00+07:00",
        gross_dividend_per_share_idr=25.0,
        cum_date="2026-08-25",
        ex_date="2026-08-26",
        record_date="2026-08-26",
        payment_date="2026-08-28",
        source_evidence_sha256="a" * 64,
    )


def _state(session: str, *, cash: float = 1_000_000.0, shares: int = 5_000) -> dividend.DividendAwarePaperState:
    return dividend.DividendAwarePaperState(
        base_state=PaperPortfolioState(
            as_of_session_date=session,
            cash_idr=cash,
            positions=(PaperPosition("T00", shares),) if shares else (),
            pending_buys=(),
            pending_sells=(),
        ),
        dividend_ledger=dividend.DividendLedger(),
    )


def _summary(state: dividend.DividendAwarePaperState) -> dict[str, object]:
    return {
        "session_date": state.base_state.as_of_session_date,
        "cash_idr": state.base_state.cash_idr,
        "positions": [(row.ticker, row.shares) for row in state.base_state.positions],
        "entitlements": [row.event_id for row in state.dividend_ledger.entitlements],
        "receivables": [
            (row.event_id, row.entitled_shares, row.gross_amount_idr)
            for row in state.dividend_ledger.receivables
        ],
        "settlements": [row.event_id for row in state.dividend_ledger.settlements],
    }


def run(output_dir: Path) -> Path:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise SystemExit(f"DETERMINISTIC_OUTPUT_NOT_EMPTY:{output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    t0 = bootstrap_t0(output_dir, session_date="2026-08-24")
    t0_sha = _sha(t0)

    event = _event()
    close_prices = {"T00": 1_000.0}
    cum_state = _state("2026-08-25")
    cum = dividend.process_dividend_eod(cum_state, (event,), session_date="2026-08-25")
    if [row.entitled_shares for row in cum.dividend_ledger.entitlements] != [5_000]:
        raise RuntimeError("DETERMINISTIC_CUM_ENTITLEMENT_ORACLE_FAILED")
    if cum.dividend_ledger.receivables:
        raise RuntimeError("DETERMINISTIC_CUM_RECEIVABLE_ORACLE_FAILED")

    ex_input = dividend.DividendAwarePaperState(
        base_state=PaperPortfolioState(
            as_of_session_date="2026-08-26",
            cash_idr=cum.base_state.cash_idr,
            positions=cum.base_state.positions,
            pending_buys=(),
            pending_sells=(),
        ),
        dividend_ledger=cum.dividend_ledger,
    )
    ex = dividend.process_dividend_eod(ex_input, (event,), session_date="2026-08-26")
    raw_nav = dividend.paper_total_return_nav_idr(ex, close_prices) - 125_000.0
    total_return_nav = dividend.paper_total_return_nav_idr(ex, close_prices)
    if raw_nav != 6_000_000.0 or total_return_nav != 6_125_000.0:
        raise RuntimeError("DETERMINISTIC_RECEIVABLE_NAV_ORACLE_FAILED")
    if ex.base_state.cash_idr != 1_000_000.0:
        raise RuntimeError("DETERMINISTIC_RECEIVABLE_SPENDABLE_CASH_ORACLE_FAILED")

    payment_input = dividend.DividendAwarePaperState(
        base_state=PaperPortfolioState(
            as_of_session_date="2026-08-28",
            cash_idr=ex.base_state.cash_idr,
            positions=ex.base_state.positions,
            pending_buys=(),
            pending_sells=(),
        ),
        dividend_ledger=ex.dividend_ledger,
    )
    settled = dividend.process_dividend_eod(payment_input, (event,), session_date="2026-08-28")
    if settled.base_state.cash_idr != 1_125_000.0:
        raise RuntimeError("DETERMINISTIC_PAYMENT_CASH_ORACLE_FAILED")
    if settled.dividend_ledger.receivables or len(settled.dividend_ledger.settlements) != 1:
        raise RuntimeError("DETERMINISTIC_PAYMENT_SETTLEMENT_ORACLE_FAILED")
    replayed = dividend.process_dividend_eod(settled, (event,), session_date="2026-08-28")
    if dividend.dividend_aware_state_hash(replayed) != dividend.dividend_aware_state_hash(settled):
        raise RuntimeError("DETERMINISTIC_SETTLEMENT_NOT_IDEMPOTENT")

    late_current = _state("2026-08-26")
    historical = {"2026-08-25": cum_state}
    late = dividend.process_dividend_eod(
        late_current,
        (event,),
        session_date="2026-08-26",
        historical_states_by_date=historical,
    )
    if [row.entitled_shares for row in late.dividend_ledger.entitlements] != [5_000]:
        raise RuntimeError("DETERMINISTIC_LATE_KNOWN_ENTITLEMENT_ORACLE_FAILED")
    try:
        dividend.process_dividend_eod(late_current, (event,), session_date="2026-08-26")
    except dividend.DecisionV1Error as exc:
        if str(exc) != "DIVIDEND_V1_HISTORICAL_CUM_STATE_REQUIRED":
            raise
    else:
        raise RuntimeError("DETERMINISTIC_LATE_KNOWN_MISSING_HISTORY_NOT_FAIL_CLOSED")

    try:
        bootstrap_t0(output_dir, session_date="2026-08-25")
    except Exception as exc:
        if str(exc) != "E2E_T0_ROOT_CONFLICT":
            raise
    else:
        raise RuntimeError("DETERMINISTIC_T0_DIVERGENCE_NOT_REJECTED")
    if _sha(t0) != t0_sha:
        raise RuntimeError("DETERMINISTIC_T0_MUTATED_AFTER_DIVERGENT_RETRY")

    body = {
        "schema_version": "idx_trade_e2e_paper_deterministic_replay_v1",
        "replay_kind": "DETERMINISTIC_CORE_REPLAY",
        "synthetic_only": True,
        "provider_calls": False,
        "protected_outcomes_accessed": False,
        "oracle": {
            "cum_entitled_shares": 5_000,
            "ex_receivable_amount_idr": 125_000.0,
            "raw_nav_idr": raw_nav,
            "total_return_nav_idr": total_return_nav,
            "payment_cash_idr": 1_125_000.0,
            "settlement_count_after_replay": 1,
        },
        "states": {
            "cum": _summary(cum),
            "ex": _summary(ex),
            "settled": _summary(settled),
            "late_known": _summary(late),
        },
        "checks": {
            "cold_replay_idempotent": True,
            "late_known_requires_historical_state": True,
            "divergent_t0_is_fail_closed": True,
            "t0_sha256": t0_sha,
        },
    }
    body["summary_sha256"] = _canonical_hash(body)
    summary = output_dir / "acceptance_summary.json"
    summary.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    summary = run(Path(args.output_dir).expanduser().resolve())
    print({
        "status": "DETERMINISTIC_CORE_REPLAY_PASS",
        "summary_path": str(summary),
        "summary_sha256": _sha(summary),
        "outcome_access": False,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
