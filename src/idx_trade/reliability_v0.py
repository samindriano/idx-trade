"""Frozen Reliability / Uncertainty V0 historical O2-OOF diagnostic.

This module does not fit a reliability model. It derives two predefined primary
ex-ante reliability proxies plus two secondary diagnostics, then asks whether
they stratify the already-frozen O2 historical out-of-fold ranking quality.
Fresh-forward runtime/outcomes are never inputs to this runner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


O2_MODEL = "O2_OPEN_GEOMETRY"
EXPECTED_O2_MANIFEST_SHA256 = "cc26bc689dd37bc83cc2c32d348d3201e5c4f41577f4bb8f938ab5cac2c7a97a"
EXPECTED_O2_PREDICTIONS_SHA256 = "fe02c0c743e7bfc5a57b1c8e731c5685a4bff5f9854f910f88703b15a6ca8f0c"
EXPECTED_O2_COMMON_SUPPORT_CSV_SHA256 = "59b95ad907a8adc911bbf2a411cb1b52a433bd3d225927268440a11b958f6c6f"
EXPECTED_O2_FOLD_DEFINITIONS_SHA256 = "f16ddd1640701b206cb10418ca9fa7736695fe8268ac5c38213ba22b1fe76046"
EXPECTED_O2_FEATURE_MANIFEST_SHA256 = "9014166635a7365d6f0a101132648c24637b04a6af2455063f3f37eee6586f04"
EXPECTED_COMMON_SUPPORT_KEY_SHA256 = "716bed364b5ba0dcb034f335bc7b09b4abac23eb1236a7c718fe6e0f6a78577a"
EXPECTED_COMMON_SUPPORT_ROWS = 278_168
EXPECTED_O2_OOF_ROWS = 140_679
EXPECTED_TRAINING_TABLE_SHA256 = "5893c9f2872aae0f33acd4104d82ee8c1d4474aae7d54e9d01879724b86dffbe"
EXPECTED_TRAINING_MANIFEST_SHA256 = "4e84ce02c6ee856c0f260dd6099b2a479723c53da82131ae669e0bf7e4d384f9"
EXPECTED_COVERAGE_SHA256 = "d9b2da0b1831b8fe087fe8ee9093e6ce7f649dd0c6c3f6f378cebe23e5694242"
EXPECTED_V3B_ROWS = 292_633
EXPECTED_V3B_FEATURE_ORDER_SHA256 = "100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e"
EXPECTED_O2_FEATURE_ORDER_SHA256 = "a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f"
MAX_ALLOWED_DATE = pd.Timestamp("2026-07-31")

V3B_FEATURES = (
    "xs_rank_close_return_5",
    "xs_rank_close_return_20",
    "xs_rank_atr14_over_close",
    "xs_rank_close_position_20",
    "xs_rank_distance_high_20_atr",
    "xs_rank_distance_low_20_atr",
    "xs_rank_distance_high_60_atr",
    "xs_rank_distance_low_60_atr",
    "xs_rank_relative_volume_20",
    "xs_rank_log_regular_value_relative_20",
    "market_primary_liquid_count",
    "market_breadth_return_5_positive",
    "market_breadth_return_20_positive",
    "market_median_close_return_5",
    "market_median_close_return_20",
    "market_median_atr14_over_close",
    "market_median_close_position_20",
    "market_median_relative_volume_20",
    "market_median_log_regular_value_relative_20",
    "market_relative_close_return_5",
    "market_relative_close_return_20",
    "market_relative_atr14_over_close",
    "market_relative_close_position_20",
    "market_relative_relative_volume_20",
    "market_relative_log_regular_value_relative_20",
    "structure_support_distance_atr",
    "structure_resistance_distance_atr",
    "structure_support_touch_count_60",
    "structure_resistance_touch_count_60",
    "structure_nearest_level_age_sessions",
    "structure_role_reversal_count_120",
    "structure_breakout_retest_state",
    "structure_breakout_volume_confirmed",
)
GEOMETRY_FEATURES = ("open_position", "open_to_high", "open_to_low")
O2_FEATURES = (*V3B_FEATURES, *GEOMETRY_FEATURES)

PRIMARY_PROXIES = (
    "score_margin_reliability",
    "joint_marginal_support_reliability",
)
SECONDARY_PROXIES = (
    "observed_feature_fraction",
    "mean_marginal_support",
)
ALL_PROXIES = (*PRIMARY_PROXIES, *SECONDARY_PROXIES)

RUNTIME_FLAGS = {
    "reliability_model_fit": False,
    "composite_reliability_score_created": False,
    "trade_filter_optimized": False,
    "provider_calls": False,
    "o2_refit": False,
    "o2_rescored": False,
    "fresh_forward_outcomes_accessed": False,
    "forward_outcome_access_marker_written": False,
}


@dataclass(frozen=True)
class Fold:
    name: str
    train_start: int
    train_end: int
    gap_start: int
    gap_end: int
    validation_start: int
    validation_end: int


FOLDS = (
    Fold("V2F1", 1, 504, 505, 524, 525, 624),
    Fold("V2F2", 1, 624, 625, 644, 645, 744),
    Fold("V2F3", 1, 744, 745, 764, 765, 864),
    Fold("V2F4", 1, 864, 865, 884, 885, 984),
    Fold("V2F5", 1, 984, 985, 1004, 1005, 1104),
    Fold("V2F6", 1, 1104, 1105, 1124, 1125, 1224),
)
FOLD_BY_NAME = {fold.name: fold for fold in FOLDS}


class ReliabilityDataBlocked(RuntimeError):
    """Raised when the frozen V0 data contract is not satisfied."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_sha(path: Path, expected: str, label: str) -> None:
    if not path.is_file():
        raise ReliabilityDataBlocked(f"missing {label}: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise ReliabilityDataBlocked(f"{label} SHA mismatch: expected {expected}, got {actual}")


def _normal_date(values: pd.Series) -> pd.Series:
    dates = pd.to_datetime(values, errors="coerce")
    if dates.isna().any():
        raise ReliabilityDataBlocked("invalid date value")
    if getattr(dates.dt, "tz", None) is not None:
        dates = dates.dt.tz_localize(None)
    return dates.dt.normalize()


def feature_order_sha256(columns: Iterable[str]) -> str:
    payload = json.dumps(list(columns), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def stable_support_key_sha256(frame: pd.DataFrame) -> str:
    keys = frame[["ticker", "date", "signal_session_index"]].copy()
    keys["ticker"] = keys["ticker"].astype(str).str.upper().str.strip()
    keys["date"] = _normal_date(keys["date"]).dt.strftime("%Y-%m-%d")
    keys["signal_session_index"] = pd.to_numeric(keys["signal_session_index"], errors="raise").astype(int)
    lines = (
        keys.sort_values(["ticker", "date", "signal_session_index"], kind="mergesort")
        .astype(str)
        .agg("|".join, axis=1)
    )
    return hashlib.sha256(("\n".join(lines.tolist()) + "\n").encode("utf-8")).hexdigest()


def _bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).astype(bool)
    mapped = series.astype(str).str.strip().str.lower().map(
        {"true": True, "1": True, "yes": True, "false": False, "0": False, "no": False}
    )
    if mapped.isna().any():
        raise ReliabilityDataBlocked("open_feature_ready contains non-boolean values")
    return mapped.astype(bool)


def validate_fold_windows(predictions: pd.DataFrame) -> None:
    required = set(FOLD_BY_NAME)
    present = set(predictions["fold"].astype(str).unique())
    if present != required:
        raise ReliabilityDataBlocked(f"OOF folds mismatch: {sorted(present)}")
    for fold_name, block in predictions.groupby("fold", sort=False):
        fold = FOLD_BY_NAME[str(fold_name)]
        idx = pd.to_numeric(block["signal_session_index"], errors="raise").astype(int)
        if idx.min() < fold.validation_start or idx.max() > fold.validation_end:
            raise ReliabilityDataBlocked(f"{fold_name} contains rows outside frozen validation window")
        expected_sessions = set(range(fold.validation_start, fold.validation_end + 1))
        if set(idx.unique()) != expected_sessions:
            raise ReliabilityDataBlocked(f"{fold_name} does not contain all 100 frozen validation sessions")


def score_margin_reliability(frame: pd.DataFrame) -> pd.Series:
    """Nearest adjacent O2-score gap divided by session score IQR."""
    if len(frame) < 2:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    ordered = frame[["score", "ticker"]].copy()
    ordered["_idx"] = frame.index
    ordered = ordered.sort_values(["score", "ticker"], kind="mergesort").reset_index(drop=True)
    score = pd.to_numeric(ordered["score"], errors="coerce").to_numpy(dtype=float)
    if not np.isfinite(score).all():
        return pd.Series(np.nan, index=frame.index, dtype=float)
    iqr = float(np.quantile(score, 0.75) - np.quantile(score, 0.25))
    if not np.isfinite(iqr) or iqr <= 0.0:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    lower = np.full(len(score), np.inf, dtype=float)
    upper = np.full(len(score), np.inf, dtype=float)
    lower[1:] = score[1:] - score[:-1]
    upper[:-1] = score[1:] - score[:-1]
    nearest = np.minimum(lower, upper)
    values = nearest / iqr
    result = pd.Series(values, index=ordered["_idx"].to_numpy(), dtype=float)
    return result.reindex(frame.index)


def empirical_centrality(training: np.ndarray, validation: np.ndarray) -> np.ndarray:
    """Training-only two-sided empirical centrality, with NaN validation preserved."""
    train = np.asarray(training, dtype=float)
    train = train[np.isfinite(train)]
    if len(train) == 0:
        raise ReliabilityDataBlocked("feature has no finite fold-training observations")
    train.sort()
    val = np.asarray(validation, dtype=float)
    output = np.full(len(val), np.nan, dtype=float)
    finite = np.isfinite(val)
    if not finite.any():
        return output
    x = val[finite]
    left = np.searchsorted(train, x, side="left")
    right = np.searchsorted(train, x, side="right")
    f_mid = (left + right) / (2.0 * len(train))
    centrality = 2.0 * np.minimum(f_mid, 1.0 - f_mid)
    output[finite] = np.clip(centrality, 1e-6, 1.0)
    return output


def attach_feature_support(train: pd.DataFrame, validation: pd.DataFrame) -> pd.DataFrame:
    """Attach frozen missingness and marginal-support diagnostics to validation rows."""
    support_matrix = np.full((len(validation), len(O2_FEATURES)), np.nan, dtype=float)
    for j, feature in enumerate(O2_FEATURES):
        train_values = pd.to_numeric(train[feature], errors="coerce").to_numpy(dtype=float)
        val_values = pd.to_numeric(validation[feature], errors="coerce").to_numpy(dtype=float)
        support_matrix[:, j] = empirical_centrality(train_values, val_values)
    observed = np.isfinite(validation.loc[:, O2_FEATURES].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float))
    observed_count = observed.sum(axis=1)
    mean_support = np.nanmean(support_matrix, axis=1)
    clipped = np.where(np.isfinite(support_matrix), np.clip(support_matrix, 1e-6, 1.0), np.nan)
    joint = np.exp(np.nanmean(np.log(clipped), axis=1))
    joint[observed_count < 18] = np.nan
    result = validation.copy()
    result["observed_feature_fraction"] = observed_count / float(len(O2_FEATURES))
    result["mean_marginal_support"] = mean_support
    result["joint_marginal_support_reliability"] = joint
    return result


