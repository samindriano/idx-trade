from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from idx_trade.stockbit_stream_archive import (
    SCHEDULE_CRONS,
    StorageImmutabilityConflict,
    StreamArchiveError,
    QuotaSnapshot,
    LocalImmutableStore,
    capture_stream_run,
    load_universe,
    normalize_post,
    parse_stream_payload,
    parse_stream_payload_detailed,
    verify_universe_manifest,
)


def _item(post_id: int = 1, created_at: str = "2026-08-21 08:50:40") -> dict:
    return {
        "id": post_id,
        "createdAt": created_at,
        "content": "watch $BBCA",
        "tickers": ["BBCA"],
        "userId": "private-user-1",
        "username": "private-name",
        "fullName": "Private Person",
        "likes": 1,
    }


def _payload(symbol: str = "BBCA", items: list[dict] | None = None) -> bytes:
    values = items if items is not None else [_item()]
    return json.dumps({"data": {"count": len(values), "items": values, "symbol": symbol}}).encode()


def _universe() -> list[dict[str, str]]:
    return [
        {
            "ticker": "BBCA",
            "company_name": "Bank Central Asia",
            "listed_from": "2000-01-01",
            "listed_to": "",
            "capture_broad": "1",
            "capture_high": "1",
            "activity_rank": "1",
            "activity_median_regular_value_60": "1000000000",
            "universe_source": "TEST",
        },
        {
            "ticker": "AADI",
            "company_name": "Adaro",
            "listed_from": "2024-01-01",
            "listed_to": "",
            "capture_broad": "1",
            "capture_high": "0",
            "activity_rank": "",
            "activity_median_regular_value_60": "",
            "universe_source": "TEST",
        },
    ]


class _Response:
    def __init__(self, payload: bytes, status_code: int = 200):
        self.content = payload
        self.status_code = status_code
        self.headers = {"content-type": "application/json"}


class _Client:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.stream_calls: list[str] = []
        self.usage_calls = 0

    def get_usage(self) -> QuotaSnapshot:
        self.usage_calls += 1
        return QuotaSnapshot("pro", 0, 100, 100, None, "TEST")

    def stream(self, symbol: str):
        self.stream_calls.append(symbol)
        return _Response(self.payload), self.payload, datetime(2026, 8, 21, 1, tzinfo=timezone.utc)


def test_stream_parser_rejects_empty_partial_and_duplicate_responses() -> None:
    status, _, items = parse_stream_payload(_payload(), 200, "BBCA")
    assert status == "OK"
    assert len(items) == 1

    status, _, _ = parse_stream_payload(_payload("BBCA", []), 200, "BBCA")
    assert status == "EMPTY_RESPONSE_FAIL_CLOSED"

    partial = json.dumps({"data": {"count": 2, "items": [_item()], "symbol": "BBCA"}}).encode()
    status, _, _ = parse_stream_payload(partial, 200, "BBCA")
    assert status == "PARTIAL_OR_SYMBOL_MISMATCH"

    status, _, _ = parse_stream_payload(_payload(items=[_item(), _item()]), 200, "BBCA")
    assert status == "DUPLICATE_POST_ID_FAIL_CLOSED"

    malformed = _payload(items=[{"id": 1, "createdAt": "2026-08-21 08:50:40"}])
    status, _, items, detail = parse_stream_payload_detailed(malformed, 200, "BBCA")
    assert status == "ITEM_SCHEMA_ERROR"
    assert items == []
    assert detail == "item[0].missing_content"


def test_normalization_hmacs_author_and_rejects_naive_source_timezone() -> None:
    row = normalize_post(_item(), "BBCA", "HIGH_ACTIVITY", datetime(2026, 8, 21, tzinfo=timezone.utc), "salt")
    assert row["author_pseudonym_hmac_sha256"]
    assert row["author_identity_kind"] == "USER_ID"
    assert "username" not in row and "fullName" not in row
    assert row["mentioned_tickers"] == ["BBCA"]
    assert row["source_created_at_utc"] is None
    assert row["source_created_at_timezone_status"] == "NAIVE_TIMEZONE_UNRESOLVED"


