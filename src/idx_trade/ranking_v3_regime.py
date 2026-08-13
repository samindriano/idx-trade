from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .provenance import sha256_file
from .ranking_v2_candidate import _assert_clean_output_dir, _normalize_candidate_table
from .ranking_v3_recency import (
    DISCOVERY_FOLDS,
    _absolute_sanity,
    _aggregate_candidate,
    _paired_metrics,
    _paired_promotion,
    _read_reference_artifacts,
    prove_control_equivalence,
)
from .ranking_v3_structure_lite import (
    CALENDAR_SHA256,
    MAX_DISCOVERY_SIGNAL_INDEX,
    PANEL_SHA256,
    SECURITY_MASTER_SHA256,
    V2_MANIFEST_SHA256,
    V2_PREPARED_SHA256,
    _feature_order_hash,
    _normalized_git_blob_sha1,
    _read_calendar,
    _read_panel_bounded,
    _read_v2_discovery_subset,
)
from .research_features import build_baseline_features
from .research_v2_features import V2_FULL_FEATURE_COLUMNS, build_v2_feature_table
from .research_v2_models import HGB_XS_MARKET, pointwise_model, pointwise_raw_score
from .research_v2_validation import RANKING_V2_FOLDS, evaluate_v2_scores, split_v2_model_table
from .research_v3_regime import (
    REGIME_AUDIT_COLUMNS,
    REGIME_CONTEXT_ATOL,
    REGIME_MISSING,
    REGIME_NORMAL,
    REGIME_SOURCE_COLUMNS,
    REGIME_STATES,
    REGIME_STRESS,
    build_regime_table,
)
from .stage5_ranking_holdout import _assert_environment


V3_C_HYPOTHESIS_ID = "V3-C-REGIME-V1"
V3_C_CONTROL = "V3-C-REGIME-V1-CONTROL-006"
V3_C_CANDIDATE = "V3-C-REGIME-V1-TWO-EXPERT-007"
V3_C_CANDIDATES = (V3_C_CONTROL, V3_C_CANDIDATE)

REGIME_SPEC_GIT_BLOB = "2a2f48d68f5d3df839c61191d4a11fa870470b00"
REGIME_ADDENDUM_GIT_BLOB = "a13c5ae103908311968e38c6ded233b7a1cbd901"
SEALED_FOLD_NAMES = frozenset(fold.name for fold in RANKING_V2_FOLDS[4:])

TRAIN_MIN_DATES_PER_REGIME = 40
TRAIN_MIN_ROWS_PER_REGIME = 5_000
VALIDATION_MIN_DATES_PER_REGIME = 8
VALIDATION_MIN_ROWS_PER_REGIME = 500

STRESS_MEDIAN_PR_MIN = 0.001
STRESS_NONNEGATIVE_FOLDS_MIN = 3
NORMAL_MEDIAN_PR_FLOOR = -0.001
REGIME_WORST_PR_FLOOR = -0.005
REGIME_MEDIAN_ROC_FLOOR = -0.005
REGIME_MEDIAN_Q5_FLOOR = -0.005

REGIME_JOIN_COLUMNS = tuple(column for column in REGIME_AUDIT_COLUMNS if column not in REGIME_SOURCE_COLUMNS)


def assert_discovery_fold_allowed(name: str) -> None:
    allowed = {fold.name for fold in DISCOVERY_FOLDS}
    if name in SEALED_FOLD_NAMES or name not in allowed:
        raise PermissionError(f"{name} is sealed for V3-C regime discovery")


def _assert_spec_files(spec_path: Path, addendum_path: Path) -> dict[str, str]:
    identities = {
        "spec_git_blob": _normalized_git_blob_sha1(spec_path),
        "addendum_git_blob": _normalized_git_blob_sha1(addendum_path),
    }
    if identities["spec_git_blob"] != REGIME_SPEC_GIT_BLOB:
        raise RuntimeError("V3-C regime spec Git blob mismatch")
    if identities["addendum_git_blob"] != REGIME_ADDENDUM_GIT_BLOB:
        raise RuntimeError("V3-C regime review addendum Git blob mismatch")
    return identities


