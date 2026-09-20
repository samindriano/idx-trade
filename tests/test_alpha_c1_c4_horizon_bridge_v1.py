import pandas as pd

from research.alpha_c1_c4_horizon_bridge_v1 import TOP_K, compare_pair, signal_sets


def test_signal_sets_and_pair_compare() -> None:
    tickers = [f"T{index:02d}" for index in range(TOP_K)]
    frame = pd.DataFrame(
        {
            "ticker": tickers + tickers,
            "date": pd.to_datetime(["2026-01-02"] * TOP_K + ["2026-01-05"] * TOP_K),
            "eligible_decision_universe": [True] * (2 * TOP_K),
            "C1_residual_reversal_5_v1": list(range(TOP_K, 0, -1)) + list(range(TOP_K, 0, -1)),
            "c1_raw_reversal_5": list(range(TOP_K, 0, -1)) + list(range(TOP_K, 0, -1)),
            "c1_residual_numerator": list(range(TOP_K, 0, -1)) + list(range(TOP_K, 0, -1)),
            "C4_path_efficiency_reversal_20_v1": list(range(TOP_K, 0, -1)) + list(range(TOP_K, 0, -1)),
            "c4_raw_reversal_20": list(range(TOP_K, 0, -1)) + list(range(TOP_K, 0, -1)),
        }
    )
    assert len(signal_sets(frame, "C1_STORED")) == 2
    result = compare_pair(frame, "C1_STORED", "C4_STORED")
    assert result["common_selection_dates"] == 2
    assert result["mean_overlap_fraction"] == 1.0
    assert result["exact_match_fraction"] == 1.0
