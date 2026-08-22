from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from idx_trade.stockbit_stream_archive import QuotaSnapshot
from idx_trade.stockbit_stream_capture_v2 import (
    LocalLeanArchive,
    RuntimeUniverse,
    build_runtime_universe,
    capture_stream_v2,
)


class _Response:
    status_code = 200
    headers = {"content-type": "application/json"}


class _TimingClient:
    def __init__(self, start: datetime):
        self.start = start
        self.calls: list[str] = []

    def get_usage(self):
        return QuotaSnapshot("pro", 1, 25000, 24999, None, "RED_TEAM")

    def stream(self, symbol: str):
        index = len(self.calls)
        self.calls.append(symbol)
        observed = self.start + timedelta(seconds=index * 3)
        item = {
            "id": f"{symbol}-1",
            "createdAt": "2026-08-21 12:00:00",
            "content": f"watch ${symbol}",
            "userId": "u",
        }
        raw = json.dumps({"data": {"count": 1, "items": [item], "symbol": symbol}}).encode()
        return _Response(), raw, observed


def _wide_universe() -> RuntimeUniverse:
    tickers = ["BBCA", "BBRI", "BMRI", "TLKM", "ASII", "AMRT", "ICBP", "INDF"]
    rows = [
        {
            "ticker": ticker,
            "company_name": ticker,
            "listed_from": "2000-01-01",
            "source_session": "2026-08-20",
            "regular_value": float(1000 - rank),
            "activity_rank": rank,
        }
        for rank, ticker in enumerate(tickers, start=1)
    ]
    return RuntimeUniverse(
        "2026-08-21",
        "2026-08-20",
        rows,
        b'{}',
        "a" * 64,
        "0123456789abcdef" * 4,
        identity_source_sha256="c" * 64,
    )


def _expected_hash_order(universe: RuntimeUniverse, slot: str) -> list[str]:
    def key(ticker: str) -> str:
        material = f"{universe.capture_date}|{slot}|{universe.universe_sha256}|{ticker}"
        return hashlib.sha256(material.encode()).hexdigest()

    return sorted((row["ticker"] for row in universe.rows), key=key)


def test_capture_order_is_deterministic_but_not_liquidity_rank_order(tmp_path: Path) -> None:
    universe = _wide_universe()
    client = _TimingClient(datetime(2026, 8, 21, 5, 0, tzinfo=timezone.utc))
    result = capture_stream_v2(
        client=client,
        archive=LocalLeanArchive(tmp_path),
        universe=universe,
        slot="midday",
        hmac_salt="salt",
        monthly_reserve=1,
    )
    expected = _expected_hash_order(universe, "midday")
    rank_order = [row["ticker"] for row in universe.rows]
    assert client.calls == expected
    assert client.calls != rank_order
    assert result["capture_order_rule"] == "SHA256_DATE_SLOT_UNIVERSE_TICKER"


def test_same_logical_slot_retries_keep_same_capture_order(tmp_path: Path) -> None:
    universe = _wide_universe()
    first = _TimingClient(datetime(2026, 8, 21, 5, 0, tzinfo=timezone.utc))
    second = _TimingClient(datetime(2026, 8, 21, 5, 5, tzinfo=timezone.utc))
    first_result = capture_stream_v2(
        client=first,
        archive=LocalLeanArchive(tmp_path),
        universe=universe,
        slot="after_close",
        hmac_salt="salt",
        monthly_reserve=1,
    )
    second_result = capture_stream_v2(
        client=second,
        archive=LocalLeanArchive(tmp_path),
        universe=universe,
        slot="after_close",
        hmac_salt="salt",
        monthly_reserve=1,
    )
    assert first.calls == second.calls
    assert first_result["logical_slot_id"] == second_result["logical_slot_id"]
    assert first_result["attempt_id"] != second_result["attempt_id"]


def test_manifest_records_observation_span_and_capture_order_index(tmp_path: Path) -> None:
    universe = _wide_universe()
    start = datetime(2026, 8, 21, 5, 0, tzinfo=timezone.utc)
    client = _TimingClient(start)
    result = capture_stream_v2(
        client=client,
        archive=LocalLeanArchive(tmp_path),
        universe=universe,
        slot="midday",
        hmac_salt="salt",
        monthly_reserve=1,
    )
    assert result["first_observed_at_utc"] == "2026-08-21T05:00:00Z"
    assert result["last_observed_at_utc"] == "2026-08-21T05:00:21Z"
    assert result["observation_span_seconds"] == 21.0
    assert [r["capture_order_index"] for r in result["request_records"]] == list(range(1, 9))


IDENTITY_FIELDS = [
    "ticker",
    "company_name",
    "listed_from",
    "listed_to",
    "capture_broad",
    "capture_high",
    "activity_rank",
    "activity_median_regular_value_60",
    "universe_source",
]


def _identity_csv(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=IDENTITY_FIELDS)
        writer.writeheader()
        writer.writerow(
            {
                "ticker": "BBCA",
                "company_name": "BBCA",
                "listed_from": "2000-01-01",
                "listed_to": "",
                "capture_broad": "1",
                "capture_high": "0",
                "activity_rank": "",
                "activity_median_regular_value_60": "",
                "universe_source": "RED_TEAM",
            }
        )


class _SummaryResponse:
    def __init__(self, body: dict):
        self.status_code = 200
        self._body = body
        self.content = json.dumps(body).encode()
        self.headers = {"content-type": "application/json"}

    def json(self):
        return self._body


class _WeekendProbeSession:
    def __init__(self):
        self.requested_dates: list[str] = []

    def get(self, url, params, headers, timeout):
        candidate = params["date"]
        self.requested_dates.append(candidate)
        if candidate != "2026-08-21":
            return _SummaryResponse(
                {
                    "provider": "idx",
                    "dataset": "stock-summary",
                    "recordsTotal": 0,
                    "recordsFiltered": 0,
                    "start": 0,
                    "length": 0,
                    "data": [],
                }
            )
        row = {
            "StockCode": "BBCA",
            "Date": "2026-08-21T00:00:00",
            "Value": 100,
            "NonRegularValue": 0,
        }
        return _SummaryResponse(
            {
                "provider": "idx",
                "dataset": "stock-summary",
                "recordsTotal": 1,
                "recordsFiltered": 1,
                "start": 0,
                "length": 1,
                "data": [row],
            }
        )


def test_prior_session_lookup_skips_known_weekends_without_api_calls(tmp_path: Path) -> None:
    identity = tmp_path / "identity.csv"
    _identity_csv(identity)
    session = _WeekendProbeSession()
    universe = build_runtime_universe(
        api_key="x",
        identity_csv=identity,
        capture_date="2026-08-24",  # Monday; prior Friday is 2026-08-21.
        top_n=1,
        session=session,
    )
    assert universe.source_session == "2026-08-21"
    assert session.requested_dates == ["2026-08-21"]
    assert universe.selection_diagnostics["stock_summary_requests"] == 1


def test_identity_roster_age_is_explicit_provenance(tmp_path: Path) -> None:
    identity = tmp_path / "identity.csv"
    _identity_csv(identity)
    session = _WeekendProbeSession()
    universe = build_runtime_universe(
        api_key="x",
        identity_csv=identity,
        capture_date="2026-08-24",
        top_n=1,
        session=session,
        identity_roster_as_of="2026-07-31",
    )
    assert universe.identity_roster_as_of == "2026-07-31"
    assert universe.selection_diagnostics["identity_roster_age_days"] == 24
    assert universe.selection_diagnostics["identity_roster_status"] in {"CURRENT", "STALE"}
