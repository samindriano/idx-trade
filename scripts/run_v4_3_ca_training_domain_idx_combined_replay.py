"""Replay frozen KSEI schedule-80 plus frozen IDX residual-59 evidence.

The runner starts from the immutable KSEI-129 training-domain replay, applies
exactly the previously frozen KSEI adjudication to all 80 schedule events, then
applies the frozen IDX adjudication only to the resulting residual 59 schedule
events.  It recomputes continuity/support and the preregistered 90% gate without
loading targets, fitting models, computing predictions, or accessing outcomes.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

BASE_REPLAY_RUNNER = REPO_ROOT / "scripts" / "run_v4_3_ca_training_domain_schedule_80_adjudication_replay.py"
DEFAULT_CONFIG = REPO_ROOT / "config" / "v4_3_ca_training_domain_idx_combined_replay_v1.json"


def _load_base_runner():
    spec = importlib.util.spec_from_file_location("v4_3_schedule80_replay_base", BASE_REPLAY_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("BASE_REPLAY_RUNNER_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


base = _load_base_runner()

from idx_trade.ranking_v4_3_ca_idx_adjudication_replay import apply_idx_adjudication  # noqa: E402
from idx_trade.ranking_v4_3_ca_schedule_reuse import event_inventory_identity  # noqa: E402
from idx_trade.ranking_v4_3_ca_training_domain import (  # noqa: E402
    GATE_RATE,
    attach_continuity,
    build_training_date_sets,
    combine_target_support,
    validate_frozen_tail,
)


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


def normalize_ticker(value: object) -> str:
    return clean(value).upper().replace(".JK", "")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-replay-root", type=Path, required=True)
    parser.add_argument("--ksei-adjudication-root", type=Path, required=True)
    parser.add_argument("--idx-adjudication-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def verify_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != "v4_3_ca_training_domain_idx_combined_replay_v1":
        raise RuntimeError("CONFIG_SCHEMA_INVALID")
    if config.get("outcome_blind") is not True:
        raise RuntimeError("CONFIG_NOT_OUTCOME_BLIND")
    if float(config.get("gate_rate")) != float(GATE_RATE):
        raise RuntimeError(f"GATE_RATE_CHANGED:{config.get('gate_rate')}!={GATE_RATE}")
    hard = config.get("hard_boundaries") or {}
    for key, value in hard.items():
        if value is not False:
            raise RuntimeError(f"HARD_BOUNDARY_CHANGED:{key}")


def base_compat_config(config: dict[str, Any]) -> dict[str, Any]:
    """Map the new frozen contract onto the already-tested base verifier schema."""
    return {
        "parent_replay": config["base_replay"],
        "adjudication_parent": config["ksei_schedule80_adjudication"],
        "validation_folds": config["validation_folds"],
        "gate_rate": config["gate_rate"],
        "hard_boundaries": {
            "network_calls": False,
            "provider_calls": False,
            "source_substitution": False,
            "new_document_discovery": False,
            "fuzzy_event_matching": False,
            "price_inference": False,
            "record_or_distribution_date_as_transition": False,
            "pass_preserving_subset_selection": False,
            "threshold_change": False,
            "target_or_rank_materialization": False,
            "historical_target_loaded": False,
            "model_fit": False,
            "prediction": False,
            "performance": False,
            "protected_forward_access": False,
        },
    }


def verify_idx_adjudication(
    root: Path,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, str]]:
    expected = config["idx_schedule59_adjudication"]
    manifest_path = root / "MANIFEST.json"
    summary_path = root / "summary.json"
    evidence_path = root / "schedule_59_idx_event_evidence.csv"
    audit_path = root / "schedule_59_idx_adjudication_audit.csv"
    parse_failure_path = root / "idx_attachment_parse_failures.csv"

    actual_manifest = sha256_file(manifest_path)
    if actual_manifest != expected["manifest_sha256"]:
        raise RuntimeError(
            f"IDX_ADJUDICATION_MANIFEST_SHA_MISMATCH:{actual_manifest}!={expected['manifest_sha256']}"
        )
    manifest = read_json(manifest_path, "IDX_ADJUDICATION_MANIFEST")
    summary = read_json(summary_path, "IDX_ADJUDICATION_SUMMARY")
    if manifest.get("status") != expected["status"] or summary.get("status") != expected["status"]:
        raise RuntimeError("IDX_ADJUDICATION_STATUS_CHANGED")
    if manifest.get("outcome_blind") is not True or summary.get("outcome_blind") is not True:
        raise RuntimeError("IDX_ADJUDICATION_NOT_OUTCOME_BLIND")

    scalar_keys = (
        "residual_events",
        "resolved_events",
        "exact_transition_events",
        "exact_nonblocking_events",
        "conflict_events",
        "unresolved_events",
        "verified_successful_raw_attachments",
        "frozen_event_attachment_links",
        "parsed_unique_event_attachment_links",
        "missing_raw_candidate_links",
        "unsupported_or_parse_failed_attachments",
    )
    for key in scalar_keys:
        if int(summary.get(key, -1)) != int(expected[key]):
            raise RuntimeError(
                f"IDX_ADJUDICATION_SCALAR_CHANGED:{key}:{summary.get(key)}!={expected[key]}"
            )
    if summary.get("residual_event_identity_sha256") != expected["residual_event_identity_sha256"]:
        raise RuntimeError("IDX_ADJUDICATION_EVENT_IDENTITY_CHANGED")
    for key in (
        "network_calls",
        "provider_calls",
        "source_substitution",
        "new_document_discovery",
        "target_or_rank_materialized",
        "historical_target_loaded",
        "model_fit",
        "prediction_generated",
        "performance_computed",
        "protected_forward_accessed",
    ):
        if summary.get(key) is not False:
            raise RuntimeError(f"IDX_ADJUDICATION_GUARDRAIL_CHANGED:{key}")

    outputs = manifest.get("output_hashes") or {}
    paths = {
        "event_evidence": evidence_path,
        "adjudication_audit": audit_path,
        "attachment_parse_failures": parse_failure_path,
        "summary": summary_path,
    }
    hashes: dict[str, str] = {"manifest": actual_manifest}
    for key, path in paths.items():
        expected_sha = clean(outputs.get(key))
        actual_sha = sha256_file(path)
        if not expected_sha or actual_sha != expected_sha:
            raise RuntimeError(
                f"IDX_ADJUDICATION_CHILD_SHA_MISMATCH:{key}:{actual_sha}!={expected_sha}"
            )
        hashes[key] = actual_sha

    evidence = pd.read_csv(evidence_path, dtype=str, keep_default_na=False)
    identity = event_inventory_identity(evidence[["event_id", "ticker"]])
    if identity != expected["residual_event_identity_sha256"]:
        raise RuntimeError(f"IDX_ADJUDICATION_EVIDENCE_IDENTITY_CHANGED:{identity}")
    return evidence, summary, hashes


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")

    config = read_json(args.config, "CONFIG")
    verify_config(config)
    compat = base_compat_config(config)
    base.verify_config(compat)

    parent_frames, parent_summary, parent_hashes = base.verify_parent_replay(
        args.base_replay_root, compat
    )
    ksei_evidence, ksei_summary, ksei_hashes = base.verify_adjudication(
        args.ksei_adjudication_root, compat
    )
    idx_evidence, idx_summary, idx_hashes = verify_idx_adjudication(
        args.idx_adjudication_root, config
    )
    folds, folds_sha = base.verify_folds(compat)

    parent_events = base.build_parent_events(parent_frames["event_audit"])
    parent_schedule = pd.DataFrame(
        [
            {"event_id": event.event_id, "ticker": event.ticker}
            for event in parent_events.values()
            if event.semantic_class == "SCHEDULE_REQUIRED"
        ]
    )
    if len(parent_schedule) != 80:
        raise RuntimeError(f"BASE_SCHEDULE_REQUIRED_COUNT_CHANGED:{len(parent_schedule)}")
    parent_schedule_identity = event_inventory_identity(parent_schedule)
    if parent_schedule_identity != config["ksei_schedule80_adjudication"]["schedule_event_identity_sha256"]:
        raise RuntimeError("BASE_SCHEDULE80_IDENTITY_CHANGED")

    after_ksei, ksei_overlay = base.apply_adjudication(
        parent_events,
        ksei_evidence,
        expected_schedule_events=80,
    )
    residual = pd.DataFrame(
        [
            {"event_id": event.event_id, "ticker": event.ticker}
            for event in after_ksei.values()
            if event.semantic_class == "SCHEDULE_REQUIRED"
        ]
    )
    if len(residual) != 59:
        raise RuntimeError(f"POST_KSEI_RESIDUAL_COUNT_CHANGED:{len(residual)}")
    residual_identity = event_inventory_identity(residual)
    expected_residual_identity = config["idx_schedule59_adjudication"][
        "residual_event_identity_sha256"
    ]
    if residual_identity != expected_residual_identity:
        raise RuntimeError(
            f"POST_KSEI_RESIDUAL_IDENTITY_CHANGED:{residual_identity}!={expected_residual_identity}"
        )

    replayed_events, idx_overlay = apply_idx_adjudication(
        after_ksei,
        idx_evidence,
        expected_schedule_events=59,
    )
    replayed_audit = base.event_audit_frame(replayed_events)
    semantic_counts = dict(Counter(replayed_audit["semantic_class"].astype(str)))
    remaining_schedule = int((replayed_audit["semantic_class"] == "SCHEDULE_REQUIRED").sum())
    resolved_from_original_80 = 80 - remaining_schedule
    if resolved_from_original_80 != int(ksei_summary["resolved_events"]) + int(idx_summary["resolved_events"]):
        raise RuntimeError("COMBINED_RESOLVED_EVENT_COUNT_INCONSISTENT")

    ca = parent_summary["ca_diagnostics"]
    unresolved_coverage = {
        normalize_ticker(value)
        for value in ca.get("coverage_unresolved_decision_ticker_list") or []
    }
    missing_coverage = {
        normalize_ticker(value)
        for value in ca.get("coverage_missing_historical_ticker_list") or []
    }
    cross_source = {
        normalize_ticker(value)
        for value in ca.get("cross_source_conflict_tickers") or []
    }
    if len(unresolved_coverage) != int(config["base_replay"]["coverage_unresolved_decision_tickers"]):
        raise RuntimeError("BASE_UNRESOLVED_COVERAGE_IDENTITY_COUNT_CHANGED")
    if len(missing_coverage) != int(config["base_replay"]["coverage_missing_historical_tickers"]):
        raise RuntimeError("BASE_MISSING_COVERAGE_IDENTITY_COUNT_CHANGED")
    if sorted(cross_source) != sorted(config["base_replay"]["cross_source_conflict_tickers"]):
        raise RuntimeError("BASE_CROSS_SOURCE_CONFLICT_IDENTITY_CHANGED")

    windows = base.windows_from_parent(parent_frames["continuity"])
    continuity = base.replay_continuity(
        windows,
        replayed_events,
        unresolved_coverage_tickers=unresolved_coverage,
        missing_coverage_tickers=missing_coverage,
        cross_source_conflict_tickers=cross_source,
    )
    continuity_attached = attach_continuity(windows, continuity)
    decision_support = base.decision_support_from_parent(parent_frames["combined"])
    combined, per_date = combine_target_support(decision_support, continuity_attached)
    training_dates = build_training_date_sets(per_date, folds)
    frozen_check = validate_frozen_tail(per_date, folds)

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

    full_eligible = {
        "h5": int(per_date["h5_eligible"].astype(bool).sum()),
        "h10": int(per_date["h10_eligible"].astype(bool).sum()),
        "consensus": int(per_date["consensus_eligible"].astype(bool).sum()),
    }
    pass_gate = bool(
        frozen_check["all_frozen_600_full_target_eligible"]
        and frozen_check["tail_600_identity_unchanged"]
        and int(frozen_check["eligible_sessions_after_frozen_end"]) == 0
        and all_training_sets_nonempty
    )
    status = (
        "V4_3_CA_IDX_COMBINED_REPLAY_PASS_READY_FOR_HISTORICAL_EXECUTION_PIN"
        if pass_gate
        else "V4_3_CA_IDX_COMBINED_REPLAY_BLOCKED_REVIEW_REQUIRED"
    )

    args.output_dir.mkdir(parents=True)
    outputs = {
        "continuity": args.output_dir / "v4_3_ca_training_domain_idx_combined_continuity.csv",
        "combined": args.output_dir / "v4_3_full_target_support_rows_idx_combined.csv",
        "per_date": args.output_dir / "v4_3_full_target_support_per_date_idx_combined.csv",
        "training_dates": args.output_dir / "v4_3_training_date_sets_idx_combined.csv",
        "event_audit": args.output_dir / "v4_3_ca_training_event_semantics_idx_combined.csv",
        "ksei_overlay": args.output_dir / "schedule_80_ksei_replay_overlay.csv",
        "idx_overlay": args.output_dir / "schedule_59_idx_replay_overlay.csv",
        "summary": args.output_dir / "summary.json",
        "manifest": args.output_dir / "MANIFEST.json",
    }
    continuity.to_csv(outputs["continuity"], index=False, lineterminator="\n")
    combined.to_csv(outputs["combined"], index=False, lineterminator="\n")
    per_date.to_csv(outputs["per_date"], index=False, lineterminator="\n")
    training_dates.to_csv(outputs["training_dates"], index=False, lineterminator="\n")
    replayed_audit.to_csv(outputs["event_audit"], index=False, lineterminator="\n")
    ksei_overlay.to_csv(outputs["ksei_overlay"], index=False, lineterminator="\n")
    idx_overlay.to_csv(outputs["idx_overlay"], index=False, lineterminator="\n")

    summary = {
        "schema_version": "v4_3_ca_training_domain_idx_combined_replay_result_v1",
        "status": status,
        "outcome_blind": True,
        "provider_calls": False,
        "network_calls": False,
        "source_substitution": False,
        "target_or_rank_materialized": False,
        "historical_target_loaded": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "scientific_config_changed": False,
        "gate_rate": float(GATE_RATE),
        "ksei_adjudication": {
            "resolved_events": int(ksei_summary["resolved_events"]),
            "exact_transition_events": int(ksei_summary["exact_transition_events"]),
            "exact_nonblocking_events": int(ksei_summary["exact_nonblocking_events"]),
            "unresolved_events": int(ksei_summary["unresolved_events"]),
            "conflict_events": int(ksei_summary["conflict_events"]),
        },
        "idx_adjudication": {
            "resolved_events": int(idx_summary["resolved_events"]),
            "exact_transition_events": int(idx_summary["exact_transition_events"]),
            "exact_nonblocking_events": int(idx_summary["exact_nonblocking_events"]),
            "unresolved_events": int(idx_summary["unresolved_events"]),
            "conflict_events": int(idx_summary["conflict_events"]),
        },
        "combined_resolved_from_original_80": resolved_from_original_80,
        "combined_remaining_schedule_events": remaining_schedule,
        "replayed_event_semantic_counts": semantic_counts,
        "coverage_unresolved_decision_tickers": len(unresolved_coverage),
        "coverage_missing_historical_tickers": len(missing_coverage),
        "cross_source_conflict_tickers": sorted(cross_source),
        "full_eligible_sessions": full_eligible,
        "frozen_validation": frozen_check,
        "training_date_counts": fold_counts.to_dict("records"),
        "all_fold_head_training_sets_nonempty": all_training_sets_nonempty,
        "base_replay_manifest_sha256": parent_hashes["manifest"],
        "ksei_adjudication_manifest_sha256": ksei_hashes["manifest"],
        "idx_adjudication_manifest_sha256": idx_hashes["manifest"],
        "validation_folds_sha256": folds_sha,
        "next": (
            "PIN_PASS_ARTIFACT_BEFORE_HISTORICAL_EXECUTION"
            if pass_gate
            else "REVIEW_REMAINING_47_SCHEDULE_EVENTS_AND_APPLY_STOP_RULE"
        ),
    }
    outputs["summary"].write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    output_hashes = {
        key: sha256_file(path)
        for key, path in outputs.items()
        if key != "manifest"
    }
    manifest = {
        "schema_version": "v4_3_ca_training_domain_idx_combined_replay_manifest_v1",
        "status": status,
        "outcome_blind": True,
        "immutable_inputs": {
            "base_replay_manifest": parent_hashes["manifest"],
            "ksei_adjudication_manifest": ksei_hashes["manifest"],
            "idx_adjudication_manifest": idx_hashes["manifest"],
            "validation_folds": folds_sha,
            "post_ksei_residual_identity": residual_identity,
        },
        "input_child_hashes": {
            "base_replay": parent_hashes,
            "ksei_adjudication": ksei_hashes,
            "idx_adjudication": idx_hashes,
        },
        "output_hashes": output_hashes,
        "guardrails": config["hard_boundaries"],
    }
    outputs["manifest"].write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "status": status,
                "combined_resolved_from_original_80": resolved_from_original_80,
                "combined_remaining_schedule_events": remaining_schedule,
                "idx_exact_transition_events": int(idx_summary["exact_transition_events"]),
                "idx_exact_nonblocking_events": int(idx_summary["exact_nonblocking_events"]),
                "full_eligible_sessions": full_eligible,
                "frozen_validation": frozen_check,
                "all_fold_head_training_sets_nonempty": all_training_sets_nonempty,
                "training_date_counts": fold_counts.to_dict("records"),
                "historical_target_loaded": False,
                "model_fit": False,
                "performance_computed": False,
                "manifest": str(outputs["manifest"]),
                "manifest_sha256": sha256_file(outputs["manifest"]),
                "next": summary["next"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
