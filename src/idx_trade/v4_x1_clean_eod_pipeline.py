"""Clean V4-X1 adapter over the existing canonical EOD + X1 pipeline.

The operational pipeline (canonical EOD catch-up, same-day anti-backfill,
immutable registry, counter verification) is reused unchanged. This adapter
only swaps the score module to the accepted clean model/input lineage for the
duration of the process.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from . import v4_x1_clean_forward_score as clean_x1
from . import v4_x1_eod_pipeline as legacy_pipeline


def run_clean_eod_pipeline(
    runtime_root: str | Path,
    x1_model_root: str | Path,
    *,
    clean_panel: str | Path,
    clean_security_master: str | Path,
    repo_root: str | Path,
    batch_size: int = 100,
    observed_by: str = clean_x1.DEFAULT_OBSERVED_BY,
) -> dict[str, Any]:
    clean_x1.configure_clean_inputs(clean_panel, clean_security_master)
    original_x1 = legacy_pipeline.x1
    legacy_pipeline.x1 = clean_x1
    try:
        result = legacy_pipeline.run_eod_v4_x1_pipeline(
            runtime_root,
            x1_model_root,
            repo_root=repo_root,
            batch_size=batch_size,
            observed_by=observed_by,
        )
    finally:
        legacy_pipeline.x1 = original_x1
    result = dict(result)
    result["clean_generation"] = clean_x1.GENERATION
    result["clean_model_id"] = clean_x1.MODEL_ID
    result["prospective_freeze_boundary"] = observed_by
    result["clean_panel_sha256"] = clean_x1.EXPECTED_CLEAN_PANEL_SHA256
    result["clean_security_master_baseline_sha256"] = (
        clean_x1.EXPECTED_CLEAN_SECURITY_MASTER_SHA256
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Canonical EOD + accepted clean V4-X1 prospective score pipeline"
    )
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--x1-model-root", type=Path, required=True)
    parser.add_argument("--clean-panel", type=Path, required=True)
    parser.add_argument("--clean-security-master", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--observed-by", default=clean_x1.DEFAULT_OBSERVED_BY)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_clean_eod_pipeline(
        args.runtime_root,
        args.x1_model_root,
        clean_panel=args.clean_panel,
        clean_security_master=args.clean_security_master,
        repo_root=args.repo_root,
        batch_size=args.batch_size,
        observed_by=args.observed_by,
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, default=str))
    return 0 if str(result.get("status", "")).startswith("PIPELINE_OK_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
