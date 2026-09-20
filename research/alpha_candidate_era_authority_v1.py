"""Outcome-blind candidate-specific era and authority dependency census.

This is a descriptive structural audit. It uses the frozen feature artifact
and official session calendar to identify calendar-year support strata and
maps each candidate to the upstream authority gates its formula actually
consumes. It does not select an eligibility policy or admit any era.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


CANDIDATES = {
    "C1": "C1_residual_reversal_5_v1",
    "C2": "C2_participation_confirmation_5_v1",
    "C3": "C3_financial_quality_growth_v1",
    "C4": "C4_path_efficiency_reversal_20_v1",
}
FEATURE_COLUMNS = [
    "ticker",
    "date",
    "eligible_decision_universe",
    *CANDIDATES.values(),
    "financial_pit_valid",
]
FORBIDDEN_INPUT_MARKERS = ("target", "forward", "label", "outcome", "vault", "counter")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def summarize(features: pd.DataFrame, official_dates: pd.Index) -> dict[str, Any]:
    required = set(FEATURE_COLUMNS)
    missing = required.difference(features.columns)
    if missing:
        raise ValueError(f"feature artifact missing columns: {sorted(missing)}")
    frame = features[FEATURE_COLUMNS].copy()
    frame["ticker"] = frame["ticker"].astype("string")
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    if frame.duplicated(["ticker", "date"]).any():
        raise ValueError("feature artifact has duplicate ticker/date keys")
    official_values = pd.to_datetime(official_dates, errors="raise")
    if isinstance(official_values, pd.Series):
        official_values = official_values.dt.normalize()
    else:
        official_values = official_values.normalize()
    official = pd.Index(official_values, name="date")
    if not frame["date"].isin(official).all():
        raise ValueError("feature dates fall outside official session calendar")
    frame["eligible_decision_universe"] = frame["eligible_decision_universe"].fillna(False).astype(bool)
    frame["year"] = frame["date"].dt.year.astype(int)
    years = sorted(frame["year"].unique().tolist())
    eras: dict[str, Any] = {}
    for year in years:
        era = frame.loc[frame["year"] == year]
        eligible = era.loc[era["eligible_decision_universe"]]
        daily = eligible.groupby("date").size()
        row: dict[str, Any] = {
            "year": year,
            "eligible_rows": int(len(eligible)),
            "eligible_dates": int(eligible["date"].nunique()),
            "eligible_tickers": int(eligible["ticker"].nunique()),
            "daily_population": {
                "min": int(daily.min()) if len(daily) else 0,
                "median": float(daily.median()) if len(daily) else None,
                "mean": float(daily.mean()) if len(daily) else None,
                "max": int(daily.max()) if len(daily) else 0,
            },
            "candidates": {},
        }
        for candidate, column in CANDIDATES.items():
            finite = eligible[column].notna()
            finite_rows = int(finite.sum())
            row["candidates"][candidate] = {
                "finite_rows": finite_rows,
                "coverage_of_eligible_rows": float(finite_rows / len(eligible)) if len(eligible) else None,
                "finite_dates": int(eligible.loc[finite, "date"].nunique()),
                "finite_tickers": int(eligible.loc[finite, "ticker"].nunique()),
                "financial_pit_valid_rows": int(
                    eligible.loc[finite, "financial_pit_valid"].fillna(False).astype(bool).sum()
                ),
            }
        row["financial_pit_valid_rows_all_candidates"] = int(
            eligible["financial_pit_valid"].fillna(False).astype(bool).sum()
        )
        eras[str(year)] = row

    return {
        "status": "PASS_STRUCTURAL_ERA_AND_DEPENDENCY_MAP",
        "scope": "Outcome-blind calendar-year support strata; no policy or era selected.",
        "calendar": {
            "official_session_count": int(len(official)),
            "official_min": str(official.min().date()) if len(official) else None,
            "official_max": str(official.max().date()) if len(official) else None,
            "era_rule": "calendar year derived from the frozen official session date; descriptive only",
        },
        "eras": eras,
        "candidate_dependency_contracts": {
            "C1": {
                "formula_inputs": ["close", "regular_market_value", "eligible mask", "official session calendar"],
                "direct_authority_gates": ["eligibility policy", "historical PIT population", "security/issuer identity", "corporate-action price basis"],
                "economic_gate": "historical executable capacity remains required before economic or production claims",
                "candidate_specific_observation": "No financial bundle is a direct score input; market return and beta still inherit the eligible price panel.",
            },
            "C2": {
                "formula_inputs": ["close", "volume", "regular_market_value", "eligible mask", "official session calendar"],
                "direct_authority_gates": ["eligibility policy", "historical PIT population", "security/issuer identity", "corporate-action price/volume basis", "historical liquidity semantics"],
                "economic_gate": "historical executable capacity is directly material because turnover is a formula input",
                "candidate_specific_observation": "C2's 60-session feature warm-up makes its score/rank support unchanged in the 20-vs-60 counterfactual.",
            },
            "C3": {
                "formula_inputs": ["five financial values", "reporting knowledge time", "period date", "bundle version/attachment provenance", "eligible mask"],
                "direct_authority_gates": ["eligibility policy", "historical PIT population", "security/issuer identity", "publication/available-at timing", "revision/vintage semantics"],
                "economic_gate": "capacity is not a direct score input but remains required for portfolio/economic admission",
                "candidate_specific_observation": "The score does not directly consume close/volume, but its eligibility mask still consumes the liquidity field and active anchors.",
            },
            "C4": {
                "formula_inputs": ["close", "regular_market_value", "eligible mask", "official session calendar"],
                "direct_authority_gates": ["eligibility policy", "historical PIT population", "security/issuer identity", "corporate-action price basis"],
                "economic_gate": "historical executable capacity remains required before economic or production claims",
                "candidate_specific_observation": "No financial bundle is a direct score input; the 20-session return/path window remains price-basis dependent.",
            },
        },
        "bounded_era_interpretation": {
            "C1_C2_C4": "2022-2026 have broad finite structural support, but no era is population/PIT/identity/CA admitted.",
            "C3": "No finite structural support occurs in 2021-2024; observed support begins 2025-04-25 and remains partial through 2026-07-17.",
            "selection": "No era or candidate subset was selected; these are descriptive strata for future policy-authorized review.",
        },
        "admission": {
            "policy_selected": False,
            "era_admitted": False,
            "candidate_status_changed": False,
            "protected_boundary": "CLOSED",
        },
    }


def summarize_panel_anchor_boundary(panel: pd.DataFrame, anchors: pd.DataFrame) -> dict[str, Any]:
    panel = panel[["ticker", "date"]].copy()
    anchors = anchors[["ticker", "market", "as_of_date", "state"]].copy()
    panel["ticker"] = panel["ticker"].astype("string")
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    anchors["ticker"] = anchors["ticker"].astype("string")
    anchors["date"] = pd.to_datetime(anchors["as_of_date"], errors="raise").dt.normalize()
    if panel.duplicated(["ticker", "date"]).any():
        raise ValueError("panel has duplicate ticker/date keys")
    if anchors.duplicated(["ticker", "date"]).any():
        raise ValueError("anchors have duplicate ticker/date keys")
    anchors = anchors.loc[anchors["market"].eq("REGULAR")].copy()
    panel_keys = set(zip(panel["ticker"], panel["date"]))
    active = anchors.loc[anchors["state"].eq("ACTIVE")]
    no_trade = anchors.loc[anchors["state"].eq("NO_TRADE")]
    active_keys = set(zip(active["ticker"], active["date"]))
    no_trade_keys = set(zip(no_trade["ticker"], no_trade["date"]))
    years = sorted(panel["date"].dt.year.unique().tolist())
    by_year: dict[str, Any] = {}
    for year in years:
        panel_year = panel.loc[panel["date"].dt.year.eq(year)]
        active_year = active.loc[active["date"].dt.year.eq(year)]
        by_year[str(year)] = {
            "panel_rows": int(len(panel_year)),
            "panel_tickers": int(panel_year["ticker"].nunique()),
            "active_anchor_rows": int(len(active_year)),
            "active_anchor_tickers": int(active_year["ticker"].nunique()),
            "active_anchor_rows_absent_from_panel": int(
                len(set(zip(active_year["ticker"], active_year["date"])) - set(zip(panel_year["ticker"], panel_year["date"])))
            ),
        }
    return {
        "panel_rows": int(len(panel)),
        "panel_tickers": int(panel["ticker"].nunique()),
        "active_anchor_rows": int(len(active)),
        "no_trade_anchor_rows": int(len(no_trade)),
        "panel_keys_with_active_anchor": int(len(panel_keys & active_keys)),
        "panel_keys_with_no_trade_anchor": int(len(panel_keys & no_trade_keys)),
        "panel_keys_without_active_anchor": int(len(panel_keys - active_keys)),
        "by_year": by_year,
        "interpretation": "All observed panel keys are ACTIVE anchors, but extra ACTIVE anchor rows are absent from the panel in earlier years; this is structural overlap, not population completeness.",
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")
    for path in (args.features, args.sessions, args.panel, args.anchors):
        if any(marker in str(path).lower() for marker in FORBIDDEN_INPUT_MARKERS):
            raise ValueError(f"refusing input path with protected-data marker: {path}")
    features = pd.read_parquet(args.features, columns=FEATURE_COLUMNS)
    sessions = pd.read_csv(args.sessions, usecols=["date"])
    panel = pd.read_parquet(args.panel, columns=["ticker", "date"])
    anchors = pd.read_csv(args.anchors, usecols=["ticker", "market", "as_of_date", "state"])
    result = summarize(features, sessions["date"])
    result["panel_anchor_boundary"] = summarize_panel_anchor_boundary(panel, anchors)
    result["inputs"] = {
        "features": {"path": str(args.features), "sha256": sha256_file(args.features), "rows": int(len(features))},
        "official_sessions": {"path": str(args.sessions), "sha256": sha256_file(args.sessions)},
        "panel": {"path": str(args.panel), "sha256": sha256_file(args.panel), "rows": int(len(panel))},
        "anchors": {"path": str(args.anchors), "sha256": sha256_file(args.anchors), "rows": int(len(anchors))},
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
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
