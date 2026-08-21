from __future__ import annotations

from pathlib import Path

import pandas as pd

from idx_trade.decision_v2_failure_diagnosis import FrozenStructuralLedgers
from idx_trade.decision_v3_kill_supply import (
    build_residual_underfill_supply_decomposition,
)


def test_underfill_supply_does_not_double_count_core_already_used_by_v2(
    tmp_path: Path,
) -> None:
    dates = [pd.Timestamp("2026-01-01"), pd.Timestamp("2026-01-02")]
    rows = []
    tickers = [chr(ord("A") + i) for i in range(12)]
    for index, date in enumerate(dates):
        if index == 0:
            order = tickers
        else:
            order = ["B", "C", "A", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
        for rank, ticker in enumerate(order, start=1):
            rows.append(
                {
                    "date": date,
                    "ticker": ticker,
                    "rank_consensus": rank,
                }
            )
    score = pd.DataFrame(rows)

    # Previous ranks: B=2 (core), C=3 would also be core in this toy, so make
    # C's previous rank 25 by adding enough names to the previous session.
    extra = []
    previous_order = ["A", "B"] + [f"X{i:02d}" for i in range(1, 23)] + ["C"]
    previous_rows = []
    for rank, ticker in enumerate(previous_order, start=1):
        previous_rows.append(
            {
                "date": dates[0],
                "ticker": ticker,
                "rank_consensus": rank,
            }
        )
    current_rows = score.loc[score["date"].eq(dates[1])].to_dict(orient="records")
    score = pd.DataFrame(previous_rows + current_rows)

    sessions = pd.DataFrame(
        [
            {
                "index": 0,
                "date": "2026-01-01",
                "capacity_state": "FULL",
                "unfilled_slots": 0,
            },
            {
                "index": 1,
                "date": "2026-01-02",
                "capacity_state": "UNFILLED_NO_QUALIFIED_CHALLENGER",
                "unfilled_slots": 1,
            },
        ]
    )
    # B is already consumed into the frozen V2 target. C remains outside it.
    memberships = pd.DataFrame(
        [
            {"index": 0, "ticker": ticker}
            for ticker in ["A", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
        ]
        + [
            {"index": 1, "ticker": ticker}
            for ticker in ["A", "B", "D", "E", "F", "G", "H", "I", "J"]
        ]
    )
    ledgers = FrozenStructuralLedgers(
        root=tmp_path,
        manifest={},
        sessions=sessions,
        memberships=memberships,
        intents=pd.DataFrame(),
        states=pd.DataFrame(),
    )

    result = build_residual_underfill_supply_decomposition(score, ledgers)
    assert len(result) == 1
    row = result.iloc[0]
    assert int(row["core_le20_supply"]) == 0
    assert int(row["previous_21_30_supply"]) == 1
    assert bool(row["core_plus_21_50_ge_vacancies"]) is True
