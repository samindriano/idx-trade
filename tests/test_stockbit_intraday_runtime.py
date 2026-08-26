from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.stockbit_intraday_runtime import (
    JAKARTA,
    SessionJournal,
    parse_chart_payload,
    run_recovery_batch,
    validate_capture_window,
)


SESSION = date(2026, 8, 26)
NOW = datetime(2026, 8, 26, 18, 30, tzinfo=JAKARTA)


def _universe(*tickers: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": list(tickers),
            "company_name": [f"Company {ticker}" for ticker in tickers],
            "listed_from": ["2000-01-01"] * len(tickers),
            "source": ["IDX_STOCK_LIST"] * len(tickers),
        }
    )


def _payload(ticker: str, *, session: date = SESSION) -> dict[str, object]:
    return {
        "symbol": ticker,
        "provider": "stockbit",
        "interval": "intraday",
        "timeframe": "today",
        "tradingDate": session.strftime("%d/%m/%Y"),
        "previousClose": 100,
        "items": [
            {
                "time": f"{session.isoformat()}T09:00:00+07:00",
                "price": 101,
                "change": 1,
                "changePercent": 1,
            },
            {
                "time": f"{session.isoformat()}T15:30:00+07:00",
                "price": 103,
                "change": 3,
                "changePercent": 3,
            },
        ],
    }


def _ok_meta(remaining: int = 20_000) -> dict[str, object]:
    return {
        "attempts": 1,
        "retries": 0,
        "rate_limit_events": 0,
        "errors": [],
        "safe_headers": {"http_status": 200, "remaining_month": str(remaining)},
    }


def _error_meta() -> dict[str, object]:
    return {
        "attempts": 3,
        "retries": 2,
        "rate_limit_events": 0,
        "errors": ["TimeoutError: provider timeout"],
        "safe_headers": {},
    }


def _journal(tmp_path: Path, *tickers: str) -> SessionJournal:
    journal = SessionJournal(tmp_path / "session", expected_date=SESSION)
    journal.freeze_or_verify_universe(_universe(*tickers), captured_at=NOW)
    return journal


def test_parse_chart_payload_preserves_exact_session_contract_without_overclaiming_completeness():
    parsed = parse_chart_payload("BBCA", _payload("BBCA"), expected_date=SESSION)
    assert parsed.status["status"] == "SUCCESS"
    assert parsed.status["points"] == 2
    assert parsed.status["last_price"] == 103.0
    assert parsed.status["coverage_claim"] == "EXACT_SESSION_PROVIDER_PATH_ONLY"
    assert parsed.rows["session_date"].eq(SESSION.isoformat()).all()


def test_parse_chart_payload_rejects_wrong_identity_and_stale_session():
    wrong = parse_chart_payload("BBCA", _payload("BBRI"), expected_date=SESSION)
    assert wrong.rows.empty
    assert wrong.status["status"] == "IDENTITY_OR_PAYLOAD_ERROR"

    stale = parse_chart_payload("BBCA", _payload("BBCA", session=date(2026, 8, 25)), expected_date=SESSION)
    assert stale.rows.empty
    assert stale.status["status"] == "NON_CURRENT_SESSION"


def test_request_error_is_retried_on_recovery_and_prior_attempt_is_preserved(tmp_path: Path):
    journal = _journal(tmp_path, "BBCA", "BBRI")
    first_calls: list[str] = []

    def first_request(ticker: str):
        first_calls.append(ticker)
        if ticker == "BBCA":
            return None, _error_meta()
        return _payload(ticker), _ok_meta()

    first = run_recovery_batch(journal, requester=first_request, now=NOW)
    assert first_calls == ["BBCA", "BBRI"]
    assert first.summary["complete"] is False
    assert first.summary["retryable_count"] == 1
    assert first.summary["admissible_terminal_count"] == 1

    second_calls: list[str] = []

    def second_request(ticker: str):
        second_calls.append(ticker)
        return _payload(ticker), _ok_meta()

    second = run_recovery_batch(journal, requester=second_request, now=NOW)
    assert second_calls == ["BBCA"]
    assert second.summary["complete"] is True
    assert second.summary["admissible_complete"] is True
    assert second.summary["retryable_count"] == 0

    attempts = sorted((journal.root / "attempts" / "BBCA").iterdir())
    assert [path.name for path in attempts] == ["attempt-0001", "attempt-0002"]
    first_status = json.loads((attempts[0] / "status.json").read_text(encoding="utf-8"))
    second_status = json.loads((attempts[1] / "status.json").read_text(encoding="utf-8"))
    assert first_status["status"] == "REQUEST_ERROR"
    assert second_status["status"] == "SUCCESS"


