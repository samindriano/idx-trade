"""Frozen Open research-grade coverage gate.

This module is deliberately read-only with respect to the certified panel.  It
copies the already accepted Yahoo+TradingView derivative, applies exactly one
reviewed SMBR candidate in memory, and evaluates Open availability on the
materialized V3-B Structure-Lite final-refit population.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


BASE_ROOT = Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v")
PANEL_PATH = BASE_ROOT / "research_feasibility_1260_20260809" / "unknown_state_diagnostic_1260_20260809" / "model_safe_signal_research_panel_1260.parquet"
DERIVATIVE_ROOT = BASE_ROOT / "open_backfill_zapi_tradingview_derivative_v1_20260811"
DERIVATIVE_PANEL_PATH = DERIVATIVE_ROOT / "execution_open_candidate_panel_yahoo_tradingview.parquet"
DERIVATIVE_PROVENANCE_PATH = DERIVATIVE_ROOT / "execution_open_candidate_provenance_yahoo_tradingview.parquet"
SMBR_CANDIDATE_PATH = BASE_ROOT / "open_backfill_zapi_tradingview_identity_remediation_v1_20260812" / "tradingview_remediation_row_audit.csv"
FINAL_REFIT_ROOT = BASE_ROOT / "ranking_v3_b_final_refit_20260810_001"
FINAL_REFIT_TABLE_PATH = FINAL_REFIT_ROOT / "ranking_v3_b_structure_lite_final_training_table.parquet"
FINAL_REFIT_MANIFEST_PATH = FINAL_REFIT_ROOT / "ranking_v3_b_structure_lite_final_manifest.json"
RESIDUAL_PATH = BASE_ROOT / "open_backfill_yahoo_census_v1_20260810" / "residual_open_detail.csv"
TRADINGVIEW_CENSUS_PATH = BASE_ROOT / "open_backfill_zapi_tradingview_targeted_census_v1_20260811" / "tradingview_combined_row_audit.csv"
PARTITION_PATHS = {
    "V2F1-V2F4": BASE_ROOT / "ranking_v3_structure_lite_run_20260810_run1" / "ranking_v3_b_structure_lite_f1_f4_predictions.parquet",
    "V2F5-V2F6": BASE_ROOT / "ranking_v3_final_structure_lite_late_dev_run_20260810_001" / "ranking_v3_final_structure_lite_f5_f6_predictions.parquet",
}
OUTPUT_ROOT = BASE_ROOT / "open_research_coverage_gate_v1_20260812"

EXPECTED = {
    "panel": "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76",
    "derivative_panel": "a1dae0714971904b266a380be6bb96a2a4976068c9d60c54c8c43746826f7cab",
    "derivative_provenance": "90deaad64ff3330921859eb222df556794c345bb3d440df89edab8ef6d342687",
    "smbr_candidate_audit": "33b06259e663ab3ecae5be01514d495a071ef57f7628b061986cf88af9e0e7f5",
    "final_refit_table": "5893c9f2872aae0f33acd4104d82ee8c1d4474aae7d54e9d01879724b86dffbe",
    "final_refit_manifest": "4e84ce02c6ee856c0f260dd6099b2a479723c53da82131ae669e0bf7e4d384f9",
    "residual_detail": "26cd2319991aa5dc2fcce78d7f256f31fb1762b4510c0623fcd16fb87b66fd02",
}
V3_B_ARCHITECTURE = "V3-B-STRUCTURE-LITE-V1-CANDIDATE-005"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(value: object, path: Path) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    data = frame.copy()
    for column in data.columns:
        if pd.api.types.is_datetime64_any_dtype(data[column]):
            data[column] = data[column].dt.strftime("%Y-%m-%d")
    data.to_csv(path, index=False, lineterminator="\n")


def _normalise_dates(frame: pd.DataFrame, column: str = "date") -> pd.DataFrame:
    result = frame.copy()
    result[column] = pd.to_datetime(result[column], errors="coerce").dt.tz_localize(None).dt.normalize()
    if result[column].isna().any():
        raise ValueError(f"invalid dates in {column}")
    return result


def apply_smb_overlay(
    derivative: pd.DataFrame,
    derivative_provenance: pd.DataFrame,
    candidate_audit: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Apply exactly one accepted candidate without overwriting existing Open."""

    panel = _normalise_dates(derivative)
    provenance = _normalise_dates(derivative_provenance)
    candidate = _normalise_dates(candidate_audit)
    required = {"ticker", "date", "raw_open", "raw_high", "raw_low", "raw_close", "hlc_exact", "admission_status"}
    if not required.issubset(candidate.columns):
        raise ValueError(f"candidate audit missing: {sorted(required - set(candidate.columns))}")
    selected = candidate[(candidate["ticker"].astype(str).str.upper() == "SMBR") & candidate["date"].eq(pd.Timestamp("2023-03-14"))]
    if len(selected) != 1:
        raise ValueError(f"expected exactly one SMBR candidate, got {len(selected)}")
    row = selected.iloc[0]
    if not bool(row["hlc_exact"]) or str(row["admission_status"]) != "ADMISSIBLE_OPEN_EVIDENCE":
        raise ValueError("SMBR candidate does not satisfy the frozen admission gate")
    value = float(row["raw_open"])
    high, low, close = float(row["raw_high"]), float(row["raw_low"]), float(row["raw_close"])
    if not np.isfinite(value) or value <= 0 or not (low <= value <= high):
        raise ValueError("SMBR candidate Open is not positive and in range")

    key = (panel["ticker"].astype(str).str.upper().eq("SMBR")) & panel["date"].eq(pd.Timestamp("2023-03-14"))
    if int(key.sum()) != 1:
        raise ValueError("SMBR overlay key is not unique in derivative")
    if panel.loc[key, "open"].notna().any():
        raise ValueError("overlay would overwrite an existing non-null Open")
    if not np.isclose(float(panel.loc[key, "high"].iloc[0]), high) or not np.isclose(float(panel.loc[key, "low"].iloc[0]), low) or not np.isclose(float(panel.loc[key, "close"].iloc[0]), close):
        raise ValueError("SMBR candidate H/L/C does not match derivative panel")

    overlay = panel.copy()
    overlay.loc[key, "open"] = value
    if "open_available" in overlay:
        overlay.loc[key, "open_available"] = True
    if "open_evidence_status" in overlay:
        overlay.loc[key, "open_evidence_status"] = "OPEN_OPTIONAL_ZAPI_TRADINGVIEW_REMEDIATION"

    pkey = provenance["ticker"].astype(str).str.upper().eq("SMBR") & provenance["date"].eq(pd.Timestamp("2023-03-14"))
    if int(pkey.sum()) != 1:
        raise ValueError("SMBR provenance key is not unique")
    if "open_source" in provenance:
        provenance.loc[pkey, "open_source"] = "ZAPI_TRADINGVIEW_REMEDIATION"
    if "open_evidence_class" in provenance:
        provenance.loc[pkey, "open_evidence_class"] = "TV_RECOVERY_CANDIDATE"
    if "validation_status" in provenance:
        provenance.loc[pkey, "validation_status"] = "ACCEPTED_OVERLAY"
    if "tradingview_open" in provenance:
        provenance.loc[pkey, "tradingview_open"] = value
    if "tradingview_high" in provenance:
        provenance.loc[pkey, "tradingview_high"] = high
    if "tradingview_low" in provenance:
        provenance.loc[pkey, "tradingview_low"] = low
    if "tradingview_close" in provenance:
        provenance.loc[pkey, "tradingview_close"] = close
    metadata = {
        "ticker": "SMBR",
        "date": "2023-03-14",
        "open": value,
        "high": high,
        "low": low,
        "close": close,
        "source": "ZAPI_TRADINGVIEW_REMEDIATION",
        "admission": "exact certified H/L/C + positive/in-range Open",
        "existing_open_overwritten": False,
    }
    return overlay, provenance, metadata


