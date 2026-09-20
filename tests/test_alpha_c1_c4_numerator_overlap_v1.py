from __future__ import annotations

import pandas as pd

from research.alpha_c1_c4_numerator_overlap_v1 import pair_summary, select_sets
from research.alpha_candidate_component_anatomy_v1 import CANDIDATES


def test_pair_summary_and_proxy_selection_are_deterministic() -> None:
    rows = []
    for index in range(32):
        rows.append(
            {
                "ticker": f"T{index:02d}",
                "date": pd.Timestamp("2025-01-02"),
                "eligible_decision_universe": True,
                CANDIDATES["C1"]: float(32 - index),
                f"rank_{CANDIDATES['C1']}": float(32 - index),
                "proxy": float(32 - index),
            }
        )
    frame = pd.DataFrame(rows)
    score, proxy = select_sets(frame, "C1", "proxy")
    summary = pair_summary(score, proxy)
    assert summary["common_dates"] == 1
    assert summary["overlap_fraction"]["median"] == 1.0
    assert summary["jaccard"]["median"] == 1.0
