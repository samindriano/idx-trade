"""Outcome-blind blocker attribution over the immutable V4 CA Stage-B ledger.

This script does not alter CA semantics or re-run provider acquisition.  It
computes row-level optimistic upper bounds by treating selected *currently
observed* blocker reasons as if they were resolved.  Hidden downstream blockers
are not reconstructed, so every counterfactual is explicitly an upper bound,
not a certification replay.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


EXPECTED_LEDGER_SHA256 = "585a9c55b200b2fe8e7b8d4a7f0453c3fdc1d659c666b036bbdec797c04ec634"
EXPECTED_ROWS = 344_790
EXPECTED_TICKERS = 610
EXPECTED_DATES = 600
GATE_RATE = 0.90
RESOLVED = "RESOLVED_NO_MECHANICAL_DISCONTINUITY"

REASON_SCHEDULE = "EXACT_OFFICIAL_EVENT_TRANSITION_REQUIRED"
REASON_KSEI_COVERAGE = "KSEI_REGISTERED_SECURITY_HISTORY_NOT_CERTIFIED"
REASON_CROSS_SOURCE = "CROSS_SOURCE_CANDIDATE_NOT_REPRESENTED_IN_KSEI_HISTORY"
REASON_KNOWN_CROSSING = "TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION"

SCENARIOS: dict[str, frozenset[str]] = {
    "BASELINE": frozenset(),
    "SCHEDULE_UNKNOWN_RESOLVED_CEILING": frozenset({REASON_SCHEDULE}),
    "KSEI_COVERAGE_RESOLVED_CEILING": frozenset({REASON_KSEI_COVERAGE}),
    "ALL_COVERAGE_RESOLVED_CEILING": frozenset({REASON_KSEI_COVERAGE, REASON_CROSS_SOURCE}),
    "SCHEDULE_PLUS_KSEI_COVERAGE_CEILING": frozenset({REASON_SCHEDULE, REASON_KSEI_COVERAGE}),
    "SCHEDULE_PLUS_ALL_COVERAGE_CEILING": frozenset({REASON_SCHEDULE, REASON_KSEI_COVERAGE, REASON_CROSS_SOURCE}),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_input(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"REQUIRED_INPUT_MISSING:{path}")
    actual = sha256(path)
    if actual != EXPECTED_LEDGER_SHA256:
        raise RuntimeError(f"PINNED_STAGE_B_LEDGER_HASH_MISMATCH:{actual}")
    return actual


def normalize_ledger(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "ticker",
        "signal_date",
        "horizon",
        "continuity_status",
        "continuity_reason",
        "blocking_event_ids",
    }
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"STAGE_B_LEDGER_COLUMNS_MISSING:{','.join(sorted(missing))}")
    out = frame.copy()
    out["ticker"] = out["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    out["signal_date"] = pd.to_datetime(out["signal_date"], errors="raise").dt.tz_localize(None).dt.normalize()
    out["horizon"] = pd.to_numeric(out["horizon"], errors="raise").astype(int)
    out["continuity_status"] = out["continuity_status"].astype(str)
    out["continuity_reason"] = out["continuity_reason"].astype(str)
    if len(out) != EXPECTED_ROWS:
        raise RuntimeError(f"STAGE_B_LEDGER_ROW_COUNT_CHANGED:{len(out)}")
    if out["ticker"].nunique() != EXPECTED_TICKERS:
        raise RuntimeError(f"STAGE_B_LEDGER_TICKER_COUNT_CHANGED:{out['ticker'].nunique()}")
    if out["signal_date"].nunique() != EXPECTED_DATES:
        raise RuntimeError(f"STAGE_B_LEDGER_DATE_COUNT_CHANGED:{out['signal_date'].nunique()}")
    if set(out["horizon"].unique()) != {5, 10}:
        raise RuntimeError("STAGE_B_LEDGER_HORIZON_SET_CHANGED")
    if out.duplicated(["ticker", "signal_date", "horizon"]).any():
        raise RuntimeError("STAGE_B_LEDGER_DUPLICATE_IDENTITY")
    return out


def scenario_resolved_mask(frame: pd.DataFrame, resolved_reasons: Iterable[str]) -> pd.Series:
    reasons = set(resolved_reasons)
    return frame["continuity_status"].eq(RESOLVED) | frame["continuity_reason"].isin(reasons)


def per_date_metrics(frame: pd.DataFrame, resolved_mask: pd.Series) -> pd.DataFrame:
    work = frame[["ticker", "signal_date", "horizon"]].copy()
    work["scenario_resolved"] = resolved_mask.to_numpy(dtype=bool)
    rows: list[dict[str, object]] = []
    for date, block in work.groupby("signal_date", sort=True):
        row: dict[str, object] = {"date": date.date().isoformat()}
        resolved_sets: dict[int, set[str]] = {}
        for horizon in (5, 10):
            sub = block[block["horizon"].eq(horizon)]
            resolved = sub[sub["scenario_resolved"]]
            rate = len(resolved) / len(sub) if len(sub) else np.nan
            row[f"h{horizon}_decision_rows"] = int(len(sub))
            row[f"h{horizon}_resolved_rows"] = int(len(resolved))
            row[f"h{horizon}_rate"] = float(rate)
            row[f"h{horizon}_gate"] = bool(len(sub) and rate >= GATE_RATE)
            resolved_sets[horizon] = set(resolved["ticker"])
        base = block[block["horizon"].eq(5)]
        consensus = resolved_sets[5] & resolved_sets[10]
        consensus_rate = len(consensus) / len(base) if len(base) else np.nan
        row["consensus_resolved_rows"] = int(len(consensus))
        row["consensus_rate"] = float(consensus_rate)
        row["consensus_gate"] = bool(len(base) and consensus_rate >= GATE_RATE)
        rows.append(row)
    result = pd.DataFrame(rows)
    if len(result) != EXPECTED_DATES:
        raise RuntimeError("SCENARIO_PER_DATE_COUNT_CHANGED")
    return result


def summarize_scenario(name: str, frame: pd.DataFrame, per_date: pd.DataFrame, mask: pd.Series) -> dict[str, object]:
    baseline = frame["continuity_status"].eq(RESOLVED)
    newly_resolved = mask & ~baseline
    metrics: dict[str, object] = {
        "scenario": name,
        "optimistic_upper_bound": name != "BASELINE",
        "newly_resolved_rows_assumed": int(newly_resolved.sum()),
        "h5_gate_dates": int(per_date["h5_gate"].sum()),
        "h10_gate_dates": int(per_date["h10_gate"].sum()),
        "consensus_gate_dates": int(per_date["consensus_gate"].sum()),
        "h5_min_rate": float(per_date["h5_rate"].min()),
        "h10_min_rate": float(per_date["h10_rate"].min()),
        "consensus_min_rate": float(per_date["consensus_rate"].min()),
    }
    for metric in ("h5", "h10", "consensus"):
        col = f"{metric}_rate"
        worst = per_date.loc[per_date[col].idxmin()]
        metrics[f"{metric}_worst_date"] = str(worst["date"])
    metrics["all_600_pass"] = bool(
        metrics["h5_gate_dates"] == EXPECTED_DATES
        and metrics["h10_gate_dates"] == EXPECTED_DATES
        and metrics["consensus_gate_dates"] == EXPECTED_DATES
    )
    return metrics


def attribution_verdict(summaries: dict[str, dict[str, object]]) -> str:
    schedule = bool(summaries["SCHEDULE_UNKNOWN_RESOLVED_CEILING"]["all_600_pass"])
    coverage = bool(summaries["ALL_COVERAGE_RESOLVED_CEILING"]["all_600_pass"])
    combined = bool(summaries["SCHEDULE_PLUS_ALL_COVERAGE_CEILING"]["all_600_pass"])
    if schedule and not coverage:
        return "OPTIMISTIC_ATTRIBUTION_SCHEDULE_DIMENSION_ALONE_CAN_CLEAR_GATE_COVERAGE_ALONE_CANNOT"
    if coverage and not schedule:
        return "OPTIMISTIC_ATTRIBUTION_COVERAGE_DIMENSION_ALONE_CAN_CLEAR_GATE_SCHEDULE_ALONE_CANNOT"
    if schedule and coverage:
        return "OPTIMISTIC_ATTRIBUTION_EITHER_DIMENSION_ALONE_CAN_CLEAR_GATE"
    if combined:
        return "OPTIMISTIC_ATTRIBUTION_BOTH_SCHEDULE_AND_COVERAGE_DIMENSIONS_REQUIRED"
    return "OPTIMISTIC_ATTRIBUTION_EVEN_COMBINED_CURRENT_BLOCKERS_CANNOT_CLEAR_GATE"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-b-ledger", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    input_sha = verify_input(args.stage_b_ledger)
    args.output_dir.mkdir(parents=True)

    frame = normalize_ledger(pd.read_csv(args.stage_b_ledger))
    reason_counts = dict(sorted(Counter(frame["continuity_reason"]).items()))
    scenario_summaries: dict[str, dict[str, object]] = {}
    per_date_frames: list[pd.DataFrame] = []

    for name, reasons in SCENARIOS.items():
        mask = scenario_resolved_mask(frame, reasons)
        per_date = per_date_metrics(frame, mask)
        scenario_summaries[name] = summarize_scenario(name, frame, per_date, mask)
        tagged = per_date.copy()
        tagged.insert(0, "scenario", name)
        per_date_frames.append(tagged)

    verdict = attribution_verdict(scenario_summaries)
    summary = {
        "schema_version": "v4_ca_blocker_attribution_v1",
        "status": "V4_CA_BLOCKER_ATTRIBUTION_COMPLETE",
        "verdict": verdict,
        "diagnostic_only": True,
        "optimistic_row_level_upper_bounds": True,
        "hidden_downstream_blockers_reconstructed": False,
        "outcome_blind": True,
        "provider_calls": False,
        "target_or_rank_materialized": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "gate_rate": GATE_RATE,
        "input_stage_b_ledger_sha256": input_sha,
        "reason_counts": reason_counts,
        "known_mechanical_crossing_rows_never_waived": int(reason_counts.get(REASON_KNOWN_CROSSING, 0)),
        "scenarios": scenario_summaries,
    }

    per_date_all = pd.concat(per_date_frames, ignore_index=True)
    per_date_path = args.output_dir / "blocker_attribution_per_date.csv"
    summary_path = args.output_dir / "summary.json"
    per_date_all.to_csv(per_date_path, index=False, lineterminator="\n")
    summary["output_hashes"] = {"per_date": sha256(per_date_path)}
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "v4_ca_blocker_attribution_manifest_v1",
        "status": summary["status"],
        "input_stage_b_ledger_sha256": input_sha,
        "summary_sha256": sha256(summary_path),
        "output_hashes": {"per_date": sha256(per_date_path)},
        "outcome_blind": True,
        "provider_calls": False,
    }
    manifest_path = args.output_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": verdict, "summary": scenario_summaries, "manifest_sha256": sha256(manifest_path)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
