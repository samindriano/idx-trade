import pandas as pd

from idx_trade.data import (
    canonicalize_ohlcv,
    price_semantics_flags,
    raw_price_semantics_verified,
)


def _canonical() -> pd.DataFrame:
    return canonicalize_ohlcv(
        pd.DataFrame(
            {
                "date": pd.to_datetime(["2026-06-02", "2026-06-03"]),
                "open": [100.0, 101.0],
                "high": [102.0, 103.0],
                "low": [99.0, 100.0],
                "close": [101.0, 102.0],
                "volume": [1000, 1200],
                "adj_close": [100.5, 101.5],
            }
        ),
        ticker="AAAA",
    )


def test_canonical_raw_execution_frame_verifies_semantics():
    frame = _canonical()
    assert raw_price_semantics_verified(frame) is True


def test_adjusted_only_or_malformed_frame_does_not_verify():
    adjusted_only = pd.DataFrame(
        {
            "date": [pd.Timestamp("2026-06-02")],
            "vendor_adj_close": [100.0],
        }
    )
    assert raw_price_semantics_verified(adjusted_only) is False

    malformed = _canonical()
    malformed.loc[0, "raw_high"] = 50.0
    assert raw_price_semantics_verified(malformed) is False


def test_price_semantics_flags_are_deterministic_and_missing_is_false():
    frames = {"AAAA": _canonical()}
    flags = price_semantics_flags(frames, ["AAAA", "BBBB"])
    assert flags == {"AAAA": True, "BBBB": False}