def _context_equivalence(v2: pd.DataFrame, regime: pd.DataFrame) -> dict[str, float]:
    keyed = regime.set_index(["signal_session_index", "date"])
    if keyed.index.duplicated().any():
        raise RuntimeError("V3-C regime table has duplicate session/date context")
    # Many securities legitimately share the same market-wide session/date key.
    # The source context index must be unique; repeated target keys are expected.
    keys = pd.MultiIndex.from_frame(v2[["signal_session_index", "date"]])
    missing = keys.difference(keyed.index)
    if len(missing):
        raise RuntimeError(f"V3-C regime context missing {len(missing)} V2 rows")
    aligned = keyed.reindex(keys)
    diffs: dict[str, float] = {}
    for column in REGIME_SOURCE_COLUMNS:
        left = pd.to_numeric(v2[column], errors="coerce").to_numpy(dtype=float)
        right = pd.to_numeric(aligned[column], errors="coerce").to_numpy(dtype=float)
        if not np.allclose(left, right, rtol=0.0, atol=REGIME_CONTEXT_ATOL, equal_nan=True):
            finite = np.isfinite(left) & np.isfinite(right)
            maximum = float(np.max(np.abs(left[finite] - right[finite]))) if finite.any() else np.inf
            raise RuntimeError(f"V3-C recomputed market context mismatch {column}: max_abs_diff={maximum}")
        finite = np.isfinite(left) & np.isfinite(right)
        diffs[column] = float(np.max(np.abs(left[finite] - right[finite]))) if finite.any() else 0.0
    return diffs


def _coverage_report(cache: pd.DataFrame) -> dict[str, Any]:
    report: dict[str, Any] = {"folds": {}, "gate_pass": True}
    for fold in DISCOVERY_FOLDS:
        assert_discovery_fold_allowed(fold.name)
        session_values = pd.to_numeric(cache["signal_session_index"], errors="raise").astype(int)
        train = cache[session_values.between(fold.train_start, fold.train_end)]
        validation = cache[session_values.between(fold.validation_start, fold.validation_end)]
        fold_report: dict[str, Any] = {"train": {}, "validation": {}}
        for state in (*REGIME_STATES, REGIME_MISSING):
            train_state = train[train["regime_state"].eq(state)]
            validation_state = validation[validation["regime_state"].eq(state)]
            fold_report["train"][state] = {
                "rows": int(len(train_state)),
                "dates": int(train_state["date"].nunique()),
            }
            fold_report["validation"][state] = {
                "rows": int(len(validation_state)),
                "dates": int(validation_state["date"].nunique()),
            }

        train_pass = all(
            fold_report["train"][state]["rows"] >= TRAIN_MIN_ROWS_PER_REGIME
            and fold_report["train"][state]["dates"] >= TRAIN_MIN_DATES_PER_REGIME
            for state in REGIME_STATES
        )
        validation_pass = (
            fold_report["validation"][REGIME_MISSING]["rows"] == 0
            and all(
                fold_report["validation"][state]["rows"] >= VALIDATION_MIN_ROWS_PER_REGIME
                and fold_report["validation"][state]["dates"] >= VALIDATION_MIN_DATES_PER_REGIME
                for state in REGIME_STATES
            )
        )
        fold_report["train_gate_pass"] = bool(train_pass)
        fold_report["validation_gate_pass"] = bool(validation_pass)
        fold_report["gate_pass"] = bool(train_pass and validation_pass)
        report["folds"][fold.name] = fold_report
        report["gate_pass"] = bool(report["gate_pass"] and fold_report["gate_pass"])
    return report


