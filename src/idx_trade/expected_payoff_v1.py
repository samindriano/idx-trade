"""Frozen Expected Payoff V1 historical experiment.

This module is deliberately a one-candidate runner.  It consumes the accepted
V0 payoff rows and O2 feature/support artifacts, fits one fold-local
HistGradientBoostingRegressor, and never touches forward runtime state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer

from .expected_payoff_v0 import (
    ACCEPTED_OPEN_STATUSES,
    MAX_ALLOWED_DATE,
    REQUIRED_FOLDS,
    PayoffDataBlocked,
    _dates,
    build_payoff_rows,
    load_actions,
    load_calendar,
    load_open_provenance,
    load_price_frame,
    load_tradability,
    sha256_file,
    stable_key_sha256,
)


FEATURES_33 = [
    "xs_rank_close_return_5", "xs_rank_close_return_20", "xs_rank_atr14_over_close",
    "xs_rank_close_position_20", "xs_rank_distance_high_20_atr", "xs_rank_distance_low_20_atr",
    "xs_rank_distance_high_60_atr", "xs_rank_distance_low_60_atr", "xs_rank_relative_volume_20",
    "xs_rank_log_regular_value_relative_20", "market_primary_liquid_count",
    "market_breadth_return_5_positive", "market_breadth_return_20_positive",
    "market_median_close_return_5", "market_median_close_return_20", "market_median_atr14_over_close",
    "market_median_close_position_20", "market_median_relative_volume_20",
    "market_median_log_regular_value_relative_20", "market_relative_close_return_5",
    "market_relative_close_return_20", "market_relative_atr14_over_close",
    "market_relative_close_position_20", "market_relative_relative_volume_20",
    "market_relative_log_regular_value_relative_20", "structure_support_distance_atr",
    "structure_resistance_distance_atr", "structure_support_touch_count_60",
    "structure_resistance_touch_count_60", "structure_nearest_level_age_sessions",
    "structure_role_reversal_count_120", "structure_breakout_retest_state",
    "structure_breakout_volume_confirmed",
]
FEATURES_36 = FEATURES_33 + ["open_position", "open_to_high", "open_to_low"]
FEATURE_HASH = "a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f"
MODEL_CONTRACT = {
    "candidate": "PAYOFF_HGB_O2_FEATURES_V1",
    "estimator": "sklearn.ensemble.HistGradientBoostingRegressor",
    "loss": "squared_error", "learning_rate": 0.05, "max_iter": 200,
    "max_leaf_nodes": 31, "l2_regularization": 1.0,
    "early_stopping": False, "random_state": 42,
    "preprocessor": "SimpleImputer(strategy=median, add_indicator=True, keep_empty_features=True)",
    "features": FEATURES_36,
    "feature_order_sha256": FEATURE_HASH,
    "target": "payoff_atr_gross",
    "o2_score_is_comparator_only": True,
}


def _require_sha(path: Path, expected: str, label: str) -> None:
    if not path.is_file():
        raise PayoffDataBlocked(f"missing {label}: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise PayoffDataBlocked(f"{label} SHA mismatch: expected {expected}, got {actual}")


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def feature_order_sha256(columns: list[str]) -> str:
    return hashlib.sha256(json.dumps(columns, separators=(",", ":")).encode("utf-8")).hexdigest()


def validate_feature_order(columns: list[str]) -> None:
    if columns != FEATURES_36:
        raise PayoffDataBlocked("V1 feature order must equal the frozen exact 36-feature contract")
    if feature_order_sha256(columns) != FEATURE_HASH:
        raise PayoffDataBlocked("V1 feature-order SHA mismatch")


def validate_validation_keys(frame: pd.DataFrame, expected_sha: str) -> None:
    actual = stable_key_sha256(frame, ["ticker", "signal_date", "fold", "signal_session_index"])
    if actual != expected_sha:
        raise PayoffDataBlocked(f"V0 validation key SHA mismatch: expected {expected_sha}, got {actual}")


def common_support_key_sha256(frame: pd.DataFrame) -> str:
    keys = frame[["ticker", "date", "signal_session_index"]].copy()
    keys["ticker"] = keys["ticker"].astype(str)
    keys["date"] = pd.to_datetime(keys["date"], errors="raise").dt.strftime("%Y-%m-%d")
    keys["signal_session_index"] = pd.to_numeric(keys["signal_session_index"], errors="raise").astype(int)
    lines = keys.sort_values(["ticker", "date", "signal_session_index"], kind="mergesort").astype(str).agg("|".join, axis=1)
    return hashlib.sha256(("\n".join(lines.tolist()) + "\n").encode("utf-8")).hexdigest()


def train_mean_baseline(y: pd.Series | np.ndarray) -> tuple[float, float]:
    values = np.asarray(y, dtype=float)
    if len(values) == 0 or not np.isfinite(values).all():
        raise PayoffDataBlocked("training target is empty or non-finite")
    mean = float(values.mean())
    mse = float(np.mean((values - mean) ** 2))
    if not np.isfinite(mse) or mse <= 0:
        raise PayoffDataBlocked("training-mean baseline MSE is zero/non-finite")
    return mean, mse


def fit_fold_model(train_x: pd.DataFrame, train_y: pd.Series) -> tuple[SimpleImputer, HistGradientBoostingRegressor, float, float]:
    mean, baseline_mse = train_mean_baseline(train_y)
    imputer = SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)
    x_train = imputer.fit_transform(train_x.loc[:, FEATURES_36])
    model = HistGradientBoostingRegressor(
        loss="squared_error", learning_rate=0.05, max_iter=200,
        max_leaf_nodes=31, l2_regularization=1.0,
        early_stopping=False, random_state=42,
    )
    model.fit(x_train, np.asarray(train_y, dtype=float))
    return imputer, model, mean, baseline_mse


def _spearman(x: pd.Series, y: pd.Series) -> float:
    if len(x) < 2 or x.nunique() < 2 or y.nunique() < 2:
        return float("nan")
    return float(np.corrcoef(x.rank(method="average"), y.rank(method="average"))[0, 1])


def _deciles(frame: pd.DataFrame, score_col: str) -> pd.DataFrame:
    ordered = frame.sort_values([score_col, "ticker"], kind="mergesort").reset_index(drop=True)
    ordinal = np.arange(len(ordered), dtype=int)
    ordered["decile"] = ((ordinal * 10) // max(len(ordered), 1) + 1).clip(1, 10)
    return ordered


def _safe_float(value: object) -> float | None:
    return None if pd.isna(value) else float(value)


def evaluate_survivor_gate(fold_metrics: pd.DataFrame, data_ready: bool) -> dict:
    if not data_ready:
        return {"data_ready": False, "verdict": "EXPECTED_PAYOFF_V1_DATA_BLOCKED"}
    skills = fold_metrics.mse_skill.to_numpy(dtype=float)
    ics = fold_metrics.median_session_ic_atr.to_numpy(dtype=float)
    spreads = fold_metrics.mean_d10_minus_d1_mean_payoff_atr.to_numpy(dtype=float)
    result = {
        "data_ready": True,
        "median_mse_skill": float(np.median(skills)),
        "positive_mse_skill_folds": int((skills > 0).sum()),
        "median_session_ic_atr": float(np.median(ics)),
        "q25_session_ic_atr": float(np.quantile(ics, 0.25)),
        "positive_ic_folds": int((ics > 0).sum()),
        "median_d10_minus_d1_mean_payoff_atr": float(np.median(spreads)),
        "positive_spread_folds": int((spreads > 0).sum()),
    }
    result["verdict"] = (
        "EXPECTED_PAYOFF_V1_SURVIVOR"
        if result["median_mse_skill"] > 0 and result["positive_mse_skill_folds"] >= 4
        and result["median_session_ic_atr"] > 0 and result["q25_session_ic_atr"] > 0
        and result["positive_ic_folds"] >= 4
        and result["median_d10_minus_d1_mean_payoff_atr"] > 0
        and result["positive_spread_folds"] >= 4
        else "EXPECTED_PAYOFF_V1_NO_SURVIVOR"
    )
    return result


def _fold_definitions(path: Path) -> dict[str, dict]:
    payload = _json(path)
    rows = payload if isinstance(payload, list) else payload.get("folds", payload)
    if isinstance(rows, list):
        rows = {row.get("fold", row.get("name")): row for row in rows}
    if set(rows) != set(REQUIRED_FOLDS):
        raise PayoffDataBlocked("fold definitions do not match frozen six folds")
    return rows


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False, default=str) + "\n", encoding="utf-8")


def _default_config(external_root: Path) -> dict:
    research = external_root / "research_feasibility_1260_20260809"
    o2 = external_root / "ohlcv_o2_geometry_v1_20260812"
    open_root = external_root / "open_backfill_zapi_tradingview_derivative_v1_20260811"
    v3 = external_root / "ranking_v3_b_final_refit_20260810_001"
    return {
        "o2_manifest_path": str(o2 / "artifact_manifest.json"), "o2_manifest_sha256": "cc26bc689dd37bc83cc2c32d348d3201e5c4f41577f4bb8f938ab5cac2c7a97a",
        "o2_predictions_path": str(o2 / "fold_predictions.parquet"), "o2_predictions_sha256": "fe02c0c743e7bfc5a57b1c8e731c5685a4bff5f9854f910f88703b15a6ca8f0c",
        "o2_common_support_path": str(o2 / "common_support_rows.csv"), "o2_common_support_sha256": "59b95ad907a8adc911bbf2a411cb1b52a433bd3d225927268440a11b958f6c6f", "o2_common_support_key_sha256": "716bed364b5ba0dcb034f335bc7b09b4abac23eb1236a7c718fe6e0f6a78577a",
        "o2_fold_definitions_path": str(o2 / "fold_definitions.json"), "o2_fold_definitions_sha256": "f16ddd1640701b206cb10418ca9fa7736695fe8268ac5c38213ba22b1fe76046",
        "o2_feature_manifest_path": str(o2 / "feature_manifest.json"), "o2_feature_manifest_sha256": "9014166635a7365d6f0a101132648c24637b04a6af2455063f3f37eee6586f04",
        "v2_prepared_table_path": str(external_root / "ranking_v2_prepared_cache_20260809/ranking_v2_prepared_model_table.parquet"), "v2_prepared_table_sha256": "522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5",
        "v0_resolved_path": str(external_root / "expected_payoff_v0_feasibility_20260812_001/resolved_payoff_rows.parquet"), "v0_resolved_sha256": "13c08f8683a3809d981c698f961ebf4d8154bdf7d1f5f13307f7b2ad552ec102", "v0_validation_key_sha256": "f978ec6b81ddc72259e403e78698971f655721f94fbfdcc57f682c5cea3c4602",
        "calendar_path": str(research / "official_exchange_sessions_1260.csv"), "calendar_sha256": "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a",
        "security_master_path": str(research / "security_master_1260.csv"), "security_master_sha256": "9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9",
        "panel_path": str(research / "unknown_state_diagnostic_1260_20260809/model_safe_signal_research_panel_1260.parquet"), "panel_sha256": "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76",
        "open_panel_path": str(open_root / "execution_open_candidate_panel_yahoo_tradingview.parquet"), "open_panel_sha256": "a1dae0714971904b266a380be6bb96a2a4976068c9d60c54c8c43746826f7cab",
        "open_provenance_path": str(open_root / "execution_open_candidate_provenance_yahoo_tradingview.parquet"), "open_provenance_sha256": "90deaad64ff3330921859eb222df556794c345bb3d440df89edab8ef6d342687",
        "tradability_path": str(research / "tradability_anchors_1260.csv"), "tradability_sha256": "33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e",
        "actions_path": str(research / "corporate_actions_1260/official_idx_split_reverse_actions_1260.csv"), "actions_sha256": "a0ef73a548b3657260b46a0c497e6f87dd9b5138588e23006d4b538677125b35",
        "actions_summary_path": str(research / "corporate_actions_1260/official_idx_split_reverse_actions_1260_summary.json"), "actions_summary_sha256": "cfdc92bc46f47c573dda097a01440768a6c8cd321c686938767462f72172b067",
        "v3_b_training_table_path": str(v3 / "ranking_v3_b_structure_lite_final_training_table.parquet"), "v3_b_training_table_sha256": "5893c9f2872aae0f33acd4104d82ee8c1d4474aae7d54e9d01879724b86dffbe",
        "v3_b_manifest_path": str(v3 / "ranking_v3_b_structure_lite_final_manifest.json"), "v3_b_manifest_sha256": "4e84ce02c6ee856c0f260dd6099b2a479723c53da82131ae669e0bf7e4d384f9",
        "expected_cutoff": "2026-07-31",
    }


def run_experiment(config: dict, output_dir: Path) -> dict:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise PayoffDataBlocked(f"output directory must be new and empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    validate_feature_order(FEATURES_36)
    for key in ("o2_manifest_path", "o2_predictions_path", "o2_common_support_path", "o2_fold_definitions_path", "o2_feature_manifest_path", "v0_resolved_path", "v2_prepared_table_path", "calendar_path", "security_master_path", "panel_path", "open_panel_path", "open_provenance_path", "tradability_path", "actions_path", "actions_summary_path", "v3_b_training_table_path", "v3_b_manifest_path"):
        _require_sha(Path(config[key]), config[key.replace("_path", "_sha256")], key)

    o2_manifest = _json(Path(config["o2_manifest_path"]))
    if o2_manifest.get("status") != "O2_SURVIVOR":
        raise PayoffDataBlocked("parent O2 is not O2_SURVIVOR")
    parent_contract = o2_manifest.get("preflight_contract", {})
    if parent_contract.get("fresh_forward_outcomes_accessed") is not False:
        raise PayoffDataBlocked("parent O2 fresh-forward flag is not false")
    # The accepted O2 manifest predates some V1 flag names.  Missing flags are
    # not silently treated as evidence of access; immutable parent identity,
    # the explicit fresh-forward flag, and the artifact hashes are the frozen
    # contract available from that manifest.
    for name, expected in o2_manifest.get("artifact_sha256", {}).items():
        _require_sha(Path(config["o2_manifest_path"]).parent / name, expected, f"O2 manifest artifact {name}")
    o2_features = _json(Path(config["o2_feature_manifest_path"]))
    if o2_features.get("challenger_feature_columns") != FEATURES_36 or o2_features.get("challenger_feature_order_sha256") != FEATURE_HASH:
        raise PayoffDataBlocked("parent O2 feature manifest does not match frozen V1 feature contract")
    folds = _fold_definitions(Path(config["o2_fold_definitions_path"]))

    common = pd.read_csv(config["o2_common_support_path"])
    common["date"] = pd.to_datetime(common["date"], errors="coerce")
    if common.date.isna().any() or common_support_key_sha256(common) != config["o2_common_support_key_sha256"]:
        raise PayoffDataBlocked("common-support key identity mismatch")
    common["ticker"] = common.ticker.astype(str).str.upper().str.strip()
    calendar = load_calendar(Path(config["calendar_path"]), config["calendar_sha256"])
    panel = load_price_frame(Path(config["panel_path"]), config["panel_sha256"], "immutable panel")
    open_panel = load_price_frame(Path(config["open_panel_path"]), config["open_panel_sha256"], "accepted Open panel")
    open_prov = load_open_provenance(Path(config["open_provenance_path"]), config["open_provenance_sha256"])
    tradability = load_tradability(Path(config["tradability_path"]), config["tradability_sha256"])
    actions = load_actions(Path(config["actions_path"]), config["actions_sha256"], Path(config["actions_summary_path"]), config["actions_summary_sha256"])

    v3 = pd.read_parquet(config["v3_b_training_table_path"])
    v3["date"] = pd.to_datetime(v3["date"])
    v3["ticker"] = v3.ticker.astype(str).str.upper().str.strip()
    keys = ["ticker", "date", "signal_session_index"]
    features = common.merge(v3[keys + FEATURES_33], on=keys, how="left", validate="one_to_one")
    if len(features) != len(common) or features[FEATURES_33].isna().all(axis=1).any():
        raise PayoffDataBlocked("V3-B feature join is incomplete")
    geom = open_panel[["ticker", "date", "open", "high", "low"]].merge(common[["ticker", "date"]], on=["ticker", "date"], how="right", validate="one_to_one")
    denom = geom.high - geom.low
    valid = geom.open.gt(0) & geom.high.ge(geom.low) & denom.gt(0) & geom.open.notna() & geom.high.notna() & geom.low.notna()
    if not bool(valid.all()):
        raise PayoffDataBlocked(f"invalid O2 geometry on {int((~valid).sum())} common-support rows")
    geom["open_position"] = (geom.open - geom.low) / denom
    geom["open_to_high"] = (geom.high - geom.open) / geom.open
    geom["open_to_low"] = (geom.open - geom.low) / geom.open
    features = features.merge(geom[["ticker", "date"] + FEATURES_36[-3:]], on=["ticker", "date"], how="left", validate="one_to_one")
    feature_matrix = features.loc[:, ["ticker", "date", "signal_session_index"] + FEATURES_36].copy()

    v0 = pd.read_parquet(config["v0_resolved_path"])
    v0["signal_date"] = pd.to_datetime(v0["signal_date"])
    v0["ticker"] = v0.ticker.astype(str).str.upper().str.strip()
    v0 = v0.loc[v0.status.eq("RESOLVED")].copy()
    validate_validation_keys(v0, config["v0_validation_key_sha256"])
    v0["fold"] = v0.fold.astype(str)
    common_parent = common.rename(columns={"date": "signal_date"}).copy()
    common_parent["fold"] = "COMMON"
    common_parent["score"] = 0.0
    common_parent = common_parent.rename(columns={"signal_date": "date"})
    # Load the raw V2 prepared table only for the frozen ATR14 ratio.
    prepared = pd.read_parquet(config["v2_prepared_table_path"], columns=["ticker", "date", "signal_session_index", "atr14_over_close"])
    prepared["date"] = pd.to_datetime(prepared["date"])
    prepared["ticker"] = prepared.ticker.astype(str).str.upper().str.strip()
    if prepared.duplicated(["ticker", "date"]).any():
        raise PayoffDataBlocked("V2 prepared ATR keys are duplicated")
    ledger, resolved = build_payoff_rows(common_parent, prepared, calendar, panel, open_panel, open_prov, tradability, actions)
    if resolved.empty:
        raise PayoffDataBlocked("no resolved training payoff rows")
    resolved["fold"] = resolved["fold"].astype(str)
    targets = resolved[["ticker", "signal_date", "signal_session_index", "payoff_atr_gross", "payoff_pct_gross", "entry_date", "exit_date"]].copy()
    targets = targets.rename(columns={"signal_date": "date"})
    target_frame = feature_matrix.merge(targets, on=["ticker", "date", "signal_session_index"], how="left", validate="one_to_one")
    val = v0[["ticker", "signal_date", "signal_session_index", "fold", "score", "payoff_atr_gross", "payoff_pct_gross", "entry_date", "exit_date"]].copy()
    val = val.rename(columns={"signal_date": "date"})
    val_features = val.merge(feature_matrix, on=["ticker", "date", "signal_session_index"], how="left", validate="one_to_one")
    if val_features[FEATURES_36].isna().all(axis=1).any():
        raise PayoffDataBlocked("V0 validation feature join is incomplete")

    fold_rows = []
    validation_predictions = []
    training_coverage = []
    exclusions = []
    model_hashes = {}
    for fold in REQUIRED_FOLDS:
        spec = folds[fold]
        train_end = int(spec.get("train_end", spec.get("train_end_session_index")))
        train_pool = target_frame.loc[target_frame.signal_session_index.le(train_end)].copy()
        eligible = train_pool.loc[train_pool.payoff_atr_gross.notna()].copy()
        training_coverage.append({"fold": fold, "common_support_rows": len(train_pool), "resolved_training_rows": len(eligible), "coverage_ratio": len(eligible) / len(train_pool) if len(train_pool) else 0.0, "train_end": train_end})
        if len(eligible) < 0.90 * len(train_pool):
            raise PayoffDataBlocked(f"{fold} training target coverage below 90%")
        val_part = val_features.loc[val_features.fold.eq(fold)].copy()
        if val_part.empty or val_part[FEATURES_36].isna().all(axis=1).any():
            raise PayoffDataBlocked(f"{fold} validation feature rows incomplete")
        imputer, model, baseline_mean, baseline_mse = fit_fold_model(eligible[FEATURES_36], eligible.payoff_atr_gross)
        pred = model.predict(imputer.transform(val_part[FEATURES_36]))
        if not np.isfinite(pred).all():
            raise PayoffDataBlocked(f"{fold} contains non-finite predictions")
        model_path = output_dir / f"model_{fold}.pkl"
        with model_path.open("wb") as handle:
            pickle.dump({"imputer": imputer, "model": model, "contract": MODEL_CONTRACT}, handle, protocol=pickle.HIGHEST_PROTOCOL)
        model_hashes[fold] = sha256_file(model_path)
        val_part["v1_predicted_payoff_atr"] = pred
        val_part["v1_predicted_payoff_pct_context_only"] = np.nan
        validation_predictions.append(val_part)
        y = val_part.payoff_atr_gross.to_numpy(dtype=float)
        mse = float(np.mean((pred - y) ** 2))
        rmse = float(np.sqrt(mse)); mae = float(np.mean(np.abs(pred - y)))
        sessions = []
        for date, group in val_part.groupby("date", sort=True):
            g = group.loc[np.isfinite(group.v1_predicted_payoff_atr) & np.isfinite(group.payoff_atr_gross)].copy()
            eligible_session = len(g) >= 30 and g.v1_predicted_payoff_atr.nunique() > 1 and g.payoff_atr_gross.nunique() > 1
            d = _deciles(g, "v1_predicted_payoff_atr")
            d1 = d.loc[d.decile.eq(1)]; d10 = d.loc[d.decile.eq(10)]
            o2_ic = _spearman(g.score, g.payoff_atr_gross)
            sessions.append({"fold": fold, "signal_date": date, "rows": len(g), "eligible": bool(eligible_session), "v1_session_ic_atr": _spearman(g.v1_predicted_payoff_atr, g.payoff_atr_gross) if eligible_session else np.nan, "o2_context_session_ic_atr": o2_ic, "d1_mean_payoff_atr": d1.payoff_atr_gross.mean() if eligible_session else np.nan, "d10_mean_payoff_atr": d10.payoff_atr_gross.mean() if eligible_session else np.nan, "d10_minus_d1_mean_payoff_atr": (d10.payoff_atr_gross.mean() - d1.payoff_atr_gross.mean()) if eligible_session else np.nan})
        session_df = pd.DataFrame(sessions)
        eligible_sessions = session_df.loc[session_df.eligible]
        fold_rows.append({"fold": fold, "train_rows": len(eligible), "validation_rows": len(val_part), "eligible_signal_sessions": len(eligible_sessions), "mse_v1": mse, "mse_baseline": baseline_mse, "mse_skill": 1.0 - mse / baseline_mse, "rmse_v1": rmse, "mae_v1": mae, "median_session_ic_atr": eligible_sessions.v1_session_ic_atr.median(), "q25_session_ic_atr": eligible_sessions.v1_session_ic_atr.quantile(0.25), "mean_session_ic_atr": eligible_sessions.v1_session_ic_atr.mean(), "o2_context_median_session_ic_atr": eligible_sessions.o2_context_session_ic_atr.median(), "mean_d10_minus_d1_mean_payoff_atr": eligible_sessions.d10_minus_d1_mean_payoff_atr.mean(), "median_d10_minus_d1_mean_payoff_atr": eligible_sessions.d10_minus_d1_mean_payoff_atr.median()})

    validation = pd.concat(validation_predictions, ignore_index=True).sort_values(["signal_session_index", "ticker"], kind="mergesort")
    session_metrics = []
    for fold in REQUIRED_FOLDS:
        part = validation.loc[validation.fold.eq(fold)]
        for date, g in part.groupby("date", sort=True):
            eligible_session = len(g) >= 30 and g.v1_predicted_payoff_atr.nunique() > 1 and g.payoff_atr_gross.nunique() > 1
            d = _deciles(g, "v1_predicted_payoff_atr")
            d1=d.loc[d.decile.eq(1)]; d10=d.loc[d.decile.eq(10)]
            session_metrics.append({"fold": fold,"signal_date":date,"rows":len(g),"eligible":eligible_session,"v1_session_ic_atr":_spearman(g.v1_predicted_payoff_atr,g.payoff_atr_gross) if eligible_session else np.nan,"o2_context_session_ic_atr":_spearman(g.score,g.payoff_atr_gross),"d1_mean_payoff_atr":d1.payoff_atr_gross.mean() if eligible_session else np.nan,"d10_mean_payoff_atr":d10.payoff_atr_gross.mean() if eligible_session else np.nan,"d10_minus_d1_mean_payoff_atr":(d10.payoff_atr_gross.mean()-d1.payoff_atr_gross.mean()) if eligible_session else np.nan})
    session_df=pd.DataFrame(session_metrics)
    fold_metrics=pd.DataFrame(fold_rows)
    training_cov=pd.DataFrame(training_coverage)
    v0_identity = v0.rename(columns={"signal_date": "date"})
    data_ready=bool(len(validation)==len(v0_identity) and set(validation[["ticker","date","fold","signal_session_index"]].itertuples(index=False,name=None))==set(v0_identity[["ticker","date","fold","signal_session_index"]].itertuples(index=False,name=None)) and (fold_metrics.eligible_signal_sessions>=80).all() and (fold_metrics.validation_rows>=30).all() and (training_cov.coverage_ratio>=.90).all())
    gate=evaluate_survivor_gate(fold_metrics,data_ready)

    decile_rows=[]
    for fold in REQUIRED_FOLDS:
        for date,g in validation.loc[validation.fold.eq(fold)].groupby("date",sort=True):
            d=_deciles(g,"v1_predicted_payoff_atr")
            for decile,part in d.groupby("decile",sort=True):
                decile_rows.append({"fold":fold,"signal_date":date,"decile":int(decile),"rows":len(part),"mean_predicted_payoff_atr":part.v1_predicted_payoff_atr.mean(),"mean_realized_payoff_atr":part.payoff_atr_gross.mean(),"median_realized_payoff_atr":part.payoff_atr_gross.median(),"q25_realized_payoff_atr":part.payoff_atr_gross.quantile(.25),"q75_realized_payoff_atr":part.payoff_atr_gross.quantile(.75)})
    artifacts = {}
    feature_manifest={"candidate":"PAYOFF_HGB_O2_FEATURES_V1","feature_columns":FEATURES_36,"feature_order_sha256":FEATURE_HASH,"feature_source":"accepted V3-B 33 features + frozen O2 geometry","o2_score_in_features":False}
    _write_json(output_dir/"preflight_contract.json", {"started_at_utc":started,"cutoff":"2026-07-31","provider_calls":False,"fresh_forward_outcomes_accessed":False,"forward_outcome_access_marker_written":False,"o2_rescored":False,"candidate_count":1})
    _write_json(output_dir/"parent_identity.json", {"o2_manifest_sha256":config["o2_manifest_sha256"],"o2_predictions_sha256":config["o2_predictions_sha256"],"v0_validation_rows":len(v0),"v0_validation_key_sha256":config["v0_validation_key_sha256"],"v3_b_training_table_sha256":config["v3_b_training_table_sha256"]})
    _write_json(output_dir/"feature_manifest.json",feature_manifest)
    _write_json(output_dir/"model_contract.json",MODEL_CONTRACT)
    _write_json(output_dir/"fold_definitions.json",folds)
    ledger.to_csv(output_dir/"training_exclusion_reasons.csv",index=False)
    training_cov.to_csv(output_dir/"training_payoff_coverage.csv",index=False)
    pd.DataFrame(fold_rows).to_csv(output_dir/"fold_training_summary.csv",index=False)
    validation[["ticker","date","signal_session_index","fold","score","v1_predicted_payoff_atr","payoff_atr_gross","payoff_pct_gross","entry_date","exit_date"]].to_parquet(output_dir/"validation_predictions.parquet",index=False)
    session_df.to_csv(output_dir/"session_metrics.csv",index=False)
    fold_metrics.to_csv(output_dir/"fold_metrics.csv",index=False)
    pd.DataFrame(decile_rows).to_csv(output_dir/"predicted_payoff_decile_summary.csv",index=False)
    calibration = pd.DataFrame({"metric":["pooled_prediction_realized_spearman","pooled_prediction_mean","pooled_realized_mean"],"value":[_spearman(validation.v1_predicted_payoff_atr,validation.payoff_atr_gross),validation.v1_predicted_payoff_atr.mean(),validation.payoff_atr_gross.mean()]})
    calibration.to_csv(output_dir/"calibration_diagnostics.csv",index=False)
    _write_json(output_dir/"aggregate_metrics.json",gate)
    _write_json(output_dir/"survivor_decision.json",{**gate,"candidate":"PAYOFF_HGB_O2_FEATURES_V1","runtime_flags":{"fresh_forward_outcomes_accessed":False,"forward_outcome_access_marker_written":False,"provider_calls":False,"o2_model_modified":False,"o2_rescored":False,"hyperparameter_search":False,"candidate_count":1}})
    artifact_names=[p.name for p in output_dir.iterdir() if p.is_file() and p.name not in {"artifact_manifest.json"}]
    for name in artifact_names: artifacts[name]=sha256_file(output_dir/name)
    _write_json(output_dir/"artifact_manifest.json",{"status":gate["verdict"],"candidate":"PAYOFF_HGB_O2_FEATURES_V1","created_at_utc":datetime.now(timezone.utc).isoformat(),"rows":{"v0_validation":len(v0),"validation_predictions":len(validation),"resolved_training":int(fold_metrics.train_rows.sum())},"feature_order_sha256":FEATURE_HASH,"model_sha256":model_hashes,"artifacts_sha256":artifacts,"runtime_flags":{"fresh_forward_outcomes_accessed":False,"forward_outcome_access_marker_written":False,"provider_calls":False,"o2_model_modified":False,"o2_rescored":False,"hyperparameter_search":False,"candidate_count":1}})
    return {"verdict":gate["verdict"],"gate":gate,"fold_metrics":fold_metrics,"artifact_manifest_sha256":sha256_file(output_dir/"artifact_manifest.json"),"validation_rows":len(validation),"resolved_training_rows":int(fold_metrics.train_rows.sum())}


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--external-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args=parser.parse_args()
    config=_default_config(args.external_root)
    result=run_experiment(config,args.output_dir)
    print(json.dumps({"verdict":result["verdict"],"gate":result["gate"],"validation_rows":result["validation_rows"],"resolved_training_rows":result["resolved_training_rows"],"artifact_manifest_sha256":result["artifact_manifest_sha256"]},indent=2,default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
