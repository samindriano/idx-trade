"""Outcome-blind V4-3 primary-liquid support and fold-identity materializer.

This script refreshes the already accepted target-support census on the V4-3
frozen primary-liquid decision universe. It does not materialize returns,
target ranks, model predictions, IC, Top-30 performance, or any protected
outcome.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from idx_trade.ranking_v4_3_preregistration import (
    build_primary_liquid_state,
    materialize_validation_folds,
)


PINNED = {
    "calendar": "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a",
    "panel": "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76",
    "anchors": "33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e",
    "intervals": "fd255f21a3accd763286fbd0b0c6d9d501d618ae611cc0681017e001bdba83cc",
    "signal_manifest": "b703f1f80aa062accfb4387e5c457458c88aec77351e7dd19342b9c45873cd1a",
    "open_derivative_panel": "a1dae0714971904b266a380be6bb96a2a4976068c9d60c54c8c43746826f7cab",
    "open_derivative_manifest": "1a6bcc9c7fbbd967cdc69f8876fe1d4aa94b46c0e466469a9643da59251deb14",
    "overlay_parquet": "2aeab3906434f48c15d9ed7a8fb073fdd3bafff362cedcc7b46f9bf16482ca41",
    "overlay_manifest": "dfb7219bddec77ced3e3aadfaa2d85d04c19e1d9fd9a8af1badba523ecf91977",
    "signal_contract": "ffff2d21b275744a3a2b74c2f7d32be7b589f3c46cf9950c5ff45c48e5bffd73",
}

STATE_NAMES = ("ACTIVE", "NO_TRADE", "SUSPENDED", "UNKNOWN", "AMBIGUOUS", "NO_FUTURE_SESSION")
FORBIDDEN_COLUMN_TOKENS = (
    "target_rank",
    "realized_return",
    "binary_target",
    "label_status",
    "actual_up",
    "outcome",
)


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
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def normalize_identity(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["ticker"] = (
        out["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    )
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if out["date"].isna().any():
        raise ValueError("identity contains invalid date")
    return out


def state_map_from_inputs(
    anchors: pd.DataFrame,
    intervals: pd.DataFrame,
    calendar: pd.DataFrame,
) -> tuple[dict[tuple[str, int], str], int]:
    date_to_index = dict(zip(calendar["date"], calendar["session_index"]))
    regular = anchors[anchors["market"].eq("REGULAR")].copy()
    regular["ticker"] = (
        regular["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    )
    regular["as_of_date"] = (
        pd.to_datetime(regular["as_of_date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    )
    regular["session_index"] = regular["as_of_date"].map(date_to_index)
    regular = regular[regular["session_index"].notna()].copy()
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
    ].copy()
    calendar_dates = calendar["date"]
    for row in regular_intervals.itertuples(index=False):
        start = pd.Timestamp(row.effective_from).tz_localize(None).normalize()
        end = (
            pd.Timestamp(row.effective_to).tz_localize(None).normalize()
            if pd.notna(row.effective_to)
            else pd.Timestamp(calendar_dates.iloc[-1])
        )
        covered = calendar.loc[
            (calendar_dates >= start) & (calendar_dates <= end), "session_index"
        ]
        ticker = str(row.ticker).upper().replace(".JK", "").strip()
        for index in covered:
            states.setdefault((ticker, int(index)), "SUSPENDED")
    conflicts = int(grouped["states"].map(len).gt(1).sum())
    return states, conflicts


def attach_open_support(
    panel: pd.DataFrame,
    derivative: pd.DataFrame,
    overlay: pd.DataFrame,
) -> dict[str, int]:
    derivative = normalize_identity(derivative)
    overlay = normalize_identity(overlay)
    if derivative.duplicated(["ticker", "date"]).any():
        raise RuntimeError("OPEN_DERIVATIVE_DUPLICATE_IDENTITY")
    if overlay.duplicated(["ticker", "date"]).any():
        raise RuntimeError("OPEN_OVERLAY_DUPLICATE_IDENTITY")
    if "open" not in derivative.columns:
        raise RuntimeError("OPEN_DERIVATIVE_MISSING_OPEN_COLUMN")

    base_keys = panel[["ticker", "date"]]
    derivative_keys = derivative[["ticker", "date"]]
    if len(base_keys) != len(derivative_keys):
        raise RuntimeError("OPEN_DERIVATIVE_ROW_COUNT_MISMATCH")
    identity = base_keys.merge(
        derivative_keys.assign(_present=True),
        on=["ticker", "date"],
        how="outer",
        indicator=True,
        validate="one_to_one",
    )
    if not identity["_merge"].eq("both").all():
        raise RuntimeError("OPEN_DERIVATIVE_IDENTITY_MISMATCH")

    derivative_open = derivative[["ticker", "date", "open"]].rename(
        columns={"open": "_accepted_open"}
    )
    merged = panel[["ticker", "date"]].merge(
        derivative_open,
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )
    numeric_open = pd.to_numeric(merged["_accepted_open"], errors="coerce")
    derivative_support = numeric_open.notna() & numeric_open.gt(0.0)

    overlay_keys = set(zip(overlay["ticker"], overlay["date"]))
    panel_keys = set(zip(panel["ticker"], panel["date"]))
    if not overlay_keys.issubset(panel_keys):
        raise RuntimeError("OPEN_OVERLAY_HAS_KEYS_OUTSIDE_SIGNAL_PANEL")
    overlay_key = pd.Series(
        [(ticker, date) in overlay_keys for ticker, date in zip(panel["ticker"], panel["date"])],
        index=panel.index,
        dtype=bool,
    )
    panel["derivative_open_support"] = derivative_support.to_numpy(dtype=bool)
    panel["overlay_incremental_open_support"] = (
        overlay_key & ~panel["derivative_open_support"]
    )
    panel["open_support"] = (
        panel["derivative_open_support"] | panel["overlay_incremental_open_support"]
    )
    return {
        "derivative_supported_rows": int(panel["derivative_open_support"].sum()),
        "overlay_rows": int(len(overlay)),
        "overlay_incremental_rows": int(panel["overlay_incremental_open_support"].sum()),
        "final_supported_rows": int(panel["open_support"].sum()),
    }


def main() -> int:
    parsed = parse_args()
    if parsed.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT: {parsed.output_dir}")
    parsed.output_dir.mkdir(parents=True)

    paths = {
        "calendar": parsed.artifact_root / "official_exchange_sessions_1260.csv",
        "panel": parsed.artifact_root / "unknown_state_diagnostic_1260_20260809" / "model_safe_signal_research_panel_1260.parquet",
        "anchors": parsed.artifact_root / "tradability_anchors_1260.csv",
        "intervals": parsed.artifact_root / "tradability_intervals_1260.csv",
        "signal_manifest": parsed.artifact_root / "unknown_state_diagnostic_1260_20260809" / "signal_research_1260_manifest.json",
        "open_derivative_panel": parsed.open_derivative_root / "execution_open_candidate_panel_yahoo_tradingview.parquet",
        "open_derivative_manifest": parsed.open_derivative_root / "artifact_manifest.json",
        "overlay_parquet": parsed.overlay_root / "open_recovery_overlay.parquet",
        "overlay_manifest": parsed.overlay_root / "manifest.json",
        "signal_contract": parsed.repo_root / "docs" / "SIGNAL_RESEARCH_HLCV_CONTRACT.md",
        "preregistration": parsed.repo_root / "config" / "ranking_v4_3_preregistration.json",
    }
    hashes: dict[str, str] = {}
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise RuntimeError(f"REQUIRED_INPUT_MISSING: {missing}")
    for name, path in paths.items():
        hashes[name] = sha256(path)
        if name in PINNED and hashes[name] != PINNED[name]:
            raise RuntimeError(
                f"PINNED_INPUT_HASH_MISMATCH {name}: {hashes[name]} != {PINNED[name]}"
            )

    config = json.loads(paths["preregistration"].read_text(encoding="utf-8"))
    if config.get("status") != "V4_3_SCIENTIFIC_CONFIG_LOCKED_PRIMARY_LIQUID_SUPPORT_AND_FOLD_BYTES_PENDING":
        raise RuntimeError("V4_3_PREREGISTRATION_STATUS_NOT_LOCKED_PENDING_SUPPORT")
    if config["decision_universe"]["id"] != "V4_PRIMARY_LIQUID_CAUSAL_V1":
        raise RuntimeError("V4_3_UNIVERSE_CONTRACT_MISMATCH")
    if config["validation"]["selection_rule"] != "last 600 chronologically ordered consensus-eligible sessions":
        raise RuntimeError("V4_3_FOLD_SELECTION_CONTRACT_MISMATCH")

    calendar = pd.read_csv(paths["calendar"])
    calendar["date"] = pd.to_datetime(calendar["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if calendar["date"].isna().any() or calendar["date"].duplicated().any():
        raise RuntimeError("OFFICIAL_CALENDAR_INVALID")
    calendar = calendar.sort_values("date", kind="mergesort").reset_index(drop=True)
    calendar["session_index"] = np.arange(len(calendar), dtype=np.int64)
    date_to_index = dict(zip(calendar["date"], calendar["session_index"]))

    panel = normalize_identity(pd.read_parquet(paths["panel"]))
    forbidden = [
        column for column in panel.columns
        if any(token in str(column).lower() for token in FORBIDDEN_COLUMN_TOKENS)
    ]
    if forbidden:
        raise RuntimeError(f"OUTCOME_OR_LABEL_COLUMN_PRESENT: {sorted(forbidden)}")
    if panel.duplicated(["ticker", "date"]).any():
        raise RuntimeError("SIGNAL_PANEL_DUPLICATE_IDENTITY")
    panel["session_index"] = panel["date"].map(date_to_index)
    if panel["session_index"].isna().any():
        raise RuntimeError("SIGNAL_PANEL_DATE_OUTSIDE_CALENDAR")
    panel["session_index"] = panel["session_index"].astype(int)
    panel["close_valid"] = pd.to_numeric(panel["close"], errors="coerce").gt(0.0)
    panel["ca_ok"] = panel["corporate_action_integrity_verified"].astype(bool)

    derivative = pd.read_parquet(paths["open_derivative_panel"])
    overlay = pd.read_parquet(paths["overlay_parquet"])
    open_stats = attach_open_support(panel, derivative, overlay)

    primary = build_primary_liquid_state(panel, calendar["date"])
    primary_keys = primary[["ticker", "date", "universe_primary_liquid"]]
    decision = panel.merge(
        primary_keys,
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )
    if decision["universe_primary_liquid"].isna().any():
        raise RuntimeError("PRIMARY_LIQUID_STATE_IDENTITY_MISMATCH")
    decision = decision[decision["universe_primary_liquid"].astype(bool)].copy()
    if decision.empty:
        raise RuntimeError("PRIMARY_LIQUID_DECISION_UNIVERSE_EMPTY")

    anchors = pd.read_csv(paths["anchors"])
    anchors["market"] = anchors["market"].astype(str).str.upper()
    anchors["state"] = anchors["state"].astype(str).str.upper()
    intervals = pd.read_csv(paths["intervals"])
    intervals["market"] = intervals["market"].astype(str).str.upper()
    intervals["state"] = intervals["state"].astype(str).str.upper()
    states, state_conflicts = state_map_from_inputs(anchors, intervals, calendar)

    panel_keys = {
        (ticker, int(index)): (bool(open_support), bool(ca_ok), bool(close_valid))
        for ticker, index, open_support, ca_ok, close_valid in panel[
            ["ticker", "session_index", "open_support", "ca_ok", "close_valid"]
        ].itertuples(index=False)
    }

    def future_state(ticker: str, index: int, horizon: int) -> str:
        target = int(index) + int(horizon)
        if target >= len(calendar):
            return "NO_FUTURE_SESSION"
        return states.get((ticker, target), "UNKNOWN")

    def future_row(ticker: str, index: int, horizon: int) -> tuple[bool, bool, bool]:
        return panel_keys.get((ticker, int(index) + int(horizon)), (False, False, False))

    for horizon, label in ((1, "entry"), (5, "h5"), (10, "h10")):
        state_values: list[str] = []
        open_values: list[bool] = []
        ca_values: list[bool] = []
        close_values: list[bool] = []
        for ticker, index in zip(decision["ticker"], decision["session_index"]):
            state_values.append(future_state(ticker, int(index), horizon))
            open_value, ca_value, close_value = future_row(ticker, int(index), horizon)
            open_values.append(open_value)
            ca_values.append(ca_value)
            close_values.append(close_value)
        decision[f"{label}_state"] = state_values
        decision[f"{label}_open_support"] = open_values
        decision[f"{label}_ca_ok"] = ca_values
        decision[f"{label}_close_valid"] = close_values

    decision["entry_open_support"] = decision["entry_state"].eq("ACTIVE") & decision["entry_open_support"]
    decision["h5_close_support"] = decision["h5_state"].eq("ACTIVE") & decision["h5_close_valid"]
    decision["h10_close_support"] = decision["h10_state"].eq("ACTIVE") & decision["h10_close_valid"]
    decision["h5_target_support"] = decision["entry_open_support"] & decision["h5_close_support"]
    decision["h10_target_support"] = decision["entry_open_support"] & decision["h10_close_support"]
    decision["both_target_support"] = decision["h5_target_support"] & decision["h10_close_support"]
    decision["ca_h5"] = (
        decision["ca_ok"]
        & decision["entry_state"].eq("ACTIVE")
        & decision["entry_ca_ok"]
        & decision["h5_state"].eq("ACTIVE")
        & decision["h5_ca_ok"]
    )
    decision["ca_h10"] = (
        decision["ca_ok"]
        & decision["entry_state"].eq("ACTIVE")
        & decision["entry_ca_ok"]
        & decision["h10_state"].eq("ACTIVE")
        & decision["h10_ca_ok"]
    )
    decision["ca_both"] = decision["ca_h5"] & decision["h10_state"].eq("ACTIVE") & decision["h10_ca_ok"]

    grouped = decision.groupby(["session_index", "date"], sort=True).agg(
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
    summary = calendar[["session_index", "date"]].merge(
        grouped,
        on=["session_index", "date"],
        how="left",
        validate="one_to_one",
    )
    row_columns = [column for column in summary.columns if column.endswith("_rows")]
    summary[row_columns] = summary[row_columns].fillna(0).astype(int)

    for prefix in ("open_t1", "h5_target", "h10_target", "both_target", "ca_h5", "ca_h10", "ca_both"):
        rate = np.where(
            summary["decision_rows"].gt(0),
            summary[f"{prefix}_rows"] / summary["decision_rows"],
            np.nan,
        )
        summary[f"{prefix}_rate"] = rate
        summary[f"{prefix}_gate"] = summary["decision_rows"].gt(0) & (summary[f"{prefix}_rate"] >= 0.90)

    summary["eligible_h5"] = summary["h5_target_gate"] & summary["ca_h5_gate"]
    summary["eligible_h10"] = summary["h10_target_gate"] & summary["ca_h10_gate"]
    summary["eligible_consensus"] = summary["both_target_gate"] & summary["ca_both_gate"]

    eligible_h5 = summary.loc[summary["eligible_h5"], ["session_index", "date"]].copy()
    eligible_h10 = summary.loc[summary["eligible_h10"], ["session_index", "date"]].copy()
    eligible_consensus = summary.loc[summary["eligible_consensus"], ["session_index", "date"]].copy()

    support_feasible = len(eligible_consensus) >= 600
    folds = (
        materialize_validation_folds(eligible_consensus)
        if support_feasible
        else pd.DataFrame(
            columns=[
                "fold",
                "validation_position",
                "eligible_sequence_position_zero_based",
                "session_index",
                "date",
                "purge_length_official_sessions",
                "max_training_signal_session_index",
            ]
        )
    )

    fold_summary_rows: list[dict[str, object]] = []
    if support_feasible:
        for fold, block in folds.groupby("fold", sort=True):
            max_train = int(block["max_training_signal_session_index"].iloc[0])
            fold_summary_rows.append(
                {
                    "fold": int(fold),
                    "validation_start_session_index": int(block["session_index"].min()),
                    "validation_end_session_index": int(block["session_index"].max()),
                    "validation_start_date": pd.Timestamp(block["date"].iloc[0]),
                    "validation_end_date": pd.Timestamp(block["date"].iloc[-1]),
                    "max_training_signal_session_index": max_train,
                    "h5_training_eligible_dates": int((eligible_h5["session_index"] <= max_train).sum()),
                    "h10_training_eligible_dates": int((eligible_h10["session_index"] <= max_train).sum()),
                }
            )
    fold_summary = pd.DataFrame(fold_summary_rows)

    outputs = {
        "support_per_date": parsed.output_dir / "v4_3_primary_liquid_support_per_date.csv",
        "eligible_h5": parsed.output_dir / "v4_3_eligible_h5_sessions.csv",
        "eligible_h10": parsed.output_dir / "v4_3_eligible_h10_sessions.csv",
        "eligible_consensus": parsed.output_dir / "v4_3_eligible_consensus_sessions.csv",
        "fold_identities": parsed.output_dir / "v4_3_validation_folds.csv",
        "fold_summary": parsed.output_dir / "v4_3_fold_summary.csv",
        "summary": parsed.output_dir / "census_summary.json",
        "manifest": parsed.output_dir / "manifest.json",
    }
    summary.to_csv(outputs["support_per_date"], index=False, lineterminator="\n")
    eligible_h5.to_csv(outputs["eligible_h5"], index=False, lineterminator="\n")
    eligible_h10.to_csv(outputs["eligible_h10"], index=False, lineterminator="\n")
    eligible_consensus.to_csv(outputs["eligible_consensus"], index=False, lineterminator="\n")
    folds.to_csv(outputs["fold_identities"], index=False, lineterminator="\n")
    fold_summary.to_csv(outputs["fold_summary"], index=False, lineterminator="\n")

    state_counts = {}
    for label in ("entry", "h5", "h10"):
        counts = decision[f"{label}_state"].value_counts().to_dict()
        state_counts[label] = {state: int(counts.get(state, 0)) for state in STATE_NAMES}

    verdict = (
        "V4_3_PRIMARY_LIQUID_SUPPORT_6X100_FEASIBLE"
        if support_feasible
        else "V4_3_PRIMARY_LIQUID_SUPPORT_BLOCKED_6X100_INFEASIBLE"
    )
    payload = {
        "schema_version": "v4_3_primary_liquid_support_census_v1",
        "verdict": verdict,
        "outcome_blind": True,
        "returns_or_target_ranks_loaded": False,
        "model_fit": False,
        "provider_calls": False,
        "decision_universe": {
            "id": "V4_PRIMARY_LIQUID_CAUSAL_V1",
            "rows": int(len(decision)),
            "tickers": int(decision["ticker"].nunique()),
            "sessions_with_rows": int(decision["date"].nunique()),
            "threshold_idr": 1_000_000_000.0,
            "lookback_official_sessions": 60,
            "minimum_observations": 20,
        },
        "open_lineage": open_stats,
        "eligible_session_counts": {
            "h5": int(len(eligible_h5)),
            "h10": int(len(eligible_h10)),
            "consensus": int(len(eligible_consensus)),
        },
        "folds_materialized": int(folds["fold"].nunique()) if len(folds) else 0,
        "validation_rows": int(len(folds)),
        "state_counts_by_leg": state_counts,
        "state_conflict_keys": state_conflicts,
        "input_hashes": hashes,
    }
    outputs["summary"].write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    pre_manifest = {
        name: sha256(path)
        for name, path in outputs.items()
        if name not in {"manifest"} and path.is_file()
    }
    manifest = {
        "schema_version": "v4_3_primary_liquid_support_manifest_v1",
        "status": verdict,
        "input_hashes": hashes,
        "outputs": pre_manifest,
        "outcome_blind": True,
        "returns_or_target_ranks_loaded": False,
        "model_fit": False,
        "provider_calls": False,
    }
    outputs["manifest"].write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "verdict": verdict,
                "decision_rows": len(decision),
                "eligible_session_counts": payload["eligible_session_counts"],
                "folds": payload["folds_materialized"],
                "manifest_sha256": sha256(outputs["manifest"]),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
