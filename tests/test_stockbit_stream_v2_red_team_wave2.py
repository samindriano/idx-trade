from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

import idx_trade.stockbit_stream_archive as archive_module
from idx_trade.stockbit_stream_archive import (
    QuotaSnapshot,
    StreamArchiveError,
    ZapiClient,
    parse_stream_payload,
)
from idx_trade.stockbit_stream_capture_v2 import (
    LocalLeanArchive,
    RuntimeUniverse,
    build_runtime_universe,
    capture_stream_v2,
)


def test_stream_parser_rejects_wrong_or_missing_provider() -> None:
    item = {"id": 1, "createdAt": "2026-08-21 12:00:00", "content": "$BBCA"}
    wrong = json.dumps(
        {"data": {"count": 1, "items": [item], "symbol": "BBCA", "provider": "not-stockbit"}}
    ).encode()
    missing = json.dumps(
        {"data": {"count": 1, "items": [item], "symbol": "BBCA"}}
    ).encode()
    assert parse_stream_payload(wrong, 200, "BBCA")[0] != "OK"
    assert parse_stream_payload(missing, 200, "BBCA")[0] != "OK"


def test_observed_available_timestamp_is_taken_after_response_receipt(monkeypatch) -> None:
    """PIT availability must be conservative: received-at, not request-start."""
    events: list[str] = []

    class FakeDateTime:
        @classmethod
        def now(cls, tz=None):
            events.append("timestamp")
            return datetime(2026, 8, 21, 5, tzinfo=timezone.utc)

    class Response:
        status_code = 200
        content = b'{}'
        headers = {}

    class Session:
        def get(self, *args, **kwargs):
            events.append("response")
            return Response()

    monkeypatch.setattr(archive_module, "datetime", FakeDateTime)
    client = ZapiClient("x", session=Session())
    client.stream("BBCA")
    assert events == ["response", "timestamp"]


def _write_identity(path: Path, ticker: str) -> None:
    fields = [
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
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow(
            {
                "ticker": ticker,
                "company_name": "bad",
                "listed_from": "2000-01-01",
                "listed_to": "",
                "capture_broad": "1",
                "capture_high": "0",
                "activity_rank": "",
                "activity_median_regular_value_60": "",
                "universe_source": "RED_TEAM",
            }
        )


class _NeverCalledSession:
    def get(self, *args, **kwargs):
        raise AssertionError("invalid identity must fail before provider access")


def test_identity_whitelist_rejects_malformed_ticker_before_network(tmp_path: Path) -> None:
    identity = tmp_path / "identity.csv"
    _write_identity(identity, "../../BBCA")
    with pytest.raises(StreamArchiveError, match="ticker|identity"):
        build_runtime_universe(
            api_key="x",
            identity_csv=identity,
            capture_date="2026-08-21",
            top_n=1,
            session=_NeverCalledSession(),
        )


class _Response:
    status_code = 200
    headers = {"content-type": "application/json"}


class _Client:
    def __init__(self, observed: datetime):
        self.observed = observed

    def get_usage(self):
        return QuotaSnapshot("pro", 1, 25000, 24999, None, "RED_TEAM")

    def stream(self, symbol: str):
        raw = json.dumps(
            {
                "data": {
                    "count": 1,
                    "items": [
                        {
                            "id": f"{symbol}-1",
                            "createdAt": "2026-08-21 12:00:00",
                            "content": f"watch ${symbol}",
                            "userId": "u",
                        }
                    ],
                    "symbol": symbol,
                    "provider": "stockbit",
                }
            }
        ).encode()
        return _Response(), raw, self.observed


def _universe() -> RuntimeUniverse:
    return RuntimeUniverse(
        "2026-08-21",
        "2026-08-20",
        [
            {
                "ticker": "BBCA",
                "company_name": "BBCA",
                "listed_from": "2000-01-01",
                "source_session": "2026-08-20",
                "regular_value": 1.0,
                "activity_rank": 1,
            }
        ],
        b'{}',
        "a" * 64,
        "b" * 64,
    )


def test_retry_with_identical_provider_bytes_but_new_observation_time_is_recoverable(tmp_path: Path) -> None:
    capture_stream_v2(
        client=_Client(datetime(2026, 8, 21, 5, 0, tzinfo=timezone.utc)),
        archive=LocalLeanArchive(tmp_path),
        universe=_universe(),
        slot="midday",
        hmac_salt="salt",
        monthly_reserve=1,
    )
    # Same provider body, later observation timestamp. This is a normal retry, not corruption.
    result = capture_stream_v2(
        client=_Client(datetime(2026, 8, 21, 5, 1, tzinfo=timezone.utc)),
        archive=LocalLeanArchive(tmp_path),
        universe=_universe(),
        slot="midday",
        hmac_salt="salt",
        monthly_reserve=1,
    )
    assert result["completed_calls"] == 1


def test_capture_rejects_unregistered_slot_name(tmp_path: Path) -> None:
    with pytest.raises(StreamArchiveError, match="slot"):
        capture_stream_v2(
            client=_Client(datetime(2026, 8, 21, 5, tzinfo=timezone.utc)),
            archive=LocalLeanArchive(tmp_path),
            universe=_universe(),
            slot="looks_like_preopen_but_is_not",
            hmac_salt="salt",
            monthly_reserve=1,
        )


def test_production_workflow_does_not_expose_repository_secrets_job_wide() -> None:
    workflow = Path(".github/workflows/stockbit-stream-prospective-capture.yml").read_text(encoding="utf-8")
    steps_index = workflow.index("    steps:")
    pre_steps = workflow[:steps_index]
    assert "secrets." not in pre_steps, (
        "R2/Zapi/HMAC secrets are job-scoped, so checkout/setup-python/pip and every dependency "
        "run with secret access. Secrets should be scoped only to the capture step."
    )


def test_production_workflow_pins_all_actions_to_full_commit_sha() -> None:
    workflow = Path(".github/workflows/stockbit-stream-prospective-capture.yml").read_text(encoding="utf-8")
    uses = re.findall(r"^\s*-?\s*uses:\s*([^\s#]+)", workflow, flags=re.MULTILINE)
    assert uses
    unpinned = [value for value in uses if not re.search(r"@[0-9a-fA-F]{40}$", value)]
    assert unpinned == [], f"actions must be immutable full-SHA pins, found: {unpinned}"
