"""Outcome-blind residual attribution for blocked V4-3 CA training-domain replay.

This runner consumes only the immutable offline replay artifacts. It does not
contact KSEI or any provider and never reads/materializes returns, targets,
ranks, models, predictions, performance, or protected-forward outcomes.

It computes explicit upper-bound counterfactuals to identify which residual
pre-target evidence class must be remediated:

- BASELINE: unchanged accepted replay semantics;
- COVERAGE_ONLY_CEILING: unresolved KSEI coverage is hypothetically certified,
  while schedule-required events and exact mechanical crossings remain blocked;
- SCHEDULE_ONLY_CEILING: schedule-required events are hypothetically resolved,
  while unresolved coverage and exact mechanical crossings remain blocked;
- COVERAGE_PLUS_SCHEDULE_CEILING: both remediable evidence gaps are
  hypothetically resolved, while exact mechanical crossings remain blocked;
- PRICE_OBSERVABILITY_ONLY_UPPER_BOUND: ignores CA only as a non-admissible
  diagnostic upper bound. It can never authorize target access.

No scenario changes the frozen 0.90 gate or chooses a pass-preserving subset of
unresolved tickers/events. Exact crossing rows are never waived in any
admissible ceiling.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = Path("config/v4_3_ca_training_domain_residual_attribution_v1.json")
FROZEN_FOLDS = Path(
    "docs/artifacts/ranking_v4_3_primary_liquid_support_v1/v4_3_validation_folds.csv"
)

RESOLVED = "RESOLVED_NO_MECHANICAL_DISCONTINUITY"
UNRESOLVED_COVERAGE = "PRICE_CONTINUITY_UNRESOLVED_COVERAGE"
UNRESOLVED_EVENT = "PRICE_CONTINUITY_UNRESOLVED_EFFECTIVE_DATE"
REASON_COVERAGE = "KSEI_REGISTERED_SECURITY_HISTORY_NOT_CERTIFIED"
REASON_CONFLICT = "CROSS_SOURCE_CANDIDATE_NOT_REPRESENTED_IN_KSEI_HISTORY"
REASON_SCHEDULE = "EXACT_OFFICIAL_EVENT_TRANSITION_REQUIRED"
REASON_CROSSING = "TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION"
SCENARIOS = (
    "BASELINE",
    "COVERAGE_ONLY_CEILING",
    "SCHEDULE_ONLY_CEILING",
    "COVERAGE_PLUS_SCHEDULE_CEILING",
    "PRICE_OBSERVABILITY_ONLY_UPPER_BOUND",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"{label}_MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{label}_NOT_OBJECT:{path}")
    return value


def normalize_bool(series: pd.Series, label: str) -> pd.Series:
    if series.dtype == bool:
        return series.copy()
    mapped = series.astype(str).str.casefold().map({"true": True, "false": False})
    if mapped.isna().any():
        raise RuntimeError(f"BOOLEAN_COLUMN_INVALID:{label}")
    return mapped.astype(bool)


def normalize_ticker(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def verify_parent(
    replay_root: Path, config: dict[str, Any]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    parent_cfg = config["parent_replay"]
    manifest_path = replay_root / "MANIFEST.json"
    summary_path = replay_root / "summary.json"
    combined_path = replay_root / "v4_3_full_target_support_rows_ksei129.csv"
    continuity_path = replay_root / "v4_3_ca_training_domain_ksei129_continuity.csv"
    per_date_path = replay_root / "v4_3_full_target_support_per_date_ksei129.csv"
    event_audit_path = replay_root / "v4_3_ca_training_event_semantics_ksei129.csv"

    actual_manifest = sha256_file(manifest_path)
    expected_manifest = str(parent_cfg["manifest_sha256"])
    if actual_manifest != expected_manifest:
        raise RuntimeError(
            f"PARENT_REPLAY_MANIFEST_SHA_MISMATCH:{actual_manifest}!={expected_manifest}"
        )
    manifest = read_json(manifest_path, "PARENT_REPLAY_MANIFEST")
    summary = read_json(summary_path, "PARENT_REPLAY_SUMMARY")
    expected_status = str(parent_cfg["status"])
    if manifest.get("status") != expected_status or summary.get("status") != expected_status:
        raise RuntimeError("PARENT_REPLAY_STATUS_CHANGED")
    if manifest.get("outcome_blind") is not True or summary.get("outcome_blind") is not True:
        raise RuntimeError("PARENT_REPLAY_NOT_OUTCOME_BLIND")

    for key in (
        "historical_target_loaded",
        "historical_target_rank_materialized",
        "historical_model_fit",
        "historical_prediction_generated",
        "historical_performance_computed",
        "protected_forward_accessed",
        "provider_calls",
        "network_calls",
    ):
        if summary.get(key) is not False:
            raise RuntimeError(f"PARENT_REPLAY_GUARDRAIL_CHANGED:{key}")

    ca_diag = summary.get("ca_diagnostics") or {}
    expected_scalars = {
        "coverage_census_tickers": parent_cfg["coverage_census_tickers"],
        "coverage_certified_tickers_total": parent_cfg["coverage_certified_tickers_total"],
        "coverage_unresolved_decision_tickers": parent_cfg["coverage_unresolved_decision_tickers"],
    }
    for key, expected in expected_scalars.items():
        if int(ca_diag.get(key) or -1) != int(expected):
            raise RuntimeError(f"PARENT_REPLAY_SCALAR_CHANGED:{key}")

    delta_diag = summary.get("ksei_129_delta") or {}
    if delta_diag:
        if int(delta_diag.get("coverage_certified_tickers") or -1) != int(
            parent_cfg["ksei_129_certified"]
        ):
            raise RuntimeError("PARENT_REPLAY_KSEI129_CERTIFIED_CHANGED")
        if int(delta_diag.get("coverage_unresolved_tickers") or -1) != int(
            parent_cfg["ksei_129_unresolved"]
        ):
            raise RuntimeError("PARENT_REPLAY_KSEI129_UNRESOLVED_CHANGED")

    outputs = manifest.get("output_hashes") or {}
    expected_paths = {
        "combined": combined_path,
        "continuity": continuity_path,
        "per_date": per_date_path,
        "event_audit": event_audit_path,
        "summary": summary_path,
    }
    # Manifest keys are generated by the replay runner. Accept exact canonical
    # labels only; no filename substitution is permitted.
    key_aliases = {
        "combined": ("combined",),
        "continuity": ("continuity",),
        "per_date": ("per_date",),
        "event_audit": ("event_audit",),
        "summary": ("summary",),
    }
    child_hashes: dict[str, str] = {}
    for logical, path in expected_paths.items():
        if not path.is_file():
            raise RuntimeError(f"PARENT_REPLAY_CHILD_MISSING:{logical}:{path}")
        expected = ""
        for candidate in key_aliases[logical]:
            value = outputs.get(candidate)
            if value:
                expected = str(value)
                break
        if not expected:
            raise RuntimeError(f"PARENT_REPLAY_CHILD_HASH_MISSING:{logical}")
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(
                f"PARENT_REPLAY_CHILD_SHA_MISMATCH:{logical}:{actual}!={expected}"
            )
        child_hashes[logical] = actual

    combined = pd.read_csv(combined_path)
    continuity = pd.read_csv(continuity_path)
    per_date = pd.read_csv(per_date_path)
    event_audit = pd.read_csv(event_audit_path)
    return combined, continuity, per_date, {
        "manifest_sha256": actual_manifest,
        "summary": summary,
        "child_hashes": child_hashes,
        "event_audit": event_audit,
    }


def verify_frozen_folds(config: dict[str, Any]) -> pd.DataFrame:
    path = REPO_ROOT / FROZEN_FOLDS
    if not path.is_file():
        raise RuntimeError(f"FROZEN_VALIDATION_FOLDS_MISSING:{path}")
    expected = str(config["frozen_validation_folds_sha256"])
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"FROZEN_VALIDATION_FOLDS_SHA_MISMATCH:{actual}!={expected}")
    folds = pd.read_csv(path)
    required = {"session_index", "date"}
    missing = required - set(folds.columns)
    if missing:
        raise RuntimeError(f"FROZEN_VALIDATION_FOLDS_COLUMNS_MISSING:{sorted(missing)}")
    folds["session_index"] = pd.to_numeric(folds["session_index"], errors="raise").astype(int)
    folds["date"] = pd.to_datetime(folds["date"], errors="coerce").dt.normalize()
    if len(folds) != 600 or folds["date"].isna().any():
        raise RuntimeError("FROZEN_VALIDATION_FOLDS_IDENTITY_INVALID")
    if folds.duplicated(["session_index", "date"]).any():
        raise RuntimeError("FROZEN_VALIDATION_FOLDS_DUPLICATED")
    return folds.sort_values("session_index", kind="mergesort").reset_index(drop=True)


def prepare_inputs(
    combined: pd.DataFrame, continuity: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    required_combined = {
        "ticker",
        "date",
        "session_index",
        "entry_open_support",
        "h5_close_support",
        "h10_close_support",
        "h5_full_target_support",
        "h10_full_target_support",
        "consensus_full_target_support",
    }
    missing = required_combined - set(combined.columns)
    if missing:
        raise RuntimeError(f"COMBINED_COLUMNS_MISSING:{sorted(missing)}")
    c = combined.copy()
    c["ticker"] = normalize_ticker(c["ticker"])
    c["date"] = pd.to_datetime(c["date"], errors="coerce").dt.normalize()
    c["session_index"] = pd.to_numeric(c["session_index"], errors="raise").astype(int)
    if c["date"].isna().any() or c.duplicated(["ticker", "date"]).any():
        raise RuntimeError("COMBINED_IDENTITY_INVALID")
    for column in (
        "entry_open_support",
        "h5_close_support",
        "h10_close_support",
        "h5_full_target_support",
        "h10_full_target_support",
        "consensus_full_target_support",
    ):
        c[column] = normalize_bool(c[column], column)

    required_continuity = {
        "ticker",
        "signal_date",
        "horizon",
        "continuity_status",
        "continuity_reason",
        "blocking_event_ids",
    }
    missing_cont = required_continuity - set(continuity.columns)
    if missing_cont:
        raise RuntimeError(f"CONTINUITY_COLUMNS_MISSING:{sorted(missing_cont)}")
    w = continuity.copy()
    w["ticker"] = normalize_ticker(w["ticker"])
    w["signal_date"] = pd.to_datetime(w["signal_date"], errors="coerce").dt.normalize()
    w["horizon"] = pd.to_numeric(w["horizon"], errors="raise").astype(int)
    if w["signal_date"].isna().any() or w.duplicated(
        ["ticker", "signal_date", "horizon"]
    ).any():
        raise RuntimeError("CONTINUITY_IDENTITY_INVALID")
    if set(w["horizon"].unique()) != {5, 10}:
        raise RuntimeError("CONTINUITY_HORIZONS_CHANGED")
    allowed_status = {RESOLVED, UNRESOLVED_COVERAGE, UNRESOLVED_EVENT}
    unknown_status = sorted(set(w["continuity_status"].astype(str)) - allowed_status)
    if unknown_status:
        raise RuntimeError(f"CONTINUITY_STATUS_UNKNOWN:{unknown_status}")
    allowed_reasons = {
        "NO_MECHANICAL_CA_TRANSITION_CROSSES_TARGET_INTERVAL",
        REASON_COVERAGE,
        REASON_CONFLICT,
        REASON_SCHEDULE,
        REASON_CROSSING,
    }
    unknown_reasons = sorted(set(w["continuity_reason"].astype(str)) - allowed_reasons)
    if unknown_reasons:
        raise RuntimeError(f"CONTINUITY_REASON_UNKNOWN:{unknown_reasons}")
    return c, w


def scenario_ca_ok(windows: pd.DataFrame, scenario: str) -> pd.Series:
    status = windows["continuity_status"].astype(str)
    reason = windows["continuity_reason"].astype(str)
    resolved = status.eq(RESOLVED)
    coverage = status.eq(UNRESOLVED_COVERAGE)
    schedule = reason.eq(REASON_SCHEDULE)
    crossing = reason.eq(REASON_CROSSING)

    if scenario == "BASELINE":
        return resolved
    if scenario == "COVERAGE_ONLY_CEILING":
        return resolved | coverage
    if scenario == "SCHEDULE_ONLY_CEILING":
        return resolved | schedule
    if scenario == "COVERAGE_PLUS_SCHEDULE_CEILING":
        # Exact crossings stay blocked. Coverage conflicts count as coverage
        # because they require source/evidence remediation, not semantic waiver.
        return (resolved | coverage | schedule) & ~crossing
    if scenario == "PRICE_OBSERVABILITY_ONLY_UPPER_BOUND":
        return pd.Series(True, index=windows.index, dtype=bool)
    raise ValueError(f"unknown scenario: {scenario}")


def build_scenario_rows(
    combined: pd.DataFrame, continuity: pd.DataFrame, scenario: str
) -> pd.DataFrame:
    ca = continuity[["ticker", "signal_date", "horizon"]].copy()
    ca["scenario_ca_ok"] = scenario_ca_ok(continuity, scenario).astype(bool).values
    wide = ca.pivot(
        index=["ticker", "signal_date"],
        columns="horizon",
        values="scenario_ca_ok",
    ).reset_index()
    if 5 not in wide.columns or 10 not in wide.columns:
        raise RuntimeError("SCENARIO_CA_HORIZON_MISSING")
    wide = wide.rename(
        columns={"signal_date": "date", 5: "scenario_ca_h5", 10: "scenario_ca_h10"}
    )
    rows = combined.merge(
        wide,
        on=["ticker", "date"],
        how="left",
        validate="one_to_one",
    )
    if rows[["scenario_ca_h5", "scenario_ca_h10"]].isna().any().any():
        raise RuntimeError("SCENARIO_CA_JOIN_MISSING")
    rows["scenario_h5_support"] = (
        rows["entry_open_support"]
        & rows["h5_close_support"]
        & rows["scenario_ca_h5"].astype(bool)
    )
    rows["scenario_h10_support"] = (
        rows["entry_open_support"]
        & rows["h10_close_support"]
        & rows["scenario_ca_h10"].astype(bool)
    )
    rows["scenario_consensus_support"] = (
        rows["scenario_h5_support"] & rows["scenario_h10_support"]
    )
    return rows


def aggregate_per_date(rows: pd.DataFrame, gate_rate: float) -> pd.DataFrame:
    result = (
        rows.groupby(["session_index", "date"], sort=True)
        .agg(
            decision_rows=("ticker", "size"),
            h5_supported_rows=("scenario_h5_support", "sum"),
            h10_supported_rows=("scenario_h10_support", "sum"),
            consensus_supported_rows=("scenario_consensus_support", "sum"),
        )
        .reset_index()
    )
    for head in ("h5", "h10", "consensus"):
        result[f"{head}_rate"] = np.where(
            result["decision_rows"].gt(0),
            result[f"{head}_supported_rows"] / result["decision_rows"],
            np.nan,
        )
        result[f"{head}_eligible"] = result[f"{head}_rate"].ge(gate_rate)
    return result


def summarize_scenario(
    name: str,
    per_date: pd.DataFrame,
    folds: pd.DataFrame,
) -> dict[str, Any]:
    frozen = folds.merge(
        per_date,
        on=["session_index", "date"],
        how="left",
        validate="one_to_one",
    )
    if frozen[["h5_rate", "h10_rate", "consensus_rate"]].isna().any().any():
        raise RuntimeError(f"FROZEN_SCENARIO_DATE_MISSING:{name}")
    return {
        "scenario": name,
        "all_sessions": {
            "dates": int(len(per_date)),
            "h5_eligible_dates": int(per_date["h5_eligible"].sum()),
            "h10_eligible_dates": int(per_date["h10_eligible"].sum()),
            "consensus_eligible_dates": int(per_date["consensus_eligible"].sum()),
            "h5_min_rate": float(per_date["h5_rate"].min()),
            "h10_min_rate": float(per_date["h10_rate"].min()),
            "consensus_min_rate": float(per_date["consensus_rate"].min()),
        },
        "frozen_600": {
            "h5_eligible_dates": int(frozen["h5_eligible"].sum()),
            "h10_eligible_dates": int(frozen["h10_eligible"].sum()),
            "consensus_eligible_dates": int(frozen["consensus_eligible"].sum()),
            "h5_min_rate": float(frozen["h5_rate"].min()),
            "h10_min_rate": float(frozen["h10_rate"].min()),
            "consensus_min_rate": float(frozen["consensus_rate"].min()),
            "all_600_h5": bool(frozen["h5_eligible"].all()),
            "all_600_h10": bool(frozen["h10_eligible"].all()),
            "all_600_consensus": bool(frozen["consensus_eligible"].all()),
        },
    }


def residual_coverage_impact(
    combined: pd.DataFrame, continuity: pd.DataFrame, folds: pd.DataFrame
) -> pd.DataFrame:
    frozen_dates = set(folds["date"])
    price_support = combined[
        ["ticker", "date", "entry_open_support", "h5_close_support", "h10_close_support"]
    ].copy()
    rows: list[dict[str, Any]] = []
    for horizon in (5, 10):
        cont = continuity[
            continuity["horizon"].eq(horizon)
            & continuity["continuity_status"].eq(UNRESOLVED_COVERAGE)
        ][["ticker", "signal_date", "continuity_reason"]].copy()
        cont = cont.rename(columns={"signal_date": "date"})
        merged = cont.merge(price_support, on=["ticker", "date"], how="left", validate="many_to_one")
        close_col = "h5_close_support" if horizon == 5 else "h10_close_support"
        merged["price_observable"] = (
            merged["entry_open_support"].fillna(False).astype(bool)
            & merged[close_col].fillna(False).astype(bool)
        )
        for ticker, group in merged.groupby("ticker", sort=True):
            observable = group[group["price_observable"]]
            rows.append(
                {
                    "ticker": ticker,
                    "horizon": horizon,
                    "coverage_unresolved_windows": int(len(group)),
                    "price_observable_unresolved_windows": int(len(observable)),
                    "price_observable_unresolved_frozen_windows": int(
                        observable["date"].isin(frozen_dates).sum()
                    ),
                    "affected_signal_dates": int(group["date"].nunique()),
                    "affected_frozen_signal_dates": int(group["date"].isin(frozen_dates).sum()),
                    "reason_counts": json.dumps(
                        dict(sorted(Counter(group["continuity_reason"].astype(str)).items())),
                        sort_keys=True,
                    ),
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["price_observable_unresolved_frozen_windows", "ticker", "horizon"],
        ascending=[False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)


def schedule_event_impact(
    continuity: pd.DataFrame, event_audit: pd.DataFrame, folds: pd.DataFrame
) -> pd.DataFrame:
    frozen_dates = set(folds["date"])
    schedule = continuity[continuity["continuity_reason"].eq(REASON_SCHEDULE)].copy()
    exploded_rows: list[dict[str, Any]] = []
    for row in schedule.itertuples(index=False):
        event_ids = [
            value.strip()
            for value in str(getattr(row, "blocking_event_ids", "") or "").split("|")
            if value.strip() and value.strip().lower() != "nan"
        ]
        for event_id in sorted(set(event_ids)):
            exploded_rows.append(
                {
                    "event_id": event_id,
                    "ticker": row.ticker,
                    "signal_date": row.signal_date,
                    "horizon": int(row.horizon),
                    "in_frozen_600": row.signal_date in frozen_dates,
                }
            )
    if not exploded_rows:
        return pd.DataFrame(
            columns=[
                "event_id",
                "ticker",
                "source_type",
                "family",
                "semantic_class",
                "affected_windows",
                "affected_frozen_windows",
                "affected_signal_dates",
            ]
        )
    exploded = pd.DataFrame(exploded_rows)
    grouped = (
        exploded.groupby(["event_id", "ticker"], sort=True)
        .agg(
            affected_windows=("horizon", "size"),
            affected_frozen_windows=("in_frozen_600", "sum"),
            affected_signal_dates=("signal_date", "nunique"),
        )
        .reset_index()
    )
    audit_cols = [
        column
        for column in ("event_id", "ticker", "source_type", "family", "semantic_class", "reason")
        if column in event_audit.columns
    ]
    audit = event_audit[audit_cols].copy() if audit_cols else pd.DataFrame()
    if not audit.empty:
        audit["ticker"] = normalize_ticker(audit["ticker"])
        audit = audit.drop_duplicates(["event_id", "ticker"], keep="first")
        grouped = grouped.merge(audit, on=["event_id", "ticker"], how="left", validate="one_to_one")
    return grouped.sort_values(
        ["affected_frozen_windows", "affected_windows", "ticker", "event_id"],
        ascending=[False, False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)


def determine_verdict(summaries: dict[str, dict[str, Any]]) -> tuple[str, str]:
    baseline = summaries["BASELINE"]["frozen_600"]
    coverage = summaries["COVERAGE_ONLY_CEILING"]["frozen_600"]
    schedule = summaries["SCHEDULE_ONLY_CEILING"]["frozen_600"]
    combined = summaries["COVERAGE_PLUS_SCHEDULE_CEILING"]["frozen_600"]
    price_only = summaries["PRICE_OBSERVABILITY_ONLY_UPPER_BOUND"]["frozen_600"]

    def passes(value: dict[str, Any]) -> bool:
        return bool(value["all_600_h5"] and value["all_600_h10"] and value["all_600_consensus"])

    if passes(baseline):
        return (
            "V4_3_CA_RESIDUAL_ATTRIBUTION_BASELINE_ALREADY_PASSES",
            "PIN_CURRENT_REPLAY_NO_REMEDIATION_REQUIRED",
        )
    if passes(coverage):
        return (
            "V4_3_CA_RESIDUAL_ATTRIBUTION_COVERAGE_ONLY_SUFFICIENT",
            "REMEDIATE_ALL_45_UNRESOLVED_COVERAGE_TICKERS_THEN_REPLAY",
        )
    if passes(schedule):
        return (
            "V4_3_CA_RESIDUAL_ATTRIBUTION_SCHEDULE_ONLY_SUFFICIENT",
            "RESOLVE_ALL_SCHEDULE_REQUIRED_EVENTS_THEN_REPLAY",
        )
    if passes(combined):
        return (
            "V4_3_CA_RESIDUAL_ATTRIBUTION_COVERAGE_PLUS_SCHEDULE_REQUIRED",
            "REMEDIATE_ALL_45_UNRESOLVED_COVERAGE_TICKERS_AND_ALL_SCHEDULE_REQUIRED_EVENTS",
        )
    if passes(price_only):
        return (
            "V4_3_CA_RESIDUAL_ATTRIBUTION_EXACT_CROSSING_OR_INTERSECTION_STRUCTURAL_BLOCKER",
            "DO_NOT_WAIVE_EXACT_CROSSINGS_REVIEW_FROZEN_CONTRACT",
        )
    return (
        "V4_3_CA_RESIDUAL_ATTRIBUTION_PRICE_OBSERVABILITY_STRUCTURAL_BLOCKER",
        "REVIEW_FROZEN_TARGET_SUPPORT_CONTRACT_WITHOUT_TARGET_ACCESS",
    )


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    config = read_json(args.config, "CONFIG")
    if config.get("schema_version") != "v4_3_ca_training_domain_residual_attribution_v1":
        raise RuntimeError("CONFIG_SCHEMA_INVALID")
    if config.get("outcome_blind") is not True:
        raise RuntimeError("CONFIG_NOT_OUTCOME_BLIND")
    hard = config.get("hard_boundaries") or {}
    for key in (
        "network_calls",
        "provider_calls",
        "retry_unresolved_tickers",
        "source_substitution",
        "parser_or_semantic_relaxation",
        "pass_preserving_subset_selection",
        "target_or_rank_materialization",
        "model_fit",
        "prediction",
        "performance",
        "protected_forward_access",
        "waive_exact_mechanical_crossings",
    ):
        if hard.get(key) is not False:
            raise RuntimeError(f"HARD_BOUNDARY_CHANGED:{key}")

    combined_raw, continuity_raw, parent_per_date, parent_meta = verify_parent(
        args.replay_root, config
    )
    folds = verify_frozen_folds(config)
    combined, continuity = prepare_inputs(combined_raw, continuity_raw)
    gate_rate = float(config["gate_rate"])
    if not np.isclose(gate_rate, 0.90):
        raise RuntimeError("GATE_RATE_CHANGED")

    scenario_per_dates: dict[str, pd.DataFrame] = {}
    scenario_summaries: dict[str, dict[str, Any]] = {}
    for scenario in SCENARIOS:
        rows = build_scenario_rows(combined, continuity, scenario)
        per_date = aggregate_per_date(rows, gate_rate)
        scenario_per_dates[scenario] = per_date
        scenario_summaries[scenario] = summarize_scenario(scenario, per_date, folds)

    # Baseline must reproduce the immutable parent replay exactly before any
    # attribution result is trusted.
    parent = parent_per_date.copy()
    parent["date"] = pd.to_datetime(parent["date"], errors="coerce").dt.normalize()
    baseline = scenario_per_dates["BASELINE"]
    compare_columns = [
        "session_index",
        "date",
        "decision_rows",
        "h5_supported_rows",
        "h10_supported_rows",
        "consensus_supported_rows",
        "h5_rate",
        "h10_rate",
        "consensus_rate",
    ]
    if not baseline[compare_columns].reset_index(drop=True).equals(
        parent[compare_columns].reset_index(drop=True)
    ):
        numeric = ["h5_rate", "h10_rate", "consensus_rate"]
        identity = [
            "session_index",
            "date",
            "decision_rows",
            "h5_supported_rows",
            "h10_supported_rows",
            "consensus_supported_rows",
        ]
        if not baseline[identity].reset_index(drop=True).equals(
            parent[identity].reset_index(drop=True)
        ) or not np.allclose(
            baseline[numeric].to_numpy(dtype=float),
            parent[numeric].to_numpy(dtype=float),
            equal_nan=True,
        ):
            raise RuntimeError("BASELINE_DOES_NOT_REPRODUCE_PARENT_REPLAY")

    coverage_impact = residual_coverage_impact(combined, continuity, folds)
    schedule_impact = schedule_event_impact(
        continuity, parent_meta["event_audit"], folds
    )
    reason_counts = dict(sorted(Counter(continuity["continuity_reason"].astype(str)).items()))
    status_counts = dict(sorted(Counter(continuity["continuity_status"].astype(str)).items()))
    verdict, next_action = determine_verdict(scenario_summaries)

    args.output_dir.mkdir(parents=True)
    outputs: dict[str, Path] = {
        "scenario_summary": args.output_dir / "scenario_summary.csv",
        "coverage_impact": args.output_dir / "residual_coverage_ticker_impact.csv",
        "schedule_impact": args.output_dir / "residual_schedule_event_impact.csv",
        "summary": args.output_dir / "summary.json",
        "manifest": args.output_dir / "MANIFEST.json",
    }
    summary_rows: list[dict[str, Any]] = []
    for scenario in SCENARIOS:
        item = scenario_summaries[scenario]
        summary_rows.append(
            {
                "scenario": scenario,
                **{f"all_{k}": v for k, v in item["all_sessions"].items()},
                **{f"frozen_{k}": v for k, v in item["frozen_600"].items()},
            }
        )
        scenario_path = args.output_dir / f"per_date_{scenario.lower()}.csv"
        scenario_per_dates[scenario].to_csv(scenario_path, index=False, lineterminator="\n")
        outputs[f"per_date_{scenario.lower()}"] = scenario_path

    pd.DataFrame(summary_rows).to_csv(
        outputs["scenario_summary"], index=False, lineterminator="\n"
    )
    coverage_impact.to_csv(outputs["coverage_impact"], index=False, lineterminator="\n")
    schedule_impact.to_csv(outputs["schedule_impact"], index=False, lineterminator="\n")

    summary = {
        "schema_version": "v4_3_ca_training_domain_residual_attribution_result_v1",
        "status": verdict,
        "outcome_blind": True,
        "network_calls": False,
        "provider_calls": False,
        "retry_unresolved_tickers": False,
        "target_or_rank_materialized": False,
        "historical_target_loaded": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "scientific_config_changed": False,
        "gate_rate": gate_rate,
        "parent_replay_manifest_sha256": parent_meta["manifest_sha256"],
        "continuity_status_counts": status_counts,
        "continuity_reason_counts": reason_counts,
        "coverage_unresolved_tickers": int(coverage_impact["ticker"].nunique())
        if not coverage_impact.empty
        else 0,
        "schedule_required_events": int(schedule_impact["event_id"].nunique())
        if not schedule_impact.empty
        else 0,
        "scenario_results": scenario_summaries,
        "exact_mechanical_crossing_rows_never_waived": int(
            continuity["continuity_reason"].eq(REASON_CROSSING).sum()
        ),
        "next": next_action,
        "interpretation": {
            "ceilings_are_authorization": False,
            "coverage_only_ceiling_means": "all unresolved coverage evidence hypothetically certified; no ticker subset selected",
            "schedule_only_ceiling_means": "all schedule-required transitions hypothetically resolved; no event subset selected",
            "coverage_plus_schedule_ceiling_keeps_exact_crossings_blocked": True,
            "price_observability_only_upper_bound_is_not_admissible": True,
        },
    }
    outputs["summary"].write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    output_hashes = {
        key: sha256_file(path)
        for key, path in outputs.items()
        if key != "manifest"
    }
    manifest = {
        "schema_version": "v4_3_ca_training_domain_residual_attribution_manifest_v1",
        "status": verdict,
        "outcome_blind": True,
        "input_hashes": {
            "parent_replay_manifest": parent_meta["manifest_sha256"],
            "frozen_validation_folds": str(config["frozen_validation_folds_sha256"]),
            **{f"parent_{k}": v for k, v in parent_meta["child_hashes"].items()},
        },
        "output_hashes": output_hashes,
        "guardrails": {
            "network_calls": False,
            "provider_calls": False,
            "retry_unresolved_tickers": False,
            "target_or_rank_materialized": False,
            "model_fit": False,
            "prediction_generated": False,
            "performance_computed": False,
            "protected_forward_accessed": False,
            "scientific_config_changed": False,
            "pass_preserving_subset_selection": False,
            "waive_exact_mechanical_crossings": False,
        },
    }
    outputs["manifest"].write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "status": verdict,
                "parent_replay_manifest_sha256": parent_meta["manifest_sha256"],
                "coverage_unresolved_tickers": summary["coverage_unresolved_tickers"],
                "schedule_required_events": summary["schedule_required_events"],
                "exact_mechanical_crossing_rows_never_waived": summary[
                    "exact_mechanical_crossing_rows_never_waived"
                ],
                "scenario_results": {
                    key: value["frozen_600"]
                    for key, value in scenario_summaries.items()
                },
                "manifest": str(outputs["manifest"]),
                "manifest_sha256": sha256_file(outputs["manifest"]),
                "historical_target_loaded": False,
                "model_fit": False,
                "performance_computed": False,
                "next": next_action,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
