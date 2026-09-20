import pandas as pd

from research.alpha_eligibility_selection_overlap_v1 import TOP_K, compare_sets, summarize_comparison, top_k_sets


def test_top_k_sets_and_cross_policy_comparison() -> None:
    tickers = [f"T{index:02d}" for index in range(TOP_K)]
    frame = pd.DataFrame(
        {
            "ticker": tickers + tickers,
            "date": pd.to_datetime(["2026-01-02"] * TOP_K + ["2026-01-05"] * TOP_K),
            "eligible_decision_universe": [True] * (2 * TOP_K),
            "rank_C1": list(range(TOP_K, 0, -1)) + list(range(TOP_K, 0, -1)),
        }
    )
    sets = top_k_sets(frame, "C1")
    assert sets[pd.Timestamp("2026-01-02")] == set(tickers)
    changed = {
        pd.Timestamp("2026-01-05"): set(tickers),
    }
    rows = compare_sets(sets, changed)
    assert len(rows) == 1
    assert rows.iloc[0]["overlap_fraction"] == 1.0
    assert summarize_comparison(rows)["exact_match_dates"] == 1
