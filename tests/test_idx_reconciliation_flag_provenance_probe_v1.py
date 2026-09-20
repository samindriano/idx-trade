from research.idx_reconciliation_flag_provenance_probe_v1 import run_probe


def test_pinned_runtime_reconciliation_flag_is_a_prior_gate_not_a_produced_mismatch():
    result = run_probe()

    assert result["runtime_head"] == "402fca4b27e91cf8c82d21ff1394ba2d6da73656"
    assert result["constant_true_assignments"] == []
    assert result["execution_writes_false_state"] is True
    assert result["state_default_false"] is True
    assert result["execution_consumes_prior_true_gate"] is True
    assert result["decision_consumes_prior_true_gate"] is True
    assert result["loader_rehydrates_serialized_bit"] is True
    assert result["mismatch_detector_marker"] is False
    assert result["writes_performed"] is False
