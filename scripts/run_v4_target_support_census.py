"""Outcome-blind V4 H5/H10 target-support census.

This remediation consumes the accepted historical Open lineage instead of
falling back to the immutable signal panel's original Open column. It never
reads realized returns/labels, fits a model, calls a provider, or acquires CA.
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
    "open_derivative_panel": "a1dae0714971904b266a380be6bb96a2a4976068c9d60c54c8c43746826f7cab",
    "open_derivative_manifest": "1a6bcc9c7fbbd967cdc69f8876fe1d4aa94b46c0e466469a9643da59251deb14",
    "overlay_parquet": "2aeab3906434f48c15d9ed7a8fb073fdd3bafff362cedcc7b46f9bf16482ca41",
    "overlay_manifest": "dfb7219bddec77ced3e3aadfaa2d85d04c19e1d9fd9a8af1badba523ecf91977",
}

STATE_NAMES = ("ACTIVE", "NO_TRADE", "SUSPENDED", "UNKNOWN", "NO_FUTURE_SESSION")
REQUIRED_ELIGIBLE_SESSIONS = 600


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--open-derivative-root", type=Path, required=True)
    parser.add_argument("--overlay-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def normalize_identity(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["ticker"] = out["ticker"].astype(str).str.upper().str.strip()
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    return out


def state_map_from_inputs(
    anchors: pd.DataFrame,
    intervals: pd.DataFrame,
    dates: pd.DataFrame,
) -> tuple[dict[tuple[str, int], str], int]:
    date_to_index = dict(zip(dates["date"], dates["session_index"]))
    regular = anchors[anchors["market"].eq("REGULAR")].copy()
    regular["ticker"] = regular["ticker"].astype(str).str.upper().str.strip()
    regular["as_of_date"] = pd.to_datetime(regular["as_of_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    regular["session_index"] = regular["as_of_date"].map(date_to_index)
    grouped = regular.groupby(["ticker", "session_index"])["state"].agg(
        lambda values: tuple(sorted({str(value).upper() for value in values.dropna()}))
    ).reset_index(name="states")
    states = {
        (ticker, int(index)): (values[0] if len(values) == 1 else "UNKNOWN")
        for ticker, index, values in grouped.itertuples(index=False)
        if pd.notna(index)
    }

    regular_intervals = intervals[
        intervals["market"].isin(["REGULAR", "ALL"])
        & intervals["state"].astype(str).str.upper().eq("SUSPENDED")
    ]
    date_values = pd.to_datetime(dates["date"])
    for row in regular_intervals.itertuples(index=False):
        start = pd.Timestamp(row.effective_from).normalize()
        end = pd.Timestamp(row.effective_to).normalize() if pd.notna(row.effective_to) else date_values.iloc[-1]
        covered = dates.loc[(date_values >= start) & (date_values <= end), "session_index"]
        for index in covered:
            states.setdefault((str(row.ticker).upper().strip(), int(index)), "SUSPENDED")
    return states, int(len(grouped[grouped["states"].map(len).gt(1)]))


def validate_and_attach_open_lineage(
    panel: pd.DataFrame,
    derivative: pd.DataFrame,
    overlay: pd.DataFrame,
) -> dict[str, int]:
    """Attach accepted Open support with strict identity preservation.

    Priority is accepted Yahoo+TradingView derivative first, then the verified
    CA-scale overlay only on still-missing derivative rows. No price-ratio
    inference or synthetic Open is performed here.
    """
    derivative = normalize_identity(derivative)
    overlay = normalize_identity(overlay)
    if derivative.duplicated(["ticker", "date"]).any():
        raise RuntimeError("OPEN_DERIVATIVE_DUPLICATE_IDENTITY")
    if overlay.duplicated(["ticker", "date"]).any():
        raise RuntimeError("OPEN_OVERLAY_DUPLICATE_IDENTITY")
    if "open" not in derivative.columns:
        raise RuntimeError("OPEN_DERIVATIVE_MISSING_OPEN_COLUMN")

    base_keys = panel[["ticker", "date"]].copy()
    derivative_keys = derivative[["ticker", "date"]].copy()
    if len(derivative_keys) != len(base_keys):
        raise RuntimeError(
            f"OPEN_DERIVATIVE_ROW_COUNT_MISMATCH: panel={len(base_keys)} derivative={len(derivative_keys)}"
        )
    key_check = base_keys.merge(
        derivative_keys.assign(_derivative_key=True),
        on=["ticker", "date"],
        how="outer",
        indicator=True,
        validate="one_to_one",
    )
    if not key_check["_merge"].eq("both").all():
        raise RuntimeError("OPEN_DERIVATIVE_IDENTITY_MISMATCH")

    derivative_open = derivative[["ticker", "date", "open"]].rename(columns={"open": "accepted_derivative_open"})
    merged = panel.merge(derivative_open, on=["ticker", "date"], how="left", validate="one_to_one")
    derivative_numeric = pd.to_numeric(merged["accepted_derivative_open"], errors="coerce")
    merged["derivative_open_support"] = derivative_numeric.notna() & derivative_numeric.gt(0)

    overlay_keys = set(zip(overlay["ticker"], overlay["date"]))
    panel_key_set = set(zip(merged["ticker"], merged["date"]))
    if not overlay_keys.issubset(panel_key_set):
        raise RuntimeError("OPEN_OVERLAY_HAS_KEYS_OUTSIDE_SIGNAL_PANEL")
    merged["overlay_key"] = [
        (ticker, date) in overlay_keys for ticker, date in zip(merged["ticker"], merged["date"])
    ]
    merged["overlay_incremental_open_support"] = merged["overlay_key"] & ~merged["derivative_open_support"]
    merged["open_support"] = merged["derivative_open_support"] | merged["overlay_incremental_open_support"]

    # Replace caller frame in place so downstream code retains the exact signal population.
    for column in (
        "accepted_derivative_open",
        "derivative_open_support",
        "overlay_key",
        "overlay_incremental_open_support",
        "open_support",
    ):
        panel[column] = merged[column].to_numpy()

    return {
        "derivative_rows": int(len(derivative)),
        "derivative_supported_rows": int(panel["derivative_open_support"].sum()),
        "overlay_rows": int(len(overlay)),
        "overlay_keys_overlapping_derivative_support": int((panel["overlay_key"] & panel["derivative_open_support"]).sum()),
        "overlay_incremental_supported_rows": int(panel["overlay_incremental_open_support"].sum()),
        "final_supported_rows": int(panel["open_support"].sum()),
    }


def main() -> int:
    parsed = parse_args()
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
        "open_derivative_panel": parsed.open_derivative_root / "execution_open_candidate_panel_yahoo_tradingview.parquet",
        "open_derivative_manifest": parsed.open_derivative_root / "artifact_manifest.json",
        "overlay_parquet": parsed.overlay_root / "open_recovery_overlay.parquet",
        "overlay_manifest": parsed.overlay_root / "manifest.json",
    }
    hashes: dict[str, str] = {}
    missing: list[dict[str, str]] = []
    mismatches: list[dict[str, str]] = []
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
    required_names = set(PINNED)
    absent_required = sorted(required_names - set(hashes))
    if absent_required:
        raise RuntimeError(f"PINNED_REQUIRED_INPUT_MISSING: {absent_required}")

    calendar = pd.read_csv(paths["calendar"])
    calendar["date"] = pd.to_datetime(calendar["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    calendar["session_index"] = np.arange(len(calendar), dtype=np.int64)
    date_to_index = dict(zip(calendar["date"], calendar["session_index"]))

    panel = normalize_identity(pd.read_parquet(paths["panel"]))
    panel["session_index"] = panel["date"].map(date_to_index)
    if panel["session_index"].isna().any() or panel.duplicated(["ticker", "date"]).any():
        raise RuntimeError("PANEL_SESSION_OR_IDENTITY_INVALID")
    panel["session_index"] = panel["session_index"].astype(np.int64)
    panel_open = pd.to_numeric(panel["open"], errors="coerce")
    panel["immutable_panel_open_support"] = (
        panel["open_available"].astype(bool) & panel_open.notna() & panel_open.gt(0)
    )
    panel["close_valid"] = pd.to_numeric(panel["close"], errors="coerce").gt(0)
    panel["ca_ok"] = panel["corporate_action_integrity_verified"].astype(bool)

    derivative = pd.read_parquet(paths["open_derivative_panel"])
    overlay = pd.read_parquet(paths["overlay_parquet"])
    open_lineage = validate_and_attach_open_lineage(panel, derivative, overlay)

    anchors = pd.read_csv(paths["anchors"])
    anchors["market"] = anchors["market"].astype(str).str.upper()
    anchors["state"] = anchors["state"].astype(str).str.upper()
    intervals = pd.read_csv(paths["intervals"])
    intervals["market"] = intervals["market"].astype(str).str.upper()
    states, state_conflicts = state_map_from_inputs(anchors, intervals, calendar)

    panel_keys = {
        (ticker, int(index)): (
            bool(immutable_open),
            bool(derivative_open),
            bool(final_open),
            bool(ca_ok),
            bool(close_valid),
        )
        for ticker, index, immutable_open, derivative_open, final_open, ca_ok, close_valid in panel[
            [
                "ticker",
                "session_index",
                "immutable_panel_open_support",
                "derivative_open_support",
                "open_support",
                "ca_ok",
                "close_valid",
            ]
        ].itertuples(index=False)
    }

    def future_state(ticker: str, index: int, horizon: int) -> str:
        target = index + horizon
        if target >= len(calendar):
            return "NO_FUTURE_SESSION"
        return states.get((ticker, target), "UNKNOWN")

    def future_row(ticker: str, index: int, horizon: int) -> tuple[bool, bool, bool, bool, bool]:
        return panel_keys.get((ticker, index + horizon), (False, False, False, False, False))

    for horizon, label in ((1, "entry"), (5, "h5"), (10, "h10")):
        state_values: list[str] = []
        immutable_open_values: list[bool] = []
        derivative_open_values: list[bool] = []
        final_open_values: list[bool] = []
        ca_values: list[bool] = []
        close_values: list[bool] = []
        for ticker, index in zip(panel["ticker"], panel["session_index"]):
            state_values.append(future_state(ticker, int(index), horizon))
            immutable_open, derivative_open, final_open, ca_value, close_value = future_row(ticker, int(index), horizon)
            immutable_open_values.append(immutable_open)
            derivative_open_values.append(derivative_open)
            final_open_values.append(final_open)
            ca_values.append(ca_value)
            close_values.append(close_value)
        panel[f"{label}_state"] = state_values
        panel[f"{label}_immutable_open_support"] = immutable_open_values
        panel[f"{label}_derivative_open_support"] = derivative_open_values
        panel[f"{label}_open_support"] = final_open_values
        panel[f"{label}_ca_ok"] = ca_values
        panel[f"{label}_close_valid"] = close_values

    active_entry = panel["entry_state"].eq("ACTIVE")
    panel["entry_immutable_open_support"] = active_entry & panel["entry_immutable_open_support"]
    panel["entry_derivative_open_support"] = active_entry & panel["entry_derivative_open_support"]
    panel["entry_open_support"] = active_entry & panel["entry_open_support"]
    panel["h5_close_support"] = panel["h5_state"].eq("ACTIVE") & panel["h5_close_valid"]
    panel["h10_close_support"] = panel["h10_state"].eq("ACTIVE") & panel["h10_close_valid"]
    panel["h5_target_support"] = panel["entry_open_support"] & panel["h5_close_support"]
    panel["h10_target_support"] = panel["entry_open_support"] & panel["h10_close_support"]
    panel["both_target_support"] = panel["entry_open_support"] & panel["h5_close_support"] & panel["h10_close_support"]
    panel["ca_h5"] = (
        panel["ca_ok"]
        & panel["entry_state"].eq("ACTIVE")
        & panel["entry_ca_ok"]
        & panel["h5_state"].eq("ACTIVE")
        & panel["h5_ca_ok"]
    )
    panel["ca_h10"] = (
        panel["ca_ok"]
        & panel["entry_state"].eq("ACTIVE")
        & panel["entry_ca_ok"]
        & panel["h10_state"].eq("ACTIVE")
        & panel["h10_ca_ok"]
    )
    panel["ca_both"] = panel["ca_h5"] & panel["h10_state"].eq("ACTIVE") & panel["h10_ca_ok"]

    state_counts: dict[str, dict[str, int]] = {}
    for label in ("entry", "h5", "h10"):
        counts = panel[f"{label}_state"].value_counts().to_dict()
        state_counts[label] = {state: int(counts.get(state, 0)) for state in STATE_NAMES}

    group = panel.groupby(["session_index", "date"], sort=True)
    summary = group.agg(
        decision_rows=("ticker", "size"),
        open_t1_immutable_rows=("entry_immutable_open_support", "sum"),
        open_t1_derivative_rows=("entry_derivative_open_support", "sum"),
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
    for prefix in (
        "open_t1_immutable",
        "open_t1_derivative",
        "open_t1",
        "h5_close",
        "h10_close",
        "h5_target",
        "h10_target",
        "both_target",
        "ca_h5",
        "ca_h10",
        "ca_both",
    ):
        summary[f"{prefix}_rate"] = summary[f"{prefix}_rows"] / summary["decision_rows"]
    for prefix in ("open_t1", "h5_target", "h10_target", "both_target", "ca_h5", "ca_h10", "ca_both"):
        summary[f"{prefix}_gate"] = summary[f"{prefix}_rate"] >= 0.90

    for label in ("entry", "h5", "h10"):
        for state in STATE_NAMES:
            state_frame = panel[f"{label}_state"].eq(state).groupby([panel["session_index"], panel["date"]]).sum()
            state_frame.index = pd.MultiIndex.from_tuples(state_frame.index, names=["session_index", "date"])
            state_frame = state_frame.rename(f"{label}_{state.lower()}_rows").reset_index()
            summary = summary.merge(state_frame, on=["session_index", "date"], how="left", validate="one_to_one")

    summary["eligible_h5"] = summary["h5_target_gate"] & summary["ca_h5_gate"]
    summary["eligible_h10"] = summary["h10_target_gate"] & summary["ca_h10_gate"]
    summary["eligible_consensus"] = summary["both_target_gate"] & summary["ca_both_gate"]
    summary = summary.sort_values("session_index").reset_index(drop=True)

    eligible_h5 = summary.loc[summary["eligible_h5"], ["session_index", "date"]].copy()
    eligible_h10 = summary.loc[summary["eligible_h10"], ["session_index", "date"]].copy()
    eligible_consensus = summary.loc[summary["eligible_consensus"], ["session_index", "date"]].copy()
    feasible = {
        "h5": len(eligible_h5) >= REQUIRED_ELIGIBLE_SESSIONS,
        "h10": len(eligible_h10) >= REQUIRED_ELIGIBLE_SESSIONS,
        "consensus": len(eligible_consensus) >= REQUIRED_ELIGIBLE_SESSIONS,
    }
    support_feasible = all(feasible.values())
    verdict = "V4_TARGET_SUPPORT_6X100_FEASIBLE" if support_feasible else "V4_TARGET_SUPPORT_BLOCKED_6X100_INFEASIBLE"

    summary_csv = parsed.output_dir / "v4_target_support_per_date.csv"
    identity_csv = parsed.output_dir / "v4_session_identities_1260.csv"
    eligible_h5_csv = parsed.output_dir / "v4_eligible_h5_sessions.csv"
    eligible_h10_csv = parsed.output_dir / "v4_eligible_h10_sessions.csv"
    eligible_consensus_csv = parsed.output_dir / "v4_eligible_consensus_sessions.csv"
    census_json = parsed.output_dir / "census_summary.json"
    manifest_json = parsed.output_dir / "manifest.json"

    summary.to_csv(summary_csv, index=False, lineterminator="\n")
    identities = summary[[
        "session_index", "date", "decision_rows", "eligible_h5", "eligible_h10", "eligible_consensus",
    ]].copy()
    identities.insert(2, "base_official_session", True)
    identities.to_csv(identity_csv, index=False, lineterminator="\n")
    eligible_h5.to_csv(eligible_h5_csv, index=False, lineterminator="\n")
    eligible_h10.to_csv(eligible_h10_csv, index=False, lineterminator="\n")
    eligible_consensus.to_csv(eligible_consensus_csv, index=False, lineterminator="\n")

    overall = {name: int(panel[name].sum()) for name in (
        "entry_immutable_open_support",
        "entry_derivative_open_support",
        "entry_open_support",
        "h5_close_support",
        "h10_close_support",
        "h5_target_support",
        "h10_target_support",
        "both_target_support",
        "ca_h5",
        "ca_h10",
        "ca_both",
    )}
    gate_counts = {name: int(summary[name].sum()) for name in (
        "open_t1_gate",
        "h5_target_gate",
        "h10_target_gate",
        "both_target_gate",
        "ca_h5_gate",
        "ca_h10_gate",
        "ca_both_gate",
        "eligible_h5",
        "eligible_h10",
        "eligible_consensus",
    )}
    provenance_warnings = [item for item in missing if item["name"] == "signal_contract"]
    summary_payload = {
        "schema_version": "v4_target_support_census_v1_1_open_lineage_remediation",
        "verdict": verdict,
        "support_feasible": support_feasible,
        "required_eligible_sessions_per_horizon": REQUIRED_ELIGIBLE_SESSIONS,
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
        },
        "open_lineage": open_lineage,
        "overall_support_rows": overall,
        "gate_date_counts": gate_counts,
        "eligible_session_counts": {
            "h5": int(len(eligible_h5)),
            "h10": int(len(eligible_h10)),
            "consensus": int(len(eligible_consensus)),
        },
        "six_by_100_feasible": feasible,
        "state_counts_by_leg": state_counts,
        "state_conflict_keys": state_conflicts,
        "input_hashes": hashes,
        "provenance_warnings": provenance_warnings,
        "interpretation": {
            "consecutive_semantics": "Consecutive eligible signal sessions means adjacency in the filtered eligible-session sequence; calendar-adjacent runs are diagnostic only.",
            "below_gate_dates": "Dates below the locked 90% gate remain visible in the full identity/per-date census but do not enter the relevant eligible-session sequence.",
            "shared_fold_identity": "Whether H5, H10, and consensus ultimately share one fold list remains a V4-3 preregistration choice; this census tests technical feasibility for all three separately.",
        },
    }
    census_json.write_text(json.dumps(summary_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    outputs_without_manifest = {
        path.name: sha256(path)
        for path in (summary_csv, identity_csv, eligible_h5_csv, eligible_h10_csv, eligible_consensus_csv, census_json)
    }
    manifest = {
        "schema_version": "v4_target_support_census_manifest_v1_1",
        "status": verdict,
        "input_hashes": hashes,
        "outputs": outputs_without_manifest,
        "rows": int(len(summary)),
        "eligible_session_counts": summary_payload["eligible_session_counts"],
        "six_by_100_feasible": feasible,
        "outcome_blind": True,
        "model_fit": False,
        "labels_or_outcomes_loaded": False,
        "provenance_warnings": provenance_warnings,
        "supersedes_decision_use_of": "research/idx-v4-target-support-census-v1@5f3c2d7b66cf66b2676ba0a409cdc2f4c9ca8f5d",
        "supersession_reason": "Prior census omitted the accepted Yahoo+TradingView Open derivative and therefore materially understated Open(t+1) support.",
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for path in (
        summary_csv,
        identity_csv,
        eligible_h5_csv,
        eligible_h10_csv,
        eligible_consensus_csv,
        census_json,
        manifest_json,
    ):
        path.chmod(0o444)

    print(json.dumps({
        "verdict": verdict,
        "support_feasible": support_feasible,
        "eligible_session_counts": summary_payload["eligible_session_counts"],
        "open_lineage": open_lineage,
        "outputs": {
            path.name: sha256(path)
            for path in (
                summary_csv,
                identity_csv,
                eligible_h5_csv,
                eligible_h10_csv,
                eligible_consensus_csv,
                census_json,
                manifest_json,
            )
        },
        "provenance_warnings": provenance_warnings,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
