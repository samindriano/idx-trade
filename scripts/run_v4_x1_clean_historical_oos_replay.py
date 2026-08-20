"""Locked historical OOS replay for the accepted clean V4-X1 representation.

This is a post-selection robustness measurement only. It reuses the exact
frozen V4-3R 6x100 validation folds, purge, model family, hyperparameters,
features, targets, CA80 evaluator, and metrics while rebuilding the model frame
from the accepted clean Phase-A representation.

It must not mutate the deployed prospective model/counter, call providers,
retune anything, or access signal dates after the frozen validation end.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

PHASE_B_RUNNER = REPO_ROOT / "scripts" / "run_v4_x1_clean_phase_b_final_refit.py"
HISTORICAL_RUNNER = REPO_ROOT / "scripts" / "run_v4_3r_historical_one_shot.py"
PHASE_B_CONFIG = REPO_ROOT / "config" / "ranking_v4_x1_clean_phase_b_final_refit_v1.json"
DEFAULT_CONFIG = REPO_ROOT / "config" / "ranking_v4_x1_clean_historical_oos_replay_v1.json"
SELF_PATH = "scripts/run_v4_x1_clean_historical_oos_replay.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"CLEAN_HIST_IMPORT_FAILED:{name}:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


phase_b = _load_module("clean_phase_b_for_historical_replay", PHASE_B_RUNNER)
hist = _load_module("v4_3r_historical_for_clean_replay", HISTORICAL_RUNNER)
phase_a = phase_b.phase_a
open_fix = phase_b.open_fix

from idx_trade.ranking_v4_3_model_eval import CHALLENGER, CONTROL  # noqa: E402
from idx_trade.ranking_v4_3_target_execution import materialize_v4_target_ledger  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase-a-root", type=Path, required=True)
    parser.add_argument("--execution-lock-manifest", type=Path, required=True)
    parser.add_argument("--clean-bundle-manifest", type=Path, required=True)
    parser.add_argument("--clean-panel", type=Path, required=True)
    parser.add_argument("--clean-security-master", type=Path, required=True)
    parser.add_argument("--field-provenance", type=Path, required=True)
    parser.add_argument("--parent-combined-replay-root", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--open-derivative-root", type=Path, required=True)
    parser.add_argument("--overlay-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def verify_contract(repo_root: Path, config_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    cfg = hist.read_json(config_path, "CLEAN_HIST_CONFIG")
    _require(cfg.get("schema_version") == "ranking_v4_x1_clean_historical_oos_replay_v1", "CLEAN_HIST_CONFIG_SCHEMA_INVALID")
    _require(cfg.get("generation_id") == "V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1", "CLEAN_HIST_GENERATION_INVALID")
    _require(cfg.get("measurement_only") is True, "CLEAN_HIST_MEASUREMENT_ONLY_REQUIRED")
    _require(cfg.get("model_change_authorized") is False, "CLEAN_HIST_MODEL_CHANGE_MUST_BE_FALSE")
    _require(int(cfg.get("required_fit_count", -1)) == 24, "CLEAN_HIST_FIT_COUNT_CHANGED")

    guards = cfg.get("hard_guards") or {}
    required_false = (
        "provider_calls_authorized",
        "network_calls_authorized",
        "hyperparameter_search_authorized",
        "retune_authorized",
        "feature_change_authorized",
        "universe_change_authorized",
        "ca80_change_authorized",
        "session_semantics_change_authorized",
        "prospective_score_authorized",
        "forward_counter_mutation_authorized",
        "protected_forward_access_authorized",
        "fresh_forward_access_authorized",
        "deployed_model_replacement_authorized",
    )
    for key in required_false:
        _require(guards.get(key) is False, f"CLEAN_HIST_GUARD_CHANGED:{key}")
    _require(guards.get("historical_training_target_access_authorized") is True, "CLEAN_HIST_TRAINING_TARGET_NOT_AUTHORIZED")
    _require(guards.get("historical_validation_target_access_authorized") is True, "CLEAN_HIST_VALIDATION_TARGET_NOT_AUTHORIZED")
    _require(guards.get("historical_model_fit_authorized") is True, "CLEAN_HIST_MODEL_FIT_NOT_AUTHORIZED")
    _require(guards.get("historical_oos_scoring_authorized") is True, "CLEAN_HIST_OOS_SCORE_NOT_AUTHORIZED")
    _require(guards.get("historical_performance_computation_authorized") is True, "CLEAN_HIST_PERFORMANCE_NOT_AUTHORIZED")

    expected_phase_b_blob = str(cfg["parent_phase_b_contract_blob"])
    actual_phase_b_blob = hist.git_output(repo_root, "rev-parse", "HEAD:config/ranking_v4_x1_clean_phase_b_final_refit_v1.json")
    _require(actual_phase_b_blob == expected_phase_b_blob, f"CLEAN_HIST_PHASE_B_CONFIG_BLOB_CHANGED:{actual_phase_b_blob}!={expected_phase_b_blob}")
    phase_b_cfg = hist.read_json(PHASE_B_CONFIG, "PHASE_B_CONFIG")
    phase_b.verify_config(repo_root, PHASE_B_CONFIG, phase_b_cfg)
    phase_b.verify_git_blobs(repo_root, phase_b_cfg["pinned_git_blobs"])

    fold_spec = cfg["validation_folds"]
    _require(str(phase_b_cfg["validation_folds"]["sha256"]) == str(fold_spec["sha256"]), "CLEAN_HIST_FOLD_SHA_CONTRACT_CHANGED")
    return cfg, phase_b_cfg


def derive_training_dates(per_date: pd.DataFrame, folds: pd.DataFrame, expected: dict[str, int]) -> pd.DataFrame:
    work = per_date.copy()
    pieces: list[pd.DataFrame] = []
    for fold in range(1, 7):
        block = folds.loc[folds["fold"].astype(int).eq(fold)].copy()
        _require(len(block) == 100, f"CLEAN_HIST_FOLD_SIZE_CHANGED:F{fold}:{len(block)}")
        if "max_training_signal_session_index" in block.columns:
            values = pd.to_numeric(block["max_training_signal_session_index"], errors="raise").astype(int).unique()
            _require(len(values) == 1, f"CLEAN_HIST_PURGE_BOUNDARY_NOT_UNIQUE:F{fold}")
            max_train = int(values[0])
        else:
            first_validation = int(pd.to_numeric(block["session_index"], errors="raise").min())
            max_train = first_validation - 11  # exact inherited purge10 boundary
        for head, eligible_col in (("H5", "h5_eligible"), ("H10", "h10_eligible")):
            part = work.loc[
                work[eligible_col].astype(bool)
                & work["session_index"].astype(int).le(max_train),
                ["date", "session_index"],
            ].copy()
            part = part.sort_values("session_index", kind="mergesort").drop_duplicates("date")
            key = f"F{fold}_{head}"
            _require(len(part) == int(expected[key]), f"CLEAN_HIST_TRAINING_DATE_COUNT_CHANGED:{key}:{len(part)}!={expected[key]}")
            part["fold"] = fold
            part["head"] = head
            pieces.append(part[["fold", "head", "date", "session_index"]])
    result = pd.concat(pieces, ignore_index=True)
    return result.sort_values(["fold", "head", "session_index"], kind="mergesort").reset_index(drop=True)


def _metric_snapshot(model_summaries: dict[str, Any], paired: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"models": {}, "incremental": {}}
    for mode in (CONTROL, CHALLENGER):
        out["models"][mode] = {}
        for head in ("H5", "H10", "CONSENSUS"):
            item = model_summaries[mode][head]
            out["models"][mode][head] = {
                "aggregate": item["aggregate"],
                "bootstrap_95pct_mean_daily_ic": item.get("bootstrap_95pct_mean_daily_ic"),
                "fold_summary": item["fold_summary"],
            }
    for head in ("H5", "H10", "CONSENSUS"):
        out["incremental"][head] = paired[head]
    return out


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    config_path = args.config if args.config.is_absolute() else repo_root / args.config
    output_dir = args.output_dir.resolve()
    _require(not output_dir.exists(), f"CLEAN_HIST_REFUSE_OVERWRITE:{output_dir}")
    _require(not hist.git_output(repo_root, "status", "--porcelain"), "CLEAN_HIST_GIT_WORKTREE_NOT_CLEAN")

    cfg, phase_b_cfg = verify_contract(repo_root, config_path)
    runtime = hist.verify_runtime(repo_root, phase_b_cfg)
    acceptance = phase_b.verify_phase_a_acceptance(repo_root, phase_b_cfg)
    phase_a_result = phase_b.verify_phase_a_root(args.phase_a_root.resolve(), phase_b_cfg)
    paths, input_hashes = phase_b.verify_external_inputs(args, phase_b_cfg)
    continuity, ca_hashes = phase_a.load_parent_continuity(args.parent_combined_replay_root.resolve(), phase_b_cfg)
    folds, folds_sha = hist.load_validation_folds(repo_root, phase_b_cfg)

    max_validation_index = int(pd.to_numeric(folds["session_index"], errors="raise").max())
    max_validation_date = pd.Timestamp(folds["date"].max()).normalize()
    _require(max_validation_index == int(cfg["frozen_validation_end"]["session_index"]), "CLEAN_HIST_VALIDATION_END_SESSION_CHANGED")
    _require(max_validation_date.strftime("%Y-%m-%d") == str(cfg["frozen_validation_end"]["date"]), "CLEAN_HIST_VALIDATION_END_DATE_CHANGED")

    calendar = phase_a.load_calendar(paths["calendar"])
    old_panel = pd.read_parquet(paths["old_panel"])
    clean_panel = pd.read_parquet(paths["clean_panel"])
    derivative = pd.read_parquet(paths["old_open_derivative"])
    overlay = pd.read_parquet(paths["old_open_overlay"])
    anchors = pd.read_csv(paths["anchors"])
    intervals = pd.read_csv(paths["intervals"])
    clean_master = pd.read_csv(paths["clean_security_master"])
    provenance = pd.read_parquet(paths["field_provenance"])

    parent_price, parent_price_stats = phase_a.build_old_price_evidence(old_panel, calendar, derivative, overlay, anchors, intervals)
    clean_price, clean_price_stats = open_fix.apply_clean_open_lineage(parent_price, clean_panel, provenance)
    accepted_open_stats = phase_a_result["summary"].get("clean_price_evidence") or {}
    for key in (
        "policy_id", "candidate_rows", "admitted_rows", "fail_closed_rows",
        "non_candidate_rows", "final_open_admitted", "close_admitted",
        "non_candidate_open_value_exact_parity", "non_candidate_open_admission_exact_parity",
        "market_state_reused_exactly_from_parent_executable_evidence",
    ):
        _require(clean_price_stats.get(key) == accepted_open_stats.get(key), f"CLEAN_HIST_OPEN_LINEAGE_CHANGED:{key}")

    model_frame, model_frame_stats = phase_a.build_primary_model_frame(clean_panel, calendar, clean_master, clean_price)
    _require(len(model_frame) == int(phase_b_cfg["accepted_clean_primary_rows"]), "CLEAN_HIST_PRIMARY_ROWS_CHANGED")

    continuity_evidence = hist.continuity_evidence_from_parent(
        continuity,
        continuity_sha256=ca_hashes["continuity"],
        parent_manifest_sha256=ca_hashes["manifest"],
    )

    # Historical signal identities are hard-capped at the original frozen
    # validation end. Future prices needed to mature H5/H10 for those signal
    # dates may be read from the already accepted historical clean panel.
    historical_signal_frame = model_frame.loc[
        model_frame["session_index"].astype(int).le(max_validation_index)
    ].copy()
    _require(not historical_signal_frame.empty, "CLEAN_HIST_SIGNAL_FRAME_EMPTY")

    output_dir.mkdir(parents=True, exist_ok=False)
    boundary = {
        "schema_version": "ranking_v4_x1_clean_historical_oos_access_boundary_v1",
        "status": "CLEAN_HISTORICAL_OOS_TARGET_ACCESS_COMMENCED",
        "generation_id": cfg["generation_id"],
        "measurement_only": True,
        "max_signal_session_index": max_validation_index,
        "max_signal_date": max_validation_date.strftime("%Y-%m-%d"),
        "protected_forward_accessed": False,
        "fresh_forward_accessed": False,
        "provider_calls": False,
        "network_calls": False,
        "forward_counter_mutated": False,
        "deployed_model_mutated": False,
        "git_head": hist.git_output(repo_root, "rev-parse", "HEAD"),
    }
    boundary_path = output_dir / "HISTORICAL_OOS_ACCESS_BOUNDARY.json"
    boundary_path.write_text(json.dumps(boundary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    target_ledger = materialize_v4_target_ledger(
        historical_signal_frame[["ticker", "date"]],
        calendar["date"],
        clean_price,
        continuity_evidence,
    )

    per_date = phase_a_result["per_date"]
    actual_h5 = phase_b.target_support_identity(target_ledger, per_date, head="H5")
    actual_h10 = phase_b.target_support_identity(target_ledger, per_date, head="H10")
    phase_b._assert_same_identity(actual_h5, phase_a_result["h5_support"], label="CLEAN_HIST_H5")
    phase_b._assert_same_identity(actual_h10, phase_a_result["h10_support"], label="CLEAN_HIST_H10")

    training_dates = derive_training_dates(per_date, folds, phase_b_cfg["accepted_clean_training_date_counts"])
    scores, fit_log = hist.run_models(model_frame, target_ledger, training_dates, folds)
    _require(len(fit_log) == 24, f"CLEAN_HIST_FIT_COUNT_NOT_24:{len(fit_log)}")

    prereg = json.loads(hist.git_bytes(repo_root, "config/ranking_v4_3_preregistration.json").decode("utf-8"))
    fold_metrics, model_summaries, paired_tables, legacy_decision = hist.evaluate_models(scores, target_ledger, folds, prereg)

    challenger_consensus = model_summaries[CHALLENGER]["CONSENSUS"]["aggregate"]
    control_consensus = model_summaries[CONTROL]["CONSENSUS"]["aggregate"]
    clean_score = float(challenger_consensus["median_fold_mean_daily_ic"])
    clean_control = float(control_consensus["median_fold_mean_daily_ic"])
    parent_score = float(cfg["parent_preclean_benchmark"]["challenger_consensus_median_fold_mean_daily_ic"])
    parent_control = float(cfg["parent_preclean_benchmark"]["control_consensus_median_fold_mean_daily_ic"])

    paired_summary: dict[str, Any] = {}
    for head, table in paired_tables.items():
        fold_summary, aggregate = hist.summarize_paired_deltas(table)
        paired_summary[head] = {"fold_summary": fold_summary.to_dict("records"), "aggregate": aggregate}

    outputs: dict[str, Path] = {"access_boundary": boundary_path}
    training_path = output_dir / "clean_training_date_sets.csv"
    fit_path = output_dir / "clean_fit_log.csv"
    target_path = output_dir / "clean_target_ledger.parquet"
    training_dates.to_csv(training_path, index=False, lineterminator="\n")
    fit_log.to_csv(fit_path, index=False, lineterminator="\n")
    target_ledger.to_parquet(target_path, index=False)
    outputs.update(training_dates=training_path, fit_log=fit_path, target_ledger=target_path)

    for mode in (CONTROL, CHALLENGER):
        score_path = output_dir / f"clean_{mode.lower()}_validation_scores.parquet"
        scores[mode].to_parquet(score_path, index=False)
        outputs[f"scores_{mode.lower()}"] = score_path
        for head in ("H5", "H10", "CONSENSUS"):
            metric_path = output_dir / f"clean_{mode.lower()}_{head.lower()}_date_metrics.csv"
            fold_metrics[mode][head].to_csv(metric_path, index=False, lineterminator="\n")
            outputs[f"metrics_{mode.lower()}_{head.lower()}"] = metric_path
    for head, table in paired_tables.items():
        path = output_dir / f"clean_paired_{head.lower()}_date_deltas.csv"
        table.to_csv(path, index=False, lineterminator="\n")
        outputs[f"paired_{head.lower()}"] = path

    summary = {
        "schema_version": "ranking_v4_x1_clean_historical_oos_replay_result_v1",
        "generation_id": cfg["generation_id"],
        "status": "V4_X1_CLEAN_HISTORICAL_OOS_REPLAY_COMPLETE_REVIEW_REQUIRED",
        "measurement_only": True,
        "post_selection_diagnostic": True,
        "canonical_historical_score_metric": "CHALLENGER_CONSENSUS_MEDIAN_FOLD_MEAN_DAILY_IC",
        "canonical_clean_historical_oos_ic": clean_score,
        "parent_preclean_historical_oos_ic": parent_score,
        "absolute_delta_vs_parent": clean_score - parent_score,
        "relative_delta_vs_parent": (clean_score / parent_score - 1.0) if parent_score != 0 else None,
        "control_clean_consensus_ic": clean_control,
        "control_parent_consensus_ic": parent_control,
        "control_absolute_delta_vs_parent": clean_control - parent_control,
        "fit_count": int(len(fit_log)),
        "validation_dates": int(folds["date"].nunique()),
        "validation_folds": 6,
        "validation_dates_per_fold": 100,
        "frozen_validation_end": {"session_index": max_validation_index, "date": max_validation_date.strftime("%Y-%m-%d")},
        "clean_support_identity_exact_match": {"H5": True, "H10": True},
        "model_summaries": model_summaries,
        "paired_summaries": paired_summary,
        "legacy_gate_decision_diagnostic_only": legacy_decision,
        "parent_preclean_benchmark": cfg["parent_preclean_benchmark"],
        "parent_price_evidence": parent_price_stats,
        "clean_price_evidence": clean_price_stats,
        "clean_model_frame": model_frame_stats,
        "historical_target_loaded": True,
        "historical_model_fit": True,
        "historical_oos_predictions_generated": True,
        "historical_performance_computed": True,
        "provider_calls": False,
        "network_calls": False,
        "protected_forward_accessed": False,
        "fresh_forward_accessed": False,
        "forward_counter_mutated": False,
        "deployed_model_mutated": False,
        "model_change_authorized": False,
        "next": "INDEPENDENT_REVIEW; IF VALID, USE CLEAN IC AS CANONICAL HISTORICAL SCORE; DO NOT RETUNE OR TOUCH FORWARD COUNTER",
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(hist.json_safe(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    outputs["summary"] = summary_path

    output_hashes = {name: hist.sha256_file(path) for name, path in outputs.items()}
    manifest = {
        "schema_version": "ranking_v4_x1_clean_historical_oos_replay_manifest_v1",
        "generation_id": cfg["generation_id"],
        "status": summary["status"],
        "measurement_only": True,
        "post_selection_diagnostic": True,
        "git": {
            "head": hist.git_output(repo_root, "rev-parse", "HEAD"),
            "branch": hist.git_output(repo_root, "rev-parse", "--abbrev-ref", "HEAD"),
            "runner_blob": hist.git_output(repo_root, "rev-parse", f"HEAD:{SELF_PATH}"),
            "config_blob": hist.git_output(repo_root, "rev-parse", "HEAD:config/ranking_v4_x1_clean_historical_oos_replay_v1.json"),
            "worktree_clean_before_run": True,
        },
        "runtime": runtime,
        "phase_a_acceptance": acceptance,
        "accepted_phase_a_manifest_sha256": phase_a_result["manifest_sha256"],
        "input_hashes": input_hashes,
        "corporate_action_hashes": ca_hashes,
        "validation_folds_sha256": folds_sha,
        "max_historical_signal_session_index": max_validation_index,
        "max_historical_signal_date": max_validation_date.strftime("%Y-%m-%d"),
        "required_fit_count": 24,
        "actual_fit_count": int(len(fit_log)),
        "canonical_clean_historical_oos_ic": clean_score,
        "parent_preclean_historical_oos_ic": parent_score,
        "output_hashes": output_hashes,
        "provider_calls": False,
        "network_calls": False,
        "protected_forward_accessed": False,
        "fresh_forward_accessed": False,
        "forward_counter_mutated": False,
        "deployed_model_mutated": False,
        "model_change_authorized": False,
        "next": summary["next"],
    }
    manifest_path = output_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(hist.json_safe(manifest), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({
        "status": summary["status"],
        "fit_count": int(len(fit_log)),
        "clean_historical_oos_ic": clean_score,
        "parent_preclean_historical_oos_ic": parent_score,
        "absolute_delta": clean_score - parent_score,
        "relative_delta": (clean_score / parent_score - 1.0) if parent_score != 0 else None,
        "control_clean_consensus_ic": clean_control,
        "forward_counter_mutated": False,
        "deployed_model_mutated": False,
        "protected_forward_accessed": False,
        "manifest": str(manifest_path),
        "manifest_sha256": hist.sha256_file(manifest_path),
        "next": summary["next"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
