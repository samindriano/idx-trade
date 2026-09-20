from research.idx_prospective_evaluator_formula_independence_probe_v1 import run_probe


def test_protected_gate_reuses_frozen_metric_engine_without_independent_formula_oracle():
    result = run_probe()

    assert result["status"] == "PROSPECTIVE_FORMULA_INDEPENDENCE_NOT_ESTABLISHED"
    assert result["all_gate_metric_functions_alias_evaluator"] is True
    assert result["gate_defines_independent_metric_functions"] is False
    assert result["evaluator_defines_metric_functions"] is True
    assert result["gate_calls_frozen_metric_engine"] is True
    assert result["development_path_calls_same_metric_engine"] is True
    assert result["writes_performed"] is False
