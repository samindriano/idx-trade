from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.impute import SimpleImputer

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
from .research_stage5 import assign_within_date_buckets
from .research_v2_models import HGB_XS_MARKET, candidate_feature_columns, pointwise_model, pointwise_raw_score
from .research_v2_validation import RANKING_V2_FOLDS, evaluate_v2_scores, split_v2_model_table
from .stage5_ranking_holdout import _assert_environment


V3_E_HYPOTHESIS_ID = "V3-E-TRUE-RANKING-V1"
V3_E_CONTROL = "V3-E-TRUE-RANKING-V1-CONTROL-010"
V3_E_LAMBDAMART = "V3-E-TRUE-RANKING-V1-LAMBDAMART-011"
V3_E_CANDIDATES = (V3_E_CONTROL, V3_E_LAMBDAMART)
V3_E_FEATURE_COLUMNS = tuple(candidate_feature_columns(HGB_XS_MARKET))

MAX_DISCOVERY_SIGNAL_INDEX = 984
SEALED_FOLD_NAMES = frozenset(fold.name for fold in RANKING_V2_FOLDS[4:])

PREPARED_CACHE_SHA256 = "522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5"
PREPARED_MANIFEST_SHA256 = "6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143"
V2_REFERENCE_SUMMARY_SHA256 = "24cd9c6d1a978b35126955802fcf4852e1f3d50a489540b761052a9221a5327d"
V2_REFERENCE_PREDICTIONS_SHA256 = "5a9df1c66a34c0d54760015c49ccb356be984703935c96ee8218ae863c47b179"
TRUE_RANKING_SPEC_SHA256 = "79534d29d414a08b60cca85e68e8781849aabefa1a103d9f43ab0ead47308c55"
TRUE_RANKING_SPEC_GIT_BLOB = "20df2927b6663ea16955919760db9c1429cff3a5"
TRUE_RANKING_ADDENDUM_SHA256 = "6652e1f934f58630619a9cab5afb0bdfaa3317894977bad8bfa9ca5ffe980812"
TRUE_RANKING_ADDENDUM_GIT_BLOB = "01c4dca87ff52fca678c948e4ee23d3e3c82dbcd"
FROZEN_XGBOOST_VERSION = "3.2.1"

RANKER_PARAMS: dict[str, Any] = {
    "objective": "rank:ndcg",
    "n_estimators": 200,
    "learning_rate": 0.05,
    "max_depth": 5,
    "min_child_weight": 1.0,
    "reg_lambda": 1.0,
    "reg_alpha": 0.0,
    "gamma": 0.0,
    "subsample": 1.0,
    "colsample_bytree": 1.0,
    "tree_method": "hist",
    "random_state": 42,
    "n_jobs": 1,
    "verbosity": 0,
    "ndcg_exp_gain": True,
    "lambdarank_pair_method": "mean",
    "lambdarank_num_pair_per_sample": 8,
    "lambdarank_normalization": True,
}


def preregistered_ledger_rows() -> list[dict[str, Any]]:
    return [
        {
            "hypothesis_id": V3_E_HYPOTHESIS_ID,
            "candidate_id": V3_E_CONTROL,
            "candidate_ordinal": 10,
            "result_status": "IMPLEMENTED_NOT_RUN",
            "result_viewed": False,
            "verdict": "PENDING_RUN",
            "cumulative_candidate_count": 7,
        },
        {
            "hypothesis_id": V3_E_HYPOTHESIS_ID,
            "candidate_id": V3_E_LAMBDAMART,
            "candidate_ordinal": 11,
            "result_status": "IMPLEMENTED_NOT_RUN",
            "result_viewed": False,
            "verdict": "PENDING_RUN",
            "cumulative_candidate_count": 7,
        },
    ]


def assert_discovery_fold_allowed(name: str) -> None:
    allowed = {fold.name for fold in DISCOVERY_FOLDS}
    if name in SEALED_FOLD_NAMES or name not in allowed:
        raise PermissionError(f"{name} is sealed for V3-E true-ranking discovery")


