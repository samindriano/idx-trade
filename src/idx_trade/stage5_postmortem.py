from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .provenance import sha256_file
from .research_features import BASELINE_FEATURE_COLUMNS, build_baseline_features
from .research_stage5 import (
    HOLDOUT_A,
    HOLDOUT_B,
    assign_within_date_buckets,
    bucket_summary,
    ranking_metrics,
)
from .stage5_ranking_holdout import (
    FROZEN_PANEL_SHA256,
    _assert_environment,
    _calendar,
    _listing_map,
    global_holdout_marker_path,
)


EXPECTED_STAGE5_SUMMARY_SHA256 = "1a38171eead5a9c72de62da4f6ef486f35e3fba2e962c3b0bccac9fea033acd0"
EXPECTED_STAGE5_PREDICTIONS_SHA256 = "9d850776c98c07e069b32d606ad510d94a26435659da86997f5302d765d8ee8c"
EXPECTED_SECURITY_MASTER_SHA256 = "9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9"
HGB_SCORE_COLUMN = "score_hist_gradient_boosting"
FIXED_BLOCKS: tuple[tuple[str, int, int], ...] = (
    ("A1", 1009, 1048),
    ("A2", 1049, 1088),
    ("A3", 1089, 1129),
    ("B1", 1130, 1169),
    ("B2", 1170, 1209),
    ("B3", 1210, 1250),
)


def _read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"unsupported table format: {path}")


