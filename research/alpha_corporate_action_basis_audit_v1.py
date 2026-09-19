"""Outcome-blind corporate-action/price-basis audit for the alpha lane.

This audit consumes already-retained local evidence read-only. It does not
repair or overwrite the clean panel, perform model fitting, access outcomes,
or authorize a refit. The counterfactual only replaces close with the staged
HLC overlay in memory to quantify candidate sensitivity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from alpha_stage_a_v2 import build_decision_universe, rolling


CANDIDATES = [
    "C1_residual_reversal_5_v1",
    "C2_participation_confirmation_5_v1",
    "C4_path_efficiency_reversal_20_v1",
]
PANEL_COLUMNS = ["ticker", "date", "close", "volume", "regular_market_value"]
EXPECTED_SESSIONS_SHA256 = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
EXPECTED_ANCHORS_SHA256 = "33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite_float(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def score_panel(panel: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    raw = panel[PANEL_COLUMNS].copy()
    raw["ticker"] = raw["ticker"].astype("string")
    raw["date"] = pd.to_datetime(raw["date"], errors="raise").dt.normalize()
    for column in ["close", "volume", "regular_market_value"]:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")
    full = universe.merge(raw, on=["ticker", "date"], how="left", validate="one_to_one")
    full = full.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    full["close_valid"] = full["close"].gt(0) & np.isfinite(full["close"])
    full["volume_valid"] = full["volume"].gt(0) & np.isfinite(full["volume"])
    full["close_for_return"] = full["close"].where(full["close_valid"])
    full["ret_1"] = full.groupby("ticker", sort=False)["close_for_return"].pct_change(
        fill_method=None
    )
    full["ret_5"] = full.groupby("ticker", sort=False)["close_for_return"].pct_change(
        periods=5, fill_method=None
    )
    full["ret_20"] = full.groupby("ticker", sort=False)["close_for_return"].pct_change(
        periods=20, fill_method=None
    )
    full["turnover"] = (full["close"] * full["volume"]).where(
        full["close_valid"] & full["volume_valid"]
    )
    full["abs_ret_1"] = full["ret_1"].abs()
    full["abs_ret_sum_20"] = rolling(full, "abs_ret_1", 20, "sum")
    full["vol_20"] = rolling(full, "ret_1", 20, "std")
    full["turnover_mean_5"] = rolling(full, "turnover", 5, "mean")
    full["turnover_median_60"] = rolling(full, "turnover", 60, "median")

    eligible_returns = full.loc[
        full["eligible_decision_universe"] & np.isfinite(full["ret_1"]),
        ["date", "ret_1"],
    ]
    official_dates = pd.Index(sorted(universe["date"].unique()), name="date")
    market_ret = eligible_returns.groupby("date", sort=True)["ret_1"].mean().reindex(official_dates)
    market_ret_5 = (
        (1.0 + market_ret).rolling(window=5, min_periods=5).apply(np.prod, raw=True)
        .sub(1.0)
    )
    full = full.join(
        pd.concat([market_ret.rename("market_ret"), market_ret_5.rename("market_ret_5")], axis=1),
        on="date",
    )
    full["stock_ret_lag1"] = full.groupby("ticker", sort=False)["ret_1"].shift(1)
    full["market_ret_lag1"] = full.groupby("ticker", sort=False)["market_ret"].shift(1)
    valid_pair = np.isfinite(full["stock_ret_lag1"]) & np.isfinite(full["market_ret_lag1"])
    beta_x = full["stock_ret_lag1"].where(valid_pair)
    beta_y = full["market_ret_lag1"].where(valid_pair)
    n = rolling(pd.DataFrame({"ticker": full["ticker"], "x": beta_x}), "x", 60, "count")
    sx = rolling(pd.DataFrame({"ticker": full["ticker"], "x": beta_x}), "x", 60, "sum")
    sy = rolling(pd.DataFrame({"ticker": full["ticker"], "x": beta_y}), "x", 60, "sum")
    sxy = rolling(
        pd.DataFrame({"ticker": full["ticker"], "x": beta_x * beta_y}), "x", 60, "sum"
    )
    syy = rolling(pd.DataFrame({"ticker": full["ticker"], "x": beta_y**2}), "x", 60, "sum")
    covariance = sxy - (sx * sy / n)
    market_variance = syy - (sy * sy / n)
    beta = covariance / market_variance.replace(0.0, np.nan)
    full[CANDIDATES[0]] = -(
        full["ret_5"] - beta * full["market_ret_5"]
    ) / full["vol_20"].replace(0.0, np.nan)
    abnormal_turnover = full["turnover_mean_5"] / full["turnover_median_60"].replace(0.0, np.nan)
    full[CANDIDATES[1]] = full["ret_5"] * np.log(abnormal_turnover)
    full[CANDIDATES[2]] = -full["ret_20"] / full["abs_ret_sum_20"].replace(0.0, np.nan)
    for column in CANDIDATES:
        full.loc[~full["eligible_decision_universe"], column] = np.nan
    return full.loc[full["ticker"].notna(), ["ticker", "date", "eligible_decision_universe", *CANDIDATES]]


def rank_frame(scores: pd.DataFrame) -> pd.DataFrame:
    result = scores[["ticker", "date", "eligible_decision_universe", *CANDIDATES]].copy()
    for column in CANDIDATES:
        result[f"rank_{column}"] = result.groupby("date", sort=False)[column].rank(
            method="average", pct=True
        )
    return result


def top30_sets(frame: pd.DataFrame, column: str) -> dict[pd.Timestamp, set[str]]:
    valid = frame["eligible_decision_universe"] & frame[column].notna() & np.isfinite(frame[column])
    result: dict[pd.Timestamp, set[str]] = {}
    for date, group in frame.loc[valid].groupby("date", sort=True):
        chosen = group.sort_values([column, "ticker"], ascending=[False, True], kind="mergesort").head(30)
        if len(chosen) == 30:
            result[pd.Timestamp(date)] = set(chosen["ticker"].astype(str))
    return result


def compare_candidate_values(
    baseline: pd.DataFrame, counterfactual: pd.DataFrame
) -> dict[str, object]:
    merged = baseline.merge(
        counterfactual,
        on=["ticker", "date", "eligible_decision_universe"],
        suffixes=("_base", "_cf"),
        validate="one_to_one",
    )
    baseline_ranked = rank_frame(baseline)
    counterfactual_ranked = rank_frame(counterfactual)
    ranked = baseline_ranked.merge(
        counterfactual_ranked,
        on=["ticker", "date", "eligible_decision_universe"],
        suffixes=("_base", "_cf"),
        validate="one_to_one",
    )
    result: dict[str, object] = {}
    for column in CANDIDATES:
        base = pd.to_numeric(merged[f"{column}_base"], errors="coerce")
        cf = pd.to_numeric(merged[f"{column}_cf"], errors="coerce")
        valid = merged["eligible_decision_universe"] & np.isfinite(base) & np.isfinite(cf)
        delta = (cf - base).where(valid)
        base_rank = pd.to_numeric(ranked[f"rank_{column}_base"], errors="coerce")
        cf_rank = pd.to_numeric(ranked[f"rank_{column}_cf"], errors="coerce")
        rank_valid = ranked["eligible_decision_universe"] & np.isfinite(base_rank) & np.isfinite(cf_rank)
        rank_changed = (base_rank - cf_rank).abs().gt(1e-12) & rank_valid
        top_base = top30_sets(baseline, column)
        top_cf = top30_sets(counterfactual, column)
        overlaps = [
            len(top_base[date] & top_cf[date]) / 30.0
            for date in sorted(set(top_base) & set(top_cf))
        ]
        result[column] = {
            "finite_eligible_rows_compared": int(valid.sum()),
            "rows_with_score_change": int((delta.abs() > 1e-12).sum()),
            "mean_abs_score_change": finite_float(delta.abs().mean()),
            "max_abs_score_change": finite_float(delta.abs().max()),
            "rows_with_rank_change": int(rank_changed.sum()),
            "rank_change_rate_of_compared_rows": finite_float(
                rank_changed.sum() / rank_valid.sum()
            ) if rank_valid.any() else None,
            "top30_common_dates": int(len(overlaps)),
            "mean_top30_overlap": finite_float(np.mean(overlaps)) if overlaps else None,
            "min_top30_overlap": finite_float(np.min(overlaps)) if overlaps else None,
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--actions", type=Path, required=True)
    parser.add_argument("--hlc-overlay", type=Path, required=True)
    parser.add_argument("--unresolved-scale", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if "idx-alpha-available-data-staging-20260919" not in str(args.output.resolve()):
        raise ValueError("refusing output outside isolated alpha staging")

    panel = pd.read_parquet(args.panel, columns=PANEL_COLUMNS)
    panel["ticker"] = panel["ticker"].astype("string")
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    if panel.duplicated(["ticker", "date"]).any():
        raise ValueError("panel duplicate keys")
    features = pd.read_parquet(args.features)
    features["ticker"] = features["ticker"].astype("string")
    features["date"] = pd.to_datetime(features["date"], errors="raise").dt.normalize()
    baseline = features[["ticker", "date", "eligible_decision_universe", *CANDIDATES]].copy()
    universe, universe_stats = build_decision_universe(
        panel[["ticker", "date", "regular_market_value"]], args.sessions, args.anchors
    )
    reproduced = score_panel(panel, universe)
    reproduction = {}
    for column in CANDIDATES:
        joined = baseline.merge(reproduced, on=["ticker", "date", "eligible_decision_universe"], suffixes=("_stored", "_reproduced"), validate="one_to_one")
        left = pd.to_numeric(joined[f"{column}_stored"], errors="coerce")
        right = pd.to_numeric(joined[f"{column}_reproduced"], errors="coerce")
        valid = np.isfinite(left) & np.isfinite(right)
        reproduction[column] = {
            "finite_compared": int(valid.sum()),
            "max_abs_diff": finite_float((left[valid] - right[valid]).abs().max()),
        }

    actions = pd.read_csv(args.actions)
    actions["ticker"] = actions["ticker"].astype("string")
    actions["effective_date"] = pd.to_datetime(actions["effective_date"], errors="coerce").dt.normalize()
    overlay = pd.read_csv(args.hlc_overlay)
    overlay["ticker"] = overlay["ticker"].astype("string")
    overlay["date"] = pd.to_datetime(overlay["date"], errors="raise").dt.normalize()
    overlay["remediated_close"] = pd.to_numeric(overlay["remediated_close"], errors="coerce")
    unresolved = pd.read_csv(args.unresolved_scale, usecols=["ticker", "date", "panel_idx_scale_factor", "panel_idx_row_scale_consistent"])
    unresolved["ticker"] = unresolved["ticker"].astype("string")
    unresolved["date"] = pd.to_datetime(unresolved["date"], errors="raise").dt.normalize()

    overlay_keys = overlay[["ticker", "date"]].drop_duplicates()
    panel_keys = panel[["ticker", "date"]]
    overlay_panel = overlay_keys.merge(panel_keys, on=["ticker", "date"], how="left", indicator=True)
    overlay_panel_values = overlay[["ticker", "date", "original_close", "remediated_close"]].merge(
        panel[["ticker", "date", "close"]], on=["ticker", "date"], how="left", validate="one_to_one"
    )
    overlay_panel_values["original_close"] = pd.to_numeric(overlay_panel_values["original_close"], errors="coerce")
    overlay_panel_values["remediated_close"] = pd.to_numeric(overlay_panel_values["remediated_close"], errors="coerce")
    overlay_panel_values["close"] = pd.to_numeric(overlay_panel_values["close"], errors="coerce")
    panel_overlay_comparison = {
        "rows": int(len(overlay_panel_values)),
        "panel_close_equals_remediated_close_rows": int(
            np.isclose(overlay_panel_values["close"], overlay_panel_values["remediated_close"], rtol=0.0, atol=1e-8, equal_nan=False).sum()
        ),
        "panel_close_equals_original_close_rows": int(
            np.isclose(overlay_panel_values["close"], overlay_panel_values["original_close"], rtol=0.0, atol=1e-8, equal_nan=False).sum()
        ),
        "panel_close_mismatch_rows": int(
            (~np.isclose(overlay_panel_values["close"], overlay_panel_values["remediated_close"], rtol=0.0, atol=1e-8, equal_nan=False)).sum()
        ),
    }
    overlay_eligible = overlay_keys.merge(
        baseline.loc[baseline["eligible_decision_universe"], ["ticker", "date"]],
        on=["ticker", "date"], how="inner"
    )
    counterfactual_panel = panel.merge(
        overlay[["ticker", "date", "remediated_close"]],
        on=["ticker", "date"], how="left", validate="one_to_one"
    )
    counterfactual_panel["close"] = counterfactual_panel["remediated_close"].fillna(counterfactual_panel["close"])
    counterfactual_panel = counterfactual_panel[PANEL_COLUMNS]
    counterfactual = score_panel(counterfactual_panel, universe)
    sensitivity = compare_candidate_values(reproduced, counterfactual)

    official_sessions = pd.read_csv(args.sessions, usecols=["date"])
    official_sessions["date"] = pd.to_datetime(official_sessions["date"], errors="raise").dt.normalize()
    session_index = {date: index for index, date in enumerate(official_sessions["date"].sort_values())}
    overlay_forward_60 = set()
    for row in overlay_keys.itertuples(index=False):
        if row.date not in session_index:
            continue
        for offset in range(61):
            index = session_index[row.date] + offset
            dates = official_sessions["date"].sort_values()
            if index >= len(dates):
                break
            overlay_forward_60.add((str(row.ticker), pd.Timestamp(dates.iloc[index])))
    forward_60_eligible = baseline.loc[baseline["eligible_decision_universe"], ["ticker", "date"]].astype({"ticker": str})
    forward_60_eligible_keys = set(zip(forward_60_eligible["ticker"], forward_60_eligible["date"])) & overlay_forward_60

    checks = {
        "panel_unique_keys": not panel.duplicated(["ticker", "date"]).any(),
        "features_key_closure": set(zip(panel["ticker"], panel["date"])) == set(zip(features["ticker"], features["date"])),
        "official_sessions_hash_expected": sha256_file(args.sessions) == EXPECTED_SESSIONS_SHA256,
        "anchors_hash_expected": sha256_file(args.anchors) == EXPECTED_ANCHORS_SHA256,
        "stored_reproduction_within_tolerance": all(
            value["max_abs_diff"] is not None and value["max_abs_diff"] <= 1e-10
            for value in reproduction.values()
        ),
        "overlay_rows_are_unique": not overlay.duplicated(["ticker", "date"]).any(),
        "overlay_close_finite_positive": bool(overlay["remediated_close"].gt(0).all()),
        "panel_close_matches_overlay_remediated": panel_overlay_comparison["panel_close_mismatch_rows"] == 0,
        "no_target_or_outcome_access": True,
        "no_refit_or_panel_mutation": True,
    }
    result = {
        "status": "PASS_STRUCTURAL_ONLY" if all(checks.values()) else "FAIL_AUDIT",
        "stage": "B_J_CORPORATE_ACTION_PRICE_BASIS_EXPOSURE_AUDIT",
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "outcome_accessed": False,
        "target_accessed": False,
        "provider_accessed": False,
        "model_fit": False,
        "model_scoring": False,
        "panel_mutated": False,
        "clean_refit_authorized": False,
        "checks": checks,
        "universe": universe_stats,
        "official_action_inventory": {
            "rows": int(len(actions)),
            "tickers": int(actions["ticker"].nunique()),
            "date_min": str(actions["effective_date"].min().date()),
            "date_max": str(actions["effective_date"].max().date()),
            "action_counts": actions["action"].value_counts(dropna=False).to_dict(),
            "known_ratio_rows": int(pd.to_numeric(actions["ratio"], errors="coerce").notna().sum()),
            "source_identity_values": sorted(actions["source_identity"].dropna().astype(str).unique().tolist()),
        },
        "hlc_overlay_inventory": {
            "rows": int(len(overlay)),
            "tickers": int(overlay["ticker"].nunique()),
            "date_min": str(overlay["date"].min().date()),
            "date_max": str(overlay["date"].max().date()),
            "panel_key_overlap_rows": int((overlay_panel["_merge"] == "both").sum()),
            "eligible_key_overlap_rows": int(len(overlay_eligible)),
            "nonunit_factor_rows": int((pd.to_numeric(overlay["observed_factor"], errors="coerce") != 1.0).sum()),
            "ca_type_counts": overlay["ca_type"].value_counts(dropna=False).to_dict(),
            "panel_overlay_comparison": panel_overlay_comparison,
        },
        "unresolved_nonstable_scale": {
            "rows": int(len(unresolved)),
            "tickers": int(unresolved["ticker"].nunique()),
            "panel_key_overlap_rows": int(len(unresolved.merge(panel_keys, on=["ticker", "date"], how="inner"))),
            "scale_factors": sorted(pd.to_numeric(unresolved["panel_idx_scale_factor"], errors="coerce").dropna().round(10).unique().tolist()),
        },
        "candidate_exposure": {
            "overlay_tickers": sorted(overlay["ticker"].astype(str).unique().tolist()),
            "eligible_rows_in_forward_60_sessions_from_overlay": int(len(forward_60_eligible_keys)),
            "eligible_tickers_in_forward_60_sessions_from_overlay": int(len({ticker for ticker, _ in forward_60_eligible_keys})),
            "stored_score_reproduction": reproduction,
            "counterfactual_close_overlay_sensitivity": sensitivity,
        },
        "interpretation": {
            "classification": "PARTIAL / FORENSIC EVIDENCE ONLY",
            "corporate_action_basis_admitted": False,
            "historical_pit_admitted": False,
            "price_overlay_is_counterfactual": True,
            "no_predictive_claim": True,
            "warning": "Existing upstream artifacts explicitly stop for forensic review and do not authorize clean refit; this result must not replace the frozen panel or authorize target evaluation.",
        },
        "source_hashes": {name: sha256_file(path) for name, path in {
            "panel": args.panel,
            "features": args.features,
            "official_sessions": args.sessions,
            "tradability_anchors": args.anchors,
            "official_actions": args.actions,
            "hlc_overlay": args.hlc_overlay,
            "unresolved_scale": args.unresolved_scale,
        }.items()},
        "code_sha256": sha256_file(Path(__file__)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    if result["status"] != "PASS_STRUCTURAL_ONLY":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
