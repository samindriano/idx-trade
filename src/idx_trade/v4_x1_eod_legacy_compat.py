"""Scoped legacy canonical-EOD compatibility for the V4-X1 automation path.

The canonical hardening verifier remains authoritative. A legacy DATA_READY row
that cannot satisfy the modern manifest contract is accepted only when its DB
core artifacts are still byte-identical and an immutable, strictly verified
calendar-parent attestation exists for that exact session.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from . import forward_monitoring as monitor
from . import v4_x1_eod_pipeline as pipeline
from .canonical_eod_calendar_parent_attestation import (
    ATTESTATION_FILENAME,
    ATTESTATION_NAMESPACE,
    verify_canonical_eod_calendar_parent_attestation,
)
from .provenance import sha256_file


def attestation_path(runtime_root: str | Path, session_date: str) -> Path:
    return (
        Path(runtime_root).expanduser().resolve()
        / ATTESTATION_NAMESPACE
        / session_date
        / ATTESTATION_FILENAME
    )


def _db_core_artifacts_still_exact(row: Any) -> bool:
    try:
        for path_key, hash_key in (
            ("snapshot_path", "snapshot_sha256"),
            ("evidence_path", "evidence_sha256"),
            ("manifest_path", "manifest_sha256"),
        ):
            raw_path = row[path_key]
            expected = row[hash_key]
            if not raw_path or not expected:
                return False
            path = Path(str(raw_path)).expanduser().resolve()
            if not path.is_file() or sha256_file(path) != str(expected):
                return False
        return True
    except Exception:
        return False


def build_scoped_ready_verifier(
    runtime_root: str | Path,
    strict_verifier: Callable[[Any], bool],
) -> Callable[[Any], bool]:
    root = Path(runtime_root).expanduser().resolve()

    def verify(row: Any) -> bool:
        # Modern canonical sessions always take the accepted hardening path.
        if strict_verifier(row):
            return True
        try:
            if str(row["state"]) != "DATA_READY":
                return False
            session = str(row["session_date"])
            if not _db_core_artifacts_still_exact(row):
                return False
            proof = attestation_path(root, session)
            if not proof.is_file():
                return False
            return verify_canonical_eod_calendar_parent_attestation(
                proof,
                expected_session=session,
            )
        except Exception:
            return False

    return verify


def run_with_legacy_attestation_compat(
    runtime_root: str | Path,
    x1_model_root: str | Path,
    *,
    repo_root: str | Path,
    batch_size: int = 100,
    observed_by: str = pipeline.x1.DEFAULT_OBSERVED_BY,
) -> dict[str, object]:
    """Run the normal pipeline with a process-local legacy verifier shim."""

    original = monitor._verify_ready_row
    monitor._verify_ready_row = build_scoped_ready_verifier(runtime_root, original)
    try:
        return pipeline.run_eod_v4_x1_pipeline(
            runtime_root,
            x1_model_root,
            repo_root=repo_root,
            batch_size=batch_size,
            observed_by=observed_by,
        )
    finally:
        monitor._verify_ready_row = original


def build_parser() -> argparse.ArgumentParser:
    parser = pipeline.build_parser()
    parser.description = "Canonical EOD + frozen V4-X1 pipeline with strict legacy attestation compatibility"
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_with_legacy_attestation_compat(
        args.runtime_root,
        args.x1_model_root,
        repo_root=args.repo_root,
        batch_size=args.batch_size,
        observed_by=args.observed_by,
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, default=str))
    return 0 if str(result.get("status", "")).startswith("PIPELINE_OK_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
