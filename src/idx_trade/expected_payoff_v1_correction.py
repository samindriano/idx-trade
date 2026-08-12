"""Metric-only correction for the frozen Expected Payoff V1 runtime.

The original V1 models and validation predictions are immutable inputs here.
This module reconstructs only the fold training payoff targets needed for the
constant baseline, then evaluates that constant on the existing validation
outcomes.  It never fits or invokes a V1 model.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .expected_payoff_v0 import (
    REQUIRED_FOLDS,
    PayoffDataBlocked,
    build_payoff_rows,
    load_actions,
    load_calendar,
    load_open_provenance,
    load_price_frame,
    load_tradability,
    sha256_file,
    stable_key_sha256,
)
from .expected_payoff_v1 import (
    _default_config,
    _fold_definitions,
    _json,
    _require_sha,
    common_support_key_sha256,
)


EXPECTED_ORIGINAL_MANIFEST_SHA256 = "8f6a082016828bbd146b7ddfdf4d90ed0c4feedb946187dd2080aefdeeab63e2"
EXPECTED_V0_VALIDATION_KEY_SHA256 = "f978ec6b81ddc72259e403e78698971f655721f94fbfdcc57f682c5cea3c4602"


def validation_baseline_mse(train_mean: float, validation_target: pd.Series | np.ndarray) -> float:
    """Evaluate the training-derived constant on validation outcomes only."""
    values = np.asarray(validation_target, dtype=float)
    if len(values) == 0 or not np.isfinite(values).all() or not np.isfinite(train_mean):
        raise PayoffDataBlocked("validation baseline inputs are empty or non-finite")
    result = float(np.mean((values - float(train_mean)) ** 2))
    if not np.isfinite(result) or result <= 0:
        raise PayoffDataBlocked("validation baseline MSE is zero/non-finite")
    return result


def corrected_mse_skill(model_mse: float, validation_baseline: float) -> float:
    if not np.isfinite(model_mse) or not np.isfinite(validation_baseline) or validation_baseline <= 0:
        raise PayoffDataBlocked("cannot compute corrected MSE skill")
    return float(1.0 - float(model_mse) / float(validation_baseline))


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, allow_nan=False, default=str) + "\n", encoding="utf-8")


def _verify_manifest_files(manifest_path: Path, manifest: dict) -> None:
    for name, expected in manifest.get("artifacts_sha256", {}).items():
        _require_sha(manifest_path.parent / name, expected, f"original V1 artifact {name}")
    for name, expected in manifest.get("model_sha256", {}).items():
        _require_sha(manifest_path.parent / f"model_{name}.pkl", expected, f"original V1 model {name}")


def _verify_frozen_sources(config: dict) -> None:
    keys = (
        "o2_manifest_path", "o2_predictions_path", "o2_common_support_path",
        "o2_fold_definitions_path", "o2_feature_manifest_path", "v0_resolved_path",
        "v2_prepared_table_path", "calendar_path", "security_master_path", "panel_path",
        "open_panel_path", "open_provenance_path", "tradability_path", "actions_path",
        "actions_summary_path", "v3_b_training_table_path", "v3_b_manifest_path",
    )
    for key in keys:
        _require_sha(Path(config[key]), config[key.replace("_path", "_sha256")], key)


def _reconstruct_training_targets(config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    common = pd.read_csv(config["o2_common_support_path"])
    common["date"] = pd.to_datetime(common["date"], errors="coerce")
    common["ticker"] = common.ticker.astype(str).str.upper().str.strip()
    if common.date.isna().any() or common_support_key_sha256(common) != config["o2_common_support_key_sha256"]:
        raise PayoffDataBlocked("common-support identity mismatch during correction")

    calendar = load_calendar(Path(config["calendar_path"]), config["calendar_sha256"])
    panel = load_price_frame(Path(config["panel_path"]), config["panel_sha256"], "immutable panel")
    open_panel = load_price_frame(Path(config["open_panel_path"]), config["open_panel_sha256"], "accepted Open panel")
    open_prov = load_open_provenance(Path(config["open_provenance_path"]), config["open_provenance_sha256"])
    tradability = load_tradability(Path(config["tradability_path"]), config["tradability_sha256"])
    actions = load_actions(
        Path(config["actions_path"]), config["actions_sha256"],
        Path(config["actions_summary_path"]), config["actions_summary_sha256"],
    )
    prepared = pd.read_parquet(
        config["v2_prepared_table_path"],
        columns=["ticker", "date", "signal_session_index", "atr14_over_close"],
    )
    prepared["date"] = pd.to_datetime(prepared["date"])
    prepared["ticker"] = prepared.ticker.astype(str).str.upper().str.strip()
    if prepared.duplicated(["ticker", "date"]).any():
        raise PayoffDataBlocked("V2 prepared ATR keys are duplicated")

    parent = common.rename(columns={"date": "signal_date"}).copy()
    parent["fold"] = "COMMON"
    parent["score"] = 0.0
    parent = parent.rename(columns={"signal_date": "date"})
    ledger, resolved = build_payoff_rows(parent, prepared, calendar, panel, open_panel, open_prov, tradability, actions)
    if resolved.empty or not np.isfinite(resolved.payoff_atr_gross).all():
        raise PayoffDataBlocked("training payoff reconstruction is empty/non-finite")
    return ledger, resolved


def run_metric_correction(
    *,
    external_root: Path,
    original_output: Path,
    correction_output: Path,
) -> dict:
    if correction_output.exists() and any(correction_output.iterdir()):
        raise PayoffDataBlocked(f"correction output must be new and empty: {correction_output}")
    correction_output.mkdir(parents=True, exist_ok=True)
    original_manifest_path = original_output / "artifact_manifest.json"
    _require_sha(original_manifest_path, EXPECTED_ORIGINAL_MANIFEST_SHA256, "original V1 artifact manifest")
    original_manifest = _json(original_manifest_path)
    if original_manifest.get("candidate") != "PAYOFF_HGB_O2_FEATURES_V1":
        raise PayoffDataBlocked("original artifact candidate mismatch")
    _verify_manifest_files(original_manifest_path, original_manifest)
    if original_manifest.get("runtime_flags", {}).get("fresh_forward_outcomes_accessed") is not False:
        raise PayoffDataBlocked("original V1 fresh-forward flag is not false")

    validation_path = original_output / "validation_predictions.parquet"
    validation_sha = original_manifest.get("artifacts_sha256", {}).get("validation_predictions.parquet")
    _require_sha(validation_path, validation_sha, "original V1 validation predictions")
    validation = pd.read_parquet(validation_path)
    validation["date"] = pd.to_datetime(validation["date"], errors="coerce")
    if validation.date.isna().any() or validation.duplicated(["ticker", "date", "fold", "signal_session_index"]).any():
        raise PayoffDataBlocked("original V1 validation keys are invalid")
    validation_identity = validation.rename(columns={"date": "signal_date"})
    validation_key_sha = stable_key_sha256(
        validation_identity, ["ticker", "signal_date", "fold", "signal_session_index"]
    )
    if validation_key_sha != EXPECTED_V0_VALIDATION_KEY_SHA256:
        raise PayoffDataBlocked("original V1 validation keys do not equal accepted V0 keys")
    if not np.isfinite(validation["v1_predicted_payoff_atr"]).all() or not np.isfinite(validation["payoff_atr_gross"]).all():
        raise PayoffDataBlocked("original V1 validation predictions/targets are non-finite")

    original_fold_metrics = pd.read_csv(original_output / "fold_metrics.csv")
    fold_metrics_sha = original_manifest.get("artifacts_sha256", {}).get("fold_metrics.csv")
    _require_sha(original_output / "fold_metrics.csv", fold_metrics_sha, "original V1 fold metrics")
    config = _default_config(external_root)
    _verify_frozen_sources(config)
    _, resolved = _reconstruct_training_targets(config)
    folds = _fold_definitions(Path(config["o2_fold_definitions_path"]))

    rows = []
    for fold in REQUIRED_FOLDS:
        fold_train_end = int(folds[fold].get("train_end", folds[fold].get("train_end_session_index")))
        train = resolved.loc[resolved.signal_session_index.le(fold_train_end), "payoff_atr_gross"]
        val = validation.loc[validation.fold.eq(fold)].copy()
        if val.empty or train.empty:
            raise PayoffDataBlocked(f"{fold} has empty training or validation target")
        train_mean = float(train.mean())
        baseline_mse = validation_baseline_mse(train_mean, val.payoff_atr_gross)
        model_mse = float(np.mean((val.v1_predicted_payoff_atr.to_numpy(dtype=float) - val.payoff_atr_gross.to_numpy(dtype=float)) ** 2))
        skill = corrected_mse_skill(model_mse, baseline_mse)
        original = original_fold_metrics.loc[original_fold_metrics.fold.eq(fold)]
        if len(original) != 1:
            raise PayoffDataBlocked(f"missing original metrics for {fold}")
        original_mse = float(original.iloc[0].mse_v1)
        if not np.isclose(model_mse, original_mse, rtol=0, atol=1e-12):
            raise PayoffDataBlocked(f"frozen V1 model MSE changed for {fold}")
        rows.append({
            "fold": fold,
            "train_end": fold_train_end,
            "train_rows": int(len(train)),
            "validation_rows": int(len(val)),
            "train_mean_payoff_atr": train_mean,
            "validation_baseline_mse": baseline_mse,
            "frozen_v1_validation_mse": model_mse,
            "corrected_mse_skill": skill,
            "original_incorrect_mse_skill": float(original.iloc[0].mse_skill),
            "median_session_ic_atr": float(original.iloc[0].median_session_ic_atr),
            "q25_session_ic_atr": float(original.iloc[0].q25_session_ic_atr),
            "mean_d10_minus_d1_mean_payoff_atr": float(original.iloc[0].mean_d10_minus_d1_mean_payoff_atr),
            "median_d10_minus_d1_mean_payoff_atr": float(original.iloc[0].median_d10_minus_d1_mean_payoff_atr),
        })
    corrected = pd.DataFrame(rows)
    if not (corrected.validation_rows == validation.groupby("fold").size().reindex(REQUIRED_FOLDS).to_numpy()).all():
        raise PayoffDataBlocked("corrected validation row counts changed")

    median_skill = float(corrected.corrected_mse_skill.median())
    positive_skill = int((corrected.corrected_mse_skill > 0).sum())
    median_ic = float(corrected.median_session_ic_atr.median())
    q25_ic = float(corrected.median_session_ic_atr.quantile(0.25))
    positive_ic = int((corrected.median_session_ic_atr > 0).sum())
    median_spread = float(corrected.mean_d10_minus_d1_mean_payoff_atr.median())
    positive_spread = int((corrected.mean_d10_minus_d1_mean_payoff_atr > 0).sum())
    verdict = (
        "EXPECTED_PAYOFF_V1_SURVIVOR"
        if median_skill > 0 and positive_skill >= 4
        and median_ic > 0 and q25_ic > 0 and positive_ic >= 4
        and median_spread > 0 and positive_spread >= 4
        else "EXPECTED_PAYOFF_V1_NO_SURVIVOR"
    )
    decision = {
        "status": "EXPECTED_PAYOFF_V1_MSE_CORRECTION_COMPLETE",
        "data_ready": True,
        "corrected_verdict": verdict,
        "median_corrected_mse_skill": median_skill,
        "positive_corrected_mse_skill_folds": positive_skill,
        "median_session_ic_atr_unchanged": median_ic,
        "q25_session_ic_atr_unchanged": q25_ic,
        "positive_ic_folds_unchanged": positive_ic,
        "median_d10_minus_d1_mean_payoff_atr_unchanged": median_spread,
        "positive_spread_folds_unchanged": positive_spread,
        "original_runtime_verdict_superseded_for_mse_gate": original_manifest.get("status"),
        "runtime_flags": {
            "model_refit": False, "provider_calls": False,
            "o2_rescored": False, "fresh_forward_outcomes_accessed": False,
            "forward_outcome_access_marker_written": False,
        },
    }
    contract = {
        "correction": "TRAIN_MEAN_PAYOFF_VALIDATION_MSE_ONLY",
        "original_manifest_sha256": EXPECTED_ORIGINAL_MANIFEST_SHA256,
        "validation_predictions_sha256": validation_sha,
        "validation_key_sha256": validation_key_sha,
        "validation_rows": int(len(validation)),
        "source_cutoff": "2026-07-31",
        "model_refit": False,
        "provider_calls": False,
        "fresh_forward_outcomes_accessed": False,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(correction_output / "correction_contract.json", contract)
    corrected.to_csv(correction_output / "corrected_mse_metrics.csv", index=False)
    corrected[["fold", "train_end", "train_rows", "validation_rows", "train_mean_payoff_atr"]].to_csv(correction_output / "training_mean_summary.csv", index=False)
    _write_json(correction_output / "corrected_survivor_decision.json", decision)
    artifact_hashes = {
        path.name: sha256_file(path)
        for path in correction_output.iterdir()
        if path.is_file()
    }
    manifest = {
        "status": "EXPECTED_PAYOFF_V1_MSE_CORRECTION_COMPLETE",
        "corrected_verdict": verdict,
        "original_runtime_manifest_sha256": EXPECTED_ORIGINAL_MANIFEST_SHA256,
        "artifact_sha256": artifact_hashes,
        "metrics": decision,
        "runtime_flags": decision["runtime_flags"],
    }
    _write_json(correction_output / "correction_manifest.json", manifest)
    return {
        "corrected": corrected,
        "decision": decision,
        "manifest_sha256": sha256_file(correction_output / "correction_manifest.json"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-root", type=Path, required=True)
    parser.add_argument("--original-output", type=Path, required=True)
    parser.add_argument("--correction-output", type=Path, required=True)
    args = parser.parse_args()
    result = run_metric_correction(
        external_root=args.external_root,
        original_output=args.original_output,
        correction_output=args.correction_output,
    )
    print(json.dumps({"decision": result["decision"], "manifest_sha256": result["manifest_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
