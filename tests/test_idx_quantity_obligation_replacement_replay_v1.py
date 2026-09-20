from research.idx_quantity_obligation_replacement_replay_v1 import (
    run_replacement_scenario,
)


def test_sell_replacement_replay_preserves_pair_and_reversal_lineage():
    result = run_replacement_scenario()

    assert result["first_partial"]["positions"] == [("AAA", 4_000)]
    assert result["first_partial"]["sell_remaining"] == 4_000
    assert result["first_partial"]["buy_status"] == "BLOCKED"
    assert result["first_partial"]["reload_hash_equal"] is True
    assert result["after_retry"]["positions"] == [("AAA", 3_000)]
    assert result["after_retry"]["sell_remaining_before_cancel"] == 3_000
    assert result["after_reversal"]["positions"] == [("AAA", 3_000)]
    assert result["after_reversal"]["sell_relinquished"] == 3_000
    assert result["after_reversal"]["buy_relinquished"] == 5_000
    assert result["after_reversal"]["sell_status"] == "CANCELED"
    assert result["after_reversal"]["buy_status"] == "CANCELED"
    assert result["after_reversal"]["duplicate_cancel_idempotent"] is True


def test_replacement_event_log_retains_block_and_cancel_events():
    result = run_replacement_scenario()
    assert result["after_reversal"]["event_ids"] == [
        "BUY-BLOCK-1",
        "BUY-BLOCK-2",
        "BUY-CANCEL-1",
        "SELL-CANCEL-1",
        "SELL-FILL-1",
        "SELL-FILL-2",
    ]
