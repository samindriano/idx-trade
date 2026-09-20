from research.idx_universe_identity_collision_probe_v1 import run_probe


def test_pinned_runtime_universe_does_not_fail_closed_on_alias_collision():
    result = run_probe()

    assert result["runtime_head"] == "402fca4b27e91cf8c82d21ff1394ba2d6da73656"
    assert result["synthetic_input_keys"] == ["ABCD", "ABCD.JK"]
    assert result["normalized_identity"] == "ABCD"
    assert result["output_rows"] == 2
    assert result["unique_tickers"] == 1
    assert result["selected_rows"] == 2
    assert result["duplicate_ticker_key"] is True
    assert result["selected_rank_values"] == [1, 2]
    assert result["downstream_decision_guard"] == "DECISION_V2_V4_X1_DUPLICATE_TICKER"
    assert result["writes_performed"] is False
