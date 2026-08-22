from __future__ import annotations

import argparse
from pathlib import Path
import sys
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import idx_trade.forward_dividend_execution_v1_1 as gate
import idx_trade.forward_dividend_runtime_v1_1 as runtime
import idx_trade.forward_dividend_v1 as dividend

from idx_trade.v4_x1_execution_v1_contract import (
    PaperPortfolioState,
    PaperPosition,
)


EXPECTED_ANNOUNCEMENT_ID = (
    "20260819183103-005/CSG-IVR/2026_id-id"
)
EXPECTED_ANNOUNCEMENT_NUMBER = "005/CSG-IVR/2026"
EXPECTED_TICKER = "BBCA"
EXPECTED_AMOUNT = 25.0
EXPECTED_CUM_DATE = "2026-08-28"
EXPECTED_EX_DATE = "2026-08-31"
EXPECTED_RECORD_DATE = "2026-09-01"
EXPECTED_PAYMENT_DATE = "2026-09-16"
EXPECTED_SHARES = 200
EXPECTED_GROSS_CLAIM = 5_000.0
STARTING_CASH = 50_000_000.0
EXPECTED_FINAL_CASH = 50_005_000.0


def paper_state(
    session_date: str,
    *,
    cash: float = STARTING_CASH,
    shares: int = 0,
) -> PaperPortfolioState:
    positions = (
        (PaperPosition(EXPECTED_TICKER, shares),)
        if shares
        else ()
    )
    return PaperPortfolioState(
        as_of_session_date=session_date,
        cash_idr=cash,
        positions=positions,
    )


