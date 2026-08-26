from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pytest

from idx_trade.stockbit_intraday_recovery import (
    NO_CHART_404,
    QUOTA_EXHAUSTED,
    REQUEST_ERROR,
    REQUEST_TERMINAL_ERROR,
    SKIPPED_IDX_NO_ACTIVITY,
)
from idx_trade.stockbit_intraday_runtime import (
    JAKARTA,
    SessionJournal,
    classify_request_failure,
    run_recovery_batch,
)


SESSION = date(2026, 8, 26)
NOW = datetime(2026, 8, 26, 18, 30, tzinfo=JAKARTA)


def _universe(*tickers: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": list(tickers),
            "company_name": list(tickers),
            "listed_from": ["2000-01-01"] * len(tickers),
            "source": ["IDX_STOCK_LIST"] * len(tickers),
        }
    )


def _payload(ticker: str) -> dict[str, object]:
    return {
        "symbol": ticker,
        "provider": "stockbit",
        "interval": "intraday",
        "timeframe": "today",
        "tradingDate": "26/08/2026",
        "previousClose": 100,
        "items": [
            {
                "time": "2026-08-26T09:00:00+07:00",
                "price": 101,
                "change": 1,
                "changePercent": 1,
            }
        ],
    }


def _meta(status: int, *errors: str, window: str | None = None) -> dict[str, object]:
    result: dict[str, object] = {
        "attempts": 1,
        "retries": 0,
        "rate_limit_events": 1 if status == 429 else 0,
        "errors": list(errors),
        "safe_headers": {"http_status": status, "remaining_month": "20000"},
    }
    if window is not None:
        result["rate_limit_window"] = window
    return result


def _journal(tmp_path: Path, *tickers: str) -> SessionJournal:
    journal = SessionJournal(tmp_path / "session", expected_date=SESSION)
    journal.freeze_or_verify_universe(_universe(*tickers), captured_at=NOW)
    return journal


def test_request_failure_classification_separates_retryable_from_terminal():
    assert classify_request_failure(_meta(404, "HTTP_404")) == NO_CHART_404
    assert classify_request_failure(_meta(401, "HTTP_401")) == REQUEST_TERMINAL_ERROR
    assert classify_request_failure(_meta(403, "HTTP_403")) == REQUEST_TERMINAL_ERROR
    assert classify_request_failure(_meta(429, "HTTP_429:month", window="month")) == QUOTA_EXHAUSTED
    assert classify_request_failure(_meta(429, "HTTP_429:minute", window="minute")) == REQUEST_ERROR
    assert classify_request_failure(_meta(503, "HTTP_503")) == REQUEST_ERROR
    assert classify_request_failure(
        {"attempts": 3, "errors": ["TimeoutError"], "safe_headers": {}}
    ) == REQUEST_ERROR


def test_404_is_not_retried_by_recovery_slot(tmp_path: Path):
    journal = _journal(tmp_path, "ZERO")
    calls: list[str] = []

    def first(ticker: str):
        calls.append(ticker)
        return None, _meta(404, "HTTP_404")

    first_result = run_recovery_batch(journal, requester=first, now=NOW)
    assert calls == ["ZERO"]
    assert first_result.summary["status_counts"] == {NO_CHART_404: 1}
    assert first_result.summary["blocking_count"] == 1
    assert first_result.summary["complete"] is False

    calls.clear()

    def must_not_call(ticker: str):
        calls.append(ticker)
        raise AssertionError("404 must not be automatically refetched")

    second_result = run_recovery_batch(journal, requester=must_not_call, now=NOW)
    assert calls == []
    assert second_result.summary["complete"] is False


def test_404_can_be_reconciled_only_by_explicit_official_zero_activity_evidence(tmp_path: Path):
    journal = _journal(tmp_path, "ZERO")
    run_recovery_batch(
        journal,
        requester=lambda _: (None, _meta(404, "HTTP_404")),
        now=NOW,
    )

    reconciled = journal.record_gate_skip(
        "ZERO",
        captured_at=NOW,
        gate_evidence={
            "source": "IDX_OFFICIAL",
            "session_date": SESSION.isoformat(),
            "activity_or": False,
            "volume": 0,
            "value": 0,
            "frequency": 0,
        },
    )
    assert reconciled["status"] == SKIPPED_IDX_NO_ACTIVITY
    assert journal.summary()["complete"] is True

    attempts = sorted((journal.root / "attempts" / "ZERO").iterdir())
    assert [path.name for path in attempts] == ["attempt-0001", "attempt-0002"]
    # The 404 evidence remains immutable; reconciliation appends rather than replaces it.
    assert NO_CHART_404 in (attempts[0] / "status.json").read_text(encoding="utf-8")
    assert SKIPPED_IDX_NO_ACTIVITY in (attempts[1] / "status.json").read_text(encoding="utf-8")


def test_gate_skip_rejects_nonzero_or_ambiguous_activity(tmp_path: Path):
    journal = _journal(tmp_path, "BBCA")
    with pytest.raises(ValueError, match="activity_or=false"):
        journal.record_gate_skip(
            "BBCA",
            captured_at=NOW,
            gate_evidence={"source": "IDX_OFFICIAL", "activity_or": True},
        )
    with pytest.raises(ValueError, match="activity_or=false"):
        journal.record_gate_skip(
            "BBCA",
            captured_at=NOW,
            gate_evidence={"source": "IDX_OFFICIAL"},
        )


def test_success_is_never_refetched_or_replaced(tmp_path: Path):
    journal = _journal(tmp_path, "BBCA")
    ok_meta = _meta(200)
    journal.record_provider_attempt("BBCA", payload=_payload("BBCA"), request_meta=ok_meta, captured_at=NOW)
    with pytest.raises(RuntimeError, match="provider refetch blocked"):
        journal.record_provider_attempt("BBCA", payload=_payload("BBCA"), request_meta=ok_meta, captured_at=NOW)
    assert len(list((journal.root / "attempts" / "BBCA").iterdir())) == 1


def test_attempt_number_gap_fails_closed(tmp_path: Path):
    journal = _journal(tmp_path, "BBCA")
    root = journal.root / "attempts" / "BBCA"
    (root / "attempt-0002").mkdir(parents=True)
    with pytest.raises(ValueError, match="non-contiguous"):
        journal.latest_status_by_ticker()
