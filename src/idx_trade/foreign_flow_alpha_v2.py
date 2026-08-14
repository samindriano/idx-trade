"""One-shot, preregistered Foreign Flow V2 core alpha experiment.

The runner consumes only the accepted Clean V2 historical table, the pinned
Foreign Flow V2 representation, and the accepted Clean V2 fold models.  It
has no provider or forward-runtime path.  All experiment outputs are written
to an explicitly supplied external directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline


V2_MODEL = "HGB_XS_MARKET"
BASE_MODEL = "BASE_CLEAN_V2_HGB_XS_MARKET"
CHALLENGER_MODEL = "CHALLENGER_CLEAN_V2_PLUS_FOREIGN_FLOW_V2_CORE"
HISTORICAL_BOUNDARY = pd.Timestamp("2026-07-31")
RANDOM_SEED = 42
HGB_PARAMS = {
    "learning_rate": 0.05,
    "max_iter": 200,
    "max_leaf_nodes": 31,
    "l2_regularization": 1.0,
    "random_state": RANDOM_SEED,
}

V2_FEATURE_COLUMNS = (
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
)

FOREIGN_FLOW_V2_CORE_FEATURE_COLUMNS = (
    "foreign_participation_1",
    "foreign_flow_shock_percentile_120",
    "xs_rank_foreign_flow_shock_mean_5",
    "xs_rank_foreign_flow_shock_mean_20",
    "foreign_weighted_persistence_5",
    "foreign_flow_acceleration_5_20",
    "foreign_flow_price_divergence_5",
    "foreign_flow_price_divergence_20",
)
CHALLENGER_FEATURE_COLUMNS = (*V2_FEATURE_COLUMNS, *FOREIGN_FLOW_V2_CORE_FEATURE_COLUMNS)


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

EXPECTED_V2_TABLE_SHA256 = "b27a603cea39298f18996629a16f25990d3d04422b12ccb5d9bd1e45dbb34af8"
EXPECTED_FLOW_FEATURE_SHA256 = "0c2212a166115b2f5b974b93096ea06b222b7451d70fa7d58257a9bed0f7a1f0"
EXPECTED_FLOW_MANIFEST_SHA256 = "4e8e7278b6505a356c2f95c4ac69a47cb4dc91803cc819cf6b0aaafbe34c98dc"
EXPECTED_CALENDAR_SHA256 = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
EXPECTED_V2_ROWS = 292_631
EXPECTED_V2_TICKERS = 737
EXPECTED_V2_KEY_SHA256 = "79d33b233f65b282189917c7226e979956da7f0599a5ba484d82a154ed1ea826"
EXPECTED_V2_ORDER_SHA256 = "1107bf6a65d0b2c86128de7c1123c876ffc9c5e19471b6f32852727f8c5b9a72"
EXPECTED_BASE_MODEL_SHA256 = {
    "V2F1": "d8b8d33808d899cfebd050ae35e5cbca1f4c522241553067e7d94e9c70d3a4b3",
    "V2F2": "bdce9e146227943fbeac21e6d8cc46bff2efd4a3ef1585c82f0264f5f0e1787f",
    "V2F3": "e3f2a19cd58453e029272e94058710c97f7a080e0b33056dc892d179ed8fc4ad",
    "V2F4": "3ee75ae5e9793965e6302c0e7460bbf1048421f65adb4934a19cc83dab688d3b",
    "V2F5": "60e5194916491f98b57c461791f3c8e3900ef400613a7c4122f9ae98811809bd",
    "V2F6": "f1893a6ce1dd3d2faa5998e48650d0fee0cb520d8d838b1b05978fb7809ba1d3",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_columns(columns: Sequence[str]) -> str:
    payload = json.dumps(list(columns), separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _normalize_dates(series: pd.Series) -> pd.Series:
    values = pd.to_datetime(series, errors="coerce")
    if getattr(values.dt, "tz", None) is not None:
        values = values.dt.tz_localize(None)
    return values.dt.normalize()


def _stable_key_hash(frame: pd.DataFrame) -> str:
    keys = frame[["ticker", "date", "signal_session_index"]].copy()
    keys["ticker"] = keys["ticker"].astype(str)
    keys["date"] = _normalize_dates(keys["date"]).dt.strftime("%Y-%m-%d")
    keys["signal_session_index"] = pd.to_numeric(keys["signal_session_index"], errors="raise").astype(int)
    lines = keys.sort_values(["ticker", "date", "signal_session_index"], kind="mergesort").astype(str).agg("|".join, axis=1)
    return hashlib.sha256(("\n".join(lines.tolist()) + "\n").encode("utf-8")).hexdigest()


def _require_sha(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"{label} missing: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"{label} SHA mismatch: expected {expected}, got {actual}")
    return actual


def _load_calendar(path: Path) -> dict[pd.Timestamp, int]:
    _require_sha(path, EXPECTED_CALENDAR_SHA256, "official calendar")
    calendar = pd.read_csv(path)
    date_column = next((c for c in ("date", "session_date", "Date") if c in calendar.columns), None)
    if date_column is None:
        raise RuntimeError("official calendar has no date column")
    dates = _normalize_dates(calendar[date_column])
    if dates.isna().any() or dates.duplicated().any():
        raise RuntimeError("official calendar has invalid or duplicate dates")
    index_column = next((c for c in ("session_index", "signal_session_index", "index") if c in calendar.columns), None)
    indices = pd.Series(np.arange(1, len(calendar) + 1), index=calendar.index) if index_column is None else pd.to_numeric(calendar[index_column], errors="raise").astype(int)
    if indices.duplicated().any() or indices.min() != 1:
        raise RuntimeError("official calendar has invalid session indices")
    return {pd.Timestamp(date): int(index) for date, index in zip(dates, indices, strict=True)}


def verify_flow_temporal_contract(flow: pd.DataFrame, calendar_map: dict[pd.Timestamp, int]) -> dict[str, int]:
    required = {"ticker", "feature_session", "flow_through_session", *FOREIGN_FLOW_V2_CORE_FEATURE_COLUMNS}
    missing = required - set(flow.columns)
    if missing:
        raise RuntimeError(f"flow artifact missing {sorted(missing)}")
    data = flow.copy()
    data["feature_session"] = _normalize_dates(data["feature_session"])
    data["flow_through_session"] = _normalize_dates(data["flow_through_session"])
    data["ticker"] = data["ticker"].astype(str).str.upper().str.strip()
    if data[["feature_session", "flow_through_session"]].isna().any().any():
        raise RuntimeError("flow artifact contains invalid temporal identity")
    if data.duplicated(["ticker", "feature_session"]).any():
        raise RuntimeError("flow artifact contains duplicate ticker/feature_session keys")
    feature_indices = data["feature_session"].map(calendar_map)
    through_indices = data["flow_through_session"].map(calendar_map)
    if feature_indices.isna().any() or through_indices.isna().any():
        raise RuntimeError("flow artifact contains dates absent from official calendar")
    if not (through_indices.astype(int).to_numpy() == feature_indices.astype(int).to_numpy() - 1).all():
        raise RuntimeError("flow feature row is not strictly t+1 from flow_through_session t")
    return {"rows": int(len(data)), "tickers": int(data["ticker"].nunique()), "feature_sessions": int(data["feature_session"].nunique())}


def _pipeline(columns: Sequence[str]) -> Pipeline:
    numeric = Pipeline([("impute", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True))])
    return Pipeline([
        ("preprocess", ColumnTransformer([("numeric", numeric, list(columns))], remainder="drop")),
        ("model", HistGradientBoostingClassifier(**HGB_PARAMS)),
    ])


def _raw_score(model: Pipeline, frame: pd.DataFrame, columns: Sequence[str]) -> np.ndarray:
    transformed = model.named_steps["preprocess"].transform(frame.loc[:, columns])
    probability = np.asarray(model.named_steps["model"].predict_proba(transformed)[:, 1], dtype=float)
    clipped = np.clip(probability, 1e-9, 1.0 - 1e-9)
    return np.log(clipped / (1.0 - clipped))


def _ranking_metrics(frame: pd.DataFrame, score: np.ndarray) -> dict[str, float]:
    target = frame["binary_target"].astype(int).to_numpy()
    values = np.asarray(score, dtype=float)
    if len(target) == 0 or len(target) != len(values) or not np.isfinite(values).all():
        raise RuntimeError("invalid ranking score alignment")
    if np.unique(target).size != 2:
        raise RuntimeError("fold validation must contain both target classes")
    scored = frame[["ticker", "date", "binary_target"]].copy()
    scored["score"] = values
    quintile_parts: list[pd.DataFrame] = []
    decile_parts: list[pd.DataFrame] = []
    for _, group in scored.groupby("date", sort=True):
        ordered = group.sort_values(["score", "ticker"], kind="mergesort").copy()
        n = len(ordered)
        ordered["quintile"] = np.ceil(5 * np.arange(1, n + 1) / n).astype(int).clip(1, 5)
        ordered["decile"] = np.ceil(10 * np.arange(1, n + 1) / n).astype(int).clip(1, 10)
        quintile_parts.append(ordered[["quintile", "binary_target"]])
        decile_parts.append(ordered[["decile", "binary_target"]])
    quintiles = pd.concat(quintile_parts, ignore_index=True)
    deciles = pd.concat(decile_parts, ignore_index=True)
    overall = float(target.mean())
    q1 = float(quintiles.loc[quintiles["quintile"].eq(1), "binary_target"].mean())
    q5 = float(quintiles.loc[quintiles["quintile"].eq(5), "binary_target"].mean())
    top = float(deciles.loc[deciles["decile"].eq(10), "binary_target"].mean())
    pr = float(average_precision_score(target, values))
    return {"rows": float(len(target)), "positive_rate": overall, "pr_auc": pr, "pr_auc_delta_vs_prevalence": pr - overall, "roc_auc": float(roc_auc_score(target, values)), "q1_tp_rate": q1, "q5_tp_rate": q5, "q5_minus_q1": q5 - q1, "top_decile_tp_rate": top, "top_decile_lift": top - overall}


def _aggregate(paired: pd.DataFrame) -> dict[str, float | int]:
    pr = paired["paired_pr_auc_delta"].to_numpy(dtype=float)
    return {"folds": int(len(pr)), "median_paired_pr_auc_delta": float(np.median(pr)), "q25_paired_pr_auc_delta": float(np.quantile(pr, 0.25)), "worst_paired_pr_auc_delta": float(np.min(pr)), "positive_paired_pr_auc_folds": int(np.sum(pr > 0.0)), "median_roc_auc_delta": float(np.median(paired["roc_auc_delta"])), "median_q5_minus_q1_delta": float(np.median(paired["q5_minus_q1_delta"]))}


def _gate(base: pd.DataFrame, paired: pd.DataFrame) -> dict[str, Any]:
    aggregate = _aggregate(paired)
    base_roc = float(base["roc_auc"].median())
    challenger_roc = float(paired["challenger_roc_auc"].median())
    base_spread = float(base["q5_minus_q1"].median())
    challenger_spread = float(paired["challenger_q5_minus_q1"].median())
    reversal = challenger_roc < base_roc and challenger_spread < base_spread
    checks = {"median_paired_pr_auc_gt_0": aggregate["median_paired_pr_auc_delta"] > 0.0, "q25_paired_pr_auc_gt_0": aggregate["q25_paired_pr_auc_delta"] > 0.0, "positive_paired_pr_auc_folds_ge_2": aggregate["positive_paired_pr_auc_folds"] >= 2, "ranking_guardrail_not_reversed": not reversal}
    return {"aggregate": aggregate, "base_median_roc_auc": base_roc, "challenger_median_roc_auc": challenger_roc, "base_median_q5_minus_q1": base_spread, "challenger_median_q5_minus_q1": challenger_spread, "guardrail_reversal": reversal, "checks": checks, "verdict": "FOREIGN_FLOW_V2_CORE_SURVIVOR" if all(checks.values()) else "FOREIGN_FLOW_V2_CORE_NO_SURVIVOR"}


def _load_and_join(*, table_path: Path, flow_path: Path, calendar_path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    table_sha = _require_sha(table_path, EXPECTED_V2_TABLE_SHA256, "clean V2 table")
    flow_sha = _require_sha(flow_path, EXPECTED_FLOW_FEATURE_SHA256, "Foreign Flow V2 feature parquet")
    if _hash_columns(V2_FEATURE_COLUMNS) != EXPECTED_V2_ORDER_SHA256:
        raise RuntimeError("clean V2 feature-order hash mismatch")
    calendar_map = _load_calendar(calendar_path)
    table = pd.read_parquet(table_path)
    flow = pd.read_parquet(flow_path)
    required_table = {"ticker", "date", "signal_session_index", "binary_target", *V2_FEATURE_COLUMNS}
    missing = required_table - set(table.columns)
    if missing:
        raise RuntimeError(f"clean V2 table missing {sorted(missing)}")
    if len(table) != EXPECTED_V2_ROWS or table["ticker"].nunique() != EXPECTED_V2_TICKERS:
        raise RuntimeError("clean V2 row/ticker population mismatch")
    table = table.copy()
    table["ticker"] = table["ticker"].astype(str).str.upper().str.strip()
    table["date"] = _normalize_dates(table["date"])
    table["signal_session_index"] = pd.to_numeric(table["signal_session_index"], errors="raise").astype(int)
    if table[["ticker", "date"]].duplicated().any() or table["date"].isna().any():
        raise RuntimeError("clean V2 table has duplicate or invalid identity")
    if table["date"].max() > HISTORICAL_BOUNDARY:
        raise RuntimeError("clean V2 table contains post-boundary rows")
    if _stable_key_hash(table) != EXPECTED_V2_KEY_SHA256:
        raise RuntimeError("clean V2 key hash mismatch")
    statuses = set(table.get("label_status", pd.Series(dtype=str)).dropna().astype(str))
    if statuses and statuses != {"TP_FIRST", "SL_FIRST"}:
        raise RuntimeError(f"unexpected H10 label statuses: {sorted(statuses)}")
    flow = flow.copy()
    flow_stats = verify_flow_temporal_contract(flow, calendar_map)
    flow["feature_session"] = _normalize_dates(flow["feature_session"])
    flow["flow_through_session"] = _normalize_dates(flow["flow_through_session"])
    flow["ticker"] = flow["ticker"].astype(str).str.upper().str.strip()
    joined = table.merge(flow[["ticker", "feature_session", "flow_through_session", *FOREIGN_FLOW_V2_CORE_FEATURE_COLUMNS]], left_on=["ticker", "date"], right_on=["ticker", "feature_session"], how="left", validate="one_to_one").drop(columns=["feature_session"])
    if len(joined) != len(table) or _stable_key_hash(joined) != EXPECTED_V2_KEY_SHA256:
        raise RuntimeError("BASE/CHALLENGER common support identity changed during flow join")
    through = joined["flow_through_session"].notna()
    if through.any():
        feature_indices = joined.loc[through, "date"].map(calendar_map)
        through_indices = joined.loc[through, "flow_through_session"].map(calendar_map)
        if feature_indices.isna().any() or through_indices.isna().any() or not (through_indices.astype(int).to_numpy() == feature_indices.astype(int).to_numpy() - 1).all():
            raise RuntimeError("joined flow rows violate t -> t+1 causality")
    diagnostics = {"clean_v2_table_sha256": table_sha, "foreign_flow_feature_sha256": flow_sha, "common_support_rows": int(len(joined)), "common_support_tickers": int(joined["ticker"].nunique()), "common_support_sessions": int(joined["date"].nunique()), "common_support_key_sha256": _stable_key_hash(joined), "flow_rows": flow_stats["rows"], "flow_tickers": flow_stats["tickers"], "flow_feature_sessions": flow_stats["feature_sessions"], "joined_flow_rows": int(through.sum()), "missing_flow_rows": int((~through).sum()), "all_flow_features_missing_rows": int(joined[list(FOREIGN_FLOW_V2_CORE_FEATURE_COLUMNS)].isna().all(axis=1).sum()), "partial_flow_feature_rows": int(joined[list(FOREIGN_FLOW_V2_CORE_FEATURE_COLUMNS)].notna().any(axis=1).sum() - joined[list(FOREIGN_FLOW_V2_CORE_FEATURE_COLUMNS)].notna().all(axis=1).sum()), "complete_flow_feature_rows": int(joined[list(FOREIGN_FLOW_V2_CORE_FEATURE_COLUMNS)].notna().all(axis=1).sum()), "calendar_sha256": EXPECTED_CALENDAR_SHA256, "feature_session_is_decision_session": True, "flow_through_session_is_previous_official_session": True, "same_or_future_flow_session_detected": False, "predictor_status_columns_used": False}
    return joined.sort_values(["signal_session_index", "ticker"], kind="mergesort").reset_index(drop=True), diagnostics


def run_experiment(*, table_path: Path, flow_path: Path, flow_manifest_path: Path, calendar_path: Path, base_model_dir: Path, preregistration_path: Path, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError(f"output directory must be new or empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    table, support = _load_and_join(table_path=table_path, flow_path=flow_path, calendar_path=calendar_path)
    flow_manifest_sha = _require_sha(flow_manifest_path, EXPECTED_FLOW_MANIFEST_SHA256, "Foreign Flow V2 manifest")
    prereg_sha = sha256_file(preregistration_path) if preregistration_path.is_file() else None
    if prereg_sha is None:
        raise FileNotFoundError(f"preregistration missing: {preregistration_path}")
    fold_rows: list[dict[str, Any]] = []
    paired_rows: list[dict[str, Any]] = []
    prediction_frames: list[pd.DataFrame] = []
    challenger_hashes: dict[str, str] = {}
    for fold in FOLDS:
        train = table[table["signal_session_index"].between(fold.train_start, fold.train_end)].copy()
        validation = table[table["signal_session_index"].between(fold.validation_start, fold.validation_end)].copy()
        if train.empty or validation.empty or train["binary_target"].nunique() != 2 or validation["binary_target"].nunique() != 2:
            raise RuntimeError(f"{fold.name} has invalid train/validation target support")
        base_path = base_model_dir / f"hgb_xs_market_{fold.name.lower()}.joblib"
        _require_sha(base_path, EXPECTED_BASE_MODEL_SHA256[fold.name], f"accepted clean V2 {fold.name} model")
        base_model = joblib.load(base_path)
        challenger_model = _pipeline(CHALLENGER_FEATURE_COLUMNS)
        challenger_model.fit(train.loc[:, CHALLENGER_FEATURE_COLUMNS], train["binary_target"].astype(int))
        challenger_path = output_dir / f"foreign_flow_v2_core_hgb_xs_market_{fold.name.lower()}.joblib"
        joblib.dump(challenger_model, challenger_path)
        challenger_hashes[challenger_path.name] = sha256_file(challenger_path)
        base_metrics = _ranking_metrics(validation, _raw_score(base_model, validation, V2_FEATURE_COLUMNS))
        challenger_metrics = _ranking_metrics(validation, _raw_score(challenger_model, validation, CHALLENGER_FEATURE_COLUMNS))
        fold_rows.extend([{ "model": BASE_MODEL, "fold": fold.name, **base_metrics }, { "model": CHALLENGER_MODEL, "fold": fold.name, **challenger_metrics }])
        paired_rows.append({"fold": fold.name, "base_pr_auc": base_metrics["pr_auc"], "challenger_pr_auc": challenger_metrics["pr_auc"], "paired_pr_auc_delta": challenger_metrics["pr_auc"] - base_metrics["pr_auc"], "base_pr_auc_delta_vs_prevalence": base_metrics["pr_auc_delta_vs_prevalence"], "challenger_pr_auc_delta_vs_prevalence": challenger_metrics["pr_auc_delta_vs_prevalence"], "base_roc_auc": base_metrics["roc_auc"], "challenger_roc_auc": challenger_metrics["roc_auc"], "roc_auc_delta": challenger_metrics["roc_auc"] - base_metrics["roc_auc"], "base_q5_minus_q1": base_metrics["q5_minus_q1"], "challenger_q5_minus_q1": challenger_metrics["q5_minus_q1"], "q5_minus_q1_delta": challenger_metrics["q5_minus_q1"] - base_metrics["q5_minus_q1"], "base_top_decile_lift": base_metrics["top_decile_lift"], "challenger_top_decile_lift": challenger_metrics["top_decile_lift"], "top_decile_lift_delta": challenger_metrics["top_decile_lift"] - base_metrics["top_decile_lift"], "train_rows": int(len(train)), "validation_rows": int(len(validation))})
        prediction_frames.append(validation[["ticker", "date", "signal_session_index", "binary_target"]].assign(fold=fold.name, base_score=_raw_score(base_model, validation, V2_FEATURE_COLUMNS), challenger_score=_raw_score(challenger_model, validation, CHALLENGER_FEATURE_COLUMNS)))
    fold_metrics = pd.DataFrame(fold_rows)
    paired = pd.DataFrame(paired_rows)
    gate = _gate(fold_metrics[fold_metrics["model"].eq(BASE_MODEL)].sort_values("fold").reset_index(drop=True), paired.sort_values("fold").reset_index(drop=True))
    predictions = pd.concat(prediction_frames, ignore_index=True).sort_values(["fold", "date", "ticker"], kind="mergesort")
    aggregate = {"base": {"median_pr_auc": float(fold_metrics.loc[fold_metrics["model"].eq(BASE_MODEL), "pr_auc"].median()), "median_roc_auc": float(fold_metrics.loc[fold_metrics["model"].eq(BASE_MODEL), "roc_auc"].median()), "median_q5_minus_q1": float(fold_metrics.loc[fold_metrics["model"].eq(BASE_MODEL), "q5_minus_q1"].median())}, "challenger": {"median_pr_auc": float(fold_metrics.loc[fold_metrics["model"].eq(CHALLENGER_MODEL), "pr_auc"].median()), "median_roc_auc": float(fold_metrics.loc[fold_metrics["model"].eq(CHALLENGER_MODEL), "roc_auc"].median()), "median_q5_minus_q1": float(fold_metrics.loc[fold_metrics["model"].eq(CHALLENGER_MODEL), "q5_minus_q1"].median())}}
    paths = {"paired_predictions.parquet": predictions, "common_support_keys.csv": None, "fold_metrics.csv": fold_metrics, "paired_metrics.csv": paired}
    predictions.to_parquet(output_dir / "paired_predictions.parquet", index=False)
    support_keys = table[["ticker", "date", "signal_session_index"]].copy(); support_keys["date"] = support_keys["date"].dt.strftime("%Y-%m-%d"); support_keys.to_csv(output_dir / "common_support_keys.csv", index=False)
    fold_metrics.to_csv(output_dir / "fold_metrics.csv", index=False); paired.to_csv(output_dir / "paired_metrics.csv", index=False)
    (output_dir / "aggregate_metrics.json").write_text(json.dumps(aggregate, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "gate.json").write_text(json.dumps(gate, indent=2, sort_keys=True), encoding="utf-8")
    artifact_paths = [output_dir / name for name in ("paired_predictions.parquet", "common_support_keys.csv", "fold_metrics.csv", "paired_metrics.csv", "aggregate_metrics.json", "gate.json")] + [output_dir / name for name in challenger_hashes]
    manifest = {"schema": "idx-trade/foreign-flow-alpha-v2-core", "status": "FOREIGN_FLOW_V2_CORE_ALPHA_COMPLETE", "verdict": gate["verdict"], "parent_model": V2_MODEL, "base_model": BASE_MODEL, "challenger_model": CHALLENGER_MODEL, "folds": [asdict(fold) for fold in FOLDS], "feature_columns": {"base": list(V2_FEATURE_COLUMNS), "challenger": list(CHALLENGER_FEATURE_COLUMNS), "foreign_flow_v2_core": list(FOREIGN_FLOW_V2_CORE_FEATURE_COLUMNS)}, "feature_order_sha256": {"base": _hash_columns(V2_FEATURE_COLUMNS), "foreign_flow_v2_core": _hash_columns(FOREIGN_FLOW_V2_CORE_FEATURE_COLUMNS), "challenger": _hash_columns(CHALLENGER_FEATURE_COLUMNS)}, "support": support, "aggregate": aggregate, "gate": gate, "historical_boundary": HISTORICAL_BOUNDARY.date().isoformat(), "preregistration": {"path": str(preregistration_path), "sha256": prereg_sha}, "input_sha256": {"clean_v2_table": EXPECTED_V2_TABLE_SHA256, "foreign_flow_v2_feature": EXPECTED_FLOW_FEATURE_SHA256, "foreign_flow_v2_manifest": flow_manifest_sha, "official_calendar": EXPECTED_CALENDAR_SHA256, "base_models": EXPECTED_BASE_MODEL_SHA256}, "provider_calls": False, "fresh_forward_outcomes_accessed": False, "protected_o2_outcomes_accessed": False, "artifacts": {path.name: sha256_file(path) for path in artifact_paths}, "runtime_seconds": time.perf_counter() - started, "environment": {"python": platform.python_version(), "platform": platform.platform(), "numpy": np.__version__, "pandas": pd.__version__}}
    manifest_path = output_dir / "manifest.json"; manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str), encoding="utf-8")
    manifest_sha = sha256_file(manifest_path)
    (output_dir / "result.json").write_text(json.dumps({"verdict": gate["verdict"], "manifest_sha256": manifest_sha, "gate": gate, "support": support}, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return {"verdict": gate["verdict"], "manifest_sha256": manifest_sha, "support": support, "gate": gate, "aggregate": aggregate, "output_dir": str(output_dir)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", type=Path, required=True)
    parser.add_argument("--flow", type=Path, required=True)
    parser.add_argument("--flow-manifest", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--base-model-dir", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(json.dumps(run_experiment(table_path=args.table, flow_path=args.flow, flow_manifest_path=args.flow_manifest, calendar_path=args.calendar, base_model_dir=args.base_model_dir, preregistration_path=args.preregistration, output_dir=args.output_dir), indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
