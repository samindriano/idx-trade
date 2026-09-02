"""Outcome-blind V1.1 audit of retained corporate-action source authority.

The audit is deliberately local-only.  It reconstructs event and coverage
claims from retained source bytes and manifests, and never calls a provider,
opens protected outcomes, rewrites canonical data, or authorizes Phase-E.
Historical/derived summaries are used for comparison only; raw source-bound
rows are the authority for the V1.1 reconstruction.
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
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


AUDIT_SCHEMA = "ca_source_authority_audit_v11"
AUDIT_DATE = "2026-08-29"
AUDIT_ROOT_NAME = "idx-ca-source-authority-audit-20260829-v11-final"
R31_ROOT_NAME = "idx-ca-aware-feature-basis-remediation-20260828-r3_1-final"
REVIEWED_IMPLEMENTATION_HEAD = "0626b653e273067612631fd3414b579ca93c3763"
SOURCE_CONTRACT_ID = "V4_CA_EVENT_WINDOWS_SOURCE_CONTRACT_75AD356880323FB8D4856EE70A6490B5C1F499AB568571EBEC570DD0B18F6B87"
IDX_SOURCE_CONTRACT_ID = "IDX_GET_ISSUED_HISTORY_CONTRACT_75D6C0F74FA360D225794C70C383348977DE6798"

FROZEN_FAMILIES: tuple[str, ...] = (
    "BONUS_SHARES",
    "CAPITAL_RESTRUCTURING",
    "MANDATORY_CONVERSION",
    "REVERSE_SPLIT",
    "RIGHTS_HMETD",
    "STOCK_DIVIDEND",
    "STOCK_SPLIT",
    "VOLUNTARY_CONVERSION",
)
STATIC_CUM_FAMILIES = {"RIGHTS_HMETD", "STOCK_DIVIDEND", "BONUS_SHARES"}
SCHEDULE_FAMILIES = {
    "STOCK_SPLIT",
    "REVERSE_SPLIT",
    "MANDATORY_CONVERSION",
    "VOLUNTARY_CONVERSION",
    "CAPITAL_RESTRUCTURING",
}
ACCEPTED_SCHEDULE_SEMANTICS = {
    "REGULAR_MARKET_EX_DATE",
    "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE",
}
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
SEPARATION_RE = re.compile(
    r"pemisah|spin[- ]?off|demerg|subsidiar|pups|in specie|unit usaha|distribution",
    re.IGNORECASE,
)
CURRENCY_TOKENS = {"IDR", "USD", "SGD", "EUR", "HKD", "AUD", "JPY"}


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


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _upper(value: Any) -> str:
    return _text(value).upper()


def _ticker(value: Any) -> str:
    return _upper(value).replace(".JK", "")


def _iso_date(value: Any) -> str:
    text = _text(value)
    if not text or text.casefold() in {"none", "nan", "nat", "null"}:
        return ""
    candidate = text[:10]
    try:
        return date.fromisoformat(candidate).isoformat()
    except ValueError:
        return ""


def _as_date(value: Any) -> date | None:
    parsed = _iso_date(value)
    try:
        return date.fromisoformat(parsed) if parsed else None
    except ValueError:
        return None


def _records(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if hasattr(value, "to_dict"):
        return [dict(row) for row in value.to_dict("records")]
    if isinstance(value, Mapping):
        if isinstance(value.get("rows"), Sequence):
            return [dict(row) for row in value["rows"] if isinstance(row, Mapping)]
        return [dict(value)]
    return [dict(row) for row in value if isinstance(row, Mapping)]


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


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: "" if row.get(field) is None else row.get(field) for field in fields})


def _dump_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _strict_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _upper(value) in {"TRUE", "1", "YES", "CERTIFIED", "PASS"}


def source_bound_certified(row: Mapping[str, Any]) -> bool:
    """Require complete provenance before accepting a transition lower bound."""

    certified_state = _upper(row.get("certified_state") or row.get("transition_lower_bound_certified", ""))
    accepted_status = _upper(row.get("accepted_source_bound_status") or row.get("transition_lower_bound_status", ""))
    source_ref = _text(row.get("source_ref") or row.get("transition_lower_bound_source_ref", ""))
    evidence_sha = _text(row.get("evidence_sha256") or row.get("transition_lower_bound_source_sha256", ""))
    lower_bound = _iso_date(row.get("transition_lower_bound_date") or row.get("certified_transition_lower_bound", ""))
    explicit_certified = certified_state in {"CERTIFIED", "TRUE", "PASS"} or _strict_bool(row.get("transition_lower_bound_certified", False))
    accepted = accepted_status in {"ACCEPTED", "SOURCE_BOUND", "CERTIFIED", "SOURCE_CERTIFIED", "CERTIFIED_SOURCE_BOUND"}
    return bool(explicit_certified and accepted and source_ref and valid_sha256(evidence_sha) and lower_bound)


def classify_event_scope(events: Any, closure: Any) -> Any:
    """Classify scope without treating a candidate date as a transition date."""

    event_rows = _records(events)
    closure_rows = _records(closure)
    if not closure_rows:
        raise ValueError("cannot scope events against an empty dependency closure")
    bounds: dict[str, tuple[str, str]] = {}
    for row in closure_rows:
        ticker = _ticker(row.get("ticker"))
        day = _iso_date(row.get("date"))
        if ticker and day:
            old = bounds.get(ticker)
            bounds[ticker] = (min(old[0], day), max(old[1], day)) if old else (day, day)
    result: list[dict[str, Any]] = []
    for index, source in enumerate(event_rows):
        ticker = _ticker(source.get("ticker"))
        candidate = _iso_date(source.get("candidate_date"))
        if ticker not in bounds:
            classification = "OUTSIDE_DEPENDENCY_TICKER"
            reason = "event ticker is absent from observed dependency closure"
        elif not candidate:
            classification = "UNKNOWN_UNRESOLVED_EVENT_DATE"
            reason = "source event has no valid candidate date"
        else:
            lower, upper = bounds[ticker]
            lower_bound = _iso_date(source.get("certified_transition_lower_bound", ""))
            certified = source_bound_certified(source)
            if certified and lower_bound > upper:
                classification = "OUTSIDE_DEPENDENCY_AFTER_CLOSURE"
                reason = "source-certified transition lower bound is after closure"
            elif candidate > upper:
                classification = "UNKNOWN_UNRESOLVED_AFTER_CLOSURE"
                reason = "candidate date is after closure but is not a certified transition lower bound"
            elif candidate < lower:
                classification = "UNRESOLVED_CANDIDATE_BEFORE_CLOSURE"
                reason = "pre-closure candidate may affect later basis; transition is not inferred"
            else:
                classification = "UNRESOLVED_CANDIDATE_IN_CLOSURE"
                reason = "candidate date intersects closure but source semantics do not prove transition"
        row = dict(source)
        row.update(
            {
                "closure_scope_classification": classification,
                "transition_semantics": "UNRESOLVED",
                "resolution_reason": reason,
                "transition_lower_bound_certified": source_bound_certified(source),
                "row_index": index,
            }
        )
        result.append(row)
    if hasattr(events, "columns"):
        import pandas as pd

        return pd.DataFrame(result)
    return result


def _ksei_event_identity(row: Mapping[str, Any]) -> str:
    payload = {
        "ticker": _ticker(row.get("ticker")),
        "row_index": int(row.get("row_index") or 0),
        "event_family_source": _text(row.get("event_family_source")),
        "cum_date": _text(row.get("cum_date")),
        "record_date": _text(row.get("record_date")),
        "distribution_date": _text(row.get("distribution_date")),
        "status": _text(row.get("status")),
        "ratio_raw": _text(row.get("ratio_raw")),
        "source_sha256": _text(row.get("source_sha256")).lower(),
    }
    return _canonical_hash(payload)


def _idx_event_identity(row: Mapping[str, Any]) -> str:
    payload = {
        "id": _text(row.get("id")),
        "ticker": _ticker(row.get("KodeEmiten", row.get("ticker"))),
        "action": _text(row.get("JenisTindakan", row.get("action"))),
        "candidate_date": _iso_date(row.get("TanggalPencatatan", row.get("candidate_date"))),
        "shares": _text(row.get("JumlahSaham")),
        "shares_after": _text(row.get("JumlahSahamSetelahTindakan")),
    }
    return _canonical_hash(payload)


def event_identity(row: Mapping[str, Any]) -> str:
    """Stable identity for a retained raw event row."""

    if _text(row.get("source_kind")).upper().startswith("IDX") or "JenisTindakan" in row:
        return _idx_event_identity(row)
    return _ksei_event_identity(row)


def _ksei_family(row: Mapping[str, Any]) -> str:
    source = _upper(row.get("event_family_source"))
    if source == "RIGHT DISTRIBUTION":
        return "RIGHTS_HMETD"
    if source == "STOCK DIVIDEND":
        return "STOCK_DIVIDEND"
    if source in {"SHARE BONUS", "BONUS SHARES", "BONUS SHARE", "BONUS DISTRIBUTION"}:
        return "BONUS_SHARES"
    if source == "MANDATORY CONVERSION":
        return "MANDATORY_CONVERSION"
    if source == "VOLUNTARY CONVERSION":
        return "VOLUNTARY_CONVERSION"
    if source == "MIXED DIVIDEND":
        right = _upper(row.get("ratio_right_security"))
        ticker = _ticker(row.get("ticker"))
        if right == ticker and ticker:
            return "STOCK_DIVIDEND"
        if right in CURRENCY_TOKENS:
            return "UNKNOWN_TAXONOMY"
        return "UNKNOWN_TAXONOMY"
    return ""


def _idx_family(action: Any) -> str:
    return {
        "stockSplit": "STOCK_SPLIT",
        "reverseStock": "REVERSE_SPLIT",
        "hmetd": "RIGHTS_HMETD",
        "Dividen Saham": "STOCK_DIVIDEND",
        "dividenSaham": "STOCK_DIVIDEND",
        "sahamBonus": "BONUS_SHARES",
        "obligasiWajibKonversi": "MANDATORY_CONVERSION",
        "kurangModal": "CAPITAL_RESTRUCTURING",
        "konversiSaham": "VOLUNTARY_CONVERSION",
        "gabungUsaha": "MERGER",
    }.get(_text(action), "")


def _source_dates(row: Mapping[str, Any]) -> list[str]:
    return [value for value in (_iso_date(row.get("cum_date")), _iso_date(row.get("record_date")), _iso_date(row.get("distribution_date"))) if value]


def _candidate_date(row: Mapping[str, Any]) -> str:
    for key in ("cum_date", "TanggalPencatatan", "record_date", "distribution_date", "document_date", "action_date", "transition_date"):
        value = _iso_date(row.get(key))
        if value:
            return value
    return ""


def _in_geometry(candidate_dates: Iterable[str], start: date, end: date) -> bool:
    extended_start = start - timedelta(days=60)
    extended_end = end + timedelta(days=60)
    return any((parsed := _as_date(value)) is not None and extended_start <= parsed <= extended_end for value in candidate_dates)


def _dependency_bounds(population: Mapping[str, Any], ticker: str) -> tuple[date, date] | None:
    indexed = population.get("dependency_bounds")
    if isinstance(indexed, Mapping) and ticker in indexed:
        value = indexed[ticker]
        if isinstance(value, tuple) and len(value) == 2:
            return value
    days = [
        parsed
        for current_ticker, raw_day in population.get("closure_ids", set())
        if current_ticker == ticker and (parsed := _as_date(raw_day)) is not None
    ]
    return (min(days), max(days)) if days else None


def _dependency_geometry(population: Mapping[str, Any], ticker: str) -> tuple[date, date] | None:
    bounds = _dependency_bounds(population, ticker)
    if not bounds:
        return None
    return bounds[0] - timedelta(days=60), bounds[1] + timedelta(days=60)


def _resolve_path(value: Any, root: Path) -> Path | None:
    text = _text(value)
    if not text:
        return None
    path = Path(text)
    return path if path.is_absolute() else root / path


def _path_hash(path: Path | None) -> tuple[str, bool]:
    if path is None or not path.is_file():
        return "", False
    return sha256_file(path), True


def _request_index(requests: Sequence[Mapping[str, Any]], root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    by_path: dict[str, dict[str, Any]] = {}
    by_sha: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for request in requests:
        path = _resolve_path(request.get("path"), root)
        if path is None:
            continue
        actual, exists = _path_hash(path)
        row = dict(request)
        row["resolved_path"] = str(path)
        row["actual_sha256"] = actual
        row["hash_matches_bytes"] = bool(exists and valid_sha256(request.get("sha256", "")) and actual.lower() == _text(request.get("sha256")).lower())
        by_path[str(path).casefold()] = row
        if actual:
            by_sha[actual.lower()].append(row)
    return by_path, by_sha


def _best_capture(requests_by_sha: Mapping[str, Sequence[Mapping[str, Any]]], sha: Any) -> dict[str, Any]:
    rows = list(requests_by_sha.get(_text(sha).lower(), ()))
    if not rows:
        return {}
    return sorted(rows, key=lambda row: (_text(row.get("ticker")), _text(row.get("accessed_at_utc")), _text(row.get("resolved_path"))))[-1]


def _source_row_base(
    *,
    source_kind: str,
    ticker: str,
    family: str,
    source_native_label: str,
    candidate_date: str,
    event_id: str,
    source_ref: str,
    evidence_sha: str,
    capture: Mapping[str, Any],
    raw_path: str = "",
    raw_fields: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
        "source_kind": source_kind,
        "ticker": _ticker(ticker),
        "event_family": family,
        "source_native_label": source_native_label,
        "raw_row_identity": event_id,
        "candidate_date": candidate_date,
        "cum_date": "",
        "record_date": "",
        "distribution_date": "",
        "ratio_left_security": "",
        "ratio_left_value": "",
        "ratio_right_security": "",
        "ratio_right_value": "",
        "ratio_raw": "",
        "status": "",
        "source_ref": source_ref,
        "source_url": source_ref,
        "evidence_sha256": _text(evidence_sha).lower(),
        "source_contract_id": SOURCE_CONTRACT_ID if source_kind == "KSEI_REGISTERED_SECURITY_HISTORY" else IDX_SOURCE_CONTRACT_ID,
        "capture_observed_at_utc": _text(capture.get("accessed_at_utc")),
        "raw_capture_path": raw_path or _text(capture.get("resolved_path")),
        "source_hash_matches_bytes": str(bool(capture.get("hash_matches_bytes"))).lower(),
        "publication_fields": "",
        "raw_evidence_role": "PRIMARY_RAW_SOURCE_ROW",
    }
    if raw_fields:
        row.update({key: _text(raw_fields.get(key)) for key in ("cum_date", "record_date", "distribution_date", "ratio_left_security", "ratio_left_value", "ratio_right_security", "ratio_right_value", "ratio_raw", "status")})
    return row


def _load_population(project_root: Path) -> dict[str, Any]:
    r31 = project_root / R31_ROOT_NAME
    summary = _read_json(r31 / "r3_summary.json")
    population_rows = _read_csv(r31 / "r3_cross_section_population_reconciliation.csv")
    closure_rows = _read_csv(r31 / "r3_backward_dependency_closure.csv")
    fit_ids = {(_ticker(row.get("ticker")), _iso_date(row.get("date"))) for row in population_rows if _upper(row.get("in_fit_union")) == "TRUE"}
    app_ids = {(_ticker(row.get("ticker")), _iso_date(row.get("date"))) for row in population_rows if _upper(row.get("population_role")) in {"FINAL_FIT", "CROSS_SECTION_ONLY"}}
    closure_ids = {(_ticker(row.get("ticker")), _iso_date(row.get("date"))) for row in closure_rows}
    fit_ids.discard(("", ""))
    app_ids.discard(("", ""))
    closure_ids.discard(("", ""))
    dependency_bounds: dict[str, tuple[date, date]] = {}
    for ticker, raw_day in closure_ids:
        parsed = _as_date(raw_day)
        if parsed is None:
            continue
        old = dependency_bounds.get(ticker)
        dependency_bounds[ticker] = (min(old[0], parsed), max(old[1], parsed)) if old else (parsed, parsed)
    return {
        "summary": summary,
        "population_rows": population_rows,
        "closure_rows": closure_rows,
        "fit_ids": fit_ids,
        "app_ids": app_ids,
        "closure_ids": closure_ids,
        "fit_tickers": {ticker for ticker, _ in fit_ids},
        "app_tickers": {ticker for ticker, _ in app_ids},
        "closure_tickers": {ticker for ticker, _ in closure_ids},
        "dependency_bounds": dependency_bounds,
        "closure_start": summary["backward_dependency_closure"]["closure_start"],
        "closure_end": summary["backward_dependency_closure"]["closure_end"],
    }


def _load_raw_context(project_root: Path, population: Mapping[str, Any]) -> dict[str, Any]:
    ksei_root = project_root / "idx-v4-ksei-ca-history-census-20260817-v1"
    pit_root = project_root / "idx-corporate-action-pit-source-audit-20260814-v1-final"
    schedule_root = project_root / "idx-v4-ca-schedule-evidence-20260818-v3"
    calendar_path = project_root / "idx-v4-x1-clean-historical-input-stage-r2-20260820" / "official_exchange_sessions_1260.csv"
    ksei_requests = _read_jsonl(ksei_root / "request_records.jsonl")
    ksei_by_path, ksei_by_sha = _request_index(ksei_requests, ksei_root)
    pit_manifest = _read_json(pit_root / "MANIFEST.json")
    pit_requests = pit_manifest.get("requests", []) if isinstance(pit_manifest, Mapping) else []
    pit_by_path, pit_by_sha = _request_index(pit_requests, pit_root)
    schedule_requests = _read_jsonl(schedule_root / "request_records.jsonl")
    schedule_by_path, schedule_by_sha = _request_index(schedule_requests, schedule_root)
    sessions = {_iso_date(row.get("date")) for row in _read_csv(calendar_path)} if calendar_path.is_file() else set()
    sessions.discard("")
    prior = _read_csv(project_root / "idx-v4-ca-event-window-final-20260818-v3" / "event_semantics_audit.csv")
    strict = _read_csv(project_root / R31_ROOT_NAME / "r3_structural_ca_event_scope.csv")
    scope_reclassification = _read_csv(project_root / R31_ROOT_NAME / "r3_1_scope_reclassification.csv")
    schedule_evidence = _read_csv(schedule_root / "schedule_evidence.csv")
    schedule_audit = _read_csv(schedule_root / "event_schedule_linkage_audit.csv")
    schedule_parse = _read_csv(schedule_root / "schedule_document_parse_audit.csv")
    announcements = _read_jsonl(pit_root / "idx_announcement_linkages.jsonl")
    ksei_coverage = _read_csv(ksei_root / "ticker_coverage.csv")
    ksei_rows = _read_jsonl(ksei_root / "ksei_ca_history.jsonl")
    idx_records: list[tuple[dict[str, Any], dict[str, Any]]] = []
    seen_idx: set[str] = set()
    for path in sorted((pit_root / "raw").glob("idx_issued*.json")):
        request = pit_by_path.get(str(path).casefold(), {})
        if not request:
            actual = sha256_file(path) if path.is_file() else ""
            request = _best_capture(pit_by_sha, actual)
        try:
            value = _read_json(path)
        except (OSError, ValueError):
            continue
        data = value.get("data", []) if isinstance(value, Mapping) else value
        for record in data if isinstance(data, list) else []:
            if not isinstance(record, Mapping):
                continue
            key = _idx_event_identity(record)
            if key not in seen_idx:
                seen_idx.add(key)
                idx_records.append((dict(record), request))
    return {
        "ksei_root": ksei_root,
        "pit_root": pit_root,
        "schedule_root": schedule_root,
        "calendar_path": calendar_path,
        "sessions": sessions,
        "ksei_requests": ksei_requests,
        "ksei_by_path": ksei_by_path,
        "ksei_by_sha": ksei_by_sha,
        "pit_manifest": pit_manifest,
        "pit_requests": pit_requests,
        "pit_by_path": pit_by_path,
        "pit_by_sha": pit_by_sha,
        "schedule_requests": schedule_requests,
        "schedule_by_path": schedule_by_path,
        "schedule_by_sha": schedule_by_sha,
        "prior": prior,
        "strict": strict,
        "scope_reclassification": scope_reclassification,
        "schedule_evidence": schedule_evidence,
        "schedule_audit": schedule_audit,
        "schedule_parse": schedule_parse,
        "announcements": announcements,
        "ksei_coverage": ksei_coverage,
        "ksei_rows": ksei_rows,
        "idx_records": idx_records,
        "population": population,
    }


def _build_primary_rows(context: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    population = context["population"]
    app_tickers = set(population["app_tickers"])
    start = _as_date(population["closure_start"]) or date.min
    end = _as_date(population["closure_end"]) or date.max
    primary: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []
    for raw in context["ksei_rows"]:
        ticker = _ticker(raw.get("ticker"))
        family = _ksei_family(raw)
        dates = _source_dates(raw)
        if ticker not in app_tickers or not family or _upper(raw.get("status")) != "ACTIVE" or not _in_geometry(dates, start, end):
            continue
        event_id = _ksei_event_identity(raw)
        capture = _best_capture(context["ksei_by_sha"], raw.get("source_sha256"))
        row = _source_row_base(
            source_kind="KSEI_REGISTERED_SECURITY_HISTORY",
            ticker=ticker,
            family=family,
            source_native_label=_text(raw.get("event_family_source")),
            candidate_date=_candidate_date(raw),
            event_id=event_id,
            source_ref=_text(raw.get("source_url")),
            evidence_sha=_text(raw.get("source_sha256")),
            capture=capture,
            raw_fields=raw,
        )
        row["raw_date_set"] = "|".join(sorted(set(dates)))
        row["raw_source_row_index"] = _text(raw.get("row_index"))
        primary.append(row)
        ledger.append(dict(row))
    for raw, capture in context["idx_records"]:
        ticker = _ticker(raw.get("KodeEmiten"))
        family = _idx_family(raw.get("JenisTindakan"))
        candidate = _candidate_date(raw)
        if ticker not in app_tickers or family not in set(FROZEN_FAMILIES) | {"MERGER"} or not _in_geometry([candidate], start, end):
            continue
        event_id = _idx_event_identity(raw)
        source_ref = _text(capture.get("url") or capture.get("requested_url") or capture.get("path"))
        evidence_sha = _text(capture.get("sha256"))
        row = _source_row_base(
            source_kind="IDX_GET_ISSUED_HISTORY",
            ticker=ticker,
            family=family,
            source_native_label=_text(raw.get("JenisTindakan")),
            candidate_date=candidate,
            event_id=event_id,
            source_ref=source_ref,
            evidence_sha=evidence_sha,
            capture=capture,
        )
        row.update(
            {
                "source_contract_id": IDX_SOURCE_CONTRACT_ID,
                "idx_action_id": _text(raw.get("id")),
                "idx_date_native": _text(raw.get("TanggalPencatatan")),
                "idx_shares": _text(raw.get("JumlahSaham")),
                "idx_shares_after": _text(raw.get("JumlahSahamSetelahTindakan")),
                "raw_date_set": candidate,
                "raw_source_row_index": "",
            }
        )
        primary.append(row)
        ledger.append(dict(row))
    return primary, ledger


def _build_auxiliary_ledger(context: Mapping[str, Any], ledger: list[dict[str, Any]]) -> None:
    population = context["population"]
    app_tickers = set(population["app_tickers"])
    start = _as_date(population["closure_start"]) or date.min
    end = _as_date(population["closure_end"]) or date.max
    pit_root = context["pit_root"]
    attachment_paths: dict[str, Path] = {}
    for path in (pit_root / "raw").rglob("*"):
        if path.is_file():
            actual = sha256_file(path)
            attachment_paths.setdefault(actual.lower(), path)
    for raw in context["announcements"]:
        ticker = _ticker(raw.get("ticker"))
        candidate = _iso_date(raw.get("action_date"))
        if ticker not in app_tickers or not _in_geometry([candidate], start, end):
            continue
        family = {
            "RIGHTS_ISSUE": "RIGHTS_HMETD",
            "BONUS_SHARES": "BONUS_SHARES",
            "STOCK_DIVIDEND": "STOCK_DIVIDEND",
            "STOCK_SPLIT": "STOCK_SPLIT",
            "CAPITAL_RESTRUCTURING": "CAPITAL_RESTRUCTURING",
        }.get(_upper(raw.get("event_family")), "UNKNOWN_ANNOUNCEMENT_FAMILY")
        sha = _text(raw.get("attachment_sha256")).lower()
        path = attachment_paths.get(sha)
        ledger.append(
            {
                "source_kind": "IDX_OFFICIAL_ANNOUNCEMENT_ATTACHMENT",
                "ticker": ticker,
                "event_family": family,
                "source_native_label": _text(raw.get("title") or raw.get("subject")),
                "raw_row_identity": "IDX_ANNOUNCEMENT:" + _text(raw.get("source_action_id")),
                "candidate_date": candidate,
                "cum_date": "",
                "record_date": "",
                "distribution_date": "",
                "ratio_left_security": "",
                "ratio_left_value": "",
                "ratio_right_security": "",
                "ratio_right_value": "",
                "ratio_raw": "",
                "status": "",
                "source_ref": _text(raw.get("announcement_ref") or raw.get("attachment_url")),
                "source_url": _text(raw.get("attachment_url")),
                "evidence_sha256": sha,
                "source_contract_id": "IDX_OFFICIAL_ANNOUNCEMENT_ATTACHMENT_CONTRACT",
                "capture_observed_at_utc": _text(raw.get("published_at_utc")),
                "raw_capture_path": str(path) if path else "",
                "source_hash_matches_bytes": str(bool(path and sha256_file(path).lower() == sha)).lower() if path else "false",
                "publication_fields": json.dumps({"published_at_utc": raw.get("published_at_utc"), "announcement_ref": raw.get("announcement_ref")}, sort_keys=True),
                "raw_evidence_role": "OFFICIAL_ANNOUNCEMENT_BYTES",
                "raw_date_set": candidate,
                "raw_source_row_index": "",
            }
        )
    schedule_sha_paths: dict[str, Path] = {}
    for sha, rows in context["schedule_by_sha"].items():
        for row in rows:
            path = Path(_text(row.get("resolved_path")))
            if path.is_file():
                schedule_sha_paths.setdefault(sha.lower(), path)
    for raw in context["schedule_evidence"]:
        ticker = _ticker(raw.get("ticker"))
        candidate = _iso_date(raw.get("transition_date") or raw.get("document_date"))
        if not ticker or ticker not in app_tickers or not _in_geometry([candidate, _iso_date(raw.get("document_date"))], start, end):
            continue
        family = _ksei_family({"event_family_source": raw.get("event_source_type"), "ticker": ticker, "ratio_right_security": ticker}) or {
            "STOCK SPLIT": "STOCK_SPLIT",
            "REVERSE SPLIT": "REVERSE_SPLIT",
            "MANDATORY CONVERSION": "MANDATORY_CONVERSION",
            "VOLUNTARY CONVERSION": "VOLUNTARY_CONVERSION",
            "MERGER": "MERGER",
        }.get(_upper(raw.get("event_source_type")), "UNKNOWN_SCHEDULE_FAMILY")
        sha = _text(raw.get("source_sha256")).lower()
        path = schedule_sha_paths.get(sha)
        ledger.append(
            {
                "source_kind": "KSEI_TARGETED_SCHEDULE_DOCUMENT",
                "ticker": ticker,
                "event_family": family,
                "source_native_label": _text(raw.get("event_source_type")),
                "raw_row_identity": "KSEI_SCHEDULE:" + _text(raw.get("event_id")),
                "candidate_date": candidate,
                "cum_date": "",
                "record_date": _iso_date(raw.get("document_date")),
                "distribution_date": "",
                "ratio_left_security": "",
                "ratio_left_value": "",
                "ratio_right_security": "",
                "ratio_right_value": "",
                "ratio_raw": "",
                "status": _text(raw.get("linkage_status")),
                "source_ref": _text(raw.get("source_url") or raw.get("ksei_reference")),
                "source_url": _text(raw.get("source_url")),
                "evidence_sha256": sha,
                "source_contract_id": SOURCE_CONTRACT_ID,
                "capture_observed_at_utc": "",
                "raw_capture_path": str(path) if path else "",
                "source_hash_matches_bytes": str(bool(path and sha256_file(path).lower() == sha)).lower() if path else "false",
                "publication_fields": json.dumps({"ksei_reference": raw.get("ksei_reference"), "document_date": raw.get("document_date")}, sort_keys=True),
                "raw_evidence_role": "TARGETED_SCHEDULE_BYTES",
                "raw_date_set": "|".join(value for value in (_iso_date(raw.get("document_date")), _iso_date(raw.get("transition_date"))) if value),
                "raw_source_row_index": "",
            }
        )
    # The parsed schedule ledger is an evidence index, not a transition
    # authority.  Preserve every retained document row, including unresolved
    # and missing-ticker rows, so an exact source-native label cannot disappear
    # during normalization (for example ``Pemisahan Unit Usaha``).
    for raw in context["schedule_parse"]:
        sha = _text(raw.get("source_sha256")).lower()
        path = schedule_sha_paths.get(sha)
        ticker = _ticker(raw.get("ticker"))
        family = _idx_family(raw.get("event_family")) or _ksei_family({"event_family_source": raw.get("event_family"), "ticker": ticker, "ratio_right_security": ticker}) or "UNKNOWN_SCHEDULE_FAMILY"
        document_date = _iso_date(raw.get("document_date"))
        transition_date = _iso_date(raw.get("transition_date"))
        ledger.append(
            {
                "source_kind": "KSEI_TARGETED_SCHEDULE_DOCUMENT",
                "ticker": ticker,
                "event_family": family,
                "source_native_label": _text(raw.get("subject")),
                "raw_row_identity": "KSEI_SCHEDULE_PARSED:" + _text(raw.get("reference")),
                "candidate_date": transition_date or document_date,
                "cum_date": "",
                "record_date": _iso_date(raw.get("record_date")),
                "distribution_date": _iso_date(raw.get("distribution_date")),
                "ratio_left_security": "",
                "ratio_left_value": "",
                "ratio_right_security": "",
                "ratio_right_value": "",
                "ratio_raw": "",
                "status": _text(raw.get("parse_status")),
                "source_ref": _text(raw.get("source_url") or raw.get("document_url") or raw.get("reference")),
                "source_url": _text(raw.get("source_url") or raw.get("document_url")),
                "evidence_sha256": sha,
                "source_contract_id": SOURCE_CONTRACT_ID,
                "capture_observed_at_utc": "",
                "raw_capture_path": str(path) if path else "",
                "source_hash_matches_bytes": str(bool(path and sha256_file(path).lower() == sha)).lower() if path else "false",
                "publication_fields": json.dumps({"reference": raw.get("reference"), "document_date": raw.get("document_date"), "parse_status": raw.get("parse_status"), "diagnostics": raw.get("diagnostics")}, sort_keys=True),
                "raw_evidence_role": "TARGETED_SCHEDULE_BYTES",
                "raw_date_set": "|".join(value for value in (document_date, _iso_date(raw.get("record_date")), _iso_date(raw.get("distribution_date")), transition_date) if value),
                "raw_source_row_index": "",
            }
        )


def _valid_raw_provenance(row: Mapping[str, Any]) -> bool:
    return bool(_text(row.get("source_ref")) and valid_sha256(row.get("evidence_sha256")) and _upper(row.get("source_hash_matches_bytes")) == "TRUE")


def _next_session(cum_date: str, sessions: set[str]) -> str:
    if cum_date not in sessions:
        return ""
    future = sorted(value for value in sessions if value > cum_date)
    return future[0] if future else ""


def _schedule_by_event(context: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in context["schedule_evidence"]:
        if _text(row.get("event_id")):
            result[_text(row["event_id"])].append(row)
    return result


def _exact_schedule(row: Mapping[str, Any], context: Mapping[str, Any]) -> tuple[bool, str, str]:
    if _upper(row.get("linkage_status")) != "EXACT" or _upper(row.get("transition_semantic")) not in ACCEPTED_SCHEDULE_SEMANTICS:
        return False, "", "schedule linkage is not exact/accepted"
    transition = _iso_date(row.get("transition_date"))
    sha = _text(row.get("source_sha256")).lower()
    source_ref = _text(row.get("source_url"))
    capture = _best_capture(context["schedule_by_sha"], sha)
    if not transition or not _text(row.get("ksei_reference")) or not source_ref or not valid_sha256(sha):
        return False, "", "schedule evidence lacks transition date, reference, or valid SHA"
    if not capture or not capture.get("hash_matches_bytes"):
        return False, "", "schedule evidence SHA is not bound to a retained capture byte"
    return True, transition, "exact source-contract schedule transition"


def _transition_reconstruction(primary: Sequence[Mapping[str, Any]], context: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    schedule = _schedule_by_event(context)
    prior_by_id = {_text(row.get("event_id")): row for row in context["prior"] if _text(row.get("event_id"))}
    rows: list[dict[str, Any]] = []
    resolved_ids: set[str] = set()
    for source in sorted(primary, key=lambda row: (_text(row.get("ticker")), _text(row.get("candidate_date")), _text(row.get("raw_row_identity")))):
        event_id = _text(source.get("raw_row_identity"))
        family = _text(source.get("event_family"))
        status = "UNRESOLVED"
        transition = ""
        reason = "source-native candidate date does not prove market transition"
        if source.get("source_kind") == "KSEI_REGISTERED_SECURITY_HISTORY":
            if family in STATIC_CUM_FAMILIES and _iso_date(source.get("cum_date")) and _valid_raw_provenance(source):
                transition = _next_session(_iso_date(source.get("cum_date")), context["sessions"])
                if transition:
                    status = "RESOLVED"
                    reason = "source-native KSEI cum date plus next official exchange session"
                else:
                    reason = "KSEI cum date is absent from the retained official exchange session calendar"
            if status != "RESOLVED":
                for candidate in schedule.get(event_id, ()):
                    accepted, candidate_date, schedule_reason = _exact_schedule(candidate, context)
                    if accepted:
                        status = "RESOLVED"
                        transition = candidate_date
                        reason = schedule_reason
                        break
        prior = prior_by_id.get(event_id, {})
        rows.append(
            {
                "record_kind": "RAW_SOURCE_EVENT",
                "event_id": event_id,
                "source_kind": source.get("source_kind", ""),
                "ticker": source.get("ticker", ""),
                "event_family": family,
                "source_native_label": source.get("source_native_label", ""),
                "candidate_date": source.get("candidate_date", ""),
                "cum_date": source.get("cum_date", ""),
                "record_date": source.get("record_date", ""),
                "distribution_date": source.get("distribution_date", ""),
                "prior_derived_class": _text(prior.get("semantic_class")),
                "prior_transition_source": _text(prior.get("transition_source")),
                "v11_raw_recomputed_class": status,
                "transition_date": transition,
                "resolution_reason": reason,
                "source_ref": source.get("source_ref", ""),
                "evidence_sha256": source.get("evidence_sha256", ""),
                "source_contract_id": source.get("source_contract_id", ""),
                "source_hash_matches_bytes": source.get("source_hash_matches_bytes", "false"),
                "transition_lower_bound_certified": "false",
                "transition_lower_bound_source_ref": "",
                "transition_lower_bound_source_sha256": "",
                "scope_classification": "",
            }
        )
        if status == "RESOLVED":
            resolved_ids.add(event_id)
    strict_scoped = classify_event_scope(context["strict"], context["population"]["closure_rows"])
    strict_rows = _records(strict_scoped)
    for source in strict_rows:
        rows.append(
            {
                "record_kind": "STRICT_26_SCOPE_REAUDIT",
                "event_id": _text(source.get("evidence_id")) or _canonical_hash({key: source.get(key, "") for key in ("source_kind", "ticker", "event_family", "candidate_date", "source_action_id", "source_ref", "source_sha256")}),
                "source_kind": source.get("source_kind", ""),
                "ticker": _ticker(source.get("ticker")),
                "event_family": source.get("event_family", ""),
                "source_native_label": source.get("source_ref", ""),
                "candidate_date": source.get("candidate_date", ""),
                "cum_date": "",
                "record_date": "",
                "distribution_date": "",
                "prior_derived_class": source.get("transition_semantics", ""),
                "prior_transition_source": source.get("source_ref", ""),
                "v11_raw_recomputed_class": "UNRESOLVED",
                "transition_date": "",
                "resolution_reason": source.get("resolution_reason", ""),
                "source_ref": source.get("source_ref", ""),
                "evidence_sha256": source.get("source_sha256", ""),
                "source_contract_id": "",
                "source_hash_matches_bytes": "",
                "transition_lower_bound_certified": str(bool(source.get("transition_lower_bound_certified"))).lower(),
                "transition_lower_bound_source_ref": source.get("transition_lower_bound_source_ref", ""),
                "transition_lower_bound_source_sha256": "",
                "scope_classification": source.get("closure_scope_classification", ""),
            }
        )
    prior_exact = {_text(row.get("event_id")) for row in context["prior"] if _upper(row.get("semantic_class")) == "EXACT_TRANSITION" and _text(row.get("event_id"))}
    raw_ids = {_text(row.get("event_id")) for row in rows if row.get("record_kind") == "RAW_SOURCE_EVENT"}
    reproven = prior_exact & resolved_ids
    summary = {
        "prior_exact_count": len(prior_exact),
        "retained_exact_reproven_count": len(reproven),
        "retained_exact_not_reproven_count": len(prior_exact - reproven),
        "raw_resolved_count": len(resolved_ids),
        "newly_resolved_count": len(resolved_ids - prior_exact),
        "raw_unresolved_count": len(raw_ids - resolved_ids),
        "raw_unresolved_ticker_count": len({_ticker(row.get("ticker")) for row in rows if row.get("record_kind") == "RAW_SOURCE_EVENT" and _text(row.get("event_id")) in (raw_ids - resolved_ids) and _ticker(row.get("ticker"))}),
        "raw_unresolved_ticker_set_sha256": canonical_set_hash(_ticker(row.get("ticker")) for row in rows if row.get("record_kind") == "RAW_SOURCE_EVENT" and _text(row.get("event_id")) in (raw_ids - resolved_ids)),
        "strict_26_scope_counts": dict(Counter(_text(row.get("scope_classification")) for row in rows if row.get("record_kind") == "STRICT_26_SCOPE_REAUDIT")),
        "strict_26_outside_after_closure_count": sum(row.get("scope_classification") == "OUTSIDE_DEPENDENCY_AFTER_CLOSURE" for row in rows if row.get("record_kind") == "STRICT_26_SCOPE_REAUDIT"),
        "strict_26_prior_scope_counts": dict(Counter(_text(row.get("before_classification")) for row in context.get("scope_reclassification", []))),
        "strict_26_scope_classification_changed_count": sum(_upper(row.get("classification_changed")) == "TRUE" for row in context.get("scope_reclassification", [])),
        "resolved_event_ids": sorted(resolved_ids),
    }
    return rows, summary


def _prior_event_id(row: Mapping[str, Any]) -> str:
    return _text(row.get("event_id"))


def _census(primary: Sequence[Mapping[str, Any]], transition: Sequence[Mapping[str, Any]], context: Mapping[str, Any], forensics: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    prior_ids = {_prior_event_id(row) for row in context["prior"] if _prior_event_id(row)}
    strict_signatures = {
        (_ticker(row.get("ticker")), _upper(row.get("event_family")), _iso_date(row.get("candidate_date")))
        for row in context["strict"]
    }
    transition_by_id = {_text(row.get("event_id")): row for row in transition if row.get("record_kind") == "RAW_SOURCE_EVENT"}
    taxonomy_links: dict[str, list[str]] = defaultdict(list)
    for finding in forensics:
        underlying = _text(finding.get("underlying_event_id"))
        if underlying:
            taxonomy_links[underlying].append(_text(finding.get("finding_id")))
    rows: list[dict[str, Any]] = []
    current_ids: set[str] = set()
    for source in sorted(primary, key=lambda row: (_text(row.get("source_kind")), _text(row.get("ticker")), _text(row.get("candidate_date")), _text(row.get("raw_row_identity")))):
        event_id = _text(source.get("raw_row_identity"))
        current_ids.add(event_id)
        signature = (_ticker(source.get("ticker")), _upper(source.get("event_family")), _iso_date(source.get("candidate_date")))
        tr = transition_by_id.get(event_id, {})
        rows.append(
            {
                "census_status": "PRIMARY_STRUCTURAL_EVENT",
                "event_id": event_id,
                "source_kind": source.get("source_kind", ""),
                "ticker": source.get("ticker", ""),
                "event_family": source.get("event_family", ""),
                "source_native_label": source.get("source_native_label", ""),
                "candidate_date": source.get("candidate_date", ""),
                "closure_geometry_start": str((_as_date(context["population"]["closure_start"]) or date.min) - timedelta(days=60)),
                "closure_geometry_end": str((_as_date(context["population"]["closure_end"]) or date.max) + timedelta(days=60)),
                "prior_136_present": str(event_id in prior_ids).lower(),
                "strict_26_signature_match": str(signature in strict_signatures).lower(),
                "prior_family_ticker_date_diff": "NONE" if event_id in prior_ids else "NOT_COMPARABLE",
                "strict_26_family_ticker_date_diff": "NONE" if signature in strict_signatures else "NOT_COMPARABLE",
                "difference_class": "COMMON_WITH_PRIOR_136" if event_id in prior_ids else "RAW_ADDITIONAL",
                "transition_class": tr.get("v11_raw_recomputed_class", "UNRESOLVED"),
                "transition_date": tr.get("transition_date", ""),
                 "source_ref": source.get("source_ref", ""),
                 "evidence_sha256": source.get("evidence_sha256", ""),
                 "taxonomy_status": "FROZEN_FAMILY" if source.get("event_family") in FROZEN_FAMILIES else "UNKNOWN",
                 "physical_event_counted": "true",
                 "underlying_event_id": event_id,
                 "linked_taxonomy_finding_ids": "|".join(sorted(value for value in taxonomy_links.get(event_id, []) if value)),
                 "notes": "raw source-bound row; prior semantic CSV is comparison only",
            }
        )
    for old in context["prior"]:
        event_id = _prior_event_id(old)
        if event_id and event_id not in current_ids:
            rows.append(
                {
                    "census_status": "PRIOR_ONLY_NOT_RECONSTRUCTED",
                    "event_id": event_id,
                    "source_kind": "HISTORICAL_DERIVED_EVENT_SEMANTICS",
                    "ticker": old.get("ticker", ""),
                    "event_family": old.get("family", ""),
                    "source_native_label": "",
                    "candidate_date": old.get("source_dates", ""),
                    "closure_geometry_start": "",
                    "closure_geometry_end": "",
                    "prior_136_present": "true",
                    "strict_26_signature_match": "false",
                    "prior_family_ticker_date_diff": "UNKNOWN_PRIOR_ONLY",
                    "strict_26_family_ticker_date_diff": "NOT_COMPARABLE",
                    "difference_class": "OLD_ONLY",
                    "transition_class": "UNRESOLVED",
                    "transition_date": "",
                     "source_ref": old.get("transition_source", ""),
                     "evidence_sha256": old.get("source_sha256", ""),
                     "taxonomy_status": "UNKNOWN",
                     "physical_event_counted": "false",
                     "underlying_event_id": event_id,
                     "linked_taxonomy_finding_ids": "",
                     "notes": "historical semantic row not present in retained raw candidate set",
                 }
             )
    return rows


def _find_raw_ksei(context: Mapping[str, Any], ticker: str, source_label: str, *, record_date: str = "", distribution_date: str = "") -> dict[str, Any]:
    for row in context["ksei_rows"]:
        if _ticker(row.get("ticker")) == ticker and _text(row.get("event_family_source")) == source_label and (not record_date or _iso_date(row.get("record_date")) == record_date) and (not distribution_date or _iso_date(row.get("distribution_date")) == distribution_date):
            return row
    return {}


def _forensic_row(finding_id: str, *, source_kind: str, ticker: str, label: str, candidate: str, source_ref: str, sha: str, membership: Mapping[str, Any], finding: str, decision: str, census: bool = False, source_fields: str = "", underlying_event_id: str = "", source_document_group_id: str = "") -> dict[str, Any]:
    return {
        "finding_id": finding_id,
        "source_kind": source_kind,
        "ticker": ticker,
        "source_native_label": label,
        "candidate_date": candidate,
        "source_ref": source_ref,
        "evidence_sha256": sha,
        "source_fields": source_fields,
        "fit_ticker": str(membership.get("fit", False)).lower(),
        "application_ticker": str(membership.get("application", False)).lower(),
        "closure_ticker": str(membership.get("closure", False)).lower(),
        "boundary_intersects_dependency_window": str(membership.get("intersects", False)).lower(),
        "dependency_window_start": membership.get("dependency_start", ""),
        "dependency_window_end": membership.get("dependency_end", ""),
        "underlying_event_id": underlying_event_id,
        "source_document_group_id": source_document_group_id,
        "shareholder_entitlement": "UNKNOWN",
        "authoritative_cum_record_transition_dates": "",
        "separate_cash_event": "UNKNOWN",
        "basis_change_evidence": "UNKNOWN",
        "existing_capital_restructuring_coverage": "NO_DIRECT_SOURCE_CONTRACT_MAPPING",
        "taxonomy_status": decision,
        "finding": finding,
        "census_event_candidate": str(census).lower(),
    }


def _forensics(context: Mapping[str, Any]) -> list[dict[str, Any]]:
    population = context["population"]

    def membership(ticker: str, candidates: Iterable[str]) -> dict[str, Any]:
        bounds = _dependency_bounds(population, ticker)
        return {
            "fit": ticker in population["fit_tickers"],
            "application": ticker in population["app_tickers"],
            "closure": ticker in population["closure_tickers"],
            "intersects": bool(bounds and _in_geometry(candidates, bounds[0], bounds[1])),
            "dependency_start": bounds[0].isoformat() if bounds else "",
            "dependency_end": bounds[1].isoformat() if bounds else "",
        }

    rows: list[dict[str, Any]] = []
    adro_right = _find_raw_ksei(context, "ADRO", "Right Distribution", record_date="2024-11-29", distribution_date="2024-12-02")
    adro_cash = _find_raw_ksei(context, "ADRO", "Cash Dividend", record_date="2024-11-29", distribution_date="2024-12-06")
    if adro_right:
        event_id = _ksei_event_identity(adro_right)
        candidate = _candidate_date(adro_right)
        rows.append(_forensic_row("ADRO-AADI-2024-KSEI-RIGHT-DISTRIBUTION", source_kind="KSEI_REGISTERED_SECURITY_HISTORY", ticker="ADRO", label="Right Distribution", candidate=candidate, source_ref=_text(adro_right.get("source_url")), sha=_text(adro_right.get("source_sha256")), membership=membership("ADRO", [candidate]), finding="KSEI source-native rights row: ratio grants ADRO holders 1000 ADRO-H per 4389 ADRO; it does not state distribution-in-specie of AADI shares and has no cum date. The separation question is linked to this one physical source event.", decision="REQUIRES_POLICY_DECISION", census=False, source_fields=json.dumps({key: adro_right.get(key) for key in ("cum_date", "record_date", "distribution_date", "ratio_raw", "ratio_right_security", "ratio_right_value", "status")}, sort_keys=True), underlying_event_id=event_id, source_document_group_id="ADRO-AADI-2024"))
        rows[-1]["shareholder_entitlement"] = "SOURCE_NATIVE_RIGHT_TO_ACQUIRE_ADRO_H"
        rows[-1]["authoritative_cum_record_transition_dates"] = "record=2024-11-29|distribution=2024-12-02|cum=EMPTY|transition=UNRESOLVED"
        rows[-1]["basis_change_evidence"] = "NO_SOURCE_BOUND_BASIS_TRANSITION"
        rows[-1]["existing_capital_restructuring_coverage"] = "RIGHTS_HMETD_SOURCE_CONTRACT_ONLY; separation aspect not mapped"
    if adro_cash:
        cash_id = _ksei_event_identity(adro_cash)
        cash_candidate = _candidate_date(adro_cash)
        rows.append(_forensic_row("ADRO-2024-KSEI-CASH-DIVIDEND", source_kind="KSEI_REGISTERED_SECURITY_HISTORY", ticker="ADRO", label="Cash Dividend", candidate=cash_candidate, source_ref=_text(adro_cash.get("source_url")), sha=_text(adro_cash.get("source_sha256")), membership=membership("ADRO", [cash_candidate]), finding="Separate KSEI cash-dividend row: (1 ADRO : 1 IDR), with its own cum/record/distribution dates; it is not the structural entitlement row.", decision="NOT_A_SEPARATION_EVENT", census=False, source_fields=json.dumps({key: adro_cash.get(key) for key in ("cum_date", "record_date", "distribution_date", "ratio_raw", "ratio_right_security", "ratio_right_value", "status")}, sort_keys=True), underlying_event_id=cash_id, source_document_group_id="ADRO-2024-CASH-DIVIDEND"))
        rows[-1]["shareholder_entitlement"] = "CASH_DIVIDEND"
        rows[-1]["authoritative_cum_record_transition_dates"] = "cum=2024-11-26|record=2024-11-29|distribution=2024-12-06"
        rows[-1]["separate_cash_event"] = "YES"
    aadi_ksei = [row for row in context["ksei_rows"] if _ticker(row.get("ticker")) == "AADI" and _ksei_family(row)]
    rows.append(_forensic_row("AADI-2024-KSEI-NO-STRUCTURAL-ROW", source_kind="KSEI_REGISTERED_SECURITY_HISTORY", ticker="AADI", label="NO_STRUCTURAL_KSEI_ROW_IN_RETAINED_HISTORY", candidate="", source_ref="https://web.ksei.co.id/services/registered-securities/shares/lc/AADI?setLocale=en-US", sha=_text(next((row.get("source_sha256") for row in context["ksei_rows"] if _ticker(row.get("ticker")) == "AADI"), "")), membership=membership("AADI", []), finding=f"Retained AADI KSEI history has {len(aadi_ksei)} structural-family row(s) under the controlling mapping; no row ties AADI to an ADRO separation entitlement.", decision="UNKNOWN", census=False))
    idx_adro = [raw for raw, _ in context["idx_records"] if _ticker(raw.get("KodeEmiten")) == "ADRO" and _text(raw.get("JenisTindakan")) == "kurangModal"]
    for raw in idx_adro:
        capture = next((capture for candidate, capture in context["idx_records"] if candidate is raw), {})
        candidate = _candidate_date(raw)
        rows.append(_forensic_row("ADRO-IDX-KURANG-MODAL-" + _text(raw.get("id")), source_kind="IDX_GET_ISSUED_HISTORY", ticker="ADRO", label="kurangModal", candidate=candidate, source_ref=_text(capture.get("url") or capture.get("requested_url")), sha=_text(capture.get("sha256")), membership=membership("ADRO", [candidate]), finding="IDX source-native kurangModal row is dated 2026-07-13, not the 2024 ADRO/AADI separation case; it cannot be used as proof that the 2024 event is CAPITAL_RESTRUCTURING.", decision="KNOWN_SOURCE_LABEL_NOT_2024_CASE", census=False, underlying_event_id=_idx_event_identity(raw), source_document_group_id="ADRO-2026-KURANG-MODAL"))
    idx_aadi = [raw for raw, _ in context["idx_records"] if _ticker(raw.get("KodeEmiten")) == "AADI" and _text(raw.get("JenisTindakan")) == "ipo"]
    for raw in idx_aadi:
        capture = next((capture for candidate, capture in context["idx_records"] if candidate is raw), {})
        candidate = _candidate_date(raw)
        rows.append(_forensic_row("AADI-IDX-IPO-" + _text(raw.get("id")), source_kind="IDX_GET_ISSUED_HISTORY", ticker="AADI", label="ipo", candidate=candidate, source_ref=_text(capture.get("url") or capture.get("requested_url")), sha=_text(capture.get("sha256")), membership=membership("AADI", [candidate]), finding="IDX source-native ipo row records AADI on 2024-12-05; it is listing evidence, not evidence of an ADRO shareholder entitlement or a market-basis transition for ADRO.", decision="REQUIRES_POLICY_DECISION", census=False))
    for ticker in ("ADRO", "AADI"):
        linked = [row for row in context["announcements"] if _ticker(row.get("ticker")) == ticker]
        rows.append(_forensic_row(f"{ticker}-ANNOUNCEMENT-LINKAGE-{len(linked)}", source_kind="IDX_OFFICIAL_ANNOUNCEMENT_ATTACHMENT", ticker=ticker, label="NO_RETAINED_EVENT_LINKAGE_ROW", candidate="", source_ref="idx_announcement_linkages.jsonl", sha="", membership=membership(ticker, []), finding=f"No retained IDX announcement-linkage row names {ticker} for the 2024 case (matched linkage rows={len(linked)}); absence is not no-event authority.", decision="UNKNOWN", census=False))
    for index, raw in enumerate(context["schedule_parse"], start=1):
        raw_text = " | ".join(_text(value) for value in raw.values())
        if not SEPARATION_RE.search(raw_text) or not re.search(r"pemisah|spin[- ]?off|demerg|subsidiar|pups|in specie|unit usaha", raw_text, re.IGNORECASE):
            continue
        values = list(raw.values())
        label = _text(raw.get("document_title") or raw.get("title") or raw.get("subject") or (values[1] if len(values) > 1 else ""))
        ref = _text(raw.get("source_url") or (values[-2] if len(values) >= 2 else ""))
        sha = _text(raw.get("source_sha256") or (values[-1] if values else ""))
        ticker = "TPIA" if "TPIA" in raw_text.upper() else _ticker(raw.get("ticker"))
        candidate = _iso_date(raw.get("document_date") or raw.get("date"))
        tpia_underlying = _find_raw_ksei(context, "TPIA", "Voluntary Conversion", distribution_date="2024-05-20")
        underlying = _ksei_event_identity(tpia_underlying) if ticker == "TPIA" and tpia_underlying else ""
        rows.append(_forensic_row(f"SCHEDULE-TAXONOMY-{index:03d}", source_kind="KSEI_TARGETED_SCHEDULE_DOCUMENT", ticker=ticker, label=label, candidate=candidate, source_ref=ref, sha=sha, membership=membership(ticker, [candidate, _iso_date(raw.get("distribution_date")), _iso_date(raw.get("transition_date"))]), finding="Retained source-native schedule title contains Pemisahan Unit Usaha; it is linked to the existing TPIA event where available, but no controlling contract maps it to an existing frozen family. Preserve raw label and leave taxonomy unresolved.", decision="REQUIRES_POLICY_DECISION", census=False, source_fields=json.dumps(dict(raw), sort_keys=True), underlying_event_id=underlying, source_document_group_id="TPIA-2024-05-20-SEPARATION-BUYBACK" if ticker == "TPIA" else ""))
    for raw, capture in context["idx_records"]:
        if _text(raw.get("JenisTindakan")) == "gabungUsaha":
            ticker = _ticker(raw.get("KodeEmiten"))
            if ticker not in population["app_tickers"]:
                continue
            candidate = _candidate_date(raw)
            event_id = _idx_event_identity(raw)
            member = membership(ticker, [candidate])
            primary_geometry = bool(member["application"] and member["intersects"])
            finding = "Source-native gabungUsaha is already represented by the one primary MERGER-like raw event in the V1.1 census; it is outside the eight frozen families and is not force-mapped to CAPITAL_RESTRUCTURING." if primary_geometry else "Source-native gabungUsaha is retained as a forensic-only row outside the ticker's accepted dependency geometry; it is not a primary V1.1 census event and is not force-mapped to CAPITAL_RESTRUCTURING."
            rows.append(_forensic_row("IDX-TAXONOMY-GABUNG-USAHA-" + _text(raw.get("id")), source_kind="IDX_GET_ISSUED_HISTORY", ticker=ticker, label="gabungUsaha", candidate=candidate, source_ref=_text(capture.get("url") or capture.get("requested_url")), sha=_text(capture.get("sha256")), membership=member, finding=finding, decision="REQUIRES_POLICY_DECISION", census=False, underlying_event_id=event_id, source_document_group_id="IDX-GABUNG-USAHA-" + _text(raw.get("id"))))
    return rows


def _interval_authority(context: Mapping[str, Any]) -> list[dict[str, Any]]:
    population = context["population"]
    coverage = {_ticker(row.get("ticker")): row for row in context["ksei_coverage"] if _ticker(row.get("ticker"))}
    parsed_row_counts = Counter(_ticker(row.get("ticker")) for row in context["ksei_rows"] if _ticker(row.get("ticker")))
    rows: list[dict[str, Any]] = []
    for family in FROZEN_FAMILIES:
        for ticker in sorted(population["app_tickers"]):
            source = coverage.get(ticker, {})
            dependency = _dependency_bounds(population, ticker)
            capture = _best_capture(context["ksei_by_sha"], source.get("source_sha256"))
            source_bound = bool(valid_sha256(source.get("source_sha256", "")) and _text(source.get("source_url")) and capture and capture.get("hash_matches_bytes"))
            expected_rows = _text(source.get("ca_rows"))
            parsed_rows = parsed_row_counts[ticker]
            table_row_count_matches = bool(expected_rows.isdigit() and int(expected_rows) == parsed_rows)
            page_only = family in {"RIGHTS_HMETD", "STOCK_DIVIDEND"} and _upper(source.get("coverage_status")) == "COVERAGE_CERTIFIED" and source_bound and table_row_count_matches
            rows.append(
                {
                    "ticker": ticker,
                    "event_family": family,
                    "coverage_scope": "APPLICATION_AND_CLOSURE_TICKER_SCOPE_PER_TICKER_DEPENDENCY_BOUND",
                    "coverage_start_session": dependency[0].isoformat() if dependency else "",
                    "coverage_end_session": dependency[1].isoformat() if dependency else "",
                    "coverage_geometry_start": (dependency[0] - timedelta(days=60)).isoformat() if dependency else "",
                    "coverage_geometry_end": (dependency[1] + timedelta(days=60)).isoformat() if dependency else "",
                    "coverage_observed_at": _text(capture.get("accessed_at_utc")),
                    "source_contract_id": SOURCE_CONTRACT_ID,
                    "source_ref": _text(source.get("source_url")) if source_bound else "",
                    "evidence_sha256": _text(source.get("source_sha256")).lower() if source_bound else "",
                    "retained_coverage_status": _text(source.get("coverage_status")),
                    "table_row_count": expected_rows,
                    "parsed_row_count": str(parsed_rows),
                    "table_row_count_matches": str(table_row_count_matches).lower(),
                    "coverage_state": "PARSED_PAGE_ONLY" if page_only else "UNKNOWN_INTERVAL",
                    "completeness_semantics": "retained HTML has one inline Corporate Action table and ca_rows matches parsed rows; provider-level completeness is not proven" if page_only else "family-specific complete interval not proven",
                    "pagination_semantics": "no visible recordsTotal/serverSide/ajax/pagination markers; absence does not prove no server-side truncation" if page_only else "pagination behavior not proven",
                    "observed_through_semantics": "capture retrieval timestamp only; provider-defined historical as-of/no-event authority is not proven" if page_only else "retrieval timestamp/history-present flag is insufficient",
                    "family_coverage_semantics": "positive source-native label presence only; full-family and no-event coverage are not proven" if page_only else "family coverage not proven",
                    "as_of_semantics": "not source-contract certified" if page_only else "not source-contract certified",
                    "verdict": "UNKNOWN_INTERVAL" if page_only else "UNKNOWN_INTERVAL",
                }
            )
    return rows


def _negative_coverage(context: Mapping[str, Any]) -> list[dict[str, Any]]:
    categories = {
        "STOCK_SPLIT": "stockSplit",
        "REVERSE_SPLIT": "reverseStock",
        "RIGHTS_HMETD": "hmetd",
        "STOCK_DIVIDEND": "dividenSaham",
        "BONUS_SHARES": "sahamBonus",
        "MANDATORY_CONVERSION": "obligasiWajibKonversi",
        "VOLUNTARY_CONVERSION": "konversiSaham",
        "CAPITAL_RESTRUCTURING": "kurangModal",
        "MERGER": "gabungUsaha",
    }
    rows: list[dict[str, Any]] = []
    for family, category in categories.items():
        selected = [row for row in context["pit_requests"] if _text((row.get("params") or {}).get("caType")) == category]
        hashes = sorted({_text(row.get("sha256")).lower() for row in selected if valid_sha256(row.get("sha256", ""))})
        empty = 0
        nonempty = 0
        for request in selected:
            path = _resolve_path(request.get("path"), context["pit_root"])
            if not path or not path.is_file():
                continue
            try:
                value = _read_json(path)
            except (OSError, ValueError):
                continue
            data = value.get("data", []) if isinstance(value, Mapping) else value
            if data:
                nonempty += 1
            else:
                empty += 1
        rows.append(
            {
                "event_family": family,
                "idx_ca_type": category,
                "request_count": len(selected),
                "successful_empty_response_count": empty,
                "successful_nonempty_response_count": nonempty,
                "source_contract_id": IDX_SOURCE_CONTRACT_ID,
                "source_ref": "https://www.idx.id/primary/ListingActivity/GetIssuedHistory?caType=" + category,
                "evidence_sha256": _canonical_hash(hashes),
                "negative_semantics": "UNKNOWN_NO_EXHAUSTIVE_NO_EVENT_CONTRACT",
                "date_interval": "2018-01-01..2026-08-14",
                "verdict": "UNKNOWN",
                "notes": "IDX scraper treats a data list as records but retained contract does not define successful zero rows as no-event authority",
            }
        )
    return rows


def _family_authority(context: Mapping[str, Any], primary: Sequence[Mapping[str, Any]], transitions: Sequence[Mapping[str, Any]], intervals: Sequence[Mapping[str, Any]], forensics: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    transition_by = Counter(row.get("event_family") for row in transitions if row.get("record_kind") == "RAW_SOURCE_EVENT")
    resolved_by = Counter(row.get("event_family") for row in transitions if row.get("record_kind") == "RAW_SOURCE_EVENT" and row.get("v11_raw_recomputed_class") == "RESOLVED")
    for family in FROZEN_FAMILIES:
        certified_tickers = {row["ticker"] for row in intervals if row.get("event_family") == family and row.get("coverage_state") == "CERTIFIED_INTERVAL"}
        parsed_page_tickers = {row["ticker"] for row in intervals if row.get("event_family") == family and row.get("coverage_state") == "PARSED_PAGE_ONLY"}
        family_primary = [row for row in primary if row.get("event_family") == family]
        rows.append(
            {
                "event_family": family,
                "frozen_family": "true",
                "raw_primary_event_count": len(family_primary),
                "raw_resolved_transition_count": resolved_by[family],
                 "raw_unresolved_transition_count": transition_by[family] - resolved_by[family],
                 "interval_certified_ticker_count": len(certified_tickers),
                 "interval_parsed_page_only_ticker_count": len(parsed_page_tickers),
                 "interval_missing_or_unknown_ticker_count": len(context["population"]["app_tickers"]) - len(certified_tickers),
                 "interval_certified_ticker_set_sha256": canonical_set_hash(certified_tickers),
                 "interval_parsed_page_only_ticker_set_sha256": canonical_set_hash(parsed_page_tickers),
                "source_family_certified": "false",
                "date_level_attestation": "false",
                "conflict_status": "UNKNOWN_CONFLICT_REQUIRES_SOURCE_ADJUDICATION" if family == "CAPITAL_RESTRUCTURING" else "NO_CONFLICT_PROOF",
                 "verdict": "FAIL_PAGE_ONLY_PARTIAL_SCOPE" if parsed_page_tickers else "UNKNOWN",
                 "notes": "retained KSEI pages support parsed-row facts only; provider completeness, pagination absence, observed-through as-of, and no-event semantics are not certified",
            }
        )
    taxonomy = [row for row in forensics if row.get("taxonomy_status") == "REQUIRES_POLICY_DECISION"]
    rows.append(
        {
            "event_family": "UNKNOWN_TAXONOMY_CANDIDATES",
            "frozen_family": "false",
            "raw_primary_event_count": 0,
            "raw_resolved_transition_count": 0,
            "raw_unresolved_transition_count": 0,
            "taxonomy_finding_count": len(taxonomy),
            "taxonomy_finding_linked_to_underlying_event_count": sum(bool(row.get("underlying_event_id")) for row in taxonomy),
            "interval_certified_ticker_count": 0,
            "interval_parsed_page_only_ticker_count": 0,
            "interval_missing_or_unknown_ticker_count": len(context["population"]["app_tickers"]),
            "interval_certified_ticker_set_sha256": canonical_set_hash(()),
            "interval_parsed_page_only_ticker_set_sha256": canonical_set_hash(()),
            "source_family_certified": "false",
            "date_level_attestation": "false",
            "conflict_status": "REQUIRES_POLICY_DECISION",
            "verdict": "UNKNOWN",
            "notes": "separation-like labels are preserved without force-mapping: Pemisahan Unit Usaha, gabungUsaha, ADRO/AADI case",
        }
    )
    return rows


def _population_authority(context: Mapping[str, Any], intervals: Sequence[Mapping[str, Any]], negative: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    population = context["population"]
    rows: list[dict[str, Any]] = []
    for name, ids in (("FIT", population["fit_ids"]), ("APPLICATION", population["app_ids"]), ("CLOSURE", population["closure_ids"])):
        rows.append(
            {
                "population": name,
                "identity_count": len(ids),
                "ticker_count": len({ticker for ticker, _ in ids}),
                "identity_set_sha256": canonical_set_hash(f"{ticker}|{day}" for ticker, day in ids),
                "ticker_set_sha256": canonical_set_hash(ticker for ticker, _ in ids),
                "fit_contained_in_application": str(population["fit_ids"] <= population["app_ids"]).lower(),
                "application_contained_in_closure": str(population["app_ids"] <= population["closure_ids"]).lower(),
                "source_family_certified": "false",
                "date_level_attestation": "false",
                "expanded_scope_expected": "true" if name in {"APPLICATION", "CLOSURE"} else "false",
                "verdict": "PASS_IDENTITY_CONTAINMENT_ONLY" if ((name == "FIT" and population["fit_ids"] <= population["app_ids"]) or (name == "APPLICATION" and population["app_ids"] <= population["closure_ids"])) else "FAIL",
                "notes": "identity arithmetic is not source-family or temporal certification",
            }
        )
    return rows


def _gap_matrix(context: Mapping[str, Any], family: Sequence[Mapping[str, Any]], intervals: Sequence[Mapping[str, Any]], negative: Sequence[Mapping[str, Any]], transition_summary: Mapping[str, Any], forensics: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    population = context["population"]
    unknown_taxonomy = [row for row in forensics if row.get("taxonomy_status") == "REQUIRES_POLICY_DECISION"]
    page_only_ksei = {row["ticker"] for row in intervals if row.get("event_family") == "RIGHTS_HMETD" and row.get("coverage_state") == "PARSED_PAGE_ONLY"}
    missing_ksei = sorted(population["app_tickers"] - page_only_ksei)
    missing_hash = canonical_set_hash(missing_ksei)
    return [
        {"gap_id": "V11-G001", "area": "FULL_716_SOURCE_FAMILY_COVERAGE", "verdict": "FAIL", "exact_gap": "full expanded application and closure scope lacks family-certified positive and no-event evidence", "ticker_count": len(population["app_tickers"]), "ticker_set_sha256": canonical_set_hash(population["app_tickers"]), "acquisition_requirement": "ACQ-V11-001"},
        {"gap_id": "V11-G002", "area": "KSEI_INTERVAL_COVERAGE", "verdict": "FAIL_PAGE_ONLY_PARTIAL", "exact_gap": f"retained KSEI pages are parsed-page-only for {len(page_only_ksei)}/716 tickers; provider completeness/as-of/no-event authority is not proven and unresolved or absent ticker count={len(missing_ksei)}", "ticker_count": len(missing_ksei), "ticker_set_sha256": missing_hash, "acquisition_requirement": "ACQ-V11-002"},
        {"gap_id": "V11-G003", "area": "IDX_NEGATIVE_SEMANTICS", "verdict": "UNKNOWN", "exact_gap": "successful empty GetIssuedHistory responses have no source-defined exhaustive no-event meaning", "ticker_count": len(population["app_tickers"]), "ticker_set_sha256": canonical_set_hash(population["app_tickers"]), "acquisition_requirement": "ACQ-V11-003"},
        {"gap_id": "V11-G004", "area": "TRANSITION_SEMANTICS", "verdict": "FAIL_OR_UNKNOWN", "exact_gap": f"raw events resolved={transition_summary.get('raw_resolved_count', 0)}; raw events unresolved={transition_summary.get('raw_unresolved_count', 0)}; every unresolved event identity requires explicit transition evidence", "ticker_count": transition_summary.get("raw_unresolved_ticker_count", 0), "ticker_set_sha256": transition_summary.get("raw_unresolved_ticker_set_sha256", canonical_set_hash(())), "acquisition_requirement": "ACQ-V11-004"},
        {"gap_id": "V11-G005", "area": "CROSS_SOURCE_CONFLICTS", "verdict": "UNKNOWN", "exact_gap": "retained family/date conflicts remain source-contract unresolved", "ticker_count": 3, "ticker_set_sha256": canonical_set_hash(["ISAT", "MEGA", "SCMA"]), "acquisition_requirement": "ACQ-V11-005"},
        {"gap_id": "V11-G006", "area": "SEPARATION_TAXONOMY", "verdict": "UNKNOWN", "exact_gap": f"{len(unknown_taxonomy)} retained separation-like/source-native candidates require policy decision; no force-map to CAPITAL_RESTRUCTURING", "ticker_count": len({row.get('ticker') for row in unknown_taxonomy if row.get('ticker')}), "ticker_set_sha256": canonical_set_hash(row.get("ticker", "") for row in unknown_taxonomy), "acquisition_requirement": "ACQ-V11-006"},
        {"gap_id": "V11-G007", "area": "IDENTITY_CONTAINMENT", "verdict": "PASS_IDENTITY_ONLY", "exact_gap": "none; fit identities are contained in application and application identities in closure", "ticker_count": len(population["closure_tickers"]), "ticker_set_sha256": canonical_set_hash(population["closure_tickers"]), "acquisition_requirement": "none"},
        {"gap_id": "V11-G008", "area": "TEMPORAL_ASOF_PROVENANCE", "verdict": "FAIL", "exact_gap": "full 716 identity-level as-of/date attestation with source ref and hash is absent", "ticker_count": len(population["closure_tickers"]), "ticker_set_sha256": canonical_set_hash(population["closure_tickers"]), "acquisition_requirement": "ACQ-V11-001"},
    ]


def _acquisition(context: Mapping[str, Any], forensics: Sequence[Mapping[str, Any]], transitions: Sequence[Mapping[str, Any]], transition_summary: Mapping[str, Any], intervals: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    population = context["population"]
    intervals = list(intervals) if intervals is not None else _interval_authority(context)
    page_only_ksei = {row["ticker"] for row in intervals if row.get("event_family") == "RIGHTS_HMETD" and row.get("coverage_state") == "PARSED_PAGE_ONLY"}
    missing_ksei = sorted(population["app_tickers"] - page_only_ksei)
    raw_unresolved = [
        row for row in transitions
        if row.get("record_kind") == "RAW_SOURCE_EVENT" and _text(row.get("v11_raw_recomputed_class")) != "RESOLVED"
    ]
    unresolved_ids = [_text(row.get("event_id")) for row in raw_unresolved if _text(row.get("event_id"))]
    unresolved_tickers = sorted({_ticker(row.get("ticker")) for row in raw_unresolved if _ticker(row.get("ticker"))})
    prior_schedule_required = sum(_upper(row.get("prior_derived_class")) == "SCHEDULE_REQUIRED" for row in raw_unresolved)
    additional_unresolved = len(raw_unresolved) - prior_schedule_required
    ticker_intervals = {}
    for ticker in sorted(population["closure_tickers"]):
        bounds = _dependency_bounds(population, ticker)
        if bounds:
            ticker_intervals[ticker] = {
                "dependency_start": bounds[0].isoformat(),
                "dependency_end": bounds[1].isoformat(),
                "geometry_start": (bounds[0] - timedelta(days=60)).isoformat(),
                "geometry_end": (bounds[1] + timedelta(days=60)).isoformat(),
            }
    def event_identity(row: Mapping[str, Any]) -> dict[str, Any]:
        family = _text(row.get("event_family"))
        missing_semantics = (
            "official exchange session mapping for source-native KSEI cum date"
            if row.get("source_kind") == "KSEI_REGISTERED_SECURITY_HISTORY" and _text(row.get("cum_date")) and not _next_session(_iso_date(row.get("cum_date")), context["sessions"])
            else "REGULAR_MARKET_EX_DATE or REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE linked to this event, with source ref and valid evidence SHA"
        )
        return {
            "event_id": _text(row.get("event_id")),
            "ticker": _ticker(row.get("ticker")),
            "structural_family": family,
            "source_native_label": _text(row.get("source_native_label")),
            "candidate_date": _iso_date(row.get("candidate_date")),
            "source_ref": _text(row.get("source_ref")),
            "evidence_sha256": _text(row.get("evidence_sha256")).lower(),
            "missing_transition_semantic_source": missing_semantics,
            "transition_lower_bound_certified": False,
        }
    unresolved_events = [event_identity(row) for row in sorted(raw_unresolved, key=lambda value: (_ticker(value.get("ticker")), _iso_date(value.get("candidate_date")), _text(value.get("event_id"))))]
    application_tickers = sorted(population["app_tickers"])
    closure_tickers = sorted(population["closure_tickers"])
    idx_categories = {
        "STOCK_SPLIT": "stockSplit",
        "REVERSE_SPLIT": "reverseStock",
        "RIGHTS_HMETD": "hmetd",
        "STOCK_DIVIDEND": "dividenSaham",
        "BONUS_SHARES": "sahamBonus",
        "MANDATORY_CONVERSION": "obligasiWajibKonversi",
        "VOLUNTARY_CONVERSION": "konversiSaham",
        "CAPITAL_RESTRUCTURING": "kurangModal",
        "MERGER": "gabungUsaha",
    }
    common_fields = {
        "historical_interval": ticker_intervals,
        "source_native_candidate_dates": "retained candidates are enumerated in exact_event_identities where event-specific; bulk units must preserve source-native dates",
        "fields_required": ["ticker/issuer identity", "source-native event/action label", "candidate/effective dates", "source ref", "evidence SHA-256", "publication/as-of metadata"],
        "positive_event_requirement": True,
        "no_event_completeness_requirement": True,
        "exact_transition_semantic_requirement": ["REGULAR_MARKET_EX_DATE", "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE"],
        "publication_as_of_requirement": "source-defined publication/as-of or observed-through semantics bound to source ref and evidence SHA",
        "expected_source_ref_hash_contract": {"source_contract_id": SOURCE_CONTRACT_ID, "source_ref_required": True, "evidence_sha256_required": True, "hash_binding_required": True},
        "empty_success_has_authority": False,
    }
    requirements: list[dict[str, Any]] = []
    requirements.append({
        "requirement_id": "ACQ-V11-001", "unit_id": "ACQ-V11-001-CAPABILITY-KSEI", "source_provider": "KSEI",
        "endpoint_page_document_family": "registered-security shares/lc/{ticker}", "request_type": "CAPABILITY_VERIFICATION_REQUIRED",
        "exact_action_category_parameter": {"path_template": "https://web.ksei.co.id/services/registered-securities/shares/lc/{ticker}", "query": "setLocale=en-US"},
        "ticker_set": ["AADI", "ADRO", "AALI"], "ticker_set_sha256": canonical_set_hash(["AADI", "ADRO", "AALI"]), "ticker_count": 3,
        "exact_event_ids": [], "structural_family": "ALL_FROZEN_FAMILIES", "historical_interval": {ticker: ticker_intervals[ticker] for ticker in ("AADI", "ADRO", "AALI") if ticker in ticker_intervals},
        "source_native_candidate_dates": [], "fields_required": ["raw HTML bytes", "table/pagination behavior", "coverage/as-of semantics", "source-native event rows"],
        "positive_event_requirement": True, "no_event_completeness_requirement": True,
        "exact_transition_semantic_requirement": ["source-contract family semantics", "not candidate-date inference"],
        "publication_as_of_requirement": "prove whether retrieval is provider-defined observed-through/as-of or only capture time",
        "expected_source_ref_hash_contract": {"source_contract_id": SOURCE_CONTRACT_ID, "source_ref_pattern": "registered-security shares/lc/{ticker}?setLocale=en-US", "evidence_sha256": "SHA-256 of retained response bytes"},
        "empty_success_has_authority": False, "capability_status": "CAPABILITY_VERIFICATION_REQUIRED",
        "request_count_derivation": {"formula": "one bounded capability request per representative ticker", "request_count": 3, "status": "EXACT_BOUNDED_CAPABILITY_CHECK"},
        "why_local_insufficient": "retained pages show parsed rows but do not prove provider completeness, pagination absence, or historical as-of/no-event semantics",
    })
    requirements.append({
        "requirement_id": "ACQ-V11-001", "unit_id": "ACQ-V11-001-BULK-KSEI-FULL-716", "source_provider": "KSEI",
        "endpoint_page_document_family": "registered-security shares/lc/{ticker}", "request_type": "BULK_ACQUISITION_REQUIRED_AFTER_CAPABILITY_VERIFICATION",
        "exact_action_category_parameter": {"path_template": "https://web.ksei.co.id/services/registered-securities/shares/lc/{ticker}", "query": "setLocale=en-US"},
        "ticker_set": application_tickers, "ticker_set_sha256": canonical_set_hash(application_tickers), "ticker_count": len(application_tickers),
        "exact_event_ids": [], "structural_family": "ALL_FROZEN_FAMILIES", "historical_interval": ticker_intervals,
        "source_native_candidate_dates": [], "fields_required": common_fields["fields_required"], "positive_event_requirement": True, "no_event_completeness_requirement": True,
        "exact_transition_semantic_requirement": common_fields["exact_transition_semantic_requirement"], "publication_as_of_requirement": common_fields["publication_as_of_requirement"],
        "expected_source_ref_hash_contract": {"source_contract_id": SOURCE_CONTRACT_ID, "source_ref_pattern": "registered-security shares/lc/{ticker}?setLocale=en-US", "evidence_sha256": "SHA-256 of raw response bytes"},
        "empty_success_has_authority": False, "capability_status": "BULK_ACQUISITION_REQUIRED_AFTER_CAPABILITY_VERIFICATION",
        "request_count_derivation": {"formula": "1 page request × exact 716 ticker set", "minimum_request_count": len(application_tickers), "request_count": len(application_tickers), "status": "DERIVED_IF_KSEI_PAGE_CAPABILITY_IS_CONFIRMED"},
        "why_local_insufficient": "149 application/closure tickers lack retained parsed-page evidence and all 716 lack source-contract completeness/as-of/no-event proof",
    })
    requirements.append({
        "requirement_id": "ACQ-V11-002", "unit_id": "ACQ-V11-002-BULK-KSEI-RESIDUAL-149", "source_provider": "KSEI",
        "endpoint_page_document_family": "registered-security shares/lc/{ticker}; RIGHTS_HMETD and STOCK_DIVIDEND interval residual",
        "request_type": "BULK_ACQUISITION_REQUIRED_AFTER_CAPABILITY_VERIFICATION", "exact_action_category_parameter": {"path_template": "https://web.ksei.co.id/services/registered-securities/shares/lc/{ticker}", "query": "setLocale=en-US"},
        "ticker_set": missing_ksei, "ticker_set_sha256": canonical_set_hash(missing_ksei), "ticker_count": len(missing_ksei), "exact_event_ids": [],
        "structural_family": ["RIGHTS_HMETD", "STOCK_DIVIDEND"], "historical_interval": {ticker: ticker_intervals[ticker] for ticker in missing_ksei if ticker in ticker_intervals},
        "source_native_candidate_dates": [], "fields_required": ["complete raw page", "source-native rows", "publication/as-of metadata", "source ref", "valid evidence SHA-256"],
        "positive_event_requirement": True, "no_event_completeness_requirement": True, "exact_transition_semantic_requirement": ["family-specific source contract", "no candidate-date inference"],
        "publication_as_of_requirement": common_fields["publication_as_of_requirement"], "expected_source_ref_hash_contract": {"source_contract_id": SOURCE_CONTRACT_ID, "source_ref_pattern": "registered-security shares/lc/{ticker}?setLocale=en-US", "evidence_sha256": "SHA-256 of raw response bytes"},
        "empty_success_has_authority": False, "capability_status": "BULK_ACQUISITION_REQUIRED_AFTER_CAPABILITY_VERIFICATION",
        "request_count_derivation": {"formula": "1 page request × exact residual ticker set", "request_count": len(missing_ksei), "status": "DERIVED_IF_KSEI_PAGE_CAPABILITY_IS_CONFIRMED"},
        "why_local_insufficient": "residual set is absent or unresolved in retained KSEI page coverage; page-only positives do not certify intervals",
    })
    for family, category in idx_categories.items():
        requirements.append({
            "requirement_id": "ACQ-V11-003", "unit_id": f"ACQ-V11-003-CAPABILITY-IDX-{category}", "source_provider": "IDX GetIssuedHistory",
            "endpoint_page_document_family": "https://www.idx.id/primary/ListingActivity/GetIssuedHistory", "request_type": "CAPABILITY_VERIFICATION_REQUIRED",
            "exact_action_category_parameter": {"caType": category, "dateFrom": "20180101", "dateTo": "20260814", "start": 0, "length": 250},
            "ticker_set": [], "ticker_set_sha256": canonical_set_hash(()), "ticker_count": 0, "ticker_dimension": "NONE_PROVEN; endpoint is cross-issuer and ticker set is not a request filter",
            "required_certification_ticker_set": application_tickers, "required_certification_ticker_set_sha256": canonical_set_hash(application_tickers), "exact_event_ids": [], "structural_family": family,
            "historical_interval": {"start": "2018-01-01", "end": "2026-08-14"}, "source_native_candidate_dates": [], "fields_required": ["raw JSON bytes", "recordsTotal or equivalent completeness signal", "category/action label", "issuer identity", "TanggalPencatatan", "source ref/hash"],
            "positive_event_requirement": True, "no_event_completeness_requirement": True, "exact_transition_semantic_requirement": ["category row is not a transition date", "independent accepted transition evidence required"],
            "publication_as_of_requirement": "source response capture and any source-defined historical interval/as-of semantics", "expected_source_ref_hash_contract": {"source_contract_id": IDX_SOURCE_CONTRACT_ID, "source_ref_pattern": "GetIssuedHistory?caType={category}&dateFrom=20180101&dateTo=20260814&start={start}&length=250", "evidence_sha256": "SHA-256 of raw JSON bytes"},
            "empty_success_has_authority": False, "capability_status": "CAPABILITY_VERIFICATION_REQUIRED", "request_count_derivation": {"formula": "one first-page capability request for this exact caType parameter", "request_count": 1, "status": "EXACT_BOUNDED_CAPABILITY_CHECK"},
            "why_local_insufficient": "retained endpoint has page-shaped responses but category-exhaustive and successful-empty no-event semantics are unproven",
        })
        requirements.append({
            "requirement_id": "ACQ-V11-003", "unit_id": f"ACQ-V11-003-BULK-IDX-{category}", "source_provider": "IDX GetIssuedHistory",
            "endpoint_page_document_family": "https://www.idx.id/primary/ListingActivity/GetIssuedHistory", "request_type": "BULK_ACQUISITION_REQUIRED_AFTER_CAPABILITY_VERIFICATION",
            "exact_action_category_parameter": {"caType": category, "dateFrom": "20180101", "dateTo": "20260814", "start": "0,250,...", "length": 250}, "ticker_set": application_tickers, "ticker_set_sha256": canonical_set_hash(application_tickers), "ticker_count": len(application_tickers), "ticker_dimension": "endpoint-wide response; ticker set is certification target, not a proven request filter",
            "exact_event_ids": [], "structural_family": family, "historical_interval": {"start": "2018-01-01", "end": "2026-08-14"}, "source_native_candidate_dates": [], "fields_required": ["all category rows", "issuer identity", "source-native action", "TanggalPencatatan", "raw response ref/hash", "pagination/completeness evidence"],
            "positive_event_requirement": True, "no_event_completeness_requirement": True, "exact_transition_semantic_requirement": ["separate accepted transition evidence for each event"], "publication_as_of_requirement": common_fields["publication_as_of_requirement"], "expected_source_ref_hash_contract": {"source_contract_id": IDX_SOURCE_CONTRACT_ID, "source_ref_pattern": "GetIssuedHistory?caType={category}&dateFrom=20180101&dateTo=20260814&start={start}&length=250", "evidence_sha256": "SHA-256 of each raw JSON page"},
            "empty_success_has_authority": False, "capability_status": "BULK_ACQUISITION_REQUIRED_AFTER_CAPABILITY_VERIFICATION", "request_count_derivation": {"formula": "ceil(provider-defined complete record count / 250)", "request_count": None, "status": "NOT_DERIVABLE_BEFORE_CAPABILITY_VERIFICATION", "retained_page_shape": "start=0,250,500 observed but not an exhaustive contract"},
            "why_local_insufficient": "current retained pages do not prove complete category coverage or page count",
        })
    requirements.append({
        "requirement_id": "ACQ-V11-004", "unit_id": "ACQ-V11-004-CAPABILITY-SCHEDULE", "source_provider": "KSEI schedule / issuer official source",
        "endpoint_page_document_family": "event-specific official schedule documents", "request_type": "CAPABILITY_VERIFICATION_REQUIRED",
        "exact_action_category_parameter": {"document_reference": ["KSEI-9582/JKU/0524", "KSEI-27597/JKU/1124"], "semantic_fields": ["REGULAR_MARKET_EX_DATE", "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE"]},
        "ticker_set": ["TPIA", "ADRO"], "ticker_set_sha256": canonical_set_hash(["TPIA", "ADRO"]), "ticker_count": 2, "exact_event_ids": [], "structural_family": "SCHEDULE_REQUIRED_FAMILIES",
        "historical_interval": {ticker: ticker_intervals[ticker] for ticker in ("TPIA", "ADRO") if ticker in ticker_intervals}, "source_native_candidate_dates": ["2024-05-07", "2024-11-29"], "fields_required": ["official document bytes", "KSEI reference", "issuer/source ref", "valid SHA-256", "explicit accepted transition semantic", "publication date"],
        "positive_event_requirement": True, "no_event_completeness_requirement": False, "exact_transition_semantic_requirement": ["REGULAR_MARKET_EX_DATE", "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE"], "publication_as_of_requirement": "document publication date plus source-bound document bytes", "expected_source_ref_hash_contract": {"source_contract_id": SOURCE_CONTRACT_ID, "source_ref_required": True, "evidence_sha256_required": True, "ksei_reference_required": True}, "empty_success_has_authority": False, "capability_status": "CAPABILITY_VERIFICATION_REQUIRED", "request_count_derivation": {"formula": "two retained reference/document capability checks", "request_count": 2, "status": "EXACT_BOUNDED_CAPABILITY_CHECK"}, "why_local_insufficient": "retained targeted schedules are mostly unresolved and do not establish an exhaustive lookup capability",
    })
    requirements.append({
        "requirement_id": "ACQ-V11-004", "unit_id": "ACQ-V11-004-BULK-TRANSITION-291", "source_provider": "KSEI schedule / issuer official source", "endpoint_page_document_family": "event-specific official schedule documents with accepted regular-market transition semantic", "request_type": "BULK_ACQUISITION_REQUIRED_AFTER_CAPABILITY_VERIFICATION",
        "exact_action_category_parameter": {"lookup": "one exact event identity per unit unless a source-backed document-deduplication map is proven", "accepted_semantics": ["REGULAR_MARKET_EX_DATE", "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE"]},
        "ticker_set": unresolved_tickers, "ticker_set_sha256": canonical_set_hash(unresolved_tickers), "ticker_count": len(unresolved_tickers), "exact_event_ids": unresolved_events, "event_id_set_sha256": canonical_set_hash(unresolved_ids), "structural_family": "PER_EVENT_UNRESOLVED_RAW_TRANSITIONS", "historical_interval": ticker_intervals,
        "source_native_candidate_dates": [{"event_id": item["event_id"], "ticker": item["ticker"], "candidate_date": item["candidate_date"]} for item in unresolved_events], "fields_required": ["exact event linkage", "source-native candidate dates", "accepted transition semantic", "KSEI reference/document ref", "publication date", "source ref", "valid evidence SHA-256"], "positive_event_requirement": True, "no_event_completeness_requirement": False, "exact_transition_semantic_requirement": ["REGULAR_MARKET_EX_DATE", "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE", "or separately validated source-specific lower-bound contract"], "publication_as_of_requirement": "event-specific publication/source-as-of evidence bound to the exact event identity", "expected_source_ref_hash_contract": {"source_contract_id": SOURCE_CONTRACT_ID, "source_ref_required": True, "evidence_sha256_required": True, "hash_binding_required": True, "deduplication_map_required_if_request_count_less_than_event_count": True}, "empty_success_has_authority": False, "capability_status": "BULK_ACQUISITION_REQUIRED_AFTER_CAPABILITY_VERIFICATION", "request_count_derivation": {"formula": "one request/evidence unit per exact unresolved event identity; 94 prior schedule-required + 197 additional raw unresolved", "prior_schedule_required_count": prior_schedule_required, "additional_unresolved_count": additional_unresolved, "minimum_request_count": len(unresolved_events), "request_count": len(unresolved_events), "status": "MINIMUM_EXACT_EVENT_UNIT_COUNT; no source-backed deduplication proven"}, "why_local_insufficient": "all unresolved raw event rows lack certified transition lower-bound provenance; candidate dates are not transitions",
    })
    requirements.append({
        "requirement_id": "ACQ-V11-005", "unit_id": "ACQ-V11-005-BULK-CONFLICT-3", "source_provider": "authoritative source-contract adjudication", "endpoint_page_document_family": "conflict-specific official source records", "request_type": "BULK_ACQUISITION_REQUIRED_AFTER_CAPABILITY_VERIFICATION", "exact_action_category_parameter": {"conflict_scope": ["ISAT", "MEGA", "SCMA"]}, "ticker_set": ["ISAT", "MEGA", "SCMA"], "ticker_set_sha256": canonical_set_hash(["ISAT", "MEGA", "SCMA"]), "ticker_count": 3, "exact_event_ids": [], "structural_family": "CONFLICTING_FAMILY_OR_DATE_SEMANTICS", "historical_interval": {ticker: ticker_intervals[ticker] for ticker in ("ISAT", "MEGA", "SCMA") if ticker in ticker_intervals}, "source_native_candidate_dates": [], "fields_required": ["conflicting raw rows", "source-native family/date fields", "adjudicating source ref/hash", "accepted transition semantic"], "positive_event_requirement": True, "no_event_completeness_requirement": False, "exact_transition_semantic_requirement": ["source-contract adjudicated transition"], "publication_as_of_requirement": common_fields["publication_as_of_requirement"], "expected_source_ref_hash_contract": {"source_contract_id": SOURCE_CONTRACT_ID, "source_ref_required": True, "evidence_sha256_required": True}, "empty_success_has_authority": False, "capability_status": "BULK_ACQUISITION_REQUIRED_AFTER_CAPABILITY_VERIFICATION", "request_count_derivation": {"formula": "one conflict-resolution evidence unit per exact ticker", "request_count": 3, "status": "EXACT_BOUNDED_TICKER_UNIT_COUNT"}, "why_local_insufficient": "retained family/date conflict is unresolved by the current source contract",
    })
    taxonomy = [row for row in forensics if row.get("taxonomy_status") == "REQUIRES_POLICY_DECISION"]
    taxonomy_tickers = sorted({_ticker(row.get("ticker")) for row in taxonomy if _ticker(row.get("ticker"))})
    requirements.append({
        "requirement_id": "ACQ-V11-006", "unit_id": "ACQ-V11-006-POLICY-TAXONOMY", "source_provider": "policy plus official source semantics", "endpoint_page_document_family": "separation/demerger/subsidiary-distribution/PUPS/distribution-in-specie candidate evidence", "request_type": "POLICY_DECISION_REQUIRED_BEFORE_ACQUISITION", "exact_action_category_parameter": {"terms": ["Pemisahan Unit Usaha", "gabungUsaha", "Right Distribution", "ipo"]}, "ticker_set": taxonomy_tickers, "ticker_set_sha256": canonical_set_hash(taxonomy_tickers), "ticker_count": len(taxonomy_tickers), "exact_event_ids": [{"finding_id": _text(row.get("finding_id")), "underlying_event_id": _text(row.get("underlying_event_id")), "ticker": _ticker(row.get("ticker")), "source_native_label": _text(row.get("source_native_label")), "candidate_date": _iso_date(row.get("candidate_date")), "source_ref": _text(row.get("source_ref")), "evidence_sha256": _text(row.get("evidence_sha256")).lower()} for row in taxonomy], "structural_family": "UNKNOWN_TAXONOMY", "historical_interval": ticker_intervals, "source_native_candidate_dates": [{"finding_id": _text(row.get("finding_id")), "candidate_date": _iso_date(row.get("candidate_date"))} for row in taxonomy], "fields_required": ["exact raw label", "underlying event identity", "shareholder entitlement semantics", "source ref", "valid evidence SHA-256", "policy decision"], "positive_event_requirement": False, "no_event_completeness_requirement": False, "exact_transition_semantic_requirement": ["not applicable until taxonomy policy is decided"], "publication_as_of_requirement": "source-bound publication evidence if policy authorizes follow-up", "expected_source_ref_hash_contract": {"source_ref_required": True, "evidence_sha256_required": True}, "empty_success_has_authority": False, "capability_status": "CAPABILITY_VERIFICATION_REQUIRED_ONLY_AFTER_POLICY_DECISION", "request_count_derivation": {"formula": "zero acquisition requests while taxonomy policy is unresolved", "request_count": 0, "status": "NO_ACQUISITION_AUTHORIZED"}, "why_local_insufficient": "retained raw labels are candidates, not a frozen family contract; no force-map is allowed",
    })
    return {
        "schema_version": "ca_source_authority_acquisition_requirements_v11",
        "status": "STOP_NO_PROVIDER_ACQUISITION_AUTHORIZED",
        "scope": {
            "fit": 629, "fit_ticker_set_sha256": canonical_set_hash(population["fit_tickers"]),
            "application": 716, "application_ticker_set_sha256": canonical_set_hash(application_tickers),
            "closure": 716, "closure_ticker_set_sha256": canonical_set_hash(closure_tickers),
            "closure_start": population["closure_start"],
            "closure_end": population["closure_end"],
            "application_tickers": application_tickers,
            "closure_tickers": closure_tickers,
        },
        "requirements": requirements,
        "reconciliation": {"raw_unresolved_transition_count": len(raw_unresolved), "prior_schedule_required_count": prior_schedule_required, "additional_unresolved_count": additional_unresolved, "raw_unresolved_event_id_set_sha256": canonical_set_hash(unresolved_ids), "raw_unresolved_ticker_set_sha256": canonical_set_hash(unresolved_tickers), "minimum_event_specific_evidence_units": len(unresolved_events), "previous_estimated_event_specific_request_count": 94, "previous_estimate_sufficient": False, "explanation": "94 was the prior SCHEDULE_REQUIRED subset; 197 additional raw unresolved events also lack accepted transition evidence, so 291 exact event identities are the minimum absent a proven source-document deduplication map"},
        "guardrails": {"provider_calls": False, "phase_e_run": False, "outcomes_accessed": False, "targets_accessed": False, "model_fit": False, "model_refit": False, "model_scoring": False, "counter_mutated": False, "canonical_historical_data_rewritten": False},
        "next_step": "Return for ChatGPT review; no provider acquisition or scientific execution is authorized by this artifact.",
    }


def _git_state(repo_root: Path | None) -> dict[str, str]:
    if repo_root is None:
        return {"repository": "", "branch": "", "head": ""}
    def run(*args: str) -> str:
        try:
            return subprocess.check_output(["git", "-C", str(repo_root), *args], text=True, stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError):
            return "UNKNOWN"
    return {"repository": run("config", "--get", "remote.origin.url"), "branch": run("branch", "--show-current"), "head": run("rev-parse", "HEAD"), "status": run("status", "--short")}


def _input_paths(project_root: Path, repo_root: Path | None) -> list[Path]:
    roots = [
        project_root / R31_ROOT_NAME,
        project_root / "idx-v4-ksei-ca-history-census-20260817-v1",
        project_root / "idx-corporate-action-pit-source-audit-20260814-v1-final",
        project_root / "idx-v4-ca-schedule-evidence-20260818-v3",
        project_root / "idx-v4-ca-event-window-final-20260818-v3",
        project_root / "idx-v4-x1-clean-historical-input-stage-r2-20260820" / "official_exchange_sessions_1260.csv",
        Path(r"C:\Users\Sam\OneDrive\Documents\Project\idx-trade-price-basis-remediation\src\idx_trade\v4_ca_event_windows.py"),
    ]
    paths: set[Path] = set()
    for root in roots:
        if root.is_file():
            paths.add(root)
        elif root.is_dir():
            paths.update(path for path in root.rglob("*") if path.is_file())
    if repo_root:
        for relative in ("src/idx_trade/ca_source_authority_audit_v11.py", "src/idx_trade/ca_aware_feature_basis_r3.py"):
            path = repo_root / relative
            if path.is_file():
                paths.add(path)
    return sorted(paths, key=lambda path: str(path).casefold())


def global_ca_population_gate(
    *,
    fit_tickers: int | Iterable[str],
    application_tickers: int | Iterable[str],
    closure_tickers: int | Iterable[str],
    fit_identities: Iterable[tuple[str, str]] | None = None,
    application_identities: Iterable[tuple[str, str]] | None = None,
    closure_identities: Iterable[tuple[str, str]] | None = None,
    family_coverage: Any = None,
    temporal_attestation: Any = None,
    source_family_certified: bool | None = None,
    date_level_attestation: bool | None = None,
    structural_event_complete: bool | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Fail closed on evidence-rich identity/family/temporal certification.

    The boolean arguments are accepted only for compatibility and are never a
    source of PASS.  The valid 629/716/716 architecture passes only when the
    full expanded identity set has every frozen family and temporal evidence
    with source contract, ref, and valid evidence hash.
    """

    def scope(value: int | Iterable[str] | None) -> set[str] | None:
        if value is None or isinstance(value, int):
            return None
        return {_ticker(item) for item in value if _ticker(item)}

    def ids(value: Iterable[tuple[str, str]] | None) -> set[tuple[str, str]] | None:
        if value is None:
            return None
        return {(_ticker(pair[0]), _iso_date(pair[1])) for pair in value if len(pair) >= 2 and _ticker(pair[0]) and _iso_date(pair[1])}

    fit_set, app_set, closure_set = ids(fit_identities), ids(application_identities), ids(closure_identities)
    fit_scope, app_scope, closure_scope = scope(fit_tickers), scope(application_tickers), scope(closure_tickers)
    diagnostics: dict[str, Any] = {
        "fit_ticker_count": len(fit_scope) if fit_scope is not None else fit_tickers,
        "application_ticker_count": len(app_scope) if app_scope is not None else application_tickers,
        "closure_ticker_count": len(closure_scope) if closure_scope is not None else closure_tickers,
        "naked_boolean_inputs_ignored": True,
        "fit_contained_in_application": False,
        "application_contained_in_closure": False,
    }
    if fit_set is None or app_set is None or closure_set is None:
        return {"verdict": "FAIL_IDENTITY_SCOPE_ATTESTATION_MISSING", "diagnostics": diagnostics}
    if not fit_set <= app_set:
        diagnostics["missing_application_identity_count"] = len(fit_set - app_set)
        return {"verdict": "FAIL_FIT_IDENTITIES_OUTSIDE_APPLICATION_SCOPE", "diagnostics": diagnostics}
    if not app_set <= closure_set:
        diagnostics["missing_closure_identity_count"] = len(app_set - closure_set)
        return {"verdict": "FAIL_APPLICATION_IDENTITIES_OUTSIDE_CLOSURE", "diagnostics": diagnostics}
    diagnostics["fit_contained_in_application"] = True
    diagnostics["application_contained_in_closure"] = True
    if fit_scope is not None and {ticker for ticker, _ in fit_set} != fit_scope:
        return {"verdict": "FAIL_FIT_IDENTITY_TICKER_SCOPE_MISMATCH", "diagnostics": diagnostics}
    if app_scope is not None and {ticker for ticker, _ in app_set} != app_scope:
        return {"verdict": "FAIL_APPLICATION_IDENTITY_TICKER_SCOPE_MISMATCH", "diagnostics": diagnostics}
    if closure_scope is not None and {ticker for ticker, _ in closure_set} != closure_scope:
        return {"verdict": "FAIL_CLOSURE_IDENTITY_TICKER_SCOPE_MISMATCH", "diagnostics": diagnostics}
    expected = app_set | closure_set
    family_rows = _records(family_coverage)
    temporal_rows = _records(temporal_attestation)
    claims: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in family_rows:
        key = (_ticker(row.get("ticker")), _iso_date(row.get("date")), _upper(row.get("event_family")))
        if key[0] and key[1] and key[2]:
            claims[key].append(row)
    invalid_or_missing: list[tuple[str, str]] = []
    conflicts: list[tuple[str, str]] = []
    for identity in expected:
        for family in FROZEN_FAMILIES:
            candidates = claims.get((identity[0], identity[1], family), [])
            if any(_strict_bool(row.get("coverage_conflict", False)) for row in candidates):
                conflicts.append(identity)
                continue
            valid = [row for row in candidates if _upper(row.get("coverage_state")) in {"CERTIFIED", "FAMILY_COVERAGE_CERTIFIED"} and _text(row.get("source_contract_id")) and _text(row.get("source_ref")) and valid_sha256(row.get("evidence_sha256", ""))]
            if not valid:
                invalid_or_missing.append(identity)
    diagnostics.update({"expected_identity_count": len(expected), "family_coverage_rows": len(family_rows), "family_missing_or_invalid_identity_count": len(set(invalid_or_missing)), "family_conflict_identity_count": len(set(conflicts))})
    if conflicts:
        return {"verdict": "FAIL_FAMILY_COVERAGE_CONFLICT", "diagnostics": diagnostics}
    if invalid_or_missing:
        return {"verdict": "FAIL_FAMILY_COVERAGE_NOT_FULLY_CERTIFIED", "diagnostics": diagnostics}
    temporal_by: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in temporal_rows:
        key = (_ticker(row.get("ticker")), _iso_date(row.get("date")))
        if key[0] and key[1]:
            temporal_by[key].append(row)
    temporal_invalid = []
    for identity in expected:
        valid = [row for row in temporal_by.get(identity, []) if _upper(row.get("coverage_state")) in {"CERTIFIED", "TEMPORAL_COVERAGE_CERTIFIED", "ASOF_CERTIFIED"} and _text(row.get("source_contract_id")) and _text(row.get("source_ref")) and valid_sha256(row.get("evidence_sha256", "")) and _text(row.get("as_of_semantics") or row.get("coverage_as_of_semantics") or row.get("date_level_semantics"))]
        if not valid:
            temporal_invalid.append(identity)
    diagnostics.update({"temporal_attestation_rows": len(temporal_rows), "temporal_missing_or_invalid_identity_count": len(set(temporal_invalid))})
    if temporal_invalid:
        return {"verdict": "FAIL_TEMPORAL_ASOF_EVIDENCE_MISSING_OR_INVALID", "diagnostics": diagnostics}
    diagnostics["structural_event_complete_derived"] = True
    diagnostics["full_expanded_scope_certified"] = True
    return {"verdict": "PASS", "diagnostics": diagnostics}


