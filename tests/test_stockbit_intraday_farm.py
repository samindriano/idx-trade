from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pytest

import idx_trade.stockbit_intraday_farm as farm
from idx_trade.provenance import sha256_file
from idx_trade.stockbit_intraday_capture import JAKARTA


EXPECTED_DATE = date(2026, 8, 11)
NOW = datetime(2026, 8, 11, 22, 30, tzinfo=JAKARTA)


def _idx_universe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["BBRI", "BBCA"],
            "company_name": ["Bank Rakyat Indonesia", "Bank Central Asia"],
            "listed_from": ["2003-11-10", "2000-05-31"],
            "listed_to": [pd.NaT, pd.NaT],
            "source": ["IDX_STOCK_LIST", "IDX_STOCK_LIST"],
        }
    )


def _payload(ticker: str) -> dict[str, object]:
    return {
        "symbol": ticker,
        "provider": "stockbit",
        "interval": "intraday",
        "timeframe": "today",
        "tradingDate": "11/08/2026",
        "previousClose": 100,
        "items": [
            {"price": 100, "change": 0, "changePercent": 0},
            {"time": "2026-08-11T09:00:00+07:00", "price": 101, "change": 1, "changePercent": 1},
            {"time": "2026-08-11T09:01:00+07:00", "price": 102, "change": 2, "changePercent": 2},
        ],
    }


def _fake_request_factory(*, remaining_month: int = 20_000):
    calls: list[str] = []

    def fake_request(session, ticker: str, api_key: str):
        calls.append(ticker)
        return _payload(ticker), {
            "attempts": 1,
            "retries": 0,
            "rate_limit_events": 0,
            "errors": [],
            "safe_headers": {
                "http_status": 200,
                "rate_limit_month": "25000",
                "remaining_month": str(remaining_month),
                "rate_limit_minute": "2000",
                "remaining_minute": "1999",
                "plan_expired_present": False,
            },
        }

    return fake_request, calls


def test_current_idx_universe_is_sorted_and_excludes_future_listing():
    frame = _idx_universe()
    future = pd.DataFrame(
        {
            "ticker": ["ZZZZ"],
            "company_name": ["Future"],
            "listed_from": ["2026-08-12"],
            "listed_to": [pd.NaT],
            "source": ["IDX_STOCK_LIST"],
        }
    )
    result = farm._canonical_current_idx_universe(pd.concat([frame, future], ignore_index=True), EXPECTED_DATE)
    assert result["ticker"].tolist() == ["BBCA", "BBRI"]
    assert result["as_of_date"].nunique() == 1
    assert result["as_of_date"].iloc[0] == "2026-08-11"


def test_current_idx_universe_fails_on_duplicate_active_ticker():
    frame = pd.concat([_idx_universe(), _idx_universe().iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate current IDX ticker"):
        farm._canonical_current_idx_universe(frame, EXPECTED_DATE)


def test_frozen_universe_is_hash_verified(tmp_path: Path):
    root = tmp_path / "day"
    universe, metadata, created = farm.prepare_or_load_day(
        root,
        expected_date=EXPECTED_DATE,
        captured_at=NOW,
        fetcher=_idx_universe,
    )
    assert created is True
    assert universe["ticker"].tolist() == ["BBCA", "BBRI"]
    assert metadata["universe_rows"] == 2

    universe_path = root / "universe_snapshot.csv"
    universe_path.write_text(universe_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        farm.prepare_or_load_day(
            root,
            expected_date=EXPECTED_DATE,
            captured_at=NOW,
            fetcher=_idx_universe,
        )


def test_pending_tickers_skip_success_and_optionally_retry_errors(tmp_path: Path):
    root = tmp_path / "day"
    (root / "status").mkdir(parents=True)
    farm._atomic_json(root / "status" / "BBCA.json", {"ticker": "BBCA", "status": "SUCCESS"})
    farm._atomic_json(root / "status" / "BBRI.json", {"ticker": "BBRI", "status": "REQUEST_ERROR"})

    pending, skipped = farm.pending_tickers(root, ["BBCA", "BBRI", "BMRI"], retry_errors=False)
    assert pending == ["BMRI"]
    assert skipped == ["BBCA", "BBRI"]

    pending_retry, skipped_retry = farm.pending_tickers(root, ["BBCA", "BBRI", "BMRI"], retry_errors=True)
    assert pending_retry == ["BBRI", "BMRI"]
    assert skipped_retry == ["BBCA"]


def test_farm_resume_does_not_refetch_successes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "farm"
    fake_request, calls = _fake_request_factory()
    monkeypatch.setattr(farm, "_request_chart", fake_request)

    first = farm.run_farm(
        root,
        expected_date=EXPECTED_DATE,
        api_key="secret",
        now=NOW,
        universe_fetcher=_idx_universe,
        max_new_tickers=10,
        monthly_quota_reserve=3_000,
    )
    assert first["newly_attempted_tickers"] == 2
    assert calls == ["BBCA", "BBRI"]

    calls.clear()
    second = farm.run_farm(
        root,
        expected_date=EXPECTED_DATE,
        api_key="secret",
        now=NOW,
        universe_fetcher=lambda: (_ for _ in ()).throw(AssertionError("must reuse frozen universe")),
        max_new_tickers=10,
        monthly_quota_reserve=3_000,
    )
    assert second["newly_attempted_tickers"] == 0
    assert second["prior_terminal_or_skipped"] == 2
    assert calls == []
    assert second["complete"] is True


def test_monthly_quota_reserve_stops_cleanly_and_remains_resumable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "farm"
    fake_request, calls = _fake_request_factory(remaining_month=3_000)
    monkeypatch.setattr(farm, "_request_chart", fake_request)

    result = farm.run_farm(
        root,
        expected_date=EXPECTED_DATE,
        api_key="secret",
        now=NOW,
        universe_fetcher=_idx_universe,
        max_new_tickers=10,
        monthly_quota_reserve=3_000,
    )
    assert result["stop_reason"] == "MONTHLY_QUOTA_RESERVE_REACHED"
    assert result["newly_attempted_tickers"] == 1
    assert result["complete"] is False
    assert len(calls) == 1
    assert (root / "status" / f"{calls[0]}.json").exists()


def test_today_only_farm_rejects_different_expected_date(tmp_path: Path):
    with pytest.raises(ValueError, match="today-only"):
        farm.run_farm(
            tmp_path / "farm",
            expected_date=date(2026, 8, 10),
            api_key="secret",
            now=NOW,
            universe_fetcher=_idx_universe,
        )


def test_final_summary_and_manifest_are_self_consistent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "farm"
    fake_request, _ = _fake_request_factory()
    monkeypatch.setattr(farm, "_request_chart", fake_request)

    returned = farm.run_farm(
        root,
        expected_date=EXPECTED_DATE,
        api_key="secret",
        now=NOW,
        universe_fetcher=_idx_universe,
        max_new_tickers=10,
    )
    stored = json.loads((root / "final" / "run_summary.json").read_text(encoding="utf-8"))
    assert stored["artifact_manifest_sha256"] == returned["artifact_manifest_sha256"]
    assert returned["artifact_manifest_sha256"] == sha256_file(root / "artifact_manifest.json")
