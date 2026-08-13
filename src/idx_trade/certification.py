from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from .provenance import environment_manifest, sha256_file, write_manifest_atomic


def _require_full_universe_pass(gate_report: dict[str, object]) -> dict[str, object]:
    summary = gate_report.get("full_universe_summary")
    if not isinstance(summary, dict):
        raise ValueError("Certified snapshot requires a full-universe gate report")
    if not bool(gate_report.get("passed", False)) or not bool(summary.get("passed", False)):
        raise RuntimeError("Cannot certify a snapshot from a failed full-universe DATA GATE")
    if int(summary.get("unknown_sessions", -1)) != 0:
        raise RuntimeError("Cannot certify snapshot with unresolved UNKNOWN sessions")
    if int(summary.get("missing_active_prices", -1)) != 0:
        raise RuntimeError("Cannot certify snapshot with missing ACTIVE-session prices")
    if int(summary.get("failed_tickers", -1)) != 0:
        raise RuntimeError("Cannot certify snapshot while required tickers still fail")
    return summary


def create_certified_snapshot_manifest(
    gate_report: dict[str, object],
    artifacts: Mapping[str, str | Path],
    *,
    code_commit: str,
    output_path: str | Path,
    metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    """Freeze hashes for a DATA-GATE-certified market-data snapshot.

    Certification is intentionally impossible until the point-in-time
    full-universe gate passes with zero UNKNOWN sessions and zero missing
    ACTIVE-session prices. Raw provider contamination may exist only because it
    is already quarantined by the certified model-safe view.
    """

    summary = _require_full_universe_pass(gate_report)
    commit = str(code_commit).strip()
    if not commit:
        raise ValueError("code_commit is required for snapshot certification")
    if not artifacts:
        raise ValueError("At least one data artifact is required for certification")

    hashes: dict[str, str] = {}
    paths: dict[str, str] = {}
    for logical_name, value in sorted(artifacts.items()):
        name = str(logical_name).strip()
        if not name:
            raise ValueError("Artifact logical names must be non-empty")
        path = Path(value)
        if not path.is_file():
            raise FileNotFoundError(f"Certification artifact missing: {path}")
        hashes[name] = sha256_file(path)
        paths[name] = str(path)

    reproducibility = environment_manifest(
        config={
            "code_commit": commit,
            "window_start": summary.get("window_start"),
            "window_end": summary.get("window_end"),
        },
        data_snapshots=hashes,
    )
    manifest: dict[str, object] = {
        "snapshot_schema_version": 1,
        "certified_at_utc": datetime.now(timezone.utc).isoformat(),
        "code_commit": commit,
        "data_gate": dict(summary),
        "artifacts": {
            name: {"path": paths[name], "sha256": hashes[name]}
            for name in sorted(hashes)
        },
        "metadata": metadata or {},
        "reproducibility": reproducibility,
    }
    write_manifest_atomic(Path(output_path), manifest)
    return manifest


def verify_certified_snapshot_manifest(manifest: Mapping[str, object]) -> dict[str, object]:
    """Re-hash certified artifacts and report any drift before model research."""

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, Mapping) or not artifacts:
        raise ValueError("Snapshot manifest has no certified artifacts")

    mismatches: list[dict[str, object]] = []
    verified = 0
    for logical_name, raw in artifacts.items():
        if not isinstance(raw, Mapping):
            mismatches.append(
                {"artifact": str(logical_name), "status": "INVALID_MANIFEST_ENTRY"}
            )
            continue
        path = Path(str(raw.get("path", "")))
        expected = str(raw.get("sha256", ""))
        if not path.is_file():
            mismatches.append(
                {"artifact": str(logical_name), "status": "MISSING", "path": str(path)}
            )
            continue
        actual = sha256_file(path)
        if actual != expected:
            mismatches.append(
                {
                    "artifact": str(logical_name),
                    "status": "HASH_MISMATCH",
                    "path": str(path),
                    "expected": expected,
                    "actual": actual,
                }
            )
            continue
        verified += 1

    return {
        "valid": not mismatches,
        "verified_artifacts": verified,
        "artifact_count": len(artifacts),
        "mismatches": mismatches,
    }
