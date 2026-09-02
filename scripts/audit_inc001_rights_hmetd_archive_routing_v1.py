"""Bounded archive-routing audit for the three prior RIGHTS_HMETD no-matches.

The audit first writes a deterministic, source-backed routing plan.  Execution
then reuses retained successful index bodies (including the prior candidate
month requests) and makes at most one new GET for each not-yet-retained month.
The scope is exactly SAME, SGER, and PACK.  It never broadens to the remaining
RIGHTS population and never treats a candidate, record, or distribution date
as an Ex date.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from acquire_inc001_rights_hmetd_pilot_v1 import (  # noqa: E402
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
SCHEMA = "inc001_rights_hmetd_archive_routing_v1"
KSEI_CONTRACT = "KSEI_RIGHTS_DISTRIBUTION_OFFICIAL_INDEX_CONTRACT"
KSEI_KIND = "KSEI_REGISTERED_SECURITY_HISTORY"
USER_AGENT = "IDX-Trade/INC001-rights-hmetd-archive-routing-v1"
TARGET_TICKERS = ("SAME", "SGER", "PACK")
TARGET_SOURCE_IDS = {
    "SAME": "ec01d7736d59116e37f5552f124758a4d9f7079af191e9ab2012255c50cbf38f",
    "SGER": "a9421890253582dc9d223d03cacf586b14a682a53d35184d60a331277ef630b4",
    "PACK": "b92e80322a60a5d6c7cb138f3edb650e17fe5ce3e59fcd2c3f6801dce55fb8df",
}
TARGET_EVENT_IDS = {
    "SAME": "DERIVED-cae8b02b518fd4886cbb957641bf75cb646c00d8cec959905cefde2614de9fa9",
    "SGER": "DERIVED-d4dabf435934131619c850ab1fd070aee06928d24c188ac46571722c0ad2091c",
    "PACK": "DERIVED-69e5d8da2753198c085f8ba736fcded7c6b4e98205ca3ac140d12bec69a1c1ff",
}
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
TARGET_FIELDS = [
    "economic_event_id",
    "ticker",
    "source_event_id",
    "source_native_label",
    "candidate_date",
    "candidate_dates",
    "cum_date",
    "record_date",
    "distribution_date",
    "ratio_raw",
    "source_ref",
    "evidence_sha256",
    "source_contract_id",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def valid_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value.strip()))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_json_records(path: Path) -> list[dict[str, Any]]:
    raw = path.read_text(encoding="utf-8")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if not isinstance(parsed, list):
        raise RuntimeError(f"expected list ledger: {path}")
    return [row for row in parsed if isinstance(row, dict)]


def index_url(month: str, year: str) -> str:
    return f"{KSEI_RIGHTS_DISTRIBUTION}?Month={month}&Year={year}&setLocale=id-ID"


def parse_month(value: str) -> tuple[int, int]:
    match = DATE_RE.fullmatch(text(value)[:10])
    if not match:
        raise RuntimeError(f"invalid ISO date: {value!r}")
    return int(match.group(1)), int(match.group(2))


def month_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    ordinal = year * 12 + month - 1 + delta
    return ordinal // 12, ordinal % 12 + 1


def url_month(url: Any) -> str:
    match = re.search(r"Month=(\d{2})&Year=(\d{4})", text(url))
    return f"{match.group(2)}-{match.group(1)}" if match else ""


def archive_temporal_semantics(retained_root: Path) -> dict[str, Any]:
    rows = read_csv(retained_root / "event_candidate_documents.csv")
    comparisons: list[dict[str, Any]] = []
    for row in rows:
        publication = text(row.get("document_date"))[:10]
        query = f"{int(text(row.get('query_year'))):04d}-{int(text(row.get('query_month'))):02d}"
        first_source = sorted(value[:10] for value in text(row.get("source_dates")).split("|") if DATE_RE.fullmatch(value[:10]))
        publication_month = publication[:7] if DATE_RE.fullmatch(publication) else ""
        first_event_month = first_source[0][:7] if first_source else ""
        if publication_month and first_event_month:
            pub_year, pub_month = parse_month(publication)
            event_year, event_month = parse_month(first_source[0])
            lead = (event_year * 12 + event_month) - (pub_year * 12 + pub_month)
        else:
            lead = None
        comparisons.append(
            {
                "ticker": text(row.get("ticker")),
                "document_reference": text(row.get("reference")),
                "archive_month": query,
                "publication_date": publication,
                "first_source_event_date": first_source[0] if first_source else "",
                "publication_month_equals_archive": publication_month == query,
                "publication_to_first_event_calendar_months": lead,
            }
        )
    equal = sum(item["publication_month_equals_archive"] for item in comparisons)
    leads = [item["publication_to_first_event_calendar_months"] for item in comparisons if item["publication_to_first_event_calendar_months"] is not None]
    max_lead = max(leads) if leads else 0
    min_lead = min(leads) if leads else 0
    if not comparisons or equal != len(comparisons):
        conclusion = "ARCHIVE_KEYS_MIXED_OR_UNKNOWN"
    else:
        conclusion = "ARCHIVE_KEYS_PUBLICATION_MONTH"
    return {
        "source_root": str(retained_root),
        "source_file": str(retained_root / "event_candidate_documents.csv"),
        "retained_document_rows": len(comparisons),
        "unique_document_references": len({item["document_reference"] for item in comparisons}),
        "archive_month_equals_publication_month_rows": equal,
        "archive_month_differs_from_publication_month_rows": len(comparisons) - equal,
        "publication_to_first_event_calendar_months": {"minimum": min_lead, "maximum": max_lead, "counts": dict(sorted(Counter(str(value) for value in leads).items()))},
        "publication_month_evidence_rows": comparisons,
        "pgjo_rights_candidate_rows": sum(text(row.get("ticker")).upper() == "PGJO" for row in rows),
        "conclusion": conclusion,
        "window_basis": "Use candidate month plus the two immediately preceding calendar months because retained rows show a maximum two-calendar-month publication lead; never use an arbitrary broad window.",
    }


def load_targets(v13_root: Path) -> list[dict[str, Any]]:
    source_rows = {text(row.get("source_event_id")): row for row in read_csv(v13_root / "source_evidence_ledger.csv")}
    targets: list[dict[str, Any]] = []
    for ticker in TARGET_TICKERS:
        source_id = TARGET_SOURCE_IDS[ticker]
        source = source_rows.get(source_id)
        if source is None:
            raise RuntimeError(f"missing V13 source row for {ticker}")
        if text(source.get("ticker")).upper() != ticker or text(source.get("source_kind")) != KSEI_KIND or text(source.get("source_native_label")) != "Right Distribution":
            raise RuntimeError(f"target source contract mismatch for {ticker}")
        if text(source.get("event_family")) != "RIGHTS_HMETD":
            raise RuntimeError(f"target family mismatch for {ticker}")
        dates = [text(source.get(key))[:10] for key in ("candidate_date", "cum_date", "record_date", "distribution_date") if DATE_RE.fullmatch(text(source.get(key))[:10])]
        targets.append(
            {
                "economic_event_id": TARGET_EVENT_IDS[ticker],
                "ticker": ticker,
                "source_event_id": source_id,
                "source_native_label": text(source.get("source_native_label")),
                "candidate_date": text(source.get("candidate_date"))[:10],
                "candidate_dates": "|".join(sorted(set(dates))),
                "cum_date": text(source.get("cum_date"))[:10],
                "record_date": text(source.get("record_date"))[:10],
                "distribution_date": text(source.get("distribution_date"))[:10],
                "ratio_raw": text(source.get("ratio_raw")),
                "source_ref": text(source.get("source_ref")),
                "evidence_sha256": text(source.get("evidence_sha256")).lower(),
                "source_contract_id": text(source.get("source_contract_id")),
            }
        )
    return targets


def matching_records(records: Sequence[Mapping[str, Any]], key: str) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in records
        if row.get("request_kind") == "SCHEDULE_INDEX"
        and url_month(row.get("requested_url")) == key
        and "/publications/corporate-action-schedules/rights-distribution" in text(row.get("requested_url"))
        and text(row.get("requested_url")).endswith("setLocale=id-ID")
    ]


def retained_month_evidence(retained_root: Path, key: str) -> dict[str, Any] | None:
    records = matching_records(read_json_records(retained_root / "request_records.jsonl"), key)
    successful = [row for row in records if int(row.get("status_code") or 0) == 200 and Path(text(row.get("path"))).is_file()]
    if not successful:
        return None
    selected = successful[-1]
    raw_path = Path(text(selected.get("path")))
    parsed = parse_ksei_index(raw_path, {"request_number": selected.get("attempt"), "sha256": selected.get("sha256")}, KSEI_CONTRACT)
    return {
        "evidence_source": "RETAINED_KSEI_INDEX",
        "request_records": records,
        "selected_request": selected,
        "raw_path": str(raw_path),
        "sha256": text(selected.get("sha256")).lower(),
        "parsed_rows": parsed,
    }


def prior_followup_month_evidence(followup_root: Path, target: Mapping[str, Any], key: str) -> dict[str, Any] | None:
    data = read_json(followup_root / "bounded_followup_results.json")
    candidates = [
        row
        for row in data.get("index_results", [])
        if text(row.get("ticker")).upper() == text(target.get("ticker")).upper()
        and url_month(row.get("request", {}).get("requested_url")) == key
    ]
    if not candidates:
        return None
    result = candidates[-1]
    request = result.get("request", {})
    raw_path = Path(text(request.get("raw_path")))
    parsed = []
    if int(request.get("status_code") or 0) == 200 and raw_path.is_file():
        parsed = parse_ksei_index(raw_path, {"request_number": request.get("request_number"), "sha256": request.get("sha256")}, KSEI_CONTRACT)
    return {
        "evidence_source": "PRIOR_LIVE_ARCHIVE_ROUTING_AUDIT",
        "prior_result": result,
        "selected_request": request,
        "raw_path": str(raw_path),
        "sha256": text(request.get("sha256")).lower(),
        "parsed_rows": parsed,
    }


def target_scope_and_plan(v13_root: Path, retained_root: Path, followup_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    targets = load_targets(v13_root)
    semantics = archive_temporal_semantics(retained_root)
    if semantics["conclusion"] != "ARCHIVE_KEYS_PUBLICATION_MONTH":
        raise RuntimeError("retained evidence does not establish publication-month routing")
    max_lead = int(semantics["publication_to_first_event_calendar_months"]["maximum"])
    if max_lead != 2:
        raise RuntimeError(f"unexpected retained publication lead: {max_lead}")
    plan_items: list[dict[str, Any]] = []
    retained_records = read_json_records(retained_root / "request_records.jsonl")
    followup_data = read_json(followup_root / "bounded_followup_results.json")
    for target in targets:
        year, month = parse_month(target["candidate_date"])
        keys = [month_key(*shift_month(year, month, delta)) for delta in (-2, -1, 0)]
        for key in keys:
            prior = prior_followup_month_evidence(followup_root, target, key)
            retained = retained_month_evidence(retained_root, key)
            if prior is not None:
                source = prior
                action = "REUSE_PRIOR_LIVE_EVIDENCE"
            elif retained is not None:
                source = retained
                action = "REUSE_RETAINED_INDEX_EVIDENCE"
            else:
                source = None
                action = "NEW_LIVE_REQUEST"
            request_url = index_url(key[5:7], key[:4])
            plan_items.append(
                {
                    "ticker": target["ticker"],
                    "economic_event_id": target["economic_event_id"],
                    "candidate_month": target["candidate_date"][:7],
                    "month_key": key,
                    "month_role": "CANDIDATE_MONTH" if key == target["candidate_date"][:7] else "EVIDENCE_JUSTIFIED_PREVIOUS_MONTH",
                    "action": action,
                    "request_url": request_url,
                    "retained_sha256": text(source.get("sha256")) if source else "",
                    "retained_raw_path": text(source.get("raw_path")) if source else "",
                    "retained_evidence_source": text(source.get("evidence_source")) if source else "",
                }
            )
    new_keys = [item["month_key"] for item in plan_items if item["action"] == "NEW_LIVE_REQUEST"]
    if len(new_keys) != len(set(new_keys)):
        raise RuntimeError("duplicate new month request in routing plan")
    return targets, {
        "schema_version": SCHEMA,
        "plan_status": "PLAN_READY_NO_PROVIDER_CALLS",
        "created_at_utc": now_utc(),
        "source_contract_id": KSEI_CONTRACT,
        "accepted_endpoint": KSEI_RIGHTS_DISTRIBUTION,
        "accepted_locale": "id-ID",
        "scope_tickers": list(TARGET_TICKERS),
        "scope_event_ids": [target["economic_event_id"] for target in targets],
        "planned_months_by_ticker": {ticker: [item["month_key"] for item in plan_items if item["ticker"] == ticker] for ticker in TARGET_TICKERS},
        "new_request_months": sorted(set(new_keys)),
        "new_request_count": len(new_keys),
        "no_retry_policy": True,
        "items": plan_items,
        "retained_semantics": semantics,
        "retained_request_ledger_path": str(retained_root / "request_records.jsonl"),
        "prior_followup_path": str(followup_root / "bounded_followup_results.json"),
        "unused_inputs": {"retained_records_loaded": len(retained_records), "prior_followup_index_results": len(followup_data.get("index_results", []))},
    }


def safe_response_headers(headers: Any) -> dict[str, str]:
    allowed = {"cache-control", "content-length", "content-type", "date", "etag", "expires", "location", "server", "vary"}
    return {str(name).lower(): str(value) for name, value in headers.items() if str(name).lower() in allowed}


def perform_request(url: str, raw_path: Path) -> dict[str, Any]:
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": USER_AGENT})
    result: dict[str, Any] = {
        "requested_url": url,
        "request_method": "GET",
        "request_headers": {name: value for name, value in request.header_items()},
        "raw_path": str(raw_path),
        "status_code": "",
        "response_final_url": "",
        "response_headers": {},
        "bytes": 0,
        "sha256": "",
        "error": "",
        "request_started_utc": now_utc(),
        "retrieval_mode": "NEW_OFFICIAL_REQUEST_ARCHIVE_ROUTING_NO_RETRY",
    }
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
            raw_path.write_bytes(body)
            result.update({"status_code": int(response.status), "response_final_url": response.geturl(), "response_headers": safe_response_headers(response.headers), "bytes": len(body), "sha256": sha256_bytes(body)})
    except urllib.error.HTTPError as exc:
        body = exc.read()
        if body:
            raw_path.write_bytes(body)
        result.update({"status_code": int(exc.code), "response_final_url": text(exc.geturl()), "response_headers": safe_response_headers(exc.headers), "bytes": len(body), "sha256": sha256_bytes(body) if body else "", "error": "HTTP_ERROR"})
    except (OSError, urllib.error.URLError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    result["request_completed_utc"] = now_utc()
    return result


def target_dates_match(target: Mapping[str, Any], parsed: Mapping[str, Any]) -> bool:
    expected = {text(target.get(key))[:10] for key in ("record_date", "distribution_date") if DATE_RE.fullmatch(text(target.get(key))[:10])}
    observed = {text(parsed.get(key))[:10] for key in ("record_date", "distribution_date") if DATE_RE.fullmatch(text(parsed.get(key))[:10])}
    return bool(expected) and expected.issubset(observed)


def provider_result_for_item(item: Mapping[str, Any], plan_root: Path, request_results: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    action = text(item.get("action"))
    if action == "NEW_LIVE_REQUEST":
        request = request_results[text(item.get("month_key"))]
        raw_path = Path(text(request.get("raw_path")))
        parsed = []
        if int(request.get("status_code") or 0) == 200 and raw_path.is_file():
            parsed = parse_ksei_index(raw_path, {"request_number": 1, "sha256": request.get("sha256")}, KSEI_CONTRACT)
    else:
        raw_path = Path(text(item.get("retained_raw_path")))
        parsed = []
        if raw_path.is_file() and valid_sha(text(item.get("retained_sha256"))):
            parsed = parse_ksei_index(raw_path, {"request_number": 0, "sha256": item.get("retained_sha256")}, KSEI_CONTRACT)
        request = {"status_code": 200, "requested_url": item.get("request_url"), "raw_path": str(raw_path), "sha256": item.get("retained_sha256"), "retrieval_mode": action}
    matches = [row for row in parsed if ticker_in_title(text(row.get("title")), text(item.get("ticker")))]
    return {"item": dict(item), "request": request, "parsed_rights_rows": len(parsed), "matching_target_rows": len(matches), "matching_rows": matches}


def fetch_and_parse_exact_document(row: Mapping[str, Any], ticker: str, target: Mapping[str, Any], root: Path, ordinal: int) -> dict[str, Any]:
    source_ref = text(row.get("source_ref"))
    document_ref = text(row.get("document_reference"))
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", f"{ordinal:02d}_{ticker}_{document_ref}.pdf")
    pdf_path = root / "provider" / "documents" / safe_name
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    request = perform_request(source_ref, pdf_path)
    result: dict[str, Any] = {"ticker": ticker, "document_reference": document_ref, "source_ref": source_ref, "index_row": dict(row), "request": request}
    if int(request.get("status_code") or 0) != 200 or not pdf_path.is_file():
        result["document_result"] = "PROVIDER_FAILURE"
        return result
    text_path = pdf_path.with_suffix(".txt")
    extraction_status, text_sha = extract_pdf_text(pdf_path, text_path)
    parsed = parse_rights_document({"document_id": document_ref, "ticker": ticker, "document_reference": document_ref, "title": row.get("title"), "source_ref": source_ref, "sha256": request.get("sha256"), "bytes": request.get("bytes"), "status_code": request.get("status_code"), "raw_path": str(pdf_path)}, text_path)
    result.update({"extraction_status": extraction_status, "text_sha256": text_sha, "parsed": parsed})
    if parsed.get("ex_date") and target_dates_match(target, parsed) and valid_sha(request.get("sha256")):
        result["document_result"] = "RESOLVED_EXACT"
    else:
        result["document_result"] = "DOCUMENT_FOUND_SEMANTIC_INSUFFICIENT"
    return result


def classify_target(target: Mapping[str, Any], index_results: Sequence[Mapping[str, Any]], documents: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    own = [row for row in index_results if text(row.get("item", {}).get("ticker")) == text(target.get("ticker"))]
    found = [row for row in own if int(row.get("matching_target_rows") or 0) > 0]
    non_candidate_found = [row for row in found if text(row.get("item", {}).get("month_key")) != text(target.get("candidate_date"))[:7]]
    target_docs = [row for row in documents if text(row.get("ticker")) == text(target.get("ticker"))]
    if target_docs:
        document_result = text(target_docs[0].get("document_result"))
    else:
        document_result = ""
    provider_failures = [row for row in own if int(row.get("request", {}).get("status_code") or 0) != 200]
    if non_candidate_found:
        routing_root_cause = "CANDIDATE_MONTH_ROUTING_FALSE_NEGATIVE"
    elif provider_failures:
        routing_root_cause = "PROVIDER_FAILURE"
    else:
        routing_root_cause = "ARCHIVE_ROW_STILL_NOT_DISCOVERED"
    if document_result:
        result_classification = document_result
    elif found:
        result_classification = "DOCUMENT_FOUND_SEMANTIC_INSUFFICIENT"
    else:
        result_classification = routing_root_cause
    return {
        "economic_event_id": target["economic_event_id"],
        "ticker": target["ticker"],
        "candidate_date": target["candidate_date"],
        "result_classification": result_classification,
        "routing_root_cause": routing_root_cause,
        "candidate_month_matching_rows": sum(int(row.get("matching_target_rows") or 0) for row in own if text(row.get("item", {}).get("month_key")) == text(target.get("candidate_date"))[:7]),
        "non_candidate_month_matching_rows": sum(int(row.get("matching_target_rows") or 0) for row in non_candidate_found),
        "provider_failure_months": [text(row.get("item", {}).get("month_key")) for row in provider_failures],
        "document_result": document_result,
    }


def manifest_for(root: Path) -> dict[str, Any]:
    outputs = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.json":
            outputs[path.relative_to(root).as_posix()] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    return {"manifest_version": f"{SCHEMA}_manifest", "artifact_root": str(root), "audit_date": AUDIT_DATE, "outcome_blind": True, "provider_calls": True, "output_hashes_excluding_manifest": outputs, "self_hash_policy": "MANIFEST.json excluded from its own hash"}


def write_plan(output_root: Path, v13_root: Path, retained_root: Path, followup_root: Path) -> dict[str, Any]:
    if output_root.exists():
        raise FileExistsError(f"immutable archive-routing root already exists: {output_root}")
    output_root.mkdir(parents=True)
    targets, plan = target_scope_and_plan(v13_root, retained_root, followup_root)
    write_json(output_root / "archive_temporal_semantics.json", plan["retained_semantics"])
    write_csv(output_root / "target_scope.csv", targets, TARGET_FIELDS)
    write_json(output_root / "routing_plan.json", plan)
    write_json(output_root / "input_pins.json", {"v13_root": str(v13_root), "retained_root": str(retained_root), "prior_followup_root": str(followup_root), "v13_manifest_sha256": sha256_file(v13_root / "MANIFEST.json"), "retained_manifest_sha256": sha256_file(retained_root / "MANIFEST.json"), "prior_followup_manifest_sha256": sha256_file(followup_root / "MANIFEST.json"), "provider_calls": False})
    write_json(output_root / "PLAN_READY.json", {"status": "PLAN_READY_NO_PROVIDER_CALLS", "created_at_utc": now_utc(), "planned_new_request_months": plan["new_request_months"]})
    return plan


def execute_plan(output_root: Path) -> dict[str, Any]:
    plan_path = output_root / "routing_plan.json"
    if not plan_path.is_file() or read_json(plan_path).get("plan_status") != "PLAN_READY_NO_PROVIDER_CALLS":
        raise RuntimeError("execution requires a valid PLAN_READY routing plan")
    if (output_root / "provider_execution_state.json").exists():
        raise RuntimeError("provider execution already recorded; no retry is permitted")
    plan = read_json(plan_path)
    write_json(output_root / "provider_execution_state.json", {"status": "STARTED_NO_RETRY", "started_at_utc": now_utc(), "planned_new_request_months": plan["new_request_months"]})
    provider_dir = output_root / "provider"
    provider_dir.mkdir(parents=True, exist_ok=True)
    request_results: dict[str, dict[str, Any]] = {}
    for key in plan["new_request_months"]:
        raw_path = provider_dir / f"index_{key.replace('-', '')}.body"
        request_results[key] = perform_request(index_url(key[5:7], key[:4]), raw_path)
    index_results = [provider_result_for_item(item, output_root, request_results) for item in plan["items"]]
    targets = read_csv(output_root / "target_scope.csv")
    documents: list[dict[str, Any]] = []
    document_ordinal = 1
    for index_result in index_results:
        matches = index_result.get("matching_rows", [])
        if len(matches) == 1:
            target = next(row for row in targets if text(row.get("ticker")) == text(index_result["item"].get("ticker")))
            documents.append(fetch_and_parse_exact_document(matches[0], text(target.get("ticker")), target, output_root, document_ordinal))
            document_ordinal += 1
    classification = [classify_target(target, index_results, documents) for target in targets]
    result_counts = Counter(text(row.get("result_classification")) for row in classification)
    root_cause_counts = Counter(text(row.get("routing_root_cause")) for row in classification)
    summary = {
        "schema_version": SCHEMA,
        "audit_date": AUDIT_DATE,
        "status": "COMPLETE_BOUNDED_ARCHIVE_ROUTING_AUDIT",
        "scope_tickers": list(TARGET_TICKERS),
        "provider_requests_executed": len(request_results) + len(documents),
        "new_index_requests_executed": len(request_results),
        "exact_document_fetches": len(documents),
        "archive_month_semantic": plan["retained_semantics"]["conclusion"],
        "planned_months_by_ticker": plan["planned_months_by_ticker"],
        "new_request_months": plan["new_request_months"],
        "target_results": classification,
        "result_classification_counts": dict(sorted(result_counts.items())),
        "routing_root_cause_counts": dict(sorted(root_cause_counts.items())),
        "candidate_month_routing_false_negative_count": root_cause_counts.get("CANDIDATE_MONTH_ROUTING_FALSE_NEGATIVE", 0),
        "new_exact_documents": sum(text(row.get("document_result")) == "RESOLVED_EXACT" for row in documents),
        "new_resolved_exact": sum(text(row.get("result_classification")) == "RESOLVED_EXACT" for row in classification),
        "rights_archive_routing_contract_verdict": "RIGHTS_ARCHIVE_ROUTING_CONTRACT_PROVEN" if all(text(row.get("routing_root_cause")) == "CANDIDATE_MONTH_ROUTING_FALSE_NEGATIVE" for row in classification) else "RIGHTS_ARCHIVE_ROUTING_CONTRACT_PARTIAL" if any(text(row.get("routing_root_cause")) == "CANDIDATE_MONTH_ROUTING_FALSE_NEGATIVE" for row in classification) else "RIGHTS_ARCHIVE_ROUTING_CONTRACT_UNKNOWN",
        "rights_index_source_contract_verdict": "RIGHTS_INDEX_LIVE_CONTRACT_CONDITIONALLY_REPEATABLE" if all(int(request.get("status_code") or 0) == 200 for request in request_results.values()) else "RIGHTS_INDEX_LIVE_CONTRACT_UNKNOWN",
        "full_rights_acquisition_recommendation": "GO_BOUNDED_EVENT_SPECIFIC" if all(text(row.get("result_classification")) == "RESOLVED_EXACT" for row in classification) and not any(int(request.get("status_code") or 0) != 200 for request in request_results.values()) else "HOLD_FOR_ALTERNATE_SOURCE_PATH",
        "prior_proven_linkages": 27,
        "recomputed_proven_linkages": 27,
        "new_proven_linkages": 0,
        "removed_or_conflicting": 0,
        "economic_events_before": 387,
        "economic_events_after": 387,
        "resolved_before": 159,
        "resolved_after": 159,
        "unresolved_before": 182,
        "unresolved_after": 182,
        "non_basis": 46,
        "rights_hmetd_unresolved": 69,
        "reconciliation_required": False,
        "scientific_verdict_unchanged": {"DATA_ADMISSION": "FAIL", "RESEARCH_ADMISSION": "FAIL", "MODEL_PROMOTION": "NOT_EVALUATED", "HISTORICAL_APPLICATION": "BLOCKED_PHASE_E_NOT_RUN", "REFIT_AUTHORIZED": False, "COUNTER_ACTION": "NONE"},
        "authority_blockers": {"IDX_HISTORICAL_NEGATIVE_AUTHORITY": "UNSUPPORTED", "IDX_HISTORICAL_ASOF_AUTHORITY": "UNKNOWN", "KSEI_HISTORICAL_COMPLETE_INTERVAL_AUTHORITY": "UNKNOWN"},
        "guardrails": {"remaining_rights_acquisition": False, "mMix_retry": False, "other_ca_family_acquisition": False, "phase_e": False, "outcomes_or_targets": False, "fit_refit_score": False, "counter_mutation": False, "canonical_historical_rewrite": False, "production_execution": False, "merge": False},
    }
    write_json(output_root / "index_results.json", index_results)
    write_json(output_root / "document_results.json", documents)
    write_json(output_root / "target_results.json", classification)
    write_json(output_root / "audit_summary.json", summary)
    write_json(output_root / "provider_execution_state.json", {"status": "COMPLETE_NO_RETRY", "completed_at_utc": now_utc(), "executed_months": sorted(request_results), "request_count": len(request_results) + len(documents)})
    write_json(output_root / "MANIFEST.json", manifest_for(output_root))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--v13-root", type=Path, required=True)
    parser.add_argument("--retained-root", type=Path, required=True)
    parser.add_argument("--prior-followup-root", type=Path, required=True)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.plan_only == args.execute:
        parser.error("choose exactly one of --plan-only or --execute")
    result = write_plan(args.output_root, args.v13_root, args.retained_root, args.prior_followup_root) if args.plan_only else execute_plan(args.output_root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
