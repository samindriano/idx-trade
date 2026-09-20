"""Outcome-blind score-separation mechanics for the fixed C1-C4 ranks.

This audit asks whether fixed Top-30 selection has a thin or wide score edge
at the 30/31 boundary. It uses only the guarded Stage-A feature artifact and
official sessions. It does not read targets, forward returns, incumbent
scores, protected outcomes, or change any candidate/policy.
"""

from __future__ import annotations

import argparse
import hashlib
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
    *(CANDIDATES.values()),
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


def quantile_summary(values: pd.Series | list[float]) -> dict[str, float | int | None]:
    series = pd.Series(values, dtype="float64").replace([np.inf, -np.inf], np.nan).dropna()
    if series.empty:
        return {
            "count": 0,
            "min": None,
            "q25": None,
            "median": None,
            "q75": None,
            "q95": None,
            "max": None,
            "mean": None,
            "std": None,
        }
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


def correlation_summary(left: pd.Series, right: pd.Series) -> dict[str, float | int | None]:
    paired = pd.DataFrame({"left": left, "right": right}).replace([np.inf, -np.inf], np.nan).dropna()
    if len(paired) < 3 or paired["left"].nunique() < 2 or paired["right"].nunique() < 2:
        return {"pairs": int(len(paired)), "spearman": None, "pearson": None}
    return {
        "pairs": int(len(paired)),
        "spearman": finite_float(paired["left"].corr(paired["right"], method="spearman")),
        "pearson": finite_float(paired["left"].corr(paired["right"], method="pearson")),
    }


def prepare_frame(features: pd.DataFrame, official_dates: pd.Series | pd.Index) -> tuple[pd.DataFrame, pd.Index, dict[pd.Timestamp, int]]:
    missing = set(FEATURE_COLUMNS).difference(features.columns)
    if missing:
        raise ValueError(f"feature artifact missing columns: {sorted(missing)}")
    frame = features[FEATURE_COLUMNS].copy()
    frame["ticker"] = frame["ticker"].astype("string")
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    if frame.duplicated(["ticker", "date"]).any():
        raise ValueError("feature artifact has duplicate ticker/date keys")
    sessions = pd.Series(pd.to_datetime(official_dates, errors="raise"), dtype="datetime64[ns]")
    sessions = sessions.dt.normalize().drop_duplicates().sort_values().reset_index(drop=True)
    official = pd.Index(sessions, name="date")
    if not frame["date"].isin(official).all():
        raise ValueError("feature dates fall outside official session calendar")
    frame["eligible_decision_universe"] = frame["eligible_decision_universe"].fillna(False).astype(bool)
    return frame, official, {date: index for index, date in enumerate(official)}


def daily_separation(
    frame: pd.DataFrame,
    candidate: str,
    top_k: int,
    session_index: dict[pd.Timestamp, int],
) -> tuple[pd.DataFrame, dict[pd.Timestamp, set[str]]]:
    score_column = CANDIDATES[candidate]
    rank_column = f"rank_{score_column}"
    valid = frame.loc[
        frame["eligible_decision_universe"]
        & frame[score_column].notna()
        & frame[rank_column].notna(),
        ["ticker", "date", score_column, rank_column],
    ].copy()
    selections: dict[pd.Timestamp, set[str]] = {}
    records: list[dict[str, Any]] = []
    for date, group in valid.groupby("date", sort=True):
        ordered = group.sort_values([rank_column, "ticker"], ascending=[False, True], kind="mergesort")
        if len(ordered) < top_k + 1:
            continue
        scores = pd.to_numeric(group[score_column], errors="coerce").dropna()
        q25 = float(scores.quantile(0.25))
        q75 = float(scores.quantile(0.75))
        iqr = q75 - q25
        top = ordered.head(top_k)
        cutoff = float(top.iloc[-1][score_column])
        next_score = float(ordered.iloc[top_k][score_column])
        top1 = float(top.iloc[0][score_column])
        boundary_gap = cutoff - next_score
        records.append(
            {
                "date": pd.Timestamp(date),
                "year": int(pd.Timestamp(date).year),
                "finite_count": int(len(ordered)),
                "score_iqr": finite_float(iqr),
                "boundary_gap": finite_float(boundary_gap),
                "normalized_boundary_gap": finite_float(boundary_gap / iqr) if iqr > 0 else None,
                "top1_to_cutoff_gap": finite_float(top1 - cutoff),
                "normalized_top1_to_cutoff_gap": finite_float((top1 - cutoff) / iqr) if iqr > 0 else None,
                "boundary_exact_tie": bool(cutoff == next_score),
                "top30_unique_score_fraction": finite_float(top[score_column].nunique(dropna=True) / top_k),
            }
        )
        selections[pd.Timestamp(date)] = set(top["ticker"].astype(str))
    result = pd.DataFrame(records)
    if not result.empty:
        result["next_turnover"] = np.nan
        dates = sorted(selections)
        for current, next_date in zip(dates, dates[1:]):
            if session_index[next_date] != session_index[current] + 1 or next_date.year != current.year:
                continue
            overlap = len(selections[current] & selections[next_date])
            result.loc[result["date"].eq(current), "next_turnover"] = 1.0 - overlap / top_k
    return result, selections


