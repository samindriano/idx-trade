"""Freeze the four final V4-X1 models for prospective-only confirmation.

This runner may use the already-consumed V4-3R historical target corpus for
training, but it must not generate historical predictions or recompute any
historical performance. A successful run fits exactly four models:
CONTROL/CHALLENGER x H5/H10. The resulting model bytes are immutable inputs
to the future V4-X1 prospective score-capture lane.
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

HISTORICAL_RUNNER = REPO_ROOT / "scripts" / "run_v4_3r_historical_one_shot.py"
DEFAULT_CONFIG = REPO_ROOT / "config" / "ranking_v4_x1_final_refit_v1.json"
SELF_PATH = "scripts/run_v4_x1_final_refit_freeze.py"


def _load_historical_runner():
    spec = importlib.util.spec_from_file_location(
        "v4_3r_historical_frozen_for_x1_refit",
        HISTORICAL_RUNNER,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("V4_X1_HISTORICAL_RUNNER_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


hist = _load_historical_runner()

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
    parser.add_argument("--historical-result-root", type=Path, required=True)
    parser.add_argument("--execution-freeze-root", type=Path, required=True)
    parser.add_argument("--prefit-root", type=Path, required=True)
    parser.add_argument("--parent-combined-replay-root", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--open-derivative-root", type=Path, required=True)
    parser.add_argument("--overlay-root", type=Path, required=True)
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def strict_bool(series: pd.Series, *, label: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series.dtype):
        return series.astype(bool)
    normalized = series.astype(str).str.strip().str.lower()
    allowed = {"true", "false"}
    seen = set(normalized.dropna().unique())
    if not seen.issubset(allowed):
        raise RuntimeError(f"V4_X1_INVALID_BOOLEAN:{label}:{sorted(seen)}")
    return normalized.eq("true")


def verify_config(repo_root: Path, config_path: Path, cfg: dict[str, Any]) -> None:
    expected_path = (repo_root / "config" / "ranking_v4_x1_final_refit_v1.json").resolve()
    if config_path.resolve() != expected_path:
        raise RuntimeError("V4_X1_REFIT_NONCANONICAL_CONFIG_PATH")
    if cfg.get("schema_version") != "ranking_v4_x1_final_refit_v1":
        raise RuntimeError("V4_X1_REFIT_CONFIG_SCHEMA_INVALID")
    if cfg.get("generation_id") != "V4_X1_GEOMETRY3_PROSPECTIVE":
        raise RuntimeError("V4_X1_REFIT_GENERATION_INVALID")
    if int(cfg.get("required_fit_count", -1)) != 4:
        raise RuntimeError("V4_X1_REFIT_FIT_COUNT_CHANGED")
    if cfg.get("historical_performance_recomputation_authorized") is not False:
        raise RuntimeError("V4_X1_HISTORICAL_PERFORMANCE_UNEXPECTEDLY_AUTHORIZED")
    if cfg.get("historical_prediction_generation_authorized") is not False:
        raise RuntimeError("V4_X1_HISTORICAL_PREDICTION_UNEXPECTEDLY_AUTHORIZED")
    if cfg.get("protected_forward_access_authorized") is not False:
        raise RuntimeError("V4_X1_PROTECTED_FORWARD_UNEXPECTEDLY_AUTHORIZED")
    if cfg.get("provider_calls_authorized") is not False:
        raise RuntimeError("V4_X1_PROVIDER_UNEXPECTEDLY_AUTHORIZED")
    if cfg.get("final_training_policy") != "ALL_CA80_HEAD_ELIGIBLE_DATES_THROUGH_FROZEN_V4_3R_END":
        raise RuntimeError("V4_X1_FINAL_TRAINING_POLICY_CHANGED")


def verify_scientific_blobs(repo_root: Path, cfg: dict[str, Any]) -> dict[str, str]:
    actual: dict[str, str] = {}
    for relative, expected in cfg["scientific_git_blobs"].items():
        blob = hist.git_output(repo_root, "rev-parse", f"HEAD:{relative}")
        if blob != expected:
            raise RuntimeError(
                f"V4_X1_SCIENTIFIC_BLOB_CHANGED:{relative}:{blob}!={expected}"
            )
        actual[relative] = blob
    prereg = cfg["x1_preregistration"]
    prereg_blob = hist.git_output(repo_root, "rev-parse", f"HEAD:{prereg['path']}")
    if prereg_blob != prereg["git_blob_sha1"]:
        raise RuntimeError(
            f"V4_X1_PREREGISTRATION_BLOB_CHANGED:{prereg_blob}!={prereg['git_blob_sha1']}"
        )
    actual[prereg["path"]] = prereg_blob
    return actual


def verify_historical_parent(root: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    manifest_path = root / "MANIFEST.json"
    summary_path = root / "summary.json"
    actual_manifest = hist.sha256_file(manifest_path)
    expected = cfg["historical_selection_parent"]
    if actual_manifest != expected["manifest_sha256"]:
        raise RuntimeError(
            f"V4_X1_HISTORICAL_PARENT_MANIFEST_MISMATCH:{actual_manifest}!={expected['manifest_sha256']}"
        )
    manifest = hist.read_json(manifest_path, "V4_X1_HISTORICAL_PARENT_MANIFEST")
    if manifest.get("status") != expected["status"]:
        raise RuntimeError("V4_X1_HISTORICAL_PARENT_MANIFEST_STATUS_CHANGED")
    actual_summary = hist.sha256_file(summary_path)
    expected_summary = str((manifest.get("output_hashes") or {}).get("summary") or "")
    if not expected_summary or actual_summary != expected_summary:
        raise RuntimeError(
            f"V4_X1_HISTORICAL_PARENT_SUMMARY_SHA_MISMATCH:{actual_summary}!={expected_summary}"
        )
    summary = hist.read_json(summary_path, "V4_X1_HISTORICAL_PARENT_SUMMARY")
    if summary.get("status") != expected["status"]:
        raise RuntimeError("V4_X1_HISTORICAL_PARENT_STATUS_CHANGED")
    decision = summary.get("decision") or {}
    if decision.get("verdict") != expected["status"]:
        raise RuntimeError("V4_X1_HISTORICAL_PARENT_DECISION_CHANGED")
    if summary.get("protected_forward_accessed") is not False:
        raise RuntimeError("V4_X1_HISTORICAL_PARENT_PROTECTED_FORWARD_ACCESSED")
    if summary.get("provider_calls") is not False:
        raise RuntimeError("V4_X1_HISTORICAL_PARENT_PROVIDER_CALLS")
    if int(summary.get("fit_count", -1)) != 24:
        raise RuntimeError("V4_X1_HISTORICAL_PARENT_FIT_COUNT_CHANGED")
    parity = summary.get("target_support_parity_mismatches") or {}
    if parity != {"consensus": 0, "h10": 0, "h5": 0}:
        raise RuntimeError(f"V4_X1_HISTORICAL_PARENT_PARITY_CHANGED:{parity}")
    return {
        "manifest_sha256": actual_manifest,
        "summary_sha256": actual_summary,
        "status": summary["status"],
    }


def load_prefit_per_date(root: Path) -> tuple[pd.DataFrame, str]:
    manifest = hist.read_json(root / "MANIFEST.json", "V4_X1_PREFIT_MANIFEST")
    path = root / "v4_3r_ca80_full_target_support_per_date.csv"
    actual = hist.sha256_file(path)
    expected = str((manifest.get("output_hashes") or {}).get("per_date") or "")
    if not expected or actual != expected:
        raise RuntimeError(
            f"V4_X1_PREFIT_PER_DATE_SHA_MISMATCH:{actual}!={expected}"
        )
    frame = pd.read_csv(path)
    frame["session_index"] = pd.to_numeric(
        frame["session_index"], errors="raise"
    ).astype(int)
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    for head in ("h5", "h10", "consensus"):
        frame[f"{head}_eligible"] = strict_bool(
            frame[f"{head}_eligible"], label=f"{head}_eligible"
        )
    if frame.duplicated(["session_index", "date"]).any():
        raise RuntimeError("V4_X1_PREFIT_PER_DATE_DUPLICATE_IDENTITY")
    return frame, actual


def final_training_frame(
    model_frame: pd.DataFrame,
    target_ledger: pd.DataFrame,
    per_date: pd.DataFrame,
    *,
    head: str,
) -> tuple[pd.DataFrame, str, pd.DataFrame]:
    if head == "H5":
        eligible_col = "h5_eligible"
        state_col = "target_state_h5"
        available_state = TARGET_H5_AVAILABLE
        target_col = "target_rank_h5"
    elif head == "H10":
        eligible_col = "h10_eligible"
        state_col = "target_state_h10"
        available_state = TARGET_H10_AVAILABLE
        target_col = "target_rank_h10"
    else:
        raise ValueError(f"V4_X1_UNSUPPORTED_HEAD:{head}")

    dates = per_date.loc[
        per_date[eligible_col], ["session_index", "date"]
    ].copy()
    if dates.empty:
        raise RuntimeError(f"V4_X1_NO_ELIGIBLE_DATES:{head}")
    date_set = set(dates["date"])
    target_rows = target_ledger.loc[
        target_ledger["date"].isin(date_set)
        & target_ledger[state_col].eq(available_state),
        ["ticker", "date", target_col],
    ].copy()
    if target_rows.empty:
        raise RuntimeError(f"V4_X1_NO_TARGET_ROWS:{head}")
    train = target_rows.merge(
        model_frame,
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )
    if train[target_col].isna().any():
        raise RuntimeError(f"V4_X1_TRAINING_TARGET_MISSING:{head}")
    if int(train["date"].nunique()) != len(dates):
        raise RuntimeError(
            f"V4_X1_TRAINING_DATE_COUNT_MISMATCH:{head}:{train['date'].nunique()}!={len(dates)}"
        )
    dates["head"] = head
    return train, target_col, dates[["head", "session_index", "date"]]


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    output_dir = args.output_dir.resolve()
    config_path = args.config if args.config.is_absolute() else repo_root / args.config

    if output_dir.exists():
        raise RuntimeError(f"V4_X1_REFUSE_OVERWRITE_EXISTING_OUTPUT:{output_dir}")
    if hist.git_output(repo_root, "status", "--porcelain"):
        raise RuntimeError("V4_X1_GIT_WORKTREE_NOT_CLEAN")

    cfg = hist.read_json(config_path, "V4_X1_REFIT_CONFIG")
    verify_config(repo_root, config_path, cfg)
    scientific_blobs = verify_scientific_blobs(repo_root, cfg)
    historical_parent = verify_historical_parent(
        args.historical_result_root.resolve(), cfg
    )

    runtime = hist.verify_runtime(repo_root, cfg)
    hist.verify_execution_freeze(args.execution_freeze_root.resolve(), cfg)
    _, prefit_hashes = hist.verify_prefit(args.prefit_root.resolve(), cfg)
    per_date, per_date_sha = load_prefit_per_date(args.prefit_root.resolve())
    combined, continuity, parent_hashes = hist.verify_parent_combined(
        args.parent_combined_replay_root.resolve(), cfg
    )
    paths, market_hashes = hist.load_frozen_market_inputs(args, cfg)
    folds, folds_sha = hist.load_validation_folds(repo_root, cfg)

    frozen_end_index = int(folds["session_index"].max())
    frozen_end_date = pd.Timestamp(
        folds.loc[folds["session_index"].idxmax(), "date"]
    ).normalize()
    eligible_after = {
        head: int(
            (
                per_date[f"{head}_eligible"]
                & per_date["session_index"].gt(frozen_end_index)
            ).sum()
        )
        for head in ("h5", "h10", "consensus")
    }
    if any(eligible_after.values()):
        raise RuntimeError(
            f"V4_X1_ELIGIBLE_DATE_AFTER_FROZEN_END:{eligible_after}"
        )
    expected_eligible = cfg["expected_head_eligible_dates"]
    actual_eligible = {
        "H5": int(per_date["h5_eligible"].sum()),
        "H10": int(per_date["h10_eligible"].sum()),
    }
    if actual_eligible != {
        "H5": int(expected_eligible["H5"]),
        "H10": int(expected_eligible["H10"]),
    }:
        raise RuntimeError(
            f"V4_X1_ELIGIBLE_DATE_COUNT_CHANGED:{actual_eligible}!={expected_eligible}"
        )

    calendar = pd.read_csv(paths["calendar"])
    calendar["date"] = pd.to_datetime(
        calendar["date"], errors="coerce"
    ).dt.normalize()
    if calendar["date"].isna().any() or calendar["date"].duplicated().any():
        raise RuntimeError("V4_X1_OFFICIAL_CALENDAR_INVALID")
    calendar = calendar.sort_values("date", kind="mergesort").reset_index(drop=True)
    calendar["session_index"] = np.arange(len(calendar), dtype=np.int64)

    panel = hist.normalize_identity(pd.read_parquet(paths["panel"]))
    derivative = pd.read_parquet(paths["open_derivative_panel"])
    overlay = pd.read_parquet(paths["overlay_parquet"])
    anchors = pd.read_csv(paths["anchors"])
    intervals = pd.read_csv(paths["intervals"])
    security_master = pd.read_csv(paths["security_master"])

    features, pit_diagnostics = hist.build_v4_control_feature_table(
        panel,
        calendar["date"],
        security_master,
    )
    price_evidence, price_stats = hist.build_price_evidence(
        panel,
        calendar,
        derivative,
        overlay,
        anchors,
        intervals,
    )
    model_frame = hist.prepare_model_frame(features, combined, price_evidence)
    continuity_evidence = hist.continuity_evidence_from_parent(
        continuity,
        continuity_sha256=parent_hashes["continuity"],
        parent_manifest_sha256=parent_hashes["manifest"],
    )

    # Historical labels are used for final training only. X1 does not score
    # any historical date and does not compute any historical performance.
    target_ledger = materialize_v4_target_ledger(
        combined[["ticker", "date"]],
        calendar["date"],
        price_evidence,
        continuity_evidence,
    )
    parity = hist.assert_target_support_parity(target_ledger, combined)

    training_frames: dict[str, tuple[pd.DataFrame, str]] = {}
    training_dates_parts: list[pd.DataFrame] = []
    for head in ("H5", "H10"):
        train, target_col, dates = final_training_frame(
            model_frame,
            target_ledger,
            per_date,
            head=head,
        )
        training_frames[head] = (train, target_col)
        training_dates_parts.append(dates)
    final_training_dates = pd.concat(
        training_dates_parts, ignore_index=True
    ).sort_values(["head", "session_index"], kind="mergesort")

    # No prospective scoring is authorized unless this run reaches a complete
    # manifest with exactly four model files.
    output_dir.mkdir(parents=True)
    boundary_path = output_dir / "FINAL_REFIT_BOUNDARY.json"
    boundary = {
        "schema_version": "ranking_v4_x1_final_refit_boundary_v1",
        "generation_id": cfg["generation_id"],
        "status": "V4_X1_FINAL_REFIT_COMMENCED",
        "git_head": hist.git_output(repo_root, "rev-parse", "HEAD"),
        "historical_training_target_loaded": True,
        "historical_prediction_generated": False,
        "historical_performance_computed": False,
        "protected_forward_accessed": False,
        "provider_calls": False,
        "frozen_historical_signal_end_session_index": frozen_end_index,
        "frozen_historical_signal_end_date": frozen_end_date.strftime("%Y-%m-%d"),
    }
    boundary_path.write_text(
        json.dumps(boundary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    model_paths: dict[str, Path] = {}
    fit_log: list[dict[str, object]] = []
    for mode in (CONTROL, CHALLENGER):
        for head in ("H5", "H10"):
            train, target_col = training_frames[head]
            model = fit_v4_head(train, target_column=target_col, mode=mode)
            path = output_dir / f"v4_x1_{mode.lower()}_{head.lower()}_final.joblib"
            joblib.dump(model, path, compress=0, protocol=5)
            model_paths[f"{mode.lower()}_{head.lower()}"] = path
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
        raise RuntimeError("V4_X1_FINAL_REFIT_DID_NOT_PRODUCE_EXACTLY_FOUR_MODELS")

    training_dates_path = output_dir / "v4_x1_final_training_dates.csv"
    fit_log_path = output_dir / "v4_x1_final_refit_log.json"
    summary_path = output_dir / "summary.json"
    manifest_path = output_dir / "MANIFEST.json"
    final_training_dates.to_csv(
        training_dates_path, index=False, lineterminator="\n"
    )
    fit_log_path.write_text(
        json.dumps(fit_log, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary = {
        "schema_version": "ranking_v4_x1_final_refit_result_v1",
        "generation_id": cfg["generation_id"],
        "status": "V4_X1_FINAL_REFIT_FROZEN_READY_FOR_FRESH_PROSPECTIVE_SCORING",
        "fit_count": 4,
        "fit_log": fit_log,
        "historical_training_target_loaded": True,
        "historical_prediction_generated": False,
        "historical_performance_computed": False,
        "protected_forward_accessed": False,
        "provider_calls": False,
        "target_support_parity_mismatches": parity,
        "eligible_dates": actual_eligible,
        "eligible_dates_after_frozen_end": eligible_after,
        "frozen_historical_signal_end_session_index": frozen_end_index,
        "frozen_historical_signal_end_date": frozen_end_date.strftime("%Y-%m-%d"),
        "pit_diagnostics": pit_diagnostics.__dict__,
        "price_evidence": price_stats,
        "historical_parent": historical_parent,
        "prospective_boundary": {
            "historical_dates_forbidden_for_x1_evaluation": True,
            "pre_model_freeze_forward_sessions_forbidden_for_x1_evaluation": True,
            "first_eligible_score_session": cfg["first_eligible_score_session_rule"],
            "do_not_infer_calendar_date": True,
            "outcome_access_before_100_and_h10_maturity": False,
        },
        "next": "START_IMMUTABLE_V4_X1_SCORE_ONLY_CAPTURE_ON_FIRST_SOURCE_CERTIFIED_OFFICIAL_SESSION_STRICTLY_AFTER_MODEL_FREEZE",
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
        **{f"model_{key}": value for key, value in model_paths.items()},
    }
    output_hashes = {
        name: hist.sha256_file(path) for name, path in outputs.items()
    }
    manifest = {
        "schema_version": "ranking_v4_x1_final_refit_manifest_v1",
        "generation_id": cfg["generation_id"],
        "status": summary["status"],
        "git": {
            "head": hist.git_output(repo_root, "rev-parse", "HEAD"),
            "branch": hist.git_output(repo_root, "rev-parse", "--abbrev-ref", "HEAD"),
            "worktree_clean_before_run": True,
            "runner_blob": hist.git_output(repo_root, "rev-parse", f"HEAD:{SELF_PATH}"),
            "config_blob": hist.git_output(
                repo_root,
                "rev-parse",
                "HEAD:config/ranking_v4_x1_final_refit_v1.json",
            ),
        },
        "runtime": runtime,
        "scientific_git_blobs": scientific_blobs,
        "immutable_inputs": {
            "historical_selection_parent": historical_parent,
            "execution_freeze_manifest": cfg["execution_freeze"]["manifest_sha256"],
            "prefit": prefit_hashes,
            "prefit_per_date": per_date_sha,
            "parent_combined_replay": parent_hashes,
            "market_inputs": market_hashes,
            "validation_folds": folds_sha,
        },
        "training_policy": cfg["final_training_policy"],
        "required_fit_count": 4,
        "historical_prediction_generated": False,
        "historical_performance_computed": False,
        "protected_forward_accessed": False,
        "provider_calls": False,
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
                "eligible_dates": actual_eligible,
                "target_support_parity_mismatches": parity,
                "historical_prediction_generated": False,
                "historical_performance_computed": False,
                "protected_forward_accessed": False,
                "provider_calls": False,
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
