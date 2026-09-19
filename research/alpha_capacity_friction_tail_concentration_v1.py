"""Outcome-blind tail concentration and friction diagnostics.

This extends the fixed Top-30 structural review with explicit selected-slot
concentration, value/volume/dollar-turnover quartiles, and turnover-tail cost
burdens. It uses only the frozen panel, guarded Stage-A ranks, sessions, and
tradability anchors. It is not executable capacity, ADV, spread, queue, fill,
or profitability evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from alpha_stage_a_v2 import build_decision_universe, rolling


TOP_K = 30
FROZEN_SESSION_COUNT = 600
BASE_COST_BPS_PER_MATCHED_TURNOVER = 60.0
SENSITIVITY_COST_BPS_PER_MATCHED_TURNOVER = 110.0
SCORE_COLUMNS = {
    "C1": "rank_C1_residual_reversal_5_v1",
    "C2": "rank_C2_participation_confirmation_5_v1",
    "C4": "rank_C4_path_efficiency_reversal_20_v1",
    "H-LIQ-01": "HLIQ01_variability_log_turnover_20_v1",
    "H-VOL-01": "H_VOL_01_compression_5v60_v1",
    "H-EXC-02": "H_EXC_02_bounded_excursion_balance_5_v1",
}
EXPECTED_HASHES = {
    "panel": "25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e",
    "features": "aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4",
    "sessions": "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a",
    "anchors": "33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e",
}
EXTERNAL_STAGE_ROOT = Path(r"D:\Documents\Project\idx-alpha-available-data-staging-20260919").resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def quantile_summary(values: pd.Series) -> dict[str, float | int | None]:
    numeric = pd.to_numeric(values, errors="coerce")
    numeric = numeric[np.isfinite(numeric)]
    if numeric.empty:
        return {"count": 0, "mean": None, "median": None, "q95": None, "q99": None, "max": None}
    return {
        "count": int(len(numeric)),
        "mean": finite(numeric.mean()),
        "median": finite(numeric.median()),
        "q95": finite(numeric.quantile(0.95)),
        "q99": finite(numeric.quantile(0.99)),
        "max": finite(numeric.max()),
    }


def top_selection(frame: pd.DataFrame, score_column: str) -> pd.DataFrame:
    eligible = frame["eligible_decision_universe"].astype(bool)
    score = pd.to_numeric(frame[score_column], errors="coerce")
    valid = eligible & score.notna() & np.isfinite(score)
    rows = frame.loc[valid].copy()
    rows[score_column] = score.loc[valid]
    rows = rows.sort_values(["date", score_column, "ticker"], ascending=[True, False, True], kind="mergesort")
    return rows.groupby("date", sort=False, group_keys=False).head(TOP_K).copy()


def selection_sets(selection: pd.DataFrame) -> dict[pd.Timestamp, set[str]]:
    return {
        pd.Timestamp(date): set(group["ticker"].astype(str))
        for date, group in selection.groupby("date", sort=True)
    }


def turnover_summary(sets: dict[pd.Timestamp, set[str]], session_dates: list[pd.Timestamp]) -> dict[str, object]:
    index = {date: number for number, date in enumerate(session_dates)}
    dates = sorted(sets)
    values: list[float] = []
    for previous, current in zip(dates, dates[1:]):
        if index.get(current) != index.get(previous, -2) + 1:
            continue
        overlap = len(sets[previous] & sets[current])
        values.append(float(1.0 - overlap / TOP_K))
    series = pd.Series(values, dtype="float64")
    burden = {
        "base_60bps": {
            "mean": finite(series.mean() * BASE_COST_BPS_PER_MATCHED_TURNOVER) if not series.empty else None,
            "q95": finite(series.quantile(0.95) * BASE_COST_BPS_PER_MATCHED_TURNOVER) if not series.empty else None,
            "q99": finite(series.quantile(0.99) * BASE_COST_BPS_PER_MATCHED_TURNOVER) if not series.empty else None,
            "max": finite(series.max() * BASE_COST_BPS_PER_MATCHED_TURNOVER) if not series.empty else None,
        },
        "sensitivity_110bps": {
            "mean": finite(series.mean() * SENSITIVITY_COST_BPS_PER_MATCHED_TURNOVER) if not series.empty else None,
            "q95": finite(series.quantile(0.95) * SENSITIVITY_COST_BPS_PER_MATCHED_TURNOVER) if not series.empty else None,
            "q99": finite(series.quantile(0.99) * SENSITIVITY_COST_BPS_PER_MATCHED_TURNOVER) if not series.empty else None,
            "max": finite(series.max() * SENSITIVITY_COST_BPS_PER_MATCHED_TURNOVER) if not series.empty else None,
        },
    }
    return {
        "observations": int(len(series)),
        "one_way_turnover": quantile_summary(series),
        "friction_burden_bps_per_nav": burden,
        "definition": "1 - consecutive Top-30 name overlap / 30; adjacent official sessions only",
    }


def add_quartile_labels(frame: pd.DataFrame, column: str, output: str) -> pd.DataFrame:
    valid = frame["eligible_decision_universe"].astype(bool)
    numeric = pd.to_numeric(frame[column], errors="coerce")
    valid &= numeric.notna() & np.isfinite(numeric) & numeric.gt(0)
    labels = pd.Series(pd.NA, index=frame.index, dtype="Int64")
    for _, group in frame.loc[valid].groupby("date", sort=True):
        values = pd.to_numeric(group[column], errors="coerce")
        ranks = values.rank(method="first", pct=True)
        labels.loc[group.index] = np.clip(np.ceil(ranks * 4.0), 1, 4).astype("int64")
    result = frame[["ticker", "date"]].copy()
    result[output] = labels
    return result


def bucket_diagnostics(selection: pd.DataFrame, bucket_map: pd.DataFrame, label: str) -> dict[str, object]:
    joined = selection[["ticker", "date"]].merge(bucket_map, on=["ticker", "date"], how="left", validate="one_to_one")
    bucketable = joined[label].notna()
    counts = joined.loc[bucketable, label].value_counts().sort_index()
    total = int(len(joined))
    bucketable_count = int(bucketable.sum())
    shares = {
        str(int(key)): finite(value / bucketable_count) if bucketable_count else None
        for key, value in counts.items()
    }
    return {
        "selected_slots": total,
        "bucketable_slots": bucketable_count,
        "bucketable_share_of_selected": finite(bucketable_count / total) if total else None,
        "selected_slot_share_by_quartile": shares,
        "interpretation": "slot fraction among bucketable selected rows; not notional/value weighted",
    }


def concentration(selection: pd.DataFrame) -> dict[str, object]:
    counts = selection["ticker"].astype(str).value_counts()
    total = int(len(selection))
    shares = counts / total if total else pd.Series(dtype="float64")
    hhi = float((shares * shares).sum()) if total else None
    return {
        "selected_slots": total,
        "unique_names": int(len(counts)),
        "top_1_slot_share": finite(shares.head(1).sum()) if total else None,
        "top_10_slot_share": finite(shares.head(10).sum()) if total else None,
        "hhi": finite(hhi),
        "effective_names_1_over_hhi": finite(1.0 / hhi) if hhi and hhi > 0 else None,
        "interpretation": "name-slot concentration over the fixed selected history; not executable capacity",
    }


def build_scores(raw: pd.DataFrame) -> pd.DataFrame:
    result = raw.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True).copy()
    positive = (
        result["close"].gt(0) & result["volume"].gt(0)
        & np.isfinite(result["close"]) & np.isfinite(result["volume"])
    )
    result["dollar_turnover"] = (result["close"] * result["volume"]).where(positive)
    result["log_dollar_turnover"] = np.log(result["dollar_turnover"].where(result["dollar_turnover"].gt(0)))
    result["HLIQ01_variability_log_turnover_20_v1"] = rolling(result, "log_dollar_turnover", 20, "std")

    range_valid = (
        result["high"].gt(0) & result["low"].gt(0) & result["close"].gt(0)
        & np.isfinite(result["high"]) & np.isfinite(result["low"]) & np.isfinite(result["close"])
        & result["high"].ge(result["low"])
    )
    result["range_pct"] = ((result["high"] - result["low"]) / result["close"]).where(range_valid)
    short_range = rolling(result, "range_pct", 5, "median")
    long_range = rolling(result, "range_pct", 60, "median")
    ratio = short_range / long_range
    result["H_VOL_01_compression_5v60_v1"] = (-np.log(ratio.where(ratio.gt(0)))).where(np.isfinite(ratio))

    result["prev_close"] = result.groupby("ticker", sort=False)["close"].shift(1)
    excursion_valid = (
        result["high"].gt(0) & result["low"].gt(0) & result["prev_close"].gt(0)
        & np.isfinite(result["high"]) & np.isfinite(result["low"]) & np.isfinite(result["prev_close"])
        & result["high"].ge(result["low"])
    )
    up = (result["high"] - result["prev_close"]).abs()
    down = (result["low"] - result["prev_close"]).abs()
    denominator = up + down
    daily_balance = ((up - down) / denominator).where(excursion_valid & denominator.gt(0))
    result["bounded_daily_balance"] = daily_balance
    result["H_EXC_02_bounded_excursion_balance_5_v1"] = rolling(result, "bounded_daily_balance", 5, "median")
    return result


def candidate_result(selection: pd.DataFrame, score_column: str, bucket_maps: dict[str, pd.DataFrame], session_dates: list[pd.Timestamp]) -> dict[str, object]:
    sets = selection_sets(selection)
    return {
        "score_column": score_column,
        "top30_dates": int(selection["date"].nunique()),
        "selected_slots": int(len(selection)),
        "concentration": concentration(selection),
        "turnover": turnover_summary(sets, session_dates),
        "buckets": {
            name: bucket_diagnostics(selection, bucket_maps[name], name)
            for name in ["market_value_quartile", "raw_volume_quartile", "dollar_turnover_quartile"]
        },
        "capacity_unit": {
            "regular_market_value": "panel field; assumed IDR by source naming; no executable-capacity authority",
            "volume": "panel field; unit semantics not independently admitted",
            "dollar_turnover": "close * volume; unit semantics inherit panel fields and are not an ADV substitute",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repo-head", required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if EXTERNAL_STAGE_ROOT not in output.parents:
        raise ValueError("output must remain inside the isolated external staging root")

    paths = {"panel": args.panel, "features": args.features, "sessions": args.sessions, "anchors": args.anchors}
    source_hashes = {name: sha256_file(path) for name, path in paths.items()}
    if source_hashes != EXPECTED_HASHES:
        raise ValueError(f"input hash mismatch: {source_hashes}")

    sessions = pd.read_csv(args.sessions, usecols=["date"])
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    sessions = sessions.drop_duplicates("date").sort_values("date", kind="mergesort").reset_index(drop=True)
    frozen_sessions = sessions.tail(FROZEN_SESSION_COUNT).copy()
    session_dates = [pd.Timestamp(value) for value in frozen_sessions["date"]]

    panel_columns = ["ticker", "date", "high", "low", "close", "volume", "regular_market_value"]
    raw = pd.read_parquet(args.panel, columns=panel_columns)
    raw["ticker"] = raw["ticker"].astype("string")
    raw["date"] = pd.to_datetime(raw["date"], errors="raise").dt.normalize()
    for column in panel_columns[2:]:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")
    if raw.duplicated(["ticker", "date"]).any():
        raise ValueError("panel duplicate ticker/date keys")

    universe, universe_stats = build_decision_universe(raw[["ticker", "date", "regular_market_value"]], args.sessions, args.anchors)
    scored = build_scores(universe.merge(raw, on=["ticker", "date"], how="left", validate="one_to_one"))
    scored = scored[scored["date"].isin(set(session_dates))].copy()

    feature_columns = [
        "ticker",
        "date",
        "eligible_decision_universe",
        SCORE_COLUMNS["C1"],
        SCORE_COLUMNS["C2"],
        SCORE_COLUMNS["C4"],
    ]
    features = pd.read_parquet(args.features, columns=feature_columns)
    features["ticker"] = features["ticker"].astype("string")
    features["date"] = pd.to_datetime(features["date"], errors="raise").dt.normalize()
    if features.duplicated(["ticker", "date"]).any():
        raise ValueError("feature duplicate ticker/date keys")
    eligibility = features[["ticker", "date", "eligible_decision_universe"]].merge(
        universe[["ticker", "date", "eligible_decision_universe"]],
        on=["ticker", "date"], how="left", suffixes=("_stored", "_recomputed"), validate="one_to_one",
    )
    if len(eligibility) != len(features):
        raise ValueError("feature/universe key closure failed")
    if not eligibility["eligible_decision_universe_stored"].fillna(False).astype(bool).equals(
        eligibility["eligible_decision_universe_recomputed"].fillna(False).astype(bool)
    ):
        raise ValueError("stored/recomputed eligibility mismatch")

    scored = scored.merge(
        features[["ticker", "date", "eligible_decision_universe", *[SCORE_COLUMNS[name] for name in ["C1", "C2", "C4"]]]],
        on=["ticker", "date"], how="left", suffixes=("_recomputed", "_stored"), validate="one_to_one",
    )
    scored["eligible_decision_universe"] = (
        scored["eligible_decision_universe_stored"].astype("boolean").fillna(False).astype(bool)
    )
    for name in ["C1", "C2", "C4"]:
        score = SCORE_COLUMNS[name]
        scored[score] = pd.to_numeric(scored[score], errors="coerce")
    for name in ["H-LIQ-01", "H-VOL-01", "H-EXC-02"]:
        scored.loc[~scored["eligible_decision_universe"], SCORE_COLUMNS[name]] = np.nan

    bucket_maps = {
        "market_value_quartile": add_quartile_labels(scored, "regular_market_value", "market_value_quartile"),
        "raw_volume_quartile": add_quartile_labels(scored, "volume", "raw_volume_quartile"),
        "dollar_turnover_quartile": add_quartile_labels(scored, "dollar_turnover", "dollar_turnover_quartile"),
    }
    candidates: dict[str, object] = {}
    for name, score_column in SCORE_COLUMNS.items():
        selection = top_selection(scored, score_column)
        candidates[name] = candidate_result(selection, score_column, bucket_maps, session_dates)

    result = {
        "status": "PASS_STRUCTURAL_ONLY",
        "stage": "L_CAPACITY_FRICTION_TAIL_CONCENTRATION",
        "repo_head": args.repo_head,
        "source_hashes": source_hashes,
        "code_sha256": sha256_file(Path(__file__)),
        "frozen_session_count": FROZEN_SESSION_COUNT,
        "frozen_window_start": session_dates[0].strftime("%Y-%m-%d"),
        "frozen_window_end": session_dates[-1].strftime("%Y-%m-%d"),
        "top_k": TOP_K,
        "candidate_set": list(SCORE_COLUMNS),
        "universe": universe_stats,
        "friction_contract": {
            "base_matched_turnover_bps": BASE_COST_BPS_PER_MATCHED_TURNOVER,
            "sensitivity_matched_turnover_bps": SENSITIVITY_COST_BPS_PER_MATCHED_TURNOVER,
            "turnover_cost_rule": "one-way turnover multiplied by fixed matched-turnover burden; not realized return or fill evidence",
        },
        "candidates": candidates,
        "scope": {
            "outcome_accessed": False,
            "target_accessed": False,
            "provider_accessed": False,
            "incumbent_score_accessed": False,
            "canonical_mutation": False,
            "candidate_id_created": False,
            "executable_capacity_admitted": False,
            "pit_price_basis_admitted": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": result["status"], "output_sha256": sha256_file(output), "code_sha256": result["code_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
