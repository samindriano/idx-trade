from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd

from idx_trade.e2e_paper_cloud_runtime_v1 import LocalConditionalStore
from idx_trade.official_trading_schedule_v1 import VerifiedOfficialTradingSchedule
from idx_trade.stockbit_intraday_cloud_archive import StockbitIntradayCloudArchive
from idx_trade.stockbit_intraday_cloud_runner import run_cloud_slot
from idx_trade.stockbit_intraday_eod_context import VerifiedIntradayEodContext
from idx_trade.stockbit_intraday_eod_gate import VerifiedEodGate
from idx_trade.stockbit_intraday_runtime import JAKARTA


SESSION = date(2026, 8, 26)


def _schedule(*, session: bool = True) -> VerifiedOfficialTradingSchedule:
    return VerifiedOfficialTradingSchedule(
        attestation_path=Path("schedule.json"),
        attestation_sha256="a" * 64,
        source_document_path=Path("schedule.pdf"),
        source_document_sha256="b" * 64,
        source_reference="IDX",
        coverage_start="2026-08-25",
        coverage_end="2026-08-26",
        holiday_dates=() if session else (SESSION.isoformat(),),
        session_dates=(SESSION.isoformat(),) if session else ("2026-08-25",),
    )


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
        manifest_path=tmp_path / "eod" / "manifest.json",
        manifest_sha256="c" * 64,
        stock_summary_path=tmp_path / "eod" / "idx_stock_summary.csv",
        stock_summary_sha256="d" * 64,
        stock_summary_raw_path=tmp_path / "eod" / "idx_stock_summary.raw.json",
        stock_summary_raw_sha256="e" * 64,
        source_ref="IDX",
        observed_available_at_utc="2026-08-26T11:30:00+00:00",
        records_total=2,
        records_filtered=2,
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


def _payload(ticker: str) -> dict[str, object]:
    return {
        "symbol": ticker,
        "provider": "stockbit",
        "interval": "intraday",
        "timeframe": "today",
        "tradingDate": "26/08/2026",
        "previousClose": 100,
        "items": [{"time": "2026-08-26T09:00:00+07:00", "price": 101}],
    }


def _ok() -> dict[str, object]:
    return {
        "attempts": 1,
        "retries": 0,
        "rate_limit_events": 0,
        "errors": [],
        "safe_headers": {"http_status": 200, "remaining_month": "20000"},
    }


def _timeout() -> dict[str, object]:
    return {
        "attempts": 3,
        "retries": 2,
        "rate_limit_events": 0,
        "errors": ["TimeoutError"],
        "safe_headers": {},
    }


def _not_found() -> dict[str, object]:
    return {
        "attempts": 1,
        "retries": 0,
        "rate_limit_events": 0,
        "errors": ["HTTP_404"],
        "safe_headers": {"http_status": 404, "remaining_month": "20000"},
    }


def _archive(tmp_path: Path) -> tuple[LocalConditionalStore, StockbitIntradayCloudArchive]:
    store = LocalConditionalStore(tmp_path / "cloud")
    return store, StockbitIntradayCloudArchive(store)


def test_waiting_eod_slot_commits_without_provider_call_then_next_slot_can_start(tmp_path: Path):
    _, archive = _archive(tmp_path)
    calls: list[str] = []

    def no_call(ticker: str):
        calls.append(ticker)
        raise AssertionError("provider must not be called before canonical EOD")

    first = run_cloud_slot(
        expected_date=SESSION,
        slot="1830",
        now=datetime(2026, 8, 26, 18, 30, tzinfo=JAKARTA),
        schedule=_schedule(),
        context=None,
        archive=archive,
        journal_root=tmp_path / "journal",
        requester=no_call,
        code_identity={"commit": "1" * 40},
    )
    assert first.status == "WAITING_CANONICAL_EOD_GATE"
    assert calls == []

    calls2: list[str] = []

    def full(ticker: str):
        calls2.append(ticker)
        return (_payload(ticker), _ok()) if ticker == "BBCA" else (None, _not_found())

    second = run_cloud_slot(
        expected_date=SESSION,
        slot="1930",
        now=datetime(2026, 8, 26, 19, 30, tzinfo=JAKARTA),
        schedule=_schedule(),
        context=_context(tmp_path),
        archive=archive,
        journal_root=tmp_path / "journal2",
        requester=full,
        code_identity={"commit": "1" * 40},
    )
    assert second.status == "ADMISSIBLE_COMPLETE"
    assert calls2 == ["BBCA", "ZERO"]