def run_audit(project_root: Path, output_root: Path, repo_root: Path | None = None) -> Path:
    if output_root.exists():
        raise FileExistsError(f"immutable audit root already exists: {output_root}")
    population = _load_population(project_root)
    context = _load_raw_context(project_root, population)
    primary, ledger = _build_primary_rows(context)
    _build_auxiliary_ledger(context, ledger)
    forensics = _forensics(context)
    transitions, transition_summary = _transition_reconstruction(primary, context)
    census = _census(primary, transitions, context, forensics)
    intervals = _interval_authority(context)
    negative = _negative_coverage(context)
    family = _family_authority(context, primary, transitions, intervals, forensics)
    population_rows = _population_authority(context, intervals, negative)
    gaps = _gap_matrix(context, family, intervals, negative, transition_summary, forensics)
    acquisition = _acquisition(context, forensics, transitions, transition_summary, intervals)
    staging = output_root.parent / f".{output_root.name}.staging"
    if staging.exists():
        raise FileExistsError(f"staging root already exists: {staging}")
    staging.mkdir(parents=True)
    try:
        ledger_fields = ["source_kind", "ticker", "event_family", "source_native_label", "raw_row_identity", "candidate_date", "cum_date", "record_date", "distribution_date", "ratio_left_security", "ratio_left_value", "ratio_right_security", "ratio_right_value", "ratio_raw", "status", "source_ref", "source_url", "evidence_sha256", "source_contract_id", "capture_observed_at_utc", "raw_capture_path", "source_hash_matches_bytes", "publication_fields", "raw_evidence_role", "raw_date_set", "raw_source_row_index", "idx_action_id", "idx_date_native", "idx_shares", "idx_shares_after"]
        transition_fields = ["record_kind", "event_id", "source_kind", "ticker", "event_family", "source_native_label", "candidate_date", "cum_date", "record_date", "distribution_date", "prior_derived_class", "prior_transition_source", "v11_raw_recomputed_class", "transition_date", "resolution_reason", "source_ref", "evidence_sha256", "source_contract_id", "source_hash_matches_bytes", "transition_lower_bound_certified", "transition_lower_bound_source_ref", "transition_lower_bound_source_sha256", "scope_classification"]
        census_fields = ["census_status", "event_id", "source_kind", "ticker", "event_family", "source_native_label", "candidate_date", "closure_geometry_start", "closure_geometry_end", "prior_136_present", "strict_26_signature_match", "prior_family_ticker_date_diff", "strict_26_family_ticker_date_diff", "difference_class", "transition_class", "transition_date", "source_ref", "evidence_sha256", "taxonomy_status", "physical_event_counted", "underlying_event_id", "linked_taxonomy_finding_ids", "notes"]
        forensic_fields = ["finding_id", "source_kind", "ticker", "source_native_label", "candidate_date", "source_ref", "evidence_sha256", "source_fields", "fit_ticker", "application_ticker", "closure_ticker", "boundary_intersects_dependency_window", "dependency_window_start", "dependency_window_end", "underlying_event_id", "source_document_group_id", "shareholder_entitlement", "authoritative_cum_record_transition_dates", "separate_cash_event", "basis_change_evidence", "existing_capital_restructuring_coverage", "taxonomy_status", "finding", "census_event_candidate"]
        _write_csv(staging / "v11_raw_source_event_ledger.csv", sorted(ledger, key=lambda row: (_text(row.get("source_kind")), _text(row.get("ticker")), _text(row.get("candidate_date")), _text(row.get("raw_row_identity")))), ledger_fields)
        _write_csv(staging / "v11_transition_reconstruction.csv", transitions, transition_fields)
        _write_csv(staging / "v11_dependency_closure_event_census.csv", census, census_fields)
        _write_csv(staging / "v11_structural_separation_forensics.csv", forensics, forensic_fields)
        interval_fields = list(intervals[0].keys()) if intervals else ["ticker"]
        _write_csv(staging / "v11_source_interval_authority.csv", intervals, interval_fields)
        _write_csv(staging / "v11_idx_negative_coverage_contract.csv", negative, list(negative[0].keys()))
        _write_csv(staging / "v11_source_family_authority_matrix.csv", family, list(family[0].keys()))
        _write_csv(staging / "v11_population_authority.csv", population_rows, list(population_rows[0].keys()))
        _write_csv(staging / "v11_remaining_gap_matrix.csv", gaps, list(gaps[0].keys()))
        _dump_json(staging / "acquisition_requirements_v11.json", acquisition)
        data_hashes = {path.name: sha256_file(path) for path in sorted(staging.iterdir()) if path.is_file()}
        strict_counts = transition_summary["strict_26_scope_counts"]
        interval_certified = {family: sum(row.get("coverage_state") == "CERTIFIED_INTERVAL" for row in intervals if row.get("event_family") == family) for family in FROZEN_FAMILIES}
        interval_page_only = {family: sum(row.get("coverage_state") == "PARSED_PAGE_ONLY" for row in intervals if row.get("event_family") == family) for family in FROZEN_FAMILIES}
        summary = {
            "schema_version": AUDIT_SCHEMA,
            "audit_date": AUDIT_DATE,
            "status": "SOURCE_AUTHORITY_GAP_CONFIRMED_PHASE_E_BLOCKED",
            "artifact_root": "<immutable-output-root>",
            "source_repository_state": _git_state(repo_root),
            "reviewed_implementation_head": REVIEWED_IMPLEMENTATION_HEAD,
            "facts_current_local_audit": {
                "fit": {"rows": population["summary"]["exact_final_fit"]["union_rows"], "tickers": len(population["fit_tickers"]), "identity_count": len(population["fit_ids"]), "ticker_set_sha256": canonical_set_hash(population["fit_tickers"])},
                "application": {"rows": population["summary"]["cross_section_application"]["application_rows"], "tickers": len(population["app_tickers"]), "identity_count": len(population["app_ids"]), "ticker_set_sha256": canonical_set_hash(population["app_tickers"])},
                "closure": {"rows": population["summary"]["backward_dependency_closure"]["closure_rows"], "tickers": len(population["closure_tickers"]), "identity_count": len(population["closure_ids"]), "start": population["closure_start"], "end": population["closure_end"], "ticker_set_sha256": canonical_set_hash(population["closure_tickers"])},
                "raw_source_event_ledger_rows": len(ledger),
                "primary_structural_event_count": len(primary),
                "full_census_rows": len(census),
                 "taxonomy_unknown_candidate_count": sum(row.get("taxonomy_status") == "REQUIRES_POLICY_DECISION" for row in forensics),
                 "taxonomy_findings_linked_to_physical_events": sum(bool(row.get("underlying_event_id")) for row in forensics if row.get("taxonomy_status") == "REQUIRES_POLICY_DECISION"),
                "census_difference_counts": dict(Counter(row.get("difference_class", "") for row in census)),
                "transition_reconstruction": transition_summary,
                "strict_26_after_scope_counts": strict_counts,
                "strict_26_outside_after_closure": transition_summary["strict_26_outside_after_closure_count"],
                "ksei_interval_certified_by_family": interval_certified,
                 "ksei_interval_parsed_page_only_by_family": interval_page_only,
                 "ksei_interval_scope": "567/716 parsed-page-only for RIGHTS_HMETD and STOCK_DIVIDEND; zero source-certified intervals; all other frozen families UNKNOWN_INTERVAL",
                "idx_negative_verdicts": dict(Counter(row["verdict"] for row in negative)),
                "separation_forensic_findings": len(forensics),
                "separation_taxonomy_unknown_findings": sum(row.get("taxonomy_status") == "REQUIRES_POLICY_DECISION" for row in forensics),
            },
            "facts_historical_notes_not_current_authority": {
                "prior_event_semantics": "comparison-only derived labels; V1.1 raw ledger is authoritative for recomputation",
                "prior_strict_26": "re-audited with candidate-date fail-closed rule; no candidate date promoted",
                "ADRO_AADI_2024": "retained-source forensic finding; no new frozen family selected",
                "source_label_red_team": "Pemisahan Unit Usaha and gabungUsaha preserved as taxonomy candidates; exact labels are not force-mapped",
            },
            "authority_matrix_verdicts": dict(Counter(row["verdict"] for row in family)),
            "temporal_authority": "PARTIAL_CERTIFIED_INTERVAL_FAIL_FULL_716",
            "local_evidence_sufficient": False,
            "provider_acquisition_required": True,
            "phase_e_gate": {"full_716_source_coverage": False, "structural_family_coverage": False, "temporal_asof": False, "transition_semantics": False, "negative_coverage": False, "taxonomy_policy": False, "verdict": "STOP"},
            "scientific_verdict_unchanged": {"DATA_ADMISSION": "FAIL", "RESEARCH_ADMISSION": "FAIL", "MODEL_PROMOTION": "NOT_EVALUATED", "HISTORICAL_APPLICATION": "BLOCKED_PHASE_E_NOT_RUN", "REFIT_AUTHORIZED": False, "COUNTER_ACTION": "NONE"},
            "guardrails": acquisition["guardrails"],
            "input_scope": {"closure_geometry": "candidate source dates intersect closure +/- 60 calendar days", "source_roots": [str(path) for path in _input_paths(project_root, repo_root)]},
            "output_hashes_excluding_manifest": dict(sorted(data_hashes.items())),
        }
        _dump_json(staging / "summary.json", summary)
        output_hashes = {path.name: sha256_file(path) for path in sorted(staging.iterdir()) if path.is_file()}
        input_files = []
        for path in _input_paths(project_root, repo_root):
            try:
                input_files.append({"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size})
            except OSError:
                continue
        _dump_json(staging / "MANIFEST.json", {"schema_version": f"{AUDIT_SCHEMA}_manifest", "status": "IMMUTABLE_LOCAL_SOURCE_AUTHORITY_AUDIT", "created_at_policy": f"fixed audit date {AUDIT_DATE}", "source_implementation_head": REVIEWED_IMPLEMENTATION_HEAD, "outcome_blind": True, "provider_calls": False, "input_files": input_files, "output_hashes_excluding_manifest": dict(sorted(output_hashes.items())), "self_hash_policy": "MANIFEST.json excluded from its own hash"})
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
    print(run_audit(args.project_root, args.output_root, args.repo_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
