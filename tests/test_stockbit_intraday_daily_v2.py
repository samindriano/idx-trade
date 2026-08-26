from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd

from idx_trade.official_trading_schedule_v1 import VerifiedOfficialTradingSchedule
from idx_trade.stockbit_intraday_daily_v2 import default_policy, run_daily_cycle
from idx_trade.stockbit_intraday_eod_context import VerifiedIntradayEodContext
from idx_trade.stockbit_intraday_eod_gate import VerifiedEodGate
from idx_trade.stockbit_intraday_runtime import JAKARTA, SessionJournal


SESSION = date(2026, 8, 26)
NOW = datetime(2026, 8, 26, 18, 30, tzinfo=JAKARTA)


def _schedule(*, include_session: bool = True) -> VerifiedOfficialTradingSchedule:
    sessions = (SESSION.isoformat(),) if include_session else ("2026-08-25",)
    return VerifiedOfficialTradingSchedule(
        attestation_path=Path("schedule.json"),
        attestation_sha256="e" * 64,
        source_document_path=Path("schedule-source.pdf"),
        source_document_sha256="f" * 64,
        source_reference="IDX official schedule",
        coverage_start="2026-08-25",
        coverage_end="2026-08-26",
        holiday_dates=(SESSION.isoformat(),) if not include_session else (),
        session_dates=sessions,
    )


def _context(tmp_path: Path, *, bbca_activity: bool = True, zero_activity: bool = False) -> VerifiedIntradayEodContext:
    universe = pd.DataFrame({"ticker": ["BBCA", "ZERO"]})
    bbca_volume = 100 if bbca_activity else 0
    zero_volume = 100 if zero_activity else 0
    summary = pd.DataFrame(
        {
            "ticker": ["BBCA", "ZERO"],
            "as_of_date": [SESSION.isoformat()] * 2,
            "volume": [bbca_volume, zero_volume],
            "frequency": [1 if bbca_activity else 0, 1 if zero_activity else 0],
            "regular_value": [1000 if bbca_activity else 0, 1000 if zero_activity else 0],
        }
    )
    decisions = summary[["ticker", "volume", "frequency", "regular_value"]].copy()
    decisions["activity_or"] = decisions[["volume", "frequency", "regular_value"]].gt(0).any(axis=1)
    decisions["idx_summary_present"] = True
    decisions["gate_decision"] = decisions["activity_or"].map({True: "FETCH_TRADED", False: "SKIP_NO_ACTIVITY"})
    decisions["would_fetch_stockbit"] = decisions["activity_or"]
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


def _payload(ticker: str) -> dict[str, object]:
    return {
        "symbol": ticker,
        "provider": "stockbit",
        "interval": "intraday",
        "timeframe": "today",
        "tradingDate": "26/08/2026",
        "previousClose": 100,
        "items": [{"time": "2026-08-26T09:00:00+07:00", "price": 101, "change": 1, "changePercent": 1}],
    }


def _ok_meta() -> dict[str, object]:
    return {
        "attempts": 1,
        "retries": 0,
        "rate_limit_events": 0,
        "errors": [],
        "safe_headers": {"http_status": 200, "remaining_month": "20000"},
    }


def _404_meta() -> dict[str, object]:
    return {
        "attempts": 1,
        "retries": 0,
        "rate_limit_events": 0,
        "errors": ["HTTP_404"],
        "safe_headers": {"http_status": 404, "remaining_month": "20000"},
    }


def _timeout_meta() -> dict[str, object]:
    return {
        "attempts": 3,
        "retries": 2,
        "rate_limit_events": 0,
        "errors": ["TimeoutError"],
        "safe_headers": {},
    }


def test_holiday_noop_makes_zero_provider_calls():
    called = False

    def requester(_: str):
        nonlocal called
        called = True
        raise AssertionError("holiday must not call provider")

    result = run_daily_cycle(
        expected_date=SESSION,
        now=NOW,
        schedule=_schedule(include_session=False),
        context=None,
        journal=None,
        policy=default_policy(),
        requester=requester,
    )
    assert result.status == "WEEKEND_OR_HOLIDAY_NOOP"
    assert result.provider_calls_attempted == 0
    assert called is False


def test_waits_for_canonical_eod_before_any_provider_call():
    called = False

    def requester(_: str):
        nonlocal called
        called = True
        raise AssertionError("EOD gate must exist first")

    result = run_daily_cycle(
        expected_date=SESSION,
        now=NOW,
        schedule=_schedule(),
        context=None,
        journal=None,
        policy=default_policy(),
        requester=requester,
    )
    assert result.status == "WAITING_CANONICAL_EOD_GATE"
    assert result.provider_calls_attempted == 0
    assert called is False


def test_enforce_fetches_only_traded_and_completes(tmp_path: Path):
    context = _context(tmp_path)
    journal = SessionJournal(tmp_path / "journal", expected_date=SESSION)
    calls: list[str] = []

    def requester(ticker: str):
        calls.append(ticker)
        return _payload(ticker), _ok_meta()

    policy = default_policy()
    policy["mode"] = "ENFORCE"
    result = run_daily_cycle(
        expected_date=SESSION,
        now=NOW,
        schedule=_schedule(),
        context=context,
        journal=journal,
        policy=policy,
        requester=requester,
    )
    assert calls == ["BBCA"]
    assert result.status == "ADMISSIBLE_COMPLETE"
    assert result.run_mode == "ENFORCE"
    assert result.summary["status_counts"] == {"SUCCESS": 1, "SKIPPED_IDX_NO_ACTIVITY": 1}
    assert result.policy["enforced_sessions_since_recheck"] == 1