def prepare_regime_cache(
    *,
    panel_path: Path,
    calendar_path: Path,
    security_master_path: Path,
    v2_prepared_path: Path,
    v2_manifest_path: Path,
    spec_path: Path,
    addendum_path: Path,
    output_dir: Path,
    code_commit: str,
) -> dict[str, Any]:
    _assert_clean_output_dir(output_dir)
    contract_identity = _assert_spec_files(spec_path, addendum_path)
    source_sha256 = {
        "panel": sha256_file(panel_path),
        "calendar": sha256_file(calendar_path),
        "security_master": sha256_file(security_master_path),
        "v2_prepared": sha256_file(v2_prepared_path),
        "v2_manifest": sha256_file(v2_manifest_path),
    }
    expected = {
        "panel": PANEL_SHA256,
        "calendar": CALENDAR_SHA256,
        "security_master": SECURITY_MASTER_SHA256,
        "v2_prepared": V2_PREPARED_SHA256,
        "v2_manifest": V2_MANIFEST_SHA256,
    }
    if source_sha256 != expected:
        raise RuntimeError(f"V3-C source hash mismatch: expected={expected} actual={source_sha256}")

    sessions = _read_calendar(calendar_path)
    max_date = pd.Timestamp(sessions[MAX_DISCOVERY_SIGNAL_INDEX - 1])
    panel = _read_panel_bounded(panel_path, max_date)

    # Outcome-independent rebuild of the same baseline/V2 market context.
    baseline = build_baseline_features(panel, sessions)
    if any(column in baseline.columns for column in ("binary_target", "label_status")):
        raise RuntimeError("V3-C outcome-independent baseline unexpectedly contains labels")
    v2_feature_frame = build_v2_feature_table(baseline)
    regime = build_regime_table(
        v2_feature_frame,
        sessions,
        max_signal_session_index=MAX_DISCOVERY_SIGNAL_INDEX,
    )
    if int(regime["signal_session_index"].max()) > MAX_DISCOVERY_SIGNAL_INDEX:
        raise RuntimeError("V3-C regime table includes sealed sessions")

    v2_raw = _read_v2_discovery_subset(v2_prepared_path)
    v2 = _normalize_candidate_table(v2_raw, HGB_XS_MARKET)
    if int(v2["signal_session_index"].max()) > MAX_DISCOVERY_SIGNAL_INDEX:
        raise RuntimeError("V3-C V2 discovery subset includes sealed sessions")

    context_diffs = _context_equivalence(v2, regime)
    keyed = regime.set_index(["signal_session_index", "date"])
    keys = pd.MultiIndex.from_frame(v2[["signal_session_index", "date"]])
    aligned = keyed.reindex(keys)
    joined = v2.copy()
    for column in REGIME_JOIN_COLUMNS:
        joined[column] = aligned[column].to_numpy()

    original_columns = list(v2.columns)
    if not joined.loc[:, original_columns].equals(v2.loc[:, original_columns]):
        raise RuntimeError("V3-C cache changed an existing V2 prepared column")
    if joined.duplicated(["ticker", "date"]).any():
        raise RuntimeError("V3-C discovery cache contains duplicate ticker/date rows")

    allowed_states = {REGIME_NORMAL, REGIME_STRESS, REGIME_MISSING}
    if not set(joined["regime_state"].astype(str).unique()).issubset(allowed_states):
        raise RuntimeError("V3-C cache contains invalid regime state")
    observed_votes = pd.to_numeric(
        joined.loc[joined["regime_state"].isin(REGIME_STATES), "stress_votes"], errors="raise"
    )
    if not observed_votes.isin([0.0, 1.0, 2.0, 3.0]).all():
        raise RuntimeError("V3-C cache contains invalid stress vote count")

    coverage = _coverage_report(joined)
    cache_path = output_dir / "ranking_v3_c_regime_discovery_cache.parquet"
    joined.to_parquet(cache_path, index=False)
    cache_sha = sha256_file(cache_path)
    manifest = {
        "status": "RANKING_V3_C_REGIME_DISCOVERY_CACHE_FROZEN",
        "code_commit": code_commit,
        "source_sha256": source_sha256,
        "contract_identity": contract_identity,
        "cache_path": str(cache_path),
        "cache_sha256": cache_sha,
        "rows": int(len(joined)),
        "tickers": int(joined["ticker"].nunique()),
        "first_signal_session_index": int(joined["signal_session_index"].min()),
        "last_signal_session_index": int(joined["signal_session_index"].max()),
        "v2_feature_columns": list(V2_FULL_FEATURE_COLUMNS),
        "v2_feature_order_sha256": _feature_order_hash(tuple(V2_FULL_FEATURE_COLUMNS)),
        "regime_audit_columns": list(REGIME_JOIN_COLUMNS),
        "context_equivalence_max_abs_diff": context_diffs,
        "coverage": coverage,
        "coverage_gate_pass": bool(coverage["gate_pass"]),
        "v2f5_v2f6_materialized": False,
        "outcome_metrics_computed": False,
        "independent_validation_claim": False,
    }
    manifest_path = output_dir / "ranking_v3_c_regime_discovery_cache_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    manifest["manifest_sha256"] = sha256_file(manifest_path)
    return manifest


