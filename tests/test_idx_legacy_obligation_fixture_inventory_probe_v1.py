from research.idx_legacy_obligation_fixture_inventory_probe_v1 import run_probe


def test_pinned_runtime_has_no_retained_fill_vector_fixtures_for_migration():
    result = run_probe()

    assert result["runtime_head"] == "402fca4b27e91cf8c82d21ff1394ba2d6da73656"
    assert result["runtime_worktree_clean"] is True
    assert result["retained_fill_vector_files"] == []
    assert all(result["known_runtime_output_dirs"].values()) is False
    assert result["writes_performed"] is False
