"""Outcome-blind calendar-year mechanics for the fixed C1-C4 ranks.

This is a descriptive structural audit. It reports fixed Top-30 turnover,
selection persistence, slot concentration, and rank displacement by natural
calendar year. It does not select an era, change eligibility, or read outcomes.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


CANDIDATES = {
    "C1": "C1_residual_reversal_5_v1",
    "C2": "C2_participation_confirmation_5_v1",
    "C3": "C3_financial_quality_growth_v1",
    "C4": "C4_path_efficiency_reversal_20_v1",
}
TOP_K = 30
FEATURE_COLUMNS = [
    "ticker",
    "date",
    "eligible_decision_universe",
    *(f"rank_{column}" for column in CANDIDATES.values()),
]
FORBIDDEN_INPUT_MARKERS = ("target", "forward", "label", "outcome", "vault", "counter")


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


def quantile_summary(values: list[float] | pd.Series) -> dict[str, float | int | None]:
    series = pd.Series(values, dtype="float64").replace([np.inf, -np.inf], np.nan).dropna()
    if series.empty:
        return {"count": 0, "min": None, "q25": None, "median": None, "q75": None, "q95": None, "max": None, "mean": None, "std": None}
    return {
        "count": int(len(series)),
        "min": finite_float(series.min()),
        "q25": finite_float(series.quantile(0.25)),
        "median": finite_float(series.median()),
        "q75": finite_float(series.quantile(0.75)),
        "q95": finite_float(series.quantile(0.95)),
        "max": finite_float(series.max()),
        "mean": finite_float(series.mean()),
        "std": finite_float(series.std(ddof=1)),
    }


def concentration(selection: pd.DataFrame) -> dict[str, float | int | None]:
    if selection.empty:
        return {
            "selection_slots": 0,
            "unique_tickers": 0,
            "top10_slot_share": None,
            "largest_ticker_slot_share": None,
            "hhi": None,
            "effective_number_of_names": None,
        }
    counts = selection["ticker"].astype(str).value_counts()
    shares = counts / len(selection)
    hhi = float((shares * shares).sum())
    return {
        "selection_slots": int(len(selection)),
        "unique_tickers": int(len(counts)),
        "top10_slot_share": finite_float(counts.head(10).sum() / len(selection)),
        "largest_ticker_slot_share": finite_float(counts.iloc[0] / len(selection)),
        "hhi": finite_float(hhi),
        "effective_number_of_names": finite_float(1.0 / hhi) if hhi > 0 else None,
    }


def persistence_lengths(selection: pd.DataFrame) -> list[int]:
    lengths: list[int] = []
    for _, group in selection.groupby("ticker", sort=False):
        indices = sorted(set(int(value) for value in group["session_index"]))
        if not indices:
            continue
        start = previous = indices[0]
        for value in indices[1:]:
            if value != previous + 1:
                lengths.append(previous - start + 1)
                start = value
            previous = value
        lengths.append(previous - start + 1)
    return lengths


def select_top30(frame: pd.DataFrame, candidate: str, top_k: int) -> dict[pd.Timestamp, set[str]]:
    rank_column = f"rank_{CANDIDATES[candidate]}"
    valid = frame.loc[
        frame["eligible_decision_universe"] & frame[rank_column].notna(),
        ["ticker", "date", rank_column],
    ].copy()
    selections: dict[pd.Timestamp, set[str]] = {}
    for date, group in valid.groupby("date", sort=True):
        if len(group) < top_k:
            continue
        ordered = group.sort_values([rank_column, "ticker"], ascending=[False, True], kind="mergesort")
        selections[pd.Timestamp(date)] = set(ordered.head(top_k)["ticker"].astype(str))
    return selections


def selection_frame(frame: pd.DataFrame, candidate: str, selections: dict[pd.Timestamp, set[str]], session_index: dict[pd.Timestamp, int]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    rank_column = f"rank_{CANDIDATES[candidate]}"
    for date, tickers in selections.items():
        daily = frame.loc[frame["date"].eq(date) & frame["ticker"].astype(str).isin(tickers), ["ticker", rank_column]]
        for row in daily.itertuples(index=False):
            rows.append({
                "date": date,
                "ticker": str(row[0]),
                "rank": float(row[1]),
                "session_index": int(session_index[date]),
            })
    return pd.DataFrame(rows, columns=["date", "ticker", "rank", "session_index"])


def rank_displacement_by_year(frame: pd.DataFrame, candidate: str, session_index: dict[pd.Timestamp, int]) -> dict[str, dict[str, float | int | None]]:
    rank_column = f"rank_{CANDIDATES[candidate]}"
    valid = frame.loc[
        frame["eligible_decision_universe"] & frame[rank_column].notna(),
        ["ticker", "date", rank_column],
    ].copy()
    valid["session_index"] = valid["date"].map(session_index).astype(int)
    valid["year"] = valid["date"].dt.year.astype(int)
    valid = valid.sort_values(["ticker", "session_index"], kind="mergesort")
    valid["previous_session"] = valid.groupby("ticker", sort=False)["session_index"].shift(1)
    valid["previous_rank"] = valid.groupby("ticker", sort=False)[rank_column].shift(1)
    consecutive = valid.loc[valid["session_index"].eq(valid["previous_session"] + 1)].copy()
    consecutive["displacement"] = (consecutive[rank_column] - consecutive["previous_rank"]).abs()
    return {
        str(year): quantile_summary(group["displacement"])
        for year, group in consecutive.groupby("year", sort=True)
    }


def summarize(features: pd.DataFrame, official_dates: pd.Series | pd.Index, top_k: int = TOP_K) -> dict[str, Any]:
    missing = set(FEATURE_COLUMNS).difference(features.columns)
    if missing:
        raise ValueError(f"feature artifact missing columns: {sorted(missing)}")
    frame = features[FEATURE_COLUMNS].copy()
    frame["ticker"] = frame["ticker"].astype("string")
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    if frame.duplicated(["ticker", "date"]).any():
        raise ValueError("feature artifact has duplicate ticker/date keys")
    sessions = pd.to_datetime(official_dates, errors="raise")
    sessions = pd.Series(sessions).dt.normalize().drop_duplicates().sort_values().reset_index(drop=True)
    official = pd.Index(sessions, name="date")
    if not frame["date"].isin(official).all():
        raise ValueError("feature dates fall outside official session calendar")
    session_index = {date: index for index, date in enumerate(official)}
    frame["eligible_decision_universe"] = frame["eligible_decision_universe"].fillna(False).astype(bool)
    frame["year"] = frame["date"].dt.year.astype(int)
    years = sorted(frame["year"].unique().tolist())
    candidate_eras: dict[str, Any] = {}
    year_sets: dict[str, dict[str, set[str]]] = {}
    for candidate in CANDIDATES:
        rank_column = f"rank_{CANDIDATES[candidate]}"
        finite = frame["eligible_decision_universe"] & frame[rank_column].notna()
        selections = select_top30(frame, candidate, top_k)
        selected = selection_frame(frame, candidate, selections, session_index)
        year_sets[candidate] = {}
        displacement = rank_displacement_by_year(frame, candidate, session_index)
        candidate_eras[candidate] = {}
        for year in years:
            eligible_year = frame.loc[frame["year"].eq(year) & frame["eligible_decision_universe"]]
            finite_year = eligible_year.loc[eligible_year[rank_column].notna()]
            year_dates = sorted(date for date in selections if date.year == year)
            year_selection = selected.loc[selected["date"].dt.year.eq(year)].copy()
            year_sets[candidate][str(year)] = set(year_selection["ticker"].astype(str))
            turnovers: list[float] = []
            overlaps: list[int] = []
            for previous_date, current_date in zip(year_dates, year_dates[1:]):
                if session_index[current_date] != session_index[previous_date] + 1:
                    continue
                previous = selections[previous_date]
                current = selections[current_date]
                overlap = len(previous & current)
                overlaps.append(overlap)
                turnovers.append(1.0 - overlap / top_k)
            candidate_eras[candidate][str(year)] = {
                "eligible_rows": int(len(eligible_year)),
                "finite_rows": int(len(finite_year)),
                "finite_coverage": finite_float(len(finite_year) / len(eligible_year)) if len(eligible_year) else None,
                "finite_dates": int(finite_year["date"].nunique()),
                "usable_top30_dates": int(len(year_dates)),
                "turnover": quantile_summary(turnovers),
                "consecutive_top30_overlap_count": quantile_summary(overlaps),
                "persistence_sessions": quantile_summary(persistence_lengths(year_selection)),
                "concentration": concentration(year_selection),
                "mean_abs_rank_displacement": displacement.get(str(year), quantile_summary([])),
            }
    between_era: dict[str, dict[str, dict[str, float | int | None]]] = {}
    for candidate in CANDIDATES:
        between_era[candidate] = {}
        for left, right in itertools.combinations(years, 2):
            left_set = year_sets[candidate][str(left)]
            right_set = year_sets[candidate][str(right)]
            union = left_set | right_set
            intersection = left_set & right_set
            between_era[candidate][f"{left}__{right}"] = {
                "left_selected_tickers": int(len(left_set)),
                "right_selected_tickers": int(len(right_set)),
                "intersection": int(len(intersection)),
                "union": int(len(union)),
                "comparable": bool(left_set and right_set),
                "jaccard": finite_float(len(intersection) / len(union)) if left_set and right_set else None,
            }
    return {
        "status": "PASS_STRUCTURAL_ERA_MECHANICS",
        "scope": "Fixed Top-30 calendar-year mechanics; no era, policy, or candidate selected.",
        "top_k": top_k,
        "calendar": {
            "official_session_count": int(len(official)),
            "official_min": str(official.min().date()) if len(official) else None,
            "official_max": str(official.max().date()) if len(official) else None,
            "year_rule": "calendar year derived from the official session date",
            "turnover_rule": "only consecutive official sessions within the same calendar year",
        },
        "candidate_eras": candidate_eras,
        "between_era_selection_overlap": between_era,
        "admission": {
            "policy_selected": False,
            "era_admitted": False,
            "candidate_status_changed": False,
            "protected_boundary": "CLOSED",
        },
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")
    for path in (args.features, args.sessions):
        if any(marker in str(path).lower() for marker in FORBIDDEN_INPUT_MARKERS):
            raise ValueError(f"refusing input path with protected-data marker: {path}")
    features = pd.read_parquet(args.features, columns=FEATURE_COLUMNS)
    sessions = pd.read_csv(args.sessions, usecols=["date"])
    result = summarize(features, sessions["date"])
    result["inputs"] = {
        "features": {"path": str(args.features), "sha256": sha256_file(args.features), "rows": int(len(features))},
        "official_sessions": {"path": str(args.sessions), "sha256": sha256_file(args.sessions)},
    }
    result["code_sha256"] = sha256_file(Path(__file__).resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
