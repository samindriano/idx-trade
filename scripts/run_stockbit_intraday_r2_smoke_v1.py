from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.stockbit_intraday_cloud_smoke import (  # noqa: E402
    run_r2_smoke,
    safe_smoke_prefix,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the isolated create-only Stockbit Intraday R2 smoke contract"
    )
    parser.add_argument(
        "--prefix",
        required=True,
        help="Unique throwaway prefix: stockbit-intraday-smoke-v1/<run-id>",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    prefix = safe_smoke_prefix(args.prefix)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "mode": "DRY_RUN",
                    "throwaway_prefix": prefix,
                    "r2_calls": 0,
                    "provider_calls": 0,
                    "production_prefix_written": False,
                    "outcome_accessed": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    result = run_r2_smoke(values=os.environ, prefix=prefix)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
