from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .provenance import sha256_file
from .research_stage5 import assign_within_date_buckets, bucket_summary
from .research_v2_models import (
    ALL_RANKING_V2_MODELS,
    PAIRWISE_LOGISTIC_XS,
    PairwiseLogisticRanker,
    candidate_feature_columns,
    pointwise_model,
    pointwise_raw_score,
)
from .research_v2_validation import RANKING_V2_FOLDS, evaluate_v2_scores, split_v2_model_table
from .stage5_ranking_holdout import _assert_environment


def _read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"unsupported Ranking V2 table format: {path}")


def _assert_clean_output_dir(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise RuntimeError("Ranking V2 candidate output directory must be new or empty")
    path.mkdir(parents=True, exist_ok=True)


def _normalize_candidate_table(table: pd.DataFrame, candidate: str) -> pd.DataFrame:
    required = {
        "ticker",
        "date",
        "signal_session_index",
        "binary_target",
        "label_status",
        "universe_primary_liquid",
        *candidate_feature_columns(candidate),
    }
    missing = required - set(table.columns)
    if missing:
        raise ValueError(f"Ranking V2 prepared table missing {sorted(missing)}")
    data = table.copy()
    data["ticker"] = data["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if data["date"].isna().any():
        raise ValueError("Ranking V2 prepared table contains invalid dates")
    data["signal_session_index"] = pd.to_numeric(data["signal_session_index"], errors="raise").astype(int)
    data["binary_target"] = pd.to_numeric(data["binary_target"], errors="raise").astype(int)
    if not set(data["binary_target"].unique()).issubset({0, 1}):
        raise ValueError("Ranking V2 binary_target must contain only 0/1")
    if data.duplicated(["ticker", "date"]).any():
        raise ValueError("Ranking V2 prepared table contains duplicate ticker/date rows")
    if not data["universe_primary_liquid"].astype(bool).all():
        raise ValueError("Ranking V2 prepared model table must contain primary-liquid rows only")
    if not data["label_status"].isin(["TP_FIRST", "SL_FIRST"]).all():
        raise ValueError("Ranking V2 prepared model table must contain resolved H10 rows only")
    if data["signal_session_index"].min() < 1 or data["signal_session_index"].max() > 1250:
        raise ValueError("Ranking V2 prepared H10 rows must stay inside signal sessions 1..1250")
    return data.sort_values(["signal_session_index", "ticker"], kind="mergesort").reset_index(drop=True)


def _bucket_rows(scored: pd.DataFrame, *, buckets: int, bucket_name: str) -> pd.DataFrame:
    bucketed = assign_within_date_buckets(
        scored,
        score_column="score",
        buckets=buckets,
        output_column=bucket_name,
    )
    summary = bucket_summary(bucketed, bucket_column=bucket_name)
    return summary.rename(columns={"bucket": bucket_name})


def run_candidate(
    *,
    prepared_table_path: Path,
    expected_cache_sha256: str,
    candidate: str,
    output_dir: Path,
    code_commit: str,
) -> dict[str, object]:
    if candidate not in ALL_RANKING_V2_MODELS:
        raise ValueError(f"unknown Ranking V2 candidate: {candidate}")
    environment = _assert_environment()
    actual_cache_sha = sha256_file(prepared_table_path)
    if actual_cache_sha != expected_cache_sha256:
        raise RuntimeError(
            f"Ranking V2 prepared-cache hash mismatch: expected={expected_cache_sha256} actual={actual_cache_sha}"
        )
    _assert_clean_output_dir(output_dir)
    table = _normalize_candidate_table(_read_table(prepared_table_path), candidate)

    metrics_rows: list[dict[str, object]] = []
    prediction_rows: list[pd.DataFrame] = []
    quintile_rows: list[pd.DataFrame] = []
    decile_rows: list[pd.DataFrame] = []
    model_hashes: dict[str, str] = {}
    pairwise_diagnostics: dict[str, dict[str, int]] = {}

    for fold in RANKING_V2_FOLDS:
        train, validation = split_v2_model_table(table, fold)
        y_train = train["binary_target"].to_numpy(dtype=int)
        if candidate == PAIRWISE_LOGISTIC_XS:
            fitted = PairwiseLogisticRanker().fit(train, y_train)
            score = fitted.score(validation)
            pairwise_diagnostics[fold.name] = {
                "pair_days": int(fitted.fitted_pair_days),
                "unique_pairs": int(fitted.fitted_unique_pairs),
            }
            model_object = fitted
        else:
            fitted = pointwise_model(candidate)
            fitted.fit(train, y_train)
            score = pointwise_raw_score(fitted, validation)
            model_object = fitted

        if not np.isfinite(score).all():
            raise RuntimeError(f"{candidate} {fold.name} produced non-finite ranking scores")
        metric = evaluate_v2_scores(validation, score)
        metrics_rows.append(
            {
                "candidate": candidate,
                "fold": fold.name,
                "train_start": fold.train_start,
                "train_end": fold.train_end,
                "gap_start": fold.gap_start,
                "gap_end": fold.gap_end,
                "validation_start": fold.validation_start,
                "validation_end": fold.validation_end,
                "train_rows": int(len(train)),
                "validation_rows": int(len(validation)),
                **metric,
            }
        )

        scored = validation[["ticker", "date", "signal_session_index", "binary_target"]].copy()
        scored.insert(0, "fold", fold.name)
        scored.insert(0, "candidate", candidate)
        scored["score"] = score
        prediction_rows.append(scored)

        quintiles = _bucket_rows(scored, buckets=5, bucket_name="quintile")
        quintiles.insert(0, "fold", fold.name)
        quintiles.insert(0, "candidate", candidate)
        quintile_rows.append(quintiles)

        deciles = _bucket_rows(scored, buckets=10, bucket_name="decile")
        deciles.insert(0, "fold", fold.name)
        deciles.insert(0, "candidate", candidate)
        decile_rows.append(deciles)

        model_path = output_dir / f"ranking_v2_{candidate.lower()}_{fold.name.lower()}.joblib"
        joblib.dump(model_object, model_path)
        model_hashes[model_path.name] = sha256_file(model_path)

    fold_metrics = pd.DataFrame(metrics_rows)
    predictions = pd.concat(prediction_rows, ignore_index=True)
    quintiles = pd.concat(quintile_rows, ignore_index=True)
    deciles = pd.concat(decile_rows, ignore_index=True)

    output_paths = {
        "fold_metrics": output_dir / f"ranking_v2_{candidate.lower()}_fold_metrics.csv",
        "predictions": output_dir / f"ranking_v2_{candidate.lower()}_predictions.parquet",
        "quintiles": output_dir / f"ranking_v2_{candidate.lower()}_quintiles.csv",
        "deciles": output_dir / f"ranking_v2_{candidate.lower()}_deciles.csv",
    }
    fold_metrics.to_csv(output_paths["fold_metrics"], index=False)
    predictions.to_parquet(output_paths["predictions"], index=False)
    quintiles.to_csv(output_paths["quintiles"], index=False)
    deciles.to_csv(output_paths["deciles"], index=False)

    artifact_hashes = {name: sha256_file(path) for name, path in output_paths.items()}
    artifact_hashes.update(model_hashes)
    summary = {
        "status": "RANKING_V2_CANDIDATE_COMPLETE",
        "candidate": candidate,
        "code_commit": code_commit,
        "prepared_cache_path": str(prepared_table_path),
        "prepared_cache_sha256": actual_cache_sha,
        "environment": environment,
        "feature_columns": list(candidate_feature_columns(candidate)),
        "folds": [fold.__dict__ for fold in RANKING_V2_FOLDS],
        "pairwise_diagnostics": pairwise_diagnostics,
        "artifact_sha256": artifact_hashes,
        "probability_claim": False,
        "independent_validation_claim": False,
        "historical_period_is_development_knowledge": True,
    }
    summary_path = output_dir / f"ranking_v2_{candidate.lower()}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    summary["summary_sha256"] = sha256_file(summary_path)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one frozen Ranking V2 historical-development candidate")
    parser.add_argument("--prepared-table", type=Path, required=True)
    parser.add_argument("--expected-cache-sha256", required=True)
    parser.add_argument("--candidate", choices=list(ALL_RANKING_V2_MODELS), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--code-commit", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = run_candidate(
        prepared_table_path=args.prepared_table,
        expected_cache_sha256=args.expected_cache_sha256,
        candidate=args.candidate,
        output_dir=args.output_dir,
        code_commit=args.code_commit,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
