"""Outcome-blind V4 CA event-window continuity support census.

The runner consumes the immutable blocked V4 continuity ledger and immutable
610-ticker KSEI history census.  It does not load returns, targets, model
artifacts, predictions, or performance.  With no schedule-evidence file it
runs the frozen static-exact tier and emits the exact set of events that still
require official KSEI schedule evidence.
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

from idx_trade.v4_ca_event_windows import (
    RESOLVED,
    classify_event,
    event_relevant_to_study_period,
    window_continuity,
)


PINNED = {
    "continuity_ledger": "52ce3f172e126363b6c51b57fbcaf5551a4e2b0217f120e4b01e6ae0d75497eb",
    "prior_event_evidence": "4c9973781a3c254ad5c82d66d7f6f27afc3bc977681015236693b96d7be638b7",
    "official_calendar": "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a",
    "ksei_manifest": "7cc3ac4d409c3e15c6aa566b63bedab4268562fd4914d1af198ab29657dba25",
    "ksei_summary": "a046637fbcff69cbc42c09e4cac30d9181b2ce93a3cf7297a9a01cfc23a2f422",
    "ksei_coverage": "bb5414125862411e5d3ee760f8e7415b8418803c71d1cc1ef26fb0c55397bc70",
    "ksei_history": "3ea2f0a160300dd4d74c40281dbcbf680e03accc565487cf00b190630471c08d",
}
EXPECTED_ROWS = 344_790
EXPECTED_TICKERS = 610
EXPECTED_DATES = 600
GATE_RATE = 0.90
SELECTION_HALO_DAYS = 60


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


def normalize_date(values: pd.Series, label: str) -> pd.Series:
    result = pd.to_datetime(values, errors="coerce")
    if result.isna().any():
        raise RuntimeError(f"INVALID_DATE_COLUMN:{label}")
    return result.dt.tz_localize(None).dt.normalize()


def normalize_ticker(values: pd.Series) -> pd.Series:
    return (
        values.astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def read_inputs(args: argparse.Namespace) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, str],
]:
    hashes = {
        "continuity_ledger": verify_hash(
            args.continuity_ledger, PINNED["continuity_ledger"], "continuity_ledger"
        ),
        "prior_event_evidence": verify_hash(
            args.prior_event_evidence,
            PINNED["prior_event_evidence"],
            "prior_event_evidence",
        ),
        "official_calendar": verify_hash(
            args.official_calendar, PINNED["official_calendar"], "official_calendar"
        ),
        "ksei_manifest": verify_hash(
            args.ksei_census_root / "MANIFEST.json",
            PINNED["ksei_manifest"],
            "ksei_manifest",
        ),
        "ksei_summary": verify_hash(
            args.ksei_census_root / "summary.json",
            PINNED["ksei_summary"],
            "ksei_summary",
        ),
        "ksei_coverage": verify_hash(
            args.ksei_census_root / "ticker_coverage.csv",
            PINNED["ksei_coverage"],
            "ksei_coverage",
        ),
        "ksei_history": verify_hash(
            args.ksei_census_root / "ksei_ca_history.jsonl",
            PINNED["ksei_history"],
            "ksei_history",
        ),
    }

    ledger = pd.read_csv(args.continuity_ledger)
    if len(ledger) != EXPECTED_ROWS:
        raise RuntimeError(f"CONTINUITY_LEDGER_ROW_COUNT_CHANGED:{len(ledger)}")
    ledger["ticker"] = normalize_ticker(ledger["ticker"])
    for column in ("signal_date", "entry_date", "terminal_date"):
        ledger[column] = normalize_date(ledger[column], column)
    ledger["horizon"] = pd.to_numeric(ledger["horizon"], errors="raise").astype(int)
    if ledger["ticker"].nunique() != EXPECTED_TICKERS:
        raise RuntimeError("CONTINUITY_LEDGER_TICKER_COUNT_CHANGED")
    if ledger["signal_date"].nunique() != EXPECTED_DATES:
        raise RuntimeError("CONTINUITY_LEDGER_DATE_COUNT_CHANGED")
    if set(ledger["horizon"].unique()) != {5, 10}:
        raise RuntimeError("CONTINUITY_LEDGER_HORIZON_SET_CHANGED")
    if ledger.duplicated(["ticker", "signal_date", "horizon"]).any():
        raise RuntimeError("CONTINUITY_LEDGER_DUPLICATE_IDENTITY")

    prior = pd.read_csv(args.prior_event_evidence)
    prior["ticker"] = normalize_ticker(prior["ticker"])
    prior["candidate_date"] = normalize_date(prior["candidate_date"], "candidate_date")

    calendar = pd.read_csv(args.official_calendar)
    if "date" not in calendar.columns:
        raise RuntimeError("OFFICIAL_CALENDAR_DATE_COLUMN_MISSING")
    calendar["date"] = normalize_date(calendar["date"], "calendar.date")
    if calendar["date"].duplicated().any():
        raise RuntimeError("OFFICIAL_CALENDAR_DUPLICATE_DATE")
    calendar = calendar.sort_values("date", kind="mergesort").reset_index(drop=True)

    coverage = pd.read_csv(args.ksei_census_root / "ticker_coverage.csv")
    coverage["ticker"] = normalize_ticker(coverage["ticker"])
    coverage["coverage_certified"] = (
        coverage["coverage_certified"]
        .astype(str)
        .str.casefold()
        .map({"true": True, "false": False})
    )
    if coverage["coverage_certified"].isna().any():
        raise RuntimeError("KSEI_COVERAGE_BOOLEAN_INVALID")
    if coverage["ticker"].duplicated().any() or len(coverage) != EXPECTED_TICKERS:
        raise RuntimeError("KSEI_COVERAGE_TICKER_IDENTITY_INVALID")

    history = read_jsonl(args.ksei_census_root / "ksei_ca_history.jsonl")
    history_tickers = {str(row.get("ticker", "")).upper().strip() for row in history}
    if not history_tickers.issubset(set(ledger["ticker"])):
        raise RuntimeError("KSEI_HISTORY_OUT_OF_SCOPE_TICKER")

    schedule: list[dict[str, Any]] = []
    if args.schedule_evidence is not None:
        if not args.schedule_evidence.is_file():
            raise RuntimeError(f"SCHEDULE_EVIDENCE_MISSING:{args.schedule_evidence}")
        hashes["schedule_evidence"] = sha256(args.schedule_evidence)
        if args.schedule_evidence.suffix.lower() == ".jsonl":
            schedule = read_jsonl(args.schedule_evidence)
        else:
            schedule = pd.read_csv(args.schedule_evidence).to_dict("records")

    return ledger, prior, calendar, coverage, history, schedule, hashes


def prior_candidate_tickers(
    prior: pd.DataFrame,
    *,
    period_start: pd.Timestamp,
    period_end: pd.Timestamp,
) -> set[str]:
    start = period_start - pd.Timedelta(days=SELECTION_HALO_DAYS)
    end = period_end + pd.Timedelta(days=SELECTION_HALO_DAYS)
    mask = prior["candidate_date"].between(start, end, inclusive="both")
    return set(prior.loc[mask, "ticker"])


def build_events(
    history: list[dict[str, Any]],
    *,
    official_sessions: list[pd.Timestamp],
    schedule: list[dict[str, Any]],
    period_start: pd.Timestamp,
    period_end: pd.Timestamp,
) -> tuple[dict[str, list[Any]], pd.DataFrame]:
    by_ticker: dict[str, list[Any]] = {}
    audit_rows: list[dict[str, Any]] = []
    for row in history:
        event = classify_event(
            row,
            official_sessions=official_sessions,
            schedule_evidence=schedule,
        )
        if not event_relevant_to_study_period(
            event,
            period_start=period_start,
            period_end=period_end,
            selection_halo_calendar_days=SELECTION_HALO_DAYS,
        ):
            continue
        by_ticker.setdefault(event.ticker, []).append(event)
        audit_rows.append(
            {
                "event_id": event.event_id,
                "ticker": event.ticker,
                "source_type": event.source_type,
                "family": event.family,
                "semantic_class": event.semantic_class,
                "transition_date": (
                    event.transition_date.date().isoformat()
                    if event.transition_date is not None
                    else ""
                ),
                "transition_source": event.transition_source or "",
                "reason": event.reason,
                "source_dates": "|".join(
                    value.date().isoformat() for value in event.source_dates
                ),
            }
        )
    audit = pd.DataFrame(audit_rows)
    if audit.empty:
        audit = pd.DataFrame(
            columns=[
                "event_id",
                "ticker",
                "source_type",
                "family",
                "semantic_class",
                "transition_date",
                "transition_source",
                "reason",
                "source_dates",
            ]
        )
    return by_ticker, audit.sort_values(
        ["ticker", "source_dates", "source_type", "event_id"], kind="mergesort"
    ).reset_index(drop=True)


def build_window_ledger(
    ledger: pd.DataFrame,
    coverage: pd.DataFrame,
    events_by_ticker: dict[str, list[Any]],
    cross_source_conflicts: set[str],
) -> pd.DataFrame:
    coverage_map = dict(zip(coverage["ticker"], coverage["coverage_certified"]))
    rows: list[dict[str, Any]] = []
    for row in ledger.itertuples(index=False):
        result = window_continuity(
            coverage_certified=bool(coverage_map[str(row.ticker)]),
            cross_source_conflict=str(row.ticker) in cross_source_conflicts,
            events=events_by_ticker.get(str(row.ticker), []),
            entry_date=row.entry_date,
            terminal_date=row.terminal_date,
        )
        rows.append(
            {
                "ticker": str(row.ticker),
                "signal_date": row.signal_date,
                "horizon": int(row.horizon),
                "entry_date": row.entry_date,
                "terminal_date": row.terminal_date,
                "continuity_status": result.status,
                "continuity_reason": result.reason,
                "blocking_event_ids": "|".join(result.blocking_event_ids),
                "blocking_transition_dates": "|".join(
                    result.blocking_transition_dates
                ),
                "policy_id": "V4_CA_EVENT_WINDOW_SEMANTICS_V1",
            }
        )
    result = pd.DataFrame(rows)
    if len(result) != EXPECTED_ROWS:
        raise RuntimeError("WINDOW_LEDGER_ROW_COUNT_CHANGED")
    return result


def build_per_date(window_ledger: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for date, block in window_ledger.groupby("signal_date", sort=True):
        output: dict[str, Any] = {"date": date}
        resolved_sets: dict[int, set[str]] = {}
        for horizon in (5, 10):
            sub = block[block["horizon"].eq(horizon)]
            resolved = sub[sub["continuity_status"].eq(RESOLVED)]
            rate = len(resolved) / len(sub) if len(sub) else np.nan
            output[f"h{horizon}_decision_rows"] = int(len(sub))
            output[f"h{horizon}_resolved_rows"] = int(len(resolved))
            output[f"h{horizon}_rate"] = rate
            output[f"h{horizon}_gate"] = bool(len(sub) and rate >= GATE_RATE)
            resolved_sets[horizon] = set(resolved["ticker"])
        base = block[block["horizon"].eq(5)]
        consensus = resolved_sets[5] & resolved_sets[10]
        consensus_rate = len(consensus) / len(base) if len(base) else np.nan
        output["consensus_resolved_rows"] = len(consensus)
        output["consensus_rate"] = consensus_rate
        output["consensus_gate"] = bool(len(base) and consensus_rate >= GATE_RATE)
        rows.append(output)
    result = pd.DataFrame(rows).sort_values("date", kind="mergesort").reset_index(drop=True)
    if len(result) != EXPECTED_DATES:
        raise RuntimeError("PER_DATE_COUNT_CHANGED")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--continuity-ledger", type=Path, required=True)
    parser.add_argument("--prior-event-evidence", type=Path, required=True)
    parser.add_argument("--official-calendar", type=Path, required=True)
    parser.add_argument("--ksei-census-root", type=Path, required=True)
    parser.add_argument("--schedule-evidence", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    args.output_dir.mkdir(parents=True)

    ledger, prior, calendar, coverage, history, schedule, input_hashes = read_inputs(args)
    period_start = ledger["entry_date"].min()
    period_end = ledger["terminal_date"].max()
    prior_tickers = prior_candidate_tickers(
        prior, period_start=period_start, period_end=period_end
    )
    events_by_ticker, event_audit = build_events(
        history,
        official_sessions=calendar["date"].tolist(),
        schedule=schedule,
        period_start=period_start,
        period_end=period_end,
    )

    # Preserve the V2 fail-closed cross-source disagreement rule.  A prior
    # candidate conflicts only when KSEI has no mechanically relevant event in
    # the broad study period after semantic decomposition.
    represented = {
        ticker
        for ticker, events in events_by_ticker.items()
        if any(event.semantic_class != "NON_BLOCKING" for event in events)
    }
    cross_source_conflicts = prior_tickers - represented

    window_ledger = build_window_ledger(
        ledger, coverage, events_by_ticker, cross_source_conflicts
    )
    per_date = build_per_date(window_ledger)
    schedule_needs = event_audit[event_audit["semantic_class"].eq("SCHEDULE_REQUIRED")].copy()

    verdict = (
        "V4_CA_EVENT_WINDOW_CONTINUITY_CERTIFIED"
        if bool(per_date["h5_gate"].all() and per_date["h10_gate"].all() and per_date["consensus_gate"].all())
        else "V4_CA_EVENT_WINDOW_CONTINUITY_STILL_BLOCKED"
    )

    event_path = args.output_dir / "event_semantics_audit.csv"
    needs_path = args.output_dir / "schedule_evidence_needs.csv"
    ledger_path = args.output_dir / "v4_frozen_continuity_ledger_event_window.csv"
    per_date_path = args.output_dir / "v4_frozen_continuity_per_date_event_window.csv"
    event_audit.to_csv(event_path, index=False, lineterminator="\n")
    schedule_needs.to_csv(needs_path, index=False, lineterminator="\n")
    window_ledger.to_csv(ledger_path, index=False, lineterminator="\n")
    per_date.to_csv(per_date_path, index=False, lineterminator="\n")

    status_counts = Counter(window_ledger["continuity_status"])
    reason_counts = Counter(window_ledger["continuity_reason"])
    semantic_counts = Counter(event_audit["semantic_class"])
    summary = {
        "schema_version": "v4_ca_event_window_support_v1",
        "verdict": verdict,
        "corporate_action_continuity_certified": verdict.endswith("CERTIFIED"),
        "outcome_blind": True,
        "provider_calls": False,
        "target_or_rank_materialized": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "frozen_rows": int(len(window_ledger)),
        "frozen_tickers": int(window_ledger["ticker"].nunique()),
        "frozen_dates": int(window_ledger["signal_date"].nunique()),
        "coverage_certified_tickers": int(coverage["coverage_certified"].sum()),
        "coverage_unresolved_tickers": int((~coverage["coverage_certified"]).sum()),
        "cross_source_conflict_tickers": sorted(cross_source_conflicts),
        "event_rows_relevant_to_study": int(len(event_audit)),
        "event_semantic_counts": dict(sorted(semantic_counts.items())),
        "schedule_required_events": int(len(schedule_needs)),
        "schedule_required_tickers": int(schedule_needs["ticker"].nunique()) if len(schedule_needs) else 0,
        "continuity_status_counts": dict(sorted(status_counts.items())),
        "continuity_reason_counts": dict(sorted(reason_counts.items())),
        "per_date": {
            "h5_gate_dates": int(per_date["h5_gate"].sum()),
            "h10_gate_dates": int(per_date["h10_gate"].sum()),
            "consensus_gate_dates": int(per_date["consensus_gate"].sum()),
            "h5_min_rate": float(per_date["h5_rate"].min()),
            "h10_min_rate": float(per_date["h10_rate"].min()),
            "consensus_min_rate": float(per_date["consensus_rate"].min()),
        },
        "policy": {
            "gate_rate": GATE_RATE,
            "selection_halo_calendar_days": SELECTION_HALO_DAYS,
            "static_cum_next_official_session": True,
            "price_inference": False,
            "missing_exact_schedule_fails_closed": True,
            "entry_on_transition_is_post_event_basis": True,
        },
        "input_hashes": input_hashes,
        "output_hashes": {},
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary["output_hashes"] = {
        "event_semantics_audit": sha256(event_path),
        "schedule_evidence_needs": sha256(needs_path),
        "continuity_ledger": sha256(ledger_path),
        "per_date": sha256(per_date_path),
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "v4_ca_event_window_support_manifest_v1",
        "status": verdict,
        "outcome_blind": True,
        "summary_sha256": sha256(summary_path),
        "input_hashes": input_hashes,
        "output_hashes": summary["output_hashes"],
    }
    manifest_path = args.output_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
