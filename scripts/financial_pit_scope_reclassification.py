from __future__ import annotations

import argparse
import json

from idx_trade.financial_scope_reclassification import run_offline_reclassification


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline Financial PIT scope reclassification")
    parser.add_argument("--census-root", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()
    result = run_offline_reclassification(
        census_root=args.census_root,
        output_root=args.output_root,
    )
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    print(json.dumps(result["manifest"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
