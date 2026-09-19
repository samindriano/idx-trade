"""Outcome-blind structural readiness for fixed C1/C2/C4 combinations.

This is a bounded Phase M/L study. It uses equal-weight averages of the
already frozen cross-sectional ranks and fixed friction scenarios. It does not
fit weights, read outcomes, compare predictive performance, or create a new
candidate ID.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


FROZEN_SESSION_COUNT = 600
TOP_KS = (10, 20, 30, 50)
COMPONENTS = {
    "C1": "rank_C1_residual_reversal_5_v1",
    "C2": "rank_C2_participation_confirmation_5_v1",
    "C4": "rank_C4_path_efficiency_reversal_20_v1",
}
COMBINATIONS = {
    "C1_C2_EW": ("C1", "C2"),
    "C1_C4_EW": ("C1", "C4"),
    "C2_C4_EW": ("C2", "C4"),
    "C1_C2_C4_EW": ("C1", "C2", "C4"),
}
FRICTION_SCENARIOS = {
    "LOW": {
        "buy_fee_bps": 10.0,
        "sell_fee_bps": 20.0,
        "slippage_bps_per_side": 5.0,
    },
    "BASE": {
        "buy_fee_bps": 15.0,
        "sell_fee_bps": 25.0,
        "slippage_bps_per_side": 10.0,
    },
    "STRESS": {
        "buy_fee_bps": 40.0,
        "sell_fee_bps": 50.0,
        "slippage_bps_per_side": 10.0,
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite_float(value: object) -> float | None:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    return converted if np.isfinite(converted) else None


def quantile_summary(values: list[float]) -> dict[str, float | int | None]:
    series = pd.Series(values, dtype="float64")
    series = series.replace([np.inf, -np.inf], np.nan).dropna()
    if series.empty:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "q10": None,
            "q90": None,
            "max": None,
        }
    return {
        "count": int(len(series)),
        "mean": finite_float(series.mean()),
        "median": finite_float(series.median()),
        "q10": finite_float(series.quantile(0.10)),
        "q90": finite_float(series.quantile(0.90)),
        "max": finite_float(series.max()),
    }


def scenario_contracts() -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for name, values in FRICTION_SCENARIOS.items():
        matched = (
            values["buy_fee_bps"]
            + values["sell_fee_bps"]
            + 2.0 * values["slippage_bps_per_side"]
        )
        result[name] = {**values, "matched_turnover_bps": matched}
    return result


def build_selection(
    frame: pd.DataFrame,
    score_column: str,
    top_k: int,
) -> dict[pd.Timestamp, set[str]]:
    eligible = frame["eligible_decision_universe"].astype(bool)
    score = pd.to_numeric(frame[score_column], errors="coerce")
    finite = eligible & score.notna() & np.isfinite(score)
    rows = frame.loc[finite, ["ticker", "date", score_column]].copy()
    rows[score_column] = pd.to_numeric(rows[score_column], errors="coerce")
    result: dict[pd.Timestamp, set[str]] = {}
    for date, group in rows.groupby("date", sort=True):
        selected = group.sort_values(
            [score_column, "ticker"], ascending=[False, True], kind="mergesort"
        ).head(top_k)
        if len(selected) == top_k:
            result[pd.Timestamp(date)] = set(selected["ticker"].astype(str))
    return result


def consecutive_turnovers(
    selections: dict[pd.Timestamp, set[str]],
    session_index: dict[pd.Timestamp, int],
    top_k: int,
) -> list[float]:
    dates = sorted(selections)
    values: list[float] = []
    for previous, current in zip(dates, dates[1:]):
        if session_index.get(current) != session_index.get(previous, -2) + 1:
            continue
        values.append(1.0 - len(selections[previous] & selections[current]) / top_k)
    return values


def persistence_lengths(
    selections: dict[pd.Timestamp, set[str]],
    session_index: dict[pd.Timestamp, int],
) -> list[int]:
    by_ticker: dict[str, list[int]] = {}
    for date, names in selections.items():
        for ticker in names:
            by_ticker.setdefault(ticker, []).append(session_index[date])
    lengths: list[int] = []
    for indices in by_ticker.values():
        ordered = sorted(set(indices))
        if not ordered:
            continue
        start = previous = ordered[0]
        for current in ordered[1:]:
            if current != previous + 1:
                lengths.append(previous - start + 1)
                start = current
            previous = current
        lengths.append(previous - start + 1)
    return lengths


def selected_exposure(
    frame: pd.DataFrame,
    selections: dict[pd.Timestamp, set[str]],
    score_column: str,
    top_k: int,
) -> dict[str, object]:
    selected_rows: list[pd.DataFrame] = []
    for date, names in selections.items():
        group = frame[(frame["date"] == date) & frame["ticker"].isin(names)].copy()
        group = group.sort_values(
            [score_column, "ticker"], ascending=[False, True], kind="mergesort"
        ).head(top_k)
        selected_rows.append(group)
    if not selected_rows:
        return {
            "selected_slots": 0,
            "bottom_value_quartile_share": None,
            "bottom_volume_quartile_share": None,
            "top10_ticker_slot_share": None,
            "largest_ticker_slot_share": None,
        }
    selected = pd.concat(selected_rows, ignore_index=True)
    slots = len(selected)
    counts = selected["ticker"].astype(str).value_counts()
    return {
        "selected_slots": int(slots),
        "bottom_value_quartile_share": finite_float(
            (selected["value_percentile"] <= 0.25).mean()
        ),
        "bottom_volume_quartile_share": finite_float(
            (selected["volume_percentile"] <= 0.25).mean()
        ),
        "top10_ticker_slot_share": finite_float(counts.head(10).sum() / slots),
        "largest_ticker_slot_share": finite_float(counts.iloc[0] / slots),
    }


def daily_rank_correlations(
    frame: pd.DataFrame,
    score_column: str,
    component_columns: list[str],
) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    for component in component_columns:
        values: list[float] = []
        for _, group in frame.groupby("date", sort=True):
            rows = group[[score_column, component]].replace([np.inf, -np.inf], np.nan).dropna()
            if len(rows) < 20:
                continue
            correlation = rows[score_column].corr(rows[component], method="spearman")
            if pd.notna(correlation):
                values.append(float(correlation))
        result[component] = finite_float(pd.Series(values, dtype="float64").mean())
    return result


def combination_metrics(
    frame: pd.DataFrame,
    name: str,
    components: tuple[str, ...],
    session_index: dict[pd.Timestamp, int],
    scenario_map: dict[str, dict[str, float]],
) -> dict[str, object]:
    score_column = f"combo_{name}"
    selections_by_k = {
        str(top_k): build_selection(frame, score_column, top_k) for top_k in TOP_KS
    }
    top30 = selections_by_k["30"]
    turnover = consecutive_turnovers(top30, session_index, 30)
    component_selections = {
        component: build_selection(frame, COMPONENTS[component], 30)
        for component in components
    }
    common_dates = sorted(set(top30).intersection(*[set(value) for value in component_selections.values()]))
    overlap: dict[str, float | None] = {}
    low_overlap: dict[str, float | None] = {}
    for component, selections in component_selections.items():
        values = [
            len(top30[date] & selections[date]) / 30.0
            for date in common_dates
        ]
        overlap[component] = finite_float(pd.Series(values, dtype="float64").mean())
        low_overlap[component] = finite_float(
            pd.Series(values, dtype="float64").lt(0.50).mean()
        )
    persistence = persistence_lengths(top30, session_index)
    exposure = selected_exposure(frame, top30, score_column, 30)
    metrics: dict[str, object] = {
        "formula": "mean(" + ", ".join(COMPONENTS[component] for component in components) + ")",
        "components": list(components),
        "normalization": "already-frozen cross-sectional rank columns; equal weights only",
        "top_k_dates": {key: int(len(value)) for key, value in selections_by_k.items()},
        "top_k_turnover": {},
        "top30_component_overlap": overlap,
        "top30_component_low_overlap_frequency_lt_50pct": low_overlap,
        "top30_common_component_dates": int(len(common_dates)),
        "daily_spearman_vs_components": daily_rank_correlations(
            frame, score_column, [COMPONENTS[component] for component in components]
        ),
        "top30_turnover": quantile_summary(turnover),
        "top30_persistence_sessions": quantile_summary([float(value) for value in persistence]),
        "exposure": exposure,
    }
    for top_k, selections in selections_by_k.items():
        top_k_int = int(top_k)
        turnover_values = consecutive_turnovers(selections, session_index, top_k_int)
        metrics["top_k_turnover"][top_k] = quantile_summary(turnover_values)
    turnover_mean = metrics["top30_turnover"]["mean"]
    for scenario, values in scenario_map.items():
        metrics.setdefault("friction_burden_bps_per_nav", {})[scenario] = (
            finite_float(turnover_mean * values["matched_turnover_bps"])
            if turnover_mean is not None
            else None
        )
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    feature_columns = [
        "ticker",
        "date",
        "eligible_decision_universe",
        *COMPONENTS.values(),
    ]
    features = pd.read_parquet(args.features, columns=feature_columns)
    features["date"] = pd.to_datetime(features["date"], errors="raise").dt.normalize()
    panel = pd.read_parquet(
        args.panel,
        columns=["ticker", "date", "regular_market_value", "volume"],
    )
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    if features.duplicated(["ticker", "date"]).any():
        raise ValueError("features contain duplicate ticker/date keys")
    if panel.duplicated(["ticker", "date"]).any():
        raise ValueError("panel contains duplicate ticker/date keys")

    sessions = pd.read_csv(args.sessions, usecols=["date"])
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    sessions = sessions.drop_duplicates("date").sort_values("date", kind="mergesort").reset_index(drop=True)
    if len(sessions) < FROZEN_SESSION_COUNT:
        raise ValueError("official session source is shorter than frozen window")
    frozen_sessions = sessions.tail(FROZEN_SESSION_COUNT).copy().reset_index(drop=True)
    frozen_dates = set(frozen_sessions["date"])
    features = features[features["date"].isin(frozen_dates)].copy()
    frame = features.merge(
        panel,
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
        indicator=True,
    )
    if not frame["_merge"].eq("both").all():
        raise ValueError("feature/panel key closure failed")
    frame = frame.drop(columns=["_merge"])
    for column in COMPONENTS.values():
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["value_percentile"] = frame.groupby("date")["regular_market_value"].rank(
        pct=True, method="average"
    )
    frame["volume_percentile"] = frame.groupby("date")["volume"].rank(
        pct=True, method="average"
    )
    for name, components in COMBINATIONS.items():
        columns = [COMPONENTS[component] for component in components]
        frame[f"combo_{name}"] = frame[columns].mean(axis=1, skipna=False)

    session_index = dict(zip(frozen_sessions["date"], frozen_sessions.index, strict=True))
    scenario_map = scenario_contracts()
    combinations = {
        name: combination_metrics(frame, name, components, session_index, scenario_map)
        for name, components in COMBINATIONS.items()
    }
    result = {
        "status": "PASS_STRUCTURAL_ONLY",
        "stage": "M_COMBINATION_READINESS_L_IMPLEMENTATION_ECONOMICS",
        "outcome_accessed": False,
        "provider_accessed": False,
        "target_accessed": False,
        "incumbent_score_accessed": False,
        "candidate_id_created": False,
        "frozen_session_count": FROZEN_SESSION_COUNT,
        "frozen_window_start": frozen_sessions["date"].min().strftime("%Y-%m-%d"),
        "frozen_window_end": frozen_sessions["date"].max().strftime("%Y-%m-%d"),
        "combination_budget": {
            "exact_set": list(COMBINATIONS),
            "weight_policy": "equal weights only",
            "no_weight_optimization": True,
            "no_new_candidate_ids": True,
        },
        "friction_scenarios": scenario_map,
        "source_hashes": {
            "features": sha256_file(args.features),
            "panel": sha256_file(args.panel),
            "official_sessions": sha256_file(args.sessions),
        },
        "code_sha256": sha256_file(Path(__file__)),
        "combinations": combinations,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
