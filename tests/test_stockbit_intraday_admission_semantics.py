from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.stockbit_intraday_admission import load_verified_session_manifest
from idx_trade.stockbit_intraday_eod_context import VerifiedIntradayEodContext
from idx_trade.stockbit_intraday_eod_gate import VerifiedEodGate, gate_skip_evidence
from idx_trade.stockbit_intraday_runtime import JAKARTA, SessionJournal
from idx_trade.stockbit_intraday_session_v2 import (
    StockbitIntradaySessionError,
    bind_gate_snapshot,
    bind_run_contract,
    finalize_admissible_session,
)


SESSION = date(2026, 8, 26)
NOW = datetime(2026, 8, 26, 18, 30, tzinfo=JAKARTA)


def _context(tmp_path: Path) -> VerifiedIntradayEodContext:
    universe = pd.DataFrame({"ticker": ["BBCA", "ZERO"]})
    summary = pd.DataFrame(
        {
            "ticker": ["BBCA", "ZERO"],
            "as_of_date": [SESSION.isoformat(), SESSION.isoformat()],
            "volume": [100, 0],
            "frequency": [1, 0],
            "regular_value": [1000, 0],
        }
    )
    decisions = summary[["ticker", "volume", "frequency", "regular_value"]].copy()
    decisions["activity_or"] = [True, False]
    decisions["idx_summary_present"] = True
    decisions["gate_decision"] = ["FETCH_TRADED", "SKIP_NO_ACTIVITY"]
    decisions["would_fetch_stockbit"] = [True, False]
    gate = VerifiedEodGate(
        session_date=SESSION.isoformat(),
        manifest_path=tmp_path / "external" / "manifest.json",
        manifest_sha256="a" * 64,
        stock_summary_path=tmp_path / "external" / "idx_stock_summary.csv",
        stock_summary_sha256="b" * 64,
        stock_summary_raw_path=tmp_path / "external" / "idx_stock_summary.raw.json",
        stock_summary_raw_sha256="c" * 64,
        source_ref="IDX",
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


def _journal(tmp_path: Path) -> tuple[SessionJournal, VerifiedIntradayEodContext]:
    context = _context(tmp_path)
    source = pd.DataFrame(
        {
            "ticker": ["BBCA", "ZERO"],
            "company_name": ["BBCA", "ZERO"],
            "listed_from": ["2000-01-01", "2000-01-01"],
            "source": ["IDX", "IDX"],
        }
    )
    journal = SessionJournal(tmp_path / "journal", expected_date=SESSION)
    journal.freeze_or_verify_universe(source, captured_at=NOW)
    gate_sha = bind_gate_snapshot(journal, context)
    bind_run_contract(
        journal,
        run_mode="ENFORCE",
        schedule_attestation_sha256="e" * 64,
        gate_manifest_sha256=gate_sha,
    )
    journal.record_provider_attempt(
        "BBCA",
        payload={
            "symbol": "BBCA",
            "provider": "stockbit",
            "interval": "intraday",
            "timeframe": "today",
            "tradingDate": "26/08/2026",
            "previousClose": 100,
            "items": [{"time": "2026-08-26T09:00:00+07:00", "price": 101}],
        },
        request_meta={
            "attempts": 1,
            "retries": 0,
            "rate_limit_events": 0,
            "errors": [],
            "safe_headers": {"http_status": 200},
        },
        captured_at=NOW,
    )
    skip = context.gate.decisions.set_index("ticker").loc["ZERO"].to_dict()
    journal.record_gate_skip(
        "ZERO",
        captured_at=NOW,
        gate_evidence=gate_skip_evidence(context.gate, skip),
    )
    finalize_admissible_session(journal, shadow_metrics=None)
    return journal, context


def test_verified_final_manifest_recomputes_semantic_parents(tmp_path: Path):
    journal, _ = _journal(tmp_path)
    verified = load_verified_session_manifest(journal)
    assert verified is not None

    path = journal.root / "session_manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["eod_manifest_sha256"] = "f" * 64
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(StockbitIntradaySessionError, match="EOD_BINDING_MISMATCH"):
        load_verified_session_manifest(journal)


def test_enforce_final_manifest_rejects_injected_shadow_metrics(tmp_path: Path):
    journal, _ = _journal(tmp_path)
    path = journal.root / "session_manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["shadow_metrics"] = {
        "false_negative": 0,
        "false_positive": 0,
        "actual_success": 1,
        "actual_no_chart_404": 0,
        "certification_eligible": True,
    }
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(StockbitIntradaySessionError, match="ENFORCE_SHADOW_METRICS_PRESENT"):
        load_verified_session_manifest(journal)
