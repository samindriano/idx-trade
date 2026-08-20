"""Canonical-EOD historical compatibility wrapper for clean V4-X1.

This keeps the accepted calendar-parent compatibility logic from the existing
V4-X1 automation while delegating scoring/counter state to the clean adapter.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import forward_monitoring as monitor
from . import v4_x1_clean_forward_score as clean_x1
from . import v4_x1_clean_eod_pipeline as clean_pipeline
from .v4_x1_eod_legacy_compat import build_scoped_ready_verifier


def run_with_legacy_attestation_compat(
    runtime_root: str | Path,
    x1_model_root: str | Path,
    *,
    clean_panel: str | Path,
    clean_security_master: str | Path,
    repo_root: str | Path,
    batch_size: int = 100,
    observed_by: str = clean_x1.DEFAULT_OBSERVED_BY,
):
    original = monitor._verify_ready_row
    monitor._verify_ready_row = build_scoped_ready_verifier(runtime_root, original)
    try:
        return clean_pipeline.run_clean_eod_pipeline(
            runtime_root,
            x1_model_root,
            clean_panel=clean_panel,
            clean_security_master=clean_security_master,
            repo_root=repo_root,
            batch_size=batch_size,
            observed_by=observed_by,
        )
    finally:
        monitor._verify_ready_row = original


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Canonical EOD + accepted clean V4-X1 with strict historical calendar compatibility"
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
    result = run_with_legacy_attestation_compat(
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
