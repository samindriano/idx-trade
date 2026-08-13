import pandas as pd

from idx_trade.pit_safe_reproduction import _identity_delta


def test_identity_delta_is_deterministic_and_explicit():
    old = pd.DataFrame(
        {
            "ticker": ["AAAA", "BBBB"],
            "date": pd.to_datetime(["2024-01-02", "2024-01-02"]),
        }
    )
    new = old.iloc[[0]].copy()
    result = _identity_delta(old, new)
    assert result["removed_rows"] == 1
    assert result["added_rows"] == 0
    assert result["removed_tickers"] == ["BBBB"]
