from research.idx_security_master_revision_collision_probe_v1 import run_probe


def test_same_security_key_history_is_not_rejected_at_master_boundary():
    result = run_probe()

    assert result["runtime_head"] == "402fca4b27e91cf8c82d21ff1394ba2d6da73656"
    assert result["input_rows"] == 2
    assert result["output_rows"] == 1
    assert result["output_ticker"] == "ABCD"
    assert result["output_company_name"] == "ABCD Historical"
    assert result["output_listed_to"] == "2024-12-31"
    assert result["output_source"] == "IDX_DELISTED"
    assert result["writes_performed"] is False
