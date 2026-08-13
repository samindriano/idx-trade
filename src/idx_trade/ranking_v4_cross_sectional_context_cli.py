from __future__ import annotations

import argparse
import json
from pathlib import Path

from .ranking_v4_cross_sectional_context_prepare import prepare_v4c_cache
from .ranking_v4_cross_sectional_context_run import run_v4c_first_pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ranking V4-C Cross-Sectional Context tooling")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="prepare frozen pre-outcome V4-C cache")
    prepare.add_argument("--panel", type=Path, required=True)
    prepare.add_argument("--calendar", type=Path, required=True)
    prepare.add_argument("--v3-cache", type=Path, required=True)
    prepare.add_argument("--v3-manifest", type=Path, required=True)
    prepare.add_argument("--spec", type=Path, required=True)
    prepare.add_argument("--output-dir", type=Path, required=True)
    prepare.add_argument("--code-commit", required=True)

    run = sub.add_parser("run", help="run frozen atomic V4-C first pass")
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
        result = prepare_v4c_cache(
            panel_path=args.panel,
            calendar_path=args.calendar,
            v3_cache_path=args.v3_cache,
            v3_manifest_path=args.v3_manifest,
            spec_path=args.spec,
            output_dir=args.output_dir,
            code_commit=args.code_commit,
        )
    elif args.command == "run":
        result = run_v4c_first_pass(
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
    else:  # pragma: no cover
        raise AssertionError(f"unexpected command: {args.command}")
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
