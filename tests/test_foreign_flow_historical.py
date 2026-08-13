from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from idx_trade.foreign_flow_historical import (
    NORMALIZED_COLUMNS,
    acquire_historical_foreign_flow,
    build_coverage_census,
)
from idx_trade.providers.idx_stock_summary import StockSummaryPayloadCapture


def _capture(day: str, *, buy: int = 10, sell: int = 3) -> StockSummaryPayloadCapture:
    payload = {
        "recordsTotal": 2,
        "recordsFiltered": 2,
        "data": [
            {"StockCode": "ABCD", "Date": day, "ForeignBuy": buy, "ForeignSell": sell},
            {"StockCode": "EFGH", "Date": day, "ForeignBuy": 0, "ForeignSell": 0},
        ],
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return StockSummaryPayloadCapture(
        payload=payload,
        source_ref=f"https://www.idx.id/primary/TradingSummary/GetStockSummary?date={day.replace('-', '')}",
        raw_bytes=raw,
        endpoint="https://www.idx.id/primary/TradingSummary/GetStockSummary",
        params={"date": day.replace("-", "")},
        retrieval_started_at_utc="2026-08-14T00:00:00+00:00",
        observed_available_at_utc="2026-08-14T00:01:00+00:00",
        records_total=2,
        records_filtered=2,
        row_count=2,
        completeness_status="COMPLETE_RECORDS_TOTAL_SINGLE_RESPONSE",
    )


def test_historical_acquisition_is_exclusive_and_resumable(tmp_path: Path) -> None:
    calls: list[str] = []

    def fake_fetch(day: str, **_: object) -> StockSummaryPayloadCapture:
        calls.append(day)
        return _capture(day)

    first = acquire_historical_foreign_flow(["2026-08-11"], tmp_path, fetch_capture=fake_fetch)
    second = acquire_historical_foreign_flow(["2026-08-11"], tmp_path, fetch_capture=fake_fetch)
    assert first["available_sessions"] == 1
    assert second["available_sessions"] == 1
    assert calls == ["2026-08-11"]
    frame = pd.read_parquet(tmp_path / "sessions" / "2026-08-11" / "foreign_flow.parquet")
    assert list(frame.columns) == list(NORMALIZED_COLUMNS)
    assert frame.loc[0, "ticker"] == "ABCD"
    assert frame.loc[0, "foreign_net"] == 7
    assert frame.loc[0, "label_provenance"] == "OFFICIAL_IDX_HISTORICAL_EOD"
    assert frame.loc[0, "acquisition_mode"] == "RETROSPECTIVELY_ACQUIRED"


def test_historical_census_keeps_missing_sessions_fail_closed(tmp_path: Path) -> None:
    result = acquire_historical_foreign_flow(
        ["2026-08-11", "2026-08-12"],
        tmp_path,
        fetch_capture=lambda day, **_: _capture(day) if day.endswith("11") else (_ for _ in ()).throw(ValueError("empty")),
    )
    assert result["expected_sessions"] == 2
    assert result["available_sessions"] == 1
    assert result["missing_or_error_sessions"] == 1
    assert result["years"]["2026"]["missing_or_error_sessions"] == 1
    assert result["error_histogram"] == {"ValueError": 1}


def test_census_rejects_tampered_normalized_artifact(tmp_path: Path) -> None:
    acquire_historical_foreign_flow(["2026-08-11"], tmp_path, fetch_capture=lambda day, **_: _capture(day))
    path = tmp_path / "sessions" / "2026-08-11" / "foreign_flow.parquet"
    path.write_bytes(path.read_bytes() + b"tamper")
    summary = build_coverage_census(["2026-08-11"], tmp_path)
    assert summary["available_sessions"] == 0
    assert summary["missing_or_error_sessions"] == 1
