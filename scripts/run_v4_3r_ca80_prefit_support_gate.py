"""Outcome-blind prefit support gate for the separately preregistered V4-3R CA80 generation.

This consumes the immutable final V4-3 combined CA replay and only re-thresholds
already-frozen per-date target-support counts from 90% to the new preregistered
80% date gate.  Row-level price/CA observability is never relaxed or inferred.
No target return/rank, model, prediction, performance, or protected outcome is
materialized here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.ranking_v4_3_ca_training_domain import (  # noqa: E402
    build_training_date_sets,
    validate_frozen_tail,
)
from idx_trade.ranking_v4_3r_support import (  # noqa: E402
    GATE_RATE,
    frozen_support_bucket_counts,
    rethreshold_per_date_support,
)

DEFAULT_CONFIG = REPO_ROOT / "config" / "ranking_v4_3r_ca80_preregistration_v1.json"


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


def clean(value: object) -> str:
    return " ".join(str(value or "").split())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-combined-replay-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def verify_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != "ranking_v4_3r_ca80_preregistration_v1":
        raise RuntimeError("CONFIG_SCHEMA_INVALID")
    if config.get("generation_id") != "V4_3R_CA80":
        raise RuntimeError("CONFIG_GENERATION_INVALID")
    if config.get("outcome_blind") is not True:
        raise RuntimeError("CONFIG_NOT_OUTCOME_BLIND")
    if config.get("historical_target_access_authorized") is not False:
        raise RuntimeError("CONFIG_PRETARGET_AUTHORIZATION_CHANGED")
    changed = config.get("changed_from_v4_3") or {}
    if float(changed["prefit_date_full_target_support_gate"]["v4_3r"]) != GATE_RATE:
        raise RuntimeError("V4_3R_PREFIT_GATE_CHANGED")
    if float(changed["evaluation_date_target_coverage_gate"]["v4_3r"]) != GATE_RATE:
        raise RuntimeError("V4_3R_EVALUATION_GATE_CHANGED")
    if float(changed["prefit_date_full_target_support_gate"]["v4_3"]) != 0.90:
        raise RuntimeError("V4_3_REFERENCE_GATE_CHANGED")
    hard = config.get("hard_boundaries") or {}
    for key, value in hard.items():
        if value is not False:
            raise RuntimeError(f"HARD_BOUNDARY_CHANGED:{key}")


def verify_parent(root: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any], dict[str, str]]:
    expected = config["parent_outcome_blind_support"]
    manifest_path = root / "MANIFEST.json"
    summary_path = root / "summary.json"
    per_date_path = root / "v4_3_full_target_support_per_date_idx_combined.csv"
    combined_path = root / "v4_3_full_target_support_rows_idx_combined.csv"
    event_audit_path = root / "v4_3_ca_training_event_semantics_idx_combined.csv"

    actual_manifest = sha256_file(manifest_path)
    if actual_manifest != expected["manifest_sha256"]:
        raise RuntimeError(
            f"PARENT_MANIFEST_SHA_MISMATCH:{actual_manifest}!={expected['manifest_sha256']}"
        )
    manifest = read_json(manifest_path, "PARENT_MANIFEST")
    summary = read_json(summary_path, "PARENT_SUMMARY")
    if manifest.get("status") != expected["status"] or summary.get("status") != expected["status"]:
        raise RuntimeError("PARENT_STATUS_CHANGED")
    if manifest.get("outcome_blind") is not True or summary.get("outcome_blind") is not True:
        raise RuntimeError("PARENT_NOT_OUTCOME_BLIND")
    if int(summary.get("combined_resolved_from_original_80", -1)) != int(expected["resolved_schedule_events"]):
        raise RuntimeError("PARENT_RESOLVED_SCHEDULE_COUNT_CHANGED")
    if int(summary.get("combined_remaining_schedule_events", -1)) != int(expected["remaining_schedule_events"]):
        raise RuntimeError("PARENT_REMAINING_SCHEDULE_COUNT_CHANGED")
    for key in (
        "historical_target_loaded",
        "model_fit",
        "performance_computed",
        "protected_forward_accessed",
    ):
        if summary.get(key) is not False:
            raise RuntimeError(f"PARENT_OUTCOME_GUARD_CHANGED:{key}")

    outputs = manifest.get("output_hashes") or {}
    required_paths = {
        "per_date": per_date_path,
        "combined": combined_path,
        "event_audit": event_audit_path,
        "summary": summary_path,
    }
    hashes = {"manifest": actual_manifest}
    for key, path in required_paths.items():
        expected_sha = clean(outputs.get(key))
        actual_sha = sha256_file(path)
        if not expected_sha or expected_sha != actual_sha:
            raise RuntimeError(f"PARENT_CHILD_SHA_MISMATCH:{key}:{actual_sha}!={expected_sha}")
        hashes[key] = actual_sha

    per_date = pd.read_csv(per_date_path)
    return per_date, summary, hashes


def verify_folds(config: dict[str, Any]) -> tuple[pd.DataFrame, str]:
    cfg = config["validation_folds"]
    path = REPO_ROOT / str(cfg["path"])
    actual = sha256_file(path)
    if actual != cfg["sha256"]:
        raise RuntimeError(f"VALIDATION_FOLDS_SHA_MISMATCH:{actual}!={cfg['sha256']}")
    folds = pd.read_csv(path)
    if len(folds) != 600:
        raise RuntimeError(f"VALIDATION_FOLDS_COUNT_CHANGED:{len(folds)}")
    return folds, actual


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    config = read_json(args.config, "CONFIG")
    verify_config(config)
    parent_per_date, parent_summary, parent_hashes = verify_parent(
        args.parent_combined_replay_root, config
    )
    folds, folds_sha = verify_folds(config)

    per_date = rethreshold_per_date_support(parent_per_date, gate_rate=GATE_RATE)
    training_dates = build_training_date_sets(per_date, folds)
    frozen_check = validate_frozen_tail(per_date, folds)
    bucket_counts = frozen_support_bucket_counts(per_date, folds)

    if training_dates.empty:
        fold_counts = pd.DataFrame(columns=["fold", "head", "training_dates"])
    else:
        fold_counts = (
            training_dates.groupby(["fold", "head"], sort=True)
            .size()
            .rename("training_dates")
            .reset_index()
        )
    all_training_sets_nonempty = bool(
        len(fold_counts) == 12 and int(fold_counts["training_dates"].min()) > 0
    ) if len(fold_counts) else False

    eligible_sessions = {
        "h5": int(per_date["h5_eligible"].astype(bool).sum()),
        "h10": int(per_date["h10_eligible"].astype(bool).sum()),
        "consensus": int(per_date["consensus_eligible"].astype(bool).sum()),
    }
    pass_gate = bool(
        frozen_check["all_frozen_600_full_target_eligible"]
        and frozen_check["tail_600_identity_unchanged"]
        and int(frozen_check["eligible_sessions_after_frozen_end"]) == 0
        and all_training_sets_nonempty
        and int(bucket_counts["below_0.80"]) == 0
    )
    status = (
        "V4_3R_CA80_PREFIT_SUPPORT_PASS_READY_TO_FREEZE_EXECUTION"
        if pass_gate
        else "V4_3R_CA80_PREFIT_SUPPORT_BLOCKED_REVIEW_REQUIRED"
    )

    args.output_dir.mkdir(parents=True)
    per_date_path = args.output_dir / "v4_3r_ca80_full_target_support_per_date.csv"
    training_path = args.output_dir / "v4_3r_ca80_training_date_sets.csv"
    summary_path = args.output_dir / "summary.json"
    manifest_path = args.output_dir / "MANIFEST.json"
    per_date.to_csv(per_date_path, index=False, lineterminator="\n")
    training_dates.to_csv(training_path, index=False, lineterminator="\n")

    summary = {
        "schema_version": "ranking_v4_3r_ca80_prefit_support_result_v1",
        "generation_id": "V4_3R_CA80",
        "status": status,
        "outcome_blind": True,
        "support_gate": GATE_RATE,
        "evaluation_date_target_coverage_gate_frozen": GATE_RATE,
        "parent_v4_3_gate": 0.90,
        "adapted_after_outcome_blind_support_only": True,
        "historical_target_loaded": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "row_level_target_observability_changed": False,
        "ca_semantics_changed": False,
        "decision_universe_changed": False,
        "features_changed": False,
        "learner_or_hyperparameters_changed": False,
        "folds_or_purge_changed": False,
        "promotion_gates_changed": False,
        "parent_combined_resolved_schedule_events": int(parent_summary["combined_resolved_from_original_80"]),
        "parent_combined_remaining_schedule_events": int(parent_summary["combined_remaining_schedule_events"]),
        "eligible_sessions": eligible_sessions,
        "frozen_validation": frozen_check,
        "frozen_consensus_support_buckets": bucket_counts,
        "training_date_counts": fold_counts.to_dict("records"),
        "all_fold_head_training_sets_nonempty": all_training_sets_nonempty,
        "historical_execution_authorized": pass_gate,
        "next": (
            "FREEZE_V4_3R_EXECUTION_OVERLAY_AND_CAPTURE_PREFIT_MANIFEST"
            if pass_gate
            else "STOP_AND_REVIEW_V4_3R_PREFIT_SUPPORT_WITHOUT_TARGET_ACCESS"
        ),
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    output_hashes = {
        "per_date": sha256_file(per_date_path),
        "training_dates": sha256_file(training_path),
        "summary": sha256_file(summary_path),
    }
    manifest = {
        "schema_version": "ranking_v4_3r_ca80_prefit_support_manifest_v1",
        "generation_id": "V4_3R_CA80",
        "status": status,
        "outcome_blind": True,
        "immutable_inputs": {
            "parent_combined_replay_manifest": parent_hashes["manifest"],
            "parent_combined_replay_child_hashes": parent_hashes,
            "validation_folds": folds_sha,
            "v4_3_preregistration_canonical_sha256": config["inherited_v4_3_lineage"]["preregistration_canonical_sha256"],
            "v4_3_prefit_runtime_manifest_sha256": config["inherited_v4_3_lineage"]["prefit_runtime_manifest_sha256"],
        },
        "changed_parameters": config["changed_from_v4_3"],
        "output_hashes": output_hashes,
        "guardrails": config["hard_boundaries"],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({
        "status": status,
        "support_gate": GATE_RATE,
        "eligible_sessions": eligible_sessions,
        "frozen_validation": frozen_check,
        "frozen_consensus_support_buckets": bucket_counts,
        "all_fold_head_training_sets_nonempty": all_training_sets_nonempty,
        "training_date_counts": fold_counts.to_dict("records"),
        "historical_target_loaded": False,
        "model_fit": False,
        "performance_computed": False,
        "historical_execution_authorized": pass_gate,
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "next": summary["next"],
    }, indent=2, sort_keys=True))
    return 0 if pass_gate else 2


if __name__ == "__main__":
    raise SystemExit(main())
