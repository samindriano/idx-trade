"""Outcome-blind O2.1 sealed shadow model and forward artifact lane.

This module consumes only already-certified artifacts.  It deliberately stays
outside ``FROZEN_MODELS`` and the O2 counter: the shadow is a diagnostic
archive, not an independently counted model lane.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from .forward_ohlcv import SESSION_OHLCV_COLUMNS, validate_ohlcv_against_model_input
from .provenance import sha256_file, write_manifest_atomic
from .research_v2_features import V2_FULL_FEATURE_COLUMNS
from .research_v2_models import pointwise_raw_score
from .research_v3_structure_lite import STRUCTURE_LITE_FEATURE_COLUMNS
from .storage import write_parquet_atomic


SHADOW_MODEL_ID = "O2.1-FLAT-RANGE-SEALED-SHADOW-V1"
SHADOW_GENERATION = "O2.1-SHADOW"
SHADOW_ROOT_RELATIVE = "ohlcv_o2_1_sealed_shadow_v1_20260812"
SHADOW_MODEL_FILENAME = "o2_1_sealed_shadow_model.joblib"
SHADOW_MODEL_MANIFEST_FILENAME = "model_manifest.json"
SHADOW_ARTIFACT_MANIFEST_FILENAME = "artifact_manifest.json"
SHADOW_FEATURE_MANIFEST_FILENAME = "feature_manifest.json"
SHADOW_SUPPORT_MANIFEST_FILENAME = "training_support_manifest.json"
SHADOW_RUN_ROOT = "shadow_runs/o2_1_flat_range"

V3_FEATURE_COLUMNS = (*V2_FULL_FEATURE_COLUMNS, *STRUCTURE_LITE_FEATURE_COLUMNS)
O21_GEOMETRY_FEATURES = ("open_position_o21", "open_to_high", "open_to_low", "flat_range")
O21_FEATURE_COLUMNS = (*V3_FEATURE_COLUMNS, *O21_GEOMETRY_FEATURES)
V3_FEATURE_ORDER_SHA256 = "100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e"
O21_FEATURE_ORDER_SHA256 = "f0259e82240f3db76bab8929669082a422e124c8cb37a08cd94c6cff9220b3b3"
TRAINING_SUPPORT_SHA256 = "8c6429253d84d1e355c536c0c4b715f00d20ae0344c304aa2d7a218b323c596d"
EXPECTED_SUPPORT_ROWS = 280_044
EXPECTED_FLAT_ROWS = 1_876
EXPECTED_COVERAGE_SHA256 = "d9b2da0b1831b8fe087fe8ee9093e6ce7f649dd0c6c3f6f378cebe23e5694242"
EXPECTED_TRAINING_TABLE_SHA256 = "5893c9f2872aae0f33acd4104d82ee8c1d4474aae7d54e9d01879724b86dffbe"
EXPECTED_TRAINING_MANIFEST_SHA256 = "4e84ce02c6ee856c0f260dd6099b2a479723c53da82131ae669e0bf7e4d384f9"
EXPECTED_EXPANDED_SUPPORT_SHA256 = "af29b93964d0b27deb830e914d33d8a7db9a38f85d1cbfba74d3095038a18fdc"
EXPECTED_OPEN_PROVENANCE_SHA256 = "90deaad64ff3330921859eb222df556794c345bb3d440df89edab8ef6d342687"

HGB_PARAMS = {
    "learning_rate": 0.05,
    "max_iter": 200,
    "max_leaf_nodes": 31,
    "l2_regularization": 1.0,
    "random_state": 42,
}


def _feature_order_hash(columns: Sequence[str]) -> str:
    payload = json.dumps(list(columns), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _normal_date(values: object) -> pd.Series:
    dates = pd.to_datetime(values, errors="coerce")
    if not isinstance(dates, pd.Series):
        dates = pd.Series(dates)
    if getattr(dates.dt, "tz", None) is not None:
        dates = dates.dt.tz_localize(None)
    return dates.dt.normalize()


def _stable_key_hash(frame: pd.DataFrame) -> str:
    keys = frame[["ticker", "date", "signal_session_index"]].copy()
    keys["ticker"] = keys["ticker"].astype(str)
    keys["date"] = _normal_date(keys["date"]).dt.strftime("%Y-%m-%d")
    keys["signal_session_index"] = pd.to_numeric(keys["signal_session_index"], errors="raise").astype(int)
    lines = keys.sort_values(["ticker", "date", "signal_session_index"], kind="mergesort").astype(str).agg("|".join, axis=1)
    return hashlib.sha256(("\n".join(lines.tolist()) + "\n").encode("utf-8")).hexdigest()


def _verify_file(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"{label} missing: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"{label} SHA-256 mismatch: expected {expected}, got {actual}")
    return actual


def _as_bool(values: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(values):
        return values.fillna(False)
    return values.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def encode_o21_geometry(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int | float]]:
    """Encode flat bars as (0.5, 0, 0, 1), without changing raw OHLCV."""

    required = {"open", "high", "low"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"missing OHLC columns: {sorted(missing)}")
    values = frame[["open", "high", "low"]].apply(pd.to_numeric, errors="coerce")
    numeric = values.to_numpy(dtype=float)
    if not np.isfinite(numeric).all():
        raise ValueError("O2.1 geometry requires finite Open/High/Low")
    open_values, high_values, low_values = (values[column].to_numpy(dtype=float) for column in ("open", "high", "low"))
    if (numeric <= 0).any():
        raise ValueError("O2.1 geometry requires positive Open/High/Low")
    if (low_values > open_values).any() or (open_values > high_values).any():
        raise ValueError("O2.1 geometry violates low <= open <= high")
    flat = (open_values == high_values) & (high_values == low_values)
    denominator = high_values - low_values
    nonflat = ~flat
    position = np.empty(len(frame), dtype=float)
    to_high = np.empty(len(frame), dtype=float)
    to_low = np.empty(len(frame), dtype=float)
    position[flat], to_high[flat], to_low[flat] = 0.5, 0.0, 0.0
    position[nonflat] = (open_values[nonflat] - low_values[nonflat]) / denominator[nonflat]
    to_high[nonflat] = high_values[nonflat] / open_values[nonflat] - 1.0
    to_low[nonflat] = low_values[nonflat] / open_values[nonflat] - 1.0
    geometry = pd.DataFrame(
        {
            "open_position_o21": position,
            "open_to_high": to_high,
            "open_to_low": to_low,
            "flat_range": flat.astype(int),
        },
        index=frame.index,
    )
    if not np.isfinite(geometry.to_numpy(dtype=float)).all():
        raise ValueError("O2.1 geometry produced non-finite features")
    return geometry, {"flat_rows": int(flat.sum()), "nonflat_rows": int(nonflat.sum()), "total_rows": int(len(frame))}


def o21_hgb_pipeline(feature_columns: Sequence[str] = O21_FEATURE_COLUMNS) -> Pipeline:
    columns = tuple(feature_columns)
    if columns not in (V3_FEATURE_COLUMNS, O21_FEATURE_COLUMNS):
        raise ValueError("unknown O2.1 feature order")
    numeric = Pipeline(
        [("impute", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True))]
    )
    preprocess = ColumnTransformer([("numeric", numeric, list(columns))], remainder="drop")
    return Pipeline([("preprocess", preprocess), ("model", HistGradientBoostingClassifier(**HGB_PARAMS))])


def _source_paths(runtime_root: Path) -> dict[str, Path]:
    source_root = runtime_root / "open_research_coverage_gate_v1_20260812"
    return {
        "coverage": source_root / "v3_b_open_feature_readiness_rows.csv",
        "training_table": runtime_root / "ranking_v3_b_final_refit_20260810_001/ranking_v3_b_structure_lite_final_training_table.parquet",
        "training_manifest": runtime_root / "ranking_v3_b_final_refit_20260810_001/ranking_v3_b_structure_lite_final_manifest.json",
        "expanded_support": runtime_root / "ohlcv_o2_1_flat_range_v1_20260812/expanded_support_rows.csv",
        "open_provenance": runtime_root / "open_backfill_zapi_tradingview_derivative_v1_20260811/execution_open_candidate_provenance_yahoo_tradingview.parquet",
    }


def _load_accepted_support(runtime_root: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    paths = _source_paths(runtime_root)
    _verify_file(paths["coverage"], EXPECTED_COVERAGE_SHA256, "accepted Open coverage")
    _verify_file(paths["training_table"], EXPECTED_TRAINING_TABLE_SHA256, "V3-B training table")
    _verify_file(paths["training_manifest"], EXPECTED_TRAINING_MANIFEST_SHA256, "V3-B training manifest")
    _verify_file(paths["expanded_support"], EXPECTED_EXPANDED_SUPPORT_SHA256, "accepted expanded support")
    _verify_file(paths["open_provenance"], EXPECTED_OPEN_PROVENANCE_SHA256, "accepted Open provenance")

    training_manifest = json.loads(paths["training_manifest"].read_text(encoding="utf-8"))
    if tuple(training_manifest.get("feature_columns", ())) != V3_FEATURE_COLUMNS:
        raise RuntimeError("V3-B parent feature order differs from frozen O2.1 prefix")
    if training_manifest.get("feature_order_sha256") != V3_FEATURE_ORDER_SHA256:
        raise RuntimeError("V3-B parent feature-order SHA differs from frozen O2.1 prefix")
    if training_manifest.get("fresh_forward_outcomes_accessed") is not False or training_manifest.get("forward_outcome_access_marker_written") is not False:
        raise RuntimeError("V3-B parent manifest is not outcome-blind")

    training = pd.read_parquet(paths["training_table"])
    coverage = pd.read_csv(paths["coverage"], parse_dates=["date"])
    required_coverage = {"ticker", "date", "signal_session_index", "open", "high", "low", "open_known", "open_feature_ready", "open_position", "open_to_high", "open_to_low"}
    missing = required_coverage - set(coverage.columns)
    if missing:
        raise RuntimeError(f"accepted coverage missing {sorted(missing)}")
    for frame in (training, coverage):
        frame["ticker"] = frame["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
        frame["date"] = _normal_date(frame["date"])
        if frame.duplicated(["ticker", "date"]).any():
            raise RuntimeError("accepted support source has duplicate ticker/date keys")
    merged = training.merge(coverage, on=["ticker", "date"], how="inner", suffixes=("", "_coverage"), validate="one_to_one")
    if len(merged) != len(training):
        raise RuntimeError("V3-B training/coverage join lost rows")
    if not (merged["signal_session_index"].astype(int) == merged["signal_session_index_coverage"].astype(int)).all():
        raise RuntimeError("training/coverage session identities disagree")
    merged = merged.drop(columns=["signal_session_index_coverage"])
    merged = merged.rename(
        columns={
            "open_position": "coverage_open_position",
            "open_to_high": "coverage_open_to_high",
            "open_to_low": "coverage_open_to_low",
        }
    )
    positive = merged[["open", "high", "low"]].apply(pd.to_numeric, errors="coerce")
    basic = (
        positive.notna().all(axis=1)
        & np.isfinite(positive.to_numpy(dtype=float)).all(axis=1)
        & (positive > 0).all(axis=1)
        & _as_bool(merged["open_known"])
        & (merged["low"] <= merged["open"])
        & (merged["open"] <= merged["high"])
        & merged["binary_target"].isin([0, 1])
    )
    support = merged.loc[basic].copy()
    geometry, geometry_summary = encode_o21_geometry(support)
    support = pd.concat([support.reset_index(drop=True), geometry.reset_index(drop=True)], axis=1)
    nonflat = support["flat_range"].eq(0)
    if not _as_bool(support.loc[nonflat, "open_feature_ready"]).all():
        raise RuntimeError("non-flat accepted rows are not Open-feature ready")
    if _as_bool(support.loc[~nonflat, "open_feature_ready"]).any():
        raise RuntimeError("flat accepted rows unexpectedly have common-support Open readiness")
    if len(support) != EXPECTED_SUPPORT_ROWS or int(support["flat_range"].sum()) != EXPECTED_FLAT_ROWS:
        raise RuntimeError(f"accepted support count mismatch: rows={len(support)} flat={int(support['flat_range'].sum())}")
    support_sha = _stable_key_hash(support)
    if support_sha != TRAINING_SUPPORT_SHA256:
        raise RuntimeError(f"accepted support key SHA mismatch: expected {TRAINING_SUPPORT_SHA256}, got {support_sha}")

    expanded = pd.read_csv(paths["expanded_support"], parse_dates=["date"])
    expanded["ticker"] = expanded["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    expanded["date"] = _normal_date(expanded["date"])
    if _stable_key_hash(expanded) != TRAINING_SUPPORT_SHA256:
        raise RuntimeError("persisted expanded-support key SHA differs from accepted support")
    comparison = support[["ticker", "date", "signal_session_index", "flat_range"]].merge(
        expanded[["ticker", "date", "signal_session_index", "flat_range"]],
        on=["ticker", "date", "signal_session_index"], how="outer", suffixes=("_rebuilt", "_persisted"), indicator=True,
    )
    if not (comparison["_merge"].eq("both").all() and (comparison["flat_range_rebuilt"] == comparison["flat_range_persisted"]).all()):
        raise RuntimeError("rebuilt support does not match persisted expanded support")

    provenance = pd.read_parquet(paths["open_provenance"], columns=["ticker", "date", "open_source", "source_cache_ref", "source_raw_sha256"])
    provenance["ticker"] = provenance["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    provenance["date"] = _normal_date(provenance["date"])
    if provenance.duplicated(["ticker", "date"]).any():
        raise RuntimeError("accepted Open provenance has duplicate keys")
    provenance_check = support[["ticker", "date"]].merge(provenance, on=["ticker", "date"], how="left", validate="one_to_one")
    if provenance_check["open_source"].isna().any() or (
        provenance_check["open_source"].ne("IMMUTABLE_PANEL")
        & provenance_check["source_cache_ref"].isna()
        & provenance_check["source_raw_sha256"].isna()
    ).any():
        raise RuntimeError("accepted support has incomplete Open provenance")

    support = support.sort_values(["signal_session_index", "ticker"], kind="mergesort").reset_index(drop=True)
    return support, {
        "rows": int(len(support)),
        "tickers": int(support["ticker"].nunique()),
        "session_min": int(support["signal_session_index"].min()),
        "session_max": int(support["signal_session_index"].max()),
        "date_min": support["date"].min().date().isoformat(),
        "date_max": support["date"].max().date().isoformat(),
        "flat_rows": int(support["flat_range"].sum()),
        "flat_share": float(support["flat_range"].mean()),
        "support_sha256": TRAINING_SUPPORT_SHA256,
        "geometry_summary": geometry_summary,
        "fresh_forward_outcomes_accessed": False,
        "forward_outcome_access_marker_written": False,
        "provider_calls": False,
    }


def _shadow_root(runtime_root: Path) -> Path:
    return runtime_root / SHADOW_ROOT_RELATIVE


def _frozen_paths(runtime_root: Path) -> dict[str, Path]:
    root = _shadow_root(runtime_root)
    return {
        "root": root,
        "model": root / SHADOW_MODEL_FILENAME,
        "model_manifest": root / SHADOW_MODEL_MANIFEST_FILENAME,
        "artifact_manifest": root / SHADOW_ARTIFACT_MANIFEST_FILENAME,
        "feature_manifest": root / SHADOW_FEATURE_MANIFEST_FILENAME,
        "support_manifest": root / SHADOW_SUPPORT_MANIFEST_FILENAME,
    }


def _load_frozen_shadow(runtime_root: Path) -> dict[str, Any]:
    paths = _frozen_paths(runtime_root)
    if not paths["model"].exists() and not paths["model_manifest"].exists():
        raise FileNotFoundError("O2.1 sealed shadow model is not frozen")
    if not all(paths[key].exists() for key in ("model", "model_manifest", "artifact_manifest", "feature_manifest", "support_manifest")):
        raise RuntimeError("O2.1 sealed shadow artifact bundle is incomplete")
    manifest = json.loads(paths["model_manifest"].read_text(encoding="utf-8"))
    if manifest.get("model_id") != SHADOW_MODEL_ID or manifest.get("sealed_shadow") is not True or manifest.get("promotion_eligible") is not False:
        raise RuntimeError("O2.1 shadow model identity or eligibility contract is invalid")
    if manifest.get("feature_order_sha256") != O21_FEATURE_ORDER_SHA256 or tuple(manifest.get("feature_columns", ())) != O21_FEATURE_COLUMNS:
        raise RuntimeError("O2.1 shadow feature-order contract is invalid")
    if manifest.get("training_support_sha256") != TRAINING_SUPPORT_SHA256:
        raise RuntimeError("O2.1 shadow training-support fingerprint is invalid")
    if manifest.get("fresh_forward_outcomes_accessed") is not False or manifest.get("forward_outcome_access_marker_written") is not False:
        raise RuntimeError("O2.1 shadow model manifest is not outcome-blind")
    actual_model_sha = sha256_file(paths["model"])
    if actual_model_sha != manifest.get("model_sha256"):
        raise RuntimeError(f"O2.1 shadow model SHA mismatch: expected {manifest.get('model_sha256')}, got {actual_model_sha}")
    inventory = json.loads(paths["artifact_manifest"].read_text(encoding="utf-8"))
    for name, expected in inventory.get("artifact_sha256", {}).items():
        artifact = paths["root"] / str(name)
        if not artifact.exists() or sha256_file(artifact) != expected:
            raise RuntimeError(f"O2.1 shadow artifact hash mismatch: {name}")
    return {"paths": paths, "manifest": manifest, "inventory": inventory}


def freeze_o21_shadow_model(runtime_root: str | Path) -> dict[str, Any]:
    """Fit exactly one deterministic model from the accepted support bundle."""

    root = Path(runtime_root)
    existing = _frozen_paths(root)
    if any(path.exists() for path in existing.values()):
        return _load_frozen_shadow(root)["manifest"]
    support, support_contract = _load_accepted_support(root)
    if _feature_order_hash(O21_FEATURE_COLUMNS) != O21_FEATURE_ORDER_SHA256:
        raise RuntimeError("O2.1 feature-order SHA constant is invalid")
    model = o21_hgb_pipeline(O21_FEATURE_COLUMNS)
    model.fit(support.loc[:, list(O21_FEATURE_COLUMNS)], support["binary_target"].astype(int).to_numpy())
    paths = _frozen_paths(root)
    paths["root"].mkdir(parents=True, exist_ok=True)
    temporary_model = paths["model"].with_suffix(paths["model"].suffix + ".tmp")
    joblib.dump(model, temporary_model)
    temporary_model.replace(paths["model"])
    model_sha = sha256_file(paths["model"])

    feature_manifest = {
        "schema": "idx-trade/o2-1-sealed-shadow-feature-contract-v1",
        "model_id": SHADOW_MODEL_ID,
        "feature_columns": list(O21_FEATURE_COLUMNS),
        "feature_order_sha256": O21_FEATURE_ORDER_SHA256,
        "v3_b_feature_order_sha256": V3_FEATURE_ORDER_SHA256,
        "hgb_parameters": HGB_PARAMS,
        "flat_encoding": {"open_position_o21": 0.5, "open_to_high": 0.0, "open_to_low": 0.0, "flat_range": 1},
        "outcome_blind": True,
    }
    write_manifest_atomic(paths["feature_manifest"], feature_manifest)
    support_manifest = {
        "schema": "idx-trade/o2-1-sealed-shadow-training-support-v1",
        "support_sha256": TRAINING_SUPPORT_SHA256,
        "training_support_sha256": TRAINING_SUPPORT_SHA256,
        "support_contract": support_contract,
        "source_artifacts": {key: {"path": str(path), "sha256": sha256_file(path)} for key, path in _source_paths(root).items()},
        "fresh_forward_outcomes_accessed": False,
        "forward_outcome_access_marker_written": False,
        "provider_calls": False,
    }
    write_manifest_atomic(paths["support_manifest"], support_manifest)
    model_manifest = {
        "schema": "idx-trade/o2-1-sealed-shadow-model-v1",
        "status": "SEALED_SHADOW_READY",
        "model_id": SHADOW_MODEL_ID,
        "generation": SHADOW_GENERATION,
        "model_sha256": model_sha,
        "feature_order_sha256": O21_FEATURE_ORDER_SHA256,
        "v3_b_feature_order_sha256": V3_FEATURE_ORDER_SHA256,
        "feature_columns": list(O21_FEATURE_COLUMNS),
        "training_support_sha256": TRAINING_SUPPORT_SHA256,
        "training_support_rows": int(len(support)),
        "training_support_flat_rows": int(support["flat_range"].sum()),
        "hgb_parameters": HGB_PARAMS,
        "feature_manifest": paths["feature_manifest"].name,
        "training_support_manifest": paths["support_manifest"].name,
        "feature_manifest_sha256": sha256_file(paths["feature_manifest"]),
        "training_support_manifest_sha256": sha256_file(paths["support_manifest"]),
        "sealed_shadow": True,
        "promotion_eligible": False,
        "independent_official_counter": False,
        "historical_verdict": "O2_1_NO_SURVIVOR",
        "fresh_forward_outcomes_accessed": False,
        "forward_outcome_access_marker_written": False,
        "provider_calls": False,
    }
    write_manifest_atomic(paths["model_manifest"], model_manifest)
    inventory = {
        "schema": "idx-trade/o2-1-sealed-shadow-artifact-manifest-v1",
        "model_id": SHADOW_MODEL_ID,
        "artifact_sha256": {
            paths["model"].name: model_sha,
            paths["feature_manifest"].name: sha256_file(paths["feature_manifest"]),
            paths["support_manifest"].name: sha256_file(paths["support_manifest"]),
            paths["model_manifest"].name: sha256_file(paths["model_manifest"]),
        },
        "sealed_shadow": True,
        "promotion_eligible": False,
        "fresh_forward_outcomes_accessed": False,
        "forward_outcome_access_marker_written": False,
    }
    write_manifest_atomic(paths["artifact_manifest"], inventory)
    _load_frozen_shadow(root)
    return model_manifest


def _existing_o2_coverage(paths: Any, session_key: str) -> dict[str, Any] | None:
    session_root = paths.monitor_root / "model_runs" / session_key
    candidates = list(session_root.glob("*o2*/*score_artifact.parquet"))
    if not candidates:
        return None
    frame = pd.read_parquet(candidates[0])
    return {"scored_rows": int(frame["score"].notna().sum()), "rows": int(len(frame))}


def _shadow_session_paths(paths: Any, session_key: str) -> dict[str, Path]:
    root = paths.monitor_root / SHADOW_RUN_ROOT / session_key
    return {"root": root, "artifact": root / "score_artifact.parquet", "manifest": root / "manifest.json", "diagnostics": root / "coverage_diagnostics.json"}


def score_o21_shadow_session(paths: Any, session_key: str, v3_features: pd.DataFrame, metadata: dict[str, Any]) -> dict[str, Any]:
    """Score one certified session, without creating a model-run DB row."""

    frozen = _load_frozen_shadow(Path(paths.runtime_root))
    frozen_manifest = frozen["manifest"]
    output_paths = _shadow_session_paths(paths, session_key)
    if output_paths["artifact"].exists() or output_paths["manifest"].exists():
        if not (output_paths["artifact"].exists() and output_paths["manifest"].exists()):
            raise RuntimeError("O2.1 shadow session artifact bundle is incomplete")
        prior = json.loads(output_paths["manifest"].read_text(encoding="utf-8"))
        if sha256_file(output_paths["artifact"]) != prior.get("score_artifact_sha256"):
            raise RuntimeError("O2.1 shadow session artifact hash mismatch")
        return prior

    ohlcv_path = paths.session_root / session_key / "session_ohlcv.parquet"
    if not ohlcv_path.is_file():
        raise FileNotFoundError(f"certified session OHLCV missing: {ohlcv_path}")
    ohlcv = pd.read_parquet(ohlcv_path)
    missing = set(SESSION_OHLCV_COLUMNS) - set(ohlcv.columns)
    if missing:
        raise RuntimeError(f"certified session OHLCV missing columns: {sorted(missing)}")
    model_input = pd.read_parquet(Path(metadata["snapshot_path"]))
    validate_ohlcv_against_model_input(ohlcv, model_input, session_key)
    geometry, geometry_summary = encode_o21_geometry(ohlcv)
    geometry["ticker"] = ohlcv["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip().to_numpy()
    geometry["date"] = _normal_date(session_key).iloc[0]
    source = v3_features.copy()
    source["ticker"] = source["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    source["date"] = _normal_date(source["date"])
    source = source.merge(geometry, on=["ticker", "date"], how="left", validate="one_to_one")
    if len(source) != len(v3_features) or source[list(O21_GEOMETRY_FEATURES)].isna().any().any():
        raise RuntimeError("O2.1 geometry did not align one-to-one with V3-B features")
    scores = pointwise_raw_score(joblib.load(frozen["paths"]["model"]), source.loc[:, list(O21_FEATURE_COLUMNS)])
    if not np.isfinite(scores).all():
        raise RuntimeError("O2.1 shadow produced non-finite score values")
    output = source[["ticker", "date", "flat_range"]].rename(columns={"date": "session_date"}).copy()
    output["score"] = scores
    output = output.sort_values(["score", "ticker"], ascending=[False, True], kind="mergesort").reset_index(drop=True)
    output["rank"] = np.arange(1, len(output) + 1, dtype=int)
    output["score_percentile"] = 1.0 - ((output["rank"] - 1.0) / max(len(output), 1))
    output["model_id"] = SHADOW_MODEL_ID
    output["generation"] = SHADOW_GENERATION
    output["model_sha256"] = frozen_manifest["model_sha256"]
    output["feature_order_sha256"] = O21_FEATURE_ORDER_SHA256
    output_paths["root"].mkdir(parents=True, exist_ok=True)
    write_parquet_atomic(output, output_paths["artifact"])
    artifact_sha = sha256_file(output_paths["artifact"])
    o2 = _existing_o2_coverage(paths, session_key)
    diagnostic = {
        "session_date": session_key,
        "shadow_model_id": SHADOW_MODEL_ID,
        "shadow_sessions_aligned": 1,
        "shadow_score_rows": int(len(output)),
        "shadow_scored_rows": int(output["score"].notna().sum()),
        "shadow_coverage": f"{int(output['score'].notna().sum())}/{len(output)}",
        "flat_range_included": int(output["flat_range"].sum()),
        "flat_share": float(output["flat_range"].mean()) if len(output) else 0.0,
        "o2_score_rows": None if o2 is None else o2["rows"],
        "o2_scored_rows": None if o2 is None else o2["scored_rows"],
        "o2_coverage": None if o2 is None else f"{o2['scored_rows']}/{o2['rows']}",
        "geometry_summary": geometry_summary,
        "source_session_ohlcv_path": str(ohlcv_path),
        "source_session_ohlcv_sha256": sha256_file(ohlcv_path),
        "data_snapshot_path": metadata["snapshot_path"],
        "data_snapshot_sha256": metadata["snapshot_sha256"],
        "score_artifact_path": str(output_paths["artifact"]),
        "score_artifact_sha256": artifact_sha,
        "model_sha256": frozen_manifest["model_sha256"],
        "feature_order_sha256": O21_FEATURE_ORDER_SHA256,
        "sealed_shadow": True,
        "promotion_eligible": False,
        "independent_official_counter": False,
        "fresh_forward_outcomes_accessed": False,
        "forward_outcome_access_marker_written": False,
    }
    write_manifest_atomic(output_paths["manifest"], diagnostic)
    write_manifest_atomic(output_paths["diagnostics"], diagnostic)
    return diagnostic


def align_o21_shadow_sessions(runtime_root: str | Path, session_dates: Iterable[object] | None = None) -> dict[str, Any]:
    """Align existing DATA_READY sessions using stored certified artifacts only."""

    from .forward_model_runtime import _build_features, _connection, _paths

    paths = _paths(runtime_root)
    frozen = _load_frozen_shadow(Path(paths.runtime_root))
    requested = None if session_dates is None else {_normal_date(value).iloc[0].date().isoformat() for value in session_dates}
    connection = _connection(paths)
    try:
        sessions = [str(row["session_date"]) for row in connection.execute("SELECT session_date FROM session_snapshots WHERE state='DATA_READY' ORDER BY session_date").fetchall()]
    finally:
        connection.close()
    if requested is not None:
        sessions = [session for session in sessions if session in requested]
    results = []
    for session_key in sessions:
        _, v3_features, metadata = _build_features(paths, session_key)
        results.append(score_o21_shadow_session(paths, session_key, v3_features, metadata))
    return {"status": "O2_1_SHADOW_ALIGNED", "model_sha256": frozen["manifest"]["model_sha256"], "sessions": results, "outcome_access": "LOCKED"}


def shadow_status(runtime_root: str | Path) -> dict[str, Any]:
    root = Path(runtime_root)
    try:
        frozen = _load_frozen_shadow(root)
    except FileNotFoundError:
        return {"status": "NOT_FROZEN", "model_id": SHADOW_MODEL_ID, "sealed_shadow": True, "promotion_eligible": False, "independent_official_counter": False}
    # Shadow score artifacts live under the existing forward-monitoring store,
    # alongside O2/V3-B/V2 artifacts.  The sealed model bundle itself lives at
    # the runtime root, so deriving this from the bundle parent would skip the
    # `forward_monitoring` segment and make valid runs invisible to status.
    from .forward_monitoring import runtime_paths

    run_root = runtime_paths(root).monitor_root / SHADOW_RUN_ROOT
    manifests = sorted(run_root.glob("*/manifest.json")) if run_root.exists() else []
    valid = []
    for path in manifests:
        payload = json.loads(path.read_text(encoding="utf-8"))
        artifact = Path(payload["score_artifact_path"])
        if artifact.exists() and sha256_file(artifact) == payload.get("score_artifact_sha256"):
            valid.append(payload)
    latest = sorted(valid, key=lambda item: str(item.get("session_date", "")))[-1] if valid else None
    return {
        "status": "SEALED",
        "model_id": SHADOW_MODEL_ID,
        "generation": SHADOW_GENERATION,
        "model_sha256": frozen["manifest"]["model_sha256"],
        "feature_order_sha256": O21_FEATURE_ORDER_SHA256,
        "training_support_sha256": TRAINING_SUPPORT_SHA256,
        "feature_count": len(O21_FEATURE_COLUMNS),
        "shadow_sessions_aligned": len(valid),
        "shadow_target_sessions": 100,
        "latest_session_date": None if latest is None else latest.get("session_date"),
        "o2_coverage": None if latest is None else latest.get("o2_coverage"),
        "shadow_coverage": None if latest is None else latest.get("shadow_coverage"),
        "flat_range_included": None if latest is None else latest.get("flat_range_included"),
        "flat_share": None if latest is None else latest.get("flat_share"),
        "sealed_shadow": True,
        "promotion_eligible": False,
        "independent_official_counter": False,
        "outcome_blind": True,
        "fresh_forward_outcomes_accessed": False,
        "forward_outcome_access_marker_written": False,
        "artifact_manifest_path": str(frozen["paths"]["artifact_manifest"]),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="IDX Trade O2.1 sealed shadow runtime")
    parser.add_argument("command", choices=("freeze", "align", "freeze-and-align", "status"))
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--date", default=None)
    args = parser.parse_args()
    if args.command == "freeze":
        result = freeze_o21_shadow_model(args.runtime_root)
    elif args.command == "status":
        result = shadow_status(args.runtime_root)
    elif args.command == "align":
        result = align_o21_shadow_sessions(args.runtime_root, [args.date] if args.date else None)
    else:
        freeze_o21_shadow_model(args.runtime_root)
        result = align_o21_shadow_sessions(args.runtime_root, [args.date] if args.date else None)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
