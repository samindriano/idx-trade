"""Read-only provenance audit for the pinned runtime reconciliation flag.

This probe deliberately inspects source text/AST only.  It does not import or
execute the live runtime and does not write to the runtime checkout.
"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import subprocess
from typing import Any


RUNTIME_ROOT = Path(
    r"C:\Users\Sam\OneDrive\Documents\Project\idx-trade-runtime\forward-e2e-operational"
).resolve()
EXPECTED_RUNTIME_HEAD = "402fca4b27e91cf8c82d21ff1394ba2d6da73656"
RUNTIME_FILES = (
    Path("src/idx_trade/v4_x1_execution_v1_contract.py"),
    Path("src/idx_trade/v4_x1_execution_v1.py"),
    Path("src/idx_trade/v4_x1_execution_v1_decision_v2_adapter.py"),
    Path("src/idx_trade/forward_dividend_runtime_v1_1.py"),
    Path("src/idx_trade/e2e_paper_orchestration_v1.py"),
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


def _constant_bool(node: ast.AST) -> bool | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return node.value
    return None


def _keyword_assignments(tree: ast.AST) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg != "reconciliation_required":
                continue
            rows.append(
                {
                    "line": node.lineno,
                    "value": _constant_bool(keyword.value),
                    "value_kind": type(keyword.value).__name__,
                }
            )
    return rows


def run_probe() -> dict[str, Any]:
    runtime_head = _head()
    if runtime_head != EXPECTED_RUNTIME_HEAD:
        raise RuntimeError("PINNED_RUNTIME_HEAD_CHANGED")

    parsed: dict[str, ast.AST] = {}
    source: dict[str, str] = {}
    source_sha256: dict[str, str] = {}
    for relative in RUNTIME_FILES:
        path = RUNTIME_ROOT / relative
        text = path.read_text(encoding="utf-8")
        key = relative.as_posix()
        source[key] = text
        source_sha256[key] = _sha256(path)
        parsed[key] = ast.parse(text, filename=str(path))

    assignments = {
        name: _keyword_assignments(tree)
        for name, tree in parsed.items()
    }
    constant_true_assignments = [
        {"file": name, **row}
        for name, rows in assignments.items()
        for row in rows
        if row["value"] is True
    ]
    execution_source = source["src/idx_trade/v4_x1_execution_v1.py"]
    contract_source = source["src/idx_trade/v4_x1_execution_v1_contract.py"]
    decision_source = source[
        "src/idx_trade/v4_x1_execution_v1_decision_v2_adapter.py"
    ]
    runtime_loader_source = source[
        "src/idx_trade/forward_dividend_runtime_v1_1.py"
    ]

    result = {
        "status": "RECONCILIATION_FLAG_PROVENANCE_GAP",
        "runtime_head": runtime_head,
        "source_sha256": source_sha256,
        "constant_true_assignments": constant_true_assignments,
        "execution_writes_false_state": (
            "reconciliation_required=False" in execution_source
            and execution_source.count("reconciliation_required=False") >= 2
        ),
        "state_default_false": (
            "reconciliation_required: bool = False" in contract_source
        ),
        "execution_consumes_prior_true_gate": (
            "if paper_state.reconciliation_required:" in execution_source
            and "EXECUTION_V1_PRIOR_RECONCILIATION_REQUIRED" in execution_source
        ),
        "decision_consumes_prior_true_gate": (
            "if paper_state.reconciliation_required:" in decision_source
            and "EXECUTION_V1_PRIOR_RECONCILIATION_REQUIRED" in decision_source
        ),
        "loader_rehydrates_serialized_bit": (
            "reconciliation_required=bool(value.get(\"reconciliation_required\"))"
            in runtime_loader_source
        ),
        "mismatch_detector_marker": any(
            marker in execution_source
            for marker in (
                "reconciliation_required=True",
                "reconciliation_required = True",
            )
        ),
        "writes_performed": False,
    }
    if result["constant_true_assignments"]:
        raise AssertionError("UNEXPECTED_RECONCILIATION_TRUE_ASSIGNMENT")
    if not all(
        result[key]
        for key in (
            "execution_writes_false_state",
            "state_default_false",
            "execution_consumes_prior_true_gate",
            "decision_consumes_prior_true_gate",
            "loader_rehydrates_serialized_bit",
        )
    ):
        raise AssertionError("RECONCILIATION_FLAG_PROVENANCE_UNEXPECTED")
    return result


if __name__ == "__main__":
    import json

    print(json.dumps(run_probe(), indent=2, sort_keys=True))
