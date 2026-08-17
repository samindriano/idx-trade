"""Outcome-blind V4 H5/H10 target-support census.

This script only checks row/date observability and point-in-time state.  It
never reads a label, computes a return, fits a model, or calls a provider.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


PINNED = {
    "calendar": "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a",
    "panel": "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76",
    "security_master": "9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9",
    "anchors": "33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e",
    "intervals": "fd255f21a3accd763286fbd0b0c6d9d501d618ae611cc0681017e001bdba83cc",
    "actions": "a0ef73a548b3657260b46a0c497e6f87dd9b5138588e23006d4b538677125b35",
    "scope_exclusions": "406e224dcd611f3d5a2f9ad8bbd2c03b3c8a0826cc724b01b4618c9b1c1bd938",
    "signal_manifest": "b703f1f80aa062accfb4387e5c457458c88aec77351e7dd19342b9c45873cd1a",
    "overlay_parquet": "2aeab3906434f48c15d9ed7a8fb073fdd3bafff362cedcc7b46f9bf16482ca41",
    "overlay_manifest": "dfb7219bddec77ced3e3aadfaa2d85d04c19e1d9fd9a8af1badba523ecf91977",
}

STATE_NAMES = ("ACTIVE", "NO_TRADE", "SUSPENDED", "UNKNOWN", "NO_FUTURE_SESSION")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--overlay-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def state_map_from_inputs(anchors: pd.DataFrame, intervals: pd.DataFrame, dates: pd.DataFrame) -> tuple[dict[tuple[str, int], str], int]:
    date_to_index = dict(zip(dates["date"], dates["session_index"]))
    regular = anchors[anchors["market"].eq("REGULAR")].copy()
    regular["ticker"] = regular["ticker"].astype(str).str.upper().str.strip()
    regular["as_of_date"] = pd.to_datetime(regular["as_of_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    regular["session_index"] = regular["as_of_date"].map(date_to_index)
    grouped = regular.groupby(["ticker", "session_index"])["state"].agg(
        lambda values: tuple(sorted({str(value).upper() for value in values.dropna()}))
    ).reset_index(name="states")
    states = {
        (ticker, int(index)): (values[0] if len(values) == 1 else "AMBIGUOUS")
        for ticker, index, values in grouped.itertuples(index=False)
    }

    regular_intervals = intervals[
        intervals["market"].isin(["REGULAR", "ALL"])
        & intervals["state"].astype(str).str.upper().eq("SUSPENDED")
    ]
    for row in regular_intervals.itertuples(index=False):
        start = pd.Timestamp(row.effective_from).normalize()
        end = pd.Timestamp(row.effective_to).normalize() if pd.notna(row.effective_to) else pd.Timestamp(dates["date"].iloc[-1])
        covered = dates.loc[
            (pd.to_datetime(dates["date"]) >= start)
            & (pd.to_datetime(dates["date"]) <= end),
            "session_index",
        ]
        for index in covered:
            states.setdefault((str(row.ticker).upper().strip(), int(index)), "SUSPENDED")
    return states, int(len(grouped[grouped["states"].map(len).gt(1)]))


def main() -> int:
    parsed = args()
    artifact_root = parsed.artifact_root
    if parsed.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT: {parsed.output_dir}")
    parsed.output_dir.mkdir(parents=True)

    paths = {
        "calendar": artifact_root / "official_exchange_sessions_1260.csv",
        "panel": artifact_root / "unknown_state_diagnostic_1260_20260809" / "model_safe_signal_research_panel_1260.parquet",
        "security_master": artifact_root / "security_master_1260.csv",
        "anchors": artifact_root / "tradability_anchors_1260.csv",
        "intervals": artifact_root / "tradability_intervals_1260.csv",
        "actions": artifact_root / "corporate_actions_1260" / "official_idx_split_reverse_actions_1260.csv",
        "scope_exclusions": artifact_root / "strict_gate_1260_post_fallback" / "full_universe_scope_exclusions.csv",
        "signal_manifest": artifact_root / "unknown_state_diagnostic_1260_20260809" / "signal_research_1260_manifest.json",
        "signal_contract": Path(r"C:\Users\Sam\OneDrive\Documents\Project\idx-trade\docs\SIGNAL_RESEARCH_HLCV_CONTRACT.md"),
        "overlay_parquet": parsed.overlay_root / "open_recovery_overlay.parquet",
        "overlay_manifest": parsed.overlay_root / "manifest.json",
    }
    hashes = {}
    missing = []
    mismatches = []
    for name, path in paths.items():
        if not path.is_file():
            missing.append({"name": name, "path": str(path)})
            continue
        actual = sha256(path)
        hashes[name] = actual
        if name in PINNED and actual != PINNED[name]:
            mismatches.append({"name": name, "actual": actual, "expected": PINNED[name]})
    if mismatches:
        raise RuntimeError(f"PINNED_INPUT_HASH_MISMATCH: {mismatches}")

    calendar = pd.read_csv(paths["calendar"])
    calendar["date"] = pd.to_datetime(calendar["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    calendar["session_index"] = np.arange(len(calendar), dtype=np.int64)
    date_to_index = dict(zip(calendar["date"], calendar["session_index"]))

    panel = pd.read_parquet(paths["panel"])
    panel["ticker"] = panel["ticker"].astype(str).str.upper().str.strip()
    panel["date"] = pd.to_datetime(panel["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    panel["session_index"] = panel["date"].map(date_to_index)
    if panel["session_index"].isna().any() or panel.duplicated(["ticker", "date"]).any():
        raise RuntimeError("PANEL_SESSION_OR_IDENTITY_INVALID")
    panel["session_index"] = panel["session_index"].astype(np.int64)
    panel["base_open_support"] = (
        panel["open_available"].astype(bool)
        & pd.to_numeric(panel["open"], errors="coerce").gt(0)
        & pd.to_numeric(panel["open"], errors="coerce").notna()
    )
    panel["close_valid"] = pd.to_numeric(panel["close"], errors="coerce").gt(0)
    panel["ca_ok"] = panel["corporate_action_integrity_verified"].astype(bool)

    overlay = pd.read_parquet(paths["overlay_parquet"])
    overlay["ticker"] = overlay["ticker"].astype(str).str.upper().str.strip()
    overlay["date"] = pd.to_datetime(overlay["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    overlay_keys = set(zip(overlay["ticker"], overlay["date"]))
    panel["overlay_open_support"] = pd.Series(
        [(ticker, date) in overlay_keys for ticker, date in zip(panel["ticker"], panel["date"])],
        index=panel.index,
    )
    panel["open_support"] = panel["base_open_support"] | panel["overlay_open_support"]

    anchors = pd.read_csv(paths["anchors"])
    anchors["market"] = anchors["market"].astype(str).str.upper()
    anchors["state"] = anchors["state"].astype(str).str.upper()
    intervals = pd.read_csv(paths["intervals"])
    intervals["market"] = intervals["market"].astype(str).str.upper()
    states, state_conflicts = state_map_from_inputs(anchors, intervals, calendar)

    panel_keys = {
        (ticker, int(index)): (bool(open_support), bool(ca_ok), bool(close_valid))
        for ticker, index, open_support, ca_ok, close_valid in panel[
            ["ticker", "session_index", "open_support", "ca_ok", "close_valid"]
        ].itertuples(index=False)
    }

    def future_state(ticker: str, index: int, horizon: int) -> str:
        target = index + horizon
        if target >= len(calendar):
            return "NO_FUTURE_SESSION"
        return states.get((ticker, target), "UNKNOWN")

    def future_row(ticker: str, index: int, horizon: int) -> tuple[bool, bool, bool]:
        return panel_keys.get((ticker, index + horizon), (False, False, False))

    for horizon, label in ((1, "entry"), (5, "h5"), (10, "h10")):
        state_values = []
        open_values = []
        ca_values = []
        close_values = []
        for ticker, index in zip(panel["ticker"], panel["session_index"]):
            state_values.append(future_state(ticker, int(index), horizon))
            open_value, ca_value, close_value = future_row(ticker, int(index), horizon)
            open_values.append(open_value)
            ca_values.append(ca_value)
            close_values.append(close_value)
        panel[f"{label}_state"] = state_values
        panel[f"{label}_open_support"] = open_values
        panel[f"{label}_ca_ok"] = ca_values
        panel[f"{label}_close_valid"] = close_values

    panel["entry_open_support"] = (panel["entry_state"] == "ACTIVE") & panel["entry_open_support"]
    panel["h5_close_support"] = (panel["h5_state"] == "ACTIVE") & panel["h5_close_valid"]
    panel["h10_close_support"] = (panel["h10_state"] == "ACTIVE") & panel["h10_close_valid"]
    panel["h5_target_support"] = panel["entry_open_support"] & panel["h5_close_support"]
    panel["h10_target_support"] = panel["entry_open_support"] & panel["h10_close_support"]
    panel["both_target_support"] = panel["entry_open_support"] & panel["h5_close_support"] & panel["h10_close_support"]
    panel["ca_h5"] = (
        panel["ca_ok"] & panel["entry_state"].eq("ACTIVE") & panel["entry_ca_ok"]
        & panel["h5_state"].eq("ACTIVE") & panel["h5_ca_ok"]
    )
    panel["ca_h10"] = (
        panel["ca_ok"] & panel["entry_state"].eq("ACTIVE") & panel["entry_ca_ok"]
        & panel["h10_state"].eq("ACTIVE") & panel["h10_ca_ok"]
    )
    panel["ca_both"] = panel["ca_h5"] & panel["h10_state"].eq("ACTIVE") & panel["h10_ca_ok"]

    state_counts: dict[str, dict[str, int]] = {}
    for label in ("entry", "h5", "h10"):
        counts = panel[f"{label}_state"].value_counts().to_dict()
        state_counts[label] = {state: int(counts.get(state, 0)) for state in STATE_NAMES}

    group = panel.groupby(["session_index", "date"], sort=True)
    summary = group.agg(
        decision_rows=("ticker", "size"),
        open_t1_rows=("entry_open_support", "sum"),
        h5_close_rows=("h5_close_support", "sum"),
        h10_close_rows=("h10_close_support", "sum"),
        h5_target_rows=("h5_target_support", "sum"),
        h10_target_rows=("h10_target_support", "sum"),
        both_target_rows=("both_target_support", "sum"),
        ca_h5_rows=("ca_h5", "sum"),
        ca_h10_rows=("ca_h10", "sum"),
        ca_both_rows=("ca_both", "sum"),
    ).reset_index()
    for prefix in ("open_t1", "h5_close", "h10_close", "h5_target", "h10_target", "both_target", "ca_h5", "ca_h10", "ca_both"):
        summary[f"{prefix}_rate"] = summary[f"{prefix}_rows"] / summary["decision_rows"]
        summary[f"{prefix}_gate"] = summary[f"{prefix}_rate"] >= 0.90

    for label in ("entry", "h5", "h10"):
        for state in STATE_NAMES:
            state_frame = panel[f"{label}_state"].eq(state).groupby([panel["session_index"], panel["date"]]).sum()
            state_frame.index = pd.MultiIndex.from_tuples(state_frame.index, names=["session_index", "date"])
            state_frame = state_frame.rename(f"{label}_{state.lower()}_rows").reset_index()
            summary = summary.merge(state_frame, on=["session_index", "date"], how="left", validate="one_to_one")

    summary["eligible_consensus"] = summary["both_target_gate"] & summary["ca_both_gate"]
    summary["eligible_h5"] = summary["h5_target_gate"] & summary["ca_h5_gate"]
    summary["eligible_h10"] = summary["h10_target_gate"] & summary["ca_h10_gate"]
    summary = summary.sort_values("session_index").reset_index(drop=True)

    eligible = summary.loc[summary["eligible_consensus"], ["session_index", "date"]].copy()
    eligible["session_index"] = eligible["session_index"].astype(int)
    eligible_keys = set(eligible["session_index"].tolist())
    runs: list[list[int]] = []
    for index in sorted(eligible_keys):
        if not runs or index != runs[-1][-1] + 1:
            runs.append([index])
        else:
            runs[-1].append(index)
    run_summary = [
        {"length": len(run), "start_session_index": run[0], "end_session_index": run[-1]}
        for run in sorted(runs, key=lambda values: (-len(values), values[0]))
    ]
    longest_calendar_run = max((len(run) for run in runs), default=0)
    six_hundred_possible_by_eligible_sequence = len(eligible) >= 600
    six_hundred_possible_by_calendar_contiguity = longest_calendar_run >= 600

    summary_csv = parsed.output_dir / "v4_target_support_per_date.csv"
    identity_csv = parsed.output_dir / "v4_session_identities_1260.csv"
    eligible_csv = parsed.output_dir / "v4_eligible_consensus_sessions.csv"
    census_json = parsed.output_dir / "census_summary.json"
    manifest_json = parsed.output_dir / "manifest.json"
    summary.to_csv(summary_csv, index=False, lineterminator="\n")
    identities = summary[[
        "session_index", "date", "decision_rows", "eligible_h5", "eligible_h10", "eligible_consensus",
    ]].copy()
    identities["base_official_session"] = True
    identities = identities[[
        "session_index", "date", "base_official_session", "decision_rows", "eligible_h5", "eligible_h10", "eligible_consensus",
    ]]
    identities.to_csv(identity_csv, index=False, lineterminator="\n")
    eligible.to_csv(eligible_csv, index=False, lineterminator="\n")

    overall = {name: int(panel[name].sum()) for name in (
        "entry_open_support", "h5_close_support", "h10_close_support", "h5_target_support",
        "h10_target_support", "both_target_support", "ca_h5", "ca_h10", "ca_both",
    )}
    gate_counts = {name: int(summary[name].sum()) for name in (
        "open_t1_gate", "h5_target_gate", "h10_target_gate", "both_target_gate",
        "ca_h5_gate", "ca_h10_gate", "ca_both_gate", "eligible_consensus",
    )}
    summary_payload = {
        "schema_version": "v4_target_support_census_v1",
        "verdict": "BLOCKED_6X100_TARGET_SUPPORT",
        "outcome_blind": True,
        "model_fit": False,
        "outcomes_loaded": False,
        "provider_or_ca_acquisition": False,
        "decision_population": {
            "panel_rows": int(len(panel)),
            "panel_tickers": int(panel["ticker"].nunique()),
            "official_sessions": int(len(calendar)),
            "first_session": str(calendar["date"].iloc[0]),
            "last_session": str(calendar["date"].iloc[-1]),
            "signal_state_active_rows": int((panel["date"].notna()).sum()),
        },
        "overall_support_rows": overall,
        "gate_date_counts": gate_counts,
        "state_counts_by_leg": state_counts,
        "state_conflict_keys": state_conflicts,
        "overlay_rows_consumed": int(len(overlay)),
        "overlay_rows_used_as_open": int(panel["overlay_open_support"].sum()),
        "open_t1_support_before_overlay": int((panel["entry_state"].eq("ACTIVE") & panel["entry_open_support"] & ~panel["overlay_open_support"]).sum()),
        "eligible_consensus_sessions": int(len(eligible)),
        "eligible_session_sha256": sha256(eligible_csv),
        "longest_calendar_consecutive_eligible_run": int(longest_calendar_run),
        "consecutive_run_summary": run_summary[:20],
        "six_hundred_possible_by_eligible_sequence": six_hundred_possible_by_eligible_sequence,
        "six_hundred_possible_by_calendar_contiguity": six_hundred_possible_by_calendar_contiguity,
        "blockers": [
            "CONSENSUS_90_PERCENT_DATE_GATE_ONLY_264_OF_1260",
            "SIX_BY_100_REQUIRES_600_ELIGIBLE_SESSIONS_BUT_ONLY_264",
            "PINNED_SIGNAL_CONTRACT_PATH_MISSING",
            "STRICT_EXECUTION_GRADE_1260_REMAINS_FAIL",
        ],
        "pinned_signal_contract_path_missing": any(item["name"] == "signal_contract" for item in missing),
        "missing_pinned_inputs": missing,
        "input_hashes": hashes,
    }
    census_json.write_text(json.dumps(summary_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    outputs = {path.name: sha256(path) for path in (summary_csv, identity_csv, eligible_csv, census_json)}
    manifest = {
        "schema_version": "v4_target_support_census_manifest_v1",
        "status": "BLOCKED_6X100_TARGET_SUPPORT",
        "input_hashes": hashes,
        "outputs": outputs,
        "rows": int(len(summary)),
        "eligible_consensus_sessions": int(len(eligible)),
        "eligible_consensus_session_sha256": sha256(eligible_csv),
        "outcome_blind": True,
        "model_fit": False,
        "labels_or_outcomes_loaded": False,
        "provenance_blockers": missing,
        "scientific_contract_ambiguities": [
            "V4-2 does not define whether eligible-session consecutiveness is official-calendar or filtered-list based",
            "V4-2 does not define whether below-gate dates remain in the 100-session identity sequence",
            "V4-2 does not define whether H5/H10/consensus share one frozen identity list",
        ],
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for path in (summary_csv, identity_csv, eligible_csv, census_json, manifest_json):
        path.chmod(0o444)
    print(json.dumps({
        "verdict": summary_payload["verdict"],
        "dates": len(summary),
        "eligible_consensus_sessions": len(eligible),
        "eligible_session_sha256": sha256(eligible_csv),
        "longest_calendar_run": longest_calendar_run,
        "outputs": {path.name: sha256(path) for path in (summary_csv, identity_csv, eligible_csv, census_json, manifest_json)},
        "missing_pinned_inputs": missing,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
