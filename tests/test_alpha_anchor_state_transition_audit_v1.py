from __future__ import annotations

import pandas as pd

from research.alpha_anchor_state_transition_audit_v1 import summarize


def test_transition_census_does_not_infer_lifecycle_semantics() -> None:
    anchor = pd.DataFrame(
        {
            "ticker": ["AAA"] * 4 + ["BBB"] * 2,
            "as_of_date": pd.to_datetime(
                ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04", "2025-01-01", "2025-01-02"]
            ),
            "state": ["ACTIVE", "NO_TRADE", "ACTIVE", "NO_TRADE", "NO_TRADE", "NO_TRADE"],
        }
    )

    result = summarize(anchor)

    assert result["status"] == "PASS_ANCHOR_STATE_TRANSITION_CENSUS"
    assert result["state_change_ticker_count"] == 1
    assert result["maximum_transitions"] == 3
    assert result["first_last_profiles"]["ACTIVE->NO_TRADE"] == 1
    assert "lifecycle" in result["interpretation"]