def _coverage_summary(frame: pd.DataFrame, open_column: str = "open") -> pd.DataFrame:
    data = frame.copy()
    data["known_open"] = pd.to_numeric(data[open_column], errors="coerce").notna()
    grouped = data.groupby("date", as_index=False).agg(rows=("ticker", "size"), known=("known_open", "sum"))
    grouped["missing"] = grouped["rows"] - grouped["known"]
    grouped["coverage"] = grouped["known"] / grouped["rows"]
    return grouped.sort_values("date").reset_index(drop=True)


def _feature_readiness(eligible: pd.DataFrame, panel: pd.DataFrame, overlay: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    prices = _normalise_dates(panel[["ticker", "date", "high", "low", "close"]]).sort_values(["ticker", "date"])
    prices["prior_close"] = prices.groupby("ticker")["close"].shift(1)
    data = eligible[["ticker", "date", "signal_session_index"]].merge(prices, on=["ticker", "date"], how="left", validate="one_to_one")
    data = data.merge(overlay[["ticker", "date", "open"]], on=["ticker", "date"], how="left", validate="one_to_one")
    data["overnight_gap"] = data["open"] / data["prior_close"] - 1.0
    data["intraday_return"] = data["close"] / data["open"] - 1.0
    price_range = data["high"] - data["low"]
    data["open_position"] = ((data["open"] - data["low"]) / price_range).where(price_range > 0)
    data["open_to_high"] = data["high"] / data["open"] - 1.0
    data["open_to_low"] = data["low"] / data["open"] - 1.0
    features = ["overnight_gap", "intraday_return", "open_position", "open_to_high", "open_to_low"]
    data["open_feature_ready"] = data[features].apply(lambda column: np.isfinite(pd.to_numeric(column, errors="coerce")), axis=0).all(axis=1)
    data["open_known"] = data["open"].notna()
    return data, pd.DataFrame(
        [
            {"feature": feature, "rows": int(len(data)), "usable_rows": int(data[feature].notna().sum()), "usable_rate": float(data[feature].notna().mean())}
            for feature in features
        ]
        + [{"feature": "all_open_features_after_lag_and_range", "rows": int(len(data)), "usable_rows": int(data["open_feature_ready"].sum()), "usable_rate": float(data["open_feature_ready"].mean())}]
    )


def run_open_research_coverage_gate(*, output_dir: Path = OUTPUT_ROOT, code_commit: str = "") -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError(f"output directory must be new or empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "panel": PANEL_PATH,
        "derivative_panel": DERIVATIVE_PANEL_PATH,
        "derivative_provenance": DERIVATIVE_PROVENANCE_PATH,
        "smbr_candidate_audit": SMBR_CANDIDATE_PATH,
        "final_refit_table": FINAL_REFIT_TABLE_PATH,
        "final_refit_manifest": FINAL_REFIT_MANIFEST_PATH,
        "residual_detail": RESIDUAL_PATH,
        "tradingview_census": TRADINGVIEW_CENSUS_PATH,
        **{f"partition_{key}": value for key, value in PARTITION_PATHS.items()},
    }
    source_hashes = {name: sha256_file(path) for name, path in paths.items()}
    for name, expected in EXPECTED.items():
        if source_hashes[name] != expected:
            raise RuntimeError(f"{name} SHA mismatch: expected={expected} actual={source_hashes[name]}")

    final_manifest = json.loads(FINAL_REFIT_MANIFEST_PATH.read_text(encoding="utf-8"))
    if final_manifest.get("architecture") != V3_B_ARCHITECTURE or final_manifest.get("status") != "RANKING_V3_B_FINAL_REFIT_FROZEN":
        raise RuntimeError("final V3-B manifest identity/status mismatch")
    if final_manifest.get("fresh_forward_outcomes_accessed") or final_manifest.get("forward_outcome_access_marker_written"):
        raise RuntimeError("fresh-forward outcome boundary is not clean")

    panel = pd.read_parquet(PANEL_PATH)
    derivative = pd.read_parquet(DERIVATIVE_PANEL_PATH)
    derivative_provenance = pd.read_parquet(DERIVATIVE_PROVENANCE_PATH)
    candidate = pd.read_csv(SMBR_CANDIDATE_PATH)
    overlay, overlay_provenance, overlay_change = apply_smb_overlay(derivative, derivative_provenance, candidate)
    if int(panel["open"].isna().sum()) != 446843 or int(overlay["open"].isna().sum()) != 43800:
        raise RuntimeError("global Open counts do not match frozen accounting")

    eligible = _normalise_dates(pd.read_parquet(FINAL_REFIT_TABLE_PATH))
    if len(eligible) != 292633 or eligible["ticker"].nunique() != 737 or not eligible["universe_primary_liquid"].astype(bool).all():
        raise RuntimeError("V3-B final-refit eligibility facts mismatch")
    if not eligible["label_status"].isin(["TP_FIRST", "SL_FIRST"]).all():
        raise RuntimeError("V3-B final-refit table contains non-resolved labels")
    joined = eligible.merge(overlay[["ticker", "date", "open"]], on=["ticker", "date"], how="left", validate="one_to_one")
    joined["open_known"] = joined["open"].notna()
    joined["year"] = joined["date"].dt.year

    by_year = joined.groupby("year", as_index=False).agg(rows=("ticker", "size"), known=("open_known", "sum"))
    by_year["missing"] = by_year["rows"] - by_year["known"]
    by_year["coverage"] = by_year["known"] / by_year["rows"]
    by_ticker = joined.groupby("ticker", as_index=False).agg(rows=("ticker", "size"), known=("open_known", "sum"))
    by_ticker["missing"] = by_ticker["rows"] - by_ticker["known"]
    by_ticker["coverage"] = by_ticker["known"] / by_ticker["rows"]
    by_session = _coverage_summary(joined)

    partition_rows: list[pd.DataFrame] = []
    for partition, path in PARTITION_PATHS.items():
        prediction = pd.read_parquet(path, columns=["fold", "ticker", "date", "signal_session_index"])
        prediction = _normalise_dates(prediction).drop_duplicates(["fold", "ticker", "date"])
        prediction["partition_source"] = partition
        partition_rows.append(prediction)
    partitions = pd.concat(partition_rows, ignore_index=True)
    partitions = partitions.merge(overlay[["ticker", "date", "open"]], on=["ticker", "date"], how="left", validate="one_to_one")
    partitions["open_known"] = partitions["open"].notna()
    by_partition = partitions.groupby("fold", as_index=False).agg(rows=("ticker", "size"), known=("open_known", "sum"))
    by_partition["missing"] = by_partition["rows"] - by_partition["known"]
    by_partition["coverage"] = by_partition["known"] / by_partition["rows"]

    feature_rows, feature_summary = _feature_readiness(eligible, panel, overlay)
    residual = _normalise_dates(pd.read_csv(RESIDUAL_PATH))
    tv = _normalise_dates(pd.read_csv(TRADINGVIEW_CENSUS_PATH))
    missing = joined.loc[~joined["open_known"], ["ticker", "date"]]
    overlap = missing.merge(residual, on=["ticker", "date"], how="left", validate="one_to_one")
    overlap = overlap.merge(tv[["ticker", "date", "provider_class", "residual_problem_class"]], on=["ticker", "date"], how="left", validate="one_to_one")
    overlap["tv_bucket"] = overlap["provider_class"].fillna("CORPORATE_ACTION_OR_OUTSIDE_TV_TARGET")
    residual_overlap = overlap["tv_bucket"].value_counts(dropna=False).rename_axis("bucket").reset_index(name="rows")
    residual_overlap["share_of_missing"] = residual_overlap["rows"] / len(overlap)

    top_missing = by_ticker.sort_values(["missing", "rows", "ticker"], ascending=[False, False, True])
    global_rows = int(len(overlay))
    global_known = int(overlay["open"].notna().sum())
    v3_rows = int(len(joined))
    v3_known = int(joined["open_known"].sum())
    all_features = int(feature_rows["open_feature_ready"].sum())
    if v3_known == v3_rows and all_features == v3_rows:
        decision = "PASS_FOR_OHLCV_ALPHA_RESEARCH"
    elif v3_known / v3_rows >= 0.95 and all_features / v3_rows >= 0.95:
        decision = "CONDITIONAL_PASS_FOR_OHLCV_ALPHA_RESEARCH"
    else:
        decision = "FAIL_FOR_OHLCV_ALPHA_RESEARCH"

    overlay.to_parquet(output_dir / "open_research_coverage_overlay.parquet", index=False)
    overlay_provenance.to_parquet(output_dir / "open_research_coverage_overlay_provenance.parquet", index=False)
    _write_json(overlay_change, output_dir / "smbr_overlay_change.json")
    _write_csv(joined[["ticker", "date", "signal_session_index", "open", "open_known", "year"]], output_dir / "v3_b_open_eligible_rows.csv")
    _write_csv(by_year, output_dir / "v3_b_open_coverage_by_year.csv")
    _write_csv(by_ticker.sort_values(["missing", "ticker"], ascending=[False, True]), output_dir / "v3_b_open_coverage_by_ticker.csv")
    _write_csv(by_session, output_dir / "v3_b_open_coverage_by_session.csv")
    _write_csv(by_partition, output_dir / "v3_b_open_coverage_by_partition.csv")
    _write_csv(feature_rows, output_dir / "v3_b_open_feature_readiness_rows.csv")
    _write_csv(feature_summary, output_dir / "v3_b_open_feature_readiness_summary.csv")
    _write_csv(residual_overlap, output_dir / "v3_b_open_missing_residual_overlap.csv")
    _write_csv(overlap, output_dir / "v3_b_open_missing_residual_detail.csv")

    summary: dict[str, Any] = {
        "status": "OPEN_RESEARCH_COVERAGE_GATE_COMPLETE",
        "decision": decision,
        "code_commit": code_commit,
        "immutable_panel_sha256_before": source_hashes["panel"],
        "immutable_panel_sha256_after": sha256_file(PANEL_PATH),
        "immutable_panel_unchanged": source_hashes["panel"] == sha256_file(PANEL_PATH),
        "network_calls": 0,
        "training_or_tuning_performed": False,
        "fresh_forward_outcomes_accessed": False,
        "overlay": overlay_change,
        "global_open": {"rows": global_rows, "known": global_known, "missing": global_rows - global_known, "coverage": global_known / global_rows},
        "v3_b": {
            "architecture": V3_B_ARCHITECTURE,
            "final_refit_population_rows": v3_rows,
            "final_refit_population_tickers": int(joined["ticker"].nunique()),
            "open_known": v3_known,
            "open_missing": v3_rows - v3_known,
            "open_coverage": v3_known / v3_rows,
            "all_open_feature_ready_rows": all_features,
            "all_open_feature_ready_rate": all_features / v3_rows,
            "lost_if_open_required": v3_rows - v3_known,
            "lost_if_all_open_features_required": v3_rows - all_features,
            "source_artifact": str(FINAL_REFIT_TABLE_PATH),
            "source_artifact_sha256": source_hashes["final_refit_table"],
            "manifest_sha256": source_hashes["final_refit_manifest"],
        },
        "concentration": {
            "tickers": int(len(by_ticker)),
            "fully_open_tickers": int((by_ticker["missing"] == 0).sum()),
            "partially_missing_tickers": int(((by_ticker["missing"] > 0) & (by_ticker["known"] > 0)).sum()),
            "all_missing_tickers": int((by_ticker["known"] == 0).sum()),
            "top_missing": {str(n): {"rows": int(top_missing.head(n)["missing"].sum()), "share_of_missing": float(top_missing.head(n)["missing"].sum() / (v3_rows - v3_known))} for n in (10, 20, 50)},
            "top_20_tickers": top_missing.head(20)[["ticker", "rows", "known", "missing", "coverage"]].to_dict("records"),
            "worst_sessions": by_session.sort_values(["coverage", "missing"], ascending=[True, False]).head(20).to_dict("records"),
        },
        "coverage_by_year": by_year.to_dict("records"),
        "coverage_by_partition": by_partition.to_dict("records"),
        "feature_readiness": {"features": feature_summary.to_dict("records"), "decision_time": "after session close; current Open is available by then; prior_close is previous observed ACTIVE panel bar", "flat_high_low_open_position_rows": int((feature_rows["open"].notna() & feature_rows["high"].eq(feature_rows["low"])).sum())},
        "missing_residual_overlap": residual_overlap.to_dict("records"),
        "source_hashes": source_hashes,
    }
    data_files = sorted(path for path in output_dir.iterdir() if path.is_file())
    manifest = {"runtime": "open_research_coverage_gate_v1_20260812", "files": {path.name: sha256_file(path) for path in data_files}}
    _write_json(manifest, output_dir / "artifact_manifest.json")
    summary["artifact_manifest_sha256"] = sha256_file(output_dir / "artifact_manifest.json")
    summary["artifact_hashes"] = manifest["files"]
    _write_json(summary, output_dir / "coverage_gate_summary.json")
    summary["coverage_gate_summary_sha256"] = sha256_file(output_dir / "coverage_gate_summary.json")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--code-commit", default="")
    args = parser.parse_args()
    print(json.dumps(run_open_research_coverage_gate(output_dir=args.output_dir, code_commit=args.code_commit), indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
