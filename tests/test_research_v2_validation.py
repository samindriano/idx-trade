from __future__ import annotations

import pandas as pd

from idx_trade.research_v2_models import (
    HGB_XS,
    HGB_XS_MARKET,
    LOGISTIC_XS,
    PAIRWISE_LOGISTIC_XS,
    V1_HGB_CONTROL,
)
from idx_trade.research_v2_validation import (
    RANKING_V2_FOLDS,
    assert_ranking_v2_fold_contract,
    candidate_aggregate,
    select_v2_champion,
)


def _metrics() -> pd.DataFrame:
    configs = {
        V1_HGB_CONTROL: ([0.004] * 6, [0.505] * 6, [0.006] * 6),
        LOGISTIC_XS: ([0.010] * 6, [0.520] * 6, [0.020] * 6),
        HGB_XS: ([0.012, 0.012, 0.012, 0.012, 0.012, 0.012], [0.525] * 6, [0.024] * 6),
        HGB_XS_MARKET: ([0.014, 0.014, 0.014, 0.014, 0.006, 0.006], [0.530] * 6, [0.030] * 6),
        PAIRWISE_LOGISTIC_XS: ([0.009] * 6, [0.515] * 6, [0.018] * 6),
    }
    rows: list[dict[str, object]] = []
    for candidate, (pr, roc, spread) in configs.items():
        for i, fold in enumerate(RANKING_V2_FOLDS):
            rows.append(
                {
                    "candidate": candidate,
                    "fold": fold.name,
                    "pr_auc_delta_vs_base": pr[i],
                    "roc_auc": roc[i],
                    "q5_minus_q1": spread[i],
                }
            )
    return pd.DataFrame(rows)


def test_ranking_v2_fold_contract_is_fixed_and_valid() -> None:
    assert_ranking_v2_fold_contract()
    assert len(RANKING_V2_FOLDS) == 6
    assert RANKING_V2_FOLDS[0].train_end == 504
    assert RANKING_V2_FOLDS[-1].validation_end == 1224


def test_candidate_aggregate_never_marks_v1_control_eligible() -> None:
    aggregate = candidate_aggregate(_metrics())
    control = aggregate[aggregate["candidate"].eq(V1_HGB_CONTROL)].iloc[0]
    assert not bool(control["eligible"])
    assert aggregate[aggregate["candidate"].eq(LOGISTIC_XS)]["eligible"].iloc[0]


def test_champion_rule_uses_q25_when_medians_are_within_tolerance() -> None:
    decision, champion, aggregate = select_v2_champion(_metrics())
    assert decision == "RANKING_V2_HISTORICAL_CHAMPION_SELECTED"
    # HGB_XS_MARKET has the highest median PR delta, but HGB_XS is within the
    # frozen 0.002 tolerance and has the stronger lower-quartile PR delta.
    assert champion == HGB_XS
    assert set(aggregate[aggregate["eligible"]]["candidate"]) == {
        LOGISTIC_XS,
        HGB_XS,
        HGB_XS_MARKET,
        PAIRWISE_LOGISTIC_XS,
    }


def test_no_candidate_is_forced_when_stability_gates_fail() -> None:
    frame = _metrics()
    mask = frame["candidate"].ne(V1_HGB_CONTROL)
    frame.loc[mask, "pr_auc_delta_vs_base"] = -0.001
    frame.loc[mask, "roc_auc"] = 0.49
    frame.loc[mask, "q5_minus_q1"] = -0.001
    decision, champion, _aggregate = select_v2_champion(frame)
    assert decision == "RANKING_V2_NO_CHAMPION"
    assert champion is None