def test_shadow_full_universe_reconciles_only_404_zero_activity(tmp_path: Path):
    context = _context(tmp_path)
    journal = SessionJournal(tmp_path / "journal", expected_date=SESSION)
    calls: list[str] = []

    def requester(ticker: str):
        calls.append(ticker)
        return (_payload(ticker), _ok_meta()) if ticker == "BBCA" else (None, _404_meta())

    result = run_daily_cycle(
        expected_date=SESSION,
        now=NOW,
        schedule=_schedule(),
        context=context,
        journal=journal,
        policy=default_policy(),
        requester=requester,
    )
    assert calls == ["BBCA", "ZERO"]
    assert result.status == "ADMISSIBLE_COMPLETE"
    assert result.shadow_metrics["false_negative"] == 0
    assert result.shadow_metrics["certification_eligible"] is True
    assert result.policy["consecutive_zero_fn_shadow_sessions"] == 1


def test_transient_failure_waits_then_retries_without_policy_event(tmp_path: Path):
    context = _context(tmp_path)
    journal = SessionJournal(tmp_path / "journal", expected_date=SESSION)
    first_calls: list[str] = []

    def first(ticker: str):
        first_calls.append(ticker)
        return (None, _timeout_meta()) if ticker == "BBCA" else (None, _404_meta())

    first_result = run_daily_cycle(
        expected_date=SESSION,
        now=NOW,
        schedule=_schedule(),
        context=context,
        journal=journal,
        policy=default_policy(),
        requester=first,
    )
    assert first_result.status == "WAITING_RECOVERY_RETRY"
    assert first_result.policy["history"] == []

    second_calls: list[str] = []

    def second(ticker: str):
        second_calls.append(ticker)
        return _payload(ticker), _ok_meta()

    second_result = run_daily_cycle(
        expected_date=SESSION,
        now=datetime(2026, 8, 26, 19, 30, tzinfo=JAKARTA),
        schedule=_schedule(),
        context=context,
        journal=journal,
        policy=first_result.policy,
        requester=second,
    )
    assert first_calls == ["BBCA", "ZERO"]
    assert second_calls == ["BBCA"]
    assert second_result.status == "ADMISSIBLE_COMPLETE"
    assert len(second_result.policy["history"]) == 1


def test_gate_false_negative_is_observed_and_resets_shadow_progress(tmp_path: Path):
    context = _context(tmp_path, bbca_activity=True, zero_activity=False)
    journal = SessionJournal(tmp_path / "journal", expected_date=SESSION)
    policy = default_policy()
    policy["consecutive_zero_fn_shadow_sessions"] = 2
    result = run_daily_cycle(
        expected_date=SESSION,
        now=NOW,
        schedule=_schedule(),
        context=context,
        journal=journal,
        policy=policy,
        requester=lambda ticker: (_payload(ticker), _ok_meta()),
    )
    assert result.status == "ADMISSIBLE_COMPLETE"
    assert result.shadow_metrics["false_negative"] == 1
    assert result.policy["mode"] == "SHADOW"
    assert result.policy["consecutive_zero_fn_shadow_sessions"] == 0


def test_404_for_gate_fetch_is_hard_block_not_fake_completion(tmp_path: Path):
    context = _context(tmp_path, bbca_activity=True, zero_activity=False)
    journal = SessionJournal(tmp_path / "journal", expected_date=SESSION)

    def requester(ticker: str):
        return (None, _404_meta())

    result = run_daily_cycle(
        expected_date=SESSION,
        now=NOW,
        schedule=_schedule(),
        context=context,
        journal=journal,
        policy=default_policy(),
        requester=requester,
    )
    assert result.status == "BLOCKED_NON_ADMISSIBLE_TERMINAL"
    assert result.summary["complete"] is False
    assert result.policy["history"] == []


def test_final_shadow_rerun_is_idempotent_and_makes_zero_calls(tmp_path: Path):
    context = _context(tmp_path)
    journal = SessionJournal(tmp_path / "journal", expected_date=SESSION)

    def first(ticker: str):
        return (_payload(ticker), _ok_meta()) if ticker == "BBCA" else (None, _404_meta())

    first_result = run_daily_cycle(
        expected_date=SESSION,
        now=NOW,
        schedule=_schedule(),
        context=context,
        journal=journal,
        policy=default_policy(),
        requester=first,
    )
    assert first_result.status == "ADMISSIBLE_COMPLETE"
    calls: list[str] = []

    def must_not_call(ticker: str):
        calls.append(ticker)
        raise AssertionError("final session replay must not call provider")

    second_result = run_daily_cycle(
        expected_date=SESSION,
        now=datetime(2026, 8, 26, 20, 30, tzinfo=JAKARTA),
        schedule=_schedule(),
        context=context,
        journal=journal,
        policy=first_result.policy,
        requester=must_not_call,
    )
    assert calls == []
    assert second_result.session_manifest_sha256 == first_result.session_manifest_sha256
    assert second_result.policy_event_applied is False