def local_pairwise_quality(frame: pd.DataFrame) -> pd.Series:
    """Per-row contribution to correct positive-vs-negative score ordering."""
    score = pd.to_numeric(frame["score"], errors="coerce").to_numpy(dtype=float)
    target = pd.to_numeric(frame["binary_target"], errors="coerce").to_numpy(dtype=int)
    if not np.isfinite(score).all() or not set(np.unique(target)).issubset({0, 1}):
        raise ReliabilityDataBlocked("invalid score/target for local pairwise quality")
    positives = np.sort(score[target == 1])
    negatives = np.sort(score[target == 0])
    if len(positives) == 0 or len(negatives) == 0:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    out = np.empty(len(frame), dtype=float)
    pos_mask = target == 1
    x = score[pos_mask]
    lower = np.searchsorted(negatives, x, side="left")
    upper = np.searchsorted(negatives, x, side="right")
    out[pos_mask] = (lower + 0.5 * (upper - lower)) / len(negatives)
    neg_mask = ~pos_mask
    x = score[neg_mask]
    lower = np.searchsorted(positives, x, side="left")
    upper = np.searchsorted(positives, x, side="right")
    greater = len(positives) - upper
    ties = upper - lower
    out[neg_mask] = (greater + 0.5 * ties) / len(positives)
    return pd.Series(out, index=frame.index, dtype=float)


