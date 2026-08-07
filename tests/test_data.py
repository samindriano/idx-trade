import pandas as pd

from idx_trade.data import canonicalize_ohlcv, raw_execution_prices


def test_raw_execution_prices_are_not_overwritten_by_vendor_adjustment():
    frame = pd.DataFrame(
        {
            "date": ["2025-01-02", "2025-01-03"],
            "open": [100.0, 110.0],
            "high": [105.0, 115.0],
            "low": [95.0, 108.0],
            "close": [102.0, 112.0],
            "volume": [1_000, 2_000],
            "adj_close": [51.0, 56.0],
            "dividends": [0.0, 0.0],
            "stock_splits": [0.0, 0.0],
        }
    )
    data = canonicalize_ohlcv(frame, "TEST")
    execution = raw_execution_prices(data)
    assert execution["raw_open"].tolist() == [100.0, 110.0]
    assert execution["raw_close"].tolist() == [102.0, 112.0]
    assert data["vendor_total_return_factor"].tolist() == [0.5, 0.5]


def test_corporate_action_sequence_is_calculated_after_date_sort():
    frame = pd.DataFrame(
        {
            "date": ["2025-01-03", "2025-01-01", "2025-01-02"],
            "open": [50.0, 100.0, 100.0],
            "high": [51.0, 101.0, 101.0],
            "low": [49.0, 99.0, 99.0],
            "close": [50.0, 100.0, 100.0],
            "volume": [1_000, 1_000, 1_000],
            "adj_close": [50.0, 50.0, 50.0],
            "stock_splits": [2.0, 0.0, 0.0],
            "dividends": [0.0, 0.0, 0.0],
        }
    )
    data = canonicalize_ohlcv(frame, "TEST")
    assert data["date"].is_monotonic_increasing
    assert data.loc[data["date"].eq(pd.Timestamp("2025-01-03")), "explicit_split_event"].item()
    assert not data.loc[data["date"].eq(pd.Timestamp("2025-01-01")), "explicit_split_event"].item()