def _assert_discovery_cache(
    *,
    cache_path: Path,
    manifest_path: Path,
    spec_path: Path,
    addendum_path: Path,
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, str]]:
    identities = _assert_spec_files(spec_path, addendum_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "RANKING_V3_C_REGIME_DISCOVERY_CACHE_FROZEN":
        raise RuntimeError("V3-C cache manifest is not frozen")
    if bool(manifest.get("v2f5_v2f6_materialized", True)):
        raise RuntimeError("V3-C cache claims sealed folds were materialized")
    if bool(manifest.get("outcome_metrics_computed", True)):
        raise RuntimeError("V3-C cache prepare unexpectedly computed outcomes")
    if not bool(manifest.get("coverage_gate_pass", False)):
        raise RuntimeError("V3_C_REGIME_BLOCKED_KEEP_V2_CONTROL: fragmentation coverage gate failed")
    actual_cache_sha = sha256_file(cache_path)
    if manifest.get("cache_sha256") != actual_cache_sha:
        raise RuntimeError("V3-C cache hash mismatch")
    table = pd.read_parquet(cache_path)
    if int(pd.to_numeric(table["signal_session_index"], errors="raise").max()) > MAX_DISCOVERY_SIGNAL_INDEX:
        raise RuntimeError("V3-C cache contains sealed sessions")
    table = _normalize_candidate_table(table, HGB_XS_MARKET)
    required = {"regime_state", "stress_votes", *V2_FULL_FEATURE_COLUMNS}
    if not required.issubset(table.columns):
        raise RuntimeError(f"V3-C cache missing columns: {sorted(required-set(table.columns))}")
    return table, manifest, {"cache": actual_cache_sha, "manifest": sha256_file(manifest_path), **identities}


def _score_control(
    table: pd.DataFrame,
    *,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, str]]:
    metrics_rows: list[dict[str, Any]] = []
    regime_rows: list[dict[str, Any]] = []
    predictions: list[pd.DataFrame] = []
    model_hashes: dict[str, str] = {}
    for fold in DISCOVERY_FOLDS:
        assert_discovery_fold_allowed(fold.name)
        train, validation = split_v2_model_table(table, fold)
        model = pointwise_model(HGB_XS_MARKET)
        model.fit(train, train["binary_target"].to_numpy(dtype=int))
        score = pointwise_raw_score(model, validation)
        if not np.isfinite(score).all():
            raise RuntimeError(f"V3-C control {fold.name} produced non-finite scores")
        metrics_rows.append({"candidate": V3_C_CONTROL, "fold": fold.name, **evaluate_v2_scores(validation, score)})
        for state in REGIME_STATES:
            mask = validation["regime_state"].eq(state).to_numpy(dtype=bool)
            if not mask.any():
                raise RuntimeError(f"V3-C control {fold.name} has no validation rows for {state}")
            regime_rows.append(
                {
                    "candidate": V3_C_CONTROL,
                    "fold": fold.name,
                    "regime_state": state,
                    "rows": int(mask.sum()),
                    "dates": int(validation.loc[mask, "date"].nunique()),
                    **evaluate_v2_scores(validation.loc[mask].copy(), score[mask]),
                }
            )
        scored = validation[["ticker", "date", "signal_session_index", "binary_target", "regime_state"]].copy()
        scored.insert(0, "fold", fold.name)
        scored.insert(0, "candidate", V3_C_CONTROL)
        scored["score"] = score
        predictions.append(scored)
        model_path = output_dir / f"ranking_v3_c_control_{fold.name.lower()}.joblib"
        joblib.dump(model, model_path)
        model_hashes[model_path.name] = sha256_file(model_path)
    return pd.DataFrame(metrics_rows), pd.concat(predictions, ignore_index=True), pd.DataFrame(regime_rows), model_hashes


