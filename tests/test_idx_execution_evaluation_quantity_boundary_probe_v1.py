from research.idx_execution_evaluation_quantity_boundary_probe_v1 import run_probe


def test_prospective_gate_does_not_validate_planned_vs_filled_execution_quantity():
    result = run_probe()

    assert result["status"] == "EXECUTION_EVALUATION_QUANTITY_BOUNDARY_NOT_CHECKED"
    assert result["accepted_execution_columns"] == [
        "session_date",
        "gross_buy_notional",
        "gross_sell_notional",
        "nav_prev",
    ]
    assert result["quantity_fields_absent_from_execution_validator"] is True
    assert result["quantity_fields_absent_from_state_guard"] is True
    assert result["accepted_rows_same_without_plan_quantity"] is True
    assert result["planned_turnover"] == 0.1
    assert result["filled_turnover"] == 0.05
    assert result["turnover_understates_planned_fraction"] is True
    assert result["partial_obligation_check_present"] is False
    assert result["writes_performed"] is False
