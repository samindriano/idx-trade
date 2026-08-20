"""Freeze the clean V4-X1 four-model final refit after accepted Phase A.

This runner is intentionally narrower than the historical V4-3R one-shot.
It may materialize the already-consumed historical H5/H10 training targets and
fit exactly four models (CONTROL/CHALLENGER x H5/H10), but it must never score
historical dates, recompute historical performance, access protected/fresh
forward outcomes, call providers/network, or mutate the forward counter.

The clean representation is inherited exactly from the accepted Phase-A
Open-lineage remediation: clean panel + clean security master + parent
executable Open preserved outside the frozen 1,657 Stage-A candidates.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import joblib
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

PHASE_A_RUNNER = REPO_ROOT / "scripts" / "run_v4_x1_clean_phase_a_structural_replay.py"
OPEN_REMEDIATION_RUNNER = REPO_ROOT / "scripts" / "run_v4_x1_clean_phase_a_open_lineage_remediation.py"
PARENT_FINAL_REFIT_RUNNER = REPO_ROOT / "scripts" / "run_v4_x1_final_refit_freeze.py"
HISTORICAL_RUNNER = REPO_ROOT / "scripts" / "run_v4_3r_historical_one_shot.py"
DEFAULT_CONFIG = REPO_ROOT / "config" / "ranking_v4_x1_clean_phase_b_final_refit_v1.json"
SELF_PATH = "scripts/run_v4_x1_clean_phase_b_final_refit.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"V4_X1_CLEAN_PHASE_B_IMPORT_FAILED:{name}:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


phase_a = _load_module("v4_x1_clean_phase_a_frozen", PHASE_A_RUNNER)
open_fix = _load_module("v4_x1_clean_open_lineage_frozen", OPEN_REMEDIATION_RUNNER)
parent_refit = _load_module("v4_x1_parent_final_refit_frozen", PARENT_FINAL_REFIT_RUNNER)
hist = _load_module("v4_3r_historical_frozen_for_clean_x1", HISTORICAL_RUNNER)

from idx_trade.ranking_v4_3_model_eval import (  # noqa: E402
    CHALLENGER,
    CONTROL,
    fit_v4_head,
    model_feature_columns,
)
from idx_trade.ranking_v4_3_target_execution import (  # noqa: E402
    TARGET_H10_AVAILABLE,
    TARGET_H5_AVAILABLE,
    materialize_v4_target_ledger,
)


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


def verify_config(repo_root: Path, config_path: Path, cfg: dict[str, Any]) -> None:
    expected = (repo_root / "config" / "ranking_v4_x1_clean_phase_b_final_refit_v1.json").resolve()
    if config_path.resolve() != expected:
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_NONCANONICAL_CONFIG")
    if cfg.get("schema_version") != "ranking_v4_x1_clean_phase_b_final_refit_v1":
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_CONFIG_SCHEMA_INVALID")
    if cfg.get("generation_id") != "V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1":
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_GENERATION_INVALID")
    if int(cfg.get("required_fit_count", -1)) != 4:
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_FIT_COUNT_CHANGED")
    if cfg.get("final_training_policy") != "ALL_CA80_HEAD_ELIGIBLE_DATES_THROUGH_FROZEN_V4_3R_END":
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_TRAINING_POLICY_CHANGED")
    if cfg.get("phase_b_refit_execution_authorized") is not True:
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_EXECUTION_NOT_AUTHORIZED")
    guards = cfg.get("hard_guards") or {}
    required_false = (
        "provider_calls_authorized",
        "network_calls_authorized",
        "historical_prediction_generation_authorized",
        "historical_performance_recomputation_authorized",
        "model_scoring_authorized",
        "protected_forward_access_authorized",
        "fresh_forward_access_authorized",
        "forward_counter_mutation_authorized",
        "prospective_scoring_authorized",
        "v4_x2_session_semantics_authorized",
        "ca80_threshold_change_authorized",
        "hyperparameter_search_authorized",
        "data_repair_or_rescue_authorized",
    )
    for key in required_false:
        if guards.get(key) is not False:
            raise RuntimeError(f"V4_X1_CLEAN_PHASE_B_GUARD_CHANGED:{key}")
    if guards.get("historical_training_target_access_authorized") is not True:
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_TRAINING_TARGET_NOT_AUTHORIZED")
    if guards.get("model_fit_authorized") is not True:
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_MODEL_FIT_NOT_AUTHORIZED")


def verify_git_blobs(repo_root: Path, mapping: dict[str, str]) -> dict[str, str]:
    actual: dict[str, str] = {}
    for relative, expected in mapping.items():
        blob = hist.git_output(repo_root, "rev-parse", f"HEAD:{relative}")
        if blob != str(expected):
            raise RuntimeError(
                f"V4_X1_CLEAN_PHASE_B_GIT_BLOB_CHANGED:{relative}:{blob}!={expected}"
            )
        actual[relative] = blob
    return actual


def verify_phase_a_acceptance(repo_root: Path, cfg: dict[str, Any]) -> dict[str, str]:
    spec = cfg["phase_a_acceptance"]
    actual = hist.git_output(
        repo_root,
        "rev-parse",
        f"{spec['git_ref']}:{spec['path']}",
    )
    if actual != str(spec["git_blob_sha1"]):
        raise RuntimeError(
            f"V4_X1_CLEAN_PHASE_B_ACCEPTANCE_BLOB_MISMATCH:{actual}!={spec['git_blob_sha1']}"
        )
    return {
        "git_ref": str(spec["git_ref"]),
        "path": str(spec["path"]),
        "git_blob_sha1": actual,
    }


def _require_sha(path: Path, expected: str, label: str) -> str:
    actual = hist.sha256_file(path)
    if actual != str(expected):
        raise RuntimeError(
            f"V4_X1_CLEAN_PHASE_B_SHA_MISMATCH:{label}:{actual}!={expected}"
        )
    return actual


def _canonical_identity(frame: pd.DataFrame, *, label: str) -> pd.DataFrame:
    out = phase_a.normalize_identity(frame, label=label)[["ticker", "date"]].copy()
    if out.duplicated(["ticker", "date"]).any():
        raise RuntimeError(f"V4_X1_CLEAN_PHASE_B_DUPLICATE_IDENTITY:{label}")
    return out.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)


def _assert_same_identity(actual: pd.DataFrame, expected: pd.DataFrame, *, label: str) -> None:
    left = _canonical_identity(actual, label=f"{label}_ACTUAL")
    right = _canonical_identity(expected, label=f"{label}_EXPECTED")
    if not left.equals(right):
        left_set = set(map(tuple, left.assign(date=left["date"].dt.strftime("%Y-%m-%d")).to_numpy()))
        right_set = set(map(tuple, right.assign(date=right["date"].dt.strftime("%Y-%m-%d")).to_numpy()))
        raise RuntimeError(
            f"V4_X1_CLEAN_PHASE_B_SUPPORT_IDENTITY_MISMATCH:{label}:"
            f"ADD={len(left_set-right_set)}:DROP={len(right_set-left_set)}"
        )


def verify_phase_a_root(root: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    spec = cfg["accepted_phase_a_runtime"]
    manifest_path = root / "MANIFEST.json"
    manifest_sha = _require_sha(
        manifest_path, str(spec["manifest_sha256"]), "accepted_phase_a_manifest"
    )
    manifest = hist.read_json(manifest_path, "V4_X1_CLEAN_PHASE_B_PHASE_A_MANIFEST")
    if manifest.get("status") != str(spec["status"]):
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_PHASE_A_STATUS_CHANGED")
    remediation = manifest.get("open_lineage_remediation") or {}
    if remediation.get("policy_id") != str(spec["open_lineage_policy"]):
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_OPEN_LINEAGE_POLICY_CHANGED")

    files = {
        "summary": root / "summary.json",
        "per_date": root / "clean_ca80_support_per_date.csv",
        "h5_support": root / "clean_h5_support_identities.csv",
        "h10_support": root / "clean_h10_support_identities.csv",
        "training_counts": root / "clean_training_date_counts.csv",
    }
    output_keys = {
        "summary": "summary",
        "per_date": "per_date",
        "h5_support": "clean_h5_support",
        "h10_support": "clean_h10_support",
        "training_counts": "training_counts",
    }
    output_hashes = manifest.get("output_hashes") or {}
    verified_hashes: dict[str, str] = {}
    for name, path in files.items():
        expected = str(output_hashes.get(output_keys[name]) or "")
        if not expected:
            raise RuntimeError(f"V4_X1_CLEAN_PHASE_B_PHASE_A_CHILD_HASH_MISSING:{name}")
        verified_hashes[name] = _require_sha(path, expected, f"phase_a_{name}")

    summary = hist.read_json(files["summary"], "V4_X1_CLEAN_PHASE_B_PHASE_A_SUMMARY")
    if summary.get("status") != str(spec["status"]):
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_PHASE_A_SUMMARY_STATUS_CHANGED")
    if summary.get("clean_ca80_gate_pass") is not True:
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_PHASE_A_CA80_NOT_PASS")
    frozen = summary.get("clean_frozen_support") or {}
    if frozen.get("all_frozen_600_full_target_eligible") is not True:
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_FROZEN_600_NOT_ELIGIBLE")
    if frozen.get("tail_600_identity_unchanged") is not True:
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_TAIL_600_CHANGED")
    if int(frozen.get("eligible_sessions_after_frozen_end", -1)) != 0:
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_ELIGIBLE_AFTER_FROZEN_END")
    for key in (
        "provider_calls", "network_calls", "model_fit", "model_scoring",
        "historical_predictions_accessed", "historical_performance_accessed",
        "protected_forward_accessed", "fresh_forward_accessed",
        "counter_mutated", "data_mutated",
    ):
        if summary.get(key) is not False:
            raise RuntimeError(f"V4_X1_CLEAN_PHASE_B_PHASE_A_SAFETY_CHANGED:{key}")
    summary_remediation = summary.get("open_lineage_remediation") or {}
    if summary_remediation.get("policy_id") != str(spec["open_lineage_policy"]):
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_PHASE_A_SUMMARY_OPEN_POLICY_CHANGED")

    per_date = pd.read_csv(files["per_date"])
    per_date["date"] = pd.to_datetime(per_date["date"], errors="raise").dt.normalize()
    per_date["session_index"] = pd.to_numeric(per_date["session_index"], errors="raise").astype(int)
    for head in ("h5", "h10", "consensus"):
        per_date[f"{head}_eligible"] = parent_refit.strict_bool(
            per_date[f"{head}_eligible"], label=f"clean_{head}_eligible"
        )
    if per_date.duplicated(["session_index", "date"]).any():
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_PHASE_A_PER_DATE_DUPLICATE")

    h5_support = _canonical_identity(pd.read_csv(files["h5_support"]), label="PHASE_A_H5_SUPPORT")
    h10_support = _canonical_identity(pd.read_csv(files["h10_support"]), label="PHASE_A_H10_SUPPORT")
    expected_rows = cfg["accepted_clean_support_rows"]
    if len(h5_support) != int(expected_rows["H5"]) or len(h10_support) != int(expected_rows["H10"]):
        raise RuntimeError(
            f"V4_X1_CLEAN_PHASE_B_PHASE_A_SUPPORT_ROWS_CHANGED:{len(h5_support)}:{len(h10_support)}"
        )

    counts_frame = pd.read_csv(files["training_counts"])
    counts = {
        str(row.fold_head): int(row.clean_training_dates)
        for row in counts_frame.itertuples(index=False)
    }
    expected_counts = {str(k): int(v) for k, v in cfg["accepted_clean_training_date_counts"].items()}
    if counts != expected_counts:
        raise RuntimeError(
            f"V4_X1_CLEAN_PHASE_B_TRAINING_DATE_COUNTS_CHANGED:{counts}!={expected_counts}"
        )

    return {
        "manifest_sha256": manifest_sha,
        "output_hashes": verified_hashes,
        "summary": summary,
        "per_date": per_date,
        "h5_support": h5_support,
        "h10_support": h10_support,
        "training_date_counts": counts,
    }


def verify_external_inputs(args: argparse.Namespace, cfg: dict[str, Any]) -> tuple[dict[str, Path], dict[str, str]]:
    paths = {
        "calendar": args.artifact_root / "official_exchange_sessions_1260.csv",
        "old_panel": args.artifact_root / "unknown_state_diagnostic_1260_20260809" / "model_safe_signal_research_panel_1260.parquet",
        "anchors": args.artifact_root / "tradability_anchors_1260.csv",
        "intervals": args.artifact_root / "tradability_intervals_1260.csv",
        "old_open_derivative": args.open_derivative_root / "execution_open_candidate_panel_yahoo_tradingview.parquet",
        "old_open_derivative_manifest": args.open_derivative_root / "artifact_manifest.json",
        "old_open_overlay": args.overlay_root / "open_recovery_overlay.parquet",
        "old_open_overlay_manifest": args.overlay_root / "manifest.json",
        "clean_bundle_manifest": args.clean_bundle_manifest.resolve(),
        "clean_panel": args.clean_panel.resolve(),
        "clean_security_master": args.clean_security_master.resolve(),
        "field_provenance": args.field_provenance.resolve(),
        "execution_lock_manifest": args.execution_lock_manifest.resolve(),
    }
    expected = cfg["input_sha256"]
    hashes: dict[str, str] = {}
    for name, path in paths.items():
        hashes[name] = _require_sha(path, str(expected[name]), name)

    bundle = hist.read_json(paths["clean_bundle_manifest"], "V4_X1_CLEAN_PHASE_B_BUNDLE")
    if bundle.get("stage_a_panel_rewritten") is True or bundle.get("stage_a_hlc_open_changed") is True:
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_BUNDLE_STAGE_A_REWRITE_CHANGED")
    return paths, hashes


def target_support_identity(
    target_ledger: pd.DataFrame,
    per_date: pd.DataFrame,
    *,
    head: str,
) -> pd.DataFrame:
    if head == "H5":
        eligible_col = "h5_eligible"
        state_col = "target_state_h5"
        available_state = TARGET_H5_AVAILABLE
    elif head == "H10":
        eligible_col = "h10_eligible"
        state_col = "target_state_h10"
        available_state = TARGET_H10_AVAILABLE
    else:
        raise ValueError(f"V4_X1_CLEAN_PHASE_B_UNSUPPORTED_HEAD:{head}")
    dates = set(per_date.loc[per_date[eligible_col].astype(bool), "date"])
    support = target_ledger.loc[
        target_ledger["date"].isin(dates)
        & target_ledger[state_col].eq(available_state),
        ["ticker", "date"],
    ].copy()
    return _canonical_identity(support, label=f"TARGET_{head}_SUPPORT")


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    config_path = args.config if args.config.is_absolute() else repo_root / args.config
    output_dir = args.output_dir.resolve()

    if output_dir.exists():
        raise RuntimeError(f"V4_X1_CLEAN_PHASE_B_REFUSE_OVERWRITE:{output_dir}")
    if hist.git_output(repo_root, "status", "--porcelain"):
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_GIT_WORKTREE_NOT_CLEAN")

    cfg = hist.read_json(config_path, "V4_X1_CLEAN_PHASE_B_CONFIG")
    verify_config(repo_root, config_path, cfg)
    scientific_blobs = verify_git_blobs(repo_root, cfg["pinned_git_blobs"])
    acceptance = verify_phase_a_acceptance(repo_root, cfg)
    runtime = hist.verify_runtime(repo_root, cfg)
    phase_a_result = verify_phase_a_root(args.phase_a_root.resolve(), cfg)
    paths, input_hashes = verify_external_inputs(args, cfg)

    continuity, ca_hashes = phase_a.load_parent_continuity(
        args.parent_combined_replay_root.resolve(), cfg
    )

    calendar = phase_a.load_calendar(paths["calendar"])
    old_panel = pd.read_parquet(paths["old_panel"])
    clean_panel = pd.read_parquet(paths["clean_panel"])
    derivative = pd.read_parquet(paths["old_open_derivative"])
    overlay = pd.read_parquet(paths["old_open_overlay"])
    anchors = pd.read_csv(paths["anchors"])
    intervals = pd.read_csv(paths["intervals"])
    clean_master = pd.read_csv(paths["clean_security_master"])
    provenance = pd.read_parquet(paths["field_provenance"])

    parent_price, parent_price_stats = phase_a.build_old_price_evidence(
        old_panel, calendar, derivative, overlay, anchors, intervals
    )
    clean_price, clean_price_stats = open_fix.apply_clean_open_lineage(
        parent_price, clean_panel, provenance
    )
    accepted_open_stats = phase_a_result["summary"].get("clean_price_evidence") or {}
    for key in (
        "policy_id", "candidate_rows", "admitted_rows", "fail_closed_rows",
        "non_candidate_rows", "final_open_admitted", "close_admitted",
        "non_candidate_open_value_exact_parity",
        "non_candidate_open_admission_exact_parity",
        "market_state_reused_exactly_from_parent_executable_evidence",
    ):
        if clean_price_stats.get(key) != accepted_open_stats.get(key):
            raise RuntimeError(
                f"V4_X1_CLEAN_PHASE_B_OPEN_LINEAGE_REDERIVATION_CHANGED:{key}:"
                f"{clean_price_stats.get(key)}!={accepted_open_stats.get(key)}"
            )

    model_frame, model_frame_stats = phase_a.build_primary_model_frame(
        clean_panel, calendar, clean_master, clean_price
    )
    if int(len(model_frame)) != int(cfg["accepted_clean_primary_rows"]):
        raise RuntimeError(
            f"V4_X1_CLEAN_PHASE_B_PRIMARY_ROWS_CHANGED:{len(model_frame)}!={cfg['accepted_clean_primary_rows']}"
        )

    continuity_evidence = hist.continuity_evidence_from_parent(
        continuity,
        continuity_sha256=ca_hashes["continuity"],
        parent_manifest_sha256=ca_hashes["manifest"],
    )

    # Historical numeric labels/ranks are authorized only for these final fits.
    # They are never printed, scored historically, or used for performance.
    target_ledger = materialize_v4_target_ledger(
        model_frame[["ticker", "date"]],
        calendar["date"],
        clean_price,
        continuity_evidence,
    )

    per_date = phase_a_result["per_date"]
    actual_h5_support = target_support_identity(target_ledger, per_date, head="H5")
    actual_h10_support = target_support_identity(target_ledger, per_date, head="H10")
    _assert_same_identity(actual_h5_support, phase_a_result["h5_support"], label="H5")
    _assert_same_identity(actual_h10_support, phase_a_result["h10_support"], label="H10")

    training_frames: dict[str, tuple[pd.DataFrame, str]] = {}
    training_dates_parts: list[pd.DataFrame] = []
    for head in ("H5", "H10"):
        train, target_col, dates = parent_refit.final_training_frame(
            model_frame,
            target_ledger,
            per_date,
            head=head,
        )
        training_frames[head] = (train, target_col)
        training_dates_parts.append(dates)

    final_training_dates = pd.concat(training_dates_parts, ignore_index=True).sort_values(
        ["head", "session_index"], kind="mergesort"
    )
    frozen_end_index = int(final_training_dates["session_index"].max())
    eligible_dates = {
        "H5": int(per_date["h5_eligible"].sum()),
        "H10": int(per_date["h10_eligible"].sum()),
    }

    output_dir.mkdir(parents=True, exist_ok=False)
    boundary_path = output_dir / "CLEAN_PHASE_B_FINAL_REFIT_BOUNDARY.json"
    boundary = {
        "schema_version": "ranking_v4_x1_clean_phase_b_final_refit_boundary_v1",
        "generation_id": cfg["generation_id"],
        "status": "V4_X1_CLEAN_PHASE_B_FINAL_REFIT_COMMENCED",
        "git_head": hist.git_output(repo_root, "rev-parse", "HEAD"),
        "accepted_phase_a_manifest_sha256": phase_a_result["manifest_sha256"],
        "historical_training_target_loaded": True,
        "target_ranks_accessed_for_training": True,
        "historical_prediction_generated": False,
        "historical_performance_computed": False,
        "model_scoring_performed": False,
        "protected_forward_accessed": False,
        "fresh_forward_accessed": False,
        "provider_calls": False,
        "network_calls": False,
        "forward_counter_mutated": False,
    }
    boundary_path.write_text(
        json.dumps(boundary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    model_paths: dict[str, Path] = {}
    fit_log: list[dict[str, Any]] = []
    for mode in (CONTROL, CHALLENGER):
        for head in ("H5", "H10"):
            train, target_col = training_frames[head]
            model = fit_v4_head(train, target_column=target_col, mode=mode)
            key = f"{mode.lower()}_{head.lower()}"
            path = output_dir / f"v4_x1_clean_{key}_final.joblib"
            joblib.dump(model, path, compress=0, protocol=5)
            model_paths[key] = path
            fit_log.append(
                {
                    "mode": mode,
                    "head": head,
                    "training_dates": int(train["date"].nunique()),
                    "training_rows": int(len(train)),
                    "target_column": target_col,
                    "feature_count": len(model_feature_columns(mode)),
                    "feature_columns": list(model_feature_columns(mode)),
                }
            )

    if len(fit_log) != 4 or len(model_paths) != 4:
        raise RuntimeError("V4_X1_CLEAN_PHASE_B_DID_NOT_FIT_EXACTLY_FOUR_MODELS")

    training_dates_path = output_dir / "v4_x1_clean_final_training_dates.csv"
    fit_log_path = output_dir / "v4_x1_clean_final_refit_log.json"
    summary_path = output_dir / "summary.json"
    manifest_path = output_dir / "MANIFEST.json"
    final_training_dates.to_csv(training_dates_path, index=False, lineterminator="\n")
    fit_log_path.write_text(
        json.dumps(fit_log, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    summary = {
        "schema_version": "ranking_v4_x1_clean_phase_b_final_refit_result_v1",
        "generation_id": cfg["generation_id"],
        "parent_generation_id": cfg["parent_generation_id"],
        "status": "V4_X1_CLEAN_PHASE_B_FINAL_REFIT_COMPLETE_INDEPENDENT_REVIEW_REQUIRED",
        "fit_count": 4,
        "fit_log": fit_log,
        "eligible_dates": eligible_dates,
        "accepted_clean_support_rows": {
            "H5": int(len(actual_h5_support)),
            "H10": int(len(actual_h10_support)),
        },
        "phase_a_support_identity_exact_match": {"H5": True, "H10": True},
        "historical_training_target_loaded": True,
        "numeric_target_values_accessed_for_training": True,
        "target_ranks_accessed_for_training": True,
        "historical_prediction_generated": False,
        "historical_performance_computed": False,
        "model_scoring_performed": False,
        "protected_forward_accessed": False,
        "fresh_forward_accessed": False,
        "provider_calls": False,
        "network_calls": False,
        "forward_counter_mutated": False,
        "prospective_scoring_authorized": False,
        "phase_a_manifest_sha256": phase_a_result["manifest_sha256"],
        "phase_a_acceptance": acceptance,
        "parent_price_evidence": parent_price_stats,
        "clean_price_evidence": clean_price_stats,
        "clean_model_frame": model_frame_stats,
        "frozen_historical_end_session_index": frozen_end_index,
        "next": "INDEPENDENT_REVIEW_ONLY; DO_NOT SCORE PROSPECTIVELY OR MUTATE FORWARD COUNTER UNTIL ACCEPTED",
    }
    summary_path.write_text(
        json.dumps(hist.json_safe(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    outputs: dict[str, Path] = {
        "boundary": boundary_path,
        "training_dates": training_dates_path,
        "fit_log": fit_log_path,
        "summary": summary_path,
        **{f"model_{key}": path for key, path in model_paths.items()},
    }
    output_hashes = {name: hist.sha256_file(path) for name, path in outputs.items()}
    manifest = {
        "schema_version": "ranking_v4_x1_clean_phase_b_final_refit_manifest_v1",
        "generation_id": cfg["generation_id"],
        "parent_generation_id": cfg["parent_generation_id"],
        "status": summary["status"],
        "git": {
            "head": hist.git_output(repo_root, "rev-parse", "HEAD"),
            "branch": hist.git_output(repo_root, "rev-parse", "--abbrev-ref", "HEAD"),
            "runner_blob": hist.git_output(repo_root, "rev-parse", f"HEAD:{SELF_PATH}"),
            "config_blob": hist.git_output(
                repo_root, "rev-parse", "HEAD:config/ranking_v4_x1_clean_phase_b_final_refit_v1.json"
            ),
            "worktree_clean_before_run": True,
        },
        "runtime": runtime,
        "scientific_git_blobs": scientific_blobs,
        "phase_a_acceptance": acceptance,
        "accepted_phase_a_manifest_sha256": phase_a_result["manifest_sha256"],
        "phase_a_output_hashes": phase_a_result["output_hashes"],
        "input_hashes": input_hashes,
        "corporate_action_hashes": ca_hashes,
        "training_policy": cfg["final_training_policy"],
        "required_fit_count": 4,
        "phase_a_support_identity_exact_match": {"H5": True, "H10": True},
        "historical_training_target_loaded": True,
        "target_ranks_accessed_for_training": True,
        "historical_prediction_generated": False,
        "historical_performance_computed": False,
        "model_scoring_performed": False,
        "protected_forward_accessed": False,
        "fresh_forward_accessed": False,
        "provider_calls": False,
        "network_calls": False,
        "forward_counter_mutated": False,
        "prospective_scoring_authorized": False,
        "output_hashes": output_hashes,
        "next": summary["next"],
    }
    manifest_path.write_text(
        json.dumps(hist.json_safe(manifest), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "status": summary["status"],
                "fit_count": 4,
                "eligible_dates": eligible_dates,
                "phase_a_support_identity_exact_match": {"H5": True, "H10": True},
                "historical_prediction_generated": False,
                "historical_performance_computed": False,
                "model_scoring_performed": False,
                "protected_forward_accessed": False,
                "fresh_forward_accessed": False,
                "provider_calls": False,
                "network_calls": False,
                "forward_counter_mutated": False,
                "prospective_scoring_authorized": False,
                "manifest": str(manifest_path),
                "manifest_sha256": hist.sha256_file(manifest_path),
                "next": summary["next"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
