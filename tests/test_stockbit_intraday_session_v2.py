from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.stockbit_intraday_eod_context import VerifiedIntradayEodContext
from idx_trade.stockbit_intraday_eod_gate import VerifiedEodGate, gate_skip_evidence
from idx_trade.stockbit_intraday_runtime import JAKARTA, SessionJournal
from idx_trade.stockbit_intraday_session_v2 import (
    StockbitIntradaySessionError,
    bind_gate_snapshot,
    bind_run_contract,
    finalize_admissible_session,
    verify_bound_gate,
)


SESSION = date(2026, 8, 26)
NOW = datetime(2026, 8, 26, 18, 30, tzinfo=JAKARTA)


def _source_universe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["BBCA", "ZERO"],
            "company_name": ["BBCA", "ZERO"],
            "listed_from": ["2000-01-01", "2000-01-01"],
            "source": ["IDX_STOCK_LIST", "IDX_STOCK_LIST"],
        }
    )


def _context(tmp_path: Path) -> VerifiedIntradayEodContext:
    universe = pd.DataFrame({"ticker": ["BBCA", "ZERO"]})
    summary = pd.DataFrame(
        {
            "ticker": ["BBCA", "ZERO"],
            "as_of_date": [SESSION.isoformat()] * 2,
            "volume": [100, 0],
            "frequency": [5, 0],
            "regular_value": [1000, 0],
        }
    )
    decisions = pd.DataFrame(
        {
            "ticker": ["BBCA", "ZERO"],
            "volume": [100.0, 0.0],
            "frequency": [5.0, 0.0],
            "regular_value": [1000.0, 0.0],
            "activity_or": [True, False],
            "idx_summary_present": [True, True],
            "gate_decision": ["FETCH_TRADED", "SKIP_NO_ACTIVITY"],
            "would_fetch_stockbit": [True, False],
        }
    )
    gate = VerifiedEodGate(
        session_date=SESSION.isoformat(),
        manifest_path=tmp_path / "external" / "manifest.json",
        manifest_sha256="a" * 64,
        stock_summary_path=tmp_path / "external" / "idx_stock_summary.csv",
        stock_summary_sha256="b" * 64,
        stock_summary_raw_path=tmp_path / "external" / "idx_stock_summary.raw.json",
        stock_summary_raw_sha256="c" * 64,
        source_ref="https://www.idx.id/primary/TradingSummary/GetStockSummary?date=20260826",
        observed_available_at_utc="2026-08-26T11:30:00+00:00",
        records_total=2,
        records_filtered=2,
        summary=summary,
        decisions=decisions,
    )
    return VerifiedIntradayEodContext(
        session_date=SESSION.isoformat(),
        session_dir=tmp_path / "external",
        eod_manifest_sha256="a" * 64,
        universe_evidence_path=tmp_path / "external" / "session_evidence.parquet",
        universe_evidence_sha256="d" * 64,
        universe=universe,
        gate=gate,
    )


def _payload() -> dict[str, object]:
    return {
        "symbol": "BBCA",
        "provider": "stockbit",
        "interval": "intraday",
        "timeframe": "today",
        "tradingDate": "26/08/2026",
        "previousClose": 100,
        "items": [{"time": "2026-08-26T09:00:00+07:00", "price": 101, "change": 1, "changePercent": 1}],
    }


def _meta() -> dict[str, object]:
    return {
        "attempts": 1,
        "retries": 0,
        "rate_limit_events": 0,
        "errors": [],
        "safe_headers": {"http_status": 200, "remaining_month": "20000"},
    }


def _journal(tmp_path: Path) -> SessionJournal:
    journal = SessionJournal(tmp_path / "journal", expected_date=SESSION)
    journal.freeze_or_verify_universe(_source_universe(), captured_at=NOW)
    return journal


def test_session_contract_freezes_gate_schedule_and_run_mode(tmp_path: Path):
    journal = _journal(tmp_path)
    gate_sha = bind_gate_snapshot(journal, _context(tmp_path))
    first = bind_run_contract(
        journal,
        run_mode="SHADOW",
        schedule_attestation_sha256="e" * 64,
        gate_manifest_sha256=gate_sha,
    )
    second = bind_run_contract(
        journal,
        run_mode="SHADOW",
        schedule_attestation_sha256="e" * 64,
        gate_manifest_sha256=gate_sha,
    )
    assert first == second
    with pytest.raises(StockbitIntradaySessionError, match="IMMUTABILITY_CONFLICT"):
        bind_run_contract(
            journal,
            run_mode="ENFORCE",
            schedule_attestation_sha256="e" * 64,
            gate_manifest_sha256=gate_sha,
        )


def test_final_manifest_requires_admissible_complete_and_is_idempotent(tmp_path: Path):
    journal = _journal(tmp_path)
    context = _context(tmp_path)
    gate_sha = bind_gate_snapshot(journal, context)
    bind_run_contract(
        journal,
        run_mode="ENFORCE",
        schedule_attestation_sha256="e" * 64,
        gate_manifest_sha256=gate_sha,
    )
    with pytest.raises(StockbitIntradaySessionError, match="NOT_ADMISSIBLE_COMPLETE"):
        finalize_admissible_session(journal, shadow_metrics=None)

    journal.record_provider_attempt("BBCA", payload=_payload(), request_meta=_meta(), captured_at=NOW)
    skip_row = context.gate.decisions.set_index("ticker").loc["ZERO"].to_dict()
    journal.record_gate_skip(
        "ZERO",
        captured_at=NOW,
        gate_evidence=gate_skip_evidence(context.gate, skip_row),
    )
    manifest, first_sha = finalize_admissible_session(journal, shadow_metrics=None)
    replay, second_sha = finalize_admissible_session(journal, shadow_metrics=None)
    assert first_sha == second_sha
    assert manifest == replay
    assert manifest["status"] == "ADMISSIBLE_COMPLETE"
    assert manifest["completion"]["complete"] is True
    assert manifest["synthetic_fill_used"] is False
    assert manifest["retroactive_capture_used"] is False


def test_bound_gate_tamper_is_detected(tmp_path: Path):
    journal = _journal(tmp_path)
    bind_gate_snapshot(journal, _context(tmp_path))
    path = journal.root / "gate" / "decisions.csv"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(StockbitIntradaySessionError, match="DECISIONS_SHA_MISMATCH"):
        verify_bound_gate(journal)
