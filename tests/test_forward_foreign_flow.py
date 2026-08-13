from __future__ import annotations

import pandas as pd
import pytest

from idx_trade.forward_foreign_flow import parse_stock_summary_foreign_flow


def _payload() -> dict[str, object]:
    return {
        "recordsTotal": 2,
        "recordsFiltered": 2,
        "data": [
            {"StockCode": "BBCA", "Date": "2026-08-12", "ForeignBuy": 1200, "ForeignSell": 1000},
            {"StockCode": "GOTOM", "Date": "2026-08-12", "ForeignBuy": 0, "ForeignSell": 0},
        ],
    }


def _parse(payload: dict[str, object]):
    return parse_stock_summary_foreign_flow(
        payload,
        session_date="2026-08-12",
        knowledge_at_utc="2026-08-12T11:05:00+00:00",
        source_ref="https://www.idx.id/primary/TradingSummary/GetStockSummary?date=20260812",
        source_sha256="a" * 64,
    )


def test_archives_shares_and_five_character_codes() -> None:
    frame, meta = _parse(_payload())
    assert frame["security_code"].tolist() == ["BBCA", "GOTOM"]
    assert frame.loc[0, "foreign_net"] == 200
    assert set(frame["unit"]) == {"SHARES"}
    assert meta["five_character_codes"] == 1
    assert meta["zero_flow_rows"] == 1
    assert meta["publication_time_known"] is False
    assert meta["common_share_filter_applied"] is False
    assert pd.api.types.is_datetime64_any_dtype(frame["session_date"])


def test_missing_flow_fails_closed() -> None:
    payload = _payload()
    del payload["data"][0]["ForeignBuy"]
    with pytest.raises(ValueError, match="absent"):
        _parse(payload)


def test_partial_payload_fails_closed() -> None:
    payload = _payload()
    payload["recordsTotal"] = 3
    with pytest.raises(ValueError, match="completeness mismatch"):
        _parse(payload)


@pytest.mark.parametrize("field", ["recordsTotal", "recordsFiltered"])
def test_fractional_record_metadata_fails_closed(field: str) -> None:
    payload = _payload()
    payload[field] = 2.5
    with pytest.raises(ValueError, match="non-negative integer"):
        _parse(payload)


@pytest.mark.parametrize("value", [12.5, "12.5", float("inf"), -1])
def test_fractional_infinite_or_negative_shares_fail_closed(value: object) -> None:
    payload = _payload()
    payload["data"][0]["ForeignBuy"] = value  # type: ignore[index]
    with pytest.raises(ValueError, match="non-negative integer|missing/invalid"):
        _parse(payload)
