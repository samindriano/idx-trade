"""Run a deterministic, outcome-blind five-session E2E paper replay.

This runner creates only synthetic score/EOD/Open/CA fixtures under a caller
supplied fresh directory.  It exercises the production E2E orchestrator and
emits a small hash-pinned acceptance summary; it never calls a provider or
opens a label/outcome artifact.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from idx_trade import forward_dividend_v1 as dividend
from idx_trade import forward_dividend_runtime_v1_1 as dividend_runtime
from idx_trade.e2e_paper_orchestration_v1 import (
    _canonical_hash,
    bootstrap_t0,
    execute_preopen,
    prepare_post_eod,
)
from idx_trade.forward_dividend_execution_v1_1 import (
    VerifiedCashDividendEvidence,
    VerifiedDividendCAReconciliation,
    _DIVIDEND_RECONCILIATION_TOKEN,
    _VERIFIED_DIVIDEND_EVIDENCE_TOKEN,
)
from idx_trade.official_open_evidence_v1 import (
    AUTHORITY,
    FALLBACK_POLICY,
    FIELD_SEMANTICS,
    TRANSPORT_POLICY,
    UPSTREAM_PATH,
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


TICKERS = tuple(f"T{index:02d}" for index in range(11))
SESSIONS = (
    ("2026-08-24", "2026-08-25"),
    ("2026-08-25", "2026-08-26"),
    ("2026-08-26", "2026-08-27"),
    ("2026-08-27", "2026-08-28"),
    ("2026-08-28", "2026-08-29"),
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def _score(root: Path, session: str, index: int) -> VerifiedScoreSession:
    # Session 0 bootstraps T00..T09.  Later permutations exercise a
    # rank-qualified replacement and then a pending-buy retry.
    orders = (
        TICKERS,
        ("T10", "T00", "T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08", "T09"),
        ("T09", "T10", "T00", "T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08"),
        ("T09", "T10", "T00", "T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08"),
        ("T09", "T10", "T00", "T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08"),
    )
    order = orders[index]
    ranks = {ticker: rank for rank, ticker in enumerate(order, start=1)}
    frame = pd.DataFrame(
        {
            "ticker": list(TICKERS),
            "date": [session] * len(TICKERS),
            "alpha_h5": [float(12 - ranks[ticker]) for ticker in TICKERS],
            "alpha_h10": [float(12 - ranks[ticker]) for ticker in TICKERS],
            "alpha_consensus": [float(12 - ranks[ticker]) for ticker in TICKERS],
            "rank_consensus": [ranks[ticker] for ticker in TICKERS],
        }
    )
    artifact = root / "fixtures" / f"score-{session}.parquet"
    manifest = root / "fixtures" / f"score-{session}.json"
    frame.to_parquet(artifact, index=False)
    manifest.write_text(json.dumps({"synthetic": True, "session": session}) + "\n", encoding="utf-8")
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


def _eod(root: Path, session: str, next_session: str) -> VerifiedEODExecutionInputs:
    ohlcv = root / "fixtures" / f"ohlcv-{session}.parquet"
    model = root / "fixtures" / f"model-{session}.parquet"
    calendar = root / "fixtures" / f"calendar-{session}.csv"
    closes = {ticker: 1000.0 + index for index, ticker in enumerate(TICKERS)}
    pd.DataFrame(
        {
            "ticker": list(TICKERS),
            "session_date": [session] * len(TICKERS),
            "close": [closes[ticker] for ticker in TICKERS],
        }
    ).to_parquet(ohlcv, index=False)
    pd.DataFrame(
        {
            "ticker": list(TICKERS),
            "date": [session] * len(TICKERS),
            "close": [closes[ticker] for ticker in TICKERS],
            "regular_market_value": [1_000_000_000.0] * len(TICKERS),
        }
    ).to_parquet(model, index=False)
    pd.DataFrame({"date": [session, next_session]}).to_csv(calendar, index=False)
    return VerifiedEODExecutionInputs(
        session_date=session,
        next_official_session_date=next_session,
        raw_close_prices=closes,
        regular_market_values={ticker: 1_000_000_000.0 for ticker in TICKERS},
        ohlcv_artifact_path=ohlcv,
        ohlcv_artifact_sha256=_sha(ohlcv),
        model_input_path=model,
        model_input_sha256=_sha(model),
        official_calendar_path=calendar,
        official_calendar_sha256=_sha(calendar),
        _verification_token=_EOD_INPUT_TOKEN,
    )


def _ca(root: Path, session: str, next_session: str, *, event: bool, event_id: str = "DIV-T00") -> VerifiedDividendCAReconciliation:
    attestation = root / "fixtures" / f"ca-{session}.json"
    source = root / "fixtures" / f"ca-source-{session}.json"
    _write(attestation, b"{}\n")
    _write(source, b"{}\n")
    legacy = VerifiedCorporateActionAttestation(
        from_session_date=session,
        through_session_date=next_session,
        covered_tickers=frozenset(TICKERS),
        status="NO_RELEVANT_EVENTS",
        attestation_path=attestation,
        attestation_sha256=_sha(attestation),
        source_path=source,
        source_sha256=_sha(source),
        _verification_token=_CA_ATTESTATION_TOKEN,
    )
    base = VerifiedDividendCAReconciliation(
        from_session_date=session,
        through_session_date=next_session,
        covered_tickers=frozenset(TICKERS),
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
    if not event:
        return base
    ticker = "T00" if event_id == "DIV-T00" else "T01"
    dividend_event = dividend.CertifiedCashDividend(
        event_id=event_id,
        ticker=ticker,
        announcement_timestamp="2026-08-20T10:00:00",
        gross_dividend_per_share_idr=25.0 if event_id == "DIV-T00" else 10.0,
        cum_date="2026-08-25" if event_id == "DIV-T00" else "2026-08-28",
        ex_date="2026-08-26" if event_id == "DIV-T00" else "2026-08-29",
        record_date="2026-08-27" if event_id == "DIV-T00" else "2026-08-29",
        payment_date="2026-08-27" if event_id == "DIV-T00" else "2026-08-29",
        source_evidence_sha256="d" * 64 if event_id == "DIV-T00" else "e" * 64,
    )
    return replace(
        base,
        original_status="CERTIFIED_LIVE",
        relevant_tickers=frozenset({ticker}),
        certified_events=(dividend_event,),
    )


def _open(root: Path, session: str, *, missing: set[str]) -> VerifiedOpenExecutionInputs:
    artifact = root / "fixtures" / f"open-{session}.parquet"
    _write(artifact, b"synthetic-certified-open-" + session.encode("ascii"))
    available = tuple(ticker for ticker in TICKERS if ticker not in missing)
    return VerifiedOpenExecutionInputs(
        session_date=session,
        raw_open_prices={ticker: 1000.0 for ticker in available},
        available_tickers=frozenset(available),
        ohlcv_artifact_path=artifact,
        ohlcv_artifact_sha256=_sha(artifact),
        _verification_token=_OPEN_INPUT_TOKEN,
        authority=AUTHORITY,
        upstream_path=UPSTREAM_PATH,
        field_semantics=FIELD_SEMANTICS,
        fallback_policy=FALLBACK_POLICY,
        transport="DIRECT_IDX_HTTPS",
        transport_policy=TRANSPORT_POLICY,
    )


def _evidence(root: Path, event: dividend.CertifiedCashDividend) -> VerifiedCashDividendEvidence:
    review = root / "fixtures" / f"{event.event_id}-review.json"
    _write(review, json.dumps({"synthetic": True, "event_id": event.event_id}).encode("utf-8") + b"\n")
    return VerifiedCashDividendEvidence(
        event=event,
        review_path=review,
        review_sha256=_sha(review),
        announcement_id=event.event_id,
        announcement_number=event.event_id,
        _verification_token=_VERIFIED_DIVIDEND_EVIDENCE_TOKEN,
    )


def _state_summary(state: dividend.DividendAwarePaperState) -> dict[str, object]:
    return {
        "cash_idr": state.base_state.cash_idr,
        "positions": [
            {"ticker": row.ticker, "shares": row.shares}
            for row in state.base_state.positions
        ],
        "pending_buys": [row.ticker for row in state.base_state.pending_buys],
        "pending_sells": [row.ticker for row in state.base_state.pending_sells],
        "entitlements": [row.event_id for row in state.dividend_ledger.entitlements],
        "receivables": [row.event_id for row in state.dividend_ledger.receivables],
        "settlements": [row.event_id for row in state.dividend_ledger.settlements],
    }


def run(root: Path) -> Path:
    if root.exists() and any(root.iterdir()):
        raise SystemExit(f"REPLAY_OUTPUT_NOT_EMPTY:{root}")
    root.mkdir(parents=True, exist_ok=True)
    (root / "fixtures").mkdir(parents=True, exist_ok=True)
    bootstrap_t0(root, session_date="2026-08-24")
    original_gate = dividend_runtime.gate.verify_cash_dividend_evidence_for_execution
    rows: list[dict[str, object]] = []
    all_evidence_by_path: dict[str, VerifiedCashDividendEvidence] = {}
    previous_score = None
    restart_status = None
    ca_extension = False
    try:
        for index, (decision_date, execution_date) in enumerate(SESSIONS):
            current_score = _score(root, decision_date, index)
            eod = _eod(root, decision_date, execution_date)
            # Introduce a new certified event only at PREOPEN on session 4;
            # the orchestrator must accept it as an explicit CA extension.
            if index == 3:
                prepared_ca = _ca(root, decision_date, execution_date, event=False)
                current_ca = _ca(root, decision_date, execution_date, event=True, event_id="DIV-T01")
                ca_extension = True
            else:
                event_id = "DIV-T01" if index == 4 else "DIV-T00"
                prepared_ca = _ca(root, decision_date, execution_date, event=True, event_id=event_id)
                current_ca = prepared_ca
            evidence_rows = tuple(_evidence(root, event) for event in current_ca.certified_events)
            all_evidence_by_path.update(
                {
                    str(row.review_path.resolve()): row
                    for row in evidence_rows
                }
            )
            dividend_runtime.gate.verify_cash_dividend_evidence_for_execution = (
                lambda **kwargs: all_evidence_by_path[
                    str(Path(kwargs["review_path"]).expanduser().resolve())
                ]
            )
            prepared = prepare_post_eod(
                root,
                current_score=current_score,
                previous_score=previous_score,
                eod_inputs=eod,
                ca_reconciliation=prepared_ca,
            )
            missing = {"T09"} if index == 2 else set()
            open_inputs = _open(root, execution_date, missing=missing)
            result = execute_preopen(
                root,
                prepared_path=prepared.path,
                current_score=current_score,
                previous_score=previous_score,
                eod_inputs=eod,
                open_inputs=open_inputs,
                ca_reconciliation=current_ca,
                dividend_evidence=evidence_rows,
            )
            if index == 1:
                rerun = execute_preopen(
                    root,
                    prepared_path=prepared.path,
                    current_score=current_score,
                    previous_score=previous_score,
                    eod_inputs=eod,
                    open_inputs=open_inputs,
                    ca_reconciliation=current_ca,
                    dividend_evidence=evidence_rows,
                )
                if rerun.status != "ALREADY_COMPLETE" or rerun.file_sha256 != result.file_sha256:
                    raise RuntimeError("REPLAY_EXACT_RERUN_FAILED")
                restart_status = rerun.status
            state = dividend_runtime.load_latest_runtime_snapshot(root).state
            rows.append({
                "decision_session_date": decision_date,
                "execution_session_date": execution_date,
                "status": result.status,
                "execution_sha256": result.file_sha256,
                "runtime_snapshot_sha256": result.runtime_snapshot_sha256,
                "missing_open_tickers": sorted(missing),
                "state": _state_summary(state),
                "outcome_access": False,
            })
            previous_score = current_score
    finally:
        dividend_runtime.gate.verify_cash_dividend_evidence_for_execution = original_gate
    body = {
        "schema_version": "idx_trade_e2e_paper_synthetic_replay_v1",
        "synthetic_only": True,
        "provider_calls": False,
        "protected_outcomes_accessed": False,
        "sessions": rows,
        "session_count": len(rows),
        "exact_rerun_status": restart_status,
        "ca_extension_exercised": ca_extension,
        "final_state": rows[-1]["state"],
    }
    body["summary_sha256"] = _canonical_hash(body)
    summary = root / "acceptance_summary.json"
    summary.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    summary = run(Path(args.output_dir).expanduser().resolve())
    payload = json.loads(summary.read_text(encoding="utf-8"))
    print({
        "status": "SYNTHETIC_REPLAY_PASS",
        "summary_path": str(summary),
        "summary_sha256": _sha(summary),
        "session_count": payload["session_count"],
        "exact_rerun_status": payload["exact_rerun_status"],
        "ca_extension_exercised": payload["ca_extension_exercised"],
        "provider_calls": payload["provider_calls"],
        "protected_outcomes_accessed": payload["protected_outcomes_accessed"],
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
