import pandas as pd
import pytest

from idx_trade.secondary_open_witness import (
    SECONDARY_WITNESS_MARKER,
    cross_validate_secondary_open_witness,
    merge_secondary_open_witness_history,
)


def _official(**overrides):
    row = {
        "ticker": "FREN",
        "date": "2025-04-14",
        "official_high": 23,
        "official_low": 22,
        "official_close": 23,
        "official_volume": 72980000,
        "official_source_ref": "idx://20250414",
    }
    row.update(overrides)
    return pd.DataFrame([row])


def _secondary(**overrides):
    row = {
        "ticker": "FREN",
        "date": "2025-04-14",
        "secondary_open": 23,
        "secondary_high": 23,
        "secondary_low": 22,
        "secondary_close": 23,
        "secondary_source_ref": "secondary://fren/20250414",
    }
    row.update(overrides)
    return pd.DataFrame([row])


def test_matching_hlc_accepts_secondary_open():
    accepted, diagnostics = cross_validate_secondary_open_witness(_official(), _secondary())
    assert len(accepted) == 1
    assert accepted.loc[0, "raw_open"] == 23
    assert accepted.loc[0, "raw_high"] == 23
    assert accepted.loc[0, "raw_volume"] == 72980000
    assert accepted.loc[0, "price_source"] == SECONDARY_WITNESS_MARKER
    assert accepted.loc[0, "price_source_ref"] == "idx://20250414"
    assert accepted.loc[0, "secondary_open_source_ref"] == "secondary://fren/20250414"
    assert diagnostics.loc[0, "status"] == "ACCEPTED"


@pytest.mark.parametrize(
    ("field", "value", "diagnostic"),
    [
        ("secondary_high", 24, "CROSS_SOURCE_PRICE_MISMATCH_HIGH"),
        ("secondary_low", 21, "CROSS_SOURCE_PRICE_MISMATCH_LOW"),
        ("secondary_close", 22, "CROSS_SOURCE_PRICE_MISMATCH_CLOSE"),
    ],
)
def test_mismatched_hlc_rejects_secondary_open(field, value, diagnostic):
    accepted, diagnostics = cross_validate_secondary_open_witness(
        _official(), _secondary(**{field: value})
    )
    assert accepted.empty
    assert diagnostics.loc[0, "diagnostic"] == diagnostic


def test_open_outside_official_range_rejects():
    accepted, diagnostics = cross_validate_secondary_open_witness(
        _official(), _secondary(secondary_open=30)
    )
    assert accepted.empty
    assert diagnostics.loc[0, "diagnostic"] == "SECONDARY_OPEN_OUTSIDE_OFFICIAL_RANGE"


def test_existing_primary_price_is_never_overwritten():
    existing = pd.DataFrame(
        {
            "ticker": ["FREN"],
            "date": [pd.Timestamp("2025-04-14")],
            "raw_open": [22.0],
            "raw_high": [23.0],
            "raw_low": [22.0],
            "raw_close": [23.0],
            "raw_volume": [1.0],
        }
    )
    candidate, _ = cross_validate_secondary_open_witness(_official(), _secondary())
    merged, diagnostics = merge_secondary_open_witness_history(existing, candidate, "FREN")
    assert merged.loc[0, "raw_open"] == 22.0
    assert len(diagnostics) == 1


def test_empty_fren_artifact_can_be_created_from_witness_rows():
    candidate, _ = cross_validate_secondary_open_witness(_official(), _secondary())
    merged, _ = merge_secondary_open_witness_history(pd.DataFrame(), candidate, "FREN")
    assert len(merged) == 1
    assert merged.loc[0, "ticker"] == "FREN"


def test_one_ticker_failure_does_not_stop_other_tickers():
    official = pd.concat(
        [
            _official(),
            _official(
                ticker="MASA",
                date="2024-07-25",
                official_high=6200,
                official_low=6150,
                official_close=6200,
                official_volume=90400,
                official_source_ref="idx://20240725",
            ),
        ],
        ignore_index=True,
    )
    secondary = pd.concat(
        [
            _secondary(secondary_high=24),
            _secondary(ticker="MASA", date="2024-07-25", secondary_open=6150, secondary_high=6200, secondary_low=6150, secondary_close=6200, secondary_source_ref="secondary://masa/20240725"),
        ],
        ignore_index=True,
    )
    accepted, diagnostics = cross_validate_secondary_open_witness(official, secondary)
    assert accepted["ticker"].tolist() == ["MASA"]
    assert set(diagnostics["ticker"]) == {"FREN", "MASA"}
