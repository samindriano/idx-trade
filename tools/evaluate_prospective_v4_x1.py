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
    inspect_persisted_access_status,
    validate_machine_readable_contract,
)
from idx_trade.provenance import sha256_file


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V4-X1 prospective evaluation preflight")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight-only", action="store_true")
    modes.add_argument("--status-only", action="store_true")
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("config/v4_x1_prospective_evaluation_contract_v1.json"),
    )
    parser.add_argument("--contract-sha256")
    parser.add_argument("--output-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.status_only:
        if args.output_dir is None:
            print(json.dumps({"status": "INTEGRITY_FAILURE", "reason": "--output-dir is required"}, sort_keys=True))
            return 2
        print(json.dumps(inspect_persisted_access_status(args.output_dir), sort_keys=True, indent=2))
        return 0

    result: dict[str, object] = {
        "schema_version": "v4_x1_prospective_evaluation_preflight_v1",
        "protected_outcomes_accessed": False,
        "real_protected_loader_called": False,
        "real_outcome_access_marker_written": False,
        "forward_counter_changed": False,
        "paper_state_changed": False,
    }
    try:
        if not args.contract_sha256:
            raise ProspectiveAccessGateBlocked("--contract-sha256 is required for preflight")
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
