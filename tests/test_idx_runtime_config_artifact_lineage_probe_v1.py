from research.idx_runtime_config_artifact_lineage_probe_v1 import run_probe


def test_current_runtime_still_omits_config_runner_identity_from_orchestration_artifacts():
    result = run_probe()

    assert result["runtime_head"] == "402fca4b27e91cf8c82d21ff1394ba2d6da73656"
    assert result["loader_fields_present"] is True
    assert result["prepared_execution_artifact_fields_absent"] is True
    assert result["orchestration_api_present"] is True
    assert result["writes_performed"] is False
