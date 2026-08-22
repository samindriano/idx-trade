"""Create the immutable zero-holding T0 for the E2E paper runtime."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from idx_trade.e2e_paper_orchestration_v1 import bootstrap_t0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--session-date", required=True)
    args = parser.parse_args()
    path = bootstrap_t0(args.runtime_root, session_date=args.session_date)
    print({"status": "T0_READY", "path": str(path), "outcome_access": False})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