def _score_specialist(
    table: pd.DataFrame,
    *,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, str]]:
    metrics_rows: list[dict[str, Any]] = []
    regime_rows: list[dict[str, Any]] = []
    training_rows: list[dict[str, Any]] = []
    predictions: list[pd.DataFrame] = []
    model_hashes: dict[str, str] = {}

    for fold in DISCOVERY_FOLDS:
        assert_discovery_fold_allowed(fold.name)
        train, validation = split_v2_model_table(table, fold)
        if validation["regime_state"].eq(REGIME_MISSING).any():
            raise RuntimeError(f"V3-C specialist {fold.name} has missing validation regime")
        score = np.full(len(validation), np.nan, dtype=float)

        warmup = train[train["regime_state"].eq(REGIME_MISSING)]
        training_rows.append(
            {
                "fold": fold.name,
                "regime_state": REGIME_MISSING,
                "rows": int(len(warmup)),
                "dates": int(warmup["date"].nunique()),
            }
        )

        for state in REGIME_STATES:
            train_mask = train["regime_state"].eq(state).to_numpy(dtype=bool)
            validation_mask = validation["regime_state"].eq(state).to_numpy(dtype=bool)
            expert_train = train.loc[train_mask].copy()
            expert_validation = validation.loc[validation_mask].copy()
            if len(expert_train) < TRAIN_MIN_ROWS_PER_REGIME or expert_train["date"].nunique() < TRAIN_MIN_DATES_PER_REGIME:
                raise RuntimeError(f"V3-C {fold.name} {state} training fragmentation gate failed")
            if len(expert_validation) < VALIDATION_MIN_ROWS_PER_REGIME or expert_validation["date"].nunique() < VALIDATION_MIN_DATES_PER_REGIME:
                raise RuntimeError(f"V3-C {fold.name} {state} validation fragmentation gate failed")
            if expert_train["binary_target"].nunique() != 2:
                raise RuntimeError(f"V3-C {fold.name} {state} expert training requires both classes")
            if expert_validation["binary_target"].nunique() != 2:
                raise RuntimeError(f"V3-C {fold.name} {state} expert validation requires both classes")
            model = pointwise_model(HGB_XS_MARKET)
            model.fit(expert_train, expert_train["binary_target"].to_numpy(dtype=int))
            expert_score = pointwise_raw_score(model, expert_validation)
            positions = np.flatnonzero(validation_mask)
            score[positions] = expert_score
            training_rows.append(
                {
                    "fold": fold.name,
                    "regime_state": state,
                    "rows": int(len(expert_train)),
                    "dates": int(expert_train["date"].nunique()),
                }
            )
            regime_rows.append(
                {
                    "candidate": V3_C_CANDIDATE,
                    "fold": fold.name,
                    "regime_state": state,
                    "rows": int(len(expert_validation)),
                    "dates": int(expert_validation["date"].nunique()),
                    **evaluate_v2_scores(expert_validation, expert_score),
                }
            )
            model_path = output_dir / f"ranking_v3_c_{state.lower()}_{fold.name.lower()}.joblib"
            joblib.dump(model, model_path)
            model_hashes[model_path.name] = sha256_file(model_path)

        if not np.isfinite(score).all():
            raise RuntimeError(f"V3-C specialist {fold.name} did not route every validation row")
        metrics_rows.append({"candidate": V3_C_CANDIDATE, "fold": fold.name, **evaluate_v2_scores(validation, score)})
        scored = validation[["ticker", "date", "signal_session_index", "binary_target", "regime_state"]].copy()
        scored.insert(0, "fold", fold.name)
        scored.insert(0, "candidate", V3_C_CANDIDATE)
        scored["score"] = score
        predictions.append(scored)

    return (
        pd.DataFrame(metrics_rows),
        pd.concat(predictions, ignore_index=True),
        pd.DataFrame(regime_rows),
        pd.DataFrame(training_rows),
        model_hashes,
    )


