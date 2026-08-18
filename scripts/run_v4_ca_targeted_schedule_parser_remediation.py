"""Offline parser remediation for the frozen seven-event V4 CA evidence bundle.

No provider call is permitted here. The runner reuses the exact raw PDF bytes
already captured by ``run_v4_ca_targeted_schedule_evidence.py``, performs a
layout-preserving pypdf extraction, applies strict row/date remediation, and
writes a new evidence root compatible with the existing continuity replay.

Record/Distribution dates remain linkage-only. Price inference and source
substitution remain prohibited.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from io import BytesIO
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
from pypdf import PdfReader

import run_v4_ca_schedule_acquisition as base
import run_v4_ca_targeted_schedule_continuity_replay as replay
import run_v4_ca_targeted_schedule_evidence as targeted
from idx_trade.v4_ca_event_windows import ACCEPTED_SCHEDULE_SEMANTICS
from idx_trade.v4_ca_schedule_semantics import clean, parse_ksei_schedule_transition
from idx_trade.v4_ca_targeted_schedule_evidence import NISP_EVENT_ID
from idx_trade.v4_ca_targeted_schedule_parser_remediation import repair_layout_parse
from idx_trade.v4_ksei_coverage_gap import sha256_file


EXPECTED_PARENT_MANIFEST_SHA256 = "df1455b80c4b5d76d8bde0c23ac992db81fc93373a9a40af18ca29583b94b79b"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prior-targeted-root", type=Path, required=True)
    parser.add_argument("--selected-subset", type=Path, required=True)
    parser.add_argument("--official-calendar", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def strict_pdf_layout_text(payload: bytes) -> str:
    reader = PdfReader(BytesIO(payload))
    pages: list[str] = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text(extraction_mode="layout") or "")
        except TypeError as exc:
            raise RuntimeError("PYPDF_LAYOUT_EXTRACTION_REQUIRED") from exc
    text = "\n".join(pages)
    if not clean(text):
        raise RuntimeError("PYPDF_LAYOUT_EXTRACTION_EMPTY")
    return text


def verify_parent_outputs(root: Path, summary: dict[str, Any]) -> None:
    outputs = summary.get("output_hashes") or {}
    required = {
        "targeted_evidence": root / "targeted_evidence.csv",
        "targeted_event_linkage_audit": root / "targeted_event_linkage_audit.csv",
        "targeted_schedule_document_parse_audit": root / "targeted_schedule_document_parse_audit.csv",
        "request_records": root / "request_records.jsonl",
    }
    for key, path in required.items():
        if not path.is_file():
            raise RuntimeError(f"PARENT_REQUIRED_FILE_MISSING:{path}")
        expected = clean(outputs.get(key))
        actual = sha256_file(path)
        if not expected or actual != expected:
            raise RuntimeError(f"PARENT_OUTPUT_HASH_MISMATCH:{key}:{actual}")


def raw_pdf_by_sha(root: Path, expected_sha: str) -> tuple[Path, bytes]:
    raw_root = root / "raw" / "documents"
    if not raw_root.is_dir():
        raise RuntimeError(f"PARENT_RAW_DOCUMENT_ROOT_MISSING:{raw_root}")
    matches: list[tuple[Path, bytes]] = []
    for path in sorted(raw_root.rglob("*.pdf")):
        if sha256_file(path) == expected_sha:
            matches.append((path, path.read_bytes()))
    if len(matches) != 1:
        raise RuntimeError(f"RAW_DOCUMENT_SHA_MATCH_COUNT:{expected_sha}:{len(matches)}")
    return matches[0]


def candidate_belongs_to_ticker(row: dict[str, Any], ticker: str) -> bool:
    if clean(row.get("ticker")).upper() == ticker:
        return True
    subject = clean(row.get("subject"))
    return bool(subject and base.ticker_in_subject(ticker, subject))


def build_mechanical_evidence(
    selected: pd.DataFrame,
    parsed_documents: list[dict[str, Any]],
    official_sessions: set[str],
    prior_linkage: pd.DataFrame,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    evidence_rows: list[dict[str, Any]] = []
    linkage_rows: list[dict[str, Any]] = []
    prior_counts = {
        clean(row["event_id"]): int(clean(row.get("candidate_document_count")) or 0)
        for row in prior_linkage.to_dict("records")
    }
    mechanical = selected[selected["event_id"].isin(targeted.MECHANICAL_IDS)].copy()

    for event in mechanical.to_dict("records"):
        event_id = clean(event["event_id"])
        ticker = clean(event["ticker"]).upper()
        candidates: list[dict[str, Any]] = []
        for row in parsed_documents:
            if not candidate_belongs_to_ticker(row, ticker):
                continue
            if clean(row.get("parse_status")) != "PARSED_EXACT_TRANSITION":
                continue
            if clean(row.get("ticker")).upper() != ticker:
                continue
            if not base.compatible_family(clean(event["source_type"]), clean(row.get("event_family"))):
                continue
            if not targeted.exact_source_date_link(event, row):
                continue
            transition = clean(row.get("transition_date"))
            semantic = clean(row.get("transition_semantic"))
            if transition not in official_sessions or semantic not in ACCEPTED_SCHEDULE_SEMANTICS:
                continue
            if not clean(row.get("source_sha256")) or not clean(row.get("ksei_reference") or row.get("reference")):
                continue
            candidates.append(row)

        transitions = {clean(row.get("transition_date")) for row in candidates if clean(row.get("transition_date"))}
        semantics = {clean(row.get("transition_semantic")) for row in candidates if clean(row.get("transition_semantic"))}
        if len(transitions) == 1 and len(semantics) == 1:
            transition = next(iter(transitions))
            semantic = next(iter(semantics))
            exact_rows = [
                row for row in candidates
                if clean(row.get("transition_date")) == transition
                and clean(row.get("transition_semantic")) == semantic
            ]
            for row in exact_rows:
                evidence_rows.append(
                    {
                        "event_id": event_id,
                        "ticker": ticker,
                        "event_source_type": clean(event["source_type"]),
                        "linkage_status": "EXACT",
                        "evidence_kind": "EXACT_TRANSITION",
                        "transition_semantic": semantic,
                        "transition_date": transition,
                        "ksei_reference": clean(row.get("ksei_reference") or row.get("reference")),
                        "document_date": clean(row.get("document_date")),
                        "source_url": clean(row.get("source_url")),
                        "source_sha256": clean(row.get("source_sha256")),
                        "linkage_basis": "EXACT_TICKER_FAMILY_SOURCE_DATE_AND_EXPLICIT_REGULAR_MARKET_TRANSITION_LAYOUT_REPARSE",
                        "ratio_raw": "",
                        "ratio_left_security": "",
                        "ratio_right_security": "",
                        "identity_date": "",
                        "diagnostics": clean(row.get("diagnostics")),
                    }
                )
            status = "EXACT"
        elif len(transitions) > 1 or len(semantics) > 1:
            status = "CONFLICTING_EXACT_TRANSITIONS"
        else:
            status = "NO_EXACT_LINKED_TRANSITION"

        linkage_rows.append(
            {
                "event_id": event_id,
                "ticker": ticker,
                "source_type": clean(event["source_type"]),
                "source_dates": clean(event["source_dates"]),
                "candidate_document_count": prior_counts.get(event_id, 0),
                "transition_dates": "|".join(sorted(transitions)),
                "linkage_status": status,
                "evidence_kind": "EXACT_TRANSITION",
                "diagnostics": "",
            }
        )
    return evidence_rows, linkage_rows


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")

    selected = targeted.validate_selected(args.selected_subset)
    _, official_sessions = targeted.validate_calendar(args.official_calendar)
    parent_summary, _, parent_manifest_sha = replay.verify_targeted_root(args.prior_targeted_root)
    if parent_manifest_sha != EXPECTED_PARENT_MANIFEST_SHA256:
        raise RuntimeError(f"PARENT_TARGETED_MANIFEST_SHA_MISMATCH:{parent_manifest_sha}")
    verify_parent_outputs(args.prior_targeted_root, parent_summary)

    prior_evidence = pd.read_csv(args.prior_targeted_root / "targeted_evidence.csv", dtype=str, keep_default_na=False)
    prior_linkage = pd.read_csv(args.prior_targeted_root / "targeted_event_linkage_audit.csv", dtype=str, keep_default_na=False)
    prior_parse = pd.read_csv(args.prior_targeted_root / "targeted_schedule_document_parse_audit.csv", dtype=str, keep_default_na=False)

    nisp = prior_evidence.loc[prior_evidence["event_id"].eq(NISP_EVENT_ID)].copy()
    if len(nisp) != 1 or clean(nisp.iloc[0].get("linkage_status")) != "EXACT_NON_BLOCKING_STATIC_SECURITY_TO_CURRENCY":
        raise RuntimeError("PARENT_NISP_EXACT_STATIC_EVIDENCE_CHANGED")

    reparsed_rows: list[dict[str, Any]] = []
    for prior in prior_parse.to_dict("records"):
        source_sha = clean(prior.get("source_sha256"))
        if not source_sha:
            reparsed_rows.append({**prior, "remediation_status": "NO_SOURCE_BYTES"})
            continue
        raw_path, payload = raw_pdf_by_sha(args.prior_targeted_root, source_sha)
        try:
            layout_text = strict_pdf_layout_text(payload)
            parsed = repair_layout_parse(layout_text, parse_ksei_schedule_transition(layout_text))
            reparsed_rows.append(
                {
                    **prior,
                    **asdict(parsed),
                    "diagnostics": "|".join(parsed.diagnostics),
                    "source_url": clean(prior.get("source_url") or prior.get("document_url")),
                    "source_sha256": source_sha,
                    "raw_relpath": raw_path.relative_to(args.prior_targeted_root).as_posix(),
                    "remediation_status": "LAYOUT_REPARSED",
                }
            )
        except Exception as exc:
            reparsed_rows.append(
                {
                    **prior,
                    "parse_status": "UNRESOLVED_PARSE_REMEDIATION",
                    "transition_date": "",
                    "transition_semantic": "",
                    "diagnostics": f"{type(exc).__name__}:{exc}",
                    "raw_relpath": raw_path.relative_to(args.prior_targeted_root).as_posix(),
                    "remediation_status": "LAYOUT_REPARSE_FAILED",
                }
            )

    mechanical_evidence, mechanical_linkage = build_mechanical_evidence(
        selected, reparsed_rows, official_sessions, prior_linkage
    )
    evidence_rows = [nisp.iloc[0].to_dict(), *mechanical_evidence]
    nisp_linkage = [
        row for row in prior_linkage.to_dict("records") if clean(row.get("event_id")) == NISP_EVENT_ID
    ]
    if len(nisp_linkage) != 1:
        raise RuntimeError("PARENT_NISP_LINKAGE_ROW_COUNT_CHANGED")
    linkage_rows = [*nisp_linkage, *mechanical_linkage]

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
    linkage = pd.DataFrame(linkage_rows).fillna("").sort_values(["ticker", "event_id"], kind="mergesort").reset_index(drop=True)
    parse_frame = pd.DataFrame(reparsed_rows).fillna("")

    args.output_dir.mkdir(parents=True)
    evidence_path = args.output_dir / "targeted_evidence.csv"
    linkage_path = args.output_dir / "targeted_event_linkage_audit.csv"
    parse_path = args.output_dir / "targeted_schedule_document_parse_audit.csv"
    requests_path = args.output_dir / "request_records.jsonl"
    evidence.to_csv(evidence_path, index=False, lineterminator="\n")
    linkage.to_csv(linkage_path, index=False, lineterminator="\n")
    parse_frame.to_csv(parse_path, index=False, lineterminator="\n")
    shutil.copyfile(args.prior_targeted_root / "request_records.jsonl", requests_path)

    exact_static = int(linkage["linkage_status"].eq("EXACT_NON_BLOCKING_STATIC_SECURITY_TO_CURRENCY").sum())
    exact_schedule = int(linkage["linkage_status"].eq("EXACT").sum())
    unresolved = 7 - exact_static - exact_schedule

    summary = dict(parent_summary)
    summary.update(
        {
            "exact_static_nonblocking_events": exact_static,
            "exact_schedule_transition_events": exact_schedule,
            "unresolved_selected_events": unresolved,
            "resolved_event_ids": sorted(set(evidence["event_id"])),
            "unresolved_event_ids": sorted(set(targeted.EXPECTED_SELECTED) - set(evidence["event_id"])),
            "provider_calls": True,
            "provider_calls_in_remediation": False,
            "parent_targeted_manifest_sha256": parent_manifest_sha,
            "input_hashes": {
                **(parent_summary.get("input_hashes") or {}),
                "parent_targeted_manifest": parent_manifest_sha,
            },
            "policy": {
                **(parent_summary.get("policy") or {}),
                "offline_layout_parser_remediation": True,
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
        "parent_targeted_manifest_sha256": parent_manifest_sha,
        "input_hashes": summary["input_hashes"],
        "summary_sha256": sha256_file(summary_path),
        "output_hashes": summary["output_hashes"],
    }
    manifest_path = args.output_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({**summary, "manifest_sha256": sha256_file(manifest_path)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