def _git_blob_sha1(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload, usedforsecurity=False).hexdigest()


def _assert_xgboost_version() -> str:
    version = str(xgb.__version__)
    if version != FROZEN_XGBOOST_VERSION:
        raise RuntimeError(
            f"V3-E requires xgboost=={FROZEN_XGBOOST_VERSION}, actual={version}"
        )
    return version


def build_imputer() -> SimpleImputer:
    return SimpleImputer(
        strategy="median",
        add_indicator=True,
        keep_empty_features=True,
    )


def build_lambdamart() -> xgb.XGBRanker:
    _assert_xgboost_version()
    return xgb.XGBRanker(**RANKER_PARAMS)


def _feature_order_sha256() -> str:
    payload = "\n".join(V3_E_FEATURE_COLUMNS).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _assert_contract_files(
    *,
    prepared_table_path: Path,
    prepared_manifest_path: Path,
    spec_path: Path,
    addendum_path: Path,
) -> dict[str, str]:
    if prepared_table_path.suffix.lower() not in {".parquet", ".pq"}:
        raise RuntimeError("V3-E frozen prepared table must be Parquet for sealed-row filtering")
    hashes = {
        "prepared_table": sha256_file(prepared_table_path),
        "prepared_manifest": sha256_file(prepared_manifest_path),
        "spec": sha256_file(spec_path),
        "addendum": sha256_file(addendum_path),
        "spec_git_blob": _git_blob_sha1(spec_path),
        "addendum_git_blob": _git_blob_sha1(addendum_path),
    }
    expected = {
        "prepared_table": PREPARED_CACHE_SHA256,
        "prepared_manifest": PREPARED_MANIFEST_SHA256,
        "spec": TRUE_RANKING_SPEC_SHA256,
        "addendum": TRUE_RANKING_ADDENDUM_SHA256,
        "spec_git_blob": TRUE_RANKING_SPEC_GIT_BLOB,
        "addendum_git_blob": TRUE_RANKING_ADDENDUM_GIT_BLOB,
    }
    for key, value in expected.items():
        if hashes[key] != value:
            raise RuntimeError(
                f"V3-E contract identity mismatch {key}: expected={value} actual={hashes[key]}"
            )
    return hashes


def read_discovery_table(prepared_table_path: Path) -> pd.DataFrame:
    if prepared_table_path.suffix.lower() not in {".parquet", ".pq"}:
        raise RuntimeError("V3-E discovery read requires Parquet")
    raw = pd.read_parquet(
        prepared_table_path,
        filters=[("signal_session_index", "<=", MAX_DISCOVERY_SIGNAL_INDEX)],
    )
    table = _normalize_candidate_table(raw, HGB_XS_MARKET)
    if table.empty:
        raise RuntimeError("V3-E discovery table is empty")
    maximum = int(table["signal_session_index"].max())
    if maximum > MAX_DISCOVERY_SIGNAL_INDEX:
        raise RuntimeError("V3-E discovery table materialized sealed sessions")
    allowed_validation_end = max(fold.validation_end for fold in DISCOVERY_FOLDS)
    if maximum > allowed_validation_end:
        raise RuntimeError("V3-E discovery table exceeds F1-F4 boundary")
    return table


