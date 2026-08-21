from __future__ import annotations

from pathlib import Path

from idx_trade.decision_v3_quality_supply_diagnosis import (
    _future_quality,
    classify_top10_supply,
    verify_quality_supply_contract,
)


def test_classify_top10_supply_respects_prior_rank_and_holdings() -> None:
    current = {"AAA": 1, "BBB": 2, "CCC": 3, "DDD": 4, "EEE": 11}
    previous = {"AAA": 10, "BBB": 35, "CCC": 90}
    result = classify_top10_supply(
        current_ranks=current,
        previous_ranks=previous,
        start_holdings={"AAA"},
    )
    assert result == {
        "A": [],
        "B": ["BBB"],
        "C": ["CCC"],
        "D": ["DDD"],
    }


def test_future_quality_uses_immediately_previous_observed_rank() -> None:
    maps = {
        0: {"XYZ": 80},
        1: {"XYZ": 5},
        2: {"XYZ": 7},
        3: {"XYZ": 25},
        4: {"XYZ": 4},
    }
    assert _future_quality(ticker="XYZ", entry_index=1, horizon=1, rank_maps=maps) == (7, True)
    assert _future_quality(ticker="XYZ", entry_index=1, horizon=2, rank_maps=maps) == (25, False)
    assert _future_quality(ticker="XYZ", entry_index=1, horizon=3, rank_maps=maps) == (4, False)


def test_future_quality_terminal_observation_is_excluded() -> None:
    maps = {0: {"XYZ": 80}, 1: {"XYZ": 5}}
    assert _future_quality(ticker="XYZ", entry_index=1, horizon=1, rank_maps=maps) == (None, None)


def test_contract_hash_is_frozen() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    path = verify_quality_supply_contract(repo_root)
    assert path.name == "decision_v3_quality_supply_diagnosis_v1.json"