def _spearman(x: pd.Series, y: pd.Series) -> float:
    valid = x.notna() & y.notna()
    if int(valid.sum()) < 3 or x.loc[valid].nunique() < 2 or y.loc[valid].nunique() < 2:
        return float("nan")
    return float(x.loc[valid].rank(method="average").corr(y.loc[valid].rank(method="average")))


def _ordinal_bucket(frame: pd.DataFrame, value_col: str, buckets: int, output_col: str) -> pd.DataFrame:
    ordered = frame.sort_values([value_col, "ticker"], kind="mergesort").copy()
    n = len(ordered)
    if n == 0:
        ordered[output_col] = pd.Series(dtype=int)
        return ordered
    ordinal = np.arange(n, dtype=int)
    ordered[output_col] = ((ordinal * buckets) // n + 1).clip(1, buckets)
    return ordered


def session_proxy_metrics(frame: pd.DataFrame, proxy: str) -> dict[str, float | int]:
    block = frame.loc[np.isfinite(pd.to_numeric(frame[proxy], errors="coerce"))].copy()
    if len(block) < 30 or block["binary_target"].nunique() != 2:
        return {
            "rows": int(len(block)),
            "eligible": False,
            "spearman": np.nan,
            "q4_minus_q1_quality_lift": np.nan,
            "selective_quality_lift_at_40pct": np.nan,
            "conditional_quality_lift": np.nan,
        }
    spearman = _spearman(block[proxy], block["local_pairwise_quality"])
    quartiled = _ordinal_bucket(block, proxy, 4, "reliability_quartile")
    q1 = quartiled.loc[quartiled.reliability_quartile.eq(1), "local_pairwise_quality"].mean()
    q4 = quartiled.loc[quartiled.reliability_quartile.eq(4), "local_pairwise_quality"].mean()
    ordered_desc = block.sort_values([proxy, "ticker"], ascending=[False, True], kind="mergesort")
    keep = max(1, int(np.ceil(0.40 * len(ordered_desc))))
    selective_lift = float(
        ordered_desc.iloc[:keep]["local_pairwise_quality"].mean() - block["local_pairwise_quality"].mean()
    )

    score_quintiled = _ordinal_bucket(block, "score", 5, "score_quintile")
    conditional_lifts: list[float] = []
    for _, group in score_quintiled.groupby("score_quintile", sort=True):
        if len(group) < 8 or group[proxy].nunique() < 2:
            continue
        reliability_halves = _ordinal_bucket(group, proxy, 2, "reliability_half")
        low = reliability_halves.loc[reliability_halves.reliability_half.eq(1), "local_pairwise_quality"].mean()
        high = reliability_halves.loc[reliability_halves.reliability_half.eq(2), "local_pairwise_quality"].mean()
        conditional_lifts.append(float(high - low))
    conditional = float(np.mean(conditional_lifts)) if conditional_lifts else float("nan")
    return {
        "rows": int(len(block)),
        "eligible": bool(np.isfinite(spearman) and np.isfinite(conditional)),
        "spearman": spearman,
        "q4_minus_q1_quality_lift": float(q4 - q1),
        "selective_quality_lift_at_40pct": selective_lift,
        "conditional_quality_lift": conditional,
    }


def evaluate_proxy_gate(fold_metrics: pd.DataFrame, proxy: str) -> dict[str, object]:
    block = fold_metrics.loc[fold_metrics.proxy.eq(proxy)].sort_values("fold")
    if len(block) != 6:
        raise ReliabilityDataBlocked(f"{proxy} does not have six fold metrics")
    spearman = block["median_session_spearman"].to_numpy(dtype=float)
    qlift = block["mean_q4_minus_q1_quality_lift"].to_numpy(dtype=float)
    selective = block["mean_selective_quality_lift_at_40pct"].to_numpy(dtype=float)
    conditional = block["mean_conditional_quality_lift"].to_numpy(dtype=float)
    if not all(np.isfinite(values).all() for values in (spearman, qlift, selective, conditional)):
        raise ReliabilityDataBlocked(f"{proxy} fold metrics contain non-finite gating values")
    result: dict[str, object] = {
        "proxy": proxy,
        "median_fold_median_session_spearman": float(np.median(spearman)),
        "q25_fold_median_session_spearman": float(np.quantile(spearman, 0.25)),
        "positive_spearman_folds": int((spearman > 0).sum()),
        "median_fold_mean_q4_minus_q1_quality_lift": float(np.median(qlift)),
        "positive_q4_minus_q1_folds": int((qlift > 0).sum()),
        "median_fold_mean_selective_quality_lift_at_40pct": float(np.median(selective)),
        "positive_selective_lift_folds": int((selective > 0).sum()),
        "median_fold_mean_conditional_quality_lift": float(np.median(conditional)),
        "positive_conditional_lift_folds": int((conditional > 0).sum()),
    }
    result["qualified"] = bool(
        result["median_fold_median_session_spearman"] > 0
        and result["q25_fold_median_session_spearman"] > 0
        and result["positive_spearman_folds"] >= 4
        and result["median_fold_mean_q4_minus_q1_quality_lift"] > 0
        and result["positive_q4_minus_q1_folds"] >= 4
        and result["median_fold_mean_selective_quality_lift_at_40pct"] > 0
        and result["positive_selective_lift_folds"] >= 4
        and result["median_fold_mean_conditional_quality_lift"] > 0
        and result["positive_conditional_lift_folds"] >= 4
    )
    return result


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False, default=str) + "\n", encoding="utf-8")


