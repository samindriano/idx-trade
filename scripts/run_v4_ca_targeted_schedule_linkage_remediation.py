"""Offline V4 linkage remediation for four unresolved KSEI stock-split events.

The runner consumes the accepted V3 geometry-remediation output plus the exact
raw PDFs from the original targeted acquisition. It does not call providers.

A stock-split event is admitted only when all of the following are true:
- V3 has exactly one candidate document for the event;
- exact ticker and compatible STOCK_SPLIT family are preserved;
- the official PDF contains every frozen source date for that event;
- the stock-split new-basis semantic row plus its immediately following wrapped
  line contain exactly one Regular-Market transition date;
- that transition is an official exchange session.

No Record/Distribution date is used as a transition and no price inference or
source substitution is permitted.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import pandas as pd

import run_v4_ca_targeted_schedule_continuity_replay as replay
import run_v4_ca_targeted_schedule_evidence as targeted
import run_v4_ca_targeted_schedule_parser_remediation as parser_v3
from idx_trade.v4_ca_schedule_semantics import clean
from idx_trade.v4_ca_targeted_schedule_linkage_remediation import (
    explicit_date_set,
    frozen_source_dates_contained,
    two_line_stock_split_transition,
)
from idx_trade.v4_ksei_coverage_gap import sha256_file


EXPECTED_ACQUISITION_MANIFEST_SHA256 = "df1455b80c4b5d76d8bde0c23ac992db81fc93373a9a40af18ca29583b94b79b"
EXPECTED_V3_MANIFEST_SHA256 = "1aee0285c74b47f12da76e1a4d7fccb6b8409a9c87e6d959ee9c9ea73d3c8dfe"
STOCK_SPLIT_TICKERS = frozenset({"CUAN", "ISAT", "PTRO", "RAJA"})
TRANSITION_SEMANTIC = "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prior-remediation-root", type=Path, required=True)
    parser.add_argument("--acquisition-root", type=Path, required=True)
    parser.add_argument("--selected-subset", type=Path, required=True)
    parser.add_argument("--official-calendar", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def _event_by_ticker(selected: pd.DataFrame) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for row in selected.to_dict("records"):
        ticker = clean(row.get("ticker")).upper()
        if ticker in STOCK_SPLIT_TICKERS:
            if ticker in rows:
                raise RuntimeError(f"DUPLICATE_SELECTED_STOCK_SPLIT_TICKER:{ticker}")
            rows[ticker] = row
    if set(rows) != STOCK_SPLIT_TICKERS:
        raise RuntimeError(f"SELECTED_STOCK_SPLIT_SET_CHANGED:{sorted(rows)}")
    return rows


def _source_date_tokens(event: dict[str, Any]) -> list[str]:
    return [token for token in clean(event.get("source_dates")).split("|") if token]


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")

    selected = targeted.validate_selected(args.selected_subset)
    _, official_sessions = targeted.validate_calendar(args.official_calendar)
    events = _event_by_ticker(selected)

    prior_summary, _, prior_manifest_sha = replay.verify_targeted_root(args.prior_remediation_root)
    if prior_manifest_sha != EXPECTED_V3_MANIFEST_SHA256:
        raise RuntimeError(f"V3_MANIFEST_SHA_MISMATCH:{prior_manifest_sha}")

    acquisition_summary, _, acquisition_manifest_sha = replay.verify_targeted_root(args.acquisition_root)
    if acquisition_manifest_sha != EXPECTED_ACQUISITION_MANIFEST_SHA256:
        raise RuntimeError(f"ACQUISITION_MANIFEST_SHA_MISMATCH:{acquisition_manifest_sha}")

    prior_evidence = pd.read_csv(
        args.prior_remediation_root / "targeted_evidence.csv", dtype=str, keep_default_na=False
    )
    prior_linkage = pd.read_csv(
        args.prior_remediation_root / "targeted_event_linkage_audit.csv", dtype=str, keep_default_na=False
    )
    prior_parse = pd.read_csv(
        args.prior_remediation_root / "targeted_schedule_document_parse_audit.csv", dtype=str, keep_default_na=False
    )

    exact_updates: dict[str, dict[str, Any]] = {}
    parse_updates: dict[str, dict[str, Any]] = {}

    linkage_by_ticker = {
        clean(row.get("ticker")).upper(): row for row in prior_linkage.to_dict("records")
    }

    for ticker in sorted(STOCK_SPLIT_TICKERS):
        event = events[ticker]
        linkage = linkage_by_ticker.get(ticker)
        if linkage is None:
            raise RuntimeError(f"V3_LINKAGE_ROW_MISSING:{ticker}")
        if int(clean(linkage.get("candidate_document_count")) or 0) != 1:
            continue
        if clean(linkage.get("linkage_status")) != "NO_EXACT_LINKED_TRANSITION":
            continue

        parse_matches = [
            row
            for row in prior_parse.to_dict("records")
            if clean(row.get("ticker")).upper() == ticker
        ]
        if len(parse_matches) != 1:
            raise RuntimeError(f"V3_PARSE_ROW_COUNT:{ticker}:{len(parse_matches)}")
        prior = parse_matches[0]
        if clean(prior.get("event_family")) != "STOCK_SPLIT":
            continue
        source_sha = clean(prior.get("source_sha256"))
        if not source_sha:
            continue

        raw_path, payload = parser_v3.raw_pdf_by_sha(args.acquisition_root, source_sha)
        layout_text = parser_v3.strict_pdf_layout_text(payload)
        transition, transition_diagnostics = two_line_stock_split_transition(layout_text)
        document_dates = explicit_date_set(layout_text)
        source_dates = _source_date_tokens(event)

        updated_parse = dict(prior)
        updated_parse.update(
            {
                "v4_document_date_set": "|".join(sorted(document_dates)),
                "v4_source_date_set": "|".join(sorted(source_dates)),
                "v4_source_dates_fully_contained": str(
                    frozen_source_dates_contained(source_dates, document_dates)
                ).lower(),
                "v4_raw_relpath": raw_path.relative_to(args.acquisition_root).as_posix(),
                "v4_transition_diagnostics": "|".join(transition_diagnostics),
            }
        )

        admissible = (
            transition is not None
            and transition in official_sessions
            and frozen_source_dates_contained(source_dates, document_dates)
            and clean(prior.get("ticker")).upper() == ticker
            and clean(prior.get("event_family")) == "STOCK_SPLIT"
            and bool(clean(prior.get("reference") or prior.get("ksei_reference")))
            and bool(source_sha)
        )
        if not admissible:
            updated_parse["v4_remediation_status"] = "V4_STOCK_SPLIT_LINKAGE_UNRESOLVED"
            parse_updates[ticker] = updated_parse
            continue

        updated_parse.update(
            {
                "transition_date": transition,
                "transition_semantic": TRANSITION_SEMANTIC,
                "parse_status": "PARSED_EXACT_TRANSITION",
                "diagnostics": "",
                "v4_remediation_status": "V4_TWO_LINE_STOCK_SPLIT_EXACT",
            }
        )
        parse_updates[ticker] = updated_parse
        exact_updates[ticker] = {
            "event_id": clean(event["event_id"]),
            "ticker": ticker,
            "event_source_type": clean(event["source_type"]),
            "linkage_status": "EXACT",
            "evidence_kind": "EXACT_TRANSITION",
            "transition_semantic": TRANSITION_SEMANTIC,
            "transition_date": transition,
            "ksei_reference": clean(prior.get("ksei_reference") or prior.get("reference")),
            "document_date": clean(prior.get("document_date")),
            "source_url": clean(prior.get("source_url") or prior.get("document_url")),
            "source_sha256": source_sha,
            "linkage_basis": "UNIQUE_CANDIDATE_EXACT_TICKER_STOCK_SPLIT_FULL_FROZEN_SOURCE_DATE_SET_AND_EXPLICIT_TWO_LINE_REGULAR_MARKET_TRANSITION",
            "ratio_raw": "",
            "ratio_left_security": "",
            "ratio_right_security": "",
            "identity_date": "",
            "diagnostics": "",
        }

    evidence_rows = prior_evidence.to_dict("records")
    existing_event_ids = {clean(row.get("event_id")) for row in evidence_rows}
    for ticker, row in exact_updates.items():
        if clean(row["event_id"]) in existing_event_ids:
            raise RuntimeError(f"V4_EVENT_ALREADY_RESOLVED_IN_PRIOR:{ticker}")
        evidence_rows.append(row)

    linkage_rows: list[dict[str, Any]] = []
    for row in prior_linkage.to_dict("records"):
        ticker = clean(row.get("ticker")).upper()
        if ticker in exact_updates:
            updated = dict(row)
            updated["transition_dates"] = exact_updates[ticker]["transition_date"]
            updated["linkage_status"] = "EXACT"
            updated["diagnostics"] = ""
            linkage_rows.append(updated)
        else:
            linkage_rows.append(row)

    parse_rows: list[dict[str, Any]] = []
    for row in prior_parse.to_dict("records"):
        ticker = clean(row.get("ticker")).upper()
        parse_rows.append(parse_updates.get(ticker, row))

    evidence_columns = [
        "event_id", "ticker", "event_source_type", "linkage_status", "evidence_kind",
        "transition_semantic", "transition_date", "ksei_reference", "document_date",
        "source_url", "source_sha256", "linkage_basis", "ratio_raw",
        "ratio_left_security", "ratio_right_security", "identity_date", "diagnostics",
    ]
    evidence = pd.DataFrame(evidence_rows)[evidence_columns].fillna("")
    evidence = evidence.drop_duplicates().sort_values(
        ["ticker", "event_id", "transition_date", "ksei_reference"], kind="mergesort"
    ).reset_index(drop=True)
    linkage_frame = pd.DataFrame(linkage_rows).fillna("").sort_values(
        ["ticker", "event_id"], kind="mergesort"
    ).reset_index(drop=True)
    parse_frame = pd.DataFrame(parse_rows).fillna("")

    args.output_dir.mkdir(parents=True)
    evidence_path = args.output_dir / "targeted_evidence.csv"
    linkage_path = args.output_dir / "targeted_event_linkage_audit.csv"
    parse_path = args.output_dir / "targeted_schedule_document_parse_audit.csv"
    requests_path = args.output_dir / "request_records.jsonl"
    evidence.to_csv(evidence_path, index=False, lineterminator="\n")
    linkage_frame.to_csv(linkage_path, index=False, lineterminator="\n")
    parse_frame.to_csv(parse_path, index=False, lineterminator="\n")
    shutil.copyfile(args.prior_remediation_root / "request_records.jsonl", requests_path)

    exact_static = int(
        linkage_frame["linkage_status"].eq("EXACT_NON_BLOCKING_STATIC_SECURITY_TO_CURRENCY").sum()
    )
    exact_schedule = int(linkage_frame["linkage_status"].eq("EXACT").sum())
    unresolved = 7 - exact_static - exact_schedule

    summary = dict(prior_summary)
    summary.update(
        {
            "exact_static_nonblocking_events": exact_static,
            "exact_schedule_transition_events": exact_schedule,
            "unresolved_selected_events": unresolved,
            "resolved_event_ids": sorted(set(evidence["event_id"])),
            "unresolved_event_ids": sorted(
                set(targeted.EXPECTED_SELECTED) - set(evidence["event_id"])
            ),
            "provider_calls": True,
            "provider_calls_in_remediation": False,
            "parent_targeted_manifest_sha256": prior_manifest_sha,
            "acquisition_manifest_sha256": acquisition_manifest_sha,
            "input_hashes": {
                **(prior_summary.get("input_hashes") or {}),
                "parent_targeted_manifest": prior_manifest_sha,
                "acquisition_manifest": acquisition_manifest_sha,
            },
            "policy": {
                **(prior_summary.get("policy") or {}),
                "offline_two_line_stock_split_linkage_remediation": True,
                "unique_candidate_required_for_two_line_stock_split": True,
                "full_frozen_source_date_set_containment_required": True,
                "provider_calls_in_remediation": False,
                "record_distribution_transition_fallback": False,
                "price_inference": False,
                "source_substitution": False,
            },
        }
    )
    summary["output_hashes"] = {
        "targeted_evidence": sha256_file(evidence_path),
        "targeted_event_linkage_audit": sha256_file(linkage_path),
        "targeted_schedule_document_parse_audit": sha256_file(parse_path),
        "request_records": sha256_file(requests_path),
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest = {
        "schema_version": "v4_ca_targeted_schedule_evidence_manifest_v1",
        "status": summary["status"],
        "outcome_blind": True,
        "provider_calls": True,
        "provider_calls_in_remediation": False,
        "parent_targeted_manifest_sha256": prior_manifest_sha,
        "acquisition_manifest_sha256": acquisition_manifest_sha,
        "input_hashes": summary["input_hashes"],
        "summary_sha256": sha256_file(summary_path),
        "output_hashes": summary["output_hashes"],
    }
    manifest_path = args.output_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                **summary,
                "v4_two_line_exact_tickers": sorted(exact_updates),
                "manifest_sha256": sha256_file(manifest_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
