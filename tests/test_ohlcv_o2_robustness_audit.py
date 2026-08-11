import numpy as np
import pandas as pd

from idx_trade.ohlcv_o2_robustness_audit import (
    _bounds_and_algebra,
    _choose_recommendation,
    canonical_provenance,
)


def test_canonical_provenance_is_deterministic_and_explicit_for_missing_values() -> None:
    frame = pd.DataFrame({"open_source": ["YAHOO_YFINANCE", None, ""], "open_evidence_class": ["DIRECT_RAW_HLC_EXACT", None, ""]})
    assert canonical_provenance(frame).tolist() == [
        "YAHOO_YFINANCE|DIRECT_RAW_HLC_EXACT",
        "UNRESOLVED|UNRESOLVED",
        "UNRESOLVED|UNRESOLVED",
    ]


def test_geometry_bounds_and_algebra_contract() -> None:
    frame = pd.DataFrame({"open_position": [0.0, 0.5, 1.0], "open_to_high": [1.0, 0.5, 0.0], "open_to_low": [0.0, -0.5, -0.6666666666666667]})
    result = _bounds_and_algebra(frame)
    assert result["open_position_below_zero"] == 0
    assert result["open_position_above_one"] == 0
    assert result["open_to_high_negative"] == 0
    assert result["open_to_low_positive"] == 0
    assert result["algebra_denominator_zero_or_invalid"] == 0
    assert result["algebra_rows_with_error_over_tolerance"] == 0


def test_recommendation_is_exactly_one_allowed_value() -> None:
    bounds = {key: 0 for key in ["nonfinite_open_position", "nonfinite_open_to_high", "nonfinite_open_to_low", "open_position_below_zero", "open_position_above_one", "open_to_high_negative", "open_to_low_positive", "algebra_denominator_zero_or_invalid", "algebra_rows_with_error_over_tolerance"]}
    sensitivity = pd.DataFrame({"mean_paired_pr_auc_delta": [0.001, 0.002]})
    recommendation, _ = _choose_recommendation(bounds, sensitivity)
    assert recommendation == "O2_ROBUSTNESS_PASS_MINIMALITY_AUDIT_RECOMMENDED"


def test_recommendation_stops_on_sensitivity_reversal() -> None:
    bounds = {key: 0 for key in ["nonfinite_open_position", "nonfinite_open_to_high", "nonfinite_open_to_low", "open_position_below_zero", "open_position_above_one", "open_to_high_negative", "open_to_low_positive", "algebra_denominator_zero_or_invalid", "algebra_rows_with_error_over_tolerance"]}
    sensitivity = pd.DataFrame({"mean_paired_pr_auc_delta": [0.001, -0.0001]})
    recommendation, _ = _choose_recommendation(bounds, sensitivity)
    assert recommendation == "O2_ROBUSTNESS_CONCERN_STOP"