def test_gate_skip_is_terminal_admissible_and_never_refetched(tmp_path: Path):
    journal = _journal(tmp_path, "BBCA", "ZERO")
    journal.record_gate_skip(
        "ZERO",
        captured_at=NOW,
        gate_evidence={"source": "IDX_OFFICIAL", "activity_or": False},
    )
    calls: list[str] = []

    def requester(ticker: str):
        calls.append(ticker)
        return _payload(ticker), _ok_meta()

    result = run_recovery_batch(journal, requester=requester, now=NOW)
    assert calls == ["BBCA"]
    assert result.summary["complete"] is True
    assert result.summary["status_counts"] == {"SUCCESS": 1, "SKIPPED_IDX_NO_ACTIVITY": 1}

    calls.clear()
    second = run_recovery_batch(journal, requester=requester, now=NOW)
    assert calls == []
    assert second.summary["complete"] is True


def test_blocking_payload_error_is_not_silently_retried_or_admitted(tmp_path: Path):
    journal = _journal(tmp_path, "BBCA")

    def wrong_identity(_: str):
        return _payload("BBRI"), _ok_meta()

    first = run_recovery_batch(journal, requester=wrong_identity, now=NOW)
    assert first.summary["all_observed"] is True
    assert first.summary["all_terminal"] is True
    assert first.summary["blocking_count"] == 1
    assert first.summary["complete"] is False

    called = False

    def must_not_call(_: str):
        nonlocal called
        called = True
        raise AssertionError("blocking evidence must not be retried automatically")

    second = run_recovery_batch(journal, requester=must_not_call, now=NOW)
    assert called is False
    assert second.summary["complete"] is False


def test_monthly_quota_reserve_stops_before_unattempted_tickers_and_remains_resumable(tmp_path: Path):
    journal = _journal(tmp_path, "BBCA", "BBRI")
    calls: list[str] = []

    def requester(ticker: str):
        calls.append(ticker)
        return _payload(ticker), _ok_meta(3_000)

    first = run_recovery_batch(
        journal,
        requester=requester,
        now=NOW,
        monthly_quota_reserve=3_000,
    )
    assert first.stop_reason == "MONTHLY_QUOTA_RESERVE_REACHED"
    assert calls == ["BBCA"]
    assert first.summary["missing_count"] == 1
    assert first.summary["complete"] is False

    calls.clear()

    def recovered(ticker: str):
        calls.append(ticker)
        return _payload(ticker), _ok_meta(20_000)

    second = run_recovery_batch(journal, requester=recovered, now=NOW)
    assert calls == ["BBRI"]
    assert second.summary["complete"] is True


def test_attempt_manifest_detects_tampering(tmp_path: Path):
    journal = _journal(tmp_path, "BBCA")
    run_recovery_batch(journal, requester=lambda ticker: (_payload(ticker), _ok_meta()), now=NOW)
    status_path = journal.root / "attempts" / "BBCA" / "attempt-0001" / "status.json"
    status_path.write_text(status_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        journal.latest_status_by_ticker()


def test_frozen_universe_is_write_once_and_hash_verified(tmp_path: Path):
    journal = _journal(tmp_path, "BBCA", "BBRI")
    journal.freeze_or_verify_universe(_universe("BBCA", "BBRI"), captured_at=NOW)
    with pytest.raises(ValueError, match="identity mismatch"):
        journal.freeze_or_verify_universe(_universe("BBCA", "BMRI"), captured_at=NOW)

    journal.universe_path.write_text(journal.universe_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        journal.load_universe()


def test_capture_window_is_today_only_and_post_close():
    validate_capture_window(expected_date=SESSION, now=NOW)
    with pytest.raises(RuntimeError, match="blocked before"):
        validate_capture_window(
            expected_date=SESSION,
            now=datetime(2026, 8, 26, 17, 59, tzinfo=JAKARTA),
        )
    with pytest.raises(ValueError, match="timeframe=today"):
        validate_capture_window(
            expected_date=date(2026, 8, 25),
            now=NOW,
        )
