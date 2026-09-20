"""Outcome-blind universe-breadth versus Top-30 turnover mechanics."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


TOP_K = 30
CANDIDATES = {
    "C1": "rank_C1_residual_reversal_5_v1",
    "C2": "rank_C2_participation_confirmation_5_v1",
    "C3": "rank_C3_financial_quality_growth_v1",
    "C4": "rank_C4_path_efficiency_reversal_20_v1",
}
FEATURE_COLUMNS = ["ticker", "date", "eligible_decision_universe", *CANDIDATES.values()]
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


def quantile_summary(values: list[float]) -> dict[str, float | int | None]:
    series = pd.Series(values, dtype="float64").replace([np.inf, -np.inf], np.nan).dropna()
    if series.empty:
        return {"count": 0, "mean": None, "median": None, "q10": None, "q90": None, "min": None, "max": None}
    return {
        "count": int(len(series)),
        "mean": finite_float(series.mean()),
        "median": finite_float(series.median()),
        "q10": finite_float(series.quantile(0.10)),
        "q90": finite_float(series.quantile(0.90)),
        "min": finite_float(series.min()),
        "max": finite_float(series.max()),
    }


def correlation_summary(left: list[float], right: list[float]) -> dict[str, float | int | None]:
    frame = pd.DataFrame({"left": left, "right": right}).replace([np.inf, -np.inf], np.nan).dropna()
    if len(frame) < 3:
        return {"pairs": int(len(frame)), "spearman": None}
    return {"pairs": int(len(frame)), "spearman": finite_float(frame["left"].corr(frame["right"], method="spearman"))}


def select_top30(frame: pd.DataFrame, candidate: str) -> dict[pd.Timestamp, set[str]]:
    score_column = CANDIDATES[candidate]
    valid = frame["eligible_decision_universe"].astype(bool) & frame[score_column].notna()
    rows = frame.loc[valid, ["ticker", "date", score_column]].copy()
    rows[score_column] = pd.to_numeric(rows[score_column], errors="coerce")
    rows = rows[np.isfinite(rows[score_column])]
    selections: dict[pd.Timestamp, set[str]] = {}
    for date, group in rows.groupby("date", sort=True):
        ordered = group.sort_values([score_column, "ticker"], ascending=[False, True], kind="mergesort")
        if len(ordered) >= TOP_K:
            selections[pd.Timestamp(date)] = set(ordered.head(TOP_K)["ticker"].astype(str))
    return selections


def support_maps(frame: pd.DataFrame, candidate: str) -> tuple[dict[pd.Timestamp, int], dict[pd.Timestamp, int]]:
    score_column = CANDIDATES[candidate]
    eligible = frame["eligible_decision_universe"].astype(bool)
    finite = eligible & frame[score_column].notna() & np.isfinite(pd.to_numeric(frame[score_column], errors="coerce"))
    eligible_counts = frame.loc[eligible].groupby("date")["ticker"].size().astype(int).to_dict()
    finite_counts = frame.loc[finite].groupby("date")["ticker"].size().astype(int).to_dict()
    return eligible_counts, finite_counts


def pair_metrics(
    selections: dict[pd.Timestamp, set[str]],
    eligible_counts: dict[pd.Timestamp, int],
    finite_counts: dict[pd.Timestamp, int],
    official_dates: list[pd.Timestamp],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for previous, current in zip(official_dates, official_dates[1:]):
        if previous.year != current.year or previous not in selections or current not in selections:
            continue
        previous_finite = finite_counts.get(previous)
        current_finite = finite_counts.get(current)
        if previous_finite is None or current_finite is None or previous_finite <= 0:
            continue
        turnover = 1.0 - len(selections[previous] & selections[current]) / TOP_K
        previous_eligible = eligible_counts.get(previous, 0)
        current_eligible = eligible_counts.get(current, 0)
        rows.append(
            {
                "from_date": previous,
                "to_date": current,
                "year": int(current.year),
                "from_eligible_count": float(previous_eligible),
                "to_eligible_count": float(current_eligible),
                "from_finite_count": float(previous_finite),
                "to_finite_count": float(current_finite),
                "finite_count_delta": float(current_finite - previous_finite),
                "abs_finite_count_delta": float(abs(current_finite - previous_finite)),
                "relative_finite_count_delta": float((current_finite - previous_finite) / previous_finite),
                "finite_share": float(current_finite / current_eligible) if current_eligible else np.nan,
                "turnover": float(turnover),
            }
        )
    return pd.DataFrame(rows)


def summarize_pairs(pairs: pd.DataFrame) -> dict[str, Any]:
    if pairs.empty:
        return {"pairs": 0, "turnover": quantile_summary([]), "finite_count": quantile_summary([]), "finite_share": quantile_summary([]), "correlations": {}}
    return {
        "pairs": int(len(pairs)),
        "turnover": quantile_summary(pairs["turnover"].tolist()),
        "finite_count": quantile_summary(pairs["to_finite_count"].tolist()),
        "finite_share": quantile_summary(pairs["finite_share"].tolist()),
        "correlations": {
            "to_finite_count_vs_turnover": correlation_summary(pairs["to_finite_count"].tolist(), pairs["turnover"].tolist()),
            "from_finite_count_vs_turnover": correlation_summary(pairs["from_finite_count"].tolist(), pairs["turnover"].tolist()),
            "abs_finite_count_delta_vs_turnover": correlation_summary(pairs["abs_finite_count_delta"].tolist(), pairs["turnover"].tolist()),
            "relative_finite_count_delta_vs_turnover": correlation_summary(pairs["relative_finite_count_delta"].tolist(), pairs["turnover"].tolist()),
        },
    }


def summarize(features: pd.DataFrame, official_dates: pd.Series | pd.Index) -> dict[str, Any]:
    frame = features.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    official = sorted(pd.to_datetime(pd.Series(official_dates), errors="raise").dt.normalize().drop_duplicates())
    candidates: dict[str, Any] = {}
    for candidate in CANDIDATES:
        selections = select_top30(frame, candidate)
        eligible_counts, finite_counts = support_maps(frame, candidate)
        pairs = pair_metrics(selections, eligible_counts, finite_counts, official)
        by_year = {
            str(year): summarize_pairs(group.copy())
            for year, group in pairs.groupby("year", sort=True)
        }
        candidates[candidate] = {
            "selection_dates": int(len(selections)),
            "eligible_count_by_date": quantile_summary([float(value) for value in eligible_counts.values()]),
            "finite_count_by_date": quantile_summary([float(value) for value in finite_counts.values()]),
            "pairs_same_calendar_year": summarize_pairs(pairs),
            "by_year": by_year,
        }
    return {
        "status": "PASS_STRUCTURAL_UNIVERSE_BREADTH_TURNOVER",
        "scope": "Outcome-blind fixed Top-30 turnover versus daily eligible and finite-support breadth; same-calendar-year adjacent official-session pairs only.",
        "top_k": TOP_K,
        "selection": "descending candidate rank with ascending ticker tie-break",
        "calendar": {
            "official_session_count": int(len(official)),
            "official_min": str(official[0].date()) if official else None,
            "official_max": str(official[-1].date()) if official else None,
        },
        "candidates": candidates,
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
        "features": {"path": str(args.features), "rows": int(len(features)), "sha256": sha256_file(args.features)},
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
