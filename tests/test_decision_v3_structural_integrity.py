from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from idx_trade.decision_v3_structural_integrity import validate_post_replay_integrity
from idx_trade.decision_v3_structural_replay import ReplayTrace, StructuralReplayResult
from idx_trade.decision_v3_structural_source import (
    DecisionV3StructuralReplayError,
    PinnedReplaySource,
)


def _source(tmp_path: Path) -> PinnedReplaySource:
    rows = []
    for day, names in (
        ("2026-01-02", ["AAA", "BBB", "CCC", "DDD"]),
        ("2026-01-05", ["AAA", "BBB", "DDD"]),
    ):
        for rank, ticker in enumerate(names, start=1):
            rows.append(
                {
                    "ticker": ticker,
                    "date": pd.Timestamp(day),
                    "fold": "F1",
                    "mode": "OOS",
                    "alpha_consensus": float(10 - rank),
                    "rank_consensus": rank,
                }
            )
    manifest = tmp_path / "MANIFEST.json"
    score = tmp_path / "scores.parquet"
    manifest.write_text("{}", encoding="utf-8")
    score.write_bytes(b"synthetic")
    return PinnedReplaySource(pd.DataFrame(rows), manifest, score)


def _result(
    membership_rows: list[dict],
    intent_rows: list[dict],
) -> StructuralReplayResult:
    trace = ReplayTrace(
        session_ledger=pd.DataFrame(
            [
                {"session_index": 0, "date": "2026-01-02"},
                {"session_index": 1, "date": "2026-01-05"},
            ]
        ),
        membership_ledger=pd.DataFrame(membership_rows),
        intent_ledger=pd.DataFrame(intent_rows),
        state_ledger=pd.DataFrame(),
        holding_spells=pd.DataFrame(),
        fold_boundaries=pd.DataFrame(),
        plan_digest="x",
        correctness={},
    )
    return StructuralReplayResult(
        primary=trace,
        summary={"guards": {}, "status": "TEST", "verdict": "TEST"},
    )


def test_post_replay_integrity_accepts_consistent_entry_and_universe_exit(
    tmp_path: Path,
) -> None:
    source = _source(tmp_path)
    result = _result(
        [
            {"session_index": 0, "ticker": "AAA", "rank_consensus": 1},
            {"session_index": 0, "ticker": "BBB", "rank_consensus": 2},
            {"session_index": 0, "ticker": "CCC", "rank_consensus": 3},
            {"session_index": 1, "ticker": "AAA", "rank_consensus": 1},
            {"session_index": 1, "ticker": "BBB", "rank_consensus": 2},
            {"session_index": 1, "ticker": "DDD", "rank_consensus": 3},
        ],
        [
            {
                "session_index": 1,
                "side": "SELL_INTENT",
                "ticker": "CCC",
                "reason": "UNIVERSE_EXIT",
            },
            {
                "session_index": 1,
                "side": "BUY_INTENT",
                "ticker": "DDD",
                "reason": "TIER_A_VACANCY_FILL",
            },
        ],
    )
    checked = validate_post_replay_integrity(result, source)
    assert checked.summary["guards"]["post_replay_independent_integrity_passed"] is True
    assert not any(
        checked.summary["guards"]["post_replay_integrity_violations"].values()
    )


def test_post_replay_integrity_rejects_phantom_target_without_buy(
    tmp_path: Path,
) -> None:
    source = _source(tmp_path)
    result = _result(
        [
            {"session_index": 0, "ticker": "AAA", "rank_consensus": 1},
            {"session_index": 0, "ticker": "BBB", "rank_consensus": 2},
            {"session_index": 1, "ticker": "AAA", "rank_consensus": 1},
            {"session_index": 1, "ticker": "DDD", "rank_consensus": 3},
        ],
        [],
    )
    with pytest.raises(
        DecisionV3StructuralReplayError,
        match="target_entry_without_buy_intent_count=1",
    ):
        validate_post_replay_integrity(result, source)


def test_post_replay_integrity_rejects_buy_not_promoted_to_target(
    tmp_path: Path,
) -> None:
    source = _source(tmp_path)
    result = _result(
        [
            {"session_index": 0, "ticker": "AAA", "rank_consensus": 1},
            {"session_index": 1, "ticker": "AAA", "rank_consensus": 1},
        ],
        [
            {
                "session_index": 1,
                "side": "BUY_INTENT",
                "ticker": "DDD",
                "reason": "TIER_A_VACANCY_FILL",
            }
        ],
    )
    with pytest.raises(
        DecisionV3StructuralReplayError,
        match="buy_intent_not_in_target_count=1",
    ):
        validate_post_replay_integrity(result, source)


def test_post_replay_integrity_rejects_missing_universe_exit_intent(
    tmp_path: Path,
) -> None:
    source = _source(tmp_path)
    result = _result(
        [
            {"session_index": 0, "ticker": "AAA", "rank_consensus": 1},
            {"session_index": 0, "ticker": "CCC", "rank_consensus": 3},
            {"session_index": 1, "ticker": "AAA", "rank_consensus": 1},
        ],
        [],
    )
    with pytest.raises(
        DecisionV3StructuralReplayError,
        match="universe_exit_missing_intent_count=1",
    ):
        validate_post_replay_integrity(result, source)