def build_query_training_frame(train: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray, dict[str, Any]]:
    required = {"ticker", "date", "binary_target", *V3_E_FEATURE_COLUMNS}
    missing = required - set(train.columns)
    if missing:
        raise ValueError(f"V3-E train table missing columns: {sorted(missing)}")
    data = train.copy()
    data["date"] = pd.to_datetime(data["date"], errors="raise").dt.tz_localize(None).dt.normalize()
    data["ticker"] = data["ticker"].astype(str)
    data = data.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)

    qid, unique_dates = pd.factorize(data["date"], sort=True)
    qid = np.asarray(qid, dtype=np.int64)
    if len(qid) != len(data):
        raise RuntimeError("V3-E qid length mismatch")
    if len(qid) and (np.diff(qid) < 0).any():
        raise RuntimeError("V3-E qid must be nondecreasing")
    if int(qid.min()) != 0 or int(qid.max()) + 1 != len(unique_dates):
        raise RuntimeError("V3-E qid must be contiguous zero-based date groups")

    group = data.groupby("date", sort=True)["binary_target"]
    sizes = group.size().astype(int)
    positives = group.sum().astype(int)
    all_zero = positives.eq(0)
    all_one = positives.eq(sizes)
    mixed = ~(all_zero | all_one)

    y = pd.to_numeric(data["binary_target"], errors="raise").astype(int)
    if not set(y.unique()).issubset({0, 1}):
        raise RuntimeError("V3-E training labels must remain binary")
    if y.nunique() != 2:
        raise RuntimeError("V3-E training fold requires both target classes overall")

    diagnostics = {
        "rows": int(len(data)),
        "query_dates": int(len(sizes)),
        "mixed_label_queries": int(mixed.sum()),
        "all_zero_queries": int(all_zero.sum()),
        "all_one_queries": int(all_one.sum()),
        "query_rows_min": int(sizes.min()),
        "query_rows_q25": float(sizes.quantile(0.25)),
        "query_rows_median": float(sizes.median()),
        "query_rows_max": int(sizes.max()),
        "positive_rows": int(y.sum()),
        "negative_rows": int(len(y) - y.sum()),
        "rows_dropped": 0,
    }
    if diagnostics["query_dates"] != int(data["date"].nunique()):
        raise RuntimeError("V3-E query-date count mismatch")
    return data, qid, diagnostics


