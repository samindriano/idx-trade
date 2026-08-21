from __future__ import annotations

from typing import Any

import pandas as pd

from .decision_v2_failure_diagnosis import FrozenStructuralLedgers
from .decision_v3_kill_diagnosis import (
    _rank_lookup,
    _supply_counts,
    _top10_by_index,
)


def build_residual_underfill_supply_decomposition(
    score_frame: pd.DataFrame,
    ledgers: FrozenStructuralLedgers,
) -> pd.DataFrame:
    """Measure supply remaining after the frozen V2 target is formed.

    On an underfilled V2 session, any core challenger already used by V2 is
    part of the end-of-session target and therefore must not be counted again
    as available supply. This makes the proposed near-history supply test
    conservative and avoids double-counting already-consumed core names.
    """
    rank_lookup = _rank_lookup(score_frame)
    top10_by_index = _top10_by_index(score_frame)
    target_by_index = {
        int(index): set(group["ticker"].astype(str))
        for index, group in ledgers.memberships.groupby("index", sort=True)
    }
    underfilled = ledgers.sessions.loc[
        ledgers.sessions["capacity_state"].eq(
            "UNFILLED_NO_QUALIFIED_CHALLENGER"
        )
    ].copy()

    rows: list[dict[str, Any]] = []
    for session in underfilled.itertuples(index=False):
        index = int(session.index)
        unavailable = {index: set(target_by_index.get(index, set()))}
        supply = _supply_counts(
            index,
            top10_by_index=top10_by_index,
            held_start=unavailable,
            rank_lookup=rank_lookup,
        )
        vacancies = int(session.unfilled_slots)
        core = int(supply["LE20"])
        near = int(supply["21_30"] + supply["31_50"])
        rows.append(
            {
                "index": index,
                "date": str(session.date),
                "block": index // 100 + 1,
                "vacancies": vacancies,
                "core_le20_supply": core,
                "previous_21_30_supply": int(supply["21_30"]),
                "previous_31_50_supply": int(supply["31_50"]),
                "previous_51_100_supply": int(supply["51_100"]),
                "previous_101_200_supply": int(supply["101_200"]),
                "previous_gt200_supply": int(supply["GT200"]),
                "previous_absent_supply": int(supply["ABSENT"]),
                "core_plus_21_50_supply": core + near,
                "core_plus_21_50_ge_vacancies": core + near >= vacancies,
            }
        )
    return pd.DataFrame(rows)
