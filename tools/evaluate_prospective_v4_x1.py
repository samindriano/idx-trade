"""Safe operator entry point for the V4-X1 prospective evaluation gate.

Only the read-only preflight is exposed by this task.  The protected loader,
real marker, and result writer are intentionally not reachable from this CLI.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from idx_trade.prospective_evaluation_gate_v1 import (
    ProspectiveAccessGateBlocked,
    validate_machine_readable_contract,
)
from idx_trade.provenance import sha256_file


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V4-X1 prospective evaluation preflight")
    parser.add_argument("--preflight-only", action="store_true", required=True)
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("config/v4_x1_prospective_evaluation_contract_v1.json"),
    )
    parser.add_argument("--contract-sha256", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result: dict[str, object] = {
        "schema_version": "v4_x1_prospective_evaluation_preflight_v1",
        "protected_outcomes_accessed": False,
        "real_protected_loader_called": False,
        "real_outcome_access_marker_written": False,
        "forward_counter_changed": False,
        "paper_state_changed": False,
    }
    try:
        contract = args.contract.resolve()
        if not contract.is_file() or sha256_file(contract) != str(args.contract_sha256).lower():
            raise ProspectiveAccessGateBlocked("prospective evaluation contract sha256 mismatch")
        _, payload = validate_machine_readable_contract(
            contract,
            args.contract_sha256,
            require_resolved_target=True,
        )
        result.update(
            {
                "status": "PRE_FLIGHT_READY_BUT_HUMAN_AUTHORIZATION_ABSENT",
                "blocker_codes": ["FINAL_HUMAN_AUTHORIZATION_REQUIRED"],
                "contract_sha256": payload["sha256"],
            }
        )
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    except ProspectiveAccessGateBlocked as exc:
        code = str(exc)
        if "CANONICAL_TARGET_IDENTITY_UNRESOLVED" not in code:
            code = "INTEGRITY_FAILURE"
        result.update({"status": "PRE_FLIGHT_BLOCKED", "blocker_codes": [code]})
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