def test_capture_is_immutable_idempotent_and_tracks_reobservations(tmp_path: Path) -> None:
    store = LocalImmutableStore(tmp_path)
    first_client = _Client(_payload())
    first = capture_stream_run(
        client=first_client,
        store=store,
        universe_rows=_universe(),
        slot="pre_open",
        capture_date="2026-08-21",
        hmac_salt="salt",
        universe_sha="a" * 64,
        monthly_reserve=1,
    )
    assert first["status"] == "DATA_READY"
    assert first_client.stream_calls == ["BBCA"]
    assert json.loads(store.read("posts/1.json"))["first_seen_at_utc"] == "2026-08-21T01:00:00Z"

    class _NoCallClient(_Client):
        def get_usage(self):  # pragma: no cover - assertion is the test
            raise AssertionError("idempotent replay must not call quota/provider")

    replay = capture_stream_run(
        client=_NoCallClient(_payload()),
        store=store,
        universe_rows=_universe(),
        slot="pre_open",
        capture_date="2026-08-21",
        hmac_salt="salt",
        universe_sha="a" * 64,
        monthly_reserve=1,
    )
    assert replay["idempotent_replay"] is True
    assert replay["manifest_sha256"] == first["manifest_sha256"]

    later_client = _Client(_payload())
    later = capture_stream_run(
        client=later_client,
        store=store,
        universe_rows=_universe(),
        slot="pre_open",
        capture_date="2026-08-22",
        hmac_salt="salt",
        universe_sha="a" * 64,
        monthly_reserve=1,
    )
    assert later["status"] == "DATA_READY"
    normalized = store.read("normalized/2026-08-22_pre_open_aaaaaaaaaaaaaaaa/BBCA.jsonl")
    assert normalized is not None and b'"observation_type":"REOBSERVATION"' in normalized


def test_quota_guard_writes_no_provider_manifest(tmp_path: Path) -> None:
    class _LowQuota(_Client):
        def get_usage(self):
            self.usage_calls += 1
            return QuotaSnapshot("pro", 99, 100, 1, None, "TEST")

    client = _LowQuota(_payload())
    result = capture_stream_run(
        client=client,
        store=LocalImmutableStore(tmp_path),
        universe_rows=_universe(),
        slot="after_close",
        capture_date="2026-08-21",
        hmac_salt="salt",
        universe_sha="b" * 64,
        monthly_reserve=1,
    )
    assert result["status"] == "QUOTA_BLOCKED_BEFORE_REQUEST"
    assert client.stream_calls == []


def test_universe_manifest_and_schedule_are_pinned(tmp_path: Path) -> None:
    csv_path = tmp_path / "universe.csv"
    headers = "ticker,company_name,listed_from,listed_to,capture_broad,capture_high,activity_rank,activity_median_regular_value_60,universe_source\n"
    csv_path.write_text(headers + "BBCA,Bank,2000-01-01,,1,1,1,1,TEST\n", encoding="utf-8")
    import hashlib

    digest = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    manifest_path = tmp_path / "universe.json"
    manifest_path.write_text(json.dumps({"output_sha256": digest}), encoding="utf-8")
    assert verify_universe_manifest(csv_path, manifest_path)["output_sha256"] == digest
    assert load_universe(csv_path)[0]["ticker"] == "BBCA"
    assert SCHEDULE_CRONS["47 1 * * *"] == "pre_open"

    manifest_path.write_text(json.dumps({"output_sha256": "0" * 64}), encoding="utf-8")
    with pytest.raises(StreamArchiveError):
        verify_universe_manifest(csv_path, manifest_path)

    csv_path.write_text(headers + "BBCA,Bank,2000-01-01,2026-01-01,1,1,1,1,TEST\n", encoding="utf-8")
    with pytest.raises(StreamArchiveError):
        load_universe(csv_path)


def test_immutable_store_rejects_changed_bytes(tmp_path: Path) -> None:
    store = LocalImmutableStore(tmp_path)
    store.put_if_absent("raw/a.json", b"one", "application/json")
    with pytest.raises(StorageImmutabilityConflict):
        store.put_if_absent("raw/a.json", b"two", "application/json")
