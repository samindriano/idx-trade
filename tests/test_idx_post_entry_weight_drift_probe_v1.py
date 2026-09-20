from research.idx_post_entry_weight_drift_probe_v1 import run_probe


def test_entry_cap_does_not_bound_post_entry_mark_to_market_weight():
    result = run_probe()

    assert result["runtime_head"] == "402fca4b27e91cf8c82d21ff1394ba2d6da73656"
    assert result["max_entry_weight"] == 0.15
    assert result["synthetic_winner_weight"] == 0.25
    assert result["winner_exceeds_entry_cap"] is True
    assert result["strategic_cash_overlay"] is False
    assert result["paper_state_has_mark_price_or_weight"] is False
    assert result["hash_contains_mark_price_or_weight"] is False
    assert result["writes_performed"] is False
