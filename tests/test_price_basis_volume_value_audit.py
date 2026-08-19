import numpy as np
import pandas as pd

from idx_trade.price_basis_volume_value_audit import (
    classify_basis_ratio,
    classify_frame,
    repeated_nonunit_ratio_evidence,
    ticker_factor_evidence,
)


def test_classify_basis_ratio_core_cases():
    assert classify_basis_ratio(100, 100, 5)[0] == "SAME_BASIS"
    assert classify_basis_ratio(500, 100, 5)[0] == "CA_FACTOR"
    assert classify_basis_ratio(20, 100, 5)[0] == "INVERSE_CA_FACTOR"
    assert classify_basis_ratio(130, 100, 5)[0] == "OTHER_RATIO"
    label, ratio = classify_basis_ratio(np.nan, 100, 5)
    assert label == "INVALID_OR_MISSING"
    assert np.isnan(ratio)


def test_classify_frame_and_factor_evidence():
    frame = pd.DataFrame(
        {
            "ticker": ["AAA"] * 4 + ["BBB"] * 2,
            "panel": [500, 505, 510, 100, 200, 200],
            "official": [100, 101, 102, 100, 100, 100],
            "expected_factor": [5, 5, 5, 5, 2, 2],
        }
    )
    out = classify_frame(frame, panel_column="panel", official_column="official", output_prefix="x")
    evidence = ticker_factor_evidence(out, class_column="x_basis_class")
    aaa = evidence[evidence["ticker"].eq("AAA")].iloc[0]
    assert aaa["factor_consistent_rows"] == 3
    assert bool(aaa["requires_basis_remediation"])
    bbb = evidence[evidence["ticker"].eq("BBB")].iloc[0]
    assert bbb["factor_consistent_rows"] == 2
    assert not bool(bbb["requires_basis_remediation"])


def test_repeated_nonunit_ratio_evidence_detects_unit_scale():
    frame = pd.DataFrame(
        {
            "ticker": ["AAA"] * 5 + ["BBB"] * 3,
            "ratio": [100.0, 100.0, 100.0, 1.0, 1.01, 2.0, 2.0, 1.0],
        }
    )
    out = repeated_nonunit_ratio_evidence(frame, ratio_column="ratio")
    aaa = out[(out["ticker"].eq("AAA")) & (out["ratio_key"].eq(100.0))].iloc[0]
    assert aaa["rows"] == 3
    assert bool(aaa["requires_basis_review"])
    bbb = out[(out["ticker"].eq("BBB")) & (out["ratio_key"].eq(2.0))].iloc[0]
    assert bbb["rows"] == 2
    assert not bool(bbb["requires_basis_review"])
