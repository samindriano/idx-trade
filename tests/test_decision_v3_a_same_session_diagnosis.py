from __future__ import annotations

from pathlib import Path

import pandas as pd

from idx_trade.decision_v3_a_same_session_diagnosis import (
    EXPECTED_CONTRACT_CANONICAL_SHA256,
    _build_session_summary,
    _build_stratified,
    _paired_session_indices,
    verify_same_session_contract,
)


def _row(
    session: int,
    cls: str,
    *,
    next_severe: bool | None,
    completed: bool = True,
    eventual_severe: bool | None = False,
    current_rank: int = 5,
    previous_rank: int = 12,
    top10_run: int = 1,
    top20_run: int = 3,
    last3_top20: int = 3,
) -> dict[str, object]:
    return {
        "ticker": f"{cls}_{session}_{current_rank}",
        "entry_index": session,
        "entry_date": f"2026-01-{session:02d}",
        "entry_class": cls,
        "current_rank": current_rank,
        "previous_rank": previous_rank,
        "rank_delta_current_minus_previous": current_rank - previous_rank,
        "rank_t_minus_2": 15,
        "rank_t_minus_3": 18,
        "top10_run_including_entry": top10_run,
        "top20_run_including_entry": top20_run,
        "last3_top10_count": 1,
        "last3_top20_count": last3_top20,
        "soft_rank_gap": 7 if cls == "A_SOFT" else None,
        "duration_sessions": 3,
        "one_session_holding": False,
        "completed": completed,
        "right_censored": not completed,
        "eventual_severe_exit": eventual_severe,
        "next_session_observable": next_severe is not None,
        "next_session_severe_exit": next_severe,
        "current_rank_bucket": "4-6",
        "previous_rank_bucket": "11-20",
        "top10_run_bucket": "1",
        "top20_run_bucket": ">=3",
        "severe_exit_count": 2,
        "confirmed_mild_exit_count": 0,
        "universe_exit_count": 0,
        "mandatory_exit_count": 2,
        "top10_overlap": 4,
        "top20_overlap": 10,
        "previous_top10_to_gt50_or_absent_count": 2,
    }


def test_contract_hash_is_frozen() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    path = verify_same_session_contract(repo_root)
    assert path.is_file()
    assert len(EXPECTED_CONTRACT_CANONICAL_SHA256) == 64


def test_paired_session_indices_require_both_classes() -> None:
    frame = pd.DataFrame(
        [
            _row(1, "A_SOFT", next_severe=False),
            _row(1, "A_VACANCY", next_severe=True),
            _row(2, "A_SOFT", next_severe=False),
            _row(3, "A_VACANCY", next_severe=True),
            _row(4, "A_SOFT", next_severe=False),
            _row(4, "A_VACANCY", next_severe=False),
        ]
    )
    assert _paired_session_indices(frame) == [1, 4]


def test_session_summary_is_same_session_and_censor_aware() -> None:
    paired = pd.DataFrame(
        [
            _row(1, "A_SOFT", next_severe=False, eventual_severe=False),
            _row(1, "A_VACANCY", next_severe=True, eventual_severe=True),
            _row(
                2,
                "A_SOFT",
                next_severe=None,
                completed=False,
                eventual_severe=None,
                current_rank=6,
            ),
            _row(
                2,
                "A_VACANCY",
                next_severe=None,
                completed=False,
                eventual_severe=None,
                current_rank=4,
            ),
        ]
    )
    result = _build_session_summary(paired)
    first = result.loc[result["session_index"].eq(1)].iloc[0]
    second = result.loc[result["session_index"].eq(2)].iloc[0]

    assert first["a_soft_next_severe_rate"] == 0.0
    assert first["a_vacancy_next_severe_rate"] == 1.0
    assert first["soft_minus_vacancy_next_severe_gap"] == -1.0
    assert first["soft_minus_vacancy_eventual_severe_gap"] == -1.0
    assert pd.isna(second["soft_minus_vacancy_next_severe_gap"])
    assert pd.isna(second["soft_minus_vacancy_eventual_severe_gap"])


def test_stratified_output_keeps_fixed_bins_without_policy_simulation() -> None:
    paired = pd.DataFrame(
        [
            _row(1, "A_SOFT", next_severe=False),
            _row(1, "A_VACANCY", next_severe=True),
        ]
    )
    result = _build_stratified(paired)
    current = result.loc[
        result["dimension"].eq("current_rank") & result["stratum"].eq("4-6")
    ].iloc[0]
    assert current["a_soft_entries"] == 1
    assert current["a_vacancy_entries"] == 1
    assert current["soft_minus_vacancy_next_severe_gap"] == -1.0
    assert set(result["dimension"]) == {
        "current_rank",
        "previous_rank",
        "top10_run_including_entry",
        "top20_run_including_entry",
        "last3_top20_count",
    }
