"""Run one fail-closed controlled E2E PAPER operational controller pass."""

from __future__ import annotations

import argparse
from datetime import datetime, time
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from idx_trade.e2e_paper_operational_controller_v1 import (  # noqa: E402
    OperationalControllerConfig,
    run_operational_cycle,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--forward-runtime-root", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--official-open-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--expected-branch", required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--provider-checkout", type=Path)
    parser.add_argument("--provider-commit")
    parser.add_argument("--uv-exe", type=Path)
    parser.add_argument("--python-exe", type=Path)
    parser.add_argument("--ca-attestation", type=Path)
    parser.add_argument("--ca-attestation-sha256")
    parser.add_argument("--initial-journal", type=Path)
    parser.add_argument("--initial-journal-sha256")
    parser.add_argument("--preopen-capture-start", default="08:30")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        preopen_capture_start = time.fromisoformat(args.preopen_capture_start)
    except ValueError as exc:
        raise SystemExit("E2E_PREOPEN_CAPTURE_START_INVALID") from exc
    result = run_operational_cycle(
        OperationalControllerConfig(
            runtime_root=args.runtime_root,
            forward_runtime_root=args.forward_runtime_root,
            calendar_path=args.calendar,
            official_open_root=args.official_open_root,
            repo_root=args.repo_root,
            expected_branch=args.expected_branch,
            expected_commit=args.expected_commit,
            provider_checkout=args.provider_checkout,
            provider_expected_commit=args.provider_commit,
            uv_exe=args.uv_exe,
            python_exe=args.python_exe,
            ca_attestation_path=args.ca_attestation,
            ca_attestation_sha256=args.ca_attestation_sha256,
            initial_journal_path=args.initial_journal,
            initial_journal_sha256=args.initial_journal_sha256,
            preopen_capture_start=preopen_capture_start,
        )
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