def _load_and_verify_inputs(
    *, o2_root: Path, training_table_path: Path, training_manifest_path: Path, coverage_path: Path
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    manifest_path = o2_root / "artifact_manifest.json"
    predictions_path = o2_root / "fold_predictions.parquet"
    support_csv_path = o2_root / "common_support_rows.csv"
    fold_definitions_path = o2_root / "fold_definitions.json"
    feature_manifest_path = o2_root / "feature_manifest.json"
    _require_sha(manifest_path, EXPECTED_O2_MANIFEST_SHA256, "accepted O2 artifact manifest")
    _require_sha(predictions_path, EXPECTED_O2_PREDICTIONS_SHA256, "accepted O2 OOF predictions")
    _require_sha(support_csv_path, EXPECTED_O2_COMMON_SUPPORT_CSV_SHA256, "accepted O2 common-support rows")
    _require_sha(fold_definitions_path, EXPECTED_O2_FOLD_DEFINITIONS_SHA256, "accepted O2 fold definitions")
    _require_sha(feature_manifest_path, EXPECTED_O2_FEATURE_MANIFEST_SHA256, "accepted O2 feature manifest")
    _require_sha(training_table_path, EXPECTED_TRAINING_TABLE_SHA256, "V3-B training table")
    _require_sha(training_manifest_path, EXPECTED_TRAINING_MANIFEST_SHA256, "V3-B training manifest")
    _require_sha(coverage_path, EXPECTED_COVERAGE_SHA256, "Open coverage/readiness artifact")

    o2_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact_hashes = o2_manifest.get("artifact_sha256", {})
    if artifact_hashes.get("fold_predictions.parquet") != EXPECTED_O2_PREDICTIONS_SHA256:
        raise ReliabilityDataBlocked("O2 manifest does not pin accepted predictions")
    if o2_manifest.get("preflight_contract", {}).get("fresh_forward_outcomes_accessed") is not False:
        raise ReliabilityDataBlocked("accepted O2 manifest does not preserve historical-only boundary")

    feature_manifest = json.loads(feature_manifest_path.read_text(encoding="utf-8"))
    if tuple(feature_manifest.get("challenger_feature_columns", ())) != O2_FEATURES:
        raise ReliabilityDataBlocked("O2 feature columns differ from frozen 36-feature order")
    if feature_manifest.get("challenger_feature_order_sha256") != EXPECTED_O2_FEATURE_ORDER_SHA256:
        raise ReliabilityDataBlocked("O2 feature manifest hash mismatch")
    if feature_order_sha256(O2_FEATURES) != EXPECTED_O2_FEATURE_ORDER_SHA256:
        raise ReliabilityDataBlocked("local frozen O2 feature-order hash mismatch")

    training_manifest = json.loads(training_manifest_path.read_text(encoding="utf-8"))
    if tuple(training_manifest.get("feature_columns", ())) != V3B_FEATURES:
        raise ReliabilityDataBlocked("V3-B training feature order differs from frozen 33 features")
    if training_manifest.get("feature_order_sha256") != EXPECTED_V3B_FEATURE_ORDER_SHA256:
        raise ReliabilityDataBlocked("V3-B training feature hash mismatch")

    accepted_folds = json.loads(fold_definitions_path.read_text(encoding="utf-8"))
    local_folds = [fold.__dict__ for fold in FOLDS]
    if accepted_folds != local_folds:
        raise ReliabilityDataBlocked("accepted O2 fold definitions differ from Reliability V0 contract")

    support_keys = pd.read_csv(support_csv_path, parse_dates=["date"])
    if len(support_keys) != EXPECTED_COMMON_SUPPORT_ROWS:
        raise ReliabilityDataBlocked("accepted common-support row count changed")
    if stable_support_key_sha256(support_keys) != EXPECTED_COMMON_SUPPORT_KEY_SHA256:
        raise ReliabilityDataBlocked("accepted common-support key hash mismatch")

    training = pd.read_parquet(training_table_path)
    if len(training) != EXPECTED_V3B_ROWS:
        raise ReliabilityDataBlocked("unexpected V3-B training row count")
    training["ticker"] = training["ticker"].astype(str).str.upper().str.strip()
    training["date"] = _normal_date(training["date"])
    training["signal_session_index"] = pd.to_numeric(training["signal_session_index"], errors="raise").astype(int)
    if training.duplicated(["ticker", "date"]).any() or training["date"].max() > MAX_ALLOWED_DATE:
        raise ReliabilityDataBlocked("V3-B training identity/cutoff contract failed")

    coverage = pd.read_csv(coverage_path, parse_dates=["date"])
    if len(coverage) != EXPECTED_V3B_ROWS:
        raise ReliabilityDataBlocked("unexpected Open coverage row count")
    coverage["ticker"] = coverage["ticker"].astype(str).str.upper().str.strip()
    coverage["date"] = _normal_date(coverage["date"])
    coverage["signal_session_index"] = pd.to_numeric(coverage["signal_session_index"], errors="raise").astype(int)
    if coverage.duplicated(["ticker", "date"]).any():
        raise ReliabilityDataBlocked("Open coverage keys are duplicated")
    ready = coverage.loc[_bool_series(coverage["open_feature_ready"])].copy()
    if len(ready) != EXPECTED_COMMON_SUPPORT_ROWS:
        raise ReliabilityDataBlocked("Open-ready common-support row count changed")
    missing_geometry = set(GEOMETRY_FEATURES) - set(ready.columns)
    if missing_geometry:
        raise ReliabilityDataBlocked(f"coverage missing geometry features: {sorted(missing_geometry)}")

    support = training.merge(
        ready[["ticker", "date", "signal_session_index", *GEOMETRY_FEATURES]],
        on=["ticker", "date"], how="inner", validate="one_to_one", suffixes=("", "_coverage")
    )
    if len(support) != EXPECTED_COMMON_SUPPORT_ROWS:
        raise ReliabilityDataBlocked("reconstructed O2 common support changed")
    if not (
        support["signal_session_index"].astype(int)
        == support["signal_session_index_coverage"].astype(int)
    ).all():
        raise ReliabilityDataBlocked("training/coverage session identity mismatch")
    support = support.drop(columns=["signal_session_index_coverage"])
    if stable_support_key_sha256(support) != EXPECTED_COMMON_SUPPORT_KEY_SHA256:
        raise ReliabilityDataBlocked("reconstructed O2 common-support key hash mismatch")
    if support[[*GEOMETRY_FEATURES]].isna().any().any():
        raise ReliabilityDataBlocked("O2 geometry unexpectedly missing on common support")

    predictions = pd.read_parquet(predictions_path)
    predictions = predictions.loc[predictions["model"].astype(str).eq(O2_MODEL)].copy()
    if len(predictions) != EXPECTED_O2_OOF_ROWS:
        raise ReliabilityDataBlocked(f"unexpected accepted O2 OOF rows: {len(predictions)}")
    predictions["ticker"] = predictions["ticker"].astype(str).str.upper().str.strip()
    predictions["date"] = _normal_date(predictions["date"])
    predictions["signal_session_index"] = pd.to_numeric(predictions["signal_session_index"], errors="raise").astype(int)
    predictions["fold"] = predictions["fold"].astype(str)
    predictions["score"] = pd.to_numeric(predictions["score"], errors="coerce")
    predictions["binary_target"] = pd.to_numeric(predictions["binary_target"], errors="raise").astype(int)
    if predictions.duplicated(["fold", "ticker", "date", "signal_session_index"]).any():
        raise ReliabilityDataBlocked("accepted O2 OOF keys are duplicated")
    if not np.isfinite(predictions["score"]).all() or not set(predictions["binary_target"].unique()).issubset({0, 1}):
        raise ReliabilityDataBlocked("accepted O2 score/target values are invalid")
    if predictions["date"].max() > MAX_ALLOWED_DATE:
        raise ReliabilityDataBlocked("accepted O2 OOF contains post-cutoff outcomes")
    validate_fold_windows(predictions)

    oof = predictions.merge(
        support[["ticker", "date", "signal_session_index", *O2_FEATURES]],
        on=["ticker", "date", "signal_session_index"], how="left", validate="one_to_one"
    )
    if len(oof) != len(predictions) or oof[list(O2_FEATURES)].isna().all(axis=1).any():
        raise ReliabilityDataBlocked("OOF feature reconstruction is incomplete")
    contract = {
        "o2_artifact_manifest_sha256": EXPECTED_O2_MANIFEST_SHA256,
        "o2_predictions_sha256": EXPECTED_O2_PREDICTIONS_SHA256,
        "common_support_key_sha256": EXPECTED_COMMON_SUPPORT_KEY_SHA256,
        "training_table_sha256": EXPECTED_TRAINING_TABLE_SHA256,
        "training_manifest_sha256": EXPECTED_TRAINING_MANIFEST_SHA256,
        "coverage_sha256": EXPECTED_COVERAGE_SHA256,
        "o2_feature_order_sha256": EXPECTED_O2_FEATURE_ORDER_SHA256,
        "o2_oof_rows": int(len(oof)),
        "common_support_rows": int(len(support)),
        "cutoff": MAX_ALLOWED_DATE.date().isoformat(),
        "runtime_flags": RUNTIME_FLAGS,
    }
    return support, oof, contract


def run_diagnostic(
    *, o2_root: Path, training_table_path: Path, training_manifest_path: Path,
    coverage_path: Path, output_dir: Path
) -> dict[str, object]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ReliabilityDataBlocked(f"output directory must be new/empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    support, oof, contract = _load_and_verify_inputs(
        o2_root=o2_root,
        training_table_path=training_table_path,
        training_manifest_path=training_manifest_path,
        coverage_path=coverage_path,
    )
    contract["started_at_utc"] = datetime.now(timezone.utc).isoformat()
    _write_json(output_dir / "preflight_contract.json", contract)

    proxy_frames: list[pd.DataFrame] = []
    for fold in FOLDS:
        train = support.loc[support["signal_session_index"].between(fold.train_start, fold.train_end)].copy()
        val = oof.loc[oof["fold"].eq(fold.name)].copy()
        if train.empty or val.empty:
            raise ReliabilityDataBlocked(f"{fold.name} empty train/validation population")
        val = attach_feature_support(train, val)
        margin_parts: list[pd.Series] = []
        quality_parts: list[pd.Series] = []
        for _, session in val.groupby("date", sort=True):
            margin_parts.append(score_margin_reliability(session))
            quality_parts.append(local_pairwise_quality(session))
        val["score_margin_reliability"] = pd.concat(margin_parts).reindex(val.index)
        val["local_pairwise_quality"] = pd.concat(quality_parts).reindex(val.index)
        proxy_frames.append(val)
    proxy_rows = pd.concat(proxy_frames, ignore_index=True).sort_values(
        ["fold", "signal_session_index", "ticker"], kind="mergesort"
    )

    session_rows: list[dict[str, object]] = []
    for (fold, date), session in proxy_rows.groupby(["fold", "date"], sort=True):
        base_eligible = len(session) >= 30 and session["binary_target"].nunique() == 2
        for proxy in ALL_PROXIES:
            metrics = session_proxy_metrics(session, proxy) if base_eligible else {
                "rows": int(len(session)), "eligible": False, "spearman": np.nan,
                "q4_minus_q1_quality_lift": np.nan, "selective_quality_lift_at_40pct": np.nan,
                "conditional_quality_lift": np.nan,
            }
            session_rows.append({"fold": fold, "signal_date": date, "proxy": proxy, **metrics})
    session_metrics = pd.DataFrame(session_rows)

    fold_rows: list[dict[str, object]] = []
    for (fold, proxy), block in session_metrics.groupby(["fold", "proxy"], sort=True):
        eligible = block.loc[block["eligible"].astype(bool)].copy()
        if proxy in PRIMARY_PROXIES and len(eligible) < 80:
            raise ReliabilityDataBlocked(f"{fold} {proxy} has fewer than 80 eligible sessions")
        fold_rows.append({
            "fold": fold,
            "proxy": proxy,
            "eligible_sessions": int(len(eligible)),
            "median_session_spearman": float(eligible["spearman"].median()) if len(eligible) else np.nan,
            "mean_q4_minus_q1_quality_lift": float(eligible["q4_minus_q1_quality_lift"].mean()) if len(eligible) else np.nan,
            "mean_selective_quality_lift_at_40pct": float(eligible["selective_quality_lift_at_40pct"].mean()) if len(eligible) else np.nan,
            "mean_conditional_quality_lift": float(eligible["conditional_quality_lift"].mean()) if len(eligible) else np.nan,
        })
    fold_metrics = pd.DataFrame(fold_rows)

    gate_rows = [evaluate_proxy_gate(fold_metrics, proxy) for proxy in PRIMARY_PROXIES]
    gate_summary = pd.DataFrame(gate_rows)
    qualified = gate_summary.loc[gate_summary["qualified"].astype(bool), "proxy"].tolist()
    verdict = "RELIABILITY_V0_FEASIBILITY_GO" if qualified else "RELIABILITY_V0_NO_SIGNAL"
    decision = {
        "data_ready": True,
        "verdict": verdict,
        "qualified_primary_proxies": qualified,
        "primary_proxy_count": len(PRIMARY_PROXIES),
        "runtime_flags": RUNTIME_FLAGS,
    }

    proxy_rows[[
        "fold", "ticker", "date", "signal_session_index", "score", "binary_target",
        *ALL_PROXIES, "local_pairwise_quality"
    ]].to_parquet(output_dir / "proxy_rows.parquet", index=False)
    session_metrics.to_csv(output_dir / "session_metrics.csv", index=False)
    fold_metrics.to_csv(output_dir / "fold_proxy_metrics.csv", index=False)
    gate_summary.to_csv(output_dir / "proxy_gate_summary.csv", index=False)
    _write_json(output_dir / "aggregate_decision.json", decision)

    artifacts = {
        path.name: sha256_file(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "artifact_manifest.json"
    }
    manifest = {
        "schema": "idx-trade/reliability-uncertainty-v0-artifacts-v1",
        "status": verdict,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "rows": {"o2_oof": int(len(proxy_rows)), "session_metric_rows": int(len(session_metrics))},
        "qualified_primary_proxies": qualified,
        "artifact_sha256": artifacts,
        "input_contract": contract,
        "runtime_flags": RUNTIME_FLAGS,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
    }
    _write_json(output_dir / "artifact_manifest.json", manifest)
    return {
        "verdict": verdict,
        "qualified_primary_proxies": qualified,
        "o2_oof_rows": int(len(proxy_rows)),
        "gate_summary": gate_summary,
        "artifact_manifest_sha256": sha256_file(output_dir / "artifact_manifest.json"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--o2-root", type=Path, required=True)
    parser.add_argument("--training-table", type=Path, required=True)
    parser.add_argument("--training-manifest", type=Path, required=True)
    parser.add_argument("--coverage-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run_diagnostic(
        o2_root=args.o2_root,
        training_table_path=args.training_table,
        training_manifest_path=args.training_manifest,
        coverage_path=args.coverage_path,
        output_dir=args.output_dir,
    )
    print(json.dumps({
        "verdict": result["verdict"],
        "qualified_primary_proxies": result["qualified_primary_proxies"],
        "o2_oof_rows": result["o2_oof_rows"],
        "artifact_manifest_sha256": result["artifact_manifest_sha256"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
