"""Fail-closed consistency check for the frozen eligibility contract.

This is a text/code provenance check only. It does not open market data,
feature data, labels, or results. A conflict is reported instead of choosing a
population by chronology or implementation convenience.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--implementation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")

    protocol = args.protocol.read_text(encoding="utf-8")
    packet = args.packet.read_text(encoding="utf-8")
    implementation = args.implementation.read_text(encoding="utf-8")
    checks = {
        "protocol_declares_minimum_20": bool(re.search(r"at least 20\s+finite observations", protocol, re.I)),
        "packet_declares_minimum_20": bool(re.search(r"at least 20\s+finite observations", packet, re.I)),
        "packet_declares_window_min_periods": "min_periods=window" in packet,
        "implementation_uses_window_min_periods": "min_periods=window" in implementation,
    }
    checks["contract_conflict_detected"] = (
        checks["protocol_declares_minimum_20"]
        and checks["packet_declares_minimum_20"]
        and checks["packet_declares_window_min_periods"]
        and checks["implementation_uses_window_min_periods"]
    )
    status = "BLOCKED_POLICY_CONFLICT" if checks["contract_conflict_detected"] else "PASS_NO_CONFLICT_DETECTED"
    payload = {
        "status": status,
        "stage": "ELIGIBILITY_CONTRACT_CONSISTENCY_CHECK_V1",
        "checks": checks,
        "inputs": {
            "protocol": {"path": str(args.protocol), "sha256": sha256_file(args.protocol)},
            "packet": {"path": str(args.packet), "sha256": sha256_file(args.packet)},
            "implementation": {"path": str(args.implementation), "sha256": sha256_file(args.implementation)},
        },
        "decision": "Do not choose or regenerate a population while the conflict is present.",
        "scope": "text and implementation provenance only; no dataset access",
        "verifier_code_sha256": sha256_file(Path(__file__)),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    if status == "BLOCKED_POLICY_CONFLICT":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
