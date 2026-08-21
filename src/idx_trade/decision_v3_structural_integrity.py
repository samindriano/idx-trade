from __future__ import annotations

from dataclasses import replace
from typing import Any

import pandas as pd

from .decision_v3_structural_replay import StructuralReplayResult
from .decision_v3_structural_source import (
    DecisionV3StructuralReplayError,
    PinnedReplaySource,
)


def validate_post_replay_integrity(
    result: StructuralReplayResult,
    source: PinnedReplaySource,
) -> StructuralReplayResult:
    """Fail closed on target/intent integrity independent of Decision plan objects.

    This validator reconstructs transitions from emitted ledgers plus the pinned
    full rank path. It is intentionally downstream from replay/gate computation:
    any mismatch aborts artifact promotion rather than silently changing a gate.
    """
    sessions = result.primary.session_ledger
    membership = result.primary.membership_ledger
    intents = result.primary.intent_ledger
    source_frame = source.frame

    if sessions.empty or membership.empty:
        raise DecisionV3StructuralReplayError(
            "DECISION_V3_POST_REPLAY_INTEGRITY_EMPTY_LEDGER"
        )

    violations: dict[str, int] = {
        "target_ticker_missing_current_rank_count": 0,
        "target_rank_gt50_after_processing_count": 0,
        "target_entry_not_top10_count": 0,
        "target_entry_previous_absent_count": 0,
        "target_entry_without_buy_intent_count": 0,
        "buy_intent_not_in_target_count": 0,
        "universe_exit_missing_intent_count": 0,
        "universe_exit_retained_count": 0,
    }

    source_by_index: dict[int, pd.DataFrame] = {}
    dates = list(
        sessions.sort_values("session_index", kind="mergesort")["date"].astype(str)
    )
    for index, day in enumerate(dates):
        block = source_frame.loc[
            pd.to_datetime(source_frame["date"]).dt.strftime("%Y-%m-%d").eq(day)
        ]
        if block.empty:
            raise DecisionV3StructuralReplayError(
                f"DECISION_V3_POST_REPLAY_SOURCE_DATE_MISSING:{day}"
            )
        source_by_index[index] = block

    target_by_index: dict[int, set[str]] = {
        int(index): set(block["ticker"].astype(str))
        for index, block in membership.groupby("session_index", sort=True)
    }
    rank_by_index: dict[int, dict[str, int]] = {
        index: {
            str(row.ticker): int(row.rank_consensus)
            for row in block.loc[:, ["ticker", "rank_consensus"]].itertuples(index=False)
        }
        for index, block in source_by_index.items()
    }
    universe_by_index = {
        index: set(ranks) for index, ranks in rank_by_index.items()
    }

    buy_by_index: dict[int, set[str]] = {}
    universe_sell_by_index: dict[int, set[str]] = {}
    if not intents.empty:
        for index, block in intents.groupby("session_index", sort=True):
            idx = int(index)
            buy_by_index[idx] = set(
                block.loc[block["side"].eq("BUY_INTENT"), "ticker"].astype(str)
            )
            universe_sell_by_index[idx] = set(
                block.loc[
                    block["side"].eq("SELL_INTENT")
                    & block["reason"].eq("UNIVERSE_EXIT"),
                    "ticker",
                ].astype(str)
            )

    for index in range(len(dates)):
        target = target_by_index.get(index, set())
        ranks = rank_by_index[index]
        for ticker in target:
            rank = ranks.get(ticker)
            if rank is None:
                violations["target_ticker_missing_current_rank_count"] += 1
                continue
            if rank > 50:
                violations["target_rank_gt50_after_processing_count"] += 1

        if index == 0:
            continue

        previous_target = target_by_index.get(index - 1, set())
        entries = target - previous_target
        buys = buy_by_index.get(index, set())
        previous_universe = universe_by_index[index - 1]

        for ticker in entries:
            rank = ranks.get(ticker)
            if rank is None or rank > 10:
                violations["target_entry_not_top10_count"] += 1
            if ticker not in previous_universe:
                violations["target_entry_previous_absent_count"] += 1
            if ticker not in buys:
                violations["target_entry_without_buy_intent_count"] += 1

        for ticker in buys:
            if ticker not in target:
                violations["buy_intent_not_in_target_count"] += 1

        absent_incumbents = previous_target - universe_by_index[index]
        universe_sells = universe_sell_by_index.get(index, set())
        for ticker in absent_incumbents:
            if ticker not in universe_sells:
                violations["universe_exit_missing_intent_count"] += 1
            if ticker in target:
                violations["universe_exit_retained_count"] += 1

    if any(violations.values()):
        details = ",".join(
            f"{key}={value}" for key, value in violations.items() if value
        )
        raise DecisionV3StructuralReplayError(
            f"DECISION_V3_POST_REPLAY_INTEGRITY_FAILED:{details}"
        )

    summary = dict(result.summary)
    guards = dict(summary.get("guards", {}))
    guards["post_replay_independent_integrity_passed"] = True
    guards["post_replay_integrity_violations"] = violations
    summary["guards"] = guards
    return replace(result, summary=summary)
