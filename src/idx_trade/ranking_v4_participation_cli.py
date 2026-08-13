from __future__ import annotations

import argparse
import json
from pathlib import Path

from .ranking_v4_participation_prepare import prepare_v4a_cache
from .ranking_v4_participation_run import run_v4a_first_pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Frozen Ranking V4-A Participation Quality workflow")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="build outcome-independent A1/A2 feature cache")
    prepare.add_argument("--panel", type=Path, required=True)
    prepare.add_argument("--calendar", type=Path, required=True)
    prepare.add_argument("--v3-cache", type=Path, required=True)
    prepare.add_argument("--v3-manifest", type=Path, required=True)
    prepare.add_argument("--spec", type=Path, required=True)
    prepare.add_argument("--output-dir", type=Path, required=True)
    prepare.add_argument("--code-commit", required=True)

    run = sub.add_parser(
        "run",
        help="execute frozen atomic F1-F6 control+A1+A2 run; requires separate run authorization",
    )
    run.add_argument("--cache", type=Path, required=True)
    run.add_argument("--cache-manifest", type=Path, required=True)
    run.add_argument("--spec", type=Path, required=True)
    run.add_argument("--v3-f1-f4-metrics", type=Path, required=True)
    run.add_argument("--v3-f1-f4-predictions", type=Path, required=True)
    run.add_argument("--v3-f5-f6-metrics", type=Path, required=True)
    run.add_argument("--v3-f5-f6-predictions", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--code-commit", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        result = prepare_v4a_cache(
            panel_path=args.panel,
            calendar_path=args.calendar,
            v3_cache_path=args.v3_cache,
            v3_manifest_path=args.v3_manifest,
            spec_path=args.spec,
            output_dir=args.output_dir,
            code_commit=args.code_commit,
        )
    else:
        result = run_v4a_first_pass(
            cache_path=args.cache,
            cache_manifest_path=args.cache_manifest,
            spec_path=args.spec,
            v3_f1_f4_metrics_path=args.v3_f1_f4_metrics,
            v3_f1_f4_predictions_path=args.v3_f1_f4_predictions,
            v3_f5_f6_metrics_path=args.v3_f5_f6_metrics,
            v3_f5_f6_predictions_path=args.v3_f5_f6_predictions,
            output_dir=args.output_dir,
            code_commit=args.code_commit,
        )
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