def test_transient_slot_snapshot_restores_and_next_slot_retries_only_failed_ticker(tmp_path: Path):
    _, archive = _archive(tmp_path)
    context = _context(tmp_path)
    first_calls: list[str] = []

    def first_request(ticker: str):
        first_calls.append(ticker)
        return (None, _timeout()) if ticker == "BBCA" else (None, _not_found())

    first = run_cloud_slot(
        expected_date=SESSION,
        slot="1930",
        now=datetime(2026, 8, 26, 19, 30, tzinfo=JAKARTA),
        schedule=_schedule(),
        context=context,
        archive=archive,
        journal_root=tmp_path / "journal-first",
        requester=first_request,
        code_identity={"commit": "2" * 40},
    )
    assert first.status == "WAITING_RECOVERY_RETRY"
    assert first_calls == ["BBCA", "ZERO"]

    second_calls: list[str] = []

    def second_request(ticker: str):
        second_calls.append(ticker)
        return _payload(ticker), _ok()

    second = run_cloud_slot(
        expected_date=SESSION,
        slot="2030",
        now=datetime(2026, 8, 26, 20, 30, tzinfo=JAKARTA),
        schedule=_schedule(),
        context=context,
        archive=archive,
        journal_root=tmp_path / "journal-second",
        requester=second_request,
        code_identity={"commit": "2" * 40},
    )
    assert second.status == "ADMISSIBLE_COMPLETE"
    assert second_calls == ["BBCA"]
    checkpoint = archive.load_policy_checkpoint(SESSION)
    assert checkpoint is not None
    assert checkpoint["policy"]["consecutive_zero_fn_shadow_sessions"] == 1


def test_existing_final_slot_repairs_missing_policy_checkpoint_without_provider_call(tmp_path: Path):
    store, archive = _archive(tmp_path)
    context = _context(tmp_path)

    final = run_cloud_slot(
        expected_date=SESSION,
        slot="1930",
        now=datetime(2026, 8, 26, 19, 30, tzinfo=JAKARTA),
        schedule=_schedule(),
        context=context,
        archive=archive,
        journal_root=tmp_path / "journal",
        requester=lambda ticker: (_payload(ticker), _ok()) if ticker == "BBCA" else (None, _not_found()),
        code_identity={"commit": "3" * 40},
    )
    assert final.status == "ADMISSIBLE_COMPLETE"
    store._path(archive.policy_key(SESSION)).unlink()

    called = False

    def must_not_call(_: str):
        nonlocal called
        called = True
        raise AssertionError("existing final slot must be authoritative")

    replay = run_cloud_slot(
        expected_date=SESSION,
        slot="1930",
        now=datetime(2026, 8, 26, 20, 0, tzinfo=JAKARTA),
        schedule=_schedule(),
        context=None,
        archive=archive,
        journal_root=tmp_path / "unused",
        requester=must_not_call,
        code_identity={"commit": "3" * 40},
    )
    assert replay.commit_sha256 == final.commit_sha256
    assert called is False
    assert archive.load_policy_checkpoint(SESSION) is not None


def test_holiday_cloud_slot_is_noop_and_zero_provider_calls(tmp_path: Path):
    _, archive = _archive(tmp_path)
    called = False

    def requester(_: str):
        nonlocal called
        called = True
        raise AssertionError("holiday must not call provider")

    commit = run_cloud_slot(
        expected_date=SESSION,
        slot="1830",
        now=datetime(2026, 8, 26, 18, 30, tzinfo=JAKARTA),
        schedule=_schedule(session=False),
        context=None,
        archive=archive,
        journal_root=tmp_path / "journal",
        requester=requester,
        code_identity={"commit": "4" * 40},
    )
    assert commit.status == "WEEKEND_OR_HOLIDAY_NOOP"
    assert called is False
