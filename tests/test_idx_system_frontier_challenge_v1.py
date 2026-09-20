from research.idx_system_frontier_challenge_v1 import run_challenge


def test_frontier_challenge_confirms_cross_component_false_green_boundaries():
    result = run_challenge()

    assert result["status"] == "FRONTIER_CHALLENGE_FALSE_GREEN_BOUNDARIES_CONFIRMED"
    assert all(result["gates"].values())
    assert result["systemic_interpretation"]["planned_shares"] == 5_000
    assert result["systemic_interpretation"]["first_fill_shares"] == 2_400
    assert result["systemic_interpretation"]["spec_remaining_shares"] == 2_600
    assert result["systemic_interpretation"]["evaluation_turnover_seen"] == 0.05
    assert result["systemic_interpretation"]["planned_turnover_reference"] == 0.1
    assert result["protected_outcomes_accessed"] is False
    assert result["production_or_canonical_mutation"] is False
    assert result["runtime_source_mutation"] is False
