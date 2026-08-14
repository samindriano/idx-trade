"""One-shot Financial PIT Alpha V1 historical-era experiment.

The ``prepare`` phase is outcome-blind and freezes the inherited-fold
eligibility and exact Financial-support identities.  The ``run`` phase is the
single authorized historical label/model access point.  No forward artifacts,
provider calls, or canonical refit are part of this module.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any, Sequence

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from .financial_pit_alpha import (
    CANDIDATE_FEATURE_COLUMNS,
    CONTRACT_VERSION,
    DECISION_CUTOFF_CONTRACT,
    FINANCIAL_FEATURE_PANEL_SHA256,
    FINANCIAL_SLOT_COLUMNS,
    MISSING_HANDLING_CONTRACT,
    V2_COMMON_SUPPORT_SHA256,
    sha256_file,
)
from .open_alpha_historical import (
    EXPECTED_CLEAN_V2_LABEL_SOURCE_SHA256,
    HISTORICAL_BOUNDARY,
    _load_common_support,
    _ranking_metrics,
    raw_rank_score,
)
from .open_alpha_prereg import (
    CONTROL_HGB_PARAMETERS,
    CONTROL_MODEL,
    CONTROL_PREPROCESSING,
    FROZEN_V2_FOLDS,
    SURVIVOR_GATE_RULE,
    evaluate_survivor_gate,
    feature_order_sha256,
)


EXPECTED_SUPPORT_ROWS = 70_520
EXPECTED_SUPPORT_TICKERS = 321
EXPECTED_SUPPORT_KEYS_SHA256 = (
    "b1257db0a2fc175aab010f1ab1a925e3c7d949b43fe1dd332874382fd09ec00d"
)
EXPECTED_CENSUS_SUMMARY_SHA256 = (
    "e33ded6fcd6b12c6083c8e877ae78ce4a82d05279a4f3b62aee04f7f25d28343"
)
EXPECTED_MATRIX_SHA256 = (
    "464c2a18bd7b238f98c786365026466bfd52c514022b3ced09798b2654665471"
)
EXPECTED_MODEL_CONTRACT_SHA256 = (
    "a55526407183449e25f8334c03b4dd0d76ed9b95eb3041aa079217c2c9d4468a"
)
EXPECTED_FOLD_CENSUS_SHA256 = (
    "afecdbabdfda5545432e4629a725d4e3c6b5dd0c1fdcda8869c3103cd725cdd2"
)
EXPECTED_FOLD_MANIFEST_SHA256 = (
    "713ec8a5a2d17423a1367eaa7b752ad4efcab9badb0a02a78bcb6f1cb9fdb93f"
)
EXPECTED_FOLD_NAMES = ("V2F4", "V2F5", "V2F6")
ELIGIBILITY_RULE = {
    "train_support_rows": ">= 5000",
    "train_support_tickers": ">= 100",
    "validation_support_rows": ">= 5000",
    "validation_support_tickers": ">= 100",
}

PRIMARY_CONTROL = "CONTROL_FINANCIAL_ERA"
PRIMARY_CHALLENGER = "V2_PLUS_FINANCIAL"
DIAGNOSTIC_FINANCIAL_ONLY = "FINANCIAL_ONLY"
MODEL_ORDER = (PRIMARY_CONTROL, PRIMARY_CHALLENGER, DIAGNOSTIC_FINANCIAL_ONLY)
MODEL_FEATURES = {
    PRIMARY_CONTROL: CANDIDATE_FEATURE_COLUMNS["CONTROL"],
    PRIMARY_CHALLENGER: CANDIDATE_FEATURE_COLUMNS["V2_PLUS_FINANCIAL"],
    DIAGNOSTIC_FINANCIAL_ONLY: CANDIDATE_FEATURE_COLUMNS["FINANCIAL_ONLY"],
}
KEY_COLUMNS = ("ticker", "date", "signal_session_index")


def _empty_output(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise RuntimeError(f"output directory must be new or empty: {path}")
    path.mkdir(parents=True, exist_ok=True)


def _identity_sha(frame: pd.DataFrame) -> str:
    required = ["row_id", *KEY_COLUMNS]
    if not set(required).issubset(frame.columns):
        raise RuntimeError(f"identity frame missing columns: {required}")
    work = frame.loc[:, required].copy()
    work["ticker"] = work["ticker"].astype(str).str.upper().str.strip()
    work["date"] = pd.to_datetime(work["date"], errors="raise").dt.strftime("%Y-%m-%d")
    work["signal_session_index"] = pd.to_numeric(
        work["signal_session_index"], errors="raise"
    ).astype(int)
    work["row_id"] = pd.to_numeric(work["row_id"], errors="raise").astype(int)
    work = work.sort_values(required, kind="mergesort")
    payload = "".join(
        f"{row.row_id}|{row.ticker}|{row.date}|{row.signal_session_index}\n"
        for row in work.itertuples(index=False)
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_support_keys(census_dir: Path) -> tuple[pd.DataFrame, dict[str, str]]:
    path = census_dir / "comparison_support" / "comparison_support_keys.parquet"
    if not path.exists():
        raise RuntimeError(f"missing frozen comparison support: {path}")
    keys = pd.read_parquet(path)
    required = ["row_id", *KEY_COLUMNS, "decision_timestamp_utc"]
    if not set(required).issubset(keys.columns):
        raise RuntimeError("comparison support schema changed")
    if keys.duplicated(KEY_COLUMNS).any() or keys["row_id"].duplicated().any():
        raise RuntimeError("comparison support identities are not unique")
    keys["ticker"] = keys["ticker"].astype(str).str.upper().str.strip()
    keys["date"] = pd.to_datetime(keys["date"], errors="raise").dt.normalize()
    keys["signal_session_index"] = pd.to_numeric(
        keys["signal_session_index"], errors="raise"
    ).astype(int)
    if len(keys) != EXPECTED_SUPPORT_ROWS or keys["ticker"].nunique() != EXPECTED_SUPPORT_TICKERS:
        raise RuntimeError("Financial support population changed")
    support_sha = sha256_file(path)
    if support_sha != EXPECTED_SUPPORT_KEYS_SHA256:
        raise RuntimeError(f"Financial support key SHA mismatch: {support_sha}")
    return keys.sort_values(["signal_session_index", "ticker"], kind="mergesort").reset_index(drop=True), {
        "comparison_support_keys_sha256": support_sha,
        "comparison_support_identity_sha256": _identity_sha(keys),
    }


def _verify_pinned_census(census_dir: Path) -> dict[str, Any]:
    summary_path = census_dir / "support_census_summary.json"
    matrix_path = census_dir / "selected_slot_matrix.parquet"
    model_contract_path = census_dir / "financial_model_matrix_contract.json"
    fold_path = census_dir / "fold_support" / "inherited_fold_support_census.json"
    fold_manifest_path = census_dir / "fold_support" / "inherited_fold_support_manifest.json"
    for path in (summary_path, matrix_path, model_contract_path, fold_path, fold_manifest_path):
        if not path.exists():
            raise RuntimeError(f"missing pinned census artifact: {path}")
    hashes = {
        "support_census_summary": sha256_file(summary_path),
        "selected_slot_matrix": sha256_file(matrix_path),
        "financial_model_matrix_contract": sha256_file(model_contract_path),
        "inherited_fold_support_census": sha256_file(fold_path),
        "inherited_fold_support_manifest": sha256_file(fold_manifest_path),
    }
    expected = {
        "support_census_summary": EXPECTED_CENSUS_SUMMARY_SHA256,
        "selected_slot_matrix": EXPECTED_MATRIX_SHA256,
        "financial_model_matrix_contract": EXPECTED_MODEL_CONTRACT_SHA256,
        "inherited_fold_support_census": EXPECTED_FOLD_CENSUS_SHA256,
        "inherited_fold_support_manifest": EXPECTED_FOLD_MANIFEST_SHA256,
    }
    for name, value in hashes.items():
        if value != expected[name]:
            raise RuntimeError(f"{name} SHA mismatch: {value}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("contract_version") != CONTRACT_VERSION:
        raise RuntimeError("Financial census contract version changed")
    if summary.get("financial_any_feature_rows") != EXPECTED_SUPPORT_ROWS:
        raise RuntimeError("Financial census support row count changed")
    if summary.get("provider_calls") != 0 or summary.get("outcomes_accessed"):
        raise RuntimeError("census provenance indicates provider/outcome access")
    model_contract = json.loads(model_contract_path.read_text(encoding="utf-8"))
    if model_contract.get("metrics_computed") or model_contract.get("model_fit") or model_contract.get("outcomes_accessed"):
        raise RuntimeError("model contract is not outcome-blind")
    return {"hashes": hashes, "summary": summary, "model_contract": model_contract}


def _fold_blocks(fold: Any) -> dict[str, tuple[int, int]]:
    return {
        "train": (fold.train_start, fold.train_end),
        "purge": (fold.purge_start, fold.purge_end),
        "validation": (fold.validation_start, fold.validation_end),
    }


def _fold_support_details(keys: pd.DataFrame) -> dict[str, Any]:
    details: dict[str, Any] = {}
    for fold in FROZEN_V2_FOLDS:
        blocks: dict[str, Any] = {}
        for block_name, (start, end) in _fold_blocks(fold).items():
            block = keys[keys["signal_session_index"].between(start, end)].copy()
            blocks[block_name] = {
                "session_index_start": start,
                "session_index_end": end,
                "rows": int(len(block)),
                "tickers": int(block["ticker"].nunique()),
                "identity_sha256": _identity_sha(block),
            }
        details[fold.name] = blocks
    return details


def eligible_financial_folds(details: dict[str, Any]) -> list[str]:
    selected: list[str] = []
    for fold_name in (fold.name for fold in FROZEN_V2_FOLDS):
        blocks = details[fold_name]
        qualifies = (
            blocks["train"]["rows"] >= 5000
            and blocks["train"]["tickers"] >= 100
            and blocks["validation"]["rows"] >= 5000
            and blocks["validation"]["tickers"] >= 100
        )
        if qualifies:
            selected.append(fold_name)
    return selected


def freeze_financial_era_contract(*, census_dir: Path, output_dir: Path) -> dict[str, Any]:
    """Freeze the financial-era population before any label access."""

    _empty_output(output_dir)
    pinned = _verify_pinned_census(census_dir)
    keys, key_hashes = _load_support_keys(census_dir)
    details = _fold_support_details(keys)
    eligible = eligible_financial_folds(details)
    if eligible != list(EXPECTED_FOLD_NAMES):
        raise RuntimeError(f"unexpected Financial-era folds: {eligible}")
    contract = {
        "status": "FINANCIAL_PIT_ALPHA_V1_FINANCIAL_ERA_CONTRACT_FROZEN",
        "contract_version": CONTRACT_VERSION,
        "decision_cutoff_contract": DECISION_CUTOFF_CONTRACT,
        "session_role": "session-t Financial state is used for the 18:00 EOD ranking and first actionable from session t+1",
        "eligibility_rule": ELIGIBILITY_RULE,
        "eligible_folds": eligible,
        "excluded_folds": [fold.name for fold in FROZEN_V2_FOLDS if fold.name not in eligible],
        "fold_support": details,
        "support": {
            "rows": len(keys),
            "tickers": int(keys["ticker"].nunique()),
            **key_hashes,
        },
        "candidates": {
            "primary": [PRIMARY_CONTROL, PRIMARY_CHALLENGER],
            "diagnostic_only": [DIAGNOSTIC_FINANCIAL_ONLY],
            "feature_order_sha256": {
                name: feature_order_sha256(columns) for name, columns in MODEL_FEATURES.items()
            },
            "feature_counts": {name: len(columns) for name, columns in MODEL_FEATURES.items()},
        },
        "financial_slot_count": len(FINANCIAL_SLOT_COLUMNS),
        "preprocessing": {
            "family": CONTROL_PREPROCESSING,
            "missing_handling": MISSING_HANDLING_CONTRACT,
            "fit_scope": "training_fold_only",
        },
        "control_model": {
            "identity": CONTROL_MODEL,
            "hyperparameters": CONTROL_HGB_PARAMETERS,
        },
        "survivor_gate": SURVIVOR_GATE_RULE,
        "primary_comparison": f"{PRIMARY_CHALLENGER} vs {PRIMARY_CONTROL}",
        "diagnostic_promotion": "FINANCIAL_ONLY has no survivor or promotion path",
        "winner_rule": {
            "pass": "FINANCIAL_PIT_ALPHA_V1_SURVIVOR",
            "fail": "FINANCIAL_PIT_ALPHA_V1_NO_SURVIVOR",
            "no_rescue": True,
        },
        "input_hashes": {
            "financial_panel_sha256": FINANCIAL_FEATURE_PANEL_SHA256,
            "clean_v2_common_support_sha256": V2_COMMON_SUPPORT_SHA256,
            **pinned["hashes"],
        },
        "labels_loaded": False,
        "outcomes_accessed": False,
        "scores_computed": False,
        "metrics_computed": False,
    }
    path = output_dir / "financial_era_preregistration.json"
    path.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "files": {path.name: sha256_file(path)},
        "input_hashes": contract["input_hashes"],
        "labels_loaded": False,
        "outcomes_accessed": False,
    }
    manifest_path = output_dir / "financial_era_preregistration_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "contract": contract,
        "contract_path": str(path),
        "contract_sha256": sha256_file(path),
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
    }


def _financial_matrix(census_dir: Path) -> pd.DataFrame:
    matrix = pd.read_parquet(
        census_dir / "selected_slot_matrix.parquet",
        columns=["row_id", "feature_id", "period_stratum", "feature_value", "availability_status"],
    )
    matrix["slot"] = "financial__" + matrix["feature_id"].astype(str) + "__" + matrix["period_stratum"].astype(str)
    if matrix.duplicated(["row_id", "slot"]).any():
        raise RuntimeError("selected Financial matrix has duplicate row/slot identities")
    matrix["value"] = matrix["feature_value"].where(matrix["availability_status"].eq("AVAILABLE"))
    pivot = matrix.pivot(index="row_id", columns="slot", values="value")
    pivot = pivot.reindex(columns=list(FINANCIAL_SLOT_COLUMNS))
    pivot.columns.name = None
    return pivot.reset_index()


def _financial_model(columns: Sequence[str]) -> Pipeline:
    columns = tuple(columns)
    if columns not in MODEL_FEATURES.values():
        raise RuntimeError("unfrozen Financial Alpha feature order")
    preprocessor = ColumnTransformer(
        [
            (
                "numeric",
                Pipeline(
                    [
                        (
                            "impute",
                            SimpleImputer(
                                strategy="median",
                                add_indicator=True,
                                keep_empty_features=True,
                            ),
                        )
                    ]
                ),
                list(columns),
            )
        ],
        remainder="drop",
    )
    return Pipeline(
        [
            ("preprocess", preprocessor),
            ("model", HistGradientBoostingClassifier(**CONTROL_HGB_PARAMETERS)),
        ]
    )


def _pair(metrics: pd.DataFrame, candidate: str, comparator: str) -> pd.DataFrame:
    left = metrics[metrics["model"].eq(candidate)].copy()
    right = metrics[metrics["model"].eq(comparator)].copy()
    keep = ["fold", "pr_auc", "roc_auc", "q5_minus_q1", "top_decile_lift"]
    joined = left.merge(right[keep], on="fold", suffixes=("", "_comparator"), validate="one_to_one")
    joined["pr_auc_delta"] = joined["pr_auc"] - joined["pr_auc_comparator"]
    joined["roc_auc_delta"] = joined["roc_auc"] - joined["roc_auc_comparator"]
    joined["q5_minus_q1_delta"] = joined["q5_minus_q1"] - joined["q5_minus_q1_comparator"]
    joined["top_decile_lift_delta"] = joined["top_decile_lift"] - joined["top_decile_lift_comparator"]
    return joined.sort_values("fold").reset_index(drop=True)


def _hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)).replace("\\", "/"): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name not in {"artifact_manifest.json", "artifact_manifest.sha256"}
    }


def run_financial_era_experiment(
    *,
    common_support_path: Path,
    label_source_path: Path,
    census_dir: Path,
    contract_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Run exactly one historical Financial-era experiment."""

    _empty_output(output_dir)
    contract_path = contract_dir / "financial_era_preregistration.json"
    manifest_path = contract_dir / "financial_era_preregistration_manifest.json"
    if not contract_path.exists() or not manifest_path.exists():
        raise RuntimeError("frozen Financial-era contract is missing")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if contract.get("eligible_folds") != list(EXPECTED_FOLD_NAMES):
        raise RuntimeError("Financial-era contract eligibility changed")
    if contract.get("labels_loaded") or contract.get("outcomes_accessed"):
        raise RuntimeError("Financial-era contract is not pre-outcome")
    if contract_manifest.get("files", {}).get(contract_path.name) != sha256_file(contract_path):
        raise RuntimeError("Financial-era contract manifest does not match contract")
    pinned = _verify_pinned_census(census_dir)
    keys, key_hashes = _load_support_keys(census_dir)
    if key_hashes["comparison_support_keys_sha256"] != contract["support"]["comparison_support_keys_sha256"]:
        raise RuntimeError("support key hash changed after contract freeze")

    # This is the first operation in this function that opens the frozen H10
    # label artifact. All contract and input checks above are outcome-blind.
    table, label_hashes = _load_common_support(common_support_path, label_source_path)
    table = table.merge(keys, on=list(KEY_COLUMNS), how="inner", validate="one_to_one", suffixes=("", "_support"))
    if len(table) != EXPECTED_SUPPORT_ROWS or table["ticker"].nunique() != EXPECTED_SUPPORT_TICKERS:
        raise RuntimeError("labeled Financial support population changed")
    if table["row_id"].duplicated().any():
        raise RuntimeError("labeled Financial support row IDs are not unique")
    financial = _financial_matrix(census_dir)
    table = table.merge(financial, on="row_id", how="left", validate="one_to_one")
    if table.loc[:, list(FINANCIAL_SLOT_COLUMNS)].notna().sum(axis=1).eq(0).any():
        raise RuntimeError("Financial support contains a row with no usable Financial slot")

    started = time.perf_counter()
    metrics_rows: list[dict[str, Any]] = []
    prediction_rows: list[pd.DataFrame] = []
    model_hashes: dict[str, str] = {}
    models_dir = output_dir / "fold_models"
    models_dir.mkdir()
    eligible_folds = [fold for fold in FROZEN_V2_FOLDS if fold.name in EXPECTED_FOLD_NAMES]
    for fold in eligible_folds:
        train = table[table["signal_session_index"].between(fold.train_start, fold.train_end)].copy()
        validation = table[table["signal_session_index"].between(fold.validation_start, fold.validation_end)].copy()
        if len(train) < 5000 or train["ticker"].nunique() < 100 or len(validation) < 5000 or validation["ticker"].nunique() < 100:
            raise RuntimeError(f"{fold.name} no longer satisfies frozen eligibility")
        if np.unique(train["binary_target"]).size != 2 or np.unique(validation["binary_target"]).size != 2:
            raise RuntimeError(f"{fold.name} target classes are not binary-complete")
        for model_name in MODEL_ORDER:
            columns = MODEL_FEATURES[model_name]
            model = _financial_model(columns)
            model.fit(train.loc[:, columns], train["binary_target"].to_numpy(dtype=int))
            scores = raw_rank_score(model, validation.loc[:, columns])
            if not np.isfinite(scores).all():
                raise RuntimeError(f"{model_name} {fold.name} produced non-finite scores")
            metrics_rows.append(
                {
                    "model": model_name,
                    "fold": fold.name,
                    **fold.__dict__,
                    "train_rows": int(len(train)),
                    "train_tickers": int(train["ticker"].nunique()),
                    "validation_rows": int(len(validation)),
                    "validation_tickers": int(validation["ticker"].nunique()),
                    "feature_count": len(columns),
                    "feature_order_sha256": feature_order_sha256(columns),
                    **_ranking_metrics(validation, scores),
                }
            )
            prediction = validation[["ticker", "date", "signal_session_index", "binary_target", "label_status"]].copy()
            prediction["model"] = model_name
            prediction["fold"] = fold.name
            prediction["score"] = scores
            prediction_rows.append(prediction)
            model_path = models_dir / f"{model_name.lower()}_{fold.name.lower()}.joblib"
            joblib.dump(model, model_path)
            model_hashes[model_path.name] = sha256_file(model_path)

    metrics = pd.DataFrame(metrics_rows).sort_values(["model", "fold"]).reset_index(drop=True)
    predictions = pd.concat(prediction_rows, ignore_index=True).sort_values(
        ["model", "fold", "signal_session_index", "ticker"], kind="mergesort"
    ).reset_index(drop=True)
    for fold_name in EXPECTED_FOLD_NAMES:
        blocks = [
            predictions[(predictions["fold"] == fold_name) & (predictions["model"] == model)][KEY_COLUMNS].reset_index(drop=True)
            for model in MODEL_ORDER
        ]
        if not (blocks[0].equals(blocks[1]) and blocks[0].equals(blocks[2])):
            raise RuntimeError(f"same-fold prediction identities differ in {fold_name}")

    metrics.to_csv(output_dir / "fold_metrics.csv", index=False)
    predictions.to_parquet(output_dir / "predictions.parquet", index=False)
    table.to_parquet(output_dir / "labeled_financial_era_support.parquet", index=False)

    primary_pair = _pair(metrics, PRIMARY_CHALLENGER, PRIMARY_CONTROL)
    diagnostic_pair = _pair(metrics, DIAGNOSTIC_FINANCIAL_ONLY, PRIMARY_CONTROL)
    primary_pair.to_csv(output_dir / "paired_v2_plus_financial_vs_control.csv", index=False)
    diagnostic_pair.to_csv(output_dir / "paired_financial_only_vs_control_diagnostic.csv", index=False)
    aggregate = metrics.groupby("model", sort=False).agg(
        folds=("fold", "count"),
        mean_pr_auc=("pr_auc", "mean"),
        median_pr_auc=("pr_auc", "median"),
        mean_pr_auc_minus_prevalence=("pr_auc_minus_prevalence", "mean"),
        median_roc_auc=("roc_auc", "median"),
        median_q5_minus_q1=("q5_minus_q1", "median"),
        median_top_decile_lift=("top_decile_lift", "median"),
    ).reset_index()
    aggregate.to_csv(output_dir / "aggregate_metrics.csv", index=False)
    gate = evaluate_survivor_gate(
        primary_pair["pr_auc_delta"].tolist(),
        primary_pair["roc_auc"].tolist(),
        primary_pair["roc_auc_comparator"].tolist(),
        primary_pair["q5_minus_q1"].tolist(),
        primary_pair["q5_minus_q1_comparator"].tolist(),
    )
    verdict = (
        "FINANCIAL_PIT_ALPHA_V1_SURVIVOR"
        if gate["survives"]
        else "FINANCIAL_PIT_ALPHA_V1_NO_SURVIVOR"
    )
    summary = {
        "status": "FINANCIAL_PIT_ALPHA_V1_HISTORICAL_RUN_COMPLETE",
        "verdict": verdict,
        "primary_comparison": f"{PRIMARY_CHALLENGER} vs {PRIMARY_CONTROL}",
        "diagnostic_candidate": DIAGNOSTIC_FINANCIAL_ONLY,
        "eligible_folds": list(EXPECTED_FOLD_NAMES),
        "fold_support": contract["fold_support"],
        "input_hashes": {
            "common_support_sha256": sha256_file(common_support_path),
            "clean_v2_label_source_sha256": label_hashes["clean_v2_label_source_sha256"],
            "comparison_support_keys_sha256": key_hashes["comparison_support_keys_sha256"],
            "selected_slot_matrix_sha256": pinned["hashes"]["selected_slot_matrix"],
            "financial_panel_sha256": FINANCIAL_FEATURE_PANEL_SHA256,
        },
        "feature_order_sha256": {
            name: feature_order_sha256(columns) for name, columns in MODEL_FEATURES.items()
        },
        "gate": gate,
        "model_hashes": model_hashes,
        "labels_loaded": True,
        "outcomes_accessed": True,
        "protected_forward_outcomes_accessed": False,
        "provider_calls": 0,
        "runtime_seconds": round(time.perf_counter() - started, 6),
        "historical_boundary": str(HISTORICAL_BOUNDARY.date()),
        "model_fit": True,
        "score_computed": True,
        "metrics_computed": True,
        "fresh_forward_accessed": False,
        "o2_accessed": False,
        "canonical_refit": False,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    manifest = {
        "schema": "idx-trade/financial-pit-alpha-v1-financial-era-historical-v1",
        "artifact_sha256": _hashes(output_dir),
        "source_sha256": summary["input_hashes"],
        "model_hashes": model_hashes,
        "summary_sha256": sha256_file(output_dir / "summary.json"),
        "protected_forward_outcomes_accessed": False,
    }
    manifest_path = output_dir / "artifact_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_sha = sha256_file(manifest_path)
    (output_dir / "artifact_manifest.sha256").write_text(f"{manifest_sha}  artifact_manifest.json\n", encoding="utf-8")
    return {
        "verdict": verdict,
        "summary_sha256": sha256_file(output_dir / "summary.json"),
        "artifact_manifest_sha256": manifest_sha,
        "artifact_count": len(manifest["artifact_sha256"]),
        "runtime_seconds": summary["runtime_seconds"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--census-dir", type=Path, required=True)
    prepare.add_argument("--output-dir", type=Path, required=True)
    run = sub.add_parser("run")
    run.add_argument("--common-support-path", type=Path, required=True)
    run.add_argument("--label-source-path", type=Path, required=True)
    run.add_argument("--census-dir", type=Path, required=True)
    run.add_argument("--contract-dir", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "prepare":
        result = freeze_financial_era_contract(census_dir=args.census_dir, output_dir=args.output_dir)
        print(json.dumps({"status": result["contract"]["status"], "eligible_folds": result["contract"]["eligible_folds"], "contract_sha256": result["contract_sha256"], "manifest_sha256": result["manifest_sha256"]}, indent=2, sort_keys=True))
        return 0
    result = run_financial_era_experiment(**vars(args))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
