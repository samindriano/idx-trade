"""Scoped canonical-EOD compatibility for the V4-X1 automation path.

The canonical hardening verifier remains authoritative. Historical DATA_READY
rows can fall outside that exact-byte contract because the shared official
calendar is intentionally extended over time. This shim accepts only two
bounded compatibility cases after DB core hashes remain exact:

1. modern sessions whose complete immutable session artifacts still pass the
   modern semantic contract and whose only mutable dependency is the canonical
   official calendar, which must still contain the exact session; or
2. legacy sessions covered by the accepted immutable calendar-parent
   attestation contract (or whose original calendar bytes still remain exact).

No canonical session, model, outcome, or provider state is rewritten here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from . import forward_monitoring as monitor
from . import v4_x1_eod_pipeline as pipeline
from .canonical_eod_calendar_parent_attestation import (
    ATTESTATION_FILENAME,
    ATTESTATION_NAMESPACE,
    _artifact_contract,
    verify_canonical_eod_calendar_parent_attestation,
)
from .provenance import sha256_file


MODERN_ARTIFACT_PAIRS = (
    ("session_ohlcv_path", "session_ohlcv_sha256"),
    ("stock_summary_path", "stock_summary_sha256"),
    ("stock_summary_raw_path", "stock_summary_raw_sha256"),
    ("index_summary_path", "index_summary_sha256"),
    ("index_summary_raw_path", "index_summary_raw_sha256"),
)


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


def _legacy_direct_parent_still_exact(row: Any) -> bool:
    """Validate an old manifest whose original shared calendar still matches."""

    try:
        session = str(row["session_date"])
        manifest_path = Path(str(row["manifest_path"])).expanduser().resolve()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            return False
        _artifact_contract(manifest, session_dir=manifest_path.parent, session=session)

        calendar_value = manifest.get("calendar_path")
        expected_hash = manifest.get("calendar_sha256")
        if not isinstance(calendar_value, str) or not isinstance(expected_hash, str):
            return False
        calendar = Path(calendar_value).expanduser().resolve()
        return calendar.is_file() and sha256_file(calendar) == expected_hash
    except Exception:
        return False


def _modern_calendar_extension_compatible(runtime_root: Path, row: Any) -> bool:
    """Accept a modern historical row when only the shared calendar bytes moved.

    Every immutable modern artifact is still verified by path, hash, exact
    session identity, source-table semantics, and OHLCV/model-input parity.
    The calendar is treated as an appendable provenance parent: it must be the
    canonical runtime calendar and must still contain the exact session in a
    valid unique ordered official-session list.
    """

    try:
        session = str(row["session_date"])
        expected_session = pd.Timestamp(session).normalize()
        manifest_path = Path(str(row["manifest_path"])).expanduser().resolve()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            return False

        # This path is only for complete modern manifests. Legacy manifests
        # remain behind the explicit direct-parent/attestation contract below.
        for path_key, hash_key in MODERN_ARTIFACT_PAIRS:
            if not isinstance(manifest.get(path_key), str) or not isinstance(manifest.get(hash_key), str):
                return False

        _artifact_contract(manifest, session_dir=manifest_path.parent, session=session)

        # Preserve the stronger modern source semantics from canonical EOD
        # hardening rather than accepting hashes alone.
        for key in ("stock_summary_raw_path", "index_summary_raw_path"):
            raw = json.loads(Path(str(manifest[key])).read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return False

        source_specs = (
            ("stock_summary", "as_of_date", "ticker"),
            ("index_summary", "session_date", "index_code"),
        )
        for prefix, date_column, identity_column in source_specs:
            frame = pd.read_csv(Path(str(manifest[f"{prefix}_path"])))
            if frame.empty or date_column not in frame.columns or identity_column not in frame.columns:
                return False
            dates = pd.to_datetime(frame[date_column], errors="coerce").dt.normalize()
            if dates.isna().any() or not dates.eq(expected_session).all():
                return False
            if frame[identity_column].astype(str).str.strip().eq("").any():
                return False
            if frame.duplicated([identity_column, date_column]).any():
                return False
            source = manifest.get(f"{prefix}_source")
            if not isinstance(source, dict) or source.get("session_date") != session:
                return False
            if not str(source.get("completeness_status", "")).startswith("COMPLETE"):
                return False

        snapshot = pd.read_parquet(Path(str(row["snapshot_path"])))
        evidence = pd.read_parquet(Path(str(row["evidence_path"])))
        session_ohlcv = pd.read_parquet(Path(str(manifest["session_ohlcv_path"])))
        if snapshot.empty or evidence.empty:
            return False
        if set(monitor.MODEL_INPUT_COLUMNS) - set(snapshot.columns):
            return False
        if set(monitor.SESSION_OHLCV_COLUMNS) - set(session_ohlcv.columns):
            return False
        if {"ticker", "session_date"} - set(evidence.columns):
            return False
        monitor.validate_ohlcv_against_model_input(session_ohlcv, snapshot, expected_session)

        # Only the canonical shared calendar may drift. An arbitrary substituted
        # calendar path is never accepted.
        calendar_value = manifest.get("calendar_path")
        declared_sha = manifest.get("calendar_sha256")
        if not isinstance(calendar_value, str) or not isinstance(declared_sha, str) or len(declared_sha) != 64:
            return False
        calendar = Path(calendar_value).expanduser().resolve()
        canonical_calendar = (
            runtime_root / "forward_monitoring" / "calendar" / "exchange_sessions.csv"
        ).resolve()
        if calendar != canonical_calendar or not calendar.is_file():
            return False
        sessions = monitor._read_sessions(calendar)
        if expected_session not in sessions:
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
        # Exact current-contract sessions always take accepted hardening first.
        if strict_verifier(row):
            return True
        try:
            if str(row["state"]) != "DATA_READY":
                return False
            session = str(row["session_date"])
            if not _db_core_artifacts_still_exact(row):
                return False

            # A fully modern historical session may outlive the exact bytes of
            # its shared calendar parent. All immutable artifacts remain strict.
            if _modern_calendar_extension_compatible(root, row):
                return True

            # Legacy sessions whose original calendar bytes are still present
            # need no new provenance artifact.
            if _legacy_direct_parent_still_exact(row):
                return True

            # Lost legacy calendar parents require the accepted immutable proof.
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
    """Run the normal pipeline with a process-local historical verifier shim."""

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


def build_parser():
    parser = pipeline.build_parser()
    parser.description = "Canonical EOD + frozen V4-X1 pipeline with strict historical calendar compatibility"
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