def _atomic_json(value: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def _assert_clean_output_dir(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise RuntimeError("postmortem output directory must be new or empty")
    path.mkdir(parents=True, exist_ok=True)


def _half_name(index: pd.Series) -> pd.Series:
    values = pd.to_numeric(index, errors="coerce")
    result = pd.Series(index=index.index, dtype="object")
    result.loc[values.between(HOLDOUT_A[0], HOLDOUT_A[1])] = "HOLDOUT_A"
    result.loc[values.between(HOLDOUT_B[0], HOLDOUT_B[1])] = "HOLDOUT_B"
    return result


def validate_consumed_stage5_inputs(
    *,
    panel_path: Path,
    stage5_predictions_path: Path,
    stage5_summary_path: Path,
    security_master_path: Path,
) -> dict[str, object]:
    if sha256_file(panel_path) != FROZEN_PANEL_SHA256:
        raise RuntimeError("frozen signal panel hash mismatch")
    if sha256_file(stage5_predictions_path) != EXPECTED_STAGE5_PREDICTIONS_SHA256:
        raise RuntimeError("Stage-5 prediction hash mismatch")
    if sha256_file(stage5_summary_path) != EXPECTED_STAGE5_SUMMARY_SHA256:
        raise RuntimeError("Stage-5 summary hash mismatch")
    if sha256_file(security_master_path) != EXPECTED_SECURITY_MASTER_SHA256:
        raise RuntimeError("Stage-5 security-master hash mismatch")

    summary = json.loads(stage5_summary_path.read_text(encoding="utf-8"))
    if summary.get("decision") != "STAGE5_RANKING_HOLDOUT_FAIL":
        raise RuntimeError("postmortem requires the frozen Stage-5 FAIL result")
    if not bool(summary.get("holdout_consumed", False)):
        raise RuntimeError("Stage-5 summary does not mark holdout as consumed")
    if summary.get("holdout_consumed_for") != "RANKING_V1_ONLY":
        raise RuntimeError("unexpected Stage-5 holdout-consumption scope")
    if not bool(summary.get("holdout_outcome_accessed", False)):
        raise RuntimeError("postmortem requires already-consumed holdout outcomes")

    marker_path = global_holdout_marker_path(panel_path)
    if not marker_path.exists():
        raise RuntimeError("durable Stage-5 holdout marker is missing")
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if not bool(marker.get("holdout_consumed", False)) or marker.get("holdout_consumed_for") != "RANKING_V1_ONLY":
        raise RuntimeError("durable Stage-5 marker does not prove RANKING_V1_ONLY consumption")
    return summary


def fixed_block_metrics(scored: pd.DataFrame) -> pd.DataFrame:
    required = {"signal_session_index", "date", "ticker", "binary_target", HGB_SCORE_COLUMN}
    if not required.issubset(scored.columns):
        raise ValueError(f"fixed-block input missing {sorted(required - set(scored.columns))}")
    rows: list[dict[str, object]] = []
    for name, start, end in FIXED_BLOCKS:
        block = scored[scored["signal_session_index"].between(start, end)].copy()
        metrics = ranking_metrics(block["binary_target"], block[HGB_SCORE_COLUMN])
        quintiled = assign_within_date_buckets(
            block, score_column=HGB_SCORE_COLUMN, buckets=5, output_column="quintile"
        )
        q = bucket_summary(quintiled, bucket_column="quintile").set_index("bucket")
        deciled = assign_within_date_buckets(
            block, score_column=HGB_SCORE_COLUMN, buckets=10, output_column="decile"
        )
        d = bucket_summary(deciled, bucket_column="decile").set_index("bucket")
        rows.append(
            {
                "block": name,
                "first_signal_index": start,
                "last_signal_index": end,
                **metrics,
                "pr_auc_delta_vs_base": float(metrics["pr_auc"] - metrics["positive_rate"]),
                "q5_minus_q1": float(q.loc[5, "tp_rate"] - q.loc[1, "tp_rate"]),
                "top_decile_rate": float(d.loc[10, "tp_rate"]),
                "top_decile_lift": float(d.loc[10, "lift_vs_overall"]),
            }
        )
    return pd.DataFrame(rows)


def feature_drift_table(joined: pd.DataFrame) -> pd.DataFrame:
    if "half" not in joined.columns:
        raise ValueError("feature drift requires half labels")
    rows: list[dict[str, object]] = []
    for feature in BASELINE_FEATURE_COLUMNS:
        a = pd.to_numeric(joined.loc[joined["half"].eq("HOLDOUT_A"), feature], errors="coerce")
        b = pd.to_numeric(joined.loc[joined["half"].eq("HOLDOUT_B"), feature], errors="coerce")
        af = a[np.isfinite(a)]
        bf = b[np.isfinite(b)]
        pooled = pd.concat([af, bf], ignore_index=True)
        mean_a = float(af.mean()) if len(af) else np.nan
        mean_b = float(bf.mean()) if len(bf) else np.nan
        std_a = float(af.std(ddof=0)) if len(af) else np.nan
        std_b = float(bf.std(ddof=0)) if len(bf) else np.nan
        pooled_sd = float(np.sqrt((std_a**2 + std_b**2) / 2.0)) if np.isfinite(std_a) and np.isfinite(std_b) else np.nan
        pooled_iqr = float(pooled.quantile(0.75) - pooled.quantile(0.25)) if len(pooled) else np.nan
        median_a = float(af.median()) if len(af) else np.nan
        median_b = float(bf.median()) if len(bf) else np.nan
        rows.append(
            {
                "feature": feature,
                "a_rows_finite": int(len(af)),
                "b_rows_finite": int(len(bf)),
                "a_missing_rate": float(a.isna().mean()),
                "b_missing_rate": float(b.isna().mean()),
                "missing_rate_delta_b_minus_a": float(b.isna().mean() - a.isna().mean()),
                "a_mean": mean_a,
                "b_mean": mean_b,
                "a_median": median_a,
                "b_median": median_b,
                "a_std": std_a,
                "b_std": std_b,
                "smd_b_minus_a": float((mean_b - mean_a) / pooled_sd) if pooled_sd and np.isfinite(pooled_sd) else np.nan,
                "median_shift_over_pooled_iqr": float((median_b - median_a) / pooled_iqr)
                if pooled_iqr and np.isfinite(pooled_iqr)
                else np.nan,
            }
        )
    return pd.DataFrame(rows)


def feature_target_relation_table(joined: pd.DataFrame) -> pd.DataFrame:
    required = {"half", "date", "ticker", "binary_target", *BASELINE_FEATURE_COLUMNS}
    if not required.issubset(joined.columns):
        raise ValueError(f"feature relation input missing {sorted(required - set(joined.columns))}")
    rows: list[dict[str, object]] = []
    for half in ("HOLDOUT_A", "HOLDOUT_B"):
        half_frame = joined[joined["half"].eq(half)].copy()
        for feature in BASELINE_FEATURE_COLUMNS:
            valid = half_frame[["date", "ticker", "binary_target", feature]].copy()
            valid[feature] = pd.to_numeric(valid[feature], errors="coerce")
            valid = valid[np.isfinite(valid[feature])].copy()
            if valid.empty:
                continue
            valid["within_date_feature_rank"] = valid.groupby("date")[feature].rank(method="average", pct=True)
            rank_corr = valid["within_date_feature_rank"].corr(valid["binary_target"].astype(float))
            bucketed = assign_within_date_buckets(
                valid,
                score_column=feature,
                buckets=5,
                output_column="feature_quintile",
            )
            q = bucket_summary(bucketed, bucket_column="feature_quintile").set_index("bucket")
            rows.append(
                {
                    "half": half,
                    "feature": feature,
                    "rows": int(len(valid)),
                    "within_date_rank_corr_target": float(rank_corr) if pd.notna(rank_corr) else np.nan,
                    "feature_q5_target_rate": float(q.loc[5, "tp_rate"]),
                    "feature_q1_target_rate": float(q.loc[1, "tp_rate"]),
                    "feature_q5_minus_q1": float(q.loc[5, "tp_rate"] - q.loc[1, "tp_rate"]),
                }
            )
    return pd.DataFrame(rows)


def market_regime_daily(features: pd.DataFrame) -> pd.DataFrame:
    primary = features[
        features["universe_primary_liquid"].astype(bool)
        & features["session_index_zero"].between(HOLDOUT_A[0] - 1, HOLDOUT_B[1] - 1)
    ].copy()
    if primary.empty:
        raise ValueError("no primary-liquid rows in Stage-5 holdout window")

    rows: list[dict[str, object]] = []
    for date, block in primary.groupby("date", sort=True):
        ret5 = pd.to_numeric(block["close_return_5"], errors="coerce")
        ret20 = pd.to_numeric(block["close_return_20"], errors="coerce")
        rows.append(
            {
                "date": pd.Timestamp(date),
                "signal_session_index": int(block["session_index_zero"].iloc[0]) + 1,
                "n_primary_liquid": int(len(block)),
                "breadth_return_5_positive": float((ret5.dropna() > 0).mean()) if ret5.notna().any() else np.nan,
                "breadth_return_20_positive": float((ret20.dropna() > 0).mean()) if ret20.notna().any() else np.nan,
                "median_close_return_5": float(ret5.median()),
                "median_close_return_20": float(ret20.median()),
                "median_atr14_over_close": float(pd.to_numeric(block["atr14_over_close"], errors="coerce").median()),
                "median_close_position_20": float(pd.to_numeric(block["close_position_20"], errors="coerce").median()),
                "median_relative_volume_20": float(pd.to_numeric(block["relative_volume_20"], errors="coerce").median()),
                "median_log_regular_value_relative_20": float(
                    pd.to_numeric(block["log_regular_value_relative_20"], errors="coerce").median()
                ),
            }
        )
    result = pd.DataFrame(rows)
    result["half"] = _half_name(result["signal_session_index"])
    return result


def market_regime_a_vs_b(daily: pd.DataFrame) -> pd.DataFrame:
    metrics = [column for column in daily.columns if column not in {"date", "signal_session_index", "half"}]
    rows: list[dict[str, object]] = []
    for metric in metrics:
        a = pd.to_numeric(daily.loc[daily["half"].eq("HOLDOUT_A"), metric], errors="coerce").dropna()
        b = pd.to_numeric(daily.loc[daily["half"].eq("HOLDOUT_B"), metric], errors="coerce").dropna()
        std_a = float(a.std(ddof=0)) if len(a) else np.nan
        std_b = float(b.std(ddof=0)) if len(b) else np.nan
        pooled_sd = float(np.sqrt((std_a**2 + std_b**2) / 2.0)) if np.isfinite(std_a) and np.isfinite(std_b) else np.nan
        rows.append(
            {
                "metric": metric,
                "a_mean": float(a.mean()) if len(a) else np.nan,
                "b_mean": float(b.mean()) if len(b) else np.nan,
                "a_median": float(a.median()) if len(a) else np.nan,
                "b_median": float(b.median()) if len(b) else np.nan,
                "a_std": std_a,
                "b_std": std_b,
                "smd_b_minus_a": float((b.mean() - a.mean()) / pooled_sd) if pooled_sd and np.isfinite(pooled_sd) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def hgb_deciles_by_half(scored: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for half in ("HOLDOUT_A", "HOLDOUT_B"):
        block = scored[scored["half"].eq(half)].copy()
        deciled = assign_within_date_buckets(
            block,
            score_column=HGB_SCORE_COLUMN,
            buckets=10,
            output_column="decile",
        )
        summary = bucket_summary(deciled, bucket_column="decile")
        summary.insert(0, "half", half)
        rows.append(summary)
    return pd.concat(rows, ignore_index=True)


def run_stage5_postmortem(
    *,
    panel_path: Path,
    calendar_path: Path,
    security_master_path: Path,
    stage5_predictions_path: Path,
    stage5_summary_path: Path,
    output_dir: Path,
    code_commit: str,
    calendar_column: str = "date",
    ticker_column: str = "ticker",
    listed_from_column: str = "listed_from",
) -> dict[str, object]:
    environment = _assert_environment()
    stage5_summary = validate_consumed_stage5_inputs(
        panel_path=panel_path,
        stage5_predictions_path=stage5_predictions_path,
        stage5_summary_path=stage5_summary_path,
        security_master_path=security_master_path,
    )
    calendar = _calendar(calendar_path, calendar_column)
    listing_map = _listing_map(security_master_path, ticker_column, listed_from_column)
    _assert_clean_output_dir(output_dir)

    predictions = _read_table(stage5_predictions_path)
    required_predictions = {
        "ticker",
        "date",
        "signal_session_index",
        "binary_target",
        HGB_SCORE_COLUMN,
    }
    if not required_predictions.issubset(predictions.columns):
        raise ValueError(f"Stage-5 predictions missing {sorted(required_predictions - set(predictions.columns))}")
    predictions["date"] = pd.to_datetime(predictions["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if len(predictions) != 71420:
        raise RuntimeError(f"expected 71,420 frozen H10 prediction rows, got {len(predictions)}")
    predictions["half"] = _half_name(predictions["signal_session_index"])
    if predictions["half"].isna().any():
        raise RuntimeError("prediction rows fall outside frozen H10 holdout halves")

    panel = pd.read_parquet(panel_path)
    panel["date"] = pd.to_datetime(panel["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    features = build_baseline_features(panel, calendar, listed_from=listing_map)
    feature_columns = ["ticker", "date", "session_index_zero", "universe_primary_liquid", *BASELINE_FEATURE_COLUMNS]
    joined = predictions.merge(
        features[feature_columns],
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )
    if len(joined) != len(predictions) or joined["session_index_zero"].isna().any():
        raise RuntimeError("postmortem feature join failed")

    blocks = fixed_block_metrics(predictions)
    drift = feature_drift_table(joined)
    relation = feature_target_relation_table(joined)
    daily = market_regime_daily(features)
    regime = market_regime_a_vs_b(daily)
    deciles = hgb_deciles_by_half(predictions)

    paths = {
        "fixed_block_metrics": output_dir / "postmortem_fixed_block_metrics.csv",
        "feature_drift_a_vs_b": output_dir / "postmortem_feature_drift_a_vs_b.csv",
        "feature_target_relation_by_half": output_dir / "postmortem_feature_target_relation_by_half.csv",
        "market_regime_daily": output_dir / "postmortem_market_regime_daily.csv",
        "market_regime_a_vs_b": output_dir / "postmortem_market_regime_a_vs_b.csv",
        "hgb_deciles_by_half": output_dir / "postmortem_hgb_deciles_by_half.csv",
    }
    blocks.to_csv(paths["fixed_block_metrics"], index=False)
    drift.to_csv(paths["feature_drift_a_vs_b"], index=False)
    relation.to_csv(paths["feature_target_relation_by_half"], index=False)
    daily.to_csv(paths["market_regime_daily"], index=False)
    regime.to_csv(paths["market_regime_a_vs_b"], index=False)
    deciles.to_csv(paths["hgb_deciles_by_half"], index=False)

    relation_pivot = relation.pivot(index="feature", columns="half", values="feature_q5_minus_q1")
    relation_sign_reversals = sorted(
        feature
        for feature, row in relation_pivot.iterrows()
        if pd.notna(row.get("HOLDOUT_A"))
        and pd.notna(row.get("HOLDOUT_B"))
        and float(row["HOLDOUT_A"]) * float(row["HOLDOUT_B"]) < 0
    )
    strongest_drift = (
        drift.assign(abs_smd=drift["smd_b_minus_a"].abs())
        .sort_values(["abs_smd", "feature"], ascending=[False, True])
        .head(5)[["feature", "smd_b_minus_a", "median_shift_over_pooled_iqr", "missing_rate_delta_b_minus_a"]]
        .to_dict(orient="records")
    )

    artifact_hashes = {name: sha256_file(path) for name, path in paths.items()}
    summary: dict[str, object] = {
        "stage": "STAGE5_POSTMORTEM_V1",
        "status": "DESCRIPTIVE_DIAGNOSTIC_COMPLETE",
        "code_commit": code_commit,
        "environment": environment,
        "source_stage5_decision": stage5_summary.get("decision"),
        "holdout_consumed": True,
        "holdout_consumed_for": "RANKING_V1_ONLY",
        "independent_validation_reuse_allowed": False,
        "input_hashes": {
            "panel": sha256_file(panel_path),
            "calendar": sha256_file(calendar_path),
            "security_master": sha256_file(security_master_path),
            "stage5_predictions": sha256_file(stage5_predictions_path),
            "stage5_summary": sha256_file(stage5_summary_path),
        },
        "resolved_h10_rows": int(len(predictions)),
        "feature_count": int(len(BASELINE_FEATURE_COLUMNS)),
        "fixed_blocks": blocks.to_dict(orient="records"),
        "strongest_feature_distribution_shifts_by_abs_smd": strongest_drift,
        "feature_q5_minus_q1_sign_reversals": relation_sign_reversals,
        "artifact_hashes": artifact_hashes,
        "interpretation_policy": "DIAGNOSTIC_OR_V2_HYPOTHESIS_ONLY_NOT_VALIDATED_CLAIM",
        "probability_v1_status": "PROBABILITY_V1_NOT_READY_DEFERRED",
        "future_validation_policy": "FRESH_FORWARD_DATA_STRICTLY_AFTER_2026_07_31",
    }
    summary_path = output_dir / "postmortem_summary.json"
    _atomic_json(summary, summary_path)
    summary["summary_path"] = str(summary_path)
    summary["summary_sha256"] = sha256_file(summary_path)
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bounded descriptive post-mortem of the consumed Stage-5 ranking holdout")
    parser.add_argument("--panel", required=True, type=Path)
    parser.add_argument("--calendar", required=True, type=Path)
    parser.add_argument("--security-master", required=True, type=Path)
    parser.add_argument("--stage5-predictions", required=True, type=Path)
    parser.add_argument("--stage5-summary", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--code-commit", required=True)
    parser.add_argument("--calendar-column", default="date")
    parser.add_argument("--ticker-column", default="ticker")
    parser.add_argument("--listed-from-column", default="listed_from")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    summary = run_stage5_postmortem(
        panel_path=args.panel,
        calendar_path=args.calendar,
        security_master_path=args.security_master,
        stage5_predictions_path=args.stage5_predictions,
        stage5_summary_path=args.stage5_summary,
        output_dir=args.output_dir,
        code_commit=args.code_commit,
        calendar_column=args.calendar_column,
        ticker_column=args.ticker_column,
        listed_from_column=args.listed_from_column,
    )
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
