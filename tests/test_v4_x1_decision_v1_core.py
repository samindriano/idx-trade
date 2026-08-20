from decision_v1_helpers import *

def test_initial_empty_shadow_targets_top10(tmp_path, monkeypatch):
    frame = _scores()
    plan = plan_decision_v1(_verified_direct(frame), ShadowPortfolioState.empty())
    assert plan.target_positions == tuple(f"T{i:02d}" for i in range(1, 11))
    assert len(plan.buy_intents) == 10
    assert not plan.sell_intents
    assert all(x.reason == "FILL_VACANCY_TOP10" for x in plan.buy_intents)


def test_top10_incumbents_hold_with_no_churn(tmp_path, monkeypatch):
    plan = plan_decision_v1(_verified_direct(), _state(list(range(1, 11))))
    assert not plan.buy_intents
    assert not plan.sell_intents
    assert plan.target_positions == tuple(f"T{i:02d}" for i in range(1, 11))


def test_gap_four_does_not_replace(tmp_path, monkeypatch):
    holdings = [1,2,3,4,5,6,7,8,9,14]
    plan = plan_decision_v1(_verified_direct(), _state(holdings))
    assert not plan.buy_intents
    assert not plan.sell_intents
    assert "T14" in plan.target_positions and "T10" not in plan.target_positions


def test_gap_five_replaces_exactly(tmp_path, monkeypatch):
    holdings = [1,2,3,4,5,6,7,8,9,15]
    plan = plan_decision_v1(_verified_direct(), _state(holdings))
    assert [(x.ticker, x.reason) for x in plan.buy_intents] == [("T10", "RANK_GAP_REPLACEMENT")]
    assert [(x.ticker, x.reason) for x in plan.sell_intents] == [("T15", "RANK_GAP_REPLACEMENT")]


def test_rank20_retained_if_no_gap_trigger(tmp_path, monkeypatch):
    plan = plan_decision_v1(_verified_direct(), _state([1,2,3,4,5,6,7,8,20]))
    assert not any(x.ticker == "T20" and x.reason == "HARD_EXIT_RANK_GT20" for x in plan.sell_intents)


def test_rank21_mandatory_exit(tmp_path, monkeypatch):
    plan = plan_decision_v1(_verified_direct(), _state([1,2,3,4,5,6,7,8,9,21]))
    assert any(x.ticker == "T21" and x.reason == "HARD_EXIT_RANK_GT20" for x in plan.sell_intents)
    assert any(x.ticker == "T10" and x.reason == "MANDATORY_EXIT_REPLACEMENT" for x in plan.buy_intents)


def test_absent_holding_is_exit_only_after_verified_boundary(tmp_path, monkeypatch):
    state = ShadowPortfolioState("2026-08-20", ("ZZZZ", *[f"T{i:02d}" for i in range(1,10)]))
    plan = plan_decision_v1(_verified_direct(), state)
    assert any(x.ticker == "ZZZZ" and x.reason == "NO_LONGER_IN_V4_X1_DECISION_UNIVERSE" for x in plan.sell_intents)


def test_multiple_replacements_use_best_candidate_vs_worst_incumbent(tmp_path, monkeypatch):
    plan = plan_decision_v1(_verified_direct(), _state([1,4,5,8,11,12,13,14,16,19]))
    assert plan.buy_intents[0].ticker == "T02"
    sold = [x for x in plan.sell_intents if x.reason == "RANK_GAP_REPLACEMENT"]
    assert sold[0].ticker == "T19"


def test_shadow_type_is_mandatory(tmp_path, monkeypatch):
    with pytest.raises(DecisionV1Error, match="SHADOW_STATE_TYPE_REQUIRED"):
        plan_decision_v1(_verified_direct(), ["T01"])


def test_real_state_source_forbidden(tmp_path, monkeypatch):
    state = ShadowPortfolioState("2026-08-20", tuple(f"T{i:02d}" for i in range(1,11)), source="REAL_PORTFOLIO")
    with pytest.raises(DecisionV1Error, match="NON_SHADOW_STATE_FORBIDDEN"):
        plan_decision_v1(_verified_direct(), state)


def test_more_than_10_shadow_positions_fail_closed(tmp_path, monkeypatch):
    state = ShadowPortfolioState("2026-08-20", tuple(f"T{i:02d}" for i in range(1,12)))
    with pytest.raises(DecisionV1Error, match="SHADOW_OVER_TARGET"):
        plan_decision_v1(_verified_direct(), state)


def test_same_day_shadow_state_allowed(tmp_path, monkeypatch):
    state = ShadowPortfolioState("2026-08-21", tuple(f"T{i:02d}" for i in range(1,11)))
    plan = plan_decision_v1(_verified_direct(), state)
    assert not plan.buy_intents and not plan.sell_intents


def test_future_shadow_state_forbidden(tmp_path, monkeypatch):
    state = ShadowPortfolioState("2026-08-22", tuple(f"T{i:02d}" for i in range(1,11)))
    with pytest.raises(DecisionV1Error, match="SHADOW_STATE_FROM_FUTURE"):
        plan_decision_v1(_verified_direct(), state)


def test_plan_outputs_intents_not_fills(tmp_path, monkeypatch):
    plan = plan_decision_v1(_verified_direct(), _state([1,2,3,4,5,6,7,8,9,21]))
    assert all(x.side.endswith("_INTENT") for x in (*plan.buy_intents, *plan.sell_intents))
    assert plan.execution_reference == "OFFICIAL_OPEN_T_PLUS_1"


def test_permutation_of_score_rows_does_not_change_plan(tmp_path, monkeypatch):
    base = _scores()
    state = _state([1,4,5,8,11,12,13,14,16,19])
    expected = plan_decision_v1(_verified_direct(base), state)
    for seed in range(30):
        actual = plan_decision_v1(_verified_direct(base.sample(frac=1, random_state=seed).reset_index(drop=True)), state)
        assert actual.target_positions == expected.target_positions
        assert actual.buy_intents == expected.buy_intents
        assert actual.sell_intents == expected.sell_intents


def test_idempotence_after_intended_target_is_prior_shadow_state(tmp_path, monkeypatch):
    verified = _verified_direct()
    first = plan_decision_v1(verified, _state([1,4,5,8,11,12,13,14,16,19]))
    second = plan_decision_v1(verified, ShadowPortfolioState("2026-08-20", first.target_positions))
    assert not second.buy_intents
    assert not second.sell_intents
