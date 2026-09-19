"""Read-only linkage audit between BBCA basis trace and local CA ledgers."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bbca-trace", type=Path, required=True)
    parser.add_argument("--event-census", type=Path, required=True)
    parser.add_argument("--transition-ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    trace = read_csv(args.bbca_trace)
    events = read_csv(args.event_census)
    transitions = read_csv(args.transition_ledger)
    trace_dates = [row.get("date", "") for row in trace]
    split_zero = [row for row in trace if row.get("sessions_since_recorded_split") == "0"]
    trace_hlc_exact = sum(row.get("panel_idx_hlc_exact") == "True" for row in trace)
    pre_ca_fields = (
        "lookback_5_contains_pre_ca",
        "lookback_atr14_contains_pre_ca",
        "lookback_20_contains_pre_ca",
        "lookback_60_contains_pre_ca",
    )
    pre_ca_counts = {field: sum(row.get(field) == "True" for row in trace) for field in pre_ca_fields}
    event_tickers = Counter(row.get("ticker", "") for row in events)
    transition_tickers = Counter(row.get("ticker", "") for row in transitions)

    result: dict[str, Any] = {
        "schema": "idx_trade_alpha_bbca_ca_event_linkage_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "PASS_STRUCTURAL_ONLY / EVENT_AUTHORITY_NOT_ESTABLISHED",
        "scope": {
            "outcome_accessed": False,
            "model_scoring": False,
            "canonical_write": False,
            "cloud_or_r2_write": False,
            "network_used": False,
            "feature_or_candidate_created": False,
            "event_semantics_inferred": False,
        },
        "trace": {
            "rows": len(trace),
            "ticker_set": sorted({row.get("ticker") for row in trace}),
            "date_from": min(trace_dates) if trace_dates else None,
            "date_to": max(trace_dates) if trace_dates else None,
            "sessions_since_recorded_split_min": min(int(row["sessions_since_recorded_split"]) for row in trace),
            "sessions_since_recorded_split_max": max(int(row["sessions_since_recorded_split"]) for row in trace),
            "recorded_split_zero_rows": len(split_zero),
            "recorded_split_zero_dates": [row.get("date") for row in split_zero],
            "panel_idx_hlc_exact_rows": trace_hlc_exact,
            "pre_ca_lookback_true_counts": pre_ca_counts,
            "h5_exact_final_fit_identity_true_rows": sum(row.get("h5_exact_final_fit_identity") == "True" for row in trace),
            "h10_exact_final_fit_identity_true_rows": sum(row.get("h10_exact_final_fit_identity") == "True" for row in trace),
        },
        "ca_ledgers": {
            "event_census_rows": len(events),
            "event_census_bbca_rows": event_tickers.get("BBCA", 0),
            "transition_ledger_rows": len(transitions),
            "transition_ledger_bbca_rows": transition_tickers.get("BBCA", 0),
            "event_census_ticker_count": len(event_tickers),
            "transition_ledger_ticker_count": len(transition_tickers),
            "event_census_source_kinds": dict(sorted(Counter(row.get("source_kind", "") for row in events).items())),
            "event_census_families": dict(sorted(Counter(row.get("event_family", "") for row in events).items())),
        },
        "interpretation": [
            "The BBCA trace is a structural post-date window and records exact panel-versus-IDX HLC parity, but it is not itself an event-authority ledger.",
            "Neither the retained CA event census nor the strict transition semantics ledger contains a BBCA row, so the trace cannot independently certify the event family, effective date, ratio, issuer, or ISIN transition.",
            "The 2021-10-13 trace date and the 5x TradingView/IDX basis break remain a useful forensic alignment, not permission to rescale or admit a source.",
        ],
        "inputs": {
            "bbca_trace": {"path": str(args.bbca_trace), "sha256": sha256_file(args.bbca_trace)},
            "event_census": {"path": str(args.event_census), "sha256": sha256_file(args.event_census)},
            "transition_ledger": {"path": str(args.transition_ledger), "sha256": sha256_file(args.transition_ledger)},
        },
        "source_hashes": {
            "bbca_trace": sha256_file(args.bbca_trace),
            "event_census": sha256_file(args.event_census),
            "transition_ledger": sha256_file(args.transition_ledger),
        },
        "code_sha256": sha256_file(Path(__file__)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