def run(evidence_root: Path, runtime_root: Path) -> None:
    review = evidence_root / "ATTACHMENT_REVIEW.json"

    if not review.is_file():
        raise RuntimeError(
            f"BBCA attachment review missing: {review}"
        )

    verified = gate.verify_cash_dividend_evidence_for_execution(
        review_path=review,
        attachment_dir=evidence_root,
    )
    event = verified.event

    assert verified.announcement_id == EXPECTED_ANNOUNCEMENT_ID
    assert verified.announcement_number == EXPECTED_ANNOUNCEMENT_NUMBER
    assert event.ticker == EXPECTED_TICKER
    assert event.gross_dividend_per_share_idr == EXPECTED_AMOUNT
    assert event.cum_date == EXPECTED_CUM_DATE
    assert event.ex_date == EXPECTED_EX_DATE
    assert event.record_date == EXPECTED_RECORD_DATE
    assert event.payment_date == EXPECTED_PAYMENT_DATE

    print("=== REAL EVIDENCE ADMISSION PASS ===")
    print(f"announcement_id={verified.announcement_id}")
    print(f"event_id={event.event_id}")
    print(f"event_sha={event.source_evidence_sha256}")

    registry = runtime.register_verified_cash_dividend_evidence(
        (),
        verified,
        attachment_dir=evidence_root,
    )

    announced_state = dividend.DividendAwarePaperState(
        base_state=paper_state("2026-08-21"),
    )

    first = runtime.write_runtime_snapshot(
        runtime_root,
        announced_state,
        registry,
    )

    loaded_first = runtime.load_latest_runtime_snapshot(runtime_root)

    assert runtime.registered_certified_events(
        loaded_first.certified_dividend_registry
    ) == (event,)

    print("=== ANNOUNCEMENT REGISTRY RESTART PASS ===")

    cum_pre = dividend.DividendAwarePaperState(
        base_state=paper_state(
            EXPECTED_CUM_DATE,
            shares=EXPECTED_SHARES,
        ),
        dividend_ledger=loaded_first.state.dividend_ledger,
    )

    cum_state = dividend.process_dividend_eod(
        cum_pre,
        runtime.registered_certified_events(
            loaded_first.certified_dividend_registry
        ),
        session_date=EXPECTED_CUM_DATE,
    )

    assert len(cum_state.dividend_ledger.entitlements) == 1
    entitlement = cum_state.dividend_ledger.entitlements[0]
    assert entitlement.entitled_shares == EXPECTED_SHARES
    assert (
        entitlement.entitled_shares
        * entitlement.gross_dividend_per_share_idr
        == EXPECTED_GROSS_CLAIM
    )

    runtime.write_runtime_snapshot(
        runtime_root,
        cum_state,
        loaded_first.certified_dividend_registry,
        previous_snapshot=loaded_first,
    )

    loaded_cum = runtime.load_latest_runtime_snapshot(runtime_root)

    assert len(loaded_cum.state.dividend_ledger.entitlements) == 1
    assert loaded_cum.previous_snapshot_sha256 == first.file_sha256

    print("=== CUM SNAPSHOT RESTART PASS ===")

    ex_pre = dividend.DividendAwarePaperState(
        base_state=paper_state(EXPECTED_EX_DATE, shares=0),
        dividend_ledger=loaded_cum.state.dividend_ledger,
    )

    ex_state = dividend.process_dividend_eod(
        ex_pre,
        runtime.registered_certified_events(
            loaded_cum.certified_dividend_registry
        ),
        session_date=EXPECTED_EX_DATE,
    )

    assert len(ex_state.dividend_ledger.receivables) == 1
    assert (
        ex_state.dividend_ledger.receivables[0].gross_amount_idr
        == EXPECTED_GROSS_CLAIM
    )
    assert ex_state.base_state.cash_idr == STARTING_CASH

    runtime.write_runtime_snapshot(
        runtime_root,
        ex_state,
        loaded_cum.certified_dividend_registry,
        previous_snapshot=loaded_cum,
    )

    loaded_ex = runtime.load_latest_runtime_snapshot(runtime_root)

    assert len(loaded_ex.state.dividend_ledger.receivables) == 1
    assert loaded_ex.state.base_state.cash_idr == STARTING_CASH

    print("=== EX RECEIVABLE RESTART PASS ===")

    pay_pre = dividend.DividendAwarePaperState(
        base_state=paper_state(
            EXPECTED_PAYMENT_DATE,
            cash=STARTING_CASH,
        ),
        dividend_ledger=loaded_ex.state.dividend_ledger,
    )

    paid = dividend.process_dividend_eod(
        pay_pre,
        runtime.registered_certified_events(
            loaded_ex.certified_dividend_registry
        ),
        session_date=EXPECTED_PAYMENT_DATE,
    )

    assert paid.base_state.cash_idr == EXPECTED_FINAL_CASH
    assert paid.dividend_ledger.receivables == ()
    assert len(paid.dividend_ledger.settlements) == 1

    final_written = runtime.write_runtime_snapshot(
        runtime_root,
        paid,
        loaded_ex.certified_dividend_registry,
        previous_snapshot=loaded_ex,
    )

    final = runtime.load_latest_runtime_snapshot(runtime_root)

    assert final.path == final_written.path
    assert final.state.base_state.cash_idr == EXPECTED_FINAL_CASH
    assert final.state.dividend_ledger.receivables == ()
    assert len(final.state.dividend_ledger.settlements) == 1
    assert len(final.certified_dividend_registry) == 1

    replay = runtime.write_runtime_snapshot(
        runtime_root,
        final.state,
        final.certified_dividend_registry,
        previous_snapshot=loaded_ex,
    )

    assert replay.file_sha256 == final.file_sha256
    assert replay.state.base_state.cash_idr == EXPECTED_FINAL_CASH

    print("=== PAYMENT + FULL HASH CHAIN PASS ===")
    print(f"final_cash={final.state.base_state.cash_idr}")
    print(f"final_snapshot_sha={final.file_sha256}")
    print("REAL_BBCA_DURABLE_RESTART_LIFECYCLE_PASS")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Offline acceptance rehearsal using the already captured "
            "real BBCA official IDX dividend evidence."
        )
    )
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--runtime-root")
    args = parser.parse_args()

    evidence_root = Path(args.evidence_root).expanduser().resolve()

    if args.runtime_root:
        runtime_root = Path(args.runtime_root).expanduser().resolve()
        if runtime_root.exists():
            raise SystemExit(
                f"STOP: runtime root already exists: {runtime_root}"
            )
        runtime_root.mkdir(parents=True)
        run(evidence_root, runtime_root)
        return 0

    with tempfile.TemporaryDirectory(
        prefix="idx-trade-real-bbca-dividend-"
    ) as temp:
        run(evidence_root, Path(temp))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
