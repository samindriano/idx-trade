from research.idx_exposure_cash_state_taxonomy_probe_v1 import run_probe


def test_decision_capacity_cause_is_not_in_the_restartable_paper_state_contract():
    result = run_probe()

    assert result["runtime_head"] == "402fca4b27e91cf8c82d21ff1394ba2d6da73656"
    assert result["decision_artifact_retains_capacity_fields"] is True
    assert result["omitted_state_cause_fields"] == [
        "capacity_state",
        "cash_reason",
        "fill_status_history",
        "open_availability",
        "risk_hold_reason",
        "unfilled_slots",
    ]
    assert result["state_payload_omits_cause_fields"] is True
    assert result["shadow_reconstruction_is_position_pending_only"] is True
    assert result["same_state_hash_for_distinct_upstream_histories"] is True
    assert result["writes_performed"] is False