def _fit_lambdamart(
    train: pd.DataFrame,
    *,
    fold_name: str,
    output_dir: Path,
) -> tuple[SimpleImputer, xgb.XGBRanker, dict[str, Any], dict[str, str]]:
    assert_discovery_fold_allowed(fold_name)
    sorted_train, qid, diagnostics = build_query_training_frame(train)
    features = sorted_train.loc[:, V3_E_FEATURE_COLUMNS]
    y = sorted_train["binary_target"].to_numpy(dtype=int)

    imputer = build_imputer()
    transformed = imputer.fit_transform(features)
    if transformed.shape[0] != len(sorted_train):
        raise RuntimeError("V3-E imputer dropped training rows")
    if not np.isfinite(np.asarray(transformed, dtype=float)).all():
        raise RuntimeError("V3-E imputed training features must be finite")
    diagnostics["imputed_feature_columns"] = int(transformed.shape[1])
    diagnostics["rows_after_preprocess"] = int(transformed.shape[0])
    diagnostics["rows_dropped"] = int(len(sorted_train) - transformed.shape[0])

    ranker = build_lambdamart()
    ranker.fit(transformed, y, qid=qid, verbose=False)

    imputer_path = output_dir / f"ranking_v3_e_lambdamart_{fold_name.lower()}_imputer.joblib"
    model_path = output_dir / f"ranking_v3_e_lambdamart_{fold_name.lower()}.json"
    params_path = output_dir / f"ranking_v3_e_lambdamart_{fold_name.lower()}_params.json"
    joblib.dump(imputer, imputer_path)
    ranker.save_model(str(model_path))
    params_path.write_text(
        json.dumps(ranker.get_params(), indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    hashes = {
        imputer_path.name: sha256_file(imputer_path),
        model_path.name: sha256_file(model_path),
        params_path.name: sha256_file(params_path),
    }
    return imputer, ranker, diagnostics, hashes


def _score_control(
    table: pd.DataFrame,
    *,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    metrics_rows: list[dict[str, Any]] = []
    prediction_rows: list[pd.DataFrame] = []
    model_hashes: dict[str, str] = {}
    for fold in DISCOVERY_FOLDS:
        assert_discovery_fold_allowed(fold.name)
        train, validation = split_v2_model_table(table, fold)
        model = pointwise_model(HGB_XS_MARKET)
        model.fit(train, train["binary_target"].to_numpy(dtype=int))
        score = pointwise_raw_score(model, validation)
        if not np.isfinite(score).all():
            raise RuntimeError(f"V3-E control {fold.name} produced non-finite scores")
        metrics_rows.append(
            {
                "candidate": V3_E_CONTROL,
                "fold": fold.name,
                "train_rows": int(len(train)),
                "validation_rows": int(len(validation)),
                **evaluate_v2_scores(validation, score),
            }
        )
        scored = validation[
            ["ticker", "date", "signal_session_index", "binary_target"]
        ].copy()
        scored.insert(0, "fold", fold.name)
        scored.insert(0, "candidate", V3_E_CONTROL)
        scored["score"] = score
        prediction_rows.append(scored)
        model_path = output_dir / f"ranking_v3_e_control_{fold.name.lower()}.joblib"
        joblib.dump(model, model_path)
        model_hashes[model_path.name] = sha256_file(model_path)
    return (
        pd.DataFrame(metrics_rows),
        pd.concat(prediction_rows, ignore_index=True),
        model_hashes,
    )


def _score_lambdamart(
    table: pd.DataFrame,
    *,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, str]]:
    metrics_rows: list[dict[str, Any]] = []
    prediction_rows: list[pd.DataFrame] = []
    query_rows: list[dict[str, Any]] = []
    model_hashes: dict[str, str] = {}

    for fold in DISCOVERY_FOLDS:
        assert_discovery_fold_allowed(fold.name)
        train, validation = split_v2_model_table(table, fold)
        validation_identity = validation[
            ["ticker", "date", "signal_session_index", "binary_target"]
        ].copy().reset_index(drop=True)

        imputer, ranker, query_diag, hashes = _fit_lambdamart(
            train,
            fold_name=fold.name,
            output_dir=output_dir,
        )
        model_hashes.update(hashes)

        transformed = imputer.transform(validation.loc[:, V3_E_FEATURE_COLUMNS])
        if transformed.shape[0] != len(validation):
            raise RuntimeError("V3-E imputer dropped validation rows")
        if not np.isfinite(np.asarray(transformed, dtype=float)).all():
            raise RuntimeError("V3-E imputed validation features must be finite")
        score = np.asarray(ranker.predict(transformed), dtype=float)
        if score.shape != (len(validation),):
            raise RuntimeError("V3-E LambdaMART score shape mismatch")
        if not np.isfinite(score).all():
            raise RuntimeError(f"V3-E LambdaMART {fold.name} produced non-finite scores")
        if np.unique(score).size < 2:
            raise RuntimeError(f"V3-E LambdaMART {fold.name} produced globally constant scores")

        metrics_rows.append(
            {
                "candidate": V3_E_LAMBDAMART,
                "fold": fold.name,
                "train_rows": int(len(train)),
                "validation_rows": int(len(validation)),
                **evaluate_v2_scores(validation, score),
            }
        )
        scored = validation_identity.copy()
        scored.insert(0, "fold", fold.name)
        scored.insert(0, "candidate", V3_E_LAMBDAMART)
        scored["score"] = score
        if not scored[
            ["ticker", "date", "signal_session_index", "binary_target"]
        ].equals(validation_identity):
            raise RuntimeError("V3-E validation identity/order changed during scoring")
        prediction_rows.append(scored)

        query_rows.append(
            {
                "fold": fold.name,
                **query_diag,
                "validation_dates": int(validation["date"].nunique()),
                "validation_rows": int(len(validation)),
                "validation_rows_after_preprocess": int(transformed.shape[0]),
            }
        )

    return (
        pd.DataFrame(metrics_rows),
        pd.concat(prediction_rows, ignore_index=True),
        pd.DataFrame(query_rows),
        model_hashes,
    )


def _score_diversity(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for fold in [item.name for item in DISCOVERY_FOLDS]:
        block = predictions[predictions["fold"].eq(fold)].copy()
        if block.empty:
            raise RuntimeError(f"V3-E score-diversity missing {fold}")
        per_date = (
            block.groupby("date", sort=True)["score"]
            .agg(["size", "nunique"])
            .reset_index()
        )
        fraction = per_date["nunique"].astype(float) / per_date["size"].astype(float)
        rows.append(
            {
                "fold": fold,
                "validation_dates": int(len(per_date)),
                "global_unique_scores": int(block["score"].nunique()),
                "unique_score_fraction_median": float(fraction.median()),
                "unique_score_fraction_q25": float(fraction.quantile(0.25)),
                "unique_score_fraction_min": float(fraction.min()),
                "all_tied_dates": int(per_date["nunique"].eq(1).sum()),
            }
        )
    return pd.DataFrame(rows)


def _top_decile_overlap(
    control_predictions: pd.DataFrame,
    candidate_predictions: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for fold in [item.name for item in DISCOVERY_FOLDS]:
        control = control_predictions[control_predictions["fold"].eq(fold)].copy().reset_index(drop=True)
        candidate = candidate_predictions[candidate_predictions["fold"].eq(fold)].copy().reset_index(drop=True)
        identity = ["ticker", "date", "signal_session_index", "binary_target"]
        if not control[identity].equals(candidate[identity]):
            raise RuntimeError(f"V3-E top-decile identity mismatch for {fold}")
        control_bucketed = assign_within_date_buckets(
            control,
            score_column="score",
            buckets=10,
            output_column="decile",
        )
        candidate_bucketed = assign_within_date_buckets(
            candidate,
            score_column="score",
            buckets=10,
            output_column="decile",
        )
        control_top = control_bucketed[control_bucketed["decile"].eq(10)]
        candidate_top = candidate_bucketed[candidate_bucketed["decile"].eq(10)]
        control_keys = set(zip(control_top["date"], control_top["ticker"], strict=False))
        candidate_keys = set(zip(candidate_top["date"], candidate_top["ticker"], strict=False))
        union = control_keys | candidate_keys
        overlap = control_keys & candidate_keys
        rows.append(
            {
                "fold": fold,
                "control_top_decile_rows": int(len(control_top)),
                "candidate_top_decile_rows": int(len(candidate_top)),
                "top_decile_jaccard": float(len(overlap) / len(union)) if union else 1.0,
                "top_decile_overlap_rows": int(len(overlap)),
                "top_decile_entrants": int(len(candidate_keys - control_keys)),
                "top_decile_exits": int(len(control_keys - candidate_keys)),
            }
        )
    return pd.DataFrame(rows)


def run_discovery(
    *,
    prepared_table_path: Path,
    prepared_manifest_path: Path,
    reference_v2_dir: Path,
    spec_path: Path,
    addendum_path: Path,
    output_dir: Path,
    code_commit: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    environment = _assert_environment()
    xgboost_version = _assert_xgboost_version()
    contract_hashes = _assert_contract_files(
        prepared_table_path=prepared_table_path,
        prepared_manifest_path=prepared_manifest_path,
        spec_path=spec_path,
        addendum_path=addendum_path,
    )
    _assert_clean_output_dir(output_dir)

    read_started = time.perf_counter()
    table = read_discovery_table(prepared_table_path)
    read_seconds = time.perf_counter() - read_started

    reference_summary, reference_metrics, reference_predictions, reference_hashes = _read_reference_artifacts(
        reference_v2_dir
    )
    if reference_hashes["summary"] != V2_REFERENCE_SUMMARY_SHA256:
        raise RuntimeError("V3-E frozen V2 reference summary hash mismatch")
    if reference_hashes["predictions"] != V2_REFERENCE_PREDICTIONS_SHA256:
        raise RuntimeError("V3-E frozen V2 reference predictions hash mismatch")

    control_dir = output_dir / "control"
    control_dir.mkdir(parents=True, exist_ok=False)
    control_started = time.perf_counter()
    control_metrics, control_predictions, control_models = _score_control(
        table,
        output_dir=control_dir,
    )
    control_seconds = time.perf_counter() - control_started

    equivalence = prove_control_equivalence(
        control_metrics=control_metrics,
        control_predictions=control_predictions,
        reference_metrics=reference_metrics,
        reference_predictions=reference_predictions,
        reference_hashes=reference_hashes,
    )
    equivalence["status"] = "V3_E_CONTROL_EQUIVALENCE_PASS"
    equivalence["reference_summary_identity"] = {
        "sha256": reference_hashes["summary"],
        "code_commit": reference_summary.get("code_commit"),
    }
    equivalence_path = output_dir / "ranking_v3_e_control_equivalence.json"
    equivalence_path.write_text(
        json.dumps(equivalence, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    ranker_dir = output_dir / "lambdamart"
    ranker_dir.mkdir(parents=True, exist_ok=False)
    ranker_started = time.perf_counter()
    candidate_metrics, candidate_predictions, query_diagnostics, ranker_models = _score_lambdamart(
        table,
        output_dir=ranker_dir,
    )
    ranker_seconds = time.perf_counter() - ranker_started

    control_aggregate = _aggregate_candidate(control_metrics)
    candidate_aggregate = _aggregate_candidate(candidate_metrics)
    paired_frame, paired_aggregate = _paired_metrics(candidate_metrics, control_metrics)
    absolute_pass = _absolute_sanity(candidate_aggregate)
    paired_pass = _paired_promotion(paired_aggregate)
    if absolute_pass and paired_pass:
        candidate_verdict = "PROMOTE_FOR_NEXT_RESEARCH_STEP"
        decision = "V3_E_TRUE_RANKING_PROMOTE_LAMBDAMART"
    else:
        candidate_verdict = "KEEP_DIAGNOSTIC"
        decision = "V3_E_TRUE_RANKING_KILL_KEEP_V2_CONTROL"

    diversity = _score_diversity(candidate_predictions)
    overlap = _top_decile_overlap(control_predictions, candidate_predictions)

    metrics_path = output_dir / "ranking_v3_e_true_ranking_f1_f4_metrics.csv"
    predictions_path = output_dir / "ranking_v3_e_true_ranking_f1_f4_predictions.parquet"
    paired_path = output_dir / "ranking_v3_e_true_ranking_paired.csv"
    query_path = output_dir / "ranking_v3_e_query_diagnostics.csv"
    diversity_path = output_dir / "ranking_v3_e_score_diversity.csv"
    overlap_path = output_dir / "ranking_v3_e_top_decile_overlap.csv"

    pd.concat([control_metrics, candidate_metrics], ignore_index=True).to_csv(metrics_path, index=False)
    pd.concat([control_predictions, candidate_predictions], ignore_index=True).to_parquet(
        predictions_path, index=False
    )
    paired_frame.insert(0, "candidate", V3_E_LAMBDAMART)
    paired_frame.to_csv(paired_path, index=False)
    query_diagnostics.to_csv(query_path, index=False)
    diversity.to_csv(diversity_path, index=False)
    overlap.to_csv(overlap_path, index=False)

    aggregate = {
        V3_E_CONTROL: control_aggregate,
        V3_E_LAMBDAMART: candidate_aggregate,
        "paired": paired_aggregate,
        "candidate_absolute_sanity_pass": bool(absolute_pass),
        "candidate_paired_promotion_pass": bool(paired_pass),
        "f4": {
            "control": control_metrics[control_metrics["fold"].eq("V2F4")].iloc[0].to_dict(),
            "candidate": candidate_metrics[candidate_metrics["fold"].eq("V2F4")].iloc[0].to_dict(),
        },
    }
    aggregate_path = output_dir / "ranking_v3_e_true_ranking_aggregate.json"
    aggregate_path.write_text(
        json.dumps(aggregate, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    verdict = {
        "status": decision,
        "control_verdict": "CONTROL_REFERENCE",
        "lambdamart_verdict": candidate_verdict,
        "selected_component": V3_E_LAMBDAMART if candidate_verdict == "PROMOTE_FOR_NEXT_RESEARCH_STEP" else None,
        "v2f5_v2f6_accessed": False,
        "fresh_forward_accessed": False,
        "probability_claim": False,
        "independent_validation_claim": False,
    }
    verdict_path = output_dir / "ranking_v3_e_true_ranking_verdict.json"
    verdict_path.write_text(json.dumps(verdict, indent=2, ensure_ascii=False), encoding="utf-8")

    ledger_rows = [
        {
            "hypothesis_id": V3_E_HYPOTHESIS_ID,
            "parent_hypothesis": "RANKING_V2_HGB_XS_MARKET",
            "candidate_id": V3_E_CONTROL,
            "candidate_ordinal": 10,
            "result_status": "COMPLETE",
            "result_viewed": True,
            "verdict": "CONTROL_REFERENCE",
            "cumulative_candidate_count": 8,
        },
        {
            "hypothesis_id": V3_E_HYPOTHESIS_ID,
            "parent_hypothesis": "RANKING_V2_HGB_XS_MARKET",
            "candidate_id": V3_E_LAMBDAMART,
            "candidate_ordinal": 11,
            "result_status": "COMPLETE",
            "result_viewed": True,
            "verdict": candidate_verdict,
            "cumulative_candidate_count": 9,
        },
    ]
    ledger_path = output_dir / "ranking_v3_e_true_ranking_ledger_rows.json"
    ledger_path.write_text(json.dumps(ledger_rows, indent=2, ensure_ascii=False), encoding="utf-8")

    runtime = {
        "mode": "sequential_reference",
        "read_seconds": read_seconds,
        "control_seconds": control_seconds,
        "lambdamart_seconds": ranker_seconds,
        "total_seconds": time.perf_counter() - started,
        "python": sys.version,
        "platform": platform.platform(),
        "environment": environment,
        "xgboost_version": xgboost_version,
        "ranker_params": build_lambdamart().get_params(),
    }
    runtime_path = output_dir / "ranking_v3_e_true_ranking_runtime.json"
    runtime_path.write_text(
        json.dumps(runtime, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    artifact_paths = [
        equivalence_path,
        metrics_path,
        predictions_path,
        paired_path,
        query_path,
        diversity_path,
        overlap_path,
        aggregate_path,
        verdict_path,
        ledger_path,
        runtime_path,
    ]
    artifacts = {path.name: sha256_file(path) for path in artifact_paths}
    artifacts.update(control_models)
    artifacts.update(ranker_models)

    summary = {
        "status": decision,
        "code_commit": code_commit,
        "hypothesis_id": V3_E_HYPOTHESIS_ID,
        "candidates": list(V3_E_CANDIDATES),
        "folds": [fold.name for fold in DISCOVERY_FOLDS],
        "prepared_cache_sha256": contract_hashes["prepared_table"],
        "prepared_manifest_sha256": contract_hashes["prepared_manifest"],
        "spec_sha256": contract_hashes["spec"],
        "spec_git_blob": contract_hashes["spec_git_blob"],
        "addendum_sha256": contract_hashes["addendum"],
        "addendum_git_blob": contract_hashes["addendum_git_blob"],
        "reference_sha256": reference_hashes,
        "control_equivalence_status": equivalence["status"],
        "feature_columns": list(V3_E_FEATURE_COLUMNS),
        "feature_order_sha256": _feature_order_sha256(),
        "xgboost_version": xgboost_version,
        "ranker_params": build_lambdamart().get_params(),
        "candidate_verdict": candidate_verdict,
        "artifact_sha256": artifacts,
        "v2f5_v2f6_accessed": False,
        "fresh_forward_accessed": False,
        "independent_validation_claim": False,
        "probability_claim": False,
    }
    summary_path = output_dir / "ranking_v3_e_true_ranking_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    summary["summary_sha256"] = sha256_file(summary_path)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run frozen Ranking V3-E true-ranking F1-F4 discovery"
    )
    parser.add_argument("--prepared-table", type=Path, required=True)
    parser.add_argument("--prepared-manifest", type=Path, required=True)
    parser.add_argument("--reference-v2-dir", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--addendum", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--code-commit", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_discovery(
        prepared_table_path=args.prepared_table,
        prepared_manifest_path=args.prepared_manifest,
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
