"""Read-only robustness and provenance audit for the accepted O2 artifacts."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .ohlcv_o1_research import (
    EXPECTED_ACCEPTED_OPEN_PROVENANCE_SHA256,
    EXPECTED_COMMON_SUPPORT_ROWS,
    _aggregate_metrics,
    _normal_date,
    evaluate_scores,
    sha256_file,
)
from .research_stage5 import assign_within_date_buckets, bucket_summary, ranking_metrics


EXPECTED_O2_MANIFEST_SHA256 = "cc26bc689dd37bc83cc2c32d348d3201e5c4f41577f4bb8f938ab5cac2c7a97a"
EXPECTED_COVERAGE_SHA256 = "d9b2da0b1831b8fe087fe8ee9093e6ce7f649dd0c6c3f6f378cebe23e5694242"
EXPECTED_COMMON_SUPPORT_KEY_SHA256 = "716bed364b5ba0dcb034f335bc7b09b4abac23eb1236a7c718fe6e0f6a78577a"
O2_MODEL = "O2_OPEN_GEOMETRY"
BASELINE_MODEL = "V3B_COMMON_SUPPORT_BASELINE"
GEOMETRY_FEATURES = ("open_position", "open_to_high", "open_to_low")
SOURCE_COLUMN = "open_source"
EVIDENCE_COLUMN = "open_evidence_class"


def _verify_file(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"{label} missing: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"{label} SHA-256 mismatch: expected {expected}, got {actual}")
    return actual


def _normalize_keys(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    data["ticker"] = data["ticker"].astype(str).str.upper().str.strip()
    data["date"] = _normal_date(data["date"])
    if data[["ticker", "date"]].isna().any().any():
        raise RuntimeError("audit artifact contains invalid ticker/date keys")
    return data


def canonical_provenance(frame: pd.DataFrame) -> pd.Series:
    source = frame[SOURCE_COLUMN].astype("string").fillna("UNRESOLVED").replace("", "UNRESOLVED")
    evidence = frame[EVIDENCE_COLUMN].astype("string").fillna("UNRESOLVED").replace("", "UNRESOLVED")
    return source.astype(str) + "|" + evidence.astype(str)


def _stable_support_key_hash(frame: pd.DataFrame) -> str:
    keys = frame[["ticker", "date", "signal_session_index"]].copy()
    keys["ticker"] = keys["ticker"].astype(str)
    keys["date"] = _normal_date(keys["date"]).dt.strftime("%Y-%m-%d")
    keys["signal_session_index"] = pd.to_numeric(keys["signal_session_index"], errors="raise").astype(int)
    lines = keys.sort_values(["ticker", "date", "signal_session_index"], kind="mergesort").astype(str).agg("|".join, axis=1)
    return sha256_file_from_bytes(("\n".join(lines.tolist()) + "\n").encode("utf-8"))


def sha256_file_from_bytes(payload: bytes) -> str:
    import hashlib

    return hashlib.sha256(payload).hexdigest()


def _safe_audit_metrics(frame: pd.DataFrame, scores: pd.Series | np.ndarray) -> dict[str, object]:
    """Descriptive metrics for strata; primary metrics use evaluate_scores exactly."""

    y = pd.to_numeric(frame["binary_target"], errors="raise").astype(int).to_numpy()
    values = np.asarray(scores, dtype=float)
    if len(y) == 0 or len(y) != len(values) or np.unique(y).size < 2 or not np.isfinite(values).all():
        return {"status": "INSUFFICIENT_CLASS_SUPPORT", "rows": int(len(y)), "positive_rate": float(np.mean(y)) if len(y) else np.nan}
    base = ranking_metrics(y, values)
    scored = frame[["ticker", "date", "binary_target"]].copy()
    scored["score"] = values
    quintiled = assign_within_date_buckets(scored, score_column="score", buckets=5, output_column="quintile")
    q = bucket_summary(quintiled, bucket_column="quintile").set_index("bucket")
    deciled = assign_within_date_buckets(scored, score_column="score", buckets=10, output_column="decile")
    d = bucket_summary(deciled, bucket_column="decile").set_index("bucket")
    return {
        "status": "OK",
        **base,
        "pr_auc_minus_prevalence": float(base["pr_auc"] - base["positive_rate"]),
        "q5_minus_q1": float(q.loc[5, "tp_rate"] - q.loc[1, "tp_rate"]) if 1 in q.index and 5 in q.index else np.nan,
        "top_decile_lift": float(d.loc[10, "tp_rate"] - base["positive_rate"]) if 10 in d.index else np.nan,
        "positive_rows": int(y.sum()),
        "negative_rows": int((y == 0).sum()),
    }


def _distribution_rows(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for provenance, block in frame.groupby("canonical_open_provenance", sort=True, dropna=False):
        for feature in GEOMETRY_FEATURES:
            values = pd.to_numeric(block[feature], errors="coerce").to_numpy(dtype=float)
            finite = values[np.isfinite(values)]
            rows.append(
                {
                    "canonical_open_provenance": provenance,
                    "feature": feature,
                    "rows": int(len(values)),
                    "null_or_nonfinite": int((~np.isfinite(values)).sum()),
                    "min": float(np.min(finite)) if len(finite) else np.nan,
                    "p01": float(np.quantile(finite, 0.01)) if len(finite) else np.nan,
                    "p05": float(np.quantile(finite, 0.05)) if len(finite) else np.nan,
                    "median": float(np.median(finite)) if len(finite) else np.nan,
                    "p95": float(np.quantile(finite, 0.95)) if len(finite) else np.nan,
                    "p99": float(np.quantile(finite, 0.99)) if len(finite) else np.nan,
                    "max": float(np.max(finite)) if len(finite) else np.nan,
                }
            )
    return pd.DataFrame(rows)


def _bounds_and_algebra(frame: pd.DataFrame, *, tolerance: float = 1e-12) -> dict[str, object]:
    values = {name: pd.to_numeric(frame[name], errors="coerce").to_numpy(dtype=float) for name in GEOMETRY_FEATURES}
    finite = np.isfinite(values["open_position"]) & np.isfinite(values["open_to_high"]) & np.isfinite(values["open_to_low"])
    position = values["open_position"]
    to_high = values["open_to_high"]
    to_low = values["open_to_low"]
    denominator = to_high - to_low
    algebra_valid = finite & np.isfinite(denominator) & (np.abs(denominator) > tolerance)
    algebra_expected = np.full(len(frame), np.nan, dtype=float)
    algebra_expected[algebra_valid] = -to_low[algebra_valid] / denominator[algebra_valid]
    algebra_error = np.abs(position - algebra_expected)
    return {
        "tolerance": tolerance,
        "rows": int(len(frame)),
        "nonfinite_open_position": int((~np.isfinite(position)).sum()),
        "nonfinite_open_to_high": int((~np.isfinite(to_high)).sum()),
        "nonfinite_open_to_low": int((~np.isfinite(to_low)).sum()),
        "open_position_below_zero": int((finite & (position < -tolerance)).sum()),
        "open_position_above_one": int((finite & (position > 1.0 + tolerance)).sum()),
        "open_to_high_negative": int((finite & (to_high < -tolerance)).sum()),
        "open_to_low_positive": int((finite & (to_low > tolerance)).sum()),
        "algebra_denominator_zero_or_invalid": int((~algebra_valid).sum()),
        "algebra_max_abs_error": float(np.nanmax(algebra_error)) if algebra_valid.any() else np.nan,
        "algebra_rows_with_error_over_tolerance": int((algebra_valid & (algebra_error > tolerance)).sum()),
    }


def _join_provenance(support: pd.DataFrame, coverage: pd.DataFrame, provenance: pd.DataFrame) -> pd.DataFrame:
    keys = ["ticker", "date"]
    geometry = coverage[coverage["open_feature_ready"].astype(bool)][keys + ["signal_session_index", *GEOMETRY_FEATURES]].copy()
    geometry = _normalize_keys(geometry)
    if len(geometry) != EXPECTED_COMMON_SUPPORT_ROWS or geometry.duplicated(keys).any():
        raise RuntimeError("coverage ready rows do not match the exact common-support contract")
    prov_cols = keys + [SOURCE_COLUMN, EVIDENCE_COLUMN, "split_factor", "tradingview_provenance", "validation_status"]
    prov = _normalize_keys(provenance[prov_cols])
    if prov.duplicated(keys).any():
        raise RuntimeError("Open provenance has duplicate ticker/date keys")
    joined = _normalize_keys(support).merge(geometry, on=keys, how="inner", validate="one_to_one", suffixes=("", "_coverage"))
    joined = joined.merge(prov, on=keys, how="left", validate="one_to_one")
    if len(joined) != EXPECTED_COMMON_SUPPORT_ROWS:
        raise RuntimeError(f"common-support provenance join changed rows: {len(joined)}")
    if not (joined["signal_session_index"].astype(int) == joined["signal_session_index_coverage"].astype(int)).all():
        raise RuntimeError("common-support signal-session identity mismatch after provenance join")
    joined = joined.drop(columns=["signal_session_index_coverage"])
    joined["canonical_open_provenance"] = canonical_provenance(joined)
    joined["year"] = joined["date"].dt.year.astype(int)
    return joined


def _reproduce_metrics(predictions: pd.DataFrame, persisted_fold: pd.DataFrame, persisted_aggregate: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    rows: list[dict[str, object]] = []
    for (model, fold), block in predictions.groupby(["model", "fold"], sort=True):
        metric = evaluate_scores(block, block["score"].to_numpy(dtype=float))
        rows.append({"model": model, "fold": fold, **metric})
    reproduced = pd.DataFrame(rows)
    baseline_pr = reproduced[reproduced.model.eq(BASELINE_MODEL)].set_index("fold")["pr_auc"]
    reproduced["paired_pr_auc_vs_baseline"] = reproduced.apply(
        lambda row: np.nan if row["model"] == BASELINE_MODEL else float(row["pr_auc"] - baseline_pr.loc[row["fold"]]), axis=1
    )
    persisted = persisted_fold.set_index(["model", "fold"]).sort_index()
    reproduced_indexed = reproduced.set_index(["model", "fold"]).sort_index()
    metric_fields = ["rows", "positive_rate", "pr_auc", "pr_auc_minus_prevalence", "roc_auc", "q5_minus_q1", "top_decile_lift", "paired_pr_auc_vs_baseline"]
    fold_diffs: list[float] = []
    for field in metric_fields:
        left = pd.to_numeric(persisted[field], errors="coerce")
        right = pd.to_numeric(reproduced_indexed[field], errors="coerce")
        fold_diffs.extend(np.abs((left - right).dropna()).tolist())
    aggregate = _aggregate_metrics(reproduced)
    aggregate_persisted = persisted_aggregate.set_index("model").sort_index()
    aggregate_reproduced = aggregate.set_index("model").sort_index()
    aggregate_diffs: list[float] = []
    for field in ["mean_pr_auc", "median_pr_auc", "mean_pr_auc_minus_prevalence", "median_pr_auc_minus_prevalence", "mean_roc_auc", "median_roc_auc", "mean_q5_minus_q1", "median_q5_minus_q1", "mean_top_decile_lift"]:
        aggregate_diffs.extend(np.abs((pd.to_numeric(aggregate_persisted[field], errors="coerce") - pd.to_numeric(aggregate_reproduced[field], errors="coerce")).dropna()).tolist())
    return reproduced, aggregate, {
        "fold_rows_reproduced": int(len(reproduced)),
        "aggregate_rows_reproduced": int(len(aggregate)),
        "fold_metrics_match": bool(max(fold_diffs, default=0.0) <= 1e-12),
        "aggregate_metrics_match": bool(max(aggregate_diffs, default=0.0) <= 1e-12),
        "max_abs_fold_metric_diff": float(max(fold_diffs, default=0.0)),
        "max_abs_aggregate_metric_diff": float(max(aggregate_diffs, default=0.0)),
    }


def _performance_by_group(predictions: pd.DataFrame, group_column: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for group_value, group in predictions.groupby(group_column, sort=True, dropna=False):
        model_metrics: dict[str, dict[str, object]] = {}
        for model, block in group.groupby("model", sort=True):
            model_metrics[model] = _safe_audit_metrics(block, block["score"])
        base = model_metrics.get(BASELINE_MODEL, {})
        challenger = model_metrics.get(O2_MODEL, {})
        rows.append({
            group_column: group_value,
            "rows": int(len(group[group.model.eq(BASELINE_MODEL)])),
            "positive_rows": int(group[group.model.eq(BASELINE_MODEL)]["binary_target"].sum()),
            "negative_rows": int((group[group.model.eq(BASELINE_MODEL)]["binary_target"] == 0).sum()),
            "baseline_status": base.get("status"),
            "baseline_pr_auc": base.get("pr_auc", np.nan),
            "baseline_roc_auc": base.get("roc_auc", np.nan),
            "baseline_q5_minus_q1": base.get("q5_minus_q1", np.nan),
            "o2_status": challenger.get("status"),
            "o2_pr_auc": challenger.get("pr_auc", np.nan),
            "o2_roc_auc": challenger.get("roc_auc", np.nan),
            "o2_q5_minus_q1": challenger.get("q5_minus_q1", np.nan),
            "paired_pr_auc_delta": float(challenger["pr_auc"] - base["pr_auc"]) if base.get("status") == "OK" and challenger.get("status") == "OK" else np.nan,
        })
    return pd.DataFrame(rows)


def _sensitivity(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    scenarios = {
        "EXCLUDE_ALL_ZAPI_TRADINGVIEW": predictions["open_source"].eq("ZAPI_TRADINGVIEW"),
        "EXCLUDE_YAHOO_SPLIT_SCALE_RECONSTRUCTED": predictions["open_evidence_class"].eq("SPLIT_SCALE_RECONSTRUCTABLE_EVIDENCE"),
    }
    fold_rows: list[dict[str, object]] = []
    for name, excluded in scenarios.items():
        remaining = predictions[~excluded].copy()
        for fold, fold_block in remaining.groupby("fold", sort=True):
            excluded_fold = predictions[predictions["fold"].eq(fold) & excluded]
            metrics: dict[str, dict[str, object]] = {}
            for model, block in fold_block.groupby("model", sort=True):
                metrics[model] = _safe_audit_metrics(block, block["score"])
            base = metrics.get(BASELINE_MODEL, {})
            o2 = metrics.get(O2_MODEL, {})
            fold_rows.append({
                "scenario": name,
                "fold": fold,
                "excluded_validation_rows": int(len(excluded_fold[excluded_fold.model.eq(BASELINE_MODEL)])),
                "remaining_validation_rows": int(len(fold_block[fold_block.model.eq(BASELINE_MODEL)])),
                "baseline_status": base.get("status"),
                "baseline_pr_auc": base.get("pr_auc", np.nan),
                "o2_status": o2.get("status"),
                "o2_pr_auc": o2.get("pr_auc", np.nan),
                "paired_pr_auc_delta": float(o2["pr_auc"] - base["pr_auc"]) if base.get("status") == "OK" and o2.get("status") == "OK" else np.nan,
                "o2_roc_auc": o2.get("roc_auc", np.nan),
                "o2_q5_minus_q1": o2.get("q5_minus_q1", np.nan),
                "o2_top_decile_lift": o2.get("top_decile_lift", np.nan),
            })
    fold = pd.DataFrame(fold_rows)
    aggregate = fold.groupby("scenario", sort=True).agg(
        folds=("fold", "count"),
        mean_paired_pr_auc_delta=("paired_pr_auc_delta", "mean"),
        median_paired_pr_auc_delta=("paired_pr_auc_delta", "median"),
        min_paired_pr_auc_delta=("paired_pr_auc_delta", "min"),
        positive_paired_folds=("paired_pr_auc_delta", lambda values: int((values > 0).sum())),
    ).reset_index()
    return fold, aggregate


def _choose_recommendation(bounds: dict[str, object], sensitivity_aggregate: pd.DataFrame) -> tuple[str, str]:
    bound_keys = ["nonfinite_open_position", "nonfinite_open_to_high", "nonfinite_open_to_low", "open_position_below_zero", "open_position_above_one", "open_to_high_negative", "open_to_low_positive", "algebra_denominator_zero_or_invalid", "algebra_rows_with_error_over_tolerance"]
    if any(int(bounds[key]) > 0 for key in bound_keys):
        return "O2_ROBUSTNESS_CONCERN_STOP", "geometry bounds or algebra verification reported violations"
    if sensitivity_aggregate["mean_paired_pr_auc_delta"].isna().any() or (sensitivity_aggregate["mean_paired_pr_auc_delta"] <= 0.0).any():
        return "O2_ROBUSTNESS_CONCERN_STOP", "accepted uplift disappears or reverses in a frozen provider-exclusion sensitivity"
    return "O2_ROBUSTNESS_PASS_MINIMALITY_AUDIT_RECOMMENDED", "robustness sensitivities remain positive and the three geometry features satisfy an exact algebraic redundancy relation"


def run_audit(*, o2_artifact_dir: Path, coverage_path: Path, provenance_path: Path, output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = o2_artifact_dir / "artifact_manifest.json"
    _verify_file(manifest_path, EXPECTED_O2_MANIFEST_SHA256, "O2 artifact manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name, expected in manifest["artifact_sha256"].items():
        _verify_file(o2_artifact_dir / name, expected, f"O2 artifact {name}")
    _verify_file(coverage_path, EXPECTED_COVERAGE_SHA256, "coverage-gate artifact")
    _verify_file(provenance_path, EXPECTED_ACCEPTED_OPEN_PROVENANCE_SHA256, "accepted Open provenance")
    support = pd.read_csv(o2_artifact_dir / "common_support_rows.csv", parse_dates=["date"])
    support = _normalize_keys(support)
    if len(support) != EXPECTED_COMMON_SUPPORT_ROWS or support.duplicated(["ticker", "date"]).any() or _stable_support_key_hash(support) != EXPECTED_COMMON_SUPPORT_KEY_SHA256:
        raise RuntimeError("O2 common-support identity contract mismatch")
    coverage = pd.read_csv(coverage_path, parse_dates=["date"])
    coverage = _normalize_keys(coverage)
    provenance = _normalize_keys(pd.read_parquet(provenance_path))
    joined = _join_provenance(support, coverage, provenance)
    predictions = _normalize_keys(pd.read_parquet(o2_artifact_dir / "fold_predictions.parquet"))
    predictions["year"] = predictions["date"].dt.year.astype(int)
    predictions = predictions.merge(joined[["ticker", "date", SOURCE_COLUMN, EVIDENCE_COLUMN, "canonical_open_provenance"]], on=["ticker", "date"], how="left", validate="many_to_one")
    if predictions[[SOURCE_COLUMN, EVIDENCE_COLUMN, "canonical_open_provenance"]].isna().any().any():
        raise RuntimeError("persisted O2 predictions have unresolved Open provenance")
    persisted_fold = pd.read_csv(o2_artifact_dir / "fold_metrics.csv")
    persisted_aggregate = pd.read_csv(o2_artifact_dir / "aggregate_metrics.csv")
    reproduced_fold, reproduced_aggregate, reproduction = _reproduce_metrics(predictions, persisted_fold, persisted_aggregate)
    full_counts = joined.groupby("canonical_open_provenance", sort=True).size().rename("rows").reset_index()
    full_counts["percent_of_common_support"] = full_counts["rows"] / len(joined) * 100.0
    year_counts = joined.groupby(["year", "canonical_open_provenance"], sort=True).size().rename("rows").reset_index()
    year_counts["percent_of_year_common_support"] = year_counts["rows"] / year_counts.groupby("year")["rows"].transform("sum") * 100.0
    validation = predictions[predictions.model.eq(BASELINE_MODEL)].copy()
    fold_year_counts = validation.groupby(["fold", "year", "canonical_open_provenance"], sort=True).size().rename("rows").reset_index()
    fold_year_counts["percent_of_fold_year_validation"] = fold_year_counts["rows"] / fold_year_counts.groupby(["fold", "year"])["rows"].transform("sum") * 100.0
    distributions = _distribution_rows(joined)
    bounds = _bounds_and_algebra(joined)
    provenance_performance = _performance_by_group(predictions, "canonical_open_provenance")
    era_performance = _performance_by_group(predictions, "year")
    sensitivity_fold, sensitivity_aggregate = _sensitivity(predictions)
    recommendation, recommendation_basis = _choose_recommendation(bounds, sensitivity_aggregate)
    contract = {
        "o2_artifact_manifest_sha256": EXPECTED_O2_MANIFEST_SHA256,
        "coverage_gate_sha256": EXPECTED_COVERAGE_SHA256,
        "accepted_open_provenance_sha256": EXPECTED_ACCEPTED_OPEN_PROVENANCE_SHA256,
        "common_support_rows": int(len(joined)),
        "common_support_key_sha256": EXPECTED_COMMON_SUPPORT_KEY_SHA256,
        "prediction_rows": int(len(predictions)),
        "prediction_models": sorted(predictions.model.unique().tolist()),
        "fresh_forward_outcomes_accessed": False,
        "model_retraining_performed": False,
        "provider_calls_performed": False,
        "geometry_features": list(GEOMETRY_FEATURES),
        "algebra": "open_position = -open_to_low / (open_to_high - open_to_low) when denominator is nonzero",
    }
    (output_dir / "audit_contract.json").write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "metric_reproduction.json").write_text(json.dumps(reproduction, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "geometry_bounds_algebra.json").write_text(json.dumps(bounds, indent=2, sort_keys=True), encoding="utf-8")
    full_counts.to_csv(output_dir / "common_support_provenance_counts.csv", index=False)
    year_counts.to_csv(output_dir / "common_support_provenance_by_year.csv", index=False)
    fold_year_counts.to_csv(output_dir / "validation_provenance_by_fold_year.csv", index=False)
    distributions.to_csv(output_dir / "geometry_distributions_by_provenance.csv", index=False)
    provenance_performance.to_csv(output_dir / "performance_by_provenance.csv", index=False)
    era_performance.to_csv(output_dir / "performance_by_year.csv", index=False)
    reproduced_fold.to_csv(output_dir / "reproduced_fold_metrics.csv", index=False)
    reproduced_aggregate.to_csv(output_dir / "reproduced_aggregate_metrics.csv", index=False)
    sensitivity_fold.to_csv(output_dir / "provider_exclusion_sensitivity_by_fold.csv", index=False)
    sensitivity_aggregate.to_csv(output_dir / "provider_exclusion_sensitivity_aggregate.csv", index=False)
    recommendation_payload = {"recommendation": recommendation, "basis": recommendation_basis}
    (output_dir / "recommendation.json").write_text(json.dumps(recommendation_payload, indent=2, sort_keys=True), encoding="utf-8")
    summary = {
        "status": recommendation,
        "recommendation_basis": recommendation_basis,
        "common_support_rows": int(len(joined)),
        "common_support_provenance_groups": int(joined["canonical_open_provenance"].nunique()),
        "metric_reproduction": reproduction,
        "geometry_bounds_algebra": bounds,
        "sensitivity_aggregate": sensitivity_aggregate.to_dict(orient="records"),
        "fresh_forward_outcomes_accessed": False,
        "model_retraining_performed": False,
        "provider_calls_performed": False,
    }
    (output_dir / "audit_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    artifacts: dict[str, str] = {}
    for path in sorted(output_dir.iterdir()):
        if path.name != "artifact_manifest.json" and path.is_file():
            artifacts[path.name] = sha256_file(path)
    artifact_manifest = {
        "schema": "idx-trade/ohlcv-o2-robustness-audit-v1",
        "status": recommendation,
        "artifact_sha256": artifacts,
        "input_contract": contract,
        "environment": {"python": sys.version, "platform": platform.platform(), "packages": {"numpy": np.__version__, "pandas": pd.__version__}},
    }
    artifact_manifest_path = output_dir / "artifact_manifest.json"
    artifact_manifest_path.write_text(json.dumps(artifact_manifest, indent=2, sort_keys=True, default=str), encoding="utf-8")
    manifest_sha = sha256_file(artifact_manifest_path)
    return {"recommendation": recommendation, "recommendation_basis": recommendation_basis, "common_support_rows": len(joined), "metric_reproduction": reproduction, "bounds": bounds, "sensitivity": sensitivity_aggregate.to_dict(orient="records"), "artifact_manifest_sha256": manifest_sha, "artifact_count": len(artifacts)}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--o2-artifact-dir", type=Path, required=True)
    parser.add_argument("--coverage-path", type=Path, required=True)
    parser.add_argument("--provenance-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    result = run_audit(**vars(args))
    print(json.dumps({k: result[k] for k in ("recommendation", "common_support_rows", "artifact_manifest_sha256", "artifact_count")}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
