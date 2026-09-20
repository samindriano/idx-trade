from research.idx_malformed_latest_snapshot_recovery_probe_v1 import run_probe


def test_malformed_or_tampered_latest_snapshot_blocks_selection_without_recovery(
    tmp_path,
):
    result = run_probe(tmp_path)

    assert result["status"] == "LATEST_SNAPSHOT_FAILURE_NO_RECOVERY"
    assert result["both_cases_fail_closed"] is True
    assert result["latest_files_remain_after_failure"] is True
    assert result["previous_files_remain_after_failure"] is True
    assert result["previous_direct_load_remains_available"] is True
    assert result["quarantine_or_fallback_observed"] is False
    assert result["writes_performed"] == "synthetic temp snapshots only"
