"""Synthetic read-only counterexample for the entry-only weight cap."""

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
CONFIG_FILES = (
    Path("config/v4_x1_sizing_v1.json"),
    Path("config/v4_x1_execution_v1.json"),
)
SOURCE_FILES = (
    Path("src/idx_trade/v4_x1_sizing_v1.py"),
    Path("src/idx_trade/v4_x1_execution_v1.py"),
    Path("src/idx_trade/v4_x1_execution_v1_contract.py"),
)


def _head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=RUNTIME_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


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


def run_probe() -> dict[str, Any]:
    runtime_head = _head()
    if runtime_head != EXPECTED_RUNTIME_HEAD:
        raise RuntimeError("PINNED_RUNTIME_HEAD_CHANGED")

    configs = {
        path.as_posix(): json.loads((RUNTIME_ROOT / path).read_text(encoding="utf-8"))
        for path in CONFIG_FILES
    }
    sources = {
        path.as_posix(): (RUNTIME_ROOT / path).read_text(encoding="utf-8")
        for path in SOURCE_FILES
    }
    contract_tree = ast.parse(
        sources["src/idx_trade/v4_x1_execution_v1_contract.py"]
    )
    hash_source = _function_source(
        contract_tree,
        sources["src/idx_trade/v4_x1_execution_v1_contract.py"],
        "paper_state_hash",
    )
    sizing_config = configs["config/v4_x1_sizing_v1.json"]
    execution_config = configs["config/v4_x1_execution_v1.json"]
    max_entry_weight = float(sizing_config["max_entry_weight_per_name"])

    # Ten equal 10%-of-entry positions; one winner triples while the rest stay
    # flat.  Selling two other names into cash does not reduce the winner's
    # mark-to-market weight because the cash remains in the NAV denominator.
    initial_name_value = 10_000_000.0
    winner_value = initial_name_value * 3.0
    other_value = initial_name_value * 9.0
    post_drift_nav = winner_value + other_value
    winner_weight = winner_value / post_drift_nav

    state_fields = {
        "as_of_session_date",
        "cash_idr",
        "positions",
        "pending_buys",
        "pending_sells",
        "reconciliation_required",
        "source",
    }
    result = {
        "status": "POST_ENTRY_WEIGHT_DRIFT_NOT_BOUNDED",
        "runtime_head": runtime_head,
        "config_sha256": {
            path: _sha256(RUNTIME_ROOT / Path(path))
            for path in configs
        },
        "max_entry_weight": max_entry_weight,
        "strategic_cash_overlay": execution_config["strategic_cash_overlay"],
        "post_entry_weight_drift_policy": execution_config[
            "post_entry_weight_drift_policy"
        ],
        "synthetic_initial_name_value_idr": initial_name_value,
        "synthetic_winner_multiple": 3.0,
        "synthetic_post_drift_nav_idr": post_drift_nav,
        "synthetic_winner_weight": winner_weight,
        "winner_exceeds_entry_cap": winner_weight > max_entry_weight,
        "paper_state_has_mark_price_or_weight": bool(
            state_fields & {"mark_price", "market_value", "weight"}
        ),
        "hash_contains_mark_price_or_weight": any(
            marker in hash_source
            for marker in ("mark_price", "market_value", "weight")
        ),
        "post_entry_rebalance_marker": any(
            marker in "\n".join(sources.values())
            for marker in (
                "post_entry_weight",
                "concentration_cap",
                "drawdown_trigger",
                "risk_overlay",
            )
        ),
        "writes_performed": False,
    }
    if max_entry_weight != 0.15:
        raise AssertionError("ENTRY_CAP_CONFIG_CHANGED")
    if not result["winner_exceeds_entry_cap"]:
        raise AssertionError("SYNTHETIC_DRIFT_DID_NOT_EXCEED_CAP")
    if result["paper_state_has_mark_price_or_weight"]:
        raise AssertionError("PAPER_STATE_UNEXPECTEDLY_CONTAINS_MARKS")
    if result["hash_contains_mark_price_or_weight"]:
        raise AssertionError("PAPER_STATE_HASH_UNEXPECTEDLY_CONTAINS_MARKS")
    if result["writes_performed"] is not False:
        raise AssertionError("PROBE_MUST_BE_READ_ONLY")
    return result


if __name__ == "__main__":
    import json

    print(json.dumps(run_probe(), indent=2, sort_keys=True))
