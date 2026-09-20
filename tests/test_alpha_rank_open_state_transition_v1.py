import pandas as pd

from research.alpha_rank_open_state_transition_v1 import (
    open_ready,
    rank_band,
    transition_type,
)


def test_open_ready_requires_positive_in_range_value():
    assert open_ready(10, 12, 8)
    assert not open_ready(0, 12, 8)
    assert not open_ready(13, 12, 8)
    assert not open_ready(None, 12, 8)


def test_rank_band_is_fixed_top30_partition():
    assert rank_band(1) == "1_10"
    assert rank_band(20) == "11_20"
    assert rank_band(30) == "21_30"
    assert rank_band(31) == ">30"


def test_transition_distinguishes_ranked_out_and_missing():
    selected = {"AAA"}
    assert transition_type("AAA", 3, selected) == "HOLD"
    assert transition_type("BBB", 3, selected) == "EXIT_RANKED_OUT"
    assert transition_type("CCC", None, selected) == "EXIT_RANK_MISSING"
