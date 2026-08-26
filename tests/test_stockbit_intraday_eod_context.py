from __future__ import annotations

from datetime import date
import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.provenance import sha256_file
from idx_trade.stockbit_intraday_eod_context import load_verified_intraday_eod_context
from idx_trade.stockbit_intraday_eod_gate import StockbitIntradayGateError


SESSION = date(2026, 8, 26)
COMPLETE = "COMPLETE_RECORDS_TOTAL_SINGLE_RESPONSE"


def _fixture(root: Path) -> None:
    root.mkdir(parents=True)
    raw = {
        "data": [
            {"StockCode": "BBCA", "Date": SESSION.isoformat(), "Volume": 100, "Frequency": 4, "Value": 1000},
            {"StockCode": "ZERO", "Date": SESSION.isoformat(), "Volume": 0, "Frequency": 0, "Value": 0},
        ],
        "recordsTotal": 2,
        "recordsFiltered": 2,
    }
    raw_path = root / "idx_stock_summary.raw.json"
    raw_path.write_text(json.dumps(raw, sort_keys=True) + "\n", encoding="utf-8")
    summary_path = root / "idx_stock_summary.csv"
    pd.DataFrame(
        {
            "ticker": ["BBCA", "ZERO"],
            "as_of_date": [SESSION.isoformat(), SESSION.isoformat()],
            "volume": [100, 0],
            "frequency": [4, 0],
            "regular_value": [1000, 0],
        }
    ).to_csv(summary_path, index=False, lineterminator="\n")
    evidence_path = root / "session_evidence.parquet"
    pd.DataFrame(
        {
            "ticker": ["BBCA", "BMRI", "ZERO"],
            "session_date": [SESSION.isoformat()] * 3,
            "point_state": ["ACTIVE", "ACTIVE", "NO_TRADE"],
            "evidence_reason": ["test"] * 3,
        }
    ).to_parquet(evidence_path, index=False)

    raw_sha = sha256_file(raw_path)
    summary_sha = sha256_file(summary_path)
    evidence_sha = sha256_file(evidence_path)
    manifest = {
        "schema_version": 1,
        "status": "DATA_READY",
        "session_date": SESSION.isoformat(),
        "outcome_blind": True,
        "forward_outcomes_accessed": False,
        "listed_tickers": 3,
        "point_evidence_rows": 3,
        "evidence_sha256": evidence_sha,
        "stock_summary_sha256": summary_sha,
        "stock_summary_raw_sha256": raw_sha,
        "stock_summary_meta": {
            "requested_date": SESSION.isoformat(),
            "source_ref": "https://www.idx.id/primary/TradingSummary/GetStockSummary?date=20260826",
            "records_total": 2,
            "records_filtered": 2,
            "rows": 2,
            "raw_sha256": raw_sha,
            "completeness_status": COMPLETE,
        },
        "stock_summary_source": {
            "source": "IDX_OFFICIAL",
            "source_ref": "https://www.idx.id/primary/TradingSummary/GetStockSummary?date=20260826",
            "session_date": SESSION.isoformat(),
            "row_count": 2,
            "records_total": 2,
            "records_filtered": 2,
            "completeness_status": COMPLETE,
            "observed_available_at_utc": "2026-08-26T11:30:00+00:00",
        },
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_eod_context_uses_session_evidence_as_intraday_universe(tmp_path: Path):
    root = tmp_path / "session"
    _fixture(root)
    context = load_verified_intraday_eod_context(root, expected_date=SESSION)
    assert context.universe["ticker"].tolist() == ["BBCA", "BMRI", "ZERO"]
    decisions = context.gate.decisions.set_index("ticker")
    assert decisions.loc["BBCA", "gate_decision"] == "FETCH_TRADED"
    assert decisions.loc["ZERO", "gate_decision"] == "SKIP_NO_ACTIVITY"
    # Missing from Stock Summary is conservative fetch, not a fabricated no-trade.
    assert decisions.loc["BMRI", "gate_decision"] == "FETCH_MISSING_SUMMARY"


def test_tampered_eod_universe_evidence_fails_closed(tmp_path: Path):
    root = tmp_path / "session"
    _fixture(root)
    evidence_path = root / "session_evidence.parquet"
    evidence = pd.read_parquet(evidence_path)
    evidence.loc[len(evidence)] = ["BBRI", SESSION.isoformat(), "ACTIVE", "tamper"]
    evidence.to_parquet(evidence_path, index=False)
    with pytest.raises(StockbitIntradayGateError, match="EVIDENCE_SHA_MISMATCH"):
        load_verified_intraday_eod_context(root, expected_date=SESSION)
