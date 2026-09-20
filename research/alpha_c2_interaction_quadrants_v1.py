"""Outcome-blind quadrant anatomy for the fixed C2 interaction score."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from alpha_candidate_component_anatomy_v1 import (
        CANDIDATES,
        FEATURE_COLUMNS as COMPONENT_FEATURE_COLUMNS,
        build_components,
        prepare_surface,
        quantile_summary,
        sha256_file,
    )
except ModuleNotFoundError:
    from research.alpha_candidate_component_anatomy_v1 import (
        CANDIDATES,
        FEATURE_COLUMNS as COMPONENT_FEATURE_COLUMNS,
        build_components,
        prepare_surface,
        quantile_summary,
        sha256_file,
    )


TOP_K = 30
FEATURE_COLUMNS = COMPONENT_FEATURE_COLUMNS
PANEL_COLUMNS = ["ticker", "date", "close", "volume"]
FORBIDDEN_INPUT_MARKERS = ("target", "forward", "label", "outcome", "vault", "counter")
QUADRANTS = ("ret_pos_activity_pos", "ret_pos_activity_neg", "ret_neg_activity_pos", "ret_neg_activity_neg")


def summarize_quadrants(frame: pd.DataFrame, top_k: int = TOP_K) -> dict[str, Any]:
    score_column = CANDIDATES["C2"]
    rank_column = f"rank_{score_column}"
    valid = frame.loc[
        frame["eligible_decision_universe"]
        & frame[score_column].notna()
        & frame[rank_column].notna()
        & frame["ret_5"].notna()
        & frame["c2_log_abnormal_turnover"].notna(),
        ["ticker", "date", score_column, rank_column, "ret_5", "c2_log_abnormal_turnover"],
    ].copy()
    valid["ret_sign"] = np.where(valid["ret_5"] >= 0.0, "pos", "neg")
    valid["activity_sign"] = np.where(valid["c2_log_abnormal_turnover"] >= 0.0, "pos", "neg")
    valid["quadrant"] = "ret_" + valid["ret_sign"] + "_activity_" + valid["activity_sign"]
    valid["score_sign"] = np.where(valid[score_column] >= 0.0, "positive", "negative")
    pooled_universe = valid["quadrant"].value_counts().reindex(QUADRANTS, fill_value=0)
    pooled_selected = pd.Series(0, index=QUADRANTS, dtype="int64")
    daily_selected_positive: list[float] = []
    daily_selected_negative: list[float] = []
    daily_enrichment: dict[str, list[float]] = {quadrant: [] for quadrant in QUADRANTS}
    year_rows: dict[int, list[pd.DataFrame]] = {}
    for date, group in valid.groupby("date", sort=True):
        if len(group) < top_k:
            continue
        ordered = group.sort_values([rank_column, "ticker"], ascending=[False, True], kind="mergesort")
        selected = ordered.head(top_k)
        pooled_selected = pooled_selected.add(selected["quadrant"].value_counts().reindex(QUADRANTS, fill_value=0), fill_value=0).astype("int64")
        daily_selected_positive.append(float((selected["score_sign"] == "positive").mean()))
        daily_selected_negative.append(float((selected["score_sign"] == "negative").mean()))
        universe_share = group["quadrant"].value_counts(normalize=True).reindex(QUADRANTS, fill_value=0)
        selected_share = selected["quadrant"].value_counts(normalize=True).reindex(QUADRANTS, fill_value=0)
        for quadrant in QUADRANTS:
            if universe_share[quadrant] > 0:
                daily_enrichment[quadrant].append(float(selected_share[quadrant] / universe_share[quadrant]))
        year_rows.setdefault(int(pd.Timestamp(date).year), []).append(group.assign(_selected=False))
        year_rows[int(pd.Timestamp(date).year)][-1].loc[selected.index, "_selected"] = True

    def pooled_summary(universe: pd.Series, selected: pd.Series) -> dict[str, Any]:
        universe_total = int(universe.sum())
        selected_total = int(selected.sum())
        rows: dict[str, Any] = {}
        for quadrant in QUADRANTS:
            u = int(universe[quadrant])
            s = int(selected[quadrant])
            u_share = u / universe_total if universe_total else None
            s_share = s / selected_total if selected_total else None
            rows[quadrant] = {
                "eligible_rows": u,
                "selected_slots": s,
                "eligible_share": u_share,
                "selected_share": s_share,
                "pooled_enrichment": s_share / u_share if u_share and s_share is not None else None,
            }
        return rows

    by_year: dict[str, Any] = {}
    for year, groups in sorted(year_rows.items()):
        year_frame = pd.concat(groups, ignore_index=True)
        u = year_frame["quadrant"].value_counts().reindex(QUADRANTS, fill_value=0)
        s = year_frame.loc[year_frame["_selected"], "quadrant"].value_counts().reindex(QUADRANTS, fill_value=0)
        by_year[str(year)] = {
            "usable_dates": int(len(groups)),
            "pooled_quadrants": pooled_summary(u, s),
            "selected_positive_score_fraction": finite_float((year_frame.loc[year_frame["_selected"], "score_sign"] == "positive").mean()),
        }
    return {
        "usable_dates": int(len(daily_selected_positive)),
        "pooled_quadrants": pooled_summary(pooled_universe, pooled_selected),
        "daily_selected_positive_score_fraction": quantile_summary(daily_selected_positive),
        "daily_selected_negative_score_fraction": quantile_summary(daily_selected_negative),
        "daily_quadrant_enrichment": {quadrant: quantile_summary(values) for quadrant, values in daily_enrichment.items()},
        "by_year": by_year,
    }


def finite_float(value: object) -> float | None:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    return converted if np.isfinite(converted) else None


def run(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")
    for path in (args.features, args.panel, args.sessions):
        if any(marker in str(path).lower() for marker in FORBIDDEN_INPUT_MARKERS):
            raise ValueError(f"refusing input path with protected-data marker: {path}")
    features = pd.read_parquet(args.features, columns=FEATURE_COLUMNS)
    panel = pd.read_parquet(args.panel, columns=PANEL_COLUMNS)
    sessions = pd.read_csv(args.sessions, usecols=["date"])
    surface, official = prepare_surface(features, panel, sessions["date"])
    surface = build_components(surface, official)
    result = {
        "status": "PASS_STRUCTURAL_C2_INTERACTION_QUADRANTS",
        "scope": "Outcome-blind C2 ret_5 by abnormal-turnover sign quadrant for fixed Top-30 selections; no policy, era, candidate, or outcome selection.",
        "quadrant_definition": {
            "ret_pos_activity_pos": "ret_5 >= 0 and log abnormal turnover >= 0",
            "ret_pos_activity_neg": "ret_5 >= 0 and log abnormal turnover < 0",
            "ret_neg_activity_pos": "ret_5 < 0 and log abnormal turnover >= 0",
            "ret_neg_activity_neg": "ret_5 < 0 and log abnormal turnover < 0",
            "selection": "existing descending C2 rank with ascending ticker tie-break, fixed Top-30",
        },
        "calendar": {
            "official_session_count": int(len(official)),
            "official_min": str(official.min().date()) if len(official) else None,
            "official_max": str(official.max().date()) if len(official) else None,
        },
        "overall": summarize_quadrants(surface),
        "admission": {
            "policy_selected": False,
            "era_admitted": False,
            "candidate_status_changed": False,
            "protected_boundary": "CLOSED",
        },
    }
    result["inputs"] = {
        "features": {"path": str(args.features), "sha256": sha256_file(args.features), "rows": int(len(features))},
        "panel": {"path": str(args.panel), "sha256": sha256_file(args.panel), "rows": int(len(panel))},
        "official_sessions": {"path": str(args.sessions), "sha256": sha256_file(args.sessions)},
        "component_helper_sha256": sha256_file(Path(__file__).with_name("alpha_candidate_component_anatomy_v1.py")),
    }
    result["code_sha256"] = sha256_file(Path(__file__).resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
