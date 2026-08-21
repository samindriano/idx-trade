from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from idx_trade.stockbit_stream_archive import QuotaSnapshot, StreamArchiveError
from idx_trade.stockbit_stream_capture_v2 import (
    LocalLeanArchive,
    R2LeanArchive,
    RuntimeUniverse,
    build_runtime_universe,
    capture_stream_v2,
)


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


def _identity_csv(path: Path, tickers: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=IDENTITY_FIELDS)
        writer.writeheader()
        for ticker in tickers:
            writer.writerow(
                {
                    "ticker": ticker,
                    "company_name": ticker,
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
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.content = json.dumps(payload, allow_nan=True).encode("utf-8")
        self.headers = {"content-type": "application/json"}

    def json(self):
        return self._payload


class _SummarySession:
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls = 0

    def get(self, url, params, headers, timeout):
        self.calls += 1
        return _SummaryResponse(self.payload)


def _summary_payload(rows: list[dict], *, records_total: int | None = None) -> dict:
    total = len(rows) if records_total is None else records_total
    return {
        "provider": "idx",
        "dataset": "stock-summary",
        "recordsTotal": total,
        "recordsFiltered": total,
        "start": 0,
        "length": len(rows),
        "data": rows,
    }


def _row(ticker: str, value, nonregular=0) -> dict:
    return {
        "StockCode": ticker,
        "Date": "2026-08-20T00:00:00",
        "Value": value,
        "NonRegularValue": nonregular,
    }


def test_universe_rejects_incomplete_stock_summary_page(tmp_path: Path) -> None:
    identity = tmp_path / "identity.csv"
    _identity_csv(identity, ["BBCA", "BBRI", "BMRI"])
    session = _SummarySession(
        _summary_payload(
            [_row("BBCA", 300), _row("BBRI", 500), _row("BMRI", 400)],
            records_total=1200,
        )
    )
    with pytest.raises(StreamArchiveError, match="incomplete|pagination|recordsTotal"):
        build_runtime_universe(
            api_key="x",
            identity_csv=identity,
            capture_date="2026-08-21",
            top_n=2,
            session_lookback_days=1,
            session=session,
        )


def test_universe_rejects_duplicate_ticker_rows(tmp_path: Path) -> None:
    identity = tmp_path / "identity.csv"
    _identity_csv(identity, ["BBCA", "BBRI"])
    session = _SummarySession(
        _summary_payload([_row("BBCA", 100), _row("BBCA", 999), _row("BBRI", 500)])
    )
    with pytest.raises(StreamArchiveError, match="duplicate"):
        build_runtime_universe(
            api_key="x",
            identity_csv=identity,
            capture_date="2026-08-21",
            top_n=1,
            session_lookback_days=1,
            session=session,
        )


def test_universe_does_not_admit_nonfinite_or_impossible_values(tmp_path: Path) -> None:
    identity = tmp_path / "identity.csv"
    _identity_csv(identity, ["BBCA", "BBRI", "BMRI", "TLKM"])
    session = _SummarySession(
        _summary_payload(
            [
                _row("BBCA", float("inf"), 0),
                _row("BBRI", 500, 0),
                _row("BMRI", 400, 0),
                _row("TLKM", 100, 200),
            ]
        )
    )
    universe = build_runtime_universe(
        api_key="x",
        identity_csv=identity,
        capture_date="2026-08-21",
        top_n=2,
        session_lookback_days=1,
        session=session,
    )
    assert [row["ticker"] for row in universe.rows] == ["BBRI", "BMRI"]


class _StreamResponse:
    def __init__(self, status_code: int = 200):
        self.status_code = status_code
        self.headers = {"content-type": "application/json"}


class _MixedClient:
    def __init__(self, failures: set[str] | None = None, *, fail_quota_after: bool = False):
        self.failures = failures or set()
        self.fail_quota_after = fail_quota_after
        self.usage_calls = 0
        self.stream_calls: list[str] = []

    def get_usage(self):
        self.usage_calls += 1
        if self.fail_quota_after and self.usage_calls >= 2:
            raise StreamArchiveError("quota telemetry unavailable after capture")
        return QuotaSnapshot("pro", 1, 25000, 24999, None, "RED_TEAM")

    def stream(self, symbol: str):
        self.stream_calls.append(symbol)
        observed = datetime(2026, 8, 21, 5, tzinfo=timezone.utc)
        if symbol in self.failures:
            raw = json.dumps({"error": "synthetic"}).encode("utf-8")
            return _StreamResponse(500), raw, observed
        item = {
            "id": f"{symbol}-1",
            "createdAt": "2026-08-21 12:00:00",
            "content": f"watch ${symbol}",
            "userId": "u",
        }
        raw = json.dumps({"data": {"count": 1, "items": [item], "symbol": symbol}}).encode("utf-8")
        return _StreamResponse(200), raw, observed


def _runtime_universe() -> RuntimeUniverse:
    rows = [
        {
            "ticker": "BBRI",
            "company_name": "BBRI",
            "listed_from": "2000-01-01",
            "source_session": "2026-08-20",
            "regular_value": 500.0,
            "activity_rank": 1,
        },
        {
            "ticker": "BBCA",
            "company_name": "BBCA",
            "listed_from": "2000-01-01",
            "source_session": "2026-08-20",
            "regular_value": 300.0,
            "activity_rank": 2,
        },
    ]
    return RuntimeUniverse(
        "2026-08-21",
        "2026-08-20",
        rows,
        b'{"provider":"idx"}',
        "a" * 64,
        "b" * 64,
    )


def test_partial_stream_failure_must_not_report_data_ready(tmp_path: Path) -> None:
    result = capture_stream_v2(
        client=_MixedClient({"BBCA"}),
        archive=LocalLeanArchive(tmp_path),
        universe=_runtime_universe(),
        slot="midday",
        hmac_salt="red-team-salt",
        monthly_reserve=1,
    )
    assert result["successful_responses"] == 1
    assert result["completed_calls"] == 2
    assert result["status"] != "DATA_READY"


def test_all_stream_failures_must_not_report_data_ready(tmp_path: Path) -> None:
    result = capture_stream_v2(
        client=_MixedClient({"BBRI", "BBCA"}),
        archive=LocalLeanArchive(tmp_path),
        universe=_runtime_universe(),
        slot="after_close",
        hmac_salt="red-team-salt",
        monthly_reserve=1,
    )
    assert result["successful_responses"] == 0
    assert result["status"] != "DATA_READY"


def test_quota_after_telemetry_failure_must_not_orphan_successful_capture(tmp_path: Path) -> None:
    result = capture_stream_v2(
        client=_MixedClient(fail_quota_after=True),
        archive=LocalLeanArchive(tmp_path),
        universe=_runtime_universe(),
        slot="pre_open",
        hmac_salt="red-team-salt",
        monthly_reserve=1,
    )
    assert result["completed_calls"] == 2
    assert len(list((tmp_path / "manifests").rglob("*.json"))) == 1


def test_same_slot_retry_after_partial_attempt_is_not_permanently_poisoned(tmp_path: Path) -> None:
    class _CrashClient(_MixedClient):
        def stream(self, symbol: str):
            if symbol == "BBCA":
                raise StreamArchiveError("synthetic timeout after first ticker")
            return super().stream(symbol)

    first = capture_stream_v2(
        client=_CrashClient(),
        archive=LocalLeanArchive(tmp_path),
        universe=_runtime_universe(),
        slot="midday",
        hmac_salt="red-team-salt",
        monthly_reserve=1,
    )
    assert first["status"] == "DATA_PARTIAL"
    assert first["response_classification_counts"]["REQUEST_EXCEPTION"] == 1
    assert len(list((tmp_path / "manifests").rglob("*.json"))) == 1

    class _ChangedFirstObservation(_MixedClient):
        def stream(self, symbol: str):
            response, raw, observed = super().stream(symbol)
            if symbol == "BBRI":
                payload = json.loads(raw)
                payload["data"]["items"][0]["content"] = "changed on retry $BBRI"
                raw = json.dumps(payload).encode("utf-8")
            return response, raw, observed

    result = capture_stream_v2(
        client=_ChangedFirstObservation(),
        archive=LocalLeanArchive(tmp_path),
        universe=_runtime_universe(),
        slot="midday",
        hmac_salt="red-team-salt",
        monthly_reserve=1,
    )
    assert result["status"] == "DATA_READY"
    assert result["completed_calls"] == 2
    assert result["attempt_id"] != first["attempt_id"]
    assert len(list((tmp_path / "manifests").rglob("*.json"))) == 2


def test_r2_collision_cannot_be_authenticated_by_forgeable_metadata_only() -> None:
    pytest.importorskip("botocore")
    from botocore.exceptions import ClientError

    class _FakeClient:
        def put_object(self, **kwargs):
            raise ClientError(
                {
                    "Error": {"Code": "PreconditionFailed", "Message": "exists"},
                    "ResponseMetadata": {"HTTPStatusCode": 412},
                },
                "PutObject",
            )

        def head_object(self, **kwargs):
            import hashlib
            claimed = hashlib.sha256(b"expected").hexdigest()
            return {"Metadata": {"sha256": claimed}}

        def get_object(self, **kwargs):
            return {"Body": io.BytesIO(b"different-body")}

    archive = R2LeanArchive.__new__(R2LeanArchive)
    archive.bucket = "red-team"
    archive.prefix = ""
    archive.client = _FakeClient()

    with pytest.raises(StreamArchiveError, match="immutable key changed"):
        archive.put_immutable("raw/test.json", b"expected", "application/json")
