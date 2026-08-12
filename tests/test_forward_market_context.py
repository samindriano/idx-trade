from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from idx_trade import forward_monitoring as monitor
from idx_trade.providers.idx_index_summary import (
    fetch_index_summary_payload_capture,
    parse_index_summary_payload,
)
from idx_trade.providers.idx_stock_summary import fetch_stock_summary_payload_capture


DATE = "2026-08-11"


class _Response:
    def __init__(self, payload: dict, raw: bytes | None = None, url: str = "https://example.test"):
        self._payload = payload
        self.content = raw if raw is not None else json.dumps(payload).encode("utf-8")
        self.url = url

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _Session:
    def __init__(self, response: _Response):
        self.response = response
        self.calls: list[str] = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        if "GetStockSummary" in url or "GetIndexSummary" in url:
            return self.response
        return _Response({"data": []})


def _stock_payload(*, records_total: int = 2, rows: list[dict] | None = None) -> dict:
    rows = rows or [
        {"StockCode": "AAAA", "Date": DATE, "Volume": 10, "Frequency": 1, "Value": 100},
        {"StockCode": "BBBB", "Date": DATE, "Volume": 0, "Frequency": 0, "Value": 0},
    ]
    return {"recordsTotal": records_total, "recordsFiltered": records_total, "data": rows}


def _index_payload(*, date: str = DATE) -> dict:
    return {
        "recordsTotal": 1,
        "recordsFiltered": 1,
        "data": [{
            "Date": date,
            "IndexCode": "COMPOSITE",
            "Previous": 100,
            "Highest": 105,
            "Lowest": 99,
            "Close": 104,
            "Change": 4,
            "Volume": 1000,
            "Value": 2000,
            "Frequency": 10,
            "MarketCapital": 100000,
            "NumberOfStock": 2,
        }],
    }


def test_stock_summary_rejects_partial_records_total_response():
    payload = _stock_payload(records_total=3)
    with pytest.raises(ValueError, match="partial"):
        fetch_stock_summary_payload_capture(
            DATE,
            session=_Session(_Response(payload)),
        )


def test_stock_summary_capture_preserves_exact_raw_bytes_and_metadata():
    payload = _stock_payload()
    raw = b'{"official":"exact-bytes"}'
    capture = fetch_stock_summary_payload_capture(
        DATE,
        session=_Session(_Response(payload, raw=raw)),
    )
    assert capture.raw_bytes == raw
    assert capture.row_count == capture.records_total == 2
    assert capture.records_filtered == 2
    assert capture.completeness_status == "COMPLETE_RECORDS_TOTAL_SINGLE_RESPONSE"
    assert capture.params == {"date": "20260811"}


def test_index_summary_rejects_date_mismatch_and_normalizes_official_fields():
    with pytest.raises(ValueError, match="date mismatch"):
        parse_index_summary_payload(
            _index_payload(date="2026-08-10"),
            requested_date=DATE,
            source_ref="idx://index",
            source_sha256="a" * 64,
        )

    frame, meta = parse_index_summary_payload(
        _index_payload(),
        requested_date=DATE,
        source_ref="idx://index",
        source_sha256="a" * 64,
        retrieved_at="2026-08-11T12:00:00Z",
    )
    assert frame.loc[0, "index_code"] == "COMPOSITE"
    assert frame.loc[0, "trading_value_idr"] == 2000
    assert frame.loc[0, "pit_timing_status"] == "UNRESOLVED_NO_PUBLICATION_TIMESTAMP"
    assert meta.records_total == 1


def test_index_summary_capture_uses_records_total_gate():
    capture = fetch_index_summary_payload_capture(
        DATE,
        session=_Session(_Response(_index_payload())),
    )
    assert capture.row_count == 1
    assert capture.records_total == 1
    assert capture.endpoint.endswith("TradingSummary/GetIndexSummary")
    assert capture.params == {"length": "1000", "start": "0", "date": "20260811"}


def test_immutable_bytes_rejects_revision_without_overwrite(tmp_path: Path):
    path = tmp_path / "payload.raw.json"
    assert monitor._immutable_bytes(path, b"first")
    assert not monitor._immutable_bytes(path, b"first")
    with pytest.raises(RuntimeError, match="revision conflict"):
        monitor._immutable_bytes(path, b"revised")
    assert path.read_bytes() == b"first"
