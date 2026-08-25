from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from idx_trade.prospective_preaccess_adapters_v1 import build_production_readiness


def main() -> int:
    parser = argparse.ArgumentParser(description="Outcome-blind V4-X1 pre-access artifact audit")
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--as-of-session", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_production_readiness(
        repo_root=args.repo_root.resolve(),
        data_root=args.data_root.resolve(),
        as_of_session=args.as_of_session,
    )
    rendered = json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False)
    if args.output is None:
        print(rendered)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({"output": str(args.output), "overall_status": report["readiness"]["overall_status"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
