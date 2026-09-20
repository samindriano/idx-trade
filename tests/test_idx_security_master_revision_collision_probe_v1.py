from research.idx_security_master_revision_collision_probe_v1 import run_probe


def test_same_security_key_revision_is_order_sensitive_at_master_boundary():
    result = run_probe()

    assert result["runtime_head"] == "402fca4b27e91cf8c82d21ff1394ba2d6da73656"
    assert result["input_rows"] == 2
    assert result["a_then_b"] == {
        "company_name": "History B",
        "listed_to": "2025-12-31",
        "source": "ARCHIVE_B",
    }
    assert result["b_then_a"] == {
        "company_name": "History A",
        "listed_to": "2024-12-31",
        "source": "ARCHIVE_A",
    }
    assert result["order_sensitive"] is True
    assert result["writes_performed"] is False
