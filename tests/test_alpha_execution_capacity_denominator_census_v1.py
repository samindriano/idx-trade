from research.alpha_execution_capacity_denominator_census_v1 import classify_value


def test_classify_value_distinguishes_zero_invalid_and_positive():
    assert classify_value(10) == "VALID_POSITIVE"
    assert classify_value(0) == "VALID_ZERO"
    assert classify_value(-1) == "INVALID_NEGATIVE"
    assert classify_value(None) == "INVALID_NONFINITE"
