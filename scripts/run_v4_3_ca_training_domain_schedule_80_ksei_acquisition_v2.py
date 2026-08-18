"""Compatibility-fixed entry point for V4-3 schedule-80 KSEI acquisition.

V1 used ``value or -1`` when validating ``resolved_existing_evidence_events``.
The accepted parent correctly has value 0, but Python treats integer zero as
false, so V1 converted it to -1 and failed before any provider call.  This
wrapper replaces only that pre-provider verifier with a zero-safe equivalent;
all acquisition scope, provider behavior, parsing, output, and scientific
boundaries remain V1-identical.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import run_v4_3_ca_training_domain_schedule_80_ksei_acquisition as v1  # noqa: E402


def _required_int(mapping: dict[str, Any], key: str, error: str) -> int:
    value = mapping.get(key)
    if value is None:
        raise RuntimeError(error)
    return int(value)


def verify_reuse_root_zero_safe(
    root: Path,
    config: dict[str, Any],
):
    expected = config["reuse_parent"]
    manifest_path = root / "MANIFEST.json"
    summary_path = root / "summary.json"
    residual_path = root / "schedule_80_residual_events_for_acquisition.csv"

    actual_manifest = v1.sha256_file(manifest_path)
    if actual_manifest != expected["manifest_sha256"]:
        raise RuntimeError(
            f"REUSE_MANIFEST_SHA_MISMATCH:{actual_manifest}!={expected['manifest_sha256']}"
        )
    manifest = v1.read_json(manifest_path, "REUSE_MANIFEST")
    summary = v1.read_json(summary_path, "REUSE_SUMMARY")
    if manifest.get("status") != expected["status"] or summary.get("status") != expected["status"]:
        raise RuntimeError("REUSE_STATUS_CHANGED")
    if manifest.get("outcome_blind") is not True or summary.get("outcome_blind") is not True:
        raise RuntimeError("REUSE_NOT_OUTCOME_BLIND")

    if _required_int(summary, "schedule_event_count", "REUSE_EVENT_COUNT_MISSING") != int(expected["event_count"]):
        raise RuntimeError("REUSE_EVENT_COUNT_CHANGED")
    if _required_int(summary, "residual_events_for_acquisition", "REUSE_RESIDUAL_COUNT_MISSING") != int(expected["event_count"]):
        raise RuntimeError("REUSE_RESIDUAL_COUNT_CHANGED")
    if _required_int(summary, "resolved_existing_evidence_events", "REUSE_RESOLVED_COUNT_MISSING") != int(expected["resolved_existing_evidence_events"]):
        raise RuntimeError("REUSE_RESOLVED_COUNT_CHANGED")

    if summary.get("schedule_event_identity_sha256") != expected["event_identity_sha256"]:
        raise RuntimeError("REUSE_EVENT_IDENTITY_CHANGED")
    if summary.get("residual_event_identity_sha256") != expected["event_identity_sha256"]:
        raise RuntimeError("REUSE_RESIDUAL_IDENTITY_CHANGED")

    for key in (
        "historical_target_loaded",
        "model_fit",
        "performance_computed",
        "protected_forward_accessed",
        "target_or_rank_materialized",
    ):
        if key in summary and summary.get(key) is not False:
            raise RuntimeError(f"REUSE_GUARDRAIL_CHANGED:{key}")

    outputs = manifest.get("output_hashes") or {}
    expected_residual_hash = str(outputs.get("residual_events") or "")
    actual_residual_hash = v1.sha256_file(residual_path)
    if not expected_residual_hash or actual_residual_hash != expected_residual_hash:
        raise RuntimeError("REUSE_RESIDUAL_CHILD_SHA_MISMATCH")

    residual = v1.pd.read_csv(residual_path, keep_default_na=False)
    if len(residual) != int(expected["event_count"]):
        raise RuntimeError("REUSE_RESIDUAL_FILE_COUNT_CHANGED")
    identity = v1.event_inventory_identity(residual[["event_id", "ticker"]])
    if identity != expected["event_identity_sha256"]:
        raise RuntimeError(f"REUSE_RESIDUAL_FILE_IDENTITY_CHANGED:{identity}")

    return residual, {
        "reuse_manifest": actual_manifest,
        "reuse_summary": v1.sha256_file(summary_path),
        "reuse_residual_events": actual_residual_hash,
    }


def main() -> int:
    v1.verify_reuse_root = verify_reuse_root_zero_safe
    return v1.main()


if __name__ == "__main__":
    raise SystemExit(main())
