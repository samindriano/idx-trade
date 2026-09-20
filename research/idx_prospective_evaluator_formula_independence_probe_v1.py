"""Audit whether the prospective gate independently recomputes its formulas."""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
EVALUATOR_PATH = REPO_ROOT / "src/idx_trade/prospective_evaluation_v1.py"
GATE_PATH = REPO_ROOT / "src/idx_trade/prospective_evaluation_gate_v1.py"
EXPECTED_SOURCE_SHA256 = {
    "prospective_evaluation_v1.py":
    "98658814531367cf779af71698c2db77ae454900c1f86b84dddf1db0ca834108",
    "prospective_evaluation_gate_v1.py":
    "41a5ca7987b529675bc1ef1858b50b763467d3d5651f92178e4d74275f09052a",
}
METRIC_FUNCTIONS = (
    "evaluate_alpha_metrics",
    "evaluate_portfolio_metrics",
    "evaluate_turnover",
    "evaluate_pending_orders",
    "evaluate_benchmark",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _function_names(tree: ast.AST) -> set[str]:
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _function_source(tree: ast.AST, source: str, function_name: str) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            segment = ast.get_source_segment(source, node)
            if segment is None:
                raise AssertionError(f"FUNCTION_SOURCE_NOT_FOUND:{function_name}")
            return segment
    raise AssertionError(f"FUNCTION_NOT_FOUND:{function_name}")


def _child_shared_function_objects() -> dict[str, bool]:
    code = (
        "import json\n"
        "from idx_trade import prospective_evaluation_gate_v1 as gate\n"
        "from idx_trade import prospective_evaluation_v1 as evaluator\n"
        "names = " + repr(METRIC_FUNCTIONS) + "\n"
        "print(json.dumps({name: getattr(gate, name) is getattr(evaluator, name) for name in names}, sort_keys=True))\n"
    )
    env = os.environ.copy()
    src_root = str(REPO_ROOT / "src")
    env["PYTHONPATH"] = src_root + os.pathsep + env.get("PYTHONPATH", "")
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def run_probe() -> dict[str, Any]:
    evaluator_source = EVALUATOR_PATH.read_text(encoding="utf-8")
    gate_source = GATE_PATH.read_text(encoding="utf-8")
    evaluator_tree = ast.parse(evaluator_source, filename=str(EVALUATOR_PATH))
    gate_tree = ast.parse(gate_source, filename=str(GATE_PATH))
    source_sha256 = {
        EVALUATOR_PATH.name: _sha256(EVALUATOR_PATH),
        GATE_PATH.name: _sha256(GATE_PATH),
    }
    if source_sha256 != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("PINNED_EVALUATION_SOURCES_CHANGED")

    gate_function_names = _function_names(gate_tree)
    evaluator_function_names = _function_names(evaluator_tree)
    shared_function_objects = _child_shared_function_objects()
    gate_eval_source = _function_source(
        gate_tree, gate_source, "_evaluate_loaded_bundle"
    )
    development_eval_source = _function_source(
        evaluator_tree, evaluator_source, "evaluate_prospective_v1"
    )
    result = {
        "status": "PROSPECTIVE_FORMULA_INDEPENDENCE_NOT_ESTABLISHED",
        "source_sha256": source_sha256,
        "metric_functions": list(METRIC_FUNCTIONS),
        "shared_function_objects": shared_function_objects,
        "all_gate_metric_functions_alias_evaluator": all(
            shared_function_objects.values()
        ),
        "gate_defines_independent_metric_functions": bool(
            set(METRIC_FUNCTIONS) & gate_function_names
        ),
        "evaluator_defines_metric_functions": all(
            name in evaluator_function_names for name in METRIC_FUNCTIONS
        ),
        "gate_calls_frozen_metric_engine": all(
            f"{name}(" in gate_eval_source for name in METRIC_FUNCTIONS
        ),
        "development_path_calls_same_metric_engine": all(
            f"{name}(" in development_eval_source for name in METRIC_FUNCTIONS[:2]
        ),
        "writes_performed": False,
    }
    if not result["all_gate_metric_functions_alias_evaluator"]:
        raise AssertionError("GATE_METRIC_BINDINGS_UNEXPECTEDLY_INDEPENDENT")
    if result["gate_defines_independent_metric_functions"]:
        raise AssertionError("GATE_METRIC_IMPLEMENTATION_FOUND")
    if not result["evaluator_defines_metric_functions"]:
        raise AssertionError("EVALUATOR_METRIC_IMPLEMENTATION_MISSING")
    if not result["gate_calls_frozen_metric_engine"]:
        raise AssertionError("GATE_METRIC_CALLS_NOT_FOUND")
    if not result["development_path_calls_same_metric_engine"]:
        raise AssertionError("DEVELOPMENT_METRIC_CALLS_NOT_FOUND")
    return result


if __name__ == "__main__":
    import json

    print(json.dumps(run_probe(), indent=2, sort_keys=True))