def _paired_regime_metrics(candidate: pd.DataFrame, control: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    keys = ["fold", "regime_state"]
    left = candidate.set_index(keys).sort_index()
    right = control.set_index(keys).sort_index()
    if tuple(left.index) != tuple(right.index):
        raise RuntimeError("V3-C regime paired metric keys differ")
    rows: list[dict[str, Any]] = []
    for key in left.index:
        fold, state = key
        rows.append(
            {
                "fold": fold,
                "regime_state": state,
                "pr_auc_delta_improvement": float(left.loc[key, "pr_auc_delta_vs_base"] - right.loc[key, "pr_auc_delta_vs_base"]),
                "roc_auc_change": float(left.loc[key, "roc_auc"] - right.loc[key, "roc_auc"]),
                "q5_minus_q1_change": float(left.loc[key, "q5_minus_q1"] - right.loc[key, "q5_minus_q1"]),
                "top_decile_lift_change": float(left.loc[key, "top_decile_lift"] - right.loc[key, "top_decile_lift"]),
            }
        )
    paired = pd.DataFrame(rows)
    summary: dict[str, Any] = {"by_regime": {}}
    for state in REGIME_STATES:
        block = paired[paired["regime_state"].eq(state)].copy()
        pr = block["pr_auc_delta_improvement"].to_numpy(dtype=float)
        roc = block["roc_auc_change"].to_numpy(dtype=float)
        q5 = block["q5_minus_q1_change"].to_numpy(dtype=float)
        top = block["top_decile_lift_change"].to_numpy(dtype=float)
        summary["by_regime"][state] = {
            "median_pr_auc_delta_improvement": float(np.median(pr)),
            "q25_pr_auc_delta_improvement": float(np.quantile(pr, 0.25)),
            "worst_pr_auc_delta_improvement": float(np.min(pr)),
            "pr_nonnegative_folds": int(np.sum(pr >= 0.0)),
            "median_roc_auc_change": float(np.median(roc)),
            "median_q5_minus_q1_change": float(np.median(q5)),
            "median_top_decile_lift_change": float(np.median(top)),
        }
    summary["worst_regime_fold_pr_auc_delta_improvement"] = float(paired["pr_auc_delta_improvement"].min())
    return paired, summary


def _regime_promotion(summary: dict[str, Any]) -> bool:
    stress = summary["by_regime"][REGIME_STRESS]
    normal = summary["by_regime"][REGIME_NORMAL]
    return bool(
        stress["median_pr_auc_delta_improvement"] >= STRESS_MEDIAN_PR_MIN
        and stress["pr_nonnegative_folds"] >= STRESS_NONNEGATIVE_FOLDS_MIN
        and normal["median_pr_auc_delta_improvement"] >= NORMAL_MEDIAN_PR_FLOOR
        and summary["worst_regime_fold_pr_auc_delta_improvement"] >= REGIME_WORST_PR_FLOOR
        and stress["median_roc_auc_change"] >= REGIME_MEDIAN_ROC_FLOOR
        and normal["median_roc_auc_change"] >= REGIME_MEDIAN_ROC_FLOOR
        and stress["median_q5_minus_q1_change"] >= REGIME_MEDIAN_Q5_FLOOR
        and normal["median_q5_minus_q1_change"] >= REGIME_MEDIAN_Q5_FLOOR
    )


def run_regime_discovery(
    *,
    cache_path: Path,
    cache_manifest_path: Path,
    reference_v2_dir: Path,
    spec_path: Path,
    addendum_path: Path,
    output_dir: Path,
    code_commit: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    environment = _assert_environment()
    _assert_clean_output_dir(output_dir)
    table, cache_manifest, contract_hashes = _assert_discovery_cache(
        cache_path=cache_path,
        manifest_path=cache_manifest_path,
        spec_path=spec_path,
        addendum_path=addendum_path,
    )
    reference_summary, reference_metrics, reference_predictions, reference_hashes = _read_reference_artifacts(reference_v2_dir)

    control_dir = output_dir / "control"
    control_dir.mkdir(parents=True, exist_ok=False)
    control_started = time.perf_counter()
    control_metrics, control_predictions, control_regime_metrics, control_models = _score_control(table, output_dir=control_dir)
    control_seconds = time.perf_counter() - control_started
    equivalence = prove_control_equivalence(
        control_metrics=control_metrics,
        control_predictions=control_predictions,
        reference_metrics=reference_metrics,
        reference_predictions=reference_predictions,
        reference_hashes=reference_hashes,
    )
    equivalence["status"] = "V3_C_CONTROL_EQUIVALENCE_PASS"
    equivalence["reference_summary_identity"] = {
        "sha256": reference_hashes["summary"],
        "code_commit": reference_summary.get("code_commit"),
    }
    equivalence_path = output_dir / "ranking_v3_c_control_equivalence.json"
    equivalence_path.write_text(json.dumps(equivalence, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    candidate_dir = output_dir / "two_expert"
    candidate_dir.mkdir(parents=True, exist_ok=False)
    candidate_started = time.perf_counter()
    candidate_metrics, candidate_predictions, candidate_regime_metrics, training_counts, candidate_models = _score_specialist(
        table, output_dir=candidate_dir
    )
    candidate_seconds = time.perf_counter() - candidate_started

    control_aggregate = _aggregate_candidate(control_metrics)
    candidate_aggregate = _aggregate_candidate(candidate_metrics)
    paired_overall, paired_overall_summary = _paired_metrics(candidate_metrics, control_metrics)
    paired_regime, paired_regime_summary = _paired_regime_metrics(candidate_regime_metrics, control_regime_metrics)

    absolute_pass = _absolute_sanity(candidate_aggregate)
    overall_paired_pass = _paired_promotion(paired_overall_summary)
    regime_pass = _regime_promotion(paired_regime_summary)
    if absolute_pass and overall_paired_pass and regime_pass:
        candidate_verdict = "PROMOTE_FOR_NEXT_RESEARCH_STEP"
        decision = "V3_C_REGIME_PROMOTE_TWO_STATE_EXPERTS"
    else:
        candidate_verdict = "KEEP_DIAGNOSTIC"
        decision = "V3_C_REGIME_KILL_KEEP_V2_CONTROL"

    all_metrics = pd.concat([control_metrics, candidate_metrics], ignore_index=True)
    all_predictions = pd.concat([control_predictions, candidate_predictions], ignore_index=True)
    all_regime_metrics = pd.concat([control_regime_metrics, candidate_regime_metrics], ignore_index=True)

    metrics_path = output_dir / "ranking_v3_c_regime_f1_f4_metrics.csv"
    predictions_path = output_dir / "ranking_v3_c_regime_f1_f4_predictions.parquet"
    regime_metrics_path = output_dir / "ranking_v3_c_regime_state_metrics.csv"
    paired_path = output_dir / "ranking_v3_c_regime_paired_overall.csv"
    paired_regime_path = output_dir / "ranking_v3_c_regime_paired_by_state.csv"
    training_path = output_dir / "ranking_v3_c_regime_training_counts.csv"
    all_metrics.to_csv(metrics_path, index=False)
    all_predictions.to_parquet(predictions_path, index=False)
    all_regime_metrics.to_csv(regime_metrics_path, index=False)
    paired_overall.insert(0, "candidate", V3_C_CANDIDATE)
    paired_overall.to_csv(paired_path, index=False)
    paired_regime.to_csv(paired_regime_path, index=False)
    training_counts.to_csv(training_path, index=False)

    aggregate = {
        V3_C_CONTROL: control_aggregate,
        V3_C_CANDIDATE: candidate_aggregate,
        "overall_paired": paired_overall_summary,
        "regime_paired": paired_regime_summary,
        "candidate_absolute_sanity_pass": bool(absolute_pass),
        "candidate_overall_paired_promotion_pass": bool(overall_paired_pass),
        "candidate_regime_robustness_pass": bool(regime_pass),
    }
    aggregate_path = output_dir / "ranking_v3_c_regime_aggregate.json"
    aggregate_path.write_text(json.dumps(aggregate, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    verdict = {
        "status": decision,
        "control_verdict": "CONTROL_REFERENCE",
        "regime_candidate_verdict": candidate_verdict,
        "selected_component": V3_C_CANDIDATE if candidate_verdict == "PROMOTE_FOR_NEXT_RESEARCH_STEP" else None,
        "v2f5_v2f6_accessed": False,
        "fresh_forward_accessed": False,
    }
    verdict_path = output_dir / "ranking_v3_c_regime_verdict.json"
    verdict_path.write_text(json.dumps(verdict, indent=2, ensure_ascii=False), encoding="utf-8")

    coverage_path = output_dir / "ranking_v3_c_regime_coverage.json"
    coverage_path.write_text(json.dumps(cache_manifest.get("coverage", {}), indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    ledger_rows = [
        {
            "hypothesis_id": V3_C_HYPOTHESIS_ID,
            "candidate_id": V3_C_CONTROL,
            "candidate_ordinal": 6,
            "result_status": "COMPLETE",
            "result_viewed": True,
            "verdict": "CONTROL_REFERENCE",
            "cumulative_candidate_count": 6,
        },
        {
            "hypothesis_id": V3_C_HYPOTHESIS_ID,
            "candidate_id": V3_C_CANDIDATE,
            "candidate_ordinal": 7,
            "result_status": "COMPLETE",
            "result_viewed": True,
            "verdict": candidate_verdict,
            "cumulative_candidate_count": 7,
        },
    ]
    ledger_path = output_dir / "ranking_v3_c_regime_ledger_rows.json"
    ledger_path.write_text(json.dumps(ledger_rows, indent=2, ensure_ascii=False), encoding="utf-8")

    runtime = {
        "mode": "sequential_reference",
        "control_seconds": control_seconds,
        "two_expert_seconds": candidate_seconds,
        "total_seconds": time.perf_counter() - started,
        "python": sys.version,
        "platform": platform.platform(),
        "environment": environment,
    }
    runtime_path = output_dir / "ranking_v3_c_regime_runtime.json"
    runtime_path.write_text(json.dumps(runtime, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    model_hashes = {**control_models, **candidate_models}
    artifacts = {
        path.name: sha256_file(path)
        for path in (
            equivalence_path,
            metrics_path,
            predictions_path,
            regime_metrics_path,
            paired_path,
            paired_regime_path,
            training_path,
            aggregate_path,
            verdict_path,
            coverage_path,
            ledger_path,
            runtime_path,
        )
    }
    artifacts.update(model_hashes)
    summary = {
        "status": decision,
        "code_commit": code_commit,
        "hypothesis_id": V3_C_HYPOTHESIS_ID,
        "candidates": list(V3_C_CANDIDATES),
        "folds": [fold.name for fold in DISCOVERY_FOLDS],
        "cache_sha256": contract_hashes["cache"],
        "cache_manifest_sha256": contract_hashes["manifest"],
        "contract_identity": contract_hashes,
        "control_equivalence_status": equivalence["status"],
        "v2_feature_columns": list(V2_FULL_FEATURE_COLUMNS),
        "v2_feature_order_sha256": _feature_order_hash(tuple(V2_FULL_FEATURE_COLUMNS)),
        "candidate_verdict": candidate_verdict,
        "artifact_sha256": artifacts,
        "independent_validation_claim": False,
        "probability_claim": False,
        "v2f5_v2f6_accessed": False,
        "fresh_forward_accessed": False,
    }
    summary_path = output_dir / "ranking_v3_c_regime_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    summary["summary_sha256"] = sha256_file(summary_path)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare or run frozen Ranking V3-C regime discovery")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="build outcome-independent F1-F4-only regime cache")
    prepare.add_argument("--panel", type=Path, required=True)
    prepare.add_argument("--calendar", type=Path, required=True)
    prepare.add_argument("--security-master", type=Path, required=True)
    prepare.add_argument("--v2-prepared", type=Path, required=True)
    prepare.add_argument("--v2-manifest", type=Path, required=True)
    prepare.add_argument("--spec", type=Path, required=True)
    prepare.add_argument("--addendum", type=Path, required=True)
    prepare.add_argument("--output-dir", type=Path, required=True)
    prepare.add_argument("--code-commit", required=True)

    run = sub.add_parser("run", help="run exact control then frozen two-state experts on F1-F4")
    run.add_argument("--cache", type=Path, required=True)
    run.add_argument("--cache-manifest", type=Path, required=True)
    run.add_argument("--reference-v2-dir", type=Path, required=True)
    run.add_argument("--spec", type=Path, required=True)
    run.add_argument("--addendum", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--code-commit", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        result = prepare_regime_cache(
            panel_path=args.panel,
            calendar_path=args.calendar,
            security_master_path=args.security_master,
            v2_prepared_path=args.v2_prepared,
            v2_manifest_path=args.v2_manifest,
            spec_path=args.spec,
            addendum_path=args.addendum,
            output_dir=args.output_dir,
            code_commit=args.code_commit,
        )
    else:
        result = run_regime_discovery(
            cache_path=args.cache,
            cache_manifest_path=args.cache_manifest,
            reference_v2_dir=args.reference_v2_dir,
            spec_path=args.spec,
            addendum_path=args.addendum,
            output_dir=args.output_dir,
            code_commit=args.code_commit,
        )
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
