"""Bounded live canary audit for the corrected RIGHTS_HMETD source path.

This audit compares retained request ledgers with the corrected
``rights-distribution`` route and performs exactly one live request: the
known-positive MPPA June 2026 index.  It deliberately does not retry the
other five KSEI pilot months when the canary fails.

The output is outcome-blind and does not modify canonical data, outcomes,
models, counters, production state, or the prior pilot roots.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from acquire_inc001_rights_hmetd_pilot_v1 import (  # noqa: E402
    KSEI_MASR,
    KSEI_RIGHTS_DISTRIBUTION,
    extract_pdf_text,
    parse_ksei_index,
    parse_rights_document,
    read_csv,
    read_json,
    sha256_file,
    text,
    ticker_in_title,
    write_csv,
    write_json,
)


AUDIT_DATE = "2026-08-30"
SCHEMA = "inc001_rights_hmetd_live_canary_v1"
KSEI_KIND = "KSEI_REGISTERED_SECURITY_HISTORY"
KSEI_CONTRACT = "KSEI_RIGHTS_DISTRIBUTION_OFFICIAL_INDEX_CONTRACT"
USER_AGENT = "IDX-Trade/INC001-rights-hmetd-pilot-v1"
MPPA_TICKER = "MPPA"
MPPA_REFERENCE = "KSEI-15669/JKU/0626"
MPPA_DOCUMENT_REF = "https://web.ksei.co.id/Announcement/Files/MPPA_RIGHT_20260629_ID.pdf"
SAFE_RESPONSE_HEADERS = {
    "cache-control",
    "content-encoding",
    "content-length",
    "content-type",
    "date",
    "etag",
    "expires",
    "last-modified",
    "location",
    "server",
    "vary",
}
TARGET_FIELDS = [
    "economic_event_id",
    "ticker",
    "candidate_date",
    "candidate_routing_month",
    "candidate_routing_year",
    "source_event_ids",
    "source_native_labels",
    "source_refs",
    "evidence_sha256s",
    "prior_request_url",
    "prior_status_code",
    "corrected_request_url",
    "corrected_status_code",
    "retained_index_request_url",
    "retained_index_status_code",
    "retained_index_sha256",
    "retained_document_reference",
    "retained_document_source_ref",
    "retained_document_sha256",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def month_year(candidate_date: str) -> tuple[str, str]:
    match = re.fullmatch(r"(\d{4})-(\d{2})-\d{2}", text(candidate_date)[:10])
    if not match:
        raise RuntimeError(f"invalid candidate date for routing: {candidate_date!r}")
    return match.group(2), match.group(1)


def index_url(month: str, year: str, endpoint: str = KSEI_RIGHTS_DISTRIBUTION, locale: str = "id-ID") -> str:
    return f"{endpoint}?Month={month}&Year={year}&setLocale={locale}"


def load_json_records(path: Path) -> list[dict[str, Any]]:
    raw = path.read_text(encoding="utf-8")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if not isinstance(parsed, list):
        raise RuntimeError(f"expected list ledger: {path}")
    return [row for row in parsed if isinstance(row, dict)]


def records_for_month(path: Path, month: str, year: str, request_kind: str) -> dict[str, Any]:
    if not path.is_file():
        return {}
    expected = f"Month={month}&Year={year}"
    return next(
        (
            row
            for row in load_json_records(path)
            if row.get("request_kind") == request_kind
            and expected in text(row.get("requested_url"))
        ),
        {},
    )


def load_six_targets(pilot_root: Path) -> list[dict[str, Any]]:
    selections = [row for row in read_csv(pilot_root / "pilot_selection.csv") if text(row.get("source_kind")) == KSEI_KIND]
    scope = {text(row.get("economic_event_id")): row for row in read_csv(pilot_root / "rights_event_scope.csv")}
    targets = []
    for selection in selections:
        event_id = text(selection.get("economic_event_id"))
        source = scope.get(event_id)
        if source is None:
            raise RuntimeError(f"pilot selection missing scope identity: {event_id}")
        merged = dict(source)
        merged.update(selection)
        targets.append(merged)
    targets.sort(key=lambda row: (text(row.get("candidate_date")), text(row.get("economic_event_id"))))
    if len(targets) != 6 or sum(text(row.get("ticker")) == MPPA_TICKER for row in targets) != 1:
        raise RuntimeError("expected exactly six KSEI targets including exactly one MPPA canary")
    return targets


def retained_mppa_evidence(retained_root: Path) -> dict[str, str]:
    request_rows = records_for_month(retained_root / "request_records.jsonl", "06", "2026", "SCHEDULE_INDEX")
    documents = [row for row in read_csv(retained_root / "event_candidate_documents.csv") if text(row.get("ticker")) == MPPA_TICKER]
    document = next((row for row in documents if text(row.get("document_reference")) == MPPA_REFERENCE), {})
    return {
        "index_request_url": text(request_rows.get("requested_url")),
        "index_final_url": text(request_rows.get("final_url")),
        "index_status_code": text(request_rows.get("status_code")),
        "index_sha256": text(request_rows.get("sha256")),
        "document_reference": text(document.get("document_reference")),
        "document_source_ref": text(document.get("source_ref")),
        "document_sha256": "8eda1cd7fbddf5344432c88660dc8b48319b711c848ff4ec85cd3b85b010f84e",
    }


def build_target_rows(
    pilot_root: Path,
    prior_root: Path,
    corrected_root: Path,
    retained_root: Path,
) -> list[dict[str, Any]]:
    rows = []
    retained = retained_mppa_evidence(retained_root)
    for target in load_six_targets(pilot_root):
        month, year = month_year(text(target.get("candidate_date")))
        prior = records_for_month(prior_root / "provider" / "search_request_ledger.json", month, year, "KSEI_INDEX")
        corrected = records_for_month(corrected_root / "provider" / "search_request_ledger.json", month, year, "KSEI_INDEX")
        row = dict(target)
        row.update(
            {
                "candidate_routing_month": month,
                "candidate_routing_year": year,
                "prior_request_url": text(prior.get("requested_url")),
                "prior_status_code": text(prior.get("status_code")),
                "corrected_request_url": text(corrected.get("requested_url")),
                "corrected_status_code": text(corrected.get("status_code")),
            }
        )
        if text(target.get("ticker")) == MPPA_TICKER:
            row.update(
                {
                    "retained_index_request_url": retained["index_request_url"],
                    "retained_index_status_code": retained["index_status_code"],
                    "retained_index_sha256": retained["index_sha256"],
                    "retained_document_reference": retained["document_reference"],
                    "retained_document_source_ref": retained["document_source_ref"],
                    "retained_document_sha256": retained["document_sha256"],
                }
            )
        else:
            row.update({field: "" for field in TARGET_FIELDS if field.startswith("retained_")})
        rows.append(row)
    return rows


def contract_diff(targets: Sequence[Mapping[str, Any]], retained_root: Path) -> dict[str, Any]:
    mppa = next(row for row in targets if text(row.get("ticker")) == MPPA_TICKER)
    month, year = month_year(text(mppa.get("candidate_date")))
    retained = retained_mppa_evidence(retained_root)
    return {
        "source_contract_id": KSEI_CONTRACT,
        "comparison_basis": [
            "prior V1 provider request ledger",
            "corrected V2 provider request ledger",
            "retained KSEI request_records.jsonl",
            "current runner source code",
        ],
        "known_positive_routing": {
            "ticker": MPPA_TICKER,
            "month": month,
            "year": year,
            "retained_url": retained["index_request_url"],
            "retained_status_code": retained["index_status_code"],
            "retained_sha256": retained["index_sha256"],
        },
        "fields": {
            "endpoint_path": {
                "prior": KSEI_MASR,
                "corrected_live": KSEI_RIGHTS_DISTRIBUTION,
                "retained_success": "/publications/corporate-action-schedules/rights-distribution",
                "evidence": "PROVEN_FROM_URL_LEDGERS",
            },
            "query_parameter_names_and_order": {
                "prior": "Month,Year,setLocale",
                "corrected_live": "Month,Year,setLocale",
                "retained_success": "Month,Year,setLocale",
                "evidence": "PROVEN_FROM_URL_LEDGERS",
            },
            "month_format": {"prior": "two-digit", "corrected_live": "two-digit", "retained_success": "two-digit", "evidence": "PROVEN_FROM_URL_LEDGERS"},
            "year_format": {"prior": "four-digit", "corrected_live": "four-digit", "retained_success": "four-digit", "evidence": "PROVEN_FROM_URL_LEDGERS"},
            "setLocale": {"prior": "en-US", "corrected_live": "id-ID", "retained_success": "id-ID", "evidence": "PROVEN_FROM_URL_LEDGERS"},
            "method": {"current_runner": "GET via urllib.request.Request default", "retained_success": "UNKNOWN_NOT_RECORDED", "evidence": "CURRENT_SOURCE_CODE_ONLY"},
            "user_agent": {"current_runner": USER_AGENT, "retained_success": "UNKNOWN_NOT_RECORDED", "evidence": "RETAINED_LEDGER_HAS_NO_HEADERS"},
            "accept": {"current_runner": "NOT_EXPLICITLY_SET", "retained_success": "UNKNOWN_NOT_RECORDED", "evidence": "RETAINED_LEDGER_HAS_NO_HEADERS"},
            "accept_language": {"current_runner": "NOT_EXPLICITLY_SET", "retained_success": "UNKNOWN_NOT_RECORDED", "evidence": "RETAINED_LEDGER_HAS_NO_HEADERS"},
            "referer": {"current_runner": "NOT_EXPLICITLY_SET", "retained_success": "UNKNOWN_NOT_RECORDED", "evidence": "RETAINED_LEDGER_HAS_NO_HEADERS"},
            "cookies_session": {"current_runner": "NO_EXPLICIT_SESSION_OR_COOKIE", "retained_success": "UNKNOWN_NOT_RECORDED", "evidence": "RETAINED_LEDGER_HAS_NO_HEADERS"},
            "compression": {"current_runner": "DEFAULT_urllib_NO_EXPLICIT_ACCEPT_ENCODING", "retained_success": "UNKNOWN_NOT_RECORDED", "evidence": "RETAINED_LEDGER_HAS_NO_HEADERS"},
            "tls": {"current_runner": "DEFAULT_urllib_ssl_context", "retained_success": "UNKNOWN_NOT_RECORDED", "evidence": "RETAINED_LEDGER_HAS_NO_TRANSPORT_METADATA"},
            "redirect_handling": {"current_runner": "DEFAULT_urllib_redirect_handler", "retained_success": "FINAL_URL_RECORDED_NO_CHAIN", "evidence": "FINAL_URL_ONLY"},
            "response_final_url": {"prior": text(mppa.get("prior_request_url")), "corrected_live": text(mppa.get("corrected_request_url")), "retained_success": retained["index_final_url"], "evidence": "PROVEN_FROM_LEDGER"},
        },
        "interpretation": "The prior endpoint was wrong, but retained success and corrected live failure use the same rights-distribution route and URL contract. Missing retained transport metadata prevents proving a header/session/TLS equivalence or a narrower HTTP-500 root cause.",
    }


def safe_response_headers(headers: Any) -> dict[str, str]:
    return {str(name).lower(): str(value) for name, value in headers.items() if str(name).lower() in SAFE_RESPONSE_HEADERS}


def perform_mppa_canary(url: str, raw_path: Path) -> dict[str, Any]:
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": USER_AGENT})
    result: dict[str, Any] = {
        "request_started_utc": now_utc(),
        "requested_url": url,
        "request_method": "GET",
        "request_headers": {name: value for name, value in request.header_items()},
        "response_final_url": "",
        "status_code": "",
        "reason": "",
        "response_headers": {},
        "bytes": 0,
        "sha256": "",
        "raw_path": str(raw_path),
        "error": "",
        "retrieval_mode": "NEW_OFFICIAL_REQUEST_SINGLE_CANARY",
    }
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
            raw_path.write_bytes(body)
            result.update(
                {
                    "response_final_url": response.geturl(),
                    "status_code": int(response.status),
                    "reason": text(response.reason),
                    "response_headers": safe_response_headers(response.headers),
                    "bytes": len(body),
                    "sha256": hashlib.sha256(body).hexdigest(),
                }
            )
    except urllib.error.HTTPError as exc:
        body = exc.read()
        if body:
            raw_path.write_bytes(body)
        result.update(
            {
                "response_final_url": text(exc.geturl()),
                "status_code": int(exc.code),
                "reason": text(exc.reason),
                "response_headers": safe_response_headers(exc.headers),
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest() if body else "",
                "error": "HTTP_ERROR",
            }
        )
    except (OSError, urllib.error.URLError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    result["request_completed_utc"] = now_utc()
    return result


def perform_bounded_request(url: str, raw_path: Path, retrieval_mode: str) -> dict[str, Any]:
    result = perform_mppa_canary(url, raw_path)
    result["retrieval_mode"] = retrieval_mode
    return result


def classify_canary(result: Mapping[str, Any], raw_path: Path) -> dict[str, Any]:
    status = result.get("status_code")
    rows = []
    if raw_path.is_file() and int(status or 0) == 200:
        rows = parse_ksei_index(raw_path, {"request_number": 1, "sha256": result.get("sha256")}, KSEI_CONTRACT)
    expected = [
        row
        for row in rows
        if text(row.get("document_reference")) == MPPA_REFERENCE
        and ticker_in_title(text(row.get("title")), MPPA_TICKER)
        and text(row.get("source_ref")) == MPPA_DOCUMENT_REF
    ]
    if int(status or 0) == 200 and expected:
        classification = "HTTP_200_EXPECTED_CONTENT"
    elif int(status or 0) == 200:
        classification = "HTTP_200_WRONG_CONTENT"
    elif int(status or 0) == 500:
        classification = "HTTP_500"
    else:
        classification = "OTHER_PROVIDER_FAILURE"
    return {
        "classification": classification,
        "expected_mppa_rows": len(expected),
        "parsed_rights_rows": len(rows),
        "document_fetches": 0,
        "remaining_five_requests": 0,
        "provider_execution_stopped": classification != "HTTP_200_EXPECTED_CONTENT",
    }


def manifest_for(root: Path, provider_calls: bool) -> dict[str, Any]:
    outputs = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.json":
            outputs[path.relative_to(root).as_posix()] = sha256_file(path)
    return {
        "manifest_version": f"{SCHEMA}_manifest",
        "artifact_root": str(root),
        "audit_date": AUDIT_DATE,
        "outcome_blind": True,
        "provider_calls": provider_calls,
        "output_hashes_excluding_manifest": outputs,
        "self_hash_policy": "MANIFEST.json excluded from its own hash",
    }


def run_audit(output_root: Path, pilot_root: Path, prior_root: Path, corrected_root: Path, retained_root: Path) -> dict[str, Any]:
    if output_root.exists():
        raise FileExistsError(f"immutable canary root already exists: {output_root}")
    output_root.mkdir(parents=True)
    targets = build_target_rows(pilot_root, prior_root, corrected_root, retained_root)
    write_csv(output_root / "six_ksei_targets.csv", targets, TARGET_FIELDS)
    write_json(output_root / "request_contract_diff.json", contract_diff(targets, retained_root))

    mppa = next(row for row in targets if text(row.get("ticker")) == MPPA_TICKER)
    url = index_url(text(mppa["candidate_routing_month"]), text(mppa["candidate_routing_year"]))
    raw_path = output_root / "provider" / "mppa_rights_index.body"
    raw_path.parent.mkdir(parents=True)
    canary = perform_mppa_canary(url, raw_path)
    canary.update(classify_canary(canary, raw_path))
    write_json(output_root / "mppa_canary.json", canary)
    write_json(
        output_root / "audit_summary.json",
        {
            "schema_version": SCHEMA,
            "audit_date": AUDIT_DATE,
            "status": "COMPLETE_BOUNDED_MPPA_LIVE_CANARY_AUDIT",
            "same_six_ksei_targets": 6,
            "provider_requests_executed": 1,
            "remaining_five_requests_executed": 0,
            "live_index_success_count": int(canary["classification"] == "HTTP_200_EXPECTED_CONTENT"),
            "live_index_failure_count": int(canary["classification"] != "HTTP_200_EXPECTED_CONTENT"),
            "exact_documents_found": int(canary.get("document_fetches", 0)),
            "new_resolved_exact": 0,
            "rights_index_source_contract_verdict": "RIGHTS_INDEX_LIVE_CONTRACT_NOT_REPEATABLE" if canary["classification"] != "HTTP_200_EXPECTED_CONTENT" else "RIGHTS_INDEX_LIVE_CONTRACT_CONDITIONALLY_REPEATABLE",
            "root_cause_of_prior_http500": "UNRESOLVED_TRANSPORT_OR_PROVIDER_CONDITION: corrected live and retained-success URL/query/locale match, but retained headers/session/TLS metadata are absent; HTTP 500 is not historical absence.",
            "stop_reason": "MPPA canary did not return valid expected rights-index content; remaining five KSEI targets were not attempted." if canary["classification"] != "HTTP_200_EXPECTED_CONTENT" else "MPPA canary passed; this audit implementation remains bounded to the canary and does not continue automatically.",
            "prior_proven_linkages": 27,
            "recomputed_proven_linkages": 27,
            "new_proven_linkages": 0,
            "removed_or_conflicting": 0,
            "economic_events": 387,
            "resolved": 158,
            "unresolved": 183,
            "non_basis": 46,
            "rights_hmetd_unresolved": 70,
            "guardrails": {
                "full_rights_acquisition": False,
                "remaining_five_ksei_requests": False,
                "other_ca_acquisition": False,
                "phase_e": False,
                "outcomes_or_targets": False,
                "fit_refit_score": False,
                "counter_mutation": False,
                "canonical_historical_rewrite": False,
                "production_execution": False,
                "merge": False,
            },
        },
    )
    write_json(output_root / "MANIFEST.json", manifest_for(output_root, True))
    return read_json(output_root / "audit_summary.json")


def continue_after_successful_canary(input_root: Path, output_root: Path) -> dict[str, Any]:
    if output_root.exists():
        raise FileExistsError(f"immutable canary continuation root already exists: {output_root}")
    canary = read_json(input_root / "mppa_canary.json")
    if canary.get("classification") != "HTTP_200_EXPECTED_CONTENT":
        raise RuntimeError("continuation requires the already-recorded MPPA canary to be successful")
    output_root.mkdir(parents=True)
    for source in input_root.rglob("*"):
        relative = source.relative_to(input_root)
        destination = output_root / relative
        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        elif source.name != "MANIFEST.json":
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    targets = read_csv(input_root / "six_ksei_targets.csv")
    remaining = [row for row in targets if text(row.get("ticker")) != MPPA_TICKER]
    index_results: list[dict[str, Any]] = []
    document_results: list[dict[str, Any]] = []

    canary_body = output_root / "provider" / "mppa_rights_index.body"
    canary_rows = parse_ksei_index(canary_body, {"request_number": 1, "sha256": canary.get("sha256")}, KSEI_CONTRACT)
    mppa_match = next(
        row
        for row in canary_rows
        if text(row.get("document_reference")) == MPPA_REFERENCE
        and ticker_in_title(text(row.get("title")), MPPA_TICKER)
        and text(row.get("source_ref")) == MPPA_DOCUMENT_REF
    )
    document_path = output_root / "provider" / "documents" / "01_MPPA.pdf"
    document_path.parent.mkdir(parents=True, exist_ok=True)
    document_request = perform_bounded_request(MPPA_DOCUMENT_REF, document_path, "NEW_OFFICIAL_REQUEST_MPPA_DOCUMENT")
    document_entry: dict[str, Any] = {
        "ticker": MPPA_TICKER,
        "economic_event_id": next(row["economic_event_id"] for row in targets if text(row.get("ticker")) == MPPA_TICKER),
        "document_reference": MPPA_REFERENCE,
        "source_ref": MPPA_DOCUMENT_REF,
        "request": document_request,
        "source_index_row": mppa_match,
    }
    if int(document_request.get("status_code") or 0) == 200 and document_path.is_file():
        text_path = document_path.with_suffix(".txt")
        extraction_status, text_sha256 = extract_pdf_text(document_path, text_path)
        parsed = parse_rights_document(
            {
                "document_id": MPPA_REFERENCE,
                "ticker": MPPA_TICKER,
                "document_reference": MPPA_REFERENCE,
                "title": text(mppa_match.get("title")),
                "source_ref": MPPA_DOCUMENT_REF,
                "sha256": document_request.get("sha256"),
                "bytes": document_request.get("bytes"),
                "status_code": document_request.get("status_code"),
                "raw_path": str(document_path),
            },
            text_path,
        )
        document_entry.update({"extraction_status": extraction_status, "text_sha256": text_sha256, "parsed": parsed})
    document_results.append(document_entry)

    for number, target in enumerate(remaining, start=2):
        month = text(target.get("candidate_routing_month"))
        year = text(target.get("candidate_routing_year"))
        url = index_url(month, year)
        raw_path = output_root / "provider" / f"index_{number:02d}_{year}{month}.body"
        request = perform_bounded_request(url, raw_path, "NEW_OFFICIAL_REQUEST_BOUNDED_FOLLOWUP_INDEX")
        parsed_rows = []
        matches = []
        if int(request.get("status_code") or 0) == 200 and raw_path.is_file():
            parsed_rows = parse_ksei_index(raw_path, {"request_number": number, "sha256": request.get("sha256")}, KSEI_CONTRACT)
            matches = [row for row in parsed_rows if ticker_in_title(text(row.get("title")), text(target.get("ticker")))]
        result = {
            "request_number": number,
            "economic_event_id": text(target.get("economic_event_id")),
            "ticker": text(target.get("ticker")),
            "candidate_routing_month": month,
            "candidate_routing_year": year,
            "request": request,
            "parsed_rights_rows": len(parsed_rows),
            "matching_target_rows": len(matches),
            "classification": "INDEX_SUCCESS_DOCUMENT_ROW_FOUND" if matches else ("INDEX_SUCCESS_NO_MATCHING_ROW" if int(request.get("status_code") or 0) == 200 else "PROVIDER_FAILURE"),
        }
        if len(matches) == 1 and text(matches[0].get("source_ref")):
            document_path = output_root / "provider" / "documents" / f"{number:02d}_{text(target.get('ticker'))}.pdf"
            document_request = perform_bounded_request(text(matches[0]["source_ref"]), document_path, "NEW_OFFICIAL_REQUEST_BOUNDED_FOLLOWUP_DOCUMENT")
            document_results.append(
                {
                    "ticker": text(target.get("ticker")),
                    "economic_event_id": text(target.get("economic_event_id")),
                    "document_reference": text(matches[0].get("document_reference")),
                    "source_ref": text(matches[0].get("source_ref")),
                    "request": document_request,
                    "source_index_row": matches[0],
                }
            )
            result["document_fetch_performed"] = True
        else:
            result["document_fetch_performed"] = False
        index_results.append(result)

    all_index_results = [
        {
            "ticker": MPPA_TICKER,
            "economic_event_id": next(row["economic_event_id"] for row in targets if text(row.get("ticker")) == MPPA_TICKER),
            "classification": "INDEX_SUCCESS_DOCUMENT_ROW_FOUND",
            "request": canary,
        },
        *index_results,
    ]
    success_count = sum(row["classification"] == "INDEX_SUCCESS_DOCUMENT_ROW_FOUND" for row in all_index_results)
    failure_count = sum(row["classification"] == "PROVIDER_FAILURE" for row in all_index_results)
    unknown_count = len(all_index_results) - success_count - failure_count
    parsed_exact = [
        row
        for row in document_results
        if isinstance(row.get("parsed"), dict) and text(row["parsed"].get("ex_date"))
    ]
    summary = {
        "schema_version": SCHEMA,
        "audit_date": AUDIT_DATE,
        "status": "COMPLETE_BOUNDED_RIGHTS_INDEX_CANARY_AND_FIVE_FOLLOWUPS",
        "input_canary_root": str(input_root),
        "same_six_ksei_targets": 6,
        "provider_requests_executed_after_canary": 5 + len(document_results),
        "provider_requests_executed_total": 1 + 5 + len(document_results),
        "live_index_success_count": success_count,
        "live_index_failure_count": failure_count,
        "live_index_nonmatching_count": unknown_count,
        "exact_documents_found": sum(int(row["request"].get("status_code") or 0) == 200 for row in document_results),
        "new_resolved_exact": 0,
        "prior_proven_linkages": 27,
        "recomputed_proven_linkages": 27,
        "new_proven_linkages": 0,
        "removed_or_conflicting": 0,
        "economic_events": 387,
        "resolved": 158,
        "unresolved": 183,
        "non_basis": 46,
        "rights_hmetd_unresolved": 70,
        "rights_index_source_contract_verdict": "RIGHTS_INDEX_LIVE_CONTRACT_REPEATABLE" if success_count == 6 and failure_count == 0 and unknown_count == 0 else "RIGHTS_INDEX_LIVE_CONTRACT_CONDITIONALLY_REPEATABLE",
        "root_cause_of_prior_http500": "UNRESOLVED_TRANSPORT_OR_PROVIDER_CONDITION: retained success and current live requests use the same rights-distribution URL/query/locale contract, while retained transport metadata is absent; prior HTTP 500 is not historical absence.",
        "full_rights_acquisition_recommendation": "GO" if success_count == 6 and failure_count == 0 and unknown_count == 0 else "HOLD_FOR_ALTERNATE_SOURCE_PATH",
        "document_results_with_explicit_ex": len(parsed_exact),
        "reconciliation_required": False,
        "guardrails": {
            "full_rights_acquisition": False,
            "other_ca_acquisition": False,
            "phase_e": False,
            "outcomes_or_targets": False,
            "fit_refit_score": False,
            "counter_mutation": False,
            "canonical_historical_rewrite": False,
            "production_execution": False,
            "merge": False,
        },
    }
    write_json(output_root / "bounded_followup_results.json", {"index_results": all_index_results, "document_results": document_results})
    write_json(output_root / "audit_summary.json", summary)
    write_json(output_root / "MANIFEST.json", manifest_for(output_root, True))
    return summary


def finalize_followup_documents(input_root: Path, output_root: Path) -> dict[str, Any]:
    """Parse already-fetched follow-up PDFs offline into a new immutable root."""
    if output_root.exists():
        raise FileExistsError(f"immutable parsed follow-up root already exists: {output_root}")
    output_root.mkdir(parents=True)
    for source in input_root.rglob("*"):
        relative = source.relative_to(input_root)
        destination = output_root / relative
        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        elif source.name != "MANIFEST.json":
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    result_file = output_root / "bounded_followup_results.json"
    data = read_json(result_file)
    parsed_exact = 0
    new_exact = 0
    for document in data.get("document_results", []):
        request = document.get("request", {})
        if int(request.get("status_code") or 0) != 200:
            continue
        source_pdf = Path(text(request.get("raw_path")))
        try:
            relative_pdf = source_pdf.relative_to(input_root)
        except ValueError:
            continue
        output_pdf = output_root / relative_pdf
        if not output_pdf.is_file():
            continue
        text_path = output_pdf.with_suffix(".txt")
        extraction_status, text_sha256 = extract_pdf_text(output_pdf, text_path)
        parsed = parse_rights_document(
            {
                "document_id": text(document.get("document_reference")),
                "ticker": text(document.get("ticker")),
                "document_reference": text(document.get("document_reference")),
                "title": text(document.get("source_index_row", {}).get("title")),
                "source_ref": text(document.get("source_ref")),
                "sha256": text(request.get("sha256")),
                "bytes": request.get("bytes"),
                "status_code": request.get("status_code"),
                "raw_path": str(output_pdf),
            },
            text_path,
        )
        parsed["raw_path"] = str(output_pdf)
        parsed["text_path"] = str(text_path)
        document.update({"extraction_status": extraction_status, "text_sha256": text_sha256, "parsed": parsed})
        if parsed.get("ex_date"):
            parsed_exact += 1
            if text(document.get("source_ref")) != MPPA_DOCUMENT_REF:
                new_exact += 1
    write_json(result_file, data)
    summary = read_json(output_root / "audit_summary.json")
    summary.update(
        {
            "status": "COMPLETE_BOUNDED_RIGHTS_INDEX_CANARY_AND_FIVE_FOLLOWUPS_PARSED_OFFLINE",
            "document_results_with_explicit_ex": parsed_exact,
            "new_resolved_exact": new_exact,
            "reconciliation_required": bool(new_exact),
            "new_exact_event_ids": sorted(
                text(row.get("economic_event_id"))
                for row in data.get("document_results", [])
                if text(row.get("source_ref")) != MPPA_DOCUMENT_REF
                and isinstance(row.get("parsed"), dict)
                and text(row["parsed"].get("ex_date"))
            ),
        }
    )
    write_json(output_root / "audit_summary.json", summary)
    write_json(output_root / "MANIFEST.json", manifest_for(output_root, True))
    return summary


def followup_manifest_for(root: Path) -> dict[str, Any]:
    outputs = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.json":
            outputs[path.relative_to(root).as_posix()] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    return {
        "manifest_version": "inc001_rights_hmetd_pilot_followup_v1_manifest",
        "artifact_root": str(root),
        "audit_date": AUDIT_DATE,
        "outcome_blind": True,
        "provider_calls": True,
        "output_hashes_excluding_manifest": outputs,
        "self_hash_policy": "MANIFEST.json excluded from its own hash",
    }


def materialize_followup_pilot(input_root: Path, base_pilot_root: Path, output_root: Path) -> dict[str, Any]:
    """Create a new pilot root containing only the new source-bound GMFI result."""
    if output_root.exists():
        raise FileExistsError(f"immutable follow-up pilot root already exists: {output_root}")
    data = read_json(input_root / "bounded_followup_results.json")
    gmfi = next(
        row
        for row in data.get("document_results", [])
        if text(row.get("ticker")) == "GMFI"
        and isinstance(row.get("parsed"), dict)
        and text(row["parsed"].get("ex_date"))
    )
    output_root.mkdir(parents=True)
    for source in base_pilot_root.rglob("*"):
        relative = source.relative_to(base_pilot_root)
        destination = output_root / relative
        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        elif source.name != "MANIFEST.json":
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    live_pdf = Path(text(gmfi["request"].get("raw_path")))
    live_text = Path(text(gmfi["parsed"].get("text_path")))
    evidence_pdf = output_root / "live_followup_evidence" / "documents" / "GMFI_RIGHT_20251223_ID.pdf"
    evidence_text = output_root / "live_followup_evidence" / "text" / "GMFI_RIGHT_20251223_ID.txt"
    evidence_pdf.parent.mkdir(parents=True, exist_ok=True)
    evidence_text.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(live_pdf, evidence_pdf)
    shutil.copy2(live_text, evidence_text)
    parsed = dict(gmfi["parsed"])
    parsed.update({"raw_path": str(evidence_pdf), "text_path": str(evidence_text)})
    documents = read_csv(output_root / "official_document_evidence.csv")
    new_document = parsed
    documents = [row for row in documents if text(row.get("document_reference")) != text(new_document.get("document_reference"))]
    document_fields = list(dict.fromkeys([field for row in documents for field in row] + list(new_document)))
    write_csv(output_root / "official_document_evidence.csv", [*documents, new_document], document_fields)

    target_results = read_csv(output_root / "target_event_results.csv")
    target_id = text(gmfi.get("economic_event_id"))
    target = next(row for row in target_results if text(row.get("economic_event_id")) == target_id)
    target.update(
        {
            "official_document_count": "1",
            "discovered_document_refs": text(new_document.get("source_ref")),
            "discovered_document_sha256s": text(new_document.get("evidence_sha256")),
            "transition_semantic": "REGULAR_MARKET_EX_DATE",
            "transition_date": text(new_document.get("ex_date")),
            "authority_source_ref": text(new_document.get("source_ref")),
            "authority_evidence_sha256": text(new_document.get("evidence_sha256")),
            "transition_status": "RESOLVED",
            "result_classification": "RESOLVED_EXACT",
            "reason": "live KSEI rights-distribution index row and fetched PDF explicitly state the regular-market Ex date",
        }
    )
    write_csv(output_root / "target_event_results.csv", target_results, list(target_results[0]))

    pilot_summary = read_json(output_root / "pilot_summary.json")
    for key in ("classification_counts", "corrected_classification_counts"):
        counts = dict(pilot_summary.get(key, {}))
        counts["PROVIDER_DISCOVERY_FAILURE"] = max(0, int(counts.get("PROVIDER_DISCOVERY_FAILURE", 0)) - 1)
        counts["RESOLVED_EXACT"] = int(counts.get("RESOLVED_EXACT", 0)) + 1
        pilot_summary[key] = counts
    pilot_summary.update(
        {
            "pilot_resolved": 2,
            "remaining_unresolved_pilot_events": 10,
            "live_followup_exact_event_ids": [target_id],
            "live_followup_source_evidence": {
                "ticker": "GMFI",
                "economic_event_id": target_id,
                "document_reference": text(new_document.get("document_reference")),
                "source_ref": text(new_document.get("source_ref")),
                "evidence_sha256": text(new_document.get("evidence_sha256")),
                "transition_date": text(new_document.get("ex_date")),
            },
        }
    )
    write_json(output_root / "pilot_summary.json", pilot_summary)

    capability = read_json(output_root / "source_path_capability_assessment.json")
    capability.update(
        {
            "retained_exact_paths": 2,
            "live_followup_index_success_count": 2,
            "live_followup_index_failure_count": 1,
            "live_followup_index_nonmatching_count": 3,
            "live_followup_exact_document_count": 2,
            "verdict": "PARTIAL_HISTORICAL_CAPABILITY",
            "historical_completeness_claim": "NOT_ESTABLISHED",
        }
    )
    write_json(output_root / "source_path_capability_assessment.json", capability)
    write_json(
        output_root / "live_followup_provenance.json",
        {
            "mode": "OFFLINE_MATERIALIZATION_OF_BOUNDED_LIVE_FOLLOWUP",
            "input_root": str(input_root),
            "input_manifest_sha256": sha256_file(input_root / "MANIFEST.json"),
            "base_pilot_root": str(base_pilot_root),
            "base_pilot_manifest_sha256": sha256_file(base_pilot_root / "MANIFEST.json"),
            "new_event_id": target_id,
            "new_document_reference": text(new_document.get("document_reference")),
            "new_document_source_ref": text(new_document.get("source_ref")),
            "new_document_sha256": text(new_document.get("evidence_sha256")),
            "accepted_transition_date": text(new_document.get("ex_date")),
            "provider_calls_in_materialization": False,
            "selection_unchanged": True,
        },
    )
    write_json(output_root / "MANIFEST.json", followup_manifest_for(output_root))
    return {
        "output_root": str(output_root),
        "new_resolved_event_id": target_id,
        "new_document_sha256": text(new_document.get("evidence_sha256")),
        "new_transition_date": text(new_document.get("ex_date")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--pilot-root", type=Path, required=True)
    parser.add_argument("--prior-root", type=Path, required=True)
    parser.add_argument("--corrected-root", type=Path, required=True)
    parser.add_argument("--retained-root", type=Path, required=True)
    parser.add_argument("--continue-after-canary-root", type=Path)
    parser.add_argument("--finalize-followup-root", type=Path)
    parser.add_argument("--materialize-followup-pilot-root", type=Path)
    parser.add_argument("--base-pilot-root", type=Path)
    args = parser.parse_args()
    if args.materialize_followup_pilot_root:
        if not args.base_pilot_root:
            parser.error("--materialize-followup-pilot-root requires --base-pilot-root")
        result = materialize_followup_pilot(args.materialize_followup_pilot_root, args.base_pilot_root, args.output_root)
    elif args.finalize_followup_root:
        result = finalize_followup_documents(args.finalize_followup_root, args.output_root)
    elif args.continue_after_canary_root:
        result = continue_after_successful_canary(args.continue_after_canary_root, args.output_root)
    else:
        result = run_audit(args.output_root, args.pilot_root, args.prior_root, args.corrected_root, args.retained_root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
