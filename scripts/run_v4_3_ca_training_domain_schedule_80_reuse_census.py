"""Offline reuse census for all 80 V4-3 CA schedule-required events.

No provider call is allowed here.  The runner verifies the immutable residual
attribution result, derives the exact 80-event inventory, then checks only
hash-pinned already-promoted official KSEI evidence for exact event_id+ticker
matches.  Residual events are emitted in full for a later all-residual live
acquisition; no pass-preserving subset selection is performed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from idx_trade.ranking_v4_3_ca_schedule_reuse import (
    CONFLICT,
    RESOLVED_NON_BLOCKING,
    RESOLVED_TRANSITION,
    event_inventory_identity,
    normalize_current_events,
    residual_document_claims,
    resolve_existing_claims,
    schedule_claims,
)


DEFAULT_CONFIG = Path("config/v4_3_ca_training_domain_schedule_80_reuse_v1.json")


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"INPUT_MISSING:{path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"{label}_MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{label}_NOT_OBJECT:{path}")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attribution-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def verify_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != "v4_3_ca_training_domain_schedule_80_reuse_v1":
        raise RuntimeError("CONFIG_SCHEMA_INVALID")
    if config.get("outcome_blind") is not True:
        raise RuntimeError("CONFIG_NOT_OUTCOME_BLIND")
    hard = config.get("hard_boundaries") or {}
    for key in (
        "network_calls",
        "provider_calls",
        "source_substitution",
        "fuzzy_event_matching",
        "record_or_distribution_date_as_transition",
        "price_inference",
        "pass_preserving_subset_selection",
        "target_or_rank_materialization",
        "model_fit",
        "prediction",
        "performance",
        "protected_forward_access",
    ):
        if hard.get(key) is not False:
            raise RuntimeError(f"HARD_BOUNDARY_CHANGED:{key}")


def verify_parent(root: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    parent = config["parent_attribution"]
    manifest_path = root / "MANIFEST.json"
    summary_path = root / "summary.json"
    actual_manifest = sha256_file(manifest_path)
    if actual_manifest != parent["manifest_sha256"]:
        raise RuntimeError(
            f"ATTRIBUTION_MANIFEST_SHA_MISMATCH:{actual_manifest}!={parent['manifest_sha256']}"
        )
    manifest = read_json(manifest_path, "ATTRIBUTION_MANIFEST")
    summary = read_json(summary_path, "ATTRIBUTION_SUMMARY")
    if summary.get("status") != parent["required_status"] or manifest.get("status") != parent["required_status"]:
        raise RuntimeError("ATTRIBUTION_STATUS_CHANGED")
    if summary.get("outcome_blind") is not True or manifest.get("outcome_blind") is not True:
        raise RuntimeError("ATTRIBUTION_NOT_OUTCOME_BLIND")
    if summary.get("parent_replay_manifest_sha256") != parent["parent_replay_manifest_sha256"]:
        raise RuntimeError("ATTRIBUTION_PARENT_REPLAY_CHANGED")
    if int(summary.get("schedule_required_events") or -1) != int(parent["required_schedule_events"]):
        raise RuntimeError("ATTRIBUTION_SCHEDULE_EVENT_COUNT_CHANGED")
    for key in (
        "network_calls",
        "provider_calls",
        "retry_unresolved_tickers",
        "target_or_rank_materialized",
        "historical_target_loaded",
        "model_fit",
        "prediction_generated",
        "performance_computed",
        "protected_forward_accessed",
        "scientific_config_changed",
    ):
        if summary.get(key) is not False:
            raise RuntimeError(f"ATTRIBUTION_GUARDRAIL_CHANGED:{key}")
    child_hashes = manifest.get("output_hashes") or {}
    schedule_hash = str(child_hashes.get("schedule_impact") or "")
    if not schedule_hash:
        raise RuntimeError("ATTRIBUTION_SCHEDULE_IMPACT_HASH_MISSING")
    schedule_path = root / "residual_schedule_event_impact.csv"
    actual_schedule = sha256_file(schedule_path)
    if actual_schedule != schedule_hash:
        raise RuntimeError(
            f"ATTRIBUTION_SCHEDULE_IMPACT_SHA_MISMATCH:{actual_schedule}!={schedule_hash}"
        )
    events = normalize_current_events(
        pd.read_csv(schedule_path), expected_count=int(parent["required_schedule_events"])
    )
    return events, {
        "manifest_sha256": actual_manifest,
        "schedule_impact_sha256": actual_schedule,
        "summary_sha256": sha256_file(summary_path),
    }


def verify_repo_evidence(config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    evidence = config["existing_evidence"]
    verified: dict[str, str] = {}

    schedule_cfg = evidence["ksei_schedule_v3"]
    schedule_manifest = Path(schedule_cfg["manifest_path"])
    schedule_path = Path(schedule_cfg["evidence_path"])
    for label, path, expected in (
        ("ksei_schedule_manifest", schedule_manifest, schedule_cfg["manifest_sha256"]),
        ("ksei_schedule_evidence", schedule_path, schedule_cfg["evidence_sha256"]),
    ):
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"EXISTING_EVIDENCE_SHA_MISMATCH:{label}:{actual}!={expected}")
        verified[label] = actual

    residual_cfg = evidence["residual_document_semantics_v1"]
    residual_manifest = Path(residual_cfg["manifest_path"])
    residual_path = Path(residual_cfg["evidence_path"])
    for label, path, expected in (
        ("residual_semantics_manifest", residual_manifest, residual_cfg["manifest_sha256"]),
        ("residual_semantics_evidence", residual_path, residual_cfg["evidence_sha256"]),
    ):
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"EXISTING_EVIDENCE_SHA_MISMATCH:{label}:{actual}!={expected}")
        verified[label] = actual

    schedule = pd.read_csv(schedule_path)
    residual = pd.read_csv(residual_path)
    return schedule, residual, verified


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    config = read_json(args.config, "CONFIG")
    verify_config(config)
    current_events, parent_meta = verify_parent(args.attribution_root, config)
    schedule_evidence, residual_evidence, repo_hashes = verify_repo_evidence(config)

    schedule = schedule_claims(schedule_evidence, "KSEI_SCHEDULE_V3")
    residual = residual_document_claims(
        residual_evidence, "RESIDUAL_DOCUMENT_SEMANTICS_V1"
    )
    census, admitted = resolve_existing_claims(current_events, [schedule, residual])
    if len(census) != 80 or census["event_id"].nunique() != 80:
        raise RuntimeError("REUSE_CENSUS_EVENT_IDENTITY_CHANGED")

    resolved_transition = int(census["reuse_status"].eq(RESOLVED_TRANSITION).sum())
    resolved_nonblocking = int(census["reuse_status"].eq(RESOLVED_NON_BLOCKING).sum())
    conflicts = int(census["reuse_status"].eq(CONFLICT).sum())
    resolved = resolved_transition + resolved_nonblocking
    residual_events = census[
        ~census["reuse_status"].isin([RESOLVED_TRANSITION, RESOLVED_NON_BLOCKING])
    ].copy()
    if len(residual_events) != 80 - resolved:
        raise RuntimeError("RESIDUAL_EVENT_COUNT_INCONSISTENT")

    identity_sha = event_inventory_identity(current_events)
    residual_identity_sha = (
        event_inventory_identity(residual_events[["event_id", "ticker"]])
        if len(residual_events)
        else hashlib.sha256(b"").hexdigest()
    )

    args.output_dir.mkdir(parents=True)
    census_path = args.output_dir / "schedule_80_existing_evidence_reuse_census.csv"
    admitted_path = args.output_dir / "schedule_80_admitted_existing_claims.csv"
    residual_path = args.output_dir / "schedule_80_residual_events_for_acquisition.csv"
    summary_path = args.output_dir / "summary.json"
    manifest_path = args.output_dir / "MANIFEST.json"
    census.to_csv(census_path, index=False, lineterminator="\n")
    admitted.to_csv(admitted_path, index=False, lineterminator="\n")
    residual_events.to_csv(residual_path, index=False, lineterminator="\n")

    status = (
        "V4_3_CA_SCHEDULE_80_OFFLINE_REUSE_COMPLETE_ALL_RESOLVED"
        if residual_events.empty
        else "V4_3_CA_SCHEDULE_80_OFFLINE_REUSE_COMPLETE_RESIDUAL_ACQUISITION_REQUIRED"
    )
    summary = {
        "schema_version": "v4_3_ca_training_domain_schedule_80_reuse_result_v1",
        "status": status,
        "outcome_blind": True,
        "network_calls": False,
        "provider_calls": False,
        "target_or_rank_materialized": False,
        "historical_target_loaded": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "scientific_config_changed": False,
        "pass_preserving_subset_selection": False,
        "schedule_event_count": 80,
        "schedule_event_identity_sha256": identity_sha,
        "resolved_existing_evidence_events": resolved,
        "resolved_exact_transition_events": resolved_transition,
        "resolved_exact_nonblocking_events": resolved_nonblocking,
        "conflicting_existing_evidence_events": conflicts,
        "residual_events_for_acquisition": int(len(residual_events)),
        "residual_event_identity_sha256": residual_identity_sha,
        "parent_attribution_manifest_sha256": parent_meta["manifest_sha256"],
        "parent_replay_manifest_sha256": config["parent_attribution"]["parent_replay_manifest_sha256"],
        "next": (
            "REPLAY_TRAINING_DOMAIN_WITH_REUSED_EVIDENCE"
            if residual_events.empty
            else "FREEZE_AND_ACQUIRE_ALL_RESIDUAL_SCHEDULE_EVENTS"
        ),
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_hashes = {
        "reuse_census": sha256_file(census_path),
        "admitted_existing_claims": sha256_file(admitted_path),
        "residual_events": sha256_file(residual_path),
        "summary": sha256_file(summary_path),
    }
    manifest = {
        "schema_version": "v4_3_ca_training_domain_schedule_80_reuse_manifest_v1",
        "status": status,
        "outcome_blind": True,
        "input_hashes": {
            "parent_attribution_manifest": parent_meta["manifest_sha256"],
            "parent_attribution_schedule_impact": parent_meta["schedule_impact_sha256"],
            "parent_attribution_summary": parent_meta["summary_sha256"],
            **repo_hashes,
        },
        "schedule_event_identity_sha256": identity_sha,
        "residual_event_identity_sha256": residual_identity_sha,
        "output_hashes": output_hashes,
        "guardrails": {
            "network_calls": False,
            "provider_calls": False,
            "source_substitution": False,
            "fuzzy_event_matching": False,
            "record_or_distribution_date_as_transition": False,
            "price_inference": False,
            "pass_preserving_subset_selection": False,
            "target_or_rank_materialized": False,
            "model_fit": False,
            "prediction_generated": False,
            "performance_computed": False,
            "protected_forward_accessed": False,
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "status": status,
                "schedule_event_count": 80,
                "schedule_event_identity_sha256": identity_sha,
                "resolved_existing_evidence_events": resolved,
                "resolved_exact_transition_events": resolved_transition,
                "resolved_exact_nonblocking_events": resolved_nonblocking,
                "conflicting_existing_evidence_events": conflicts,
                "residual_events_for_acquisition": int(len(residual_events)),
                "residual_event_identity_sha256": residual_identity_sha,
                "manifest": str(manifest_path),
                "manifest_sha256": sha256_file(manifest_path),
                "historical_target_loaded": False,
                "model_fit": False,
                "performance_computed": False,
                "next": summary["next"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
