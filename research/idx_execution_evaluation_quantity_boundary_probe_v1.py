"""Audit the prospective gate's execution quantity boundary, read-only."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = REPO_ROOT / "src/idx_trade/prospective_evaluation_gate_v1.py"
EVALUATOR_PATH = REPO_ROOT / "src/idx_trade/prospective_evaluation_v1.py"
EXPECTED_SOURCE_SHA256 = {
    "prospective_evaluation_gate_v1.py":
    "41a5ca7987b529675bc1ef1858b50b763467d3d5651f92178e4d74275f09052a",
    "prospective_evaluation_v1.py":
    "98658814531367cf779af71698c2db77ae454900c1f86b84dddf1db0ca834108",
}
EXECUTION_COLUMNS = (
    "session_date",
    "gross_buy_notional",
    "gross_sell_notional",
    "nav_prev",
)
QUANTITY_FIELDS = (
    "planned_shares",
    "filled_shares",
    "remaining_shares",
    "target_positions",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _function_source(tree: ast.AST, source: str, function_name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            segment = ast.get_source_segment(source, node)
            if segment is None:
                raise AssertionError(f"FUNCTION_SOURCE_NOT_FOUND:{function_name}")
            return segment
    raise AssertionError(f"FUNCTION_NOT_FOUND:{function_name}")


def _canonical_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def run_probe() -> dict[str, Any]:
    gate_source = GATE_PATH.read_text(encoding="utf-8")
    evaluator_source = EVALUATOR_PATH.read_text(encoding="utf-8")
    source_sha256 = {
        GATE_PATH.name: _sha256(GATE_PATH),
        EVALUATOR_PATH.name: _sha256(EVALUATOR_PATH),
    }
    if source_sha256 != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("PINNED_EVALUATION_SOURCES_CHANGED")
    gate_tree = ast.parse(gate_source, filename=str(GATE_PATH))
    evaluator_tree = ast.parse(evaluator_source, filename=str(EVALUATOR_PATH))
    validate_source = _function_source(
        gate_tree, gate_source, "_validate_execution_bundle"
    )
    reconstruct_source = _function_source(
        gate_tree, gate_source, "_state_reconstructable"
    )
    turnover_source = _function_source(
        evaluator_tree, evaluator_source, "evaluate_turnover"
    )

    # A partial BUY with a 5m plan and 2.5m fill can be projected into the
    # accepted aggregate execution schema as a 2.5m gross buy.  A second
    # history with no planned-vs-filled relation produces the identical schema
    # row, so the validator has no quantity evidence to compare.
    planned_buy = 5_000_000.0
    filled_buy = 2_500_000.0
    nav_prev = 50_000_000.0
    accepted_row = {
        "session_date": "2026-09-01",
        "gross_buy_notional": filled_buy,
        "gross_sell_notional": 0.0,
        "nav_prev": nav_prev,
    }
    accepted_row_without_plan = dict(accepted_row)
    filled_turnover = filled_buy / nav_prev
    planned_turnover = planned_buy / nav_prev

    result = {
        "status": "EXECUTION_EVALUATION_QUANTITY_BOUNDARY_NOT_CHECKED",
        "source_sha256": source_sha256,
        "accepted_execution_columns": list(EXECUTION_COLUMNS),
        "validator_selects_only_accepted_columns": all(
            f'"{column}"' in validate_source for column in EXECUTION_COLUMNS
        ),
        "quantity_fields_absent_from_execution_validator": all(
            field not in validate_source for field in QUANTITY_FIELDS
        ),
        "quantity_fields_absent_from_state_guard": all(
            field not in reconstruct_source for field in QUANTITY_FIELDS
        ),
        "state_guard_checks_only_aggregate_numeric_inputs": all(
            marker in reconstruct_source
            for marker in (
                '"gross_buy_notional", "gross_sell_notional", "nav_prev"',
                "pending_due_to_unavailable_open",
            )
        ),
        "turnover_uses_filled_aggregate_column": "gross_buy_notional" in turnover_source,
        "accepted_rows_same_without_plan_quantity": (
            accepted_row == accepted_row_without_plan
        ),
        "planned_turnover": planned_turnover,
        "filled_turnover": filled_turnover,
        "turnover_understates_planned_fraction": planned_turnover > filled_turnover,
        "partial_obligation_check_present": any(
            marker in validate_source + reconstruct_source
            for marker in (
                "planned_shares",
                "filled_shares",
                "remaining_shares",
                "target_positions",
            )
        ),
        "writes_performed": False,
    }
    if not result["validator_selects_only_accepted_columns"]:
        raise AssertionError("EXECUTION_SCHEMA_MARKERS_CHANGED")
    if not result["quantity_fields_absent_from_execution_validator"]:
        raise AssertionError("QUANTITY_FIELD_UNEXPECTEDLY_VALIDATED")
    if not result["quantity_fields_absent_from_state_guard"]:
        raise AssertionError("QUANTITY_FIELD_UNEXPECTEDLY_STATE_GUARDED")
    if not result["accepted_rows_same_without_plan_quantity"]:
        raise AssertionError("SYNTHETIC_ACCEPTED_ROWS_SHOULD_MATCH")
    if not result["turnover_understates_planned_fraction"]:
        raise AssertionError("SYNTHETIC_TURNOVER_GAP_MISSING")
    if result["partial_obligation_check_present"]:
        raise AssertionError("UNEXPECTED_PARTIAL_OBLIGATION_CHECK")
    return result


if __name__ == "__main__":
    import json

    print(json.dumps(run_probe(), indent=2, sort_keys=True))
