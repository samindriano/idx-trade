"""Outcome-blind capacity-proxy stress map for fixed C1-C4 selections.

The only capacity field used is the frozen panel's regular_market_value. The
result is a sensitivity map, not ADV, executable capacity, or profitability.
No target, outcome, provider, incumbent, or weight fitting is allowed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


CANDIDATES = {
    "C1": "rank_C1_residual_reversal_5_v1",
    "C2": "rank_C2_participation_confirmation_5_v1",
    "C3": "rank_C3_financial_quality_growth_v1",
    "C4": "rank_C4_path_efficiency_reversal_20_v1",
}
FROZEN_SESSION_COUNT = 600
TOP_K = 30
PARTICIPATION_RATES = (0.0025, 0.005, 0.01, 0.02)


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


def quantiles(values: pd.Series) -> dict[str, float | int | None]:
    finite = pd.to_numeric(values, errors="coerce")
    finite = finite[np.isfinite(finite) & (finite > 0)]
    if finite.empty:
        return {"count": 0, "q10": None, "q25": None, "median": None, "q75": None, "q90": None}
    return {
        "count": int(len(finite)),
        "q10": finite_float(finite.quantile(0.10)),
        "q25": finite_float(finite.quantile(0.25)),
        "median": finite_float(finite.median()),
        "q75": finite_float(finite.quantile(0.75)),
        "q90": finite_float(finite.quantile(0.90)),
    }


def select_top(frame: pd.DataFrame, score_column: str) -> pd.DataFrame:
    eligible = frame["eligible_decision_universe"].astype(bool)
    score = pd.to_numeric(frame[score_column], errors="coerce")
    valid = eligible & score.notna() & np.isfinite(score)
    rows = frame.loc[valid, ["ticker", "date", score_column, "regular_market_value"]].copy()
    rows[score_column] = pd.to_numeric(rows[score_column], errors="coerce")
    selected: list[pd.DataFrame] = []
    for _, group in rows.groupby("date", sort=True):
        top = group.sort_values(
            [score_column, "ticker"], ascending=[False, True], kind="mergesort"
        ).head(TOP_K)
        if len(top) == TOP_K:
            selected.append(top)
    if not selected:
        return pd.DataFrame(columns=["ticker", "date", score_column, "regular_market_value"])
    return pd.concat(selected, ignore_index=True)


def candidate_result(frame: pd.DataFrame, label: str, score_column: str) -> dict[str, object]:
    selected = select_top(frame, score_column)
    values = pd.to_numeric(selected["regular_market_value"], errors="coerce")
    finite_values = values[np.isfinite(values) & (values > 0)]
    capacity_by_rate = {
        f"{rate:.4f}": quantiles(finite_values * rate)
        for rate in PARTICIPATION_RATES
    }
    return {
        "candidate": label,
        "candidate_column": score_column,
        "top30_dates": int(selected["date"].nunique()),
        "selected_slots": int(len(selected)),
        "regular_market_value_finite_slots": int(len(finite_values)),
        "regular_market_value_finite_slot_share": finite_float(
            len(finite_values) / len(selected)
        ) if len(selected) else None,
        "capacity_proxy_idr_by_participation_rate": capacity_by_rate,
        "interpretation": "rate * regular_market_value only; not ADV, executable capacity, spread, or fill guarantee",
    }


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
        *CANDIDATES.values(),
    ]
    features = pd.read_parquet(args.features, columns=feature_columns)
    features["date"] = pd.to_datetime(features["date"], errors="raise").dt.normalize()
    panel = pd.read_parquet(
        args.panel,
        columns=["ticker", "date", "regular_market_value"],
    )
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    if features.duplicated(["ticker", "date"]).any():
        raise ValueError("features contain duplicate ticker/date keys")
    if panel.duplicated(["ticker", "date"]).any():
        raise ValueError("panel contains duplicate ticker/date keys")
    sessions = pd.read_csv(args.sessions, usecols=["date"])
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    sessions = sessions.drop_duplicates("date").sort_values("date", kind="mergesort")
    if len(sessions) < FROZEN_SESSION_COUNT:
        raise ValueError("official session source is shorter than frozen window")
    frozen = sessions.tail(FROZEN_SESSION_COUNT).reset_index(drop=True)
    features = features[features["date"].isin(set(frozen["date"]))].copy()
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
    result = {
        "status": "PASS_STRUCTURAL_ONLY",
        "stage": "L_CAPACITY_PROXY_STRESS",
        "outcome_accessed": False,
        "provider_accessed": False,
        "target_accessed": False,
        "incumbent_score_accessed": False,
        "candidate_id_created": False,
        "frozen_session_count": FROZEN_SESSION_COUNT,
        "frozen_window_start": frozen["date"].min().strftime("%Y-%m-%d"),
        "frozen_window_end": frozen["date"].max().strftime("%Y-%m-%d"),
        "participation_rates": list(PARTICIPATION_RATES),
        "source_hashes": {
            "features": sha256_file(args.features),
            "panel": sha256_file(args.panel),
            "official_sessions": sha256_file(args.sessions),
        },
        "code_sha256": sha256_file(Path(__file__)),
        "candidates": {
            label: candidate_result(frame, label, column)
            for label, column in CANDIDATES.items()
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