def summarize_metrics(metrics: pd.DataFrame) -> dict[str, Any]:
    if metrics.empty:
        return {
            "usable_dates": 0,
            "finite_count": quantile_summary([]),
            "score_iqr": quantile_summary([]),
            "boundary_gap": quantile_summary([]),
            "normalized_boundary_gap": quantile_summary([]),
            "top1_to_cutoff_gap": quantile_summary([]),
            "normalized_top1_to_cutoff_gap": quantile_summary([]),
            "boundary_exact_tie_fraction": None,
            "top30_unique_score_fraction": quantile_summary([]),
            "next_turnover": quantile_summary([]),
            "separation_vs_next_turnover": {"pairs": 0, "spearman": None, "pearson": None},
        }
    ties = metrics["boundary_exact_tie"].astype(bool)
    return {
        "usable_dates": int(len(metrics)),
        "finite_count": quantile_summary(metrics["finite_count"]),
        "score_iqr": quantile_summary(metrics["score_iqr"]),
        "boundary_gap": quantile_summary(metrics["boundary_gap"]),
        "normalized_boundary_gap": quantile_summary(metrics["normalized_boundary_gap"]),
        "top1_to_cutoff_gap": quantile_summary(metrics["top1_to_cutoff_gap"]),
        "normalized_top1_to_cutoff_gap": quantile_summary(metrics["normalized_top1_to_cutoff_gap"]),
        "boundary_exact_tie_fraction": finite_float(ties.mean()),
        "top30_unique_score_fraction": quantile_summary(metrics["top30_unique_score_fraction"]),
        "next_turnover": quantile_summary(metrics["next_turnover"]),
        "separation_vs_next_turnover": correlation_summary(
            metrics["normalized_boundary_gap"], metrics["next_turnover"]
        ),
    }


def summarize(features: pd.DataFrame, official_dates: pd.Series | pd.Index, top_k: int = TOP_K) -> dict[str, Any]:
    frame, official, session_index = prepare_frame(features, official_dates)
    candidates: dict[str, Any] = {}
    for candidate in CANDIDATES:
        metrics, selections = daily_separation(frame, candidate, top_k, session_index)
        by_year: dict[str, Any] = {}
        for year, group in metrics.groupby("year", sort=True):
            by_year[str(year)] = summarize_metrics(group)
        candidates[candidate] = {
            "overall": summarize_metrics(metrics),
            "by_year": by_year,
            "selection_dates": int(len(selections)),
        }
    return {
        "status": "PASS_STRUCTURAL_SCORE_SEPARATION",
        "scope": "Fixed Top-30 score-edge mechanics at the rank-30/rank-31 boundary; no outcome, policy, era, or candidate selection.",
        "top_k": top_k,
        "boundary_definition": {
            "selection_order": "descending candidate rank, then ascending ticker tie-break",
            "cutoff": "score of the 30th selected row",
            "next_score": "score of the 31st row in the same eligible finite daily universe",
            "normalized_boundary_gap": "(score_30 - score_31) / same-day finite-score IQR; null when IQR is zero",
            "next_turnover": "one-way Top-30 turnover from the current official session to the next consecutive official session",
        },
        "calendar": {
            "official_session_count": int(len(official)),
            "official_min": str(official.min().date()) if len(official) else None,
            "official_max": str(official.max().date()) if len(official) else None,
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
