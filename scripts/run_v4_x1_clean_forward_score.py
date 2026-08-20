"""CLI for one immutable, outcome-blind clean V4-X1 prospective score capture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.v4_x1_clean_forward_score import (  # noqa: E402
    DEFAULT_OBSERVED_BY,
    score_v4_x1_session,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--x1-model-root", type=Path, required=True)
    parser.add_argument("--clean-panel", type=Path, required=True)
    parser.add_argument("--clean-security-master", type=Path, required=True)
    parser.add_argument("--session-date", default=None)
    parser.add_argument("--observed-by", default=DEFAULT_OBSERVED_BY)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = score_v4_x1_session(
        args.runtime_root,
        args.x1_model_root,
        repo_root=args.repo_root,
        clean_panel=args.clean_panel,
        clean_security_master=args.clean_security_master,
        session_date=args.session_date,
        observed_by=args.observed_by,
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
