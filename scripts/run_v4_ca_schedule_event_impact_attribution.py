"""Outcome-blind event-level attribution for residual V4 CA schedule blockers.

This diagnostic consumes the exact post-KSEI continuity ledger and the exact
39-event schedule-evidence-needs table.  It never changes CA semantics.  A
schedule-blocked row is treated as hypothetically resolved only when *all*
blocking schedule event IDs recorded on that row are included in the selected
counterfactual subset.

The runner reports per-event impact, a deterministic gate-clearing subset, and
whether global minimum cardinality was actually proven.  Counterfactuals are
optimistic upper bounds only and are never continuity certification.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
from itertools import combinations
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


EXPECTED_LEDGER_SHA256 = "9dce85c55a9e8a9e1effba5c7e0d24faa150bfb0d70c0162cfb85955d8a435ec"
EXPECTED_SCHEDULE_NEEDS_SHA256 = "1988f2bb679b09835e045235fa7aa46f4d8c62cf9531e76a5b5b889d848a127a"
EXPECTED_ROWS = 344_790
EXPECTED_TICKERS = 610
EXPECTED_DATES = 600
EXPECTED_SCHEDULE_EVENTS = 39
EXPECTED_REASON_COUNTS = {
    "NO_MECHANICAL_CA_TRANSITION_CROSSES_TARGET_INTERVAL": 312_294,
    "EXACT_OFFICIAL_EVENT_TRANSITION_REQUIRED": 24_212,
    "KSEI_REGISTERED_SECURITY_HISTORY_NOT_CERTIFIED": 6_844,
    "TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION": 240,
    "CROSS_SOURCE_CANDIDATE_NOT_REPRESENTED_IN_KSEI_HISTORY": 1_200,
}
EXPECTED_BASELINE_GATE_DATES = (462, 461, 461)
EXPECTED_SCHEDULE_ONLY_GATE_DATES = (600, 600, 600)
EXPECTED_BASELINE_MIN_RATES = (
    0.8814102564102564,
    0.8789808917197452,
    0.8789808917197452,
)
EXPECTED_SCHEDULE_ONLY_MIN_RATES = (
    0.9615384615384616,
    0.9585987261146497,
    0.9585987261146497,
)
GATE_RATE = 0.90
RESOLVED = "RESOLVED_NO_MECHANICAL_DISCONTINUITY"
REASON_SCHEDULE = "EXACT_OFFICIAL_EVENT_TRANSITION_REQUIRED"
REASON_KNOWN_CROSSING = "TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION"
EXACT_SEARCH_MAX_CRITICAL_EVENTS = 12


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_hash(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise RuntimeError(f"REQUIRED_INPUT_MISSING:{label}:{path}")
    actual = sha256(path)
    if actual != expected:
        raise RuntimeError(f"PINNED_INPUT_HASH_MISMATCH:{label}:{actual}")
    return actual


def parse_event_ids(value: object) -> frozenset[str]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return frozenset()
    text = str(value).strip()
    if not text:
        return frozenset()
    return frozenset(part.strip() for part in text.split("|") if part.strip())


def _required_count(counts: np.ndarray) -> np.ndarray:
    return np.ceil(GATE_RATE * counts.astype(float) - 1e-12).astype(np.int64)


@dataclass(frozen=True)
class EvalResult:
    h5_resolved: np.ndarray
    h10_resolved: np.ndarray
    consensus_resolved: np.ndarray
    h5_rate: np.ndarray
    h10_rate: np.ndarray
    consensus_rate: np.ndarray
    h5_gate: np.ndarray
    h10_gate: np.ndarray
    consensus_gate: np.ndarray
    total_deficit: int
    resolved_schedule_rows: int

    @property
    def gate_dates(self) -> tuple[int, int, int]:
        return (
            int(self.h5_gate.sum()),
            int(self.h10_gate.sum()),
            int(self.consensus_gate.sum()),
        )

    @property
    def min_rates(self) -> tuple[float, float, float]:
        return (
            float(self.h5_rate.min()),
            float(self.h10_rate.min()),
            float(self.consensus_rate.min()),
        )

    @property
    def all_pass(self) -> bool:
        return self.gate_dates == (EXPECTED_DATES, EXPECTED_DATES, EXPECTED_DATES)


@dataclass
class ImpactEngine:
    frame: pd.DataFrame
    event_ids: tuple[str, ...]
    event_to_bit: dict[str, int]
    baseline: np.ndarray
    schedule_rows: np.ndarray
    requirement_masks: np.ndarray
    horizons: np.ndarray
    date_indices: np.ndarray
    h5_indices: np.ndarray
    h10_indices: np.ndarray
    pair_h5_indices: np.ndarray
    pair_h10_indices: np.ndarray
    pair_date_indices: np.ndarray
    h5_decision: np.ndarray
    h10_decision: np.ndarray
    consensus_decision: np.ndarray
    required_h5: np.ndarray
    required_h10: np.ndarray
    required_consensus: np.ndarray
    dates: tuple[pd.Timestamp, ...]

    def selected_mask(self, selected: Iterable[str]) -> np.uint64:
        mask = np.uint64(0)
        for event_id in selected:
            try:
                bit = self.event_to_bit[event_id]
            except KeyError as exc:
                raise RuntimeError(f"UNKNOWN_SELECTED_EVENT_ID:{event_id}") from exc
            mask |= np.uint64(1) << np.uint64(bit)
        return mask

    def evaluate(self, selected: Iterable[str]) -> EvalResult:
        selected_mask = self.selected_mask(selected)
        hypothetically_resolved_schedule = self.schedule_rows & (
            (self.requirement_masks & ~selected_mask) == 0
        )
        resolved = self.baseline | hypothetically_resolved_schedule

        h5_resolved = np.bincount(
            self.date_indices[self.h5_indices],
            weights=resolved[self.h5_indices].astype(np.int64),
            minlength=EXPECTED_DATES,
        ).astype(np.int64)
        h10_resolved = np.bincount(
            self.date_indices[self.h10_indices],
            weights=resolved[self.h10_indices].astype(np.int64),
            minlength=EXPECTED_DATES,
        ).astype(np.int64)
        consensus_bool = resolved[self.pair_h5_indices] & resolved[self.pair_h10_indices]
        consensus_resolved = np.bincount(
            self.pair_date_indices,
            weights=consensus_bool.astype(np.int64),
            minlength=EXPECTED_DATES,
        ).astype(np.int64)

        h5_rate = h5_resolved / self.h5_decision
        h10_rate = h10_resolved / self.h10_decision
        consensus_rate = consensus_resolved / self.consensus_decision
        h5_gate = h5_resolved >= self.required_h5
        h10_gate = h10_resolved >= self.required_h10
        consensus_gate = consensus_resolved >= self.required_consensus
        total_deficit = int(
            np.maximum(0, self.required_h5 - h5_resolved).sum()
            + np.maximum(0, self.required_h10 - h10_resolved).sum()
            + np.maximum(0, self.required_consensus - consensus_resolved).sum()
        )
        return EvalResult(
            h5_resolved=h5_resolved,
            h10_resolved=h10_resolved,
            consensus_resolved=consensus_resolved,
            h5_rate=h5_rate,
            h10_rate=h10_rate,
            consensus_rate=consensus_rate,
            h5_gate=h5_gate,
            h10_gate=h10_gate,
            consensus_gate=consensus_gate,
            total_deficit=total_deficit,
            resolved_schedule_rows=int(hypothetically_resolved_schedule.sum()),
        )


def build_engine(frame: pd.DataFrame, event_ids: tuple[str, ...]) -> ImpactEngine:
    event_to_bit = {event_id: idx for idx, event_id in enumerate(event_ids)}
    if len(event_to_bit) != len(event_ids):
        raise RuntimeError("SCHEDULE_EVENT_ID_DUPLICATE")
    if len(event_ids) > 63:
        raise RuntimeError("EVENT_MASK_WIDTH_EXCEEDED")

    requirement_masks = np.zeros(len(frame), dtype=np.uint64)
    schedule_rows = frame["continuity_reason"].eq(REASON_SCHEDULE).to_numpy(dtype=bool)
    parsed_sets: list[frozenset[str]] = []
    schedule_positions = np.flatnonzero(schedule_rows)
    for position, raw in zip(
        schedule_positions,
        frame.loc[schedule_rows, "blocking_event_ids"].tolist(),
    ):
        event_set = parse_event_ids(raw)
        if not event_set:
            raise RuntimeError("SCHEDULE_BLOCKED_ROW_WITHOUT_EVENT_ID")
        unknown = sorted(event_set - set(event_ids))
        if unknown:
            raise RuntimeError(f"SCHEDULE_ROW_UNKNOWN_EVENT_IDS:{','.join(unknown)}")
        mask = np.uint64(0)
        for event_id in event_set:
            mask |= np.uint64(1) << np.uint64(event_to_bit[event_id])
        requirement_masks[position] = mask
        parsed_sets.append(event_set)

    dates = tuple(sorted(frame["signal_date"].drop_duplicates().tolist()))
    if len(dates) != EXPECTED_DATES:
        raise RuntimeError("DATE_IDENTITY_CHANGED")
    date_to_idx = {date: idx for idx, date in enumerate(dates)}
    date_indices = frame["signal_date"].map(date_to_idx).to_numpy(dtype=np.int64)
    horizons = frame["horizon"].to_numpy(dtype=np.int64)
    h5_indices = np.flatnonzero(horizons == 5)
    h10_indices = np.flatnonzero(horizons == 10)

    pair_source = frame.reset_index(names="row_index")[["row_index", "ticker", "signal_date", "horizon"]]
    h5 = pair_source[pair_source["horizon"].eq(5)].rename(columns={"row_index": "h5_index"})
    h10 = pair_source[pair_source["horizon"].eq(10)].rename(columns={"row_index": "h10_index"})
    pairs = h5[["ticker", "signal_date", "h5_index"]].merge(
        h10[["ticker", "signal_date", "h10_index"]],
        on=["ticker", "signal_date"],
        how="inner",
        validate="one_to_one",
    )
    if len(pairs) * 2 != len(frame):
        raise RuntimeError("H5_H10_DECISION_IDENTITY_NOT_EXACT_PAIR")
    pair_h5_indices = pairs["h5_index"].to_numpy(dtype=np.int64)
    pair_h10_indices = pairs["h10_index"].to_numpy(dtype=np.int64)
    pair_date_indices = pairs["signal_date"].map(date_to_idx).to_numpy(dtype=np.int64)

    h5_decision = np.bincount(date_indices[h5_indices], minlength=EXPECTED_DATES).astype(np.int64)
    h10_decision = np.bincount(date_indices[h10_indices], minlength=EXPECTED_DATES).astype(np.int64)
    consensus_decision = np.bincount(pair_date_indices, minlength=EXPECTED_DATES).astype(np.int64)
    if not np.array_equal(h5_decision, consensus_decision):
        raise RuntimeError("CONSENSUS_DENOMINATOR_NOT_H5_DECISION_IDENTITY")

    return ImpactEngine(
        frame=frame,
        event_ids=event_ids,
        event_to_bit=event_to_bit,
        baseline=frame["continuity_status"].eq(RESOLVED).to_numpy(dtype=bool),
        schedule_rows=schedule_rows,
        requirement_masks=requirement_masks,
        horizons=horizons,
        date_indices=date_indices,
        h5_indices=h5_indices,
        h10_indices=h10_indices,
        pair_h5_indices=pair_h5_indices,
        pair_h10_indices=pair_h10_indices,
        pair_date_indices=pair_date_indices,
        h5_decision=h5_decision,
        h10_decision=h10_decision,
        consensus_decision=consensus_decision,
        required_h5=_required_count(h5_decision),
        required_h10=_required_count(h10_decision),
        required_consensus=_required_count(consensus_decision),
        dates=dates,
    )


def validate_inputs(ledger_path: Path, schedule_needs_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, ImpactEngine, dict[str, str]]:
    hashes = {
        "continuity_ledger": verify_hash(ledger_path, EXPECTED_LEDGER_SHA256, "continuity_ledger"),
        "schedule_evidence_needs": verify_hash(
            schedule_needs_path, EXPECTED_SCHEDULE_NEEDS_SHA256, "schedule_evidence_needs"
        ),
    }
    needs = pd.read_csv(schedule_needs_path, dtype=str, keep_default_na=False)
    required_needs = {"event_id", "ticker", "source_type", "family", "semantic_class", "reason", "source_dates"}
    missing_needs = required_needs - set(needs.columns)
    if missing_needs:
        raise RuntimeError(f"SCHEDULE_NEEDS_COLUMNS_MISSING:{','.join(sorted(missing_needs))}")
    if len(needs) != EXPECTED_SCHEDULE_EVENTS or needs["event_id"].nunique() != EXPECTED_SCHEDULE_EVENTS:
        raise RuntimeError("SCHEDULE_EVENT_IDENTITY_CHANGED")
    if not needs["semantic_class"].eq("SCHEDULE_REQUIRED").all():
        raise RuntimeError("SCHEDULE_NEEDS_SEMANTIC_CLASS_CHANGED")
    event_ids = tuple(sorted(needs["event_id"].tolist()))

    frame = pd.read_csv(
        ledger_path,
        dtype={
            "ticker": str,
            "continuity_status": str,
            "continuity_reason": str,
            "blocking_event_ids": str,
        },
        keep_default_na=False,
        low_memory=False,
    )
    required = {"ticker", "signal_date", "horizon", "continuity_status", "continuity_reason", "blocking_event_ids"}
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"LEDGER_COLUMNS_MISSING:{','.join(sorted(missing))}")
    frame["ticker"] = frame["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    frame["signal_date"] = pd.to_datetime(frame["signal_date"], errors="raise").dt.tz_localize(None).dt.normalize()
    frame["horizon"] = pd.to_numeric(frame["horizon"], errors="raise").astype(int)
    if len(frame) != EXPECTED_ROWS:
        raise RuntimeError(f"LEDGER_ROW_COUNT_CHANGED:{len(frame)}")
    if frame["ticker"].nunique() != EXPECTED_TICKERS:
        raise RuntimeError("LEDGER_TICKER_COUNT_CHANGED")
    if frame["signal_date"].nunique() != EXPECTED_DATES:
        raise RuntimeError("LEDGER_DATE_COUNT_CHANGED")
    if set(frame["horizon"].unique()) != {5, 10}:
        raise RuntimeError("LEDGER_HORIZON_SET_CHANGED")
    if frame.duplicated(["ticker", "signal_date", "horizon"]).any():
        raise RuntimeError("LEDGER_DUPLICATE_IDENTITY")
    reason_counts = dict(Counter(frame["continuity_reason"]))
    if reason_counts != EXPECTED_REASON_COUNTS:
        raise RuntimeError(f"LEDGER_REASON_COUNTS_CHANGED:{json.dumps(reason_counts, sort_keys=True)}")
    crossing_resolved = frame["continuity_reason"].eq(REASON_KNOWN_CROSSING) & frame["continuity_status"].eq(RESOLVED)
    if crossing_resolved.any():
        raise RuntimeError("KNOWN_MECHANICAL_CROSSING_MARKED_RESOLVED")

    engine = build_engine(frame, event_ids)
    baseline = engine.evaluate(())
    schedule_only = engine.evaluate(event_ids)
    if baseline.gate_dates != EXPECTED_BASELINE_GATE_DATES:
        raise RuntimeError(f"BASELINE_GATE_DATES_CHANGED:{baseline.gate_dates}")
    if schedule_only.gate_dates != EXPECTED_SCHEDULE_ONLY_GATE_DATES:
        raise RuntimeError(f"SCHEDULE_ONLY_GATE_DATES_CHANGED:{schedule_only.gate_dates}")
    if not np.allclose(baseline.min_rates, EXPECTED_BASELINE_MIN_RATES, rtol=0, atol=1e-12):
        raise RuntimeError(f"BASELINE_MIN_RATES_CHANGED:{baseline.min_rates}")
    if not np.allclose(schedule_only.min_rates, EXPECTED_SCHEDULE_ONLY_MIN_RATES, rtol=0, atol=1e-12):
        raise RuntimeError(f"SCHEDULE_ONLY_MIN_RATES_CHANGED:{schedule_only.min_rates}")
    if not schedule_only.all_pass:
        raise RuntimeError("SCHEDULE_ONLY_CEILING_NO_LONGER_CLEARS_GATE")
    return frame, needs, engine, hashes


def result_summary(result: EvalResult) -> dict[str, object]:
    return {
        "h5_gate_dates": result.gate_dates[0],
        "h10_gate_dates": result.gate_dates[1],
        "consensus_gate_dates": result.gate_dates[2],
        "h5_min_rate": result.min_rates[0],
        "h10_min_rate": result.min_rates[1],
        "consensus_min_rate": result.min_rates[2],
        "total_deficit_units": result.total_deficit,
        "resolved_schedule_rows": result.resolved_schedule_rows,
        "all_600_pass": result.all_pass,
    }


def critical_event_ids(engine: ImpactEngine, baseline: EvalResult) -> tuple[str, ...]:
    failing_dates = ~(baseline.h5_gate & baseline.h10_gate & baseline.consensus_gate)
    critical_rows = engine.schedule_rows & failing_dates[engine.date_indices]
    mask_union = np.uint64(0)
    for mask in engine.requirement_masks[critical_rows]:
        mask_union |= mask
    output = []
    for event_id, bit in sorted(engine.event_to_bit.items()):
        if mask_union & (np.uint64(1) << np.uint64(bit)):
            output.append(event_id)
    return tuple(output)


def event_impact_table(engine: ImpactEngine, needs: pd.DataFrame, baseline: EvalResult) -> pd.DataFrame:
    meta = needs.set_index("event_id", drop=False)
    baseline_gate_total = sum(baseline.gate_dates)
    failing_dates = ~(baseline.h5_gate & baseline.h10_gate & baseline.consensus_gate)
    rows: list[dict[str, object]] = []
    for event_id in engine.event_ids:
        bitmask = np.uint64(1) << np.uint64(engine.event_to_bit[event_id])
        contains = engine.schedule_rows & ((engine.requirement_masks & bitmask) != 0)
        sole = engine.schedule_rows & (engine.requirement_masks == bitmask)
        result = engine.evaluate((event_id,))
        affected_dates = np.unique(engine.date_indices[contains])
        affected_failing_dates = np.unique(engine.date_indices[contains & failing_dates[engine.date_indices]])
        source = meta.loc[event_id]
        rows.append(
            {
                "event_id": event_id,
                "ticker": source["ticker"],
                "source_type": source["source_type"],
                "family": source["family"],
                "reason": source["reason"],
                "source_dates": source["source_dates"],
                "blocking_rows": int(contains.sum()),
                "sole_blocking_rows": int(sole.sum()),
                "affected_signal_dates": int(len(affected_dates)),
                "affected_baseline_failing_dates": int(len(affected_failing_dates)),
                "single_event_deficit_reduction": int(baseline.total_deficit - result.total_deficit),
                "single_event_new_gate_metrics": int(sum(result.gate_dates) - baseline_gate_total),
                "single_event_h5_gate_dates": result.gate_dates[0],
                "single_event_h10_gate_dates": result.gate_dates[1],
                "single_event_consensus_gate_dates": result.gate_dates[2],
                "single_event_resolved_schedule_rows": int(result.resolved_schedule_rows - baseline.resolved_schedule_rows),
            }
        )
    return pd.DataFrame(rows).sort_values(
        [
            "single_event_deficit_reduction",
            "single_event_new_gate_metrics",
            "affected_baseline_failing_dates",
            "blocking_rows",
            "event_id",
        ],
        ascending=[False, False, False, False, True],
        kind="mergesort",
    ).reset_index(drop=True)


def greedy_gate_clearing_subset(
    engine: ImpactEngine,
    critical: tuple[str, ...],
) -> tuple[list[str], list[dict[str, object]]]:
    selected: list[str] = []
    selected_set: set[str] = set()
    current = engine.evaluate(selected)
    trace: list[dict[str, object]] = []
    critical_set = set(critical)
    while not current.all_pass:
        candidates = sorted(critical_set - selected_set)
        if not candidates:
            raise RuntimeError("GREEDY_EXHAUSTED_CRITICAL_EVENTS_BEFORE_GATE_CLEAR")
        best_event: str | None = None
        best_result: EvalResult | None = None
        best_score: tuple[int, int, int, int] | None = None
        current_gate_total = sum(current.gate_dates)
        for event_id in candidates:
            candidate_selected = selected_set | {event_id}
            result = engine.evaluate(candidate_selected)
            bitmask = np.uint64(1) << np.uint64(engine.event_to_bit[event_id])
            potential_rows = int(
                (engine.schedule_rows & ((engine.requirement_masks & bitmask) != 0)).sum()
            )
            score = (
                current.total_deficit - result.total_deficit,
                sum(result.gate_dates) - current_gate_total,
                result.resolved_schedule_rows - current.resolved_schedule_rows,
                potential_rows,
            )
            if best_score is None or score > best_score:
                best_score = score
                best_event = event_id
                best_result = result
        assert best_event is not None and best_result is not None and best_score is not None
        selected.append(best_event)
        selected_set.add(best_event)
        current = best_result
        trace.append(
            {
                "step": len(selected),
                "event_id": best_event,
                "deficit_reduction": best_score[0],
                "new_gate_metrics": best_score[1],
                "newly_resolved_schedule_rows": best_score[2],
                "h5_gate_dates": current.gate_dates[0],
                "h10_gate_dates": current.gate_dates[1],
                "consensus_gate_dates": current.gate_dates[2],
                "total_deficit_units": current.total_deficit,
            }
        )
    return selected, trace


def reverse_prune(engine: ImpactEngine, selection_order: list[str]) -> tuple[list[str], list[str]]:
    selected = set(selection_order)
    removed: list[str] = []
    for event_id in reversed(selection_order):
        candidate = selected - {event_id}
        if engine.evaluate(candidate).all_pass:
            selected = candidate
            removed.append(event_id)
    final = [event_id for event_id in selection_order if event_id in selected]
    if not engine.evaluate(final).all_pass:
        raise RuntimeError("PRUNED_SUBSET_NO_LONGER_CLEARS_GATE")
    for event_id in final:
        if engine.evaluate(set(final) - {event_id}).all_pass:
            raise RuntimeError("PRUNED_SUBSET_NOT_INCLUSION_MINIMAL")
    return final, removed


def exact_minimum_if_bounded(
    engine: ImpactEngine,
    critical: tuple[str, ...],
) -> tuple[list[str] | None, str, int]:
    if len(critical) > EXACT_SEARCH_MAX_CRITICAL_EVENTS:
        return None, "NOT_RUN_CRITICAL_UNIVERSE_ABOVE_EXACT_BOUND", 0
    evaluations = 0
    ordered = tuple(sorted(critical))
    for size in range(len(ordered) + 1):
        for combo in combinations(ordered, size):
            evaluations += 1
            if engine.evaluate(combo).all_pass:
                return list(combo), "GLOBAL_MINIMUM_CARDINALITY_PROVEN_WITHIN_FULL_CRITICAL_UNIVERSE", evaluations
    raise RuntimeError("EXACT_SEARCH_FOUND_NO_FEASIBLE_SUBSET_DESPITE_SCHEDULE_ONLY_PASS")


def per_date_table(engine: ImpactEngine, selected: Iterable[str]) -> pd.DataFrame:
    result = engine.evaluate(selected)
    return pd.DataFrame(
        {
            "date": [date.date().isoformat() for date in engine.dates],
            "h5_decision_rows": engine.h5_decision,
            "h5_resolved_rows": result.h5_resolved,
            "h5_rate": result.h5_rate,
            "h5_gate": result.h5_gate,
            "h10_decision_rows": engine.h10_decision,
            "h10_resolved_rows": result.h10_resolved,
            "h10_rate": result.h10_rate,
            "h10_gate": result.h10_gate,
            "consensus_resolved_rows": result.consensus_resolved,
            "consensus_rate": result.consensus_rate,
            "consensus_gate": result.consensus_gate,
        }
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--continuity-ledger", type=Path, required=True)
    parser.add_argument("--schedule-evidence-needs", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")

    frame, needs, engine, input_hashes = validate_inputs(
        args.continuity_ledger, args.schedule_evidence_needs
    )
    baseline = engine.evaluate(())
    schedule_only = engine.evaluate(engine.event_ids)
    critical = critical_event_ids(engine, baseline)
    impacts = event_impact_table(engine, needs, baseline)
    greedy, greedy_trace = greedy_gate_clearing_subset(engine, critical)
    pruned, pruned_removed = reverse_prune(engine, greedy)
    exact, exact_status, exact_evaluations = exact_minimum_if_bounded(engine, critical)

    if exact is not None:
        selected = exact
        selected_basis = "GLOBAL_MINIMUM_CARDINALITY_PROVEN"
    else:
        selected = pruned
        selected_basis = "DETERMINISTIC_INCLUSION_MINIMAL_NOT_GLOBAL_CARDINALITY_PROVEN"
    selected_result = engine.evaluate(selected)
    if not selected_result.all_pass:
        raise RuntimeError("FINAL_SELECTED_SUBSET_DOES_NOT_CLEAR_GATE")

    meta = needs.set_index("event_id", drop=False)
    selected_rows = []
    for priority, event_id in enumerate(selected, start=1):
        row = meta.loc[event_id]
        impact = impacts.loc[impacts["event_id"].eq(event_id)].iloc[0]
        selected_rows.append(
            {
                "priority": priority,
                "event_id": event_id,
                "ticker": row["ticker"],
                "source_type": row["source_type"],
                "family": row["family"],
                "reason": row["reason"],
                "source_dates": row["source_dates"],
                "blocking_rows": int(impact["blocking_rows"]),
                "affected_baseline_failing_dates": int(impact["affected_baseline_failing_dates"]),
                "single_event_deficit_reduction": int(impact["single_event_deficit_reduction"]),
            }
        )
    selected_table = pd.DataFrame(selected_rows)
    selected_per_date = per_date_table(engine, selected)
    greedy_trace_frame = pd.DataFrame(greedy_trace)

    # All computation and consistency checks complete before consuming the fresh
    # output-root identity.
    args.output_dir.mkdir(parents=True)
    impact_path = args.output_dir / "schedule_event_impact.csv"
    selected_path = args.output_dir / "selected_schedule_event_subset.csv"
    per_date_path = args.output_dir / "selected_subset_per_date.csv"
    trace_path = args.output_dir / "greedy_selection_trace.csv"
    summary_path = args.output_dir / "summary.json"
    manifest_path = args.output_dir / "MANIFEST.json"
    impacts.to_csv(impact_path, index=False, lineterminator="\n")
    selected_table.to_csv(selected_path, index=False, lineterminator="\n")
    selected_per_date.to_csv(per_date_path, index=False, lineterminator="\n")
    greedy_trace_frame.to_csv(trace_path, index=False, lineterminator="\n")

    zero_blocking = impacts.loc[impacts["blocking_rows"].eq(0), "event_id"].tolist()
    summary = {
        "schema_version": "v4_ca_schedule_event_impact_attribution_v1",
        "status": "V4_CA_SCHEDULE_EVENT_IMPACT_ATTRIBUTION_COMPLETE",
        "diagnostic_only": True,
        "optimistic_counterfactual": True,
        "outcome_blind": True,
        "provider_calls": False,
        "target_or_rank_materialized": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "gate_rate": GATE_RATE,
        "input_hashes": input_hashes,
        "schedule_event_count": len(engine.event_ids),
        "critical_event_count": len(critical),
        "critical_event_ids": list(critical),
        "zero_blocking_row_event_ids": zero_blocking,
        "baseline": result_summary(baseline),
        "schedule_only_ceiling": result_summary(schedule_only),
        "greedy_selection_order": greedy,
        "greedy_selection_count": len(greedy),
        "reverse_pruned_event_ids": pruned_removed,
        "inclusion_minimal_subset": pruned,
        "inclusion_minimal_subset_count": len(pruned),
        "exact_search_status": exact_status,
        "exact_search_evaluations": exact_evaluations,
        "exact_minimum_subset": exact,
        "selected_subset_basis": selected_basis,
        "selected_subset": selected,
        "selected_subset_count": len(selected),
        "selected_subset_result": result_summary(selected_result),
        "known_mechanical_crossing_rows_never_waived": EXPECTED_REASON_COUNTS[REASON_KNOWN_CROSSING],
        "remaining_ksei_coverage_rows_untouched": EXPECTED_REASON_COUNTS["KSEI_REGISTERED_SECURITY_HISTORY_NOT_CERTIFIED"],
        "cross_source_rows_untouched": EXPECTED_REASON_COUNTS["CROSS_SOURCE_CANDIDATE_NOT_REPRESENTED_IN_KSEI_HISTORY"],
        "continuity_certified": False,
        "acquisition_authorized": False,
    }
    summary["output_hashes"] = {
        "schedule_event_impact": sha256(impact_path),
        "selected_schedule_event_subset": sha256(selected_path),
        "selected_subset_per_date": sha256(per_date_path),
        "greedy_selection_trace": sha256(trace_path),
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "v4_ca_schedule_event_impact_attribution_manifest_v1",
        "status": summary["status"],
        "input_hashes": input_hashes,
        "summary_sha256": sha256(summary_path),
        "output_hashes": summary["output_hashes"],
        "outcome_blind": True,
        "provider_calls": False,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": summary["status"],
                "selected_subset_basis": selected_basis,
                "critical_event_count": len(critical),
                "greedy_selection_count": len(greedy),
                "selected_subset_count": len(selected),
                "selected_subset": selected,
                "selected_subset_result": summary["selected_subset_result"],
                "exact_search_status": exact_status,
                "manifest_sha256": sha256(manifest_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
