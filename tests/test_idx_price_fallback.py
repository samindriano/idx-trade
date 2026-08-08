import pandas as pd

from idx_trade.idx_price_fallback import stock_summary_price_rows


def _payload(*rows):
    return {"data": list(rows)}


def test_stock_summary_price_rows_extracts_regular_market_ohlcv():
    frames, diagnostics = stock_summary_price_rows(
        _payload(
            {
                "StockCode": "MFIN",
                "Date": "2025-03-24",
                "OpenPrice": 3300,
                "FirstTrade": 3310,
                "High": 3500,
                "Low": 3300,
                "Close": 3490,
                "Volume": 36800,
                "Frequency": 67,
            }
        ),
        requested_date="2025-03-24",
        source_ref="idx://20250324",
        tickers=["MFIN"],
    )
    frame = frames["MFIN"]
    assert frame.loc[0, "raw_open"] == 3300
    assert frame.loc[0, "raw_high"] == 3500
    assert frame.loc[0, "raw_low"] == 3300
    assert frame.loc[0, "raw_close"] == 3490
    assert frame.loc[0, "raw_volume"] == 36800
    assert frame.loc[0, "price_source"] == "IDX_PUBLIC_STOCK_SUMMARY"
    assert diagnostics.loc[0, "status"] == "PRICE_PARSED"
    assert diagnostics.loc[0, "diagnostic"] == "OPENPRICE"


def test_first_trade_is_used_only_when_official_open_price_is_unavailable():
    frames, diagnostics = stock_summary_price_rows(
        _payload(
            {
                "StockCode": "MASA",
                "Date": "2024-07-01",
                "OpenPrice": 0,
                "FirstTrade": 8300,
                "High": 8500,
                "Low": 8200,
                "Close": 8400,
                "Volume": 1000,
                "Frequency": 10,
            }
        ),
        requested_date="2024-07-01",
        source_ref="idx://20240701",
        tickers=["MASA"],
    )
    assert frames["MASA"].loc[0, "raw_open"] == 8300
    assert diagnostics.loc[0, "diagnostic"] == "FIRSTTRADE_FALLBACK"


def test_invalid_official_ohlc_remains_unresolved():
    frames, diagnostics = stock_summary_price_rows(
        _payload(
            {
                "StockCode": "MFIN",
                "Date": "2024-07-01",
                "OpenPrice": 0,
                "FirstTrade": 0,
                "High": 3500,
                "Low": 3300,
                "Close": 3400,
                "Volume": 100,
                "Frequency": 5,
            }
        ),
        requested_date="2024-07-01",
        source_ref="idx://20240701",
        tickers=["MFIN"],
    )
    assert frames == {}
    assert diagnostics.loc[0, "status"] == "UNRESOLVED_PRICE"
    assert diagnostics.loc[0, "diagnostic"] == "OFFICIAL_OHLC_MISSING_OR_NONPOSITIVE"


def test_zero_regular_volume_does_not_create_price_fallback():
    frames, diagnostics = stock_summary_price_rows(
        _payload(
            {
                "StockCode": "MFIN",
                "Date": "2024-07-01",
                "OpenPrice": 3400,
                "FirstTrade": 3400,
                "High": 3500,
                "Low": 3300,
                "Close": 3400,
                "Volume": 0,
                "Frequency": 0,
            }
        ),
        requested_date="2024-07-01",
        source_ref="idx://20240701",
        tickers=["MFIN"],
    )
    assert frames == {}
    assert diagnostics.loc[0, "status"] == "NOT_ACTIVE_PRICE_ROW"
