"""Outcome-blind synthetic challenger for semantic formula mutation detection.

This script does not touch admitted data, protected outcomes, or production
verifiers. It creates a temporary miniature OHLCV/session/anchor fixture and
uses an independently written reference implementation to produce C1/C2/C4
features and ranks. It then feeds baseline and intentionally mutated stored
features to the existing independent constructor replay and records whether
each semantic mutation is detected.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
STAGING_MARKER = "idx-alpha-available-data-staging-20260919"
SCORE_COLUMNS = [
    "C1_residual_reversal_5_v1",
    "C2_participation_confirmation_5_v1",
    "C4_path_efficiency_reversal_20_v1",
]
RANK_COLUMNS = [f"rank_{column}" for column in SCORE_COLUMNS]


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


def load_replay():
    path = ROOT / "research" / "alpha_c1234_constructor_replay_v1.py"
    spec = importlib.util.spec_from_file_location("constructor_replay_under_test", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, path


def make_fixture(root: Path) -> dict[str, Path]:
    dates = pd.bdate_range("2026-01-01", periods=150)
    tickers = ["AAA", "BBB", "CCC"]
    rows: list[dict[str, object]] = []
    for ticker_index, ticker in enumerate(tickers):
        for index, date in enumerate(dates):
            wave = 0.7 * np.sin((index + ticker_index) / 4.0)
            close = 100.0 + ticker_index * 7.0 + index * (0.11 + ticker_index * 0.02) + wave
            volume = 20_000_000.0 + ticker_index * 1_000_000.0 + (index % 9) * 250_000.0
            rows.append(
                {
                    "ticker": ticker,
                    "date": date,
                    "close": close,
                    "volume": volume,
                    "regular_market_value": close * volume,
                }
            )
    panel = pd.DataFrame(rows)
    sessions = pd.DataFrame({"date": dates})
    anchors = pd.DataFrame(
        {
            "ticker": np.repeat(tickers, len(dates)),
            "market": "REGULAR",
            "as_of_date": list(dates) * len(tickers),
            "state": "ACTIVE",
        }
    )
    panel_path = root / "synthetic_panel.parquet"
    sessions_path = root / "synthetic_sessions.csv"
    anchors_path = root / "synthetic_anchors.csv"
    panel.to_parquet(panel_path, index=False)
    sessions.to_csv(sessions_path, index=False)
    anchors.to_csv(anchors_path, index=False)
    return {"panel": panel_path, "sessions": sessions_path, "anchors": anchors_path}


def independent_reference(panel_path: Path, sessions_path: Path, anchors_path: Path, mutation: str | None = None) -> pd.DataFrame:
    raw = pd.read_parquet(panel_path)
    raw["ticker"] = raw["ticker"].astype("string")
    raw["date"] = pd.to_datetime(raw["date"], errors="raise").dt.normalize()
    sessions = pd.read_csv(sessions_path)
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    anchors = pd.read_csv(anchors_path)
    anchors["ticker"] = anchors["ticker"].astype("string")
    anchors["as_of_date"] = pd.to_datetime(anchors["as_of_date"], errors="raise").dt.normalize()

    tickers = pd.Index(sorted(raw["ticker"].unique()), name="ticker")
    full = pd.MultiIndex.from_product([tickers, sessions["date"]], names=["ticker", "date"]).to_frame(index=False)
    full = full.merge(raw[["ticker", "date", "regular_market_value"]], on=["ticker", "date"], how="left", validate="one_to_one")
    active = anchors.loc[
        (anchors["market"] == "REGULAR") & (anchors["state"] == "ACTIVE"),
        ["ticker", "as_of_date"],
    ].rename(columns={"as_of_date": "date"})
    full["active_regular"] = full.set_index(["ticker", "date"]).index.isin(active.set_index(["ticker", "date"]).index)
    full["value_for_liquidity"] = full["regular_market_value"].where(
        full["active_regular"] & full["regular_market_value"].gt(0)
    )
    full = full.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    full["value_count_60"] = rolling(full, "value_for_liquidity", 60, "count")
    full["value_median_60"] = rolling(full, "value_for_liquidity", 60, "median")
    full["eligible_decision_universe"] = (
        full["active_regular"] & full["value_count_60"].ge(20) & full["value_median_60"].ge(1_000_000_000)
    )

    frame = full[["ticker", "date", "eligible_decision_universe"]].merge(
        raw, on=["ticker", "date"], how="left", validate="one_to_one"
    )
    frame = frame.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    frame["close_for_return"] = frame["close"].where(frame["close"].gt(0))
    frame["ret_1"] = frame.groupby("ticker", sort=False)["close_for_return"].pct_change(fill_method=None)
    frame["ret_5"] = frame.groupby("ticker", sort=False)["close_for_return"].pct_change(periods=5, fill_method=None)
    frame["ret_20"] = frame.groupby("ticker", sort=False)["close_for_return"].pct_change(periods=20, fill_method=None)
    frame["turnover"] = (frame["close"] * frame["volume"]).where(frame["close"].gt(0) & frame["volume"].gt(0))
    frame["abs_ret_1"] = frame["ret_1"].abs()
    frame["abs_ret_sum_20"] = rolling(frame, "abs_ret_1", 20, "sum")
    frame["vol_20"] = rolling(frame, "ret_1", 20, "std")
    frame["turnover_mean_5"] = rolling(frame, "turnover", 5, "mean")
    frame["turnover_median_60"] = rolling(frame, "turnover", 60, "median")

    eligible_returns = frame.loc[frame["eligible_decision_universe"] & frame["ret_1"].notna(), ["date", "ret_1"]]
    official_dates = pd.Index(sorted(frame["date"].unique()), name="date")
    market_ret = eligible_returns.groupby("date", sort=True)["ret_1"].mean().reindex(official_dates)
    market_ret_5 = (1.0 + market_ret).rolling(5, min_periods=5).apply(np.prod, raw=True).sub(1.0)
    frame["market_ret"] = frame["date"].map(market_ret)
    frame["market_ret_5"] = frame["date"].map(market_ret_5)
    frame["stock_ret_lag1"] = frame.groupby("ticker", sort=False)["ret_1"].shift(1)
    frame["market_ret_lag1"] = frame.groupby("ticker", sort=False)["market_ret"].shift(1)
    frame["beta_x"] = frame["stock_ret_lag1"]
    frame["beta_y"] = frame["market_ret_lag1"]
    frame["beta_xy"] = frame["beta_x"] * frame["beta_y"]
    frame["beta_yy"] = frame["beta_y"] ** 2
    frame["beta_xx"] = frame["beta_x"] ** 2
    n = rolling(frame, "beta_x", 60, "count")
    sx = rolling(frame, "beta_x", 60, "sum")
    sy = rolling(frame, "beta_y", 60, "sum")
    sxy = rolling(frame, "beta_xy", 60, "sum")
    syy = rolling(frame, "beta_yy", 60, "sum")
    sxx = rolling(frame, "beta_xx", 60, "sum")
    covariance = sxy - sx * sy / n
    market_variance = syy - sy * sy / n
    stock_variance = sxx - sx * sx / n
    beta = covariance / market_variance.replace(0.0, np.nan)
    if mutation == "c1_stock_variance_denominator":
        beta = covariance / stock_variance.replace(0.0, np.nan)
    if mutation == "c1_current_market_timing":
        frame["market_ret_lag1"] = frame["market_ret"]
        frame["beta_y"] = frame["market_ret_lag1"]
        frame["beta_xy"] = frame["beta_x"] * frame["beta_y"]
        frame["beta_yy"] = frame["beta_y"] ** 2
        sy = rolling(frame, "beta_y", 60, "sum")
        sxy = rolling(frame, "beta_xy", 60, "sum")
        syy = rolling(frame, "beta_yy", 60, "sum")
        beta = (sxy - sx * sy / n) / (syy - sy * sy / n).replace(0.0, np.nan)

    frame[SCORE_COLUMNS[0]] = -(frame["ret_5"] - beta * frame["market_ret_5"]) / frame["vol_20"].replace(0.0, np.nan)
    abnormal_turnover = frame["turnover_mean_5"] / frame["turnover_median_60"].replace(0.0, np.nan)
    frame[SCORE_COLUMNS[1]] = frame["ret_5"] * np.log(abnormal_turnover)
    if mutation == "c2_missing_log":
        frame[SCORE_COLUMNS[1]] = frame["ret_5"] * abnormal_turnover
    frame[SCORE_COLUMNS[2]] = -frame["ret_20"] / frame["abs_ret_sum_20"].replace(0.0, np.nan)
    if mutation == "c4_sign_flip":
        frame[SCORE_COLUMNS[2]] = frame["ret_20"] / frame["abs_ret_sum_20"].replace(0.0, np.nan)

    for column in SCORE_COLUMNS:
        frame.loc[~frame["eligible_decision_universe"], column] = np.nan
    output = frame.loc[:, ["ticker", "date", "eligible_decision_universe", *SCORE_COLUMNS]].copy()
    if mutation == "eligibility_flip":
        first_eligible = output.index[output["eligible_decision_universe"]].tolist()[0]
        output.loc[first_eligible, "eligible_decision_universe"] = False
        output.loc[first_eligible, SCORE_COLUMNS] = np.nan
    for index, column in enumerate(SCORE_COLUMNS, start=1):
        rank_column = RANK_COLUMNS[index - 1]
        output[rank_column] = np.nan
        valid = output["eligible_decision_universe"] & output[column].notna() & np.isfinite(output[column])
        output.loc[valid, rank_column] = output.loc[valid].groupby("date")[column].rank(method="average", pct=True)
    return output


def write_stored(frame: pd.DataFrame, path: Path) -> None:
    frame.to_parquet(path, index=False)


def run_case(replay, fixture: dict[str, Path], stored: Path, frame: pd.DataFrame, mutation: str | None) -> dict[str, object]:
    write_stored(frame, stored)
    replay_result = replay.build_replay(
        fixture["panel"], stored, fixture["sessions"], fixture["anchors"]
    )
    checks = replay_result["checks"]
    return {
        "mutation": mutation or "baseline",
        "all_replay_checks_pass": bool(all(checks.values())),
        "failed_checks": sorted(name for name, passed in checks.items() if not passed),
        "row_counts": replay_result["row_counts"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if STAGING_MARKER not in str(output):
        raise ValueError("refusing output outside the isolated alpha staging root")

    replay, replay_path = load_replay()
    mutations = [
        "c1_stock_variance_denominator",
        "c1_current_market_timing",
        "c2_missing_log",
        "c4_sign_flip",
        "eligibility_flip",
    ]
    with tempfile.TemporaryDirectory(prefix="idx-alpha-formula-challenger-") as temp:
        temp_root = Path(temp)
        fixture = make_fixture(temp_root)
        stored = temp_root / "stored_features.parquet"
        baseline = run_case(
            replay,
            fixture,
            stored,
            independent_reference(fixture["panel"], fixture["sessions"], fixture["anchors"]),
            None,
        )
        cases = [
            run_case(
                replay,
                fixture,
                stored,
                independent_reference(
                    fixture["panel"], fixture["sessions"], fixture["anchors"], mutation=mutation
                ),
                mutation,
            )
            for mutation in mutations
        ]

    mutation_detection = {
        case["mutation"]: not case["all_replay_checks_pass"] for case in cases
    }
    result = {
        "schema_version": "IDX_TRADE_FORMULA_MUTATION_CHALLENGER_V1",
        "experiment_id": "TOOLING-040",
        "status": "PASS_SEMANTIC_MUTATIONS_DETECTED"
        if baseline["all_replay_checks_pass"] and all(mutation_detection.values())
        else "FAIL_FORMULA_MUTATION_CHALLENGER",
        "scope": "OUTCOME_BLIND_SYNTHETIC_FIXTURES_ONLY",
        "reference": {
            "implementation": "independent_reference_inside_challenger",
            "constructor_replay_under_test": str(replay_path),
            "constructor_replay_sha256": sha256_file(replay_path),
        },
        "fixture": {
            "tickers": 3,
            "official_sessions": 150,
            "panel_rows": 450,
            "stored_feature_rows": 450,
        },
        "baseline": baseline,
        "mutation_cases": cases,
        "mutation_detection": mutation_detection,
        "trial_count": len(mutations) + 1,
        "limitations": [
            "Synthetic sensitivity does not prove correctness on the admitted panel.",
            "Mutation detection does not prove PIT, identity, corporate-action, capacity, or predictive validity.",
            "The challenger does not modify the constructor replay or packet verifier.",
        ],
        "reopen_trigger": "A separately reviewed independent oracle on a policy-authorized structural fixture or a new producer/verifier semantic contract.",
    }
    rendered = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] != "FAIL_FORMULA_MUTATION_CHALLENGER" else 1


if __name__ == "__main__":
    raise SystemExit(main())
