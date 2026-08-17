"""Outcome-blind V4-3 support refresh after PIT/listing-domain remediation.

This script never materializes R5/R10, target ranks, predictions, or performance.
It verifies whether the already-frozen 600 validation dates remain >=90% target-
support eligible after invalid pre/post-listing panel rows are removed *before*
causal liquidity/feature construction.

Corporate-action price continuity is deliberately NOT certified here. That is a
separate hard gate under ``ranking_v4_3_target_execution_protocol.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from idx_trade.ranking_v4_3_features import build_v4_control_feature_table


PINNED = {
    "calendar": "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a",
    "panel": "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76",
    "anchors": "33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e",
    "intervals": "fd255f21a3accd763286fbd0b0c6d9d501d618ae611cc0681017e001bdba83cc",
    "open_derivative_panel": "a1dae0714971904b266a380be6bb96a2a4976068c9d60c54c8c43746826f7cab",
    "open_derivative_manifest": "1a6bcc9c7fbbd967cdc69f8876fe1d4aa94b46c0e466469a9643da59251deb14",
    "overlay_parquet": "2aeab3906434f48c15d9ed7a8fb073fdd3bafff362cedcc7b46f9bf16482ca41",
    "overlay_manifest": "dfb7219bddec77ced3e3aadfaa2d85d04c19e1d9fd9a8af1badba523ecf91977",
    "security_master": "c8efa462c5fee94a92aca7e5915513fdb8be6d04c2264021bab47bf1cc50a240",
    "validation_folds": "91fe0e5a1c2489d5397f9f8bef7fc999d3f83a3f0cb94b6cdb5852c1e07cd915",
}

STATE_NAMES = ("ACTIVE", "NO_TRADE", "SUSPENDED", "UNKNOWN", "AMBIGUOUS", "NO_FUTURE_SESSION")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_identity(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["ticker"] = out["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
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
    regular["ticker"] = regular["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    regular["as_of_date"] = pd.to_datetime(regular["as_of_date"], errors="coerce").dt.tz_localize(None).dt.normalize()
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
        covered = calendar.loc[(calendar_dates >= start) & (calendar_dates <= end), "session_index"]
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

    base = panel[["ticker", "date"]]
    if len(base) != len(derivative):
        raise RuntimeError("OPEN_DERIVATIVE_ROW_COUNT_MISMATCH")
    identity = base.merge(
        derivative[["ticker", "date"]].assign(_present=True),
        on=["ticker", "date"],
        how="outer",
        indicator=True,
        validate="one_to_one",
    )
    if not identity["_merge"].eq("both").all():
        raise RuntimeError("OPEN_DERIVATIVE_IDENTITY_MISMATCH")

    merged = base.merge(
        derivative[["ticker", "date", "open"]].rename(columns={"open": "_accepted_open"}),
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )
    derivative_open = pd.to_numeric(merged["_accepted_open"], errors="coerce")
    derivative_support = derivative_open.notna() & derivative_open.gt(0.0)
    overlay_keys = set(zip(overlay["ticker"], overlay["date"]))
    panel_keys = set(zip(panel["ticker"], panel["date"]))
    if not overlay_keys.issubset(panel_keys):
        raise RuntimeError("OPEN_OVERLAY_HAS_KEYS_OUTSIDE_SIGNAL_PANEL")
    overlay_support = pd.Series(
        [(ticker, day) in overlay_keys for ticker, day in zip(panel["ticker"], panel["date"])],
        index=panel.index,
        dtype=bool,
    )
    panel["open_support"] = derivative_support.to_numpy(dtype=bool) | overlay_support.to_numpy(dtype=bool)
    return {
        "derivative_supported_rows": int(derivative_support.sum()),
        "overlay_rows": int(len(overlay)),
        "overlay_incremental_rows": int((overlay_support & ~derivative_support).sum()),
        "final_supported_rows": int(panel["open_support"].sum()),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--open-derivative-root", type=Path, required=True)
    parser.add_argument("--overlay-root", type=Path, required=True)
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT: {args.output_dir}")

    paths = {
        "calendar": args.artifact_root / "official_exchange_sessions_1260.csv",
        "panel": args.artifact_root / "unknown_state_diagnostic_1260_20260809" / "model_safe_signal_research_panel_1260.parquet",
        "anchors": args.artifact_root / "tradability_anchors_1260.csv",
        "intervals": args.artifact_root / "tradability_intervals_1260.csv",
        "open_derivative_panel": args.open_derivative_root / "execution_open_candidate_panel_yahoo_tradingview.parquet",
        "open_derivative_manifest": args.open_derivative_root / "artifact_manifest.json",
        "overlay_parquet": args.overlay_root / "open_recovery_overlay.parquet",
        "overlay_manifest": args.overlay_root / "manifest.json",
        "security_master": args.security_master,
        "validation_folds": args.repo_root / "docs" / "artifacts" / "ranking_v4_3_primary_liquid_support_v1" / "v4_3_validation_folds.csv",
    }
    for name, path in paths.items():
        if not path.is_file():
            raise RuntimeError(f"REQUIRED_INPUT_MISSING: {name}: {path}")
        actual = sha256(path)
        if actual != PINNED[name]:
            raise RuntimeError(f"PINNED_INPUT_HASH_MISMATCH {name}: {actual} != {PINNED[name]}")

    calendar = pd.read_csv(paths["calendar"])
    calendar["date"] = pd.to_datetime(calendar["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if calendar["date"].isna().any() or calendar["date"].duplicated().any():
        raise RuntimeError("OFFICIAL_CALENDAR_INVALID")
    calendar = calendar.sort_values("date", kind="mergesort").reset_index(drop=True)
    calendar["session_index"] = np.arange(len(calendar), dtype=np.int64)
    date_to_index = dict(zip(calendar["date"], calendar["session_index"]))

    panel = normalize_identity(pd.read_parquet(paths["panel"]))
    if panel.duplicated(["ticker", "date"]).any():
        raise RuntimeError("SIGNAL_PANEL_DUPLICATE_IDENTITY")
    panel["session_index"] = panel["date"].map(date_to_index)
    if panel["session_index"].isna().any():
        raise RuntimeError("SIGNAL_PANEL_DATE_OUTSIDE_CALENDAR")
    panel["session_index"] = panel["session_index"].astype(int)
    panel["close_valid"] = pd.to_numeric(panel["close"], errors="coerce").gt(0.0)

    derivative = pd.read_parquet(paths["open_derivative_panel"])
    overlay = pd.read_parquet(paths["overlay_parquet"])
    open_stats = attach_open_support(panel, derivative, overlay)

    security_master = pd.read_csv(paths["security_master"])
    features, pit_diagnostics = build_v4_control_feature_table(
        panel,
        calendar["date"],
        security_master,
    )
    primary = features[features["universe_primary_liquid"].astype(bool)][["ticker", "date"]].copy()
    primary["session_index"] = primary["date"].map(date_to_index).astype(int)
    if primary.duplicated(["ticker", "date"]).any():
        raise RuntimeError("PIT_PRIMARY_DECISION_DUPLICATE_IDENTITY")

    panel_key = panel.set_index(["ticker", "date"])[["open_support", "close_valid"]]
    decision = primary.join(panel_key, on=["ticker", "date"], how="left", validate="one_to_one")
    if decision[["open_support", "close_valid"]].isna().any().any():
        raise RuntimeError("PIT_PRIMARY_DECISION_MISSING_PANEL_SUPPORT")

    anchors = pd.read_csv(paths["anchors"])
    anchors["market"] = anchors["market"].astype(str).str.upper()
    anchors["state"] = anchors["state"].astype(str).str.upper()
    intervals = pd.read_csv(paths["intervals"])
    intervals["market"] = intervals["market"].astype(str).str.upper()
    intervals["state"] = intervals["state"].astype(str).str.upper()
    states, state_conflicts = state_map_from_inputs(anchors, intervals, calendar)

    support_lookup = {
        (ticker, int(index)): (bool(open_support), bool(close_valid))
        for ticker, index, open_support, close_valid
        in panel[["ticker", "session_index", "open_support", "close_valid"]].itertuples(index=False)
    }

    def future_state(ticker: str, index: int, offset: int) -> str:
        target = int(index) + int(offset)
        if target >= len(calendar):
            return "NO_FUTURE_SESSION"
        return states.get((ticker, target), "UNKNOWN")

    def future_support(ticker: str, index: int, offset: int) -> tuple[bool, bool]:
        return support_lookup.get((ticker, int(index) + int(offset)), (False, False))

    entry_ok: list[bool] = []
    h5_close_ok: list[bool] = []
    h10_close_ok: list[bool] = []
    for ticker, index in decision[["ticker", "session_index"]].itertuples(index=False):
        entry_state = future_state(ticker, int(index), 1)
        h5_state = future_state(ticker, int(index), 5)
        h10_state = future_state(ticker, int(index), 10)
        entry_open, _ = future_support(ticker, int(index), 1)
        _, h5_close = future_support(ticker, int(index), 5)
        _, h10_close = future_support(ticker, int(index), 10)
        entry_ok.append(entry_state == "ACTIVE" and entry_open)
        h5_close_ok.append(h5_state == "ACTIVE" and h5_close)
        h10_close_ok.append(h10_state == "ACTIVE" and h10_close)
    decision["entry_open_support"] = entry_ok
    decision["h5_close_support"] = h5_close_ok
    decision["h10_close_support"] = h10_close_ok
    decision["h5_target_support"] = decision["entry_open_support"] & decision["h5_close_support"]
    decision["h10_target_support"] = decision["entry_open_support"] & decision["h10_close_support"]
    decision["both_target_support"] = decision["h5_target_support"] & decision["h10_target_support"]

    grouped = decision.groupby(["session_index", "date"], sort=True).agg(
        decision_rows=("ticker", "size"),
        open_t1_rows=("entry_open_support", "sum"),
        h5_target_rows=("h5_target_support", "sum"),
        h10_target_rows=("h10_target_support", "sum"),
        both_target_rows=("both_target_support", "sum"),
    ).reset_index()
    per_date = calendar[["session_index", "date"]].merge(
        grouped,
        on=["session_index", "date"],
        how="left",
        validate="one_to_one",
    )
    for column in ("decision_rows", "open_t1_rows", "h5_target_rows", "h10_target_rows", "both_target_rows"):
        per_date[column] = per_date[column].fillna(0).astype(int)
    for prefix in ("open_t1", "h5_target", "h10_target", "both_target"):
        per_date[f"{prefix}_rate"] = np.where(
            per_date["decision_rows"].gt(0),
            per_date[f"{prefix}_rows"] / per_date["decision_rows"],
            np.nan,
        )
        per_date[f"{prefix}_gate"] = per_date["decision_rows"].gt(0) & per_date[f"{prefix}_rate"].ge(0.90)
    per_date["basic_consensus_eligible"] = per_date["both_target_gate"]

    frozen = pd.read_csv(paths["validation_folds"])
    frozen["date"] = pd.to_datetime(frozen["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if len(frozen) != 600 or frozen["date"].duplicated().any():
        raise RuntimeError("FROZEN_VALIDATION_IDENTITY_INVALID")
    frozen_check = frozen[["fold", "validation_position", "session_index", "date"]].merge(
        per_date[["session_index", "date", "decision_rows", "both_target_rate", "basic_consensus_eligible"]],
        on=["session_index", "date"],
        how="left",
        validate="one_to_one",
    )
    all_frozen_basic_eligible = bool(frozen_check["basic_consensus_eligible"].fillna(False).all())
    corrected_eligible = per_date[per_date["basic_consensus_eligible"]][["session_index", "date"]].copy()
    eligible_after_frozen_end = int((corrected_eligible["session_index"] > int(frozen["session_index"].max())).sum())
    tail_600_same = False
    if len(corrected_eligible) >= 600:
        tail = corrected_eligible.tail(600).reset_index(drop=True)
        expected = frozen[["session_index", "date"]].reset_index(drop=True)
        tail_600_same = bool(tail.equals(expected))

    verdict = (
        "V4_3_PIT_REMEDIATED_SUPPORT_PRESERVES_FROZEN_6X100"
        if all_frozen_basic_eligible and tail_600_same
        else "V4_3_PIT_REMEDIATED_SUPPORT_REQUIRES_PREFIT_REVIEW"
    )

    args.output_dir.mkdir(parents=True)
    outputs = {
        "per_date": args.output_dir / "v4_3_pit_support_per_date.csv",
        "frozen_check": args.output_dir / "v4_3_pit_frozen_validation_check.csv",
        "eligible": args.output_dir / "v4_3_pit_basic_consensus_eligible_sessions.csv",
        "summary": args.output_dir / "summary.json",
        "manifest": args.output_dir / "manifest.json",
    }
    per_date.to_csv(outputs["per_date"], index=False, lineterminator="\n")
    frozen_check.to_csv(outputs["frozen_check"], index=False, lineterminator="\n")
    corrected_eligible.to_csv(outputs["eligible"], index=False, lineterminator="\n")

    payload = {
        "schema_version": "v4_3_pit_support_refresh_v1",
        "verdict": verdict,
        "outcome_blind": True,
        "returns_or_target_ranks_loaded": False,
        "model_fit": False,
        "performance_computed": False,
        "provider_calls": False,
        "corporate_action_continuity_certified": False,
        "pit_diagnostics": pit_diagnostics.__dict__,
        "decision_rows": int(len(decision)),
        "decision_tickers": int(decision["ticker"].nunique()),
        "basic_consensus_eligible_sessions": int(len(corrected_eligible)),
        "all_frozen_600_basic_eligible": all_frozen_basic_eligible,
        "tail_600_identity_unchanged": tail_600_same,
        "eligible_sessions_after_frozen_end": eligible_after_frozen_end,
        "state_conflict_keys": int(state_conflicts),
        "open_lineage": open_stats,
        "input_hashes": {name: sha256(path) for name, path in paths.items()},
    }
    outputs["summary"].write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "v4_3_pit_support_refresh_manifest_v1",
        "status": verdict,
        "outcome_blind": True,
        "corporate_action_continuity_certified": False,
        "input_hashes": payload["input_hashes"],
        "outputs": {
            name: sha256(path)
            for name, path in outputs.items()
            if name != "manifest" and path.is_file()
        },
    }
    outputs["manifest"].write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": verdict, "summary": payload, "manifest_sha256": sha256(outputs["manifest"])}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
