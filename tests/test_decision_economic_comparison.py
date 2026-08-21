from __future__ import annotations

import pandas as pd

from idx_trade.decision_economic_comparison import (
    PolicyMembership,
    _transition_rows,
)


def test_membership_cost_proxy_one_replacement_primary_is_six_bps_nav() -> None:
    dates = (
        pd.Timestamp("2026-01-02"),
        pd.Timestamp("2026-01-05"),
    )
    first = tuple(f"T{i:02d}" for i in range(10))
    second = (*first[:-1], "NEW")
    policy = PolicyMembership(
        policy="DECISION_V3",
        by_date={dates[0]: first, dates[1]: second},
        source_root="synthetic",
        source_manifest_sha256=None,
    )

    rows = _transition_rows(policy, dates)
    transition = rows.iloc[1]

    assert int(transition["buy_count"]) == 1
    assert int(transition["sell_count"]) == 1
    # One 10%-NAV sell at 25 fee + 10 slippage bps and one 10%-NAV
    # buy at 15 fee + 10 slippage bps = 6 bps of portfolio NAV.
    assert float(transition["cost_bps_nav_primary"]) == 6.0


def test_underfill_is_cash_not_redistributed() -> None:
    dates = (pd.Timestamp("2026-01-02"),)
    target = tuple(f"T{i:02d}" for i in range(7))
    policy = PolicyMembership(
        policy="DECISION_V2",
        by_date={dates[0]: target},
        source_root="synthetic",
        source_manifest_sha256=None,
    )

    rows = _transition_rows(policy, dates)
    bootstrap = rows.iloc[0]

    assert int(bootstrap["target_size"]) == 7
    assert int(bootstrap["buy_count"]) == 7
    # The core contract is 10 fixed 10%-NAV seats.  Missing seats remain cash;
    # the seven names are not scaled up to 1/7 each.
    assert float(bootstrap["cost_bps_nav_primary"]) < 27.0
