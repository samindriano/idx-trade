from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .provenance import sha256_file
from .ranking_v2_candidate import _assert_clean_output_dir
from .ranking_v3_sector import (
    AUTHORIZATION_STATUS,
    V3_D_CANDIDATE,
    V3_D_CONTROL,
    run_sector_discovery,
)
from .research_v2_validation import evaluate_v2_scores


V3_C_REGIME_CACHE_SHA256 = "1fd9350f949fc111968934839a65c79ac30ad1b10a5c1d396560ea370d4ce5a8"
REGIME_STATES = ("NORMAL", "STRESS")
MAX_DISCOVERY_SIGNAL_INDEX = 984

REGIME_MEDIAN_PR_FLOOR = -0.005
REGIME_MEDIAN_ROC_FLOOR = -0.005
REGIME_MEDIAN_Q5_FLOOR = -0.005
REGIME_WORST_PR_FLOOR = -0.015


_IDENTITY_COLUMNS = ("ticker", "date", "signal_session_index", "binary_target")


def _assert_amended_authorization(
    *,
    authorization_path: Path,
    amendment_path: Path,
    v3_c_regime_cache_path: Path,
) -> dict[str, Any]:
    auth = json.loads(authorization_path.read_text(encoding="utf-8"))
    if auth.get("status") != AUTHORIZATION_STATUS:
        raise PermissionError("V3-D amended outcome run is not authorized")
    if not bool(auth.get("v3_c_reviewed", False)):
        raise PermissionError("V3-D amended run requires completed V3-C review")
    if auth.get("amendment_sha256") != sha256_file(amendment_path):
        raise PermissionError("V3-D amendment identity mismatch")
    regime_sha = sha256_file(v3_c_regime_cache_path)
    if regime_sha != V3_C_REGIME_CACHE_SHA256:
        raise PermissionError("V3-C regime cache hash mismatch")
    if auth.get("v3_c_regime_cache_sha256") != regime_sha:
        raise PermissionError("V3-D authorization did not pin the V3-C regime cache")
    return auth


