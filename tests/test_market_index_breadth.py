import pandas as pd
import pytest

from idx_trade.market_index_breadth import (
    OfficialIDXMarketContextProvider,
    canonicalize_idx_index_summary,
    canonicalize_idx_stock_summary,
    derive_stock_summary_breadth,
    pit_timing_ready,
    reconcile_index_stock_aggregates,
)


SHA = "a" * 64


def _index_rows():
    return [{
        "Date": "2026-07-31T00:00:00",
        "IndexCode": "COMPOSITE",
        "Previous": 100.0,
        "Highest": 105.0,
        "Lowest": 99.0,
        "Close": 104.0,
        "Change": 4.0,
        "Volume": 1000,
        "Value": 2500000,
        "Frequency": 20,
        "MarketCapital": 100000000,
        "NumberOfStock": 5,
    }]


def _stock_rows():
    return [
        {"Date": "2026-07-31", "StockCode": "AAA", "Change": 2, "Volume": 100, "Value": 1000, "Frequency": 2,
         "NonRegularVolume": 0, "NonRegularValue": 0, "NonRegularFrequency": 0},
        {"Date": "2026-07-31", "StockCode": "BBB", "Change": -1, "Volume": 200, "Value": 2000, "Frequency": 3,
         "NonRegularVolume": 0, "NonRegularValue": 0, "NonRegularFrequency": 0},
        {"Date": "2026-07-31", "StockCode": "CCC", "Change": 0, "Volume": 0, "Value": 0, "Frequency": 0,
         "NonRegularVolume": 50, "NonRegularValue": 500, "NonRegularFrequency": 1},
    ]


def test_index_contract_keeps_knowledge_time_unresolved():
    frame = canonicalize_idx_index_summary(
        _index_rows(),
        source_ref="idx://TradingSummary/GetIndexSummary/2026-07-31",
        source_url="https://block.idx.id/primary/TradingSummary/GetIndexSummary",
        source_sha256=SHA,
        retrieved_at="2026-08-12T04:00:00Z",
    )
    assert frame.loc[0, "index_code"] == "COMPOSITE"
    assert frame.loc[0, "trading_value_idr"] == 2_500_000
    assert frame.loc[0, "pit_timing_status"] == "UNRESOLVED_NO_PUBLICATION_TIMESTAMP"
    assert not pit_timing_ready(frame)


def test_index_contract_rejects_bad_ohlc_and_duplicate_rows():
    rows = _index_rows() + _index_rows()
    with pytest.raises(ValueError, match="Duplicate"):
        canonicalize_idx_index_summary(
            rows,
            source_ref="idx://duplicate",
            source_url=None,
            source_sha256=SHA,
        )
    bad = _index_rows()
    bad[0]["Lowest"] = 106
    with pytest.raises(ValueError, match="Index High|Index Low"):
        canonicalize_idx_index_summary(
            bad,
            source_ref="idx://bad",
            source_url=None,
            source_sha256=SHA,
        )


def test_stock_contract_does_not_promote_open_price():
    rows = _stock_rows()
    rows[0]["OpenPrice"] = 123
    frame = canonicalize_idx_stock_summary(
        rows,
        source_ref="idx://TradingSummary/GetStockSummary/2026-07-31",
        source_url="https://block.idx.id/primary/TradingSummary/GetStockSummary",
        source_sha256=SHA,
    )
    assert "OpenPrice" not in frame.columns
    assert frame["regular_volume"].tolist() == [100.0, 200.0, 0.0]


def test_derived_breadth_excludes_zero_volume_from_unchanged():
    frame = canonicalize_idx_stock_summary(
        _stock_rows(),
        source_ref="idx://stock-summary",
        source_url=None,
        source_sha256=SHA,
    )
    breadth = derive_stock_summary_breadth(frame)
    row = breadth.iloc[0]
    assert (row["advancing_rows"], row["declining_rows"], row["unchanged_traded_rows"]) == (1, 1, 0)
    assert row["zero_volume_rows"] == 1
    assert bool(row["official_breadth_field_present"]) is False


def test_aggregate_reconciliation_is_explicit():
    index = canonicalize_idx_index_summary(
        [{**_index_rows()[0], "Volume": 350, "Value": 3500, "Frequency": 6}],
        source_ref="idx://index",
        source_url=None,
        source_sha256=SHA,
    )
    stock = canonicalize_idx_stock_summary(
        _stock_rows(),
        source_ref="idx://stock",
        source_url=None,
        source_sha256=SHA,
    )
    audit = reconcile_index_stock_aggregates(index, stock)
    assert audit.loc[0, "exact_reconciliation"]


def test_provider_uses_official_primary_paths_without_open():
    class FakeSession:
        def __init__(self):
            self.calls = []

        def get(self, url, **kwargs):
            self.calls.append((url, kwargs["params"]))

            class Response:
                def raise_for_status(self):
                    return None

                def json(self):
                    return {"data": []}

            return Response()

    session = FakeSession()
    provider = OfficialIDXMarketContextProvider(session=session)
    provider.fetch_index_summary("2026-07-31")
    provider.fetch_stock_summary("2026-07-31")
    assert session.calls == [
        ("https://block.idx.id/primary/TradingSummary/GetIndexSummary", {"length": 100, "start": 0, "date": "2026-07-31"}),
        ("https://block.idx.id/primary/TradingSummary/GetStockSummary", {"length": 100, "start": 0, "date": "2026-07-31"}),
    ]
