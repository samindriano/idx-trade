"""Read-only audit of Decision-to-state exposure/cash cause preservation."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any


RUNTIME_ROOT = Path(
    r"C:\Users\Sam\OneDrive\Documents\Project\idx-trade-runtime\forward-e2e-operational"
).resolve()
EXPECTED_RUNTIME_HEAD = "402fca4b27e91cf8c82d21ff1394ba2d6da73656"
RUNTIME_FILES = (
    Path("src/idx_trade/decision_v2_minimal.py"),
    Path("src/idx_trade/forward_dividend_runtime_v1_1.py"),
    Path("src/idx_trade/e2e_paper_orchestration_v1.py"),
    Path("src/idx_trade/v4_x1_execution_v1_contract.py"),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=RUNTIME_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _class_fields(tree: ast.AST, class_name: str) -> list[str]:
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        fields: list[str] = []
        for child in node.body:
            if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                fields.append(child.target.id)
        return fields
    raise AssertionError(f"CLASS_NOT_FOUND:{class_name}")


def _function_source(tree: ast.AST, source: str, function_name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            segment = ast.get_source_segment(source, node)
            if segment is None:
                raise AssertionError(f"FUNCTION_SOURCE_NOT_FOUND:{function_name}")
            return segment
    raise AssertionError(f"FUNCTION_NOT_FOUND:{function_name}")


def _canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def run_probe() -> dict[str, Any]:
    runtime_head = _head()
    if runtime_head != EXPECTED_RUNTIME_HEAD:
        raise RuntimeError("PINNED_RUNTIME_HEAD_CHANGED")

    sources: dict[str, str] = {}
    trees: dict[str, ast.AST] = {}
    source_sha256: dict[str, str] = {}
    for relative in RUNTIME_FILES:
        path = RUNTIME_ROOT / relative
        key = relative.as_posix()
        text = path.read_text(encoding="utf-8")
        sources[key] = text
        trees[key] = ast.parse(text, filename=str(path))
        source_sha256[key] = _sha256(path)

    decision_tree = trees["src/idx_trade/decision_v2_minimal.py"]
    runtime_tree = trees["src/idx_trade/forward_dividend_runtime_v1_1.py"]
    orchestration_tree = trees["src/idx_trade/e2e_paper_orchestration_v1.py"]
    contract_tree = trees["src/idx_trade/v4_x1_execution_v1_contract.py"]
    decision_source = sources["src/idx_trade/decision_v2_minimal.py"]
    runtime_source = sources["src/idx_trade/forward_dividend_runtime_v1_1.py"]
    orchestration_source = sources["src/idx_trade/e2e_paper_orchestration_v1.py"]

    decision_fields = _class_fields(decision_tree, "DecisionV2Plan")
    state_fields = _class_fields(contract_tree, "PaperPortfolioState")
    result_fields = _class_fields(contract_tree, "ExecutionResult")
    state_payload_source = _function_source(
        orchestration_tree, orchestration_source, "_state_payload"
    )
    decision_payload_source = _function_source(
        orchestration_tree, orchestration_source, "_decision_payload"
    )
    shadow_source = _function_source(
        runtime_tree, runtime_source, "reconstruct_decision_shadow_state"
    )

    decision_capacity_states = [
        "FULL",
        "UNFILLED_NO_QUALIFIED_CHALLENGER",
    ]
    state_cause_fields = {
        "capacity_state",
        "unfilled_slots",
        "cash_reason",
        "open_availability",
        "risk_hold_reason",
        "fill_status_history",
    }
    omitted_state_cause_fields = sorted(state_cause_fields - set(state_fields))

    # These are two distinct upstream histories represented by the same
    # persisted paper-state shape.  The history annotations intentionally stay
    # outside the state payload to test whether the state can distinguish them.
    common_state_payload = {
        "as_of_session_date": "2026-09-01",
        "cash_idr": 20_000_000.0,
        "positions": [{"ticker": "AAA", "shares": 5_000}],
        "pending_buys": [],
        "pending_sells": [],
        "reconciliation_required": False,
        "source": "EXECUTABLE_PAPER_V1",
    }
    histories = {
        "NO_QUALIFIED_CHALLENGER": {
            "unfilled_slots": 9,
            "capacity_state": "UNFILLED_NO_QUALIFIED_CHALLENGER",
        },
        "EXECUTION_CAPACITY_LIMITED": {
            "fill_status": "REFERENCE_DAY_CAPACITY_ZERO_PENDING",
            "unfilled_shares": 5_000,
        },
    }
    state_hashes = {
        name: _canonical_hash(common_state_payload)
        for name in histories
    }

    result = {
        "status": "EXPOSURE_CASH_STATE_TAXONOMY_GAP",
        "runtime_head": runtime_head,
        "source_sha256": source_sha256,
        "decision_plan_fields": decision_fields,
        "decision_capacity_states": decision_capacity_states,
        "decision_artifact_retains_capacity_fields": all(
            marker in decision_payload_source
            for marker in ("unfilled_slots", "capacity_state")
        ),
        "paper_state_fields": state_fields,
        "execution_result_fields": result_fields,
        "omitted_state_cause_fields": omitted_state_cause_fields,
        "state_payload_omits_cause_fields": all(
            field not in state_payload_source for field in omitted_state_cause_fields
        ),
        "shadow_reconstruction_is_position_pending_only": all(
            marker in shadow_source
            for marker in (
                "shadow = set(positions)",
                "shadow.difference_update(pending_sells)",
                "shadow.update(pending_buys)",
            )
        ) and all(
            field not in shadow_source
            for field in ("capacity_state", "unfilled_slots", "fill_status")
        ),
        "same_state_hash_for_distinct_upstream_histories": (
            len(set(state_hashes.values())) == 1
        ),
        "writes_performed": False,
    }
    if decision_capacity_states != [
        "FULL",
        "UNFILLED_NO_QUALIFIED_CHALLENGER",
    ]:
        raise AssertionError("DECISION_CAPACITY_STATE_CONTRACT_CHANGED")
    if not result["decision_artifact_retains_capacity_fields"]:
        raise AssertionError("DECISION_CAPACITY_FIELDS_NOT_SERIALIZED")
    if not result["state_payload_omits_cause_fields"]:
        raise AssertionError("STATE_CAUSE_FIELD_UNEXPECTEDLY_PRESENT")
    if not result["shadow_reconstruction_is_position_pending_only"]:
        raise AssertionError("SHADOW_RECONSTRUCTION_CONTRACT_CHANGED")
    if not result["same_state_hash_for_distinct_upstream_histories"]:
        raise AssertionError("SYNTHETIC_STATE_HASHES_SHOULD_MATCH")
    return result


if __name__ == "__main__":
    import json

    print(json.dumps(run_probe(), indent=2, sort_keys=True))
