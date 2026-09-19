"""Independent, outcome-blind replay of the frozen C1/C2/C4 constructors.

This verifier intentionally does not import the Stage A builder.  It rebuilds
the session grid, eligibility mask, causal rolling inputs, scores, and daily
average-tie ranks from the admitted non-outcome inputs, then compares those
values with the staged feature artifact.  It is a structural implementation
check only; it does not establish PIT, corporate-action, issuer, or predictive
validity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


CANDIDATES = {
    "C1": "C1_residual_reversal_5_v1",
    "C2": "C2_participation_confirmation_5_v1",
    "C4": "C4_path_efficiency_reversal_20_v1",
}
RANKS = {key: f"rank_{value}" for key, value in CANDIDATES.items()}
PANEL_COLUMNS = ["ticker", "date", "close", "volume", "regular_market_value"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rolling(frame: pd.DataFrame, column: str, window: int, operation: str) -> pd.Series:
    grouped = frame.groupby("ticker", sort=False)[column].rolling(
        window=window, min_periods=window
    )
    value = getattr(grouped, operation)().reset_index(level=0, drop=True)
    value.index = frame.index
    return value


def compare_series(left: pd.Series, right: pd.Series, tolerance: float = 1e-12) -> dict[str, object]:
    left = pd.to_numeric(left, errors="coerce")
    right = pd.to_numeric(right, errors="coerce")
    missing_match = left.isna().eq(right.isna())
    finite_pair = left.notna() & right.notna()
    if finite_pair.any():
        max_abs_diff = float((left[finite_pair] - right[finite_pair]).abs().max())
        value_match = bool(((left[finite_pair] - right[finite_pair]).abs() <= tolerance).all())
    else:
        max_abs_diff = None
        value_match = True
    return {
        "missingness_match": bool(missing_match.all()),
        "value_match": value_match,
        "mismatch_count": int((~missing_match | (finite_pair & ((left - right).abs() > tolerance))).sum()),
        "max_abs_diff": max_abs_diff,
    }


def build_replay(
    panel_path: Path,
    features_path: Path,
    sessions_path: Path,
    anchors_path: Path,
) -> dict[str, object]:
    raw = pd.read_parquet(panel_path, columns=PANEL_COLUMNS)
    raw["ticker"] = raw["ticker"].astype("string")
    raw["date"] = pd.to_datetime(raw["date"], errors="raise").dt.normalize()
    for column in PANEL_COLUMNS[2:]:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")
    raw["source_panel_row_present"] = True

    sessions = pd.read_csv(sessions_path, usecols=["date"])
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    sessions = sessions.sort_values("date", kind="mergesort").reset_index(drop=True)
    if sessions["date"].duplicated().any():
        raise ValueError("session dates are not unique")

    anchors = pd.read_csv(anchors_path)
    anchors["ticker"] = anchors["ticker"].astype("string")
    anchors["as_of_date"] = pd.to_datetime(anchors["as_of_date"], errors="raise").dt.normalize()
    active = anchors.loc[
        (anchors["market"] == "REGULAR") & (anchors["state"] == "ACTIVE"),
        ["ticker", "as_of_date"],
    ].rename(columns={"as_of_date": "date"})
    if active.duplicated(["ticker", "date"]).any():
        raise ValueError("active regular anchors are duplicated")

    tickers = pd.Index(sorted(raw["ticker"].dropna().unique()), name="ticker")
    full = pd.MultiIndex.from_product(
        [tickers, sessions["date"]], names=["ticker", "date"]
    ).to_frame(index=False)
    full = full.merge(
        raw[["ticker", "date", "regular_market_value"]],
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )
    full["active_regular"] = full.set_index(["ticker", "date"]).index.isin(
        active.set_index(["ticker", "date"]).index
    )
    full["value_for_liquidity"] = full["regular_market_value"].where(
        full["active_regular"]
        & full["regular_market_value"].gt(0)
        & np.isfinite(full["regular_market_value"])
    )
    full = full.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    full["value_count_60"] = rolling(full, "value_for_liquidity", 60, "count")
    full["value_median_60"] = rolling(full, "value_for_liquidity", 60, "median")
    full["eligible_decision_universe"] = (
        full["active_regular"]
        & full["value_count_60"].ge(20)
        & full["value_median_60"].ge(1_000_000_000)
    )
    universe = full[["ticker", "date", "eligible_decision_universe"]]

    frame = universe.merge(
        raw, on=["ticker", "date"], how="left", validate="one_to_one"
    )
    frame = frame.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    frame["source_panel_row_present"] = frame["source_panel_row_present"].fillna(False).astype(bool)
    frame["eligible_decision_universe"] = frame["eligible_decision_universe"].fillna(False).astype(bool)
    close_valid = frame["close"].gt(0) & np.isfinite(frame["close"])
    volume_valid = frame["volume"].gt(0) & np.isfinite(frame["volume"])
    frame["close_for_return"] = frame["close"].where(close_valid)
    frame["ret_1"] = frame.groupby("ticker", sort=False)["close_for_return"].pct_change(fill_method=None)
    frame["ret_5"] = frame.groupby("ticker", sort=False)["close_for_return"].pct_change(
        periods=5, fill_method=None
    )
    frame["ret_20"] = frame.groupby("ticker", sort=False)["close_for_return"].pct_change(
        periods=20, fill_method=None
    )
    frame["turnover"] = (frame["close"] * frame["volume"]).where(close_valid & volume_valid)
    frame["abs_ret_1"] = frame["ret_1"].abs()
    frame["abs_ret_sum_20"] = rolling(frame, "abs_ret_1", 20, "sum")
    frame["vol_20"] = rolling(frame, "ret_1", 20, "std")
    frame["turnover_mean_5"] = rolling(frame, "turnover", 5, "mean")
    frame["turnover_median_60"] = rolling(frame, "turnover", 60, "median")

    eligible_returns = frame.loc[
        frame["source_panel_row_present"]
        & frame["eligible_decision_universe"]
        & np.isfinite(frame["ret_1"]),
        ["date", "ret_1"],
    ]
    official_dates = pd.Index(sorted(universe["date"].unique()), name="date")
    market_ret = eligible_returns.groupby("date", sort=True)["ret_1"].mean().reindex(official_dates)
    market_ret_5 = (
        (1.0 + market_ret).rolling(window=5, min_periods=5).apply(np.prod, raw=True).sub(1.0)
    )
    frame["market_ret"] = frame["date"].map(market_ret)
    frame["market_ret_5"] = frame["date"].map(market_ret_5)
    frame["stock_ret_lag1"] = frame.groupby("ticker", sort=False)["ret_1"].shift(1)
    frame["market_ret_lag1"] = frame.groupby("ticker", sort=False)["market_ret"].shift(1)
    valid_pair = np.isfinite(frame["stock_ret_lag1"]) & np.isfinite(frame["market_ret_lag1"])
    frame["beta_x"] = frame["stock_ret_lag1"].where(valid_pair)
    frame["beta_y"] = frame["market_ret_lag1"].where(valid_pair)
    frame["beta_xy"] = frame["beta_x"] * frame["beta_y"]
    frame["beta_yy"] = frame["beta_y"] ** 2
    n = rolling(frame, "beta_x", 60, "count")
    sx = rolling(frame, "beta_x", 60, "sum")
    sy = rolling(frame, "beta_y", 60, "sum")
    sxy = rolling(frame, "beta_xy", 60, "sum")
    syy = rolling(frame, "beta_yy", 60, "sum")
    covariance = sxy - (sx * sy / n)
    variance = syy - (sy * sy / n)
    frame["beta_60_prior"] = covariance / variance.replace(0.0, np.nan)
    frame[CANDIDATES["C1"]] = -(
        frame["ret_5"] - frame["beta_60_prior"] * frame["market_ret_5"]
    ) / frame["vol_20"].replace(0.0, np.nan)
    abnormal_turnover = frame["turnover_mean_5"] / frame["turnover_median_60"].replace(0.0, np.nan)
    frame[CANDIDATES["C2"]] = frame["ret_5"] * np.log(abnormal_turnover)
    frame[CANDIDATES["C4"]] = -frame["ret_20"] / frame["abs_ret_sum_20"].replace(0.0, np.nan)
    for column in CANDIDATES.values():
        frame.loc[~frame["eligible_decision_universe"], column] = np.nan

    replay = frame.loc[
        frame["source_panel_row_present"],
        ["ticker", "date", "eligible_decision_universe", *CANDIDATES.values()],
    ].copy()
    for key, score in CANDIDATES.items():
        replay[RANKS[key]] = np.nan
        valid = replay["eligible_decision_universe"] & replay[score].notna() & np.isfinite(replay[score])
        replay.loc[valid, RANKS[key]] = replay.loc[valid].groupby("date")[score].rank(
            method="average", pct=True
        )

    stored_columns = ["ticker", "date", "eligible_decision_universe", *CANDIDATES.values(), *RANKS.values()]
    stored = pd.read_parquet(features_path, columns=stored_columns)
    stored["ticker"] = stored["ticker"].astype("string")
    stored["date"] = pd.to_datetime(stored["date"], errors="raise").dt.normalize()
    merged = replay.merge(
        stored, on=["ticker", "date"], how="outer", suffixes=("_replay", "_stored"),
        indicator=True, validate="one_to_one"
    )
    checks: dict[str, bool] = {
        "key_sets_equal": bool((merged["_merge"] == "both").all() and len(merged) == len(replay) == len(stored)),
        "replay_keys_unique": not replay.duplicated(["ticker", "date"]).any(),
        "stored_keys_unique": not stored.duplicated(["ticker", "date"]).any(),
        "replay_dates_official": set(replay["date"]).issubset(set(official_dates)),
        "eligible_match": bool((merged["eligible_decision_universe_replay"] == merged["eligible_decision_universe_stored"]).all()),
    }
    comparisons: dict[str, object] = {}
    for key, score in CANDIDATES.items():
        comparisons[score] = compare_series(merged[f"{score}_replay"], merged[f"{score}_stored"])
        comparisons[RANKS[key]] = compare_series(merged[f"{RANKS[key]}_replay"], merged[f"{RANKS[key]}_stored"])
        checks[f"{score}_match"] = bool(comparisons[score]["missingness_match"] and comparisons[score]["value_match"])
        checks[f"{RANKS[key]}_match"] = bool(comparisons[RANKS[key]]["missingness_match"] and comparisons[RANKS[key]]["value_match"])

    return {
        "checks": checks,
        "comparisons": comparisons,
        "row_counts": {"replay": int(len(replay)), "stored": int(len(stored)), "merged": int(len(merged))},
        "source_hashes": {
            "panel": sha256_file(panel_path),
            "features": sha256_file(features_path),
            "official_sessions": sha256_file(sessions_path),
            "tradability_anchors": sha256_file(anchors_path),
        },
        "implementation": {
            "candidate_ids": list(CANDIDATES),
            "rolling_windows": {"beta": 60, "volatility": 20, "participation_short": 5, "participation_long": 60, "path": 20},
            "rank_method": "average",
            "rank_percentile": True,
            "key_grain": "ticker/date",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output_path = args.output.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(output_path):
        raise ValueError("refusing output outside isolated alpha staging")
    result = build_replay(args.panel, args.features, args.sessions, args.anchors)
    checks = result["checks"]
    status = "PASS_INDEPENDENT_FORMULA_AND_RANK_REPLAY" if all(checks.values()) else "FAIL_INDEPENDENT_FORMULA_AND_RANK_REPLAY"
    payload = {
        "status": status,
        "stage": "Q_INDEPENDENT_C1234_CONSTRUCTOR_REPLAY_V1",
        "scope": "outcome-blind structural implementation replay only",
        "checks": checks,
        "details": result,
        "limitations": [
            "This replay does not certify PIT, issuer continuity, corporate-action basis, or executable capacity.",
            "It does not establish predictive performance or model superiority.",
        ],
        "verifier_code_sha256": sha256_file(Path(__file__)),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    if status != "PASS_INDEPENDENT_FORMULA_AND_RANK_REPLAY":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
