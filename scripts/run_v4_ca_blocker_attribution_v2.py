"""Outcome-blind blocker attribution over the post-KSEI V4 CA continuity ledger.

This is a diagnostic upper-bound calculator only. It never changes corporate-
action semantics and never reconstructs hidden downstream events. Selected
currently-observed blocker reasons are optimistically treated as resolved so
we can identify which remaining evidence dimensions are capable of clearing
the frozen 90% per-date continuity gate.
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


SCHEMA_VERSION = "v4_ca_blocker_attribution_v2"
EXPECTED_LEDGER_SHA256 = "9dce85c55a9e8a9e1effba5c7e0d24faa150bfb0d70c0162cfb85955d8a435ec"
EXPECTED_ROWS = 344_790
EXPECTED_TICKERS = 610
EXPECTED_DATES = 600
GATE_RATE = 0.90
RESOLVED = "RESOLVED_NO_MECHANICAL_DISCONTINUITY"

REASON_NO_CROSSING = "NO_MECHANICAL_CA_TRANSITION_CROSSES_TARGET_INTERVAL"
REASON_SCHEDULE = "EXACT_OFFICIAL_EVENT_TRANSITION_REQUIRED"
REASON_KSEI_COVERAGE = "KSEI_REGISTERED_SECURITY_HISTORY_NOT_CERTIFIED"
REASON_CROSS_SOURCE = "CROSS_SOURCE_CANDIDATE_NOT_REPRESENTED_IN_KSEI_HISTORY"
REASON_KNOWN_CROSSING = "TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION"

EXPECTED_REASON_COUNTS = {
    REASON_NO_CROSSING: 312_294,
    REASON_SCHEDULE: 24_212,
    REASON_KSEI_COVERAGE: 6_844,
    REASON_CROSS_SOURCE: 1_200,
    REASON_KNOWN_CROSSING: 240,
}

EXPECTED_BASELINE = {
    "h5_gate_dates": 462,
    "h10_gate_dates": 461,
    "consensus_gate_dates": 461,
    "h5_min_rate": 0.8814102564,
    "h10_min_rate": 0.8789808917,
    "consensus_min_rate": 0.8789808917,
}

SCENARIOS: dict[str, frozenset[str]] = {
    "BASELINE": frozenset(),
    "SCHEDULE_ONLY_CEILING": frozenset({REASON_SCHEDULE}),
    "KSEI_COVERAGE_ONLY_CEILING": frozenset({REASON_KSEI_COVERAGE}),
    "CROSS_SOURCE_ONLY_CEILING": frozenset({REASON_CROSS_SOURCE}),
    "ALL_COVERAGE_CEILING": frozenset({REASON_KSEI_COVERAGE, REASON_CROSS_SOURCE}),
    "SCHEDULE_PLUS_KSEI_COVERAGE_CEILING": frozenset({REASON_SCHEDULE, REASON_KSEI_COVERAGE}),
    "SCHEDULE_PLUS_CROSS_SOURCE_CEILING": frozenset({REASON_SCHEDULE, REASON_CROSS_SOURCE}),
    "SCHEDULE_PLUS_ALL_COVERAGE_CEILING": frozenset(
        {REASON_SCHEDULE, REASON_KSEI_COVERAGE, REASON_CROSS_SOURCE}
    ),
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
        raise RuntimeError(f"PINNED_POST_KSEI_LEDGER_HASH_MISMATCH:{actual}")
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
        raise RuntimeError(f"LEDGER_COLUMNS_MISSING:{','.join(sorted(missing))}")

    out = frame.copy()
    out["ticker"] = (
        out["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    )
    out["signal_date"] = (
        pd.to_datetime(out["signal_date"], errors="raise").dt.tz_localize(None).dt.normalize()
    )
    out["horizon"] = pd.to_numeric(out["horizon"], errors="raise").astype(int)
    out["continuity_status"] = out["continuity_status"].astype(str)
    out["continuity_reason"] = out["continuity_reason"].astype(str)

    if len(out) != EXPECTED_ROWS:
        raise RuntimeError(f"LEDGER_ROW_COUNT_CHANGED:{len(out)}")
    if out["ticker"].nunique() != EXPECTED_TICKERS:
        raise RuntimeError(f"LEDGER_TICKER_COUNT_CHANGED:{out['ticker'].nunique()}")
    if out["signal_date"].nunique() != EXPECTED_DATES:
        raise RuntimeError(f"LEDGER_DATE_COUNT_CHANGED:{out['signal_date'].nunique()}")
    if set(out["horizon"].unique()) != {5, 10}:
        raise RuntimeError("LEDGER_HORIZON_SET_CHANGED")
    if out.duplicated(["ticker", "signal_date", "horizon"]).any():
        raise RuntimeError("LEDGER_DUPLICATE_IDENTITY")

    reason_counts = dict(Counter(out["continuity_reason"]))
    if reason_counts != EXPECTED_REASON_COUNTS:
        raise RuntimeError(
            "POST_KSEI_REASON_COUNTS_CHANGED:"
            + json.dumps(dict(sorted(reason_counts.items())), sort_keys=True)
        )

    known_crossing_resolved = (
        out["continuity_reason"].eq(REASON_KNOWN_CROSSING)
        & out["continuity_status"].eq(RESOLVED)
    )
    if known_crossing_resolved.any():
        raise RuntimeError("KNOWN_MECHANICAL_CROSSING_ALREADY_MARKED_RESOLVED")
    return out


def scenario_resolved_mask(frame: pd.DataFrame, resolved_reasons: Iterable[str]) -> pd.Series:
    reasons = set(resolved_reasons)
    if REASON_KNOWN_CROSSING in reasons:
        raise RuntimeError("KNOWN_MECHANICAL_CROSSING_CANNOT_BE_WAIVED")
    mask = frame["continuity_status"].eq(RESOLVED) | frame["continuity_reason"].isin(reasons)
    crossing = frame["continuity_reason"].eq(REASON_KNOWN_CROSSING)
    if bool(mask[crossing].any()):
        raise RuntimeError("SCENARIO_WAIVED_KNOWN_MECHANICAL_CROSSING")
    return mask


def per_date_metrics(frame: pd.DataFrame, resolved_mask: pd.Series) -> pd.DataFrame:
    if len(resolved_mask) != len(frame):
        raise RuntimeError("SCENARIO_RESOLVED_MASK_LENGTH_MISMATCH")
    if not resolved_mask.index.equals(frame.index):
        raise RuntimeError("SCENARIO_RESOLVED_MASK_INDEX_MISMATCH")

    expected_dates = int(frame["signal_date"].nunique())
    work = frame[["ticker", "signal_date", "horizon"]].copy()
    work["scenario_resolved"] = resolved_mask.to_numpy(dtype=bool)
    rows: list[dict[str, object]] = []

    for date, block in work.groupby("signal_date", sort=True):
        row: dict[str, object] = {"date": date.date().isoformat()}
        resolved_sets: dict[int, set[str]] = {}
        decision_sets: dict[int, set[str]] = {}
        for horizon in (5, 10):
            sub = block[block["horizon"].eq(horizon)]
            resolved = sub[sub["scenario_resolved"]]
            rate = len(resolved) / len(sub) if len(sub) else np.nan
            row[f"h{horizon}_decision_rows"] = int(len(sub))
            row[f"h{horizon}_resolved_rows"] = int(len(resolved))
            row[f"h{horizon}_rate"] = float(rate)
            row[f"h{horizon}_gate"] = bool(len(sub) and rate >= GATE_RATE)
            resolved_sets[horizon] = set(resolved["ticker"])
            decision_sets[horizon] = set(sub["ticker"])

        if decision_sets[5] != decision_sets[10]:
            raise RuntimeError(f"H5_H10_DECISION_POPULATION_MISMATCH:{date.date().isoformat()}")
        consensus = resolved_sets[5] & resolved_sets[10]
        denominator = len(decision_sets[5])
        consensus_rate = len(consensus) / denominator if denominator else np.nan
        row["consensus_resolved_rows"] = int(len(consensus))
        row["consensus_rate"] = float(consensus_rate)
        row["consensus_gate"] = bool(denominator and consensus_rate >= GATE_RATE)
        rows.append(row)

    result = pd.DataFrame(rows)
    if len(result) != expected_dates:
        raise RuntimeError(f"SCENARIO_PER_DATE_COUNT_CHANGED:{len(result)}!={expected_dates}")
    return result


def summarize_scenario(
    name: str,
    frame: pd.DataFrame,
    per_date: pd.DataFrame,
    mask: pd.Series,
) -> dict[str, object]:
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


def verify_baseline(summary: dict[str, object]) -> None:
    for key in ("h5_gate_dates", "h10_gate_dates", "consensus_gate_dates"):
        if int(summary[key]) != int(EXPECTED_BASELINE[key]):
            raise RuntimeError(f"POST_KSEI_BASELINE_{key.upper()}_CHANGED:{summary[key]}")
    for key in ("h5_min_rate", "h10_min_rate", "consensus_min_rate"):
        if not np.isclose(float(summary[key]), float(EXPECTED_BASELINE[key]), atol=5e-11, rtol=0.0):
            raise RuntimeError(f"POST_KSEI_BASELINE_{key.upper()}_CHANGED:{summary[key]}")


def minimal_clearing_scenarios(
    summaries: dict[str, dict[str, object]],
) -> list[str]:
    passing = [name for name, value in summaries.items() if name != "BASELINE" and value["all_600_pass"]]
    result: list[str] = []
    for name in passing:
        reasons = SCENARIOS[name]
        if not any(SCENARIOS[other] < reasons for other in passing):
            result.append(name)
    return sorted(result)


def attribution_verdict(summaries: dict[str, dict[str, object]]) -> str:
    if bool(summaries["BASELINE"]["all_600_pass"]):
        return "OPTIMISTIC_ATTRIBUTION_V2_BASELINE_ALREADY_CLEARS_GATE"
    minimal = minimal_clearing_scenarios(summaries)
    if not minimal:
        return "OPTIMISTIC_ATTRIBUTION_V2_EVEN_ALL_CURRENT_REMOVABLE_BLOCKERS_CANNOT_CLEAR_GATE"
    if len(minimal) == 1:
        return f"OPTIMISTIC_ATTRIBUTION_V2_MINIMAL_CLEARING_SCENARIO_{minimal[0]}"
    return "OPTIMISTIC_ATTRIBUTION_V2_MULTIPLE_MINIMAL_CLEARING_SCENARIOS"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--continuity-ledger", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")

    input_sha = verify_input(args.continuity_ledger)
    frame = normalize_ledger(pd.read_csv(args.continuity_ledger))
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

    verify_baseline(scenario_summaries["BASELINE"])
    verdict = attribution_verdict(scenario_summaries)
    minimal = minimal_clearing_scenarios(scenario_summaries)
    per_date_all = pd.concat(per_date_frames, ignore_index=True)

    # Fresh-root budget is consumed only after all read/validation/computation passes.
    args.output_dir.mkdir(parents=True)
    per_date_path = args.output_dir / "blocker_attribution_v2_per_date.csv"
    summary_path = args.output_dir / "summary.json"
    per_date_all.to_csv(per_date_path, index=False, lineterminator="\n")

    summary = {
        "schema_version": SCHEMA_VERSION,
        "status": "V4_CA_BLOCKER_ATTRIBUTION_V2_COMPLETE",
        "verdict": verdict,
        "minimal_clearing_scenarios": minimal,
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
        "input_continuity_ledger_sha256": input_sha,
        "reason_counts": reason_counts,
        "known_mechanical_crossing_rows_never_waived": int(reason_counts[REASON_KNOWN_CROSSING]),
        "scenarios": scenario_summaries,
        "output_hashes": {"per_date": sha256(per_date_path)},
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest = {
        "schema_version": "v4_ca_blocker_attribution_v2_manifest",
        "status": summary["status"],
        "input_continuity_ledger_sha256": input_sha,
        "summary_sha256": sha256(summary_path),
        "output_hashes": {"per_date": sha256(per_date_path)},
        "outcome_blind": True,
        "provider_calls": False,
    }
    manifest_path = args.output_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "verdict": verdict,
                "minimal_clearing_scenarios": minimal,
                "scenarios": scenario_summaries,
                "manifest_sha256": sha256(manifest_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
