"""Outcome-blind census of ACTIVE/NO_TRADE state transitions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


ANCHOR_COLUMNS = ["ticker", "as_of_date", "state"]
FORBIDDEN_INPUT_MARKERS = ("target", "forward", "label", "outcome", "vault", "counter")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def summarize(anchor: pd.DataFrame) -> dict[str, Any]:
    missing = set(ANCHOR_COLUMNS).difference(anchor.columns)
    if missing:
        raise ValueError(f"missing anchor columns: {sorted(missing)}")
    frame = anchor[ANCHOR_COLUMNS].copy()
    frame["ticker"] = frame["ticker"].astype("string")
    frame["as_of_date"] = pd.to_datetime(frame["as_of_date"], errors="raise").dt.normalize()
    if frame.duplicated(["ticker", "as_of_date"]).any():
        raise ValueError("duplicate ticker/date keys")
    profiles: list[dict[str, Any]] = []
    for ticker, group in frame.sort_values(["ticker", "as_of_date"]).groupby("ticker", sort=True):
        states = group["state"].tolist()
        transitions = sum(left != right for left, right in zip(states, states[1:]))
        active_blocks = sum(
            state == "ACTIVE" and (index == 0 or states[index - 1] != "ACTIVE")
            for index, state in enumerate(states)
        )
        no_trade_blocks = sum(
            state == "NO_TRADE" and (index == 0 or states[index - 1] != "NO_TRADE")
            for index, state in enumerate(states)
        )
        profiles.append(
            {
                "ticker": str(ticker),
                "first_state": str(states[0]),
                "last_state": str(states[-1]),
                "transitions": int(transitions),
                "active_blocks": int(active_blocks),
                "no_trade_blocks": int(no_trade_blocks),
            }
        )
    profile = pd.DataFrame(profiles)
    changed = profile.loc[profile["transitions"].gt(0), "transitions"]
    first_last = {
        f"{first}->{last}": int(count)
        for (first, last), count in profile.groupby(["first_state", "last_state"]).size().items()
    }
    return {
        "status": "PASS_ANCHOR_STATE_TRANSITION_CENSUS",
        "scope": "Observed ACTIVE/NO_TRADE transition geometry; no lifecycle or identity inference",
        "ticker_count": int(len(profile)),
        "state_change_ticker_count": int(len(changed)),
        "first_last_profiles": first_last,
        "transition_ticker_median": float(changed.median()) if len(changed) else None,
        "transition_ticker_q95": float(changed.quantile(0.95)) if len(changed) else None,
        "maximum_transitions": int(profile["transitions"].max()),
        "maximum_active_blocks": int(profile["active_blocks"].max()),
        "maximum_no_trade_blocks": int(profile["no_trade_blocks"].max()),
        "tickers_over_100_transitions": int(profile["transitions"].gt(100).sum()),
        "interpretation": "Repeated ACTIVE/NO_TRADE changes are observed state geometry. They do not establish suspension, delisting, relisting, ticker reuse, issuer continuity, or lifecycle semantics.",
        "protected_boundary": "CLOSED",
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.resolve()
    if "idx-alpha-available-data-staging-20260919" not in str(output):
        raise ValueError("refusing output outside isolated alpha staging")
    if any(marker in str(args.anchor).lower() for marker in FORBIDDEN_INPUT_MARKERS):
        raise ValueError(f"refusing input path with protected-data marker: {args.anchor}")
    anchor = pd.read_csv(args.anchor, usecols=ANCHOR_COLUMNS)
    result = summarize(anchor)
    result["inputs"] = {"anchor": {"path": str(args.anchor), "sha256": sha256_file(args.anchor), "rows": int(len(anchor))}}
    result["code_sha256"] = sha256_file(Path(__file__).resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--anchor", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
