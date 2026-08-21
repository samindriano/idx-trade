from __future__ import annotations

import pandas as pd

from idx_trade.decision_economic_robustness import summarize_six_blocks


def _synthetic_frame() -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=600)
    rows = []
    for index, date in enumerate(dates):
        block = index // 100 + 1
        for policy in ("NAIVE_TOP10", "DECISION_V1", "DECISION_V2", "DECISION_V3"):
            base = {"NAIVE_TOP10": 0.00, "DECISION_V1": -0.001, "DECISION_V2": 0.002, "DECISION_V3": 0.001}[policy]
            rows.append({
                "policy": policy,
                "date": date,
                "session_index": index,
                "block": block,
                "h5_complete_support": True,
                "h10_complete_support": True,
                "h5_gross_basket_return": base,
                "h10_gross_basket_return": base * 2.0,
                "h5_net_proxy_primary": base - 0.0002,
                "h10_net_proxy_primary": base * 2.0 - 0.0002,
            })
    return pd.DataFrame(rows)


def test_fixed_six_blocks_are_exact_100_session_segments() -> None:
    summary = summarize_six_blocks(_synthetic_frame())
    h5 = summary["horizons"]["H5"]
    assert h5["block_common_support_counts"] == [100, 100, 100, 100, 100, 100]
    assert [block["session_index_start"] for block in h5["blocks"]] == [0, 100, 200, 300, 400, 500]
    assert [block["session_index_end"] for block in h5["blocks"]] == [99, 199, 299, 399, 499, 599]


def test_v2_direct_advantage_is_counted_per_block() -> None:
    summary = summarize_six_blocks(_synthetic_frame())
    for horizon in ("H5", "H10"):
        counts = summary["horizons"][horizon]["robustness_counts"]
        assert counts["v2_beats_v3_gross_mean_blocks"] == 6
        assert counts["v2_beats_v3_primary_mean_blocks"] == 6
        assert counts["v2_beats_naive_gross_mean_blocks"] == 6
        assert counts["v2_beats_naive_primary_mean_blocks"] == 6
