from __future__ import annotations

import pandas as pd

from idx_trade.decision_economic_support_bias import summarize_support_bias


POLICIES = ("NAIVE_TOP10", "DECISION_V1", "DECISION_V2", "DECISION_V3")


def _frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2024-01-02", periods=600)
    outcome_rows = []
    turnover_rows = []
    for index, date in enumerate(dates):
        block = index // 100 + 1
        for policy in POLICIES:
            early = block <= 2
            # Early dates are broadly unsupported across all policies, except
            # one date where V2 alone is incomplete. Later dates are supported.
            if early:
                supported = index == 0
                if index == 1:
                    supported = policy != "DECISION_V2"
            else:
                supported = True
            state = (
                "TARGET_H5_AVAILABLE"
                if supported
                else "TARGET_H5_TERMINAL_UNAVAILABLE"
            )
            state10 = (
                "TARGET_H10_AVAILABLE"
                if supported
                else "TARGET_H10_TERMINAL_UNAVAILABLE"
            )
            outcome_rows.append(
                {
                    "policy": policy,
                    "date": date,
                    "target_size": 9 if policy == "DECISION_V2" else 10,
                    "cash_weight": 0.1 if policy == "DECISION_V2" else 0.0,
                    "h5_complete_support": supported,
                    "h5_unsupported_names": 0 if supported else 1,
                    "h5_support_states": state,
                    "h10_complete_support": supported,
                    "h10_unsupported_names": 0 if supported else 1,
                    "h10_support_states": state10,
                }
            )
            turnover_rows.append(
                {
                    "policy": policy,
                    "date": date,
                    "buy_count": 1,
                    "sell_count": 1,
                    "cost_bps_nav_primary": 6.0,
                    "session_index": index,
                    "block": block,
                }
            )
    outcomes = pd.DataFrame(outcome_rows)
    outcomes["session_index"] = outcomes["date"].map(
        {date: i for i, date in enumerate(dates)}
    )
    outcomes["block"] = outcomes["session_index"] // 100 + 1
    return outcomes, pd.DataFrame(turnover_rows)


def test_support_bias_distinguishes_broad_failure_from_v2_exclusive_failure() -> None:
    outcomes, turnover = _frames()
    summary = summarize_support_bias(outcomes, turnover)
    early = summary["horizons"]["H5"]["early_blocks_1_2"]

    assert early["common_support_dates"] == 1
    assert early["failure_multiplicity"]["dates_with_4_incomplete_policies"] == 198
    assert early["failure_multiplicity"]["dates_with_1_incomplete_policies"] == 1
    assert early["policies"]["DECISION_V2"]["exclusive_common_support_limiter_dates"] == 1
    assert early["policies"]["NAIVE_TOP10"]["exclusive_common_support_limiter_dates"] == 0
