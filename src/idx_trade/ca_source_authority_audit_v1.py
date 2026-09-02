"""Outcome-blind audit of retained corporate-action source authority.

This module intentionally audits retained/local evidence only.  It does not
call a provider, read protected outcomes, alter canonical data, or authorize
Phase-E.  The generated tables distinguish source bytes from derived audit
artifacts so that a historical summary cannot become a new authority claim.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


AUDIT_SCHEMA = "ca_source_authority_audit_v1"
SOURCE_IMPLEMENTATION_HEAD = "a4e644b655fb7b7980b59c008b7d3dd26f364371"
R31_ROOT_NAME = "idx-ca-aware-feature-basis-remediation-20260828-r3_1-final"
AUDIT_ROOT_NAME = "idx-ca-source-authority-audit-20260828-v1"
FROZEN_FAMILIES = (
    "STOCK_SPLIT",
    "REVERSE_SPLIT",
    "RIGHTS_HMETD",
    "STOCK_DIVIDEND",
    "BONUS_SHARES",
    "MANDATORY_CONVERSION",
    "VOLUNTARY_CONVERSION",
    "CAPITAL_RESTRUCTURING",
)

SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value.strip()))


def canonical_set_hash(values: Iterable[str]) -> str:
    payload = "\n".join(sorted({str(value).strip() for value in values if str(value).strip()}))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def source_bound_certified(row: Mapping[str, Any]) -> bool:
    """Return true only for a fully provenance-bound transition assertion."""

    certified_state = str(row.get("certified_state", "")).strip().upper()
    accepted_status = str(row.get("accepted_source_bound_status", "")).strip().upper()
    source_ref = str(row.get("source_ref", "")).strip()
    lower_bound = str(row.get("transition_lower_bound_date", "")).strip()
    evidence_sha = str(row.get("evidence_sha256", "")).strip()
    if certified_state not in {"CERTIFIED", "TRUE", "PASS"}:
        return False
    if accepted_status not in {"ACCEPTED", "SOURCE_BOUND", "CERTIFIED"}:
        return False
    if not source_ref or not valid_sha256(evidence_sha):
        return False
    try:
        date.fromisoformat(lower_bound)
    except (TypeError, ValueError):
        return False
    return True


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
    return rows


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: "" if row.get(key) is None else row.get(key) for key in fieldnames})


def _dump_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _utc_mtime(path: Path) -> str:
    return __import__("datetime").datetime.fromtimestamp(path.stat().st_mtime, tz=__import__("datetime").timezone.utc).isoformat().replace("+00:00", "Z")


def _relative_or_absolute(path_value: str | None, root: Path) -> Path | None:
    if not path_value:
        return None
    path = Path(path_value)
    if path.is_absolute():
        return path
    return root / path


def _pin_row(
    *,
    pin_id: str,
    path: Path,
    artifact_class: str,
    source_contract: str,
    source_ref: str = "",
    source_url: str = "",
    capture_timestamp: str = "UNKNOWN",
    ticker_population: str = "UNKNOWN",
    date_time_scope: str = "UNKNOWN",
    event_family: str = "UNKNOWN",
    polarity: str = "UNKNOWN",
    publication_semantics: str = "UNKNOWN",
    transition_semantics: str = "UNKNOWN",
    authority_status: str = "RETAINED_LOCAL_EVIDENCE",
    notes: str = "",
    recorded_sha256: str = "",
) -> dict[str, Any]:
    exists = path.is_file()
    actual_sha = sha256_file(path) if exists else ""
    mismatch = bool(recorded_sha256 and exists and recorded_sha256.lower() != actual_sha.lower())
    return {
        "pin_id": pin_id,
        "artifact_class": artifact_class,
        "path": str(path),
        "exists": str(exists).lower(),
        "sha256": actual_sha,
        "recorded_sha256": recorded_sha256,
        "sha256_matches_record": str(not mismatch).lower() if recorded_sha256 else "NOT_RECORDED",
        "bytes": path.stat().st_size if exists else "",
        "filesystem_mtime_utc": _utc_mtime(path) if exists else "",
        "capture_retrieval_timestamp_utc": capture_timestamp,
        "source_contract": source_contract,
        "source_contract_id": "UNSPECIFIED_IN_RETAINED_SOURCE" if source_contract else "",
        "source_ref": source_ref,
        "source_url": source_url,
        "ticker_population": ticker_population,
        "date_time_scope": date_time_scope,
        "event_family": event_family,
        "evidence_polarity": polarity,
        "publication_knowledge_asof": publication_semantics,
        "transition_semantics": transition_semantics,
        "authority_status": authority_status,
        "notes": notes,
    }


def _add_static_pin(rows: list[dict[str, Any]], root: Path, spec: Mapping[str, Any]) -> None:
    path = root / str(spec["relative_path"])
    rows.append(_pin_row(path=path, **{key: value for key, value in spec.items() if key != "relative_path"}))


def _add_request_pins(
    rows: list[dict[str, Any]],
    requests: Sequence[Mapping[str, Any]],
    root: Path,
    *,
    prefix: str,
    artifact_class: str,
    source_contract: str,
    ticker_population: str,
    date_time_scope: str,
    event_family: str,
    polarity: str,
    transition_semantics: str,
    notes: str,
) -> None:
    for index, request in enumerate(requests, start=1):
        raw_path = _relative_or_absolute(request.get("path"), root)
        path = raw_path
        if path is not None and not path.exists():
            # Schedule parse records retain the logical capture stem while the
            # adjacent downloader bytes carry an attempt/extension suffix.
            candidates = sorted(path.parent.glob(path.name + "_attempt_*") )
            recorded_sha = str(request.get("sha256") or "").lower()
            matching = next((candidate for candidate in candidates if recorded_sha and candidate.is_file() and sha256_file(candidate) == recorded_sha), None)
            path = matching or next((candidate for candidate in candidates if candidate.is_file()), path)
        if path is None:
            path = root / f"MISSING_REQUEST_{index:04d}"
        source_url = str(request.get("final_url") or request.get("url") or request.get("requested_url") or "")
        ticker = str(request.get("ticker") or "")
        population = f"{ticker_population}; request_ticker={ticker}" if ticker else ticker_population
        rows.append(
            _pin_row(
                pin_id=f"{prefix}:{index:04d}",
                path=path,
                artifact_class=artifact_class,
                source_contract=source_contract,
                source_ref=source_url,
                source_url=source_url,
                capture_timestamp=str(request.get("accessed_at_utc") or "UNKNOWN"),
                ticker_population=population,
                date_time_scope=date_time_scope,
                event_family=event_family,
                polarity=polarity,
                publication_semantics="retrieval timestamp only; not historical as-of",
                transition_semantics=transition_semantics,
                notes=notes + ("; logical request path resolved to suffixed capture byte" if raw_path is not None and path != raw_path else ""),
                recorded_sha256=str(request.get("sha256") or ""),
            )
        )


def _load_idx_rows(pit_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((pit_root / "raw").glob("idx_issued_all_*.json")):
        value = _read_json(path)
        data = value.get("data", []) if isinstance(value, dict) else value
        if isinstance(data, list):
            rows.extend(row for row in data if isinstance(row, dict))
    return rows


def _idx_family(action: str) -> str:
    return {
        "stockSplit": "STOCK_SPLIT",
        "reverseStock": "REVERSE_SPLIT",
        "hmetd": "RIGHTS_HMETD",
        "Dividen Saham": "STOCK_DIVIDEND",
        "dividenSaham": "STOCK_DIVIDEND",
        "sahamBonus": "BONUS_SHARES",
        "obligasiWajibKonversi": "MANDATORY_CONVERSION",
        "kurangModal": "CAPITAL_RESTRUCTURING",
        "gabungUsaha": "MERGER",
        "konversiSaham": "VOLUNTARY_CONVERSION",
    }.get(action, "OTHER_ISSUED_HISTORY")


def _ksei_family(value: str) -> str:
    return {
        "Right Distribution": "RIGHTS_HMETD",
        "Stock Dividend": "STOCK_DIVIDEND",
        "Mandatory Conversion": "MANDATORY_CONVERSION",
        "Voluntary Conversion": "VOLUNTARY_CONVERSION",
    }.get(value, "OTHER_KSEI_HISTORY")


def _source_inventory(project_root: Path, app_tickers: set[str], closure_start: str, closure_end: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    root = project_root
    ksei = root / "idx-v4-ksei-ca-history-census-20260817-v1"
    pit = root / "idx-corporate-action-pit-source-audit-20260814-v1-final"
    schedule = root / "idx-v4-ca-schedule-evidence-20260818-v3"
    rows: list[dict[str, Any]] = []

    static_specs = [
        {"pin_id": "KSEI:MANIFEST", "relative_path": "idx-v4-ksei-ca-history-census-20260817-v1/MANIFEST.json", "artifact_class": "SOURCE_CAPTURE_MANIFEST", "source_contract": "KSEI_PUBLIC_REGISTERED_SECURITY_HISTORY", "ticker_population": "610 captured ticker requests", "date_time_scope": "history rows source-native dates; capture 2026-08-17", "event_family": "MULTI_FAMILY_SOURCE_NATIVE", "polarity": "HISTORY_ROWS_NOT_NO_EVENT", "publication_semantics": "manifest retrieval metadata", "transition_semantics": "no generic market transition", "notes": "raw capture manifest; source contract id not explicitly supplied"},
        {"pin_id": "KSEI:SUMMARY", "relative_path": "idx-v4-ksei-ca-history-census-20260817-v1/summary.json", "artifact_class": "DERIVED_AUDIT", "source_contract": "KSEI_PUBLIC_REGISTERED_SECURITY_HISTORY", "ticker_population": "610 captured ticker requests", "date_time_scope": "2001-04-10—2026-09-15 observed source-native fields", "event_family": "MULTI_FAMILY_SOURCE_NATIVE", "polarity": "HISTORY_ROWS_NOT_NO_EVENT", "publication_semantics": "retrieval timestamp only", "transition_semantics": "record/distribution/cum dates not generic transition", "authority_status": "DERIVED_SUMMARY_NOT_AUTHORITY", "notes": "summary does not certify 716 or date-level as-of"},
        {"pin_id": "KSEI:COVERAGE", "relative_path": "idx-v4-ksei-ca-history-census-20260817-v1/ticker_coverage.csv", "artifact_class": "DERIVED_AUDIT", "source_contract": "KSEI_PUBLIC_REGISTERED_SECURITY_HISTORY", "ticker_population": "610 rows; 567 certified, 43 unresolved", "date_time_scope": "per-ticker observed event-date extrema only", "event_family": "MULTI_FAMILY_SOURCE_NATIVE", "polarity": "HISTORY_ROWS_NOT_NO_EVENT", "publication_semantics": "retrieval timestamp only", "transition_semantics": "no generic market transition", "authority_status": "DERIVED_COVERAGE_NOT_FULL_AUTHORITY", "notes": "event history presence is not per-session no-event coverage"},
        {"pin_id": "IDX:PIT_MANIFEST", "relative_path": "idx-corporate-action-pit-source-audit-20260814-v1-final/MANIFEST.json", "artifact_class": "SOURCE_CAPTURE_MANIFEST", "source_contract": "IDX_ISSUED_HISTORY_AND_OFFICIAL_ANNOUNCEMENTS", "ticker_population": "683 issued-history action-bearing tickers; selected announcement candidates", "date_time_scope": "2018-01-05—2026-08-13 issued-history observations", "event_family": "MULTI_FAMILY_CANDIDATE_SOURCE", "polarity": "POSITIVE_CANDIDATE_ONLY", "publication_semantics": "capture timestamps per request", "transition_semantics": "TanggalPencatatan is not generic market transition", "notes": "87 of 88 request paths present; one failed request has no source bytes"},
        {"pin_id": "IDX:PIT_SUMMARY", "relative_path": "idx-corporate-action-pit-source-audit-20260814-v1-final/summary.json", "artifact_class": "DERIVED_AUDIT", "source_contract": "IDX_ISSUED_HISTORY_AND_OFFICIAL_ANNOUNCEMENTS", "ticker_population": "selected candidate scope", "date_time_scope": "2018-01-01—2026-08-14 request scope", "event_family": "MULTI_FAMILY_CANDIDATE_SOURCE", "polarity": "POSITIVE_CANDIDATE_ONLY", "publication_semantics": "capture timestamps only", "transition_semantics": "no generic market transition", "authority_status": "DERIVED_SUMMARY_NOT_AUTHORITY", "notes": "source rows and attachment hashes are retained, but broad no-event authority is absent"},
        {"pin_id": "IDX:DATA_GATE_ACTIONS", "relative_path": "idx-trade-data-gate-20260808v/corporate_actions/idx_actions.csv", "artifact_class": "DERIVED_AUDIT", "source_contract": "IDX_LISTING_ACTIVITY_GET_ISSUED_HISTORY", "ticker_population": "35 distinct tickers; 38 positive stock-split rows", "date_time_scope": "2023-01-01—2026-08-08", "event_family": "STOCK_SPLIT", "polarity": "POSITIVE_EVENT_ONLY", "publication_semantics": "unknown; local artifact mtime only", "transition_semantics": "source field labelled effective_date but source contract is listing activity", "authority_status": "POSITIVE_CANDIDATE_ONLY", "notes": "not a market-wide no-event census"},
        {"pin_id": "IDX:DATA_GATE_ACTION_SUMMARY", "relative_path": "idx-trade-data-gate-20260808v/corporate_actions/idx_actions_summary.json", "artifact_class": "DERIVED_AUDIT", "source_contract": "IDX_LISTING_ACTIVITY_GET_ISSUED_HISTORY", "ticker_population": "35 distinct tickers", "date_time_scope": "2023-01-01—2026-08-08", "event_family": "STOCK_SPLIT", "polarity": "POSITIVE_EVENT_ONLY", "publication_semantics": "unknown", "transition_semantics": "no generic market transition", "authority_status": "DERIVED_SUMMARY_NOT_AUTHORITY", "notes": "source URL is retained but no capture manifest is attached"},
        {"pin_id": "IDX:OFFICIAL_SPLIT_504", "relative_path": "idx-trade-data-gate-20260808v/corporate_actions/official_idx_split_reverse_actions_504.csv", "artifact_class": "DERIVED_AUDIT", "source_contract": "IDX_LISTING_ACTIVITY_GET_ISSUED_HISTORY", "ticker_population": "17 distinct tickers; 18 positive rows", "date_time_scope": "2022-01-12—2025-10-22", "event_family": "STOCK_SPLIT", "polarity": "POSITIVE_EVENT_ONLY", "publication_semantics": "unknown", "transition_semantics": "no generic market transition", "authority_status": "POSITIVE_CANDIDATE_ONLY", "notes": "official-source-labelled derivative; no per-session as-of"},
        {"pin_id": "SCHEDULE:MANIFEST", "relative_path": "idx-v4-ca-schedule-evidence-20260818-v3/MANIFEST.json", "artifact_class": "SOURCE_CAPTURE_MANIFEST", "source_contract": "KSEI_PUBLIC_CORPORATE_ACTION_SCHEDULE", "ticker_population": "75 candidate-event tickers; one exact linked row", "date_time_scope": "targeted schedule index/document retrieval", "event_family": "RIGHTS_AND_CONVERSION_CANDIDATES", "polarity": "POSITIVE_CANDIDATE_ONLY", "publication_semantics": "capture timestamps per request", "transition_semantics": "exact source-native schedule only when explicitly parsed", "notes": "94 of 95 required event links unresolved"},
        {"pin_id": "SCHEDULE:EVIDENCE", "relative_path": "idx-v4-ca-schedule-evidence-20260818-v3/schedule_evidence.csv", "artifact_class": "DERIVED_AUDIT", "source_contract": "KSEI_PUBLIC_CORPORATE_ACTION_SCHEDULE", "ticker_population": "1 exact linked ticker; 74 other candidate tickers unresolved", "date_time_scope": "one exact document date/transition row", "event_family": "NON_STRUCTURAL_MIXED_DIVIDEND", "polarity": "POSITIVE_EVENT_ONLY", "publication_semantics": "document date plus capture metadata", "transition_semantics": "one explicit regular-market ex-date; not structural-family coverage", "authority_status": "PARTIAL_EXACT_EVENT_ONLY", "notes": "cannot certify full application/closure scope"},
        {"pin_id": "CONTINUITY:EVENT_EVIDENCE", "relative_path": "idx-v4-corporate-action-continuity-gate-20260817-v3/event_family_evidence.csv", "artifact_class": "DERIVED_AUDIT", "source_contract": "COMPOSITE_KSEI_IDX_EVENT_EVIDENCE", "ticker_population": "strict 26 event rows", "date_time_scope": "selected strict event candidates", "event_family": "FROZEN_STRUCTURAL_FAMILIES_PARTIAL", "polarity": "POSITIVE_CANDIDATE_ONLY", "publication_semantics": "source-specific publication fields where present", "transition_semantics": "all strict rows unresolved", "authority_status": "DERIVED_EVENT_CENSUS_NOT_AUTHORITY", "notes": "source rows are not a full family/no-event census"},
        {"pin_id": "EVENT_WINDOW:SEMANTICS", "relative_path": "idx-v4-ca-event-window-final-20260818-v3/event_semantics_audit.csv", "artifact_class": "DERIVED_AUDIT", "source_contract": "COMPOSITE_KSEI_IDX_EVENT_WINDOW", "ticker_population": "102 event tickers; 136 relevant rows", "date_time_scope": "600 frozen validation dates", "event_family": "MULTI_FAMILY_CANDIDATE_SOURCE", "polarity": "POSITIVE_CANDIDATE_ONLY", "publication_semantics": "source-specific; not full as-of", "transition_semantics": "prior exact labels require source-linked revalidation", "authority_status": "DERIVED_SEMANTICS_NOT_AUTHORITY", "notes": "rows lack source_sha256 in the retained semantic audit"},
        {"pin_id": "R31:STRUCTURAL_26", "relative_path": f"{R31_ROOT_NAME}/r3_structural_ca_event_scope.csv", "artifact_class": "DERIVED_AUDIT", "source_contract": "R3_1_STRICT_STRUCTURAL_EVENT_CENSUS", "ticker_population": "26 strict event rows", "date_time_scope": "candidate dates through closure end 2026-07-17", "event_family": "FROZEN_STRUCTURAL_FAMILIES_PARTIAL", "polarity": "POSITIVE_CANDIDATE_ONLY", "publication_semantics": "source-specific published_at where present", "transition_semantics": "candidate/source dates do not certify market transition", "authority_status": "CURRENT_AUDIT_INPUT_NOT_SOURCE_AUTHORITY", "notes": "all 26 remain unresolved under current source semantics"},
        {"pin_id": "INTEGRITY:CA_CENSUS", "relative_path": "idx-ca-feature-basis-integrity-audit-20260826-v4/ca_event_census.csv", "artifact_class": "DERIVED_AUDIT", "source_contract": "CA_FEATURE_BASIS_INTEGRITY_AUDIT", "ticker_population": "26 evidence rows", "date_time_scope": "selected strict event candidates", "event_family": "FROZEN_STRUCTURAL_FAMILIES_PARTIAL", "polarity": "POSITIVE_CANDIDATE_ONLY", "publication_semantics": "source-specific", "transition_semantics": "transition unresolved", "authority_status": "IDENTITY_ONLY_AUDIT_EVIDENCE", "notes": "used for event identity reconciliation; not a source-family authority"},
        {"pin_id": "IDX:SOURCE_CONTRACT_DOC", "relative_path": "idx-bei-forward-ca-provider/python/API_VERIFICATION_SPEC.md", "artifact_class": "SOURCE_CONTRACT_DOCUMENTATION", "source_contract": "IDX_ISSUED_HISTORY_ENDPOINT_DOCUMENTATION", "ticker_population": "not a capture", "date_time_scope": "documentation tested August 2026", "event_family": "15 endpoint categories documented", "polarity": "CONTRACT_DOCUMENTATION_ONLY", "publication_semantics": "documentation timestamp not source as-of", "transition_semantics": "TanggalPencatatan is source field; no universal transition claim", "authority_status": "CONTRACT_DOCUMENTATION_NO_RETAINED_CAPTURE", "notes": "no local source payload in this repository"},
        {"pin_id": "IDX:SOURCE_SCRAPER", "relative_path": "idx-bei-forward-ca-provider/python/src/idx/scrapers/corporate.py", "artifact_class": "SOURCE_CONTRACT_DOCUMENTATION", "source_contract": "IDX_ISSUED_HISTORY_ENDPOINT_CLIENT", "ticker_population": "not a capture", "date_time_scope": "all endpoint categories requested without historical as-of contract", "event_family": "15 endpoint categories", "polarity": "CONTRACT_DOCUMENTATION_ONLY", "publication_semantics": "none", "transition_semantics": "no market transition contract", "authority_status": "IMPLEMENTATION_REFERENCE_NO_RETAINED_CAPTURE", "notes": "not executed by this audit"},
    ]
    for spec in static_specs:
        _add_static_pin(rows, root, spec)

    ksei_requests = _read_jsonl(ksei / "request_records.jsonl")
    _add_request_pins(
        rows, ksei_requests, ksei, prefix="KSEI:RAW", artifact_class="SOURCE_BYTES",
        source_contract="KSEI_PUBLIC_REGISTERED_SECURITY_HISTORY", ticker_population="610 captured ticker requests",
        date_time_scope="source-native event history; no per-session no-event", event_family="MULTI_FAMILY_SOURCE_NATIVE",
        polarity="HISTORY_ROWS_NOT_NO_EVENT", transition_semantics="record/distribution/cum dates not generic market transition",
        notes="request-record hash and local bytes are checked; retrieval timestamp is not historical as-of",
    )
    pit_manifest = _read_json(pit / "MANIFEST.json")
    _add_request_pins(
        rows, pit_manifest.get("requests", []), pit, prefix="IDX:PIT_RAW", artifact_class="SOURCE_BYTES",
        source_contract="IDX_ISSUED_HISTORY_AND_OFFICIAL_ANNOUNCEMENTS", ticker_population="selected source request scope",
        date_time_scope="2018-01-01—2026-08-14 request scope", event_family="MULTI_FAMILY_CANDIDATE_SOURCE",
        polarity="POSITIVE_CANDIDATE_ONLY", transition_semantics="TanggalPencatatan/announcement dates are not generic transition",
        notes="retained bytes are source-bound when present; absence is not no-event evidence",
    )
    schedule_requests = _read_jsonl(schedule / "request_records.jsonl")
    _add_request_pins(
        rows, schedule_requests, schedule, prefix="SCHEDULE:RAW", artifact_class="SOURCE_BYTES",
        source_contract="KSEI_PUBLIC_CORPORATE_ACTION_SCHEDULE", ticker_population="75 candidate-event tickers",
        date_time_scope="targeted schedule index/document request scope", event_family="RIGHTS_AND_CONVERSION_CANDIDATES",
        polarity="POSITIVE_CANDIDATE_ONLY", transition_semantics="only an explicitly parsed schedule transition can bound a transition",
        notes="schedule captures are targeted, not a full 716-ticker historical no-event census",
    )
    return rows, {"ksei_requests": len(ksei_requests), "pit_requests": len(pit_manifest.get("requests", [])), "schedule_requests": len(schedule_requests), "app_ticker_hash": canonical_set_hash(app_tickers), "closure_start": closure_start, "closure_end": closure_end}


def _population_reconciliation(project_root: Path, app_tickers: set[str], fit_tickers: set[str], closure_tickers: set[str]) -> list[dict[str, Any]]:
    ksei_rows = _read_csv(project_root / "idx-v4-ksei-ca-history-census-20260817-v1" / "ticker_coverage.csv")
    ksei = {row["ticker"].strip() for row in ksei_rows if row.get("ticker")}
    ksei_certified = {row["ticker"].strip() for row in ksei_rows if row.get("ticker") and row.get("coverage_certified", "").lower() == "true"}
    ksei_unresolved = ksei - ksei_certified
    idx_rows = _load_idx_rows(project_root / "idx-corporate-action-pit-source-audit-20260814-v1-final")
    idx = {str(row.get("KodeEmiten", "")).strip() for row in idx_rows if str(row.get("KodeEmiten", "")).strip()}
    data_gate_rows = _read_csv(project_root / "idx-trade-data-gate-20260808v" / "corporate_actions" / "idx_actions.csv")
    data_gate = {row["ticker"].strip() for row in data_gate_rows if row.get("ticker")}
    schedule_rows = _read_csv(project_root / "idx-v4-ca-schedule-evidence-20260818-v3" / "event_schedule_linkage_audit.csv")
    schedule = {row["ticker"].strip() for row in schedule_rows if row.get("ticker")}
    conflicts = {"ISAT", "MEGA", "SCMA"}

    populations = [("FINAL_FIT", fit_tickers), ("CROSS_SECTION_APPLICATION", app_tickers), ("BACKWARD_DEPENDENCY_CLOSURE", closure_tickers)]
    sources = [
        ("KSEI_REGISTERED_SECURITY_HISTORY", ksei, ksei_certified, ksei_unresolved, "TICKER_HISTORY_PRESENT_NOT_NO_EVENT", "KSEI_PUBLIC_REGISTERED_SECURITY_HISTORY"),
        ("IDX_ISSUED_HISTORY_ALL", idx, set(), set(), "POSITIVE_ACTION_ROWS_ONLY", "IDX_LISTING_ACTIVITY_GET_ISSUED_HISTORY"),
        ("IDX_DATA_GATE_SPLIT_ARTIFACT", data_gate, set(), set(), "POSITIVE_STOCK_SPLIT_ROWS_ONLY", "IDX_LISTING_ACTIVITY_GET_ISSUED_HISTORY"),
        ("KSEI_TARGETED_SCHEDULE_LINKAGE", schedule, set(), set(), "TARGETED_CANDIDATE_DOCUMENTS_ONLY", "KSEI_PUBLIC_CORPORATE_ACTION_SCHEDULE"),
    ]
    output: list[dict[str, Any]] = []
    for population_name, population in populations:
        for source_name, covered, certified, unresolved, coverage_semantics, contract in sources:
            observed = population & covered
            source_unresolved = population & unresolved
            absent = population - covered
            source_conflicts = population & conflicts if source_name in {"KSEI_REGISTERED_SECURITY_HISTORY", "IDX_ISSUED_HISTORY_ALL"} else set()
            output.append({
                "population_scope": population_name,
                "population_tickers": len(population),
                "population_ticker_set_sha256": canonical_set_hash(population),
                "source_name": source_name,
                "source_contract": contract,
                "covered_ticker_count": len(observed),
                "covered_ticker_set_sha256": canonical_set_hash(observed),
                "covered_tickers": ";".join(sorted(observed)),
                "certified_ticker_count": len(population & certified),
                "certified_ticker_set_sha256": canonical_set_hash(population & certified),
                "unresolved_ticker_count": len(source_unresolved),
                "unresolved_ticker_set_sha256": canonical_set_hash(source_unresolved),
                "unresolved_tickers": ";".join(sorted(source_unresolved)),
                "absent_ticker_count": len(absent),
                "absent_ticker_set_sha256": canonical_set_hash(absent),
                "absent_tickers": ";".join(sorted(absent)),
                "conflicting_ticker_count": len(source_conflicts),
                "conflicting_tickers": ";".join(sorted(source_conflicts)),
                "coverage_semantics": coverage_semantics,
                "verdict": "UNKNOWN_NOT_FULL_SOURCE_AUTHORITY" if source_name != "KSEI_REGISTERED_SECURITY_HISTORY" else "FAIL_716_VS_610_OR_UNKNOWN_DATE_ATTESTATION" if population_name != "FINAL_FIT" else "FAIL_629_VS_610_OR_UNKNOWN_DATE_ATTESTATION",
                "notes": "absence from a positive-event artifact never proves no event; identity containment is separate from source certification",
            })
    return output


def _family_authority(project_root: Path, app_tickers: set[str], closure_tickers: set[str]) -> list[dict[str, Any]]:
    ksei_events = _read_jsonl(project_root / "idx-v4-ksei-ca-history-census-20260817-v1" / "ksei_ca_history.jsonl")
    idx_events = _load_idx_rows(project_root / "idx-corporate-action-pit-source-audit-20260814-v1-final")
    family_rows: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for row in ksei_events:
        family_rows[_ksei_family(str(row.get("event_family_source", "")))].append(("KSEI_REGISTERED_SECURITY_HISTORY", str(row.get("ticker", ""))))
    for row in idx_events:
        family_rows[_idx_family(str(row.get("JenisTindakan", "")))].append(("IDX_ISSUED_HISTORY", str(row.get("KodeEmiten", ""))))
    conflicts = {"ISAT", "MEGA", "SCMA"}
    results: list[dict[str, Any]] = []
    for family in (*FROZEN_FAMILIES, "MERGER"):
        entries = family_rows.get(family, [])
        source_names = sorted({entry[0] for entry in entries})
        tickers = {entry[1] for entry in entries if entry[1]}
        family_conflicts = sorted(tickers & conflicts)
        if family == "MERGER":
            mapping = "UNKNOWN_NOT_PROVEN_EQUIVALENT_TO_CAPITAL_RESTRUCTURING"
        else:
            mapping = family
        positive = "PARTIAL_POSITIVE_EVENT_IDENTIFICATION" if entries else "NONE_RETAINED"
        results.append({
            "structural_family": family,
            "source_family_mapping": mapping,
            "source_contracts_observed": ";".join(source_names),
            "source_contract_id": "UNSPECIFIED_IN_RETAINED_SOURCE",
            "positive_event_authority": positive,
            "no_event_coverage_authority": "NONE",
            "transition_date_authority": "NONE_FULL_SOURCE_DEFINED_MARKET_TRANSITION",
            "population_scope": f"{len(tickers)} event-bearing source tickers; target application={len(app_tickers)}, closure={len(closure_tickers)}",
            "temporal_scope": "event-native dates only; no complete per-session interval authority",
            "as_of_semantics": "retrieval/capture timestamps only; no valid historical per-session no-event as-of",
            "observed_event_row_count": len(entries),
            "observed_event_ticker_count": len(tickers),
            "observed_event_ticker_set_sha256": canonical_set_hash(tickers),
            "conflicting_tickers": ";".join(family_conflicts),
            "verdict": "UNKNOWN_PARTIAL_POSITIVE_ONLY_NO_FULL_AUTHORITY" if entries else "FAIL_NO_RETAINED_POSITIVE_OR_NO_EVENT_AUTHORITY",
            "notes": "Do not generalize KSEI family rows or IDX candidate dates into market-wide no-event/transition evidence; MERGER mapping remains UNKNOWN.",
        })
    return results


def _temporal_authority(project_root: Path) -> list[dict[str, Any]]:
    ksei_events = _read_jsonl(project_root / "idx-v4-ksei-ca-history-census-20260817-v1" / "ksei_ca_history.jsonl")
    idx_events = _load_idx_rows(project_root / "idx-corporate-action-pit-source-audit-20260814-v1-final")
    date_values = [str(row.get(field))[:10] for row in ksei_events for field in ("cum_date", "record_date", "distribution_date") if row.get(field)]
    idx_dates = [str(row.get("TanggalPencatatan"))[:10] for row in idx_events if row.get("TanggalPencatatan")]
    return [
        {"source": "KSEI_REGISTERED_SECURITY_HISTORY", "historical_date_scope": f"{min(date_values)}—{max(date_values)}", "capture_scope": "2026-08-17 request span", "knowledge_publication_semantics": "source-native event dates; publication/knowledge time not per session", "no_event_semantics": "none", "valid_interval_attestation": "none", "verdict": "UNKNOWN_NO_PER_SESSION_ASOF", "notes": "ticker history covered does not mean no-event coverage for every session"},
        {"source": "IDX_ISSUED_HISTORY", "historical_date_scope": f"{min(idx_dates)}—{max(idx_dates)}", "capture_scope": "2018-01-01—2026-08-14 request scope; retained captures accessed 2026-08-13", "knowledge_publication_semantics": "request capture time only", "no_event_semantics": "none", "valid_interval_attestation": "none", "verdict": "UNKNOWN_POSITIVE_CANDIDATE_ONLY", "notes": "TanggalPencatatan is not a generic effective/transition date"},
        {"source": "IDX_OFFICIAL_ANNOUNCEMENT_ATTACHMENTS", "historical_date_scope": "selected event-specific documents only", "capture_scope": "2026-08-13 targeted capture", "knowledge_publication_semantics": "document publication/capture metadata for selected candidates", "no_event_semantics": "none", "valid_interval_attestation": "none", "verdict": "UNKNOWN_TARGETED_ONLY", "notes": "cannot certify 716 application/closure ticker-date scope"},
        {"source": "KSEI_TARGETED_SCHEDULE_DOCUMENTS", "historical_date_scope": "selected candidate documents; 95 required event links", "capture_scope": "2026-08-17 targeted schedule capture", "knowledge_publication_semantics": "document date plus capture time; no full as-of interval", "no_event_semantics": "none", "valid_interval_attestation": "one exact non-structural linkage; 94 unresolved", "verdict": "UNKNOWN_TARGETED_ONLY", "notes": "retrieval time is not historical no-event authority"},
        {"source": "COMPOSITE_716_SCOPE", "historical_date_scope": "closure 2021-04-29—2026-07-17; application dates 980", "capture_scope": "composite retained artifacts", "knowledge_publication_semantics": "no source-family-complete as-of attestation", "no_event_semantics": "none", "valid_interval_attestation": "none", "verdict": "FAIL_NO_FULL_SCOPE_TEMPORAL_ATTESTATION", "notes": "Phase-E remains blocked"},
    ]


def _transition_reconciliation(project_root: Path) -> list[dict[str, Any]]:
    r31 = project_root / R31_ROOT_NAME
    strict = _read_csv(r31 / "r3_structural_ca_event_scope.csv")
    retained = _read_csv(project_root / "idx-v4-ca-event-window-final-20260818-v3" / "event_semantics_audit.csv")
    rows: list[dict[str, Any]] = []
    for row in strict:
        lower_bound_row = {
            "certified_state": "CERTIFIED" if row.get("transition_lower_bound_certified", "").lower() == "true" else "",
            "accepted_source_bound_status": row.get("transition_lower_bound_status", ""),
            "source_ref": row.get("source_ref", ""),
            "evidence_sha256": row.get("source_sha256", ""),
            "transition_lower_bound_date": row.get("certified_transition_lower_bound", ""),
        }
        rows.append({
            "record_kind": "STRICT_26",
            "event_identity": "|".join(row.get(key, "") for key in ("source_kind", "ticker", "event_family", "candidate_date", "source_action_id", "source_ref", "source_sha256", "published_at_utc", "evidence_id")),
            "ticker": row.get("ticker", ""),
            "event_family": row.get("event_family", ""),
            "candidate_date": row.get("candidate_date", ""),
            "prior_semantic_class": row.get("transition_semantics", ""),
            "source_ref": row.get("source_ref", ""),
            "source_sha256": row.get("source_sha256", ""),
            "source_sha_valid": str(valid_sha256(row.get("source_sha256", ""))).lower(),
            "transition_lower_bound_certified": str(source_bound_certified(lower_bound_row)).lower(),
            "current_status": "BOUNDED_UNRESOLVED" if source_bound_certified(lower_bound_row) else "UNRESOLVED",
            "resolution_reason": row.get("resolution_reason", "candidate/source date does not prove market transition"),
            "source_contract_status": "SOURCE_REF_AND_HASH_PINNED_BUT_NO_TRANSITION_CONTRACT" if valid_sha256(row.get("source_sha256", "")) else "SOURCE_PROVENANCE_INCOMPLETE",
            "notes": "current strict census remains unresolved; no candidate date is promoted",
        })
    for row in retained:
        prior = row.get("semantic_class", "")
        source_sha = row.get("source_sha256", "")
        status = "UNRESOLVED"
        reason = row.get("reason", "retained event requires source-specific transition proof")
        if prior == "EXACT_TRANSITION" and not valid_sha256(source_sha):
            reason = "prior derived exact label lacks row-level source SHA; revalidation required"
        rows.append({
            "record_kind": "RETAINED_RELEVANT_EVENT",
            "event_identity": row.get("event_id", ""),
            "ticker": row.get("ticker", ""),
            "event_family": row.get("family", ""),
            "candidate_date": row.get("source_dates", ""),
            "prior_semantic_class": prior,
            "source_ref": row.get("transition_source", ""),
            "source_sha256": source_sha,
            "source_sha_valid": str(valid_sha256(source_sha)).lower(),
            "transition_lower_bound_certified": "false",
            "current_status": status,
            "resolution_reason": reason,
            "source_contract_status": "DERIVED_ROW_WITHOUT_SOURCE_HASH_BOUND_TRANSITION" if prior == "EXACT_TRANSITION" else "TARGETED_EVENT_NOT_RESOLVED",
            "notes": "retained semantic label is historical evidence, not promoted authority",
        })
    return rows


def _gap_matrix(project_root: Path, population_rows: Sequence[Mapping[str, Any]], family_rows: Sequence[Mapping[str, Any]], temporal_rows: Sequence[Mapping[str, Any]], transition_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    strict = [row for row in transition_rows if row.get("record_kind") == "STRICT_26"]
    return [
        {"gap_id": "G001", "area": "FULL_716_SOURCE_COVERAGE", "required_for_phase_e": "yes", "current_evidence": "KSEI 610 captured / 567 certified / 43 unresolved; IDX retained rows are positive-event only", "exact_gap": "106 application/closure tickers absent from KSEI census and no source-family-complete no-event authority exists", "verdict": "FAIL", "acquisition_requirement": "source-bound coverage for all 716 application and closure tickers"},
        {"gap_id": "G002", "area": "FROZEN_STRUCTURAL_FAMILY_COVERAGE", "required_for_phase_e": "yes", "current_evidence": f"{len(family_rows)} ontology rows audited; positive rows are partial", "exact_gap": "no complete family-by-family positive plus no-event authority; REVERSE_SPLIT and VOLUNTARY/MERGER semantics are not fully certified", "verdict": "FAIL_OR_UNKNOWN", "acquisition_requirement": "explicit source contract per frozen family and negative coverage semantics"},
        {"gap_id": "G003", "area": "TEMPORAL_ASOF", "required_for_phase_e": "yes", "current_evidence": "capture/retrieval timestamps and source-native event dates", "exact_gap": "no valid per-session/date-level historical as-of or no-event attestation for the full 716 closure interval", "verdict": "UNKNOWN", "acquisition_requirement": "date/session-level source attestation with source ref and evidence SHA"},
        {"gap_id": "G004", "area": "TRANSITION_SEMANTICS", "required_for_phase_e": "yes", "current_evidence": f"strict 26 rows={len(strict)}; certified transition rows={sum(row.get('current_status') == 'BOUNDED_UNRESOLVED' for row in strict)}", "exact_gap": "all strict event transitions remain unresolved; candidate/TanggalPencatatan/record/distribution dates are not market transitions", "verdict": "FAIL_OR_UNKNOWN", "acquisition_requirement": "official source-defined market-basis transition or certified lower bound for every relevant event"},
        {"gap_id": "G005", "area": "CROSS_SOURCE_CONFLICTS", "required_for_phase_e": "yes", "current_evidence": "retained conflict tickers: ISAT; MEGA; SCMA; conversion taxonomy disagreement", "exact_gap": "conflicts cross event-family/date semantics and are not source-contract resolved", "verdict": "UNKNOWN", "acquisition_requirement": "authoritative adjudication artifacts with source refs/hashes and explicit conflict policy"},
        {"gap_id": "G006", "area": "MERGER_MAPPING", "required_for_phase_e": "yes", "current_evidence": "IDX gabungUsaha and schedule MERGER_OR_RESTRUCTURING observations", "exact_gap": "MERGER cannot be promoted to CAPITAL_RESTRUCTURING without an explicit source contract", "verdict": "UNKNOWN", "acquisition_requirement": "explicit mapping contract or retain separate MERGER/UNKNOWN family"},
        {"gap_id": "G007", "area": "IDENTITY_CONTAINMENT", "required_for_phase_e": "yes", "current_evidence": "R3/R3.1 accepted fit=629, application=716, closure=716 identity populations", "exact_gap": "none in observed population arithmetic; source certification remains independent and failed", "verdict": "PASS_IDENTITY_ONLY", "acquisition_requirement": "do not substitute count equality for evidence certification"},
        {"gap_id": "G008", "area": "NO_EVENT_AUTHORITY", "required_for_phase_e": "yes", "current_evidence": "positive/candidate rows and ticker-history presence only", "exact_gap": "absence from retained artifacts cannot establish no event for any uncovered ticker/session", "verdict": "FAIL", "acquisition_requirement": "source-defined negative coverage for full scope and date interval"},
    ]


def _acquisition_requirements(project_root: Path, app_tickers: set[str], closure_start: str, closure_end: str) -> dict[str, Any]:
    return {
        "schema_version": "ca_source_authority_acquisition_requirements_v1",
        "status": "STOP_NO_PROVIDER_ACQUISITION_AUTHORIZED",
        "scope": {"application_tickers": len(app_tickers), "closure_tickers": len(app_tickers), "closure_start": closure_start, "closure_end": closure_end, "source_policy": "retained/local evidence only for this audit"},
        "requirements": [
            {"id": "ACQ-001", "need": "FULL_716_SCOPE", "must_prove": ["all 716 application identities covered", "all 716 closure identities covered", "identity set hash and per-source ticker records", "source ref and valid 64-hex evidence SHA per required identity"], "acceptable_evidence": "source-family-specific capture/manifest or equivalent evidence-rich rows", "blocked_until": "PASS"},
            {"id": "ACQ-002", "need": "FAMILY_POSITIVE_AND_NO_EVENT", "families": list(FROZEN_FAMILIES), "must_prove": ["positive-event authority where present", "source-defined no-event semantics", "exact family taxonomy", "source_contract_id, source_ref, evidence_sha256", "conflict handling"], "merger_rule": "MERGER remains UNKNOWN unless source contract explicitly maps it", "blocked_until": "PASS"},
            {"id": "ACQ-003", "need": "TEMPORAL_ASOF", "must_prove": ["historical coverage interval for every required ticker", "per-session/date-level as-of or valid interval semantics", "publication/knowledge timestamp semantics", "source ref and evidence SHA"], "retrieval_time_is_sufficient": False, "blocked_until": "PASS"},
            {"id": "ACQ-004", "need": "TRANSITION_SEMANTICS", "must_prove": ["source-defined market-basis transition or lower bound for every strict/relevant event", "conversion taxonomy", "SCMA restructuring/capital-reduction conflict resolution", "BBCA 2021 split semantics", "no price/chart/nearest-session inference"], "blocked_until": "PASS"},
            {"id": "ACQ-005", "need": "PROVENANCE_INTEGRITY", "must_prove": ["immutable raw capture bytes", "capture timestamp", "source contract identifier", "source ref", "valid 64-hex evidence SHA", "deterministic manifest"], "blocked_until": "PASS"},
        ],
        "guardrails": {"provider_calls": False, "outcomes_accessed": False, "targets_accessed": False, "model_fit": False, "model_scoring": False, "phase_e_run": False, "counter_mutated": False, "canonical_data_rewritten": False},
        "next_step": "Separate authorization is required before any network/provider acquisition; after acquisition, rerun this audit and stop on FAIL/UNKNOWN.",
    }


def _git_state(repo_root: Path) -> dict[str, str]:
    def run(*args: str) -> str:
        try:
            return subprocess.check_output(["git", "-C", str(repo_root), *args], text=True, stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError):
            return "UNKNOWN"
    return {"repository": run("config", "--get", "remote.origin.url"), "branch": run("branch", "--show-current"), "head": run("rev-parse", "HEAD")}


def run_audit(project_root: Path, output_root: Path, repo_root: Path | None = None) -> Path:
    if output_root.exists():
        raise FileExistsError(f"immutable audit root already exists: {output_root}")
    r31 = project_root / R31_ROOT_NAME
    ticker_rows = _read_csv(r31 / "r3_cross_section_ticker_summary.csv")
    app_tickers = {row["ticker"].strip() for row in ticker_rows if row.get("ticker")}
    fit_tickers = {row["ticker"].strip() for row in ticker_rows if row.get("ticker") and int(row.get("fit_union_rows", "0")) > 0}
    closure_tickers = set(app_tickers)
    r31_summary = _read_json(r31 / "r3_summary.json")
    closure_start = r31_summary["backward_dependency_closure"]["closure_start"]
    closure_end = r31_summary["backward_dependency_closure"]["closure_end"]
    inventory, inventory_meta = _source_inventory(project_root, app_tickers, closure_start, closure_end)
    population = _population_reconciliation(project_root, app_tickers, fit_tickers, closure_tickers)
    family = _family_authority(project_root, app_tickers, closure_tickers)
    temporal = _temporal_authority(project_root)
    transition = _transition_reconciliation(project_root)
    gaps = _gap_matrix(project_root, population, family, temporal, transition)
    acquisition = _acquisition_requirements(project_root, app_tickers, closure_start, closure_end)

    staging = output_root.parent / f".{output_root.name}.staging"
    if staging.exists():
        raise FileExistsError(f"staging root already exists: {staging}")
    staging.mkdir(parents=True)
    try:
        fields = [
            "pin_id", "artifact_class", "path", "exists", "sha256", "recorded_sha256", "sha256_matches_record", "bytes", "filesystem_mtime_utc", "capture_retrieval_timestamp_utc", "source_contract", "source_contract_id", "source_ref", "source_url", "ticker_population", "date_time_scope", "event_family", "evidence_polarity", "publication_knowledge_asof", "transition_semantics", "authority_status", "notes",
        ]
        _write_csv(staging / "ca_source_inventory.csv", inventory, fields)
        _write_csv(staging / "ca_source_family_authority_matrix.csv", family, list(family[0].keys()))
        _write_csv(staging / "ca_source_population_reconciliation.csv", population, list(population[0].keys()))
        _write_csv(staging / "ca_temporal_authority_matrix.csv", temporal, list(temporal[0].keys()))
        _write_csv(staging / "ca_transition_semantics_reconciliation.csv", transition, list(transition[0].keys()))
        _write_csv(staging / "ca_remaining_gap_matrix.csv", gaps, list(gaps[0].keys()))
        _dump_json(staging / "acquisition_requirements.json", acquisition)

        output_hashes = {
            path.name: sha256_file(path)
            for path in sorted(staging.iterdir())
            if path.is_file()
        }
        strict = [row for row in transition if row.get("record_kind") == "STRICT_26"]
        ksei_scope = [row for row in population if row.get("source_name") == "KSEI_REGISTERED_SECURITY_HISTORY" and row.get("population_scope") == "CROSS_SECTION_APPLICATION"][0]
        summary = {
            "schema_version": AUDIT_SCHEMA,
            "status": "SOURCE_AUTHORITY_GAP_CONFIRMED_PHASE_E_BLOCKED",
            "audit_date": "2026-08-28",
            "source_repository_state": _git_state(repo_root or project_root),
            "reviewed_implementation_head": SOURCE_IMPLEMENTATION_HEAD,
            "artifact_root": "<immutable-output-root>",
            "facts_current_local_audit": {
                "fit": {"rows": r31_summary["exact_final_fit"]["union_rows"], "tickers": len(fit_tickers), "ticker_set_sha256": canonical_set_hash(fit_tickers)},
                "application": {"rows": r31_summary["cross_section_application"]["application_rows"], "tickers": len(app_tickers), "ticker_set_sha256": canonical_set_hash(app_tickers)},
                "closure": {"rows": r31_summary["backward_dependency_closure"]["closure_rows"], "tickers": len(closure_tickers), "ticker_set_sha256": canonical_set_hash(closure_tickers), "start": closure_start, "end": closure_end},
                "ksei": {"captured_tickers": 610, "coverage_certified": 567, "coverage_unresolved": 43, "application_absent": int(ksei_scope["absent_ticker_count"])},
                "strict_26": {"rows": len(strict), "current_status_counts": dict(Counter(row["current_status"] for row in strict)), "families": dict(Counter(row["event_family"] for row in strict))},
                "source_inventory_rows": len(inventory),
                "source_inventory_existing_rows": sum(row["exists"] == "true" for row in inventory),
                "source_inventory_hash_mismatches": sum(row["sha256_matches_record"] == "false" for row in inventory),
            },
            "facts_historical_notes_not_current_authority": {
                "r3_r3_1_population_verdicts": "accepted identity arithmetic, reused here only by pinned hashes",
                "prior_event_window_exact_labels": "derived labels; retained source hash linkage is absent for semantic rows and therefore not promoted",
                "ksei_retrieval_timestamp": "not a historical as-of/no-event attestation",
                "idx_candidate_dates": "not generic market transition dates",
            },
            "authority_matrix_verdicts": dict(Counter(row["verdict"] for row in family)),
            "temporal_verdicts": dict(Counter(row["verdict"] for row in temporal)),
            "gap_verdicts": dict(Counter(row["verdict"] for row in gaps)),
            "phase_e_gate": {"full_716_source_coverage": False, "structural_family_coverage": False, "temporal_asof": False, "transition_semantics": False, "conflicts_resolved": False, "verdict": "STOP"},
            "scientific_verdict_unchanged": {"DATA_ADMISSION": "FAIL", "RESEARCH_ADMISSION": "FAIL", "MODEL_PROMOTION": "NOT_EVALUATED", "HISTORICAL_APPLICATION": "BLOCKED_PHASE_E_NOT_RUN", "REFIT_AUTHORIZED": False, "COUNTER_ACTION": "NONE"},
            "guardrails": acquisition["guardrails"],
            "input_scope": inventory_meta,
            "output_hashes_excluding_manifest": output_hashes,
        }
        _dump_json(staging / "summary.json", summary)
        output_hashes["summary.json"] = sha256_file(staging / "summary.json")
        manifest = {
            "schema_version": f"{AUDIT_SCHEMA}_manifest",
            "status": "IMMUTABLE_LOCAL_SOURCE_AUTHORITY_AUDIT",
            "created_at_policy": "fixed audit date 2026-08-28 for deterministic rerun",
            "source_implementation_head": SOURCE_IMPLEMENTATION_HEAD,
            "outcome_blind": True,
            "provider_calls": False,
            "input_files": sorted({
                row["path"]: {"path": row["path"], "sha256": row["sha256"], "bytes": row["bytes"], "capture_retrieval_timestamp_utc": row["capture_retrieval_timestamp_utc"]}
                for row in inventory if row["exists"] == "true"
            }.values(), key=lambda item: item["path"]),
            "output_hashes_excluding_manifest": dict(sorted(output_hashes.items())),
            "self_hash_policy": "MANIFEST.json excluded from its own hash; all other inputs/outputs are hash-pinned",
        }
        _dump_json(staging / "MANIFEST.json", manifest)
        os.replace(staging, output_root)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return output_root


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(r"D:\Documents\Project"))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path, default=Path(r"D:\Documents\Project") / AUDIT_ROOT_NAME)
    args = parser.parse_args()
    result = run_audit(args.project_root, args.output_root, args.repo_root)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
