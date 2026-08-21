from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from idx_trade.stockbit_stream_archive import QuotaSnapshot
from idx_trade.stockbit_stream_capture_v2 import LocalLeanArchive, RuntimeUniverse, build_runtime_universe, capture_stream_v2


class Response:
    def __init__(self, body: dict, status: int = 200):
        self.status_code = status
        self._body = body
        self.content = json.dumps(body).encode()
        self.headers = {"content-type": "application/json"}

    def json(self):
        return self._body


class Session:
    def get(self, url, params, headers, timeout):
        assert params["date"] == "2026-08-20"
        rows = [
            {"StockCode": "BBCA", "Date": "2026-08-20T00:00:00", "Value": 300, "NonRegularValue": 0},
            {"StockCode": "BBRI", "Date": "2026-08-20T00:00:00", "Value": 500, "NonRegularValue": 0},
            {"StockCode": "AADI", "Date": "2026-08-20T00:00:00", "Value": 1000, "NonRegularValue": 950},
        ]
        return Response({"provider": "idx", "dataset": "stock-summary", "recordsTotal": 3, "recordsFiltered": 3, "start": 0, "length": 3, "data": rows})


def identity_csv(path: Path):
    fields = ["ticker", "company_name", "listed_from", "listed_to", "capture_broad", "capture_high", "activity_rank", "activity_median_regular_value_60", "universe_source"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for ticker in ["BBCA", "BBRI", "AADI"]:
            w.writerow({"ticker": ticker, "company_name": ticker, "listed_from": "2000-01-01", "listed_to": "", "capture_broad": "1", "capture_high": "0", "activity_rank": "", "activity_median_regular_value_60": "", "universe_source": "TEST"})


def test_runtime_universe_uses_prior_session_regular_value(tmp_path: Path):
    path = tmp_path / "identity.csv"
    identity_csv(path)
    universe = build_runtime_universe(api_key="x", identity_csv=path, capture_date="2026-08-21", top_n=2, session=Session())
    assert universe.source_session == "2026-08-20"
    assert [row["ticker"] for row in universe.rows] == ["BBRI", "BBCA"]
    assert [row["activity_rank"] for row in universe.rows] == [1, 2]


class StreamResponse:
    status_code = 200
    headers = {"content-type": "application/json"}


class Client:
    def __init__(self):
        self.calls = []

    def get_usage(self):
        return QuotaSnapshot("pro", 1, 25000, 24999, None, "TEST")

    def stream(self, symbol):
        self.calls.append(symbol)
        item = {"id": f"{symbol}-1", "createdAt": "2026-08-21 12:00:00", "content": f"watch ${symbol}", "userId": "u", "likes": 1}
        raw = json.dumps({"data": {"count": 1, "items": [item], "symbol": symbol}}).encode()
        return StreamResponse(), raw, datetime(2026, 8, 21, 5, tzinfo=timezone.utc)


def test_capture_v2_avoids_per_post_hot_path_objects(tmp_path: Path):
    rows = [
        {"ticker": "BBRI", "company_name": "BBRI", "listed_from": "2000", "source_session": "2026-08-20", "regular_value": 500.0, "activity_rank": 1},
        {"ticker": "BBCA", "company_name": "BBCA", "listed_from": "2000", "source_session": "2026-08-20", "regular_value": 300.0, "activity_rank": 2},
    ]
    universe = RuntimeUniverse("2026-08-21", "2026-08-20", rows, b'{"provider":"idx"}', "a" * 64, "b" * 64)
    client = Client()
    result = capture_stream_v2(client=client, archive=LocalLeanArchive(tmp_path), universe=universe, slot="midday", hmac_salt="salt", monthly_reserve=1)
    assert result["status"] == "DATA_READY"
    assert client.calls == ["BBRI", "BBCA"]
    assert result["normalized_post_rows"] == 2
    assert not (tmp_path / "posts").exists()
    assert len(list((tmp_path / "raw").rglob("*.json"))) == 2
    assert len(list((tmp_path / "normalized").rglob("*.jsonl"))) == 2
    assert len(list((tmp_path / "manifests").rglob("*.json"))) == 1
