"""Run one fail-closed controlled E2E PAPER operational controller pass."""

from __future__ import annotations

import argparse
from datetime import datetime
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
    return parser


def main() -> int:
    args = _parser().parse_args()
    result = run_operational_cycle(
        OperationalControllerConfig(
            runtime_root=args.runtime_root,
            forward_runtime_root=args.forward_runtime_root,
            calendar_path=args.calendar,
            official_open_root=args.official_open_root,
            repo_root=args.repo_root,
            expected_branch=args.expected_branch,
            expected_commit=args.expected_commit,
        )
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
