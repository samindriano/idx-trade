import pandas as pd

from idx_trade.price_basis_open_forensic import classify_open_basis, summary


def test_factor_up_reconstructs_raw_open():
    rows = pd.DataFrame(
        {
            "accepted_open": [50.0, 20.0],
            "low": [95.0, 95.0],
            "high": [110.0, 110.0],
            "expected_factor": [2.0, 5.0],
            "official_open": [100.0, 100.0],
        }
    )
    out = classify_open_basis(rows)
    assert out["accepted_within_corrected_hlc"].tolist() == [False, False]
    assert out["factor_up_within_corrected_hlc"].tolist() == [True, True]
    assert out["factor_up_equals_official"].tolist() == [True, True]
    result = summary(out)
    assert result["rows"] == 2
    assert result["factor_up_equals_official"] == 2


def test_official_open_can_be_missing_without_becoming_match():
    rows = pd.DataFrame(
        {
            "accepted_open": [50.0],
            "low": [95.0],
            "high": [110.0],
            "expected_factor": [2.0],
            "official_open": [None],
        }
    )
    out = classify_open_basis(rows)
    assert not bool(out.loc[0, "official_open_positive"])
    assert not bool(out.loc[0, "factor_up_equals_official"])
    assert bool(out.loc[0, "factor_up_within_corrected_hlc"])
