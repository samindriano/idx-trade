"""Outcome-blind census of panel coverage by tradability-anchor state."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


ANCHOR_COLUMNS = ["ticker", "as_of_date", "state"]
PANEL_COLUMNS = ["ticker", "date"]
FORBIDDEN_INPUT_MARKERS = ("target", "forward", "label", "outcome", "vault", "counter")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def summarize(anchor: pd.DataFrame, panel: pd.DataFrame) -> dict[str, Any]:
    missing_anchor = set(ANCHOR_COLUMNS).difference(anchor.columns)
    missing_panel = set(PANEL_COLUMNS).difference(panel.columns)
    if missing_anchor or missing_panel:
        raise ValueError(f"missing anchor={sorted(missing_anchor)} panel={sorted(missing_panel)}")
    anchor = anchor[ANCHOR_COLUMNS].rename(columns={"as_of_date": "date"}).copy()
    panel = panel[PANEL_COLUMNS].copy()
    for frame in (anchor, panel):
        frame["ticker"] = frame["ticker"].astype("string")
        frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    if anchor.duplicated(["ticker", "date"]).any() or panel.duplicated(["ticker", "date"]).any():
        raise ValueError("duplicate ticker/date keys")
    anchor_keys = anchor[["ticker", "date"]]
    panel_keys = panel[["ticker", "date"]]
    state_rows: dict[str, Any] = {}
    for state, group in anchor.groupby("state", sort=True):
        keys = group[["ticker", "date"]]
        overlap = panel_keys.merge(keys, on=["ticker", "date"], how="inner")
        state_rows[str(state)] = {
            "rows": int(len(group)),
            "ticker_count": int(group["ticker"].nunique()),
            "panel_key_overlap": int(len(overlap)),
        }
    profile = anchor.groupby(["ticker", "state"]).size().unstack(fill_value=0)
    active = profile.get("ACTIVE", pd.Series(0, index=profile.index)).gt(0)
    no_trade = profile.get("NO_TRADE", pd.Series(0, index=profile.index)).gt(0)
    active_tickers = set(profile.index[active])
    panel_tickers = set(panel["ticker"])
    return {
        "status": "PASS_PANEL_ANCHOR_STATE_CENSUS",
        "scope": "Observed panel versus tradability-anchor state coverage; no admission",
        "anchor_rows": int(len(anchor)),
        "anchor_ticker_count": int(anchor["ticker"].nunique()),
        "panel_rows": int(len(panel)),
        "panel_ticker_count": int(panel["ticker"].nunique()),
        "state_rows": state_rows,
        "active_ticker_count": int(active.sum()),
        "no_trade_ticker_count": int(no_trade.sum()),
        "tickers_with_both_states": int((active & no_trade).sum()),
        "no_trade_only_ticker_count": int((~active & no_trade).sum()),
        "active_only_ticker_count": int((active & ~no_trade).sum()),
        "active_tickers_absent_from_panel": sorted(active_tickers - panel_tickers),
        "panel_keys_subset_of_active_anchor": int(
            len(panel_keys.merge(anchor.loc[anchor["state"].eq("ACTIVE"), ["ticker", "date"]], on=["ticker", "date"], how="inner"))
        )
        == len(panel_keys),
        "no_trade_keys_in_panel": int(state_rows.get("NO_TRADE", {}).get("panel_key_overlap", 0)),
        "protected_boundary": "CLOSED",
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")
    for path in (args.anchor, args.panel):
        if any(marker in str(path).lower() for marker in FORBIDDEN_INPUT_MARKERS):
            raise ValueError(f"refusing input path with protected-data marker: {path}")
    anchor = pd.read_csv(args.anchor, usecols=ANCHOR_COLUMNS)
    panel = pd.read_parquet(args.panel, columns=PANEL_COLUMNS)
    result = summarize(anchor, panel)
    result["inputs"] = {
        "anchor": {"path": str(args.anchor), "sha256": sha256_file(args.anchor), "rows": int(len(anchor))},
        "panel": {"path": str(args.panel), "sha256": sha256_file(args.panel), "rows": int(len(panel))},
    }
    result["code_sha256"] = sha256_file(Path(__file__).resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    if not result["panel_keys_subset_of_active_anchor"] or result["no_trade_keys_in_panel"] != 0:
        raise ValueError("panel/anchor state boundary failed")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--anchor", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