def _load_regime_map(path: Path) -> pd.DataFrame:
    if sha256_file(path) != V3_C_REGIME_CACHE_SHA256:
        raise RuntimeError("unexpected V3-C regime cache identity")
    columns = ["signal_session_index", "date", "regime_state"]
    table = pd.read_parquet(path, columns=columns)
    table["signal_session_index"] = pd.to_numeric(table["signal_session_index"], errors="raise").astype(int)
    table["date"] = pd.to_datetime(table["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if table["date"].isna().any():
        raise RuntimeError("V3-C regime cache contains invalid dates")
    if int(table["signal_session_index"].max()) > MAX_DISCOVERY_SIGNAL_INDEX:
        raise RuntimeError("V3-C regime cache contains sealed sessions")
    states = set(table["regime_state"].astype(str).unique())
    if not states.issubset({"NORMAL", "STRESS", "MISSING_WARMUP"}):
        raise RuntimeError(f"unexpected V3-C regime states: {sorted(states)}")
    key = ["signal_session_index", "date"]
    state_counts = table.groupby(key, sort=False)["regime_state"].nunique(dropna=False)
    if (state_counts != 1).any():
        raise RuntimeError("V3-C regime cache is not market-wide unique by session/date")
    return table[key + ["regime_state"]].drop_duplicates(key).sort_values(key, kind="mergesort").reset_index(drop=True)


def _attach_regime(predictions: pd.DataFrame, regime_map: pd.DataFrame) -> pd.DataFrame:
    data = predictions.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    data["signal_session_index"] = pd.to_numeric(data["signal_session_index"], errors="raise").astype(int)
    joined = data.merge(regime_map, on=["signal_session_index", "date"], how="left", validate="many_to_one")
    if joined["regime_state"].isna().any():
        raise RuntimeError("V3-D prediction rows missing V3-C regime assignment")
    validation_states = set(joined["regime_state"].astype(str).unique())
    if not validation_states.issubset(set(REGIME_STATES)):
        raise RuntimeError(f"V3-D validation predictions contain non-mature regime states: {sorted(validation_states)}")
    return joined


def _paired_state_metrics(predictions: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    folds = sorted(predictions["fold"].astype(str).unique())
    for fold in folds:
        for state in REGIME_STATES:
            control = predictions[
                predictions["candidate"].eq(V3_D_CONTROL)
                & predictions["fold"].eq(fold)
                & predictions["regime_state"].eq(state)
            ].copy()
            candidate = predictions[
                predictions["candidate"].eq(V3_D_CANDIDATE)
                & predictions["fold"].eq(fold)
                & predictions["regime_state"].eq(state)
            ].copy()
            control = control.sort_values(list(_IDENTITY_COLUMNS), kind="mergesort").reset_index(drop=True)
            candidate = candidate.sort_values(list(_IDENTITY_COLUMNS), kind="mergesort").reset_index(drop=True)
            if control.empty or candidate.empty:
                raise RuntimeError(f"V3-D regime diagnostic empty for {fold}/{state}")
            if not control[list(_IDENTITY_COLUMNS)].equals(candidate[list(_IDENTITY_COLUMNS)]):
                raise RuntimeError(f"V3-D regime diagnostic identity mismatch for {fold}/{state}")
            if control["binary_target"].nunique() != 2:
                raise RuntimeError(f"V3-D regime diagnostic requires both classes for {fold}/{state}")
            control_metric = evaluate_v2_scores(control, control["score"].to_numpy(dtype=float))
            candidate_metric = evaluate_v2_scores(candidate, candidate["score"].to_numpy(dtype=float))
            rows.append(
                {
                    "fold": fold,
                    "regime_state": state,
                    "rows": int(len(candidate)),
                    "dates": int(candidate["date"].nunique()),
                    "positive_rate": float(candidate_metric["positive_rate"]),
                    "control_pr_delta": float(control_metric["pr_auc_delta_vs_base"]),
                    "candidate_pr_delta": float(candidate_metric["pr_auc_delta_vs_base"]),
                    "paired_pr_delta_improvement": float(
                        candidate_metric["pr_auc_delta_vs_base"] - control_metric["pr_auc_delta_vs_base"]
                    ),
                    "control_roc_auc": float(control_metric["roc_auc"]),
                    "candidate_roc_auc": float(candidate_metric["roc_auc"]),
                    "paired_roc_change": float(candidate_metric["roc_auc"] - control_metric["roc_auc"]),
                    "control_q5_minus_q1": float(control_metric["q5_minus_q1"]),
                    "candidate_q5_minus_q1": float(candidate_metric["q5_minus_q1"]),
                    "paired_q5_minus_q1_change": float(
                        candidate_metric["q5_minus_q1"] - control_metric["q5_minus_q1"]
                    ),
                    "control_top_decile_lift": float(control_metric["top_decile_lift"]),
                    "candidate_top_decile_lift": float(candidate_metric["top_decile_lift"]),
                    "paired_top_decile_lift_change": float(
                        candidate_metric["top_decile_lift"] - control_metric["top_decile_lift"]
                    ),
                }
            )

    frame = pd.DataFrame(rows)
    if len(frame) != len(folds) * len(REGIME_STATES):
        raise RuntimeError("V3-D regime diagnostics did not produce every fold/state cell")

    aggregate: dict[str, Any] = {"states": {}}
    for state in REGIME_STATES:
        block = frame[frame["regime_state"].eq(state)]
        pr = block["paired_pr_delta_improvement"].to_numpy(dtype=float)
        roc = block["paired_roc_change"].to_numpy(dtype=float)
        q5 = block["paired_q5_minus_q1_change"].to_numpy(dtype=float)
        top = block["paired_top_decile_lift_change"].to_numpy(dtype=float)
        aggregate["states"][state] = {
            "median_pr_delta_improvement": float(np.median(pr)),
            "worst_pr_delta_improvement": float(np.min(pr)),
            "nonnegative_pr_folds": int(np.sum(pr >= 0.0)),
            "median_roc_change": float(np.median(roc)),
            "median_q5_minus_q1_change": float(np.median(q5)),
            "median_top_decile_lift_change": float(np.median(top)),
        }
    aggregate["worst_fold_state_pr_delta_improvement"] = float(frame["paired_pr_delta_improvement"].min())
    return frame, aggregate


def _regime_guard(aggregate: dict[str, Any]) -> tuple[bool, dict[str, bool]]:
    normal = aggregate["states"]["NORMAL"]
    stress = aggregate["states"]["STRESS"]
    checks = {
        "normal_median_pr": normal["median_pr_delta_improvement"] >= REGIME_MEDIAN_PR_FLOOR,
        "stress_median_pr": stress["median_pr_delta_improvement"] >= REGIME_MEDIAN_PR_FLOOR,
        "normal_median_roc": normal["median_roc_change"] >= REGIME_MEDIAN_ROC_FLOOR,
        "stress_median_roc": stress["median_roc_change"] >= REGIME_MEDIAN_ROC_FLOOR,
        "normal_median_q5": normal["median_q5_minus_q1_change"] >= REGIME_MEDIAN_Q5_FLOOR,
        "stress_median_q5": stress["median_q5_minus_q1_change"] >= REGIME_MEDIAN_Q5_FLOOR,
        "worst_fold_state_pr": aggregate["worst_fold_state_pr_delta_improvement"] >= REGIME_WORST_PR_FLOOR,
    }
    return bool(all(checks.values())), {key: bool(value) for key, value in checks.items()}


def run_amended_sector_discovery(
    *,
    cache_path: Path,
    cache_manifest_path: Path,
    reference_v2_dir: Path,
    spec_path: Path,
    amendment_path: Path,
    authorization_path: Path,
    v3_c_regime_cache_path: Path,
    output_dir: Path,
    code_commit: str,
) -> dict[str, Any]:
    _assert_clean_output_dir(output_dir)
    _assert_amended_authorization(
        authorization_path=authorization_path,
        amendment_path=amendment_path,
        v3_c_regime_cache_path=v3_c_regime_cache_path,
    )

    base_dir = output_dir / "base_v3_d"
    base_summary = run_sector_discovery(
        cache_path=cache_path,
        cache_manifest_path=cache_manifest_path,
        reference_v2_dir=reference_v2_dir,
        spec_path=spec_path,
        authorization_path=authorization_path,
        output_dir=base_dir,
        code_commit=code_commit,
    )

    predictions_path = base_dir / "ranking_v3_d_sector_relative_f1_f4_predictions.parquet"
    predictions = pd.read_parquet(predictions_path)
    regime_map = _load_regime_map(v3_c_regime_cache_path)
    predictions = _attach_regime(predictions, regime_map)
    regime_frame, regime_aggregate = _paired_state_metrics(predictions)
    regime_guard_pass, regime_guard_checks = _regime_guard(regime_aggregate)

    base_promoted = base_summary.get("status") == "V3_D_SECTOR_PROMOTE_RELATIVE6"
    final_promoted = bool(base_promoted and regime_guard_pass)
    final_status = "V3_D_SECTOR_PROMOTE_RELATIVE6" if final_promoted else "V3_D_SECTOR_KILL_KEEP_V2_CONTROL"
    final_candidate_verdict = "PROMOTE_FOR_NEXT_RESEARCH_STEP" if final_promoted else "KEEP_DIAGNOSTIC"

    regime_metrics_path = output_dir / "ranking_v3_d_post_v3c_regime_metrics.csv"
    regime_frame.to_csv(regime_metrics_path, index=False)
    regime_aggregate_path = output_dir / "ranking_v3_d_post_v3c_regime_aggregate.json"
    regime_aggregate_payload = {
        **regime_aggregate,
        "guard_thresholds": {
            "median_pr_floor_each_state": REGIME_MEDIAN_PR_FLOOR,
            "median_roc_floor_each_state": REGIME_MEDIAN_ROC_FLOOR,
            "median_q5_floor_each_state": REGIME_MEDIAN_Q5_FLOOR,
            "worst_fold_state_pr_floor": REGIME_WORST_PR_FLOOR,
        },
        "guard_checks": regime_guard_checks,
        "guard_pass": regime_guard_pass,
    }
    regime_aggregate_path.write_text(
        json.dumps(regime_aggregate_payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    final_verdict = {
        "status": final_status,
        "candidate_verdict": final_candidate_verdict,
        "base_v3_d_status": base_summary.get("status"),
        "base_v3_d_candidate_verdict": base_summary.get("candidate_verdict"),
        "base_v3_d_promoted": base_promoted,
        "regime_non_degradation_guard_pass": regime_guard_pass,
        "regime_guard_checks": regime_guard_checks,
        "selected_component": V3_D_CANDIDATE if final_promoted else None,
        "v3_c_regime_cache_sha256": V3_C_REGIME_CACHE_SHA256,
        "amendment_sha256": sha256_file(amendment_path),
        "v2f5_v2f6_accessed": False,
        "fresh_forward_accessed": False,
    }
    final_verdict_path = output_dir / "ranking_v3_d_post_v3c_final_verdict.json"
    final_verdict_path.write_text(json.dumps(final_verdict, indent=2, ensure_ascii=False), encoding="utf-8")

    summary = {
        **final_verdict,
        "code_commit": code_commit,
        "cache_sha256": sha256_file(cache_path),
        "cache_manifest_sha256": sha256_file(cache_manifest_path),
        "spec_sha256": sha256_file(spec_path),
        "authorization_sha256": sha256_file(authorization_path),
        "artifact_sha256": {
            "base_summary": base_summary.get("summary_sha256"),
            regime_metrics_path.name: sha256_file(regime_metrics_path),
            regime_aggregate_path.name: sha256_file(regime_aggregate_path),
            final_verdict_path.name: sha256_file(final_verdict_path),
        },
        "independent_validation_claim": False,
        "probability_claim": False,
    }
    summary_path = output_dir / "ranking_v3_d_post_v3c_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    summary["summary_sha256"] = sha256_file(summary_path)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run frozen post-V3-C amended V3-D sector discovery")
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--cache-manifest", type=Path, required=True)
    parser.add_argument("--reference-v2-dir", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--amendment", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--v3-c-regime-cache", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--code-commit", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_amended_sector_discovery(
        cache_path=args.cache,
        cache_manifest_path=args.cache_manifest,
        reference_v2_dir=args.reference_v2_dir,
        spec_path=args.spec,
        amendment_path=args.amendment,
        authorization_path=args.authorization,
        v3_c_regime_cache_path=args.v3_c_regime_cache,
        output_dir=args.output_dir,
        code_commit=args.code_commit,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
