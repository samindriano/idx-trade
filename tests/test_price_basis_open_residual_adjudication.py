import pandas as pd

from idx_trade.price_basis_open_residual_adjudication import classify_residuals, summarize


def _rows():
    return pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "BBB", "CCC"],
            "date": ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"],
            "accepted_open": [10.0, 10.0, 10.0, 10.0],
            "factor_up_open": [20.0, 21.0, 20.0, 40.0],
            "official_open": [20.0, 20.0, 0.0, 0.0],
            "low": [19.0, 19.0, 19.0, 19.0],
            "high": [21.0, 22.0, 21.0, 30.0],
            "official_open_positive": [True, True, False, False],
            "official_open_within_corrected_hlc": [True, True, False, False],
            "factor_up_within_corrected_hlc": [True, True, True, False],
            "factor_up_equals_official": [True, False, False, False],
            "accepted_open_source": ["DERIVATIVE_OPEN"] * 4,
            "expected_factor": [2.0, 2.0, 2.0, 4.0],
        }
    )


def test_residual_classes_are_mutually_resolved_by_primary_evidence():
    out = classify_residuals(_rows())
    assert out["adjudication_class"].tolist() == [
        "OFFICIAL_IDX_OPEN_PRIMARY_CANDIDATE",
        "OFFICIAL_PRIMARY_FACTOR_DISAGREEMENT",
        "CA_FACTOR_FALLBACK_CANDIDATE",
        "UNRESOLVED_NO_OFFICIAL_FACTOR_OUT_OF_RANGE",
    ]


def test_residual_summary_counts():
    out = classify_residuals(_rows())
    got = summarize(out)
    assert got["rows"] == 4
    assert got["official_primary_candidates"] == 2
    assert got["factor_fallback_candidates"] == 1
    assert got["official_factor_disagreements"] == 1
    assert got["factor_range_failures"] == 1
    assert got["unresolved_no_official_no_factor"] == 1
