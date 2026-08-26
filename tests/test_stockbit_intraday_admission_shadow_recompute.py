from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.official_trading_schedule_v1 import VerifiedOfficialTradingSchedule
from idx_trade.stockbit_intraday_admission import load_verified_session_manifest
from idx_trade.stockbit_intraday_daily_v2 import default_policy, run_daily_cycle
from idx_trade.stockbit_intraday_eod_context import VerifiedIntradayEodContext
from idx_trade.stockbit_intraday_eod_gate import VerifiedEodGate
from idx_trade.stockbit_intraday_runtime import JAKARTA, SessionJournal
from idx_trade.stockbit_intraday_session_v2 import StockbitIntradaySessionError


SESSION = date(2026, 8, 26)
NOW = datetime(2026, 8, 26, 18, 30, tzinfo=JAKARTA)


def _schedule() -> VerifiedOfficialTradingSchedule:
    return VerifiedOfficialTradingSchedule(
        attestation_path=Path("schedule.json"),
        attestation_sha256="a" * 64,
        source_document_path=Path("schedule.pdf"),
        source_document_sha256="b" * 64,
        source_reference="IDX",
        coverage_start=SESSION.isoformat(),
        coverage_end=SESSION.isoformat(),
        holiday_dates=(),
        session_dates=(SESSION.isoformat(),),
    )


def _context(tmp_path: Path) -> VerifiedIntradayEodContext:
    universe = pd.DataFrame({"ticker": ["ZERO"]})
    summary = pd.DataFrame(
        {
            "ticker": ["ZERO"],
            "as_of_date": [SESSION.isoformat()],
            "volume": [0],
            "frequency": [0],
            "regular_value": [0],
        }
    )
    decisions = summary[["ticker", "volume", "frequency", "regular_value"]].copy()
    decisions["activity_or"] = False
    decisions["idx_summary_present"] = True
    decisions["gate_decision"] = "SKIP_NO_ACTIVITY"
    decisions["would_fetch_stockbit"] = False
    gate = VerifiedEodGate(
        session_date=SESSION.isoformat(),
        manifest_path=tmp_path / "eod" / "manifest.json",
        manifest_sha256="c" * 64,
        stock_summary_path=tmp_path / "eod" / "idx_stock_summary.csv",
        stock_summary_sha256="d" * 64,
        stock_summary_raw_path=tmp_path / "eod" / "idx_stock_summary.raw.json",
        stock_summary_raw_sha256="e" * 64,
        source_ref="IDX",
        observed_available_at_utc="2026-08-26T11:30:00+00:00",
        records_total=1,
        records_filtered=1,
        summary=summary,
        decisions=decisions,
    )
    return VerifiedIntradayEodContext(
        session_date=SESSION.isoformat(),
        session_dir=tmp_path / "eod",
        eod_manifest_sha256="c" * 64,
        universe_evidence_path=tmp_path / "eod" / "session_evidence.parquet",
        universe_evidence_sha256="f" * 64,
        universe=universe,
        gate=gate,
    )


def _not_found_meta() -> dict[str, object]:
    return {
        "attempts": 1,
        "retries": 0,
        "rate_limit_events": 0,
        "errors": ["HTTP_404"],
        "safe_headers": {"http_status": 404, "remaining_month": "20000"},
    }


def test_shadow_metrics_are_recomputed_from_immutable_provider_attempts(tmp_path: Path):
    journal = SessionJournal(tmp_path / "journal", expected_date=SESSION)
    result = run_daily_cycle(
        expected_date=SESSION,
        now=NOW,
        schedule=_schedule(),
        context=_context(tmp_path),
        journal=journal,
        policy=default_policy(),
        requester=lambda _: (None, _not_found_meta()),
    )
    assert result.status == "ADMISSIBLE_COMPLETE"
    assert result.shadow_metrics == {
        "false_negative": 0,
        "false_positive": 0,
        "actual_success": 0,
        "actual_no_chart_404": 1,
        "certification_eligible": True,
    }
    assert load_verified_session_manifest(journal) is not None

    manifest_path = journal.root / "session_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["shadow_metrics"]["false_negative"] = 1
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        StockbitIntradaySessionError,
        match="SESSION_MANIFEST_SHADOW_METRICS_RECOMPUTE_MISMATCH",
    ):
        load_verified_session_manifest(journal)
