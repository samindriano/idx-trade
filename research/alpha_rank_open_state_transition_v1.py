"""Outcome-blind Rank-to-Open state transition audit.

This audit joins the already-frozen C1-C4 stored ranks to the existing
historical Open capability field.  It does not refit, rescore, impute, read
targets/returns, or construct a paper portfolio.  Its output is a structural
shadow of requested rank slots versus same-row Open readiness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


CANDIDATES = [
    "C1_residual_reversal_5_v1",
    "C2_participation_confirmation_5_v1",
    "C3_financial_quality_growth_v1",
    "C4_path_efficiency_reversal_20_v1",
]
TOP_K = 30
FROZEN_SESSION_COUNT = 600
EXTERNAL_STAGE_ROOT = Path(
    r"D:\Documents\Project\idx-alpha-available-data-staging-20260919"
).resolve()
EXPECTED_HASHES = {
    "features": "aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4",
    "panel": "25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e",
    "official_sessions": "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a",
    "tradability_anchors": "33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e",
}
RANK_BANDS = ((1, 10, "1_10"), (11, 20, "11_20"), (21, 30, "21_30"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite_positive(value: object) -> bool:
    try:
        return bool(np.isfinite(float(value)) and float(value) > 0)
    except (TypeError, ValueError):
        return False


def open_ready(open_value: object, high: object, low: object) -> bool:
    try:
        value = float(open_value)
        upper = float(high)
        lower = float(low)
    except (TypeError, ValueError):
        return False
    return bool(
        np.isfinite(value)
        and value > 0
        and np.isfinite(upper)
        and np.isfinite(lower)
        and lower <= value <= upper
    )


def rank_band(rank_position: int) -> str:
    for lower, upper, name in RANK_BANDS:
        if lower <= rank_position <= upper:
            return name
    return ">30"


def quantiles(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "min": None, "median": None, "mean": None, "max": None}
    series = pd.Series(values, dtype="float64")
    return {
        "count": int(len(series)),
        "min": float(series.min()),
        "median": float(series.median()),
        "mean": float(series.mean()),
        "max": float(series.max()),
    }


def transition_type(
    previous_ticker: str,
    current_eligible_rank: object,
    current_selected: set[str],
) -> str:
    if previous_ticker in current_selected:
        return "HOLD"
    if finite_positive(current_eligible_rank):
        return "EXIT_RANKED_OUT"
    return "EXIT_RANK_MISSING"


def build_candidate_selection(frame: pd.DataFrame, candidate: str) -> pd.DataFrame:
    rank_column = f"rank_{candidate}"
    eligible = frame["eligible_decision_universe"].astype(bool)
    finite_rank = pd.to_numeric(frame[rank_column], errors="coerce").notna()
    candidates = frame.loc[eligible & finite_rank].copy()
    candidates["rank_value"] = pd.to_numeric(candidates[rank_column], errors="coerce")
    candidates = candidates.sort_values(
        ["date", "rank_value", "ticker"],
        ascending=[True, False, True],
        kind="mergesort",
    )
    candidates["rank_position"] = candidates.groupby("date", sort=False).cumcount() + 1
    counts = candidates.groupby("date").size()
    valid_dates = set(counts[counts >= TOP_K].index)
    selected = candidates[candidates["date"].isin(valid_dates)]
    return (
        selected[selected["rank_position"] <= TOP_K]
        .copy()
        .sort_values(["date", "rank_position", "ticker"], kind="mergesort")
    )


def candidate_audit(
    frame: pd.DataFrame,
    candidate: str,
    session_dates: list[pd.Timestamp],
) -> dict[str, Any]:
    selected = build_candidate_selection(frame, candidate)
    selected_by_date = {
        pd.Timestamp(date): group.copy()
        for date, group in selected.groupby("date", sort=True)
    }
    all_by_key = frame.set_index(["ticker", "date"], drop=False)
    pending_streaks: list[int] = []
    current_streaks: dict[str, int] = {}
    daily: list[dict[str, Any]] = []
    transitions: dict[str, int] = {
        "ENTRY": 0,
        "HOLD": 0,
        "EXIT_RANKED_OUT": 0,
        "EXIT_RANK_MISSING": 0,
    }
    pending_by_band = {name: {"selected": 0, "pending": 0} for _, _, name in RANK_BANDS}
    pending_by_band[">30"] = {"selected": 0, "pending": 0}
    requested_turnover: list[float] = []
    ready_turnover: list[float] = []
    pending_rates: list[float] = []
    ready_slots: list[int] = []
    pending_slots: list[int] = []

    for date, group in selected_by_date.items():
        selected_tickers = set(group["ticker"].astype(str))
        for ticker in set(current_streaks) - selected_tickers:
            current_streaks.pop(ticker, None)
        statuses: list[str] = []
        for row in group.itertuples(index=False):
            ready = open_ready(row.open, row.high, row.low)
            status = "READY_OPEN" if ready else "PENDING_OPEN"
            statuses.append(status)
            band = rank_band(int(row.rank_position))
            pending_by_band[band]["selected"] += 1
            pending_by_band[band]["pending"] += int(not ready)
            ticker = str(row.ticker)
            if status == "PENDING_OPEN":
                current_streaks[ticker] = current_streaks.get(ticker, 0) + 1
                pending_streaks.append(current_streaks[ticker])
            else:
                current_streaks.pop(ticker, None)
        selected_set = selected_tickers
        ready_set = set(group.loc[np.array(statuses) == "READY_OPEN", "ticker"].astype(str))
        pending = int(len(group) - len(ready_set))
        ready_slots.append(len(ready_set))
        pending_slots.append(pending)
        pending_rates.append(pending / TOP_K)

        session_index = session_dates.index(date)
        previous_date = session_dates[session_index - 1] if session_index else None
        if previous_date is None or previous_date not in selected_by_date:
            continue
        previous = selected_by_date[previous_date]
        previous_set = set(previous["ticker"].astype(str))
        previous_ready = set(
            previous.loc[
                previous.apply(lambda row: open_ready(row["open"], row["high"], row["low"]), axis=1),
                "ticker",
            ].astype(str)
        )
        overlap = len(selected_set & previous_set)
        ready_overlap = len(ready_set & previous_ready)
        requested_turnover.append(1.0 - overlap / TOP_K)
        ready_turnover.append(1.0 - ready_overlap / TOP_K)
        for ticker in selected_set - previous_set:
            transitions["ENTRY"] += 1
        for ticker in previous_set:
            current_row = all_by_key.loc[(ticker, date)] if (ticker, date) in all_by_key.index else None
            current_rank = None
            if current_row is not None:
                if isinstance(current_row, pd.DataFrame):
                    current_row = current_row.iloc[0]
                if bool(current_row["eligible_decision_universe"]):
                    current_rank = current_row[f"rank_{candidate}"]
            transitions[transition_type(ticker, current_rank, selected_set)] += 1
        daily.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "selected_slots": int(len(group)),
                "ready_slots": int(len(ready_set)),
                "pending_slots": pending,
                "pending_rate": pending / TOP_K,
                "requested_turnover_vs_k": requested_turnover[-1],
                "open_ready_turnover_vs_k": ready_turnover[-1],
            }
        )

    return {
        "candidate": candidate,
        "top_k": TOP_K,
        "selection_dates": int(len(selected_by_date)),
        "selection_slots": int(len(selected)),
        "ready_slots": int(sum(ready_slots)),
        "pending_slots": int(sum(pending_slots)),
        "pending_rate": float(sum(pending_slots) / sum(ready_slots + pending_slots))
        if pending_slots
        else None,
        "ready_slots_distribution": quantiles([float(value) for value in ready_slots]),
        "pending_slots_distribution": quantiles([float(value) for value in pending_slots]),
        "pending_rate_distribution": quantiles(pending_rates),
        "requested_turnover_vs_k": quantiles(requested_turnover),
        "open_ready_turnover_vs_k": quantiles(ready_turnover),
        "pending_duration_sessions": quantiles([float(value) for value in pending_streaks]),
        "pending_by_rank_band": pending_by_band,
        "transitions": transitions,
        "daily": daily,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--repo-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    output = args.output.resolve()
    if EXTERNAL_STAGE_ROOT not in output.parents:
        raise ValueError("output must remain in the isolated alpha staging root")
    paths = {
        "features": args.features,
        "panel": args.panel,
        "official_sessions": args.sessions,
        "tradability_anchors": args.anchors,
    }
    source_hashes = {name: sha256_file(path) for name, path in paths.items()}
    if source_hashes != EXPECTED_HASHES:
        raise ValueError(f"input hash mismatch: {source_hashes}")

    feature_columns = [
        "ticker",
        "date",
        "eligible_decision_universe",
        *(f"rank_{candidate}" for candidate in CANDIDATES),
    ]
    features = pd.read_parquet(args.features, columns=feature_columns)
    panel = pd.read_parquet(
        args.panel,
        columns=["ticker", "date", "open", "high", "low"],
    )
    sessions = pd.read_csv(args.sessions, usecols=["date"])
    for table in (features, panel):
        table["ticker"] = table["ticker"].astype("string")
        table["date"] = pd.to_datetime(table["date"], errors="raise").dt.normalize()
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    sessions = sessions.drop_duplicates("date").sort_values("date", kind="mergesort").reset_index(drop=True)
    if len(sessions) < FROZEN_SESSION_COUNT:
        raise ValueError("official session source is shorter than frozen window")
    frozen_sessions = sessions.tail(FROZEN_SESSION_COUNT).copy().reset_index(drop=True)
    frozen_dates = set(frozen_sessions["date"])
    features = features[features["date"].isin(frozen_dates)].copy()
    panel = panel[panel["date"].isin(frozen_dates)].copy()
    if features.duplicated(["ticker", "date"]).any() or panel.duplicated(["ticker", "date"]).any():
        raise ValueError("duplicate ticker/date key in input")
    merged = features.merge(panel, on=["ticker", "date"], how="left", validate="one_to_one", indicator=True)
    if not merged["_merge"].eq("both").all():
        raise ValueError("feature/panel key closure failed")
    merged = merged.drop(columns=["_merge"])

    candidate_results = {
        candidate: candidate_audit(merged, candidate, list(frozen_sessions["date"]))
        for candidate in CANDIDATES
    }
    result = {
        "status": "PASS_STRUCTURAL_ONLY",
        "admission_status": "BLOCKED_SOURCE_ADMISSION",
        "stage": "C1_C4_RANK_TO_OPEN_STATE_TRANSITION_AUDIT_V1",
        "protocol": "2026-09-20_ALPHA_RANK_OPEN_STATE_TRANSITION_PREREGISTRATION_V1",
        "outcome_accessed": False,
        "target_accessed": False,
        "provider_accessed": False,
        "canonical_data_accessed": False,
        "protected_payloads_persisted": False,
        "imputation_used": False,
        "candidate_ids": CANDIDATES,
        "top_k": TOP_K,
        "frozen_session_count": FROZEN_SESSION_COUNT,
        "frozen_window_start": frozen_sessions["date"].min().strftime("%Y-%m-%d"),
        "frozen_window_end": frozen_sessions["date"].max().strftime("%Y-%m-%d"),
        "selection_contract": "eligible_decision_universe, finite stored rank, descending rank, ascending ticker tie-break",
        "open_contract": "READY_OPEN iff positive finite Open and same-row low <= Open <= high; otherwise PENDING_OPEN",
        "transition_contract": "EXIT_RANKED_OUT iff current eligible finite rank exists but is outside Top-30; otherwise EXIT_RANK_MISSING",
        "source_hashes": source_hashes,
        "repo_head": args.repo_head,
        "code_sha256": sha256_file(Path(__file__)),
        "candidate_results": candidate_results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "admission_status", "candidate_ids", "frozen_window_start", "frozen_window_end")}, indent=2))


if __name__ == "__main__":
    main()
