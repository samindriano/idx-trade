"""Outcome-blind calendar-year decomposition of the 20-vs-60 mask delta."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCENARIO_PATH = ROOT / "research" / "alpha_eligibility_policy_scenario_v1.py"


def load_scenario_module():
    spec = importlib.util.spec_from_file_location("alpha_eligibility_policy_scenario_v1", SCENARIO_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load {SCENARIO_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def summarize(mask20: pd.DataFrame, mask60: pd.DataFrame) -> dict[str, Any]:
    mask20 = mask20.copy()
    mask60 = mask60.copy()
    mask20["date"] = pd.to_datetime(mask20["date"], errors="raise").dt.normalize()
    mask60["date"] = pd.to_datetime(mask60["date"], errors="raise").dt.normalize()
    left = mask20.set_index(["ticker", "date"])["eligible_decision_universe"].astype(bool)
    right = mask60.set_index(["ticker", "date"])["eligible_decision_universe"].astype(bool)
    if not left.index.equals(right.index):
        raise ValueError("policy masks do not share the same ticker/date index")
    new = left & ~right
    keys = new[new].index.to_frame(index=False)
    keys["year"] = keys["date"].dt.year.astype(int)
    result: dict[str, Any] = {}
    for year in sorted(mask60["date"].dt.year.unique().tolist()):
        y20 = mask20.loc[mask20["date"].dt.year.eq(year), "eligible_decision_universe"].astype(bool)
        y60 = mask60.loc[mask60["date"].dt.year.eq(year), "eligible_decision_universe"].astype(bool)
        added = keys.loc[keys["year"].eq(year)]
        result[str(year)] = {
            "minimum_20_eligible_rows": int(y20.sum()),
            "minimum_60_eligible_rows": int(y60.sum()),
            "newly_admitted_rows": int(len(added)),
            "newly_admitted_tickers": int(added["ticker"].nunique()),
            "newly_admitted_dates": int(added["date"].nunique()),
            "new_rows_as_fraction_of_minimum_60": float(len(added) / y60.sum()) if y60.sum() else None,
        }
    return {
        "overall_newly_admitted_rows": int(new.sum()),
        "overall_newly_admitted_tickers": int(keys["ticker"].nunique()),
        "overall_newly_admitted_dates": int(keys["date"].nunique()),
        "by_year": result,
        "interpretation": "The delta is a mask difference only; it is not inferred to represent listings, delistings, ticker reuse, or a superior policy.",
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")
    panel = pd.read_parquet(args.panel, columns=["ticker", "date", "regular_market_value"])
    panel["ticker"] = panel["ticker"].astype("string")
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    sessions = pd.read_csv(args.sessions, usecols=["date"])
    sessions["date"] = pd.to_datetime(sessions["date"], errors="raise").dt.normalize()
    anchors = pd.read_csv(args.anchors)
    scenario = load_scenario_module()
    masks = {
        minimum: scenario.build_universe(panel, sessions, anchors, minimum)[0]
        for minimum in (20, 60)
    }
    result = {
        "status": "PASS_POLICY_DELTA_BY_ERA_NO_SELECTION",
        "scope": "Outcome-blind calendar-year decomposition of both eligibility interpretations.",
        "policies": {
            "minimum_20": {"window": 60, "minimum_finite_observations": 20},
            "minimum_60": {"window": 60, "minimum_finite_observations": 60},
        },
        "delta": summarize(masks[20], masks[60]),
        "inputs": {
            "panel": {"path": str(args.panel), "sha256": sha256_file(args.panel)},
            "official_sessions": {"path": str(args.sessions), "sha256": sha256_file(args.sessions)},
            "tradability_anchors": {"path": str(args.anchors), "sha256": sha256_file(args.anchors)},
        },
        "code_sha256": sha256_file(Path(__file__).resolve()),
        "scenario_helper_sha256": sha256_file(SCENARIO_PATH),
        "admission": {
            "policy_selected": False,
            "era_selected": False,
            "protected_boundary": "CLOSED",
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--anchors", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
