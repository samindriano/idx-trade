"""Safe operator entry point for the V4-X1 prospective evaluation gate.

Only the read-only preflight is exposed by this task.  The protected loader,
real marker, and result writer are intentionally not reachable from this CLI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from idx_trade.provenance import sha256_file

FROZEN_CODE_PIN_MANIFEST_SHA256 = "ee260b46f9150f150e3280bc142370baf23615efc6fea90198382f470fc3f46a"
FROZEN_GATE_BLOB_SHA1 = "499deedd5c4549285adb12bed68f427bf60d2bc8"
FROZEN_GATE_SOURCE_COMMIT = "ff05f3a8c6f398217c6eba395fca5ea11ad3dacb"


def _independent_code_pin_check() -> None:
    """Check the executing gate bytes before importing that gate module."""

    gate_path = REPO_ROOT / "src" / "idx_trade" / "prospective_evaluation_gate_v1.py"
    manifest_path = REPO_ROOT / "config" / "v4_x1_prospective_evaluation_code_pin_v1.json"
    gate_bytes = gate_path.read_bytes()
    gate_blob = hashlib.sha1(f"blob {len(gate_bytes)}\0".encode("ascii") + gate_bytes).hexdigest()
    if gate_blob != FROZEN_GATE_BLOB_SHA1:
        raise RuntimeError("independent gate Git blob pin mismatch")
    manifest_bytes = manifest_path.read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest() != FROZEN_CODE_PIN_MANIFEST_SHA256:
        raise RuntimeError("independent code-pin manifest SHA-256 mismatch")
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    gate = manifest.get("gate")
    if not isinstance(gate, dict) or gate.get("git_blob_sha1") != FROZEN_GATE_BLOB_SHA1:
        raise RuntimeError("independent manifest gate pin mismatch")
    if gate.get("source_commit") != FROZEN_GATE_SOURCE_COMMIT:
        raise RuntimeError("independent manifest gate commit mismatch")


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
    parser.add_argument("--preflight-bundle", type=Path)
    parser.add_argument("--preflight-bundle-sha256")
    parser.add_argument("--output-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        _independent_code_pin_check()
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError) as exc:
        print(json.dumps({"status": "INTEGRITY_FAILURE", "reason": str(exc)}, sort_keys=True, indent=2))
        return 0
    from idx_trade.prospective_evaluation_gate_v1 import (
        ProspectiveAccessGateBlocked,
        inspect_persisted_access_status,
        validate_preflight_bundle,
        validate_machine_readable_contract,
    )
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
        if args.preflight_bundle is None or not args.preflight_bundle_sha256:
            raise ProspectiveAccessGateBlocked("PREACCESS_ARTIFACT_BUNDLE_REQUIRED")
        validate_preflight_bundle(
            args.preflight_bundle,
            args.preflight_bundle_sha256,
            contract_path=contract,
            contract_sha256=args.contract_sha256,
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
            code = code if code == "PREACCESS_ARTIFACT_BUNDLE_REQUIRED" else "INTEGRITY_FAILURE"
        result.update({"status": "PRE_FLIGHT_BLOCKED", "blocker_codes": [code]})
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
