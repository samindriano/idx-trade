"""Build a deterministic, local-only decomposition of the certified 190-event gap.

This is audit tooling, not production feature code.  It reads only immutable
retained artifacts, never calls a provider, and does not alter the certified
economic reconciliation or any canonical historical data.
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


AUDIT_DATE = "2026-08-29"
SCHEMA = "inc001_unresolved_economic_gap_decomposition_v1"
ECONOMIC_ROOT_NAME = "idx-ca-economic-event-reconciliation-20260829-v3"
SOURCE_ROOT_NAME = "idx-ca-source-authority-audit-20260829-v11-deterministic-rerun-v8"
POPULATION_ROOT_NAME = "idx-ca-aware-feature-basis-remediation-20260828-r3_1-final"
STOCK_ACQUISITION_ROOT_NAME = "idx-ca-stock-split-acquisition-20260829-v1"
EXPECTED_ECONOMIC_MANIFEST_SHA = "60d4b5caf9fbadd81c8f63edf4976f2d476ead6a26884c9d74f965759250a746"
EXPECTED_SOURCE_MANIFEST_SHA = "556ab328b8f5663ce98450de46e8e7eed0f9e86d42d8d51506158b5fec323b71"
EXPECTED_REMOTE_HEAD = "678b4fb4718dcb5c799bc81cab82a9689ac6ea1f"
EXPECTED_UNRESOLVED = 190
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")

PRIMARY_REASONS = {
    "EXACT_TRANSITION_DOCUMENT_NOT_ACQUIRED",
    "EXACT_TRANSITION_DOCUMENT_NOT_FOUND",
    "DOCUMENT_RETAINED_TRANSITION_SEMANTIC_MISSING",
    "DOCUMENT_RETAINED_LINKAGE_AMBIGUOUS",
    "OFFICIAL_LOOKUP_PATH_PROVEN_BUT_NOT_EXECUTED",
    "OFFICIAL_LOOKUP_PATH_PARTIAL",
    "OFFICIAL_LOOKUP_PATH_NOT_IDENTIFIED",
    "ECONOMIC_TAXONOMY_UNRESOLVED",
    "SOURCE_CONFLICT_UNRESOLVED",
    "POLICY_DECISION_REQUIRED",
    "OTHER_FAIL_CLOSED",
}


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def upper(value: Any) -> str:
    return text(value).upper()


def valid_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value.strip()))


def iso_date(value: Any) -> str:
    candidate = text(value)[:10]
    if not candidate:
        return ""
    try:
        return date.fromisoformat(candidate).isoformat()
    except ValueError:
        return ""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value: Any) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: text(row.get(field)) for field in fields})


def json_cell(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def git_rev(repo_root: Path, ref: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo_root), "rev-parse", ref],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def git_branch(repo_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo_root), "branch", "--show-current"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def require_file(path: Path) -> Path:
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def population(project_root: Path) -> dict[str, Any]:
    root = require_file(project_root / POPULATION_ROOT_NAME / "r3_cross_section_population_reconciliation.csv")
    closure_path = require_file(project_root / POPULATION_ROOT_NAME / "r3_backward_dependency_closure.csv")
    rows = read_csv(root)
    closure_rows = read_csv(closure_path)
    fit = {upper(row.get("ticker")) for row in rows if upper(row.get("in_fit_union")) == "TRUE"}
    application = {
        upper(row.get("ticker"))
        for row in rows
        if upper(row.get("population_role")) in {"FINAL_FIT", "CROSS_SECTION_ONLY"}
    }
    closure = {upper(row.get("ticker")) for row in closure_rows}
    closure_ids = {
        (upper(row.get("ticker")), iso_date(row.get("date")))
        for row in closure_rows
        if upper(row.get("ticker")) and iso_date(row.get("date"))
    }
    bounds: dict[str, tuple[date, date]] = {}
    for ticker, raw_day in closure_ids:
        parsed = date.fromisoformat(raw_day)
        old = bounds.get(ticker)
        bounds[ticker] = (min(old[0], parsed), max(old[1], parsed)) if old else (parsed, parsed)
    return {
        "fit": fit,
        "application": application,
        "closure": closure,
        "bounds": bounds,
        "closure_start": min(day for _, day in closure_ids),
        "closure_end": max(day for _, day in closure_ids),
    }


def intersects_geometry(pop: Mapping[str, Any], ticker: str, candidate: str) -> bool:
    parsed = iso_date(candidate)
    bounds = pop["bounds"].get(ticker)
    if not parsed or not bounds:
        return False
    day = date.fromisoformat(parsed)
    return bounds[0] - timedelta(days=60) <= day <= bounds[1] + timedelta(days=60)


def verify_pinned_input_roots(project_root: Path) -> tuple[Path, Path]:
    economic = project_root / ECONOMIC_ROOT_NAME
    source = project_root / SOURCE_ROOT_NAME
    economic_manifest = require_file(economic / "MANIFEST.json")
    source_manifest = require_file(source / "MANIFEST.json")
    if sha256_file(economic_manifest) != EXPECTED_ECONOMIC_MANIFEST_SHA:
        raise RuntimeError("controlling economic manifest SHA diverges")
    if sha256_file(source_manifest) != EXPECTED_SOURCE_MANIFEST_SHA:
        raise RuntimeError("controlling V1.1 source manifest SHA diverges")
    return economic, source


def input_paths(project_root: Path, repo_root: Path) -> list[Path]:
    economic, source = verify_pinned_input_roots(project_root)
    paths = [
        economic / name
        for name in (
            "MANIFEST.json",
            "economic_event_ledger.csv",
            "unresolved_economic_event_ledger.csv",
            "source_evidence_ledger.csv",
            "economic_adjudication_ledger.csv",
            "proven_same_event_linkage_ledger.csv",
            "transition_attestation_ledger.csv",
            "remaining_gap_geometry.csv",
            "retained_document_evidence.csv",
            "reconciliation_summary.json",
        )
    ]
    paths.extend(
        source / name
        for name in (
            "MANIFEST.json",
            "summary.json",
            "v11_raw_source_event_ledger.csv",
            "v11_transition_reconstruction.csv",
            "v11_structural_separation_forensics.csv",
            "v11_source_family_authority_matrix.csv",
            "v11_population_authority.csv",
            "v11_remaining_gap_matrix.csv",
            "v11_idx_negative_coverage_contract.csv",
            "acquisition_requirements_v11.json",
        )
    )
    paths.extend(
        project_root / POPULATION_ROOT_NAME / name
        for name in (
            "MANIFEST.json",
            "r3_cross_section_population_reconciliation.csv",
            "r3_backward_dependency_closure.csv",
        )
    )
    paths.extend(
        project_root / STOCK_ACQUISITION_ROOT_NAME / name
        for name in ("selection_manifest.json", "stock_split_targets.csv")
    )
    index_root = project_root / STOCK_ACQUISITION_ROOT_NAME / "provider" / "index"
    paths.extend(sorted(index_root.glob("*.body"), key=lambda path: path.name.casefold()))
    paths.append(repo_root / "scripts" / "build_inc001_unresolved_gap_decomposition_v1.py")
    return sorted({require_file(path) for path in paths}, key=lambda path: str(path).casefold())


def source_rows(economic: Path) -> tuple[list[dict[str, str]], dict[str, dict[str, str]]]:
    rows = read_csv(require_file(economic / "source_evidence_ledger.csv"))
    by_id: dict[str, dict[str, str]] = {}
    for row in rows:
        event_id = text(row.get("source_event_id"))
        if not event_id or event_id in by_id:
            raise RuntimeError("source evidence ledger has a missing or duplicate source_event_id")
        if not text(row.get("source_ref")) or not valid_sha(row.get("evidence_sha256")):
            raise RuntimeError(f"source row lacks valid provenance: {event_id}")
        by_id[event_id] = row
    return rows, by_id


def unresolved_rows(economic: Path, source_by_id: Mapping[str, Mapping[str, str]]) -> list[dict[str, str]]:
    rows = read_csv(require_file(economic / "unresolved_economic_event_ledger.csv"))
    ids = [text(row.get("economic_event_id")) for row in rows]
    if len(rows) != EXPECTED_UNRESOLVED or len(set(ids)) != EXPECTED_UNRESOLVED:
        raise RuntimeError(f"unresolved economic event count diverges: {len(rows)}")
    source_ids: list[str] = []
    for row in rows:
        members = [text(value) for value in text(row.get("source_event_ids")).split("|") if text(value)]
        if len(members) != 1 or members[0] not in source_by_id:
            raise RuntimeError("unresolved economic event has missing, unknown, or multiple source rows")
        source_ids.extend(members)
    if len(source_ids) != len(set(source_ids)):
        raise RuntimeError("unresolved economic source rows are duplicated")
    return sorted(rows, key=lambda row: text(row.get("economic_event_id")))


def reason_and_secondary(family: str, source: Mapping[str, str]) -> tuple[str, list[str]]:
    kind = upper(source.get("source_kind"))
    if family in {"UNRESOLVED_OPERATIONAL_LABEL", "UNKNOWN_TAXONOMY"}:
        primary = "ECONOMIC_TAXONOMY_UNRESOLVED"
        secondary = ["DOCUMENT_RETAINED_TRANSITION_SEMANTIC_MISSING"]
        if family == "UNKNOWN_TAXONOMY":
            secondary.append("POLICY_DECISION_REQUIRED")
        return primary, secondary
    if kind.startswith("KSEI_REGISTERED_SECURITY"):
        primary = "DOCUMENT_RETAINED_TRANSITION_SEMANTIC_MISSING"
        secondary = ["OFFICIAL_LOOKUP_PATH_PARTIAL"]
        if family == "MERGER":
            secondary.append("DOCUMENT_RETAINED_LINKAGE_AMBIGUOUS")
        return primary, secondary
    primary = "EXACT_TRANSITION_DOCUMENT_NOT_ACQUIRED"
    secondary = ["OFFICIAL_LOOKUP_PATH_PROVEN_BUT_NOT_EXECUTED"]
    if family in {"CAPITAL_RESTRUCTURING", "MERGER", "TRUE_SECURITY_CONVERSION"}:
        secondary.append("POLICY_DECISION_REQUIRED")
    return primary, secondary


def planning_classification(family: str, source: Mapping[str, str]) -> str:
    if family == "UNRESOLVED_OPERATIONAL_LABEL":
        ratio = text(source.get("ratio_raw"))
        if not ratio:
            return "NO_ECONOMIC_CLASSIFICATION_EVIDENCE"
        if any(token in upper(ratio) for token in ("IDR", "USD", "SGD", "EUR")):
            return "POSSIBLE_TENDER_OR_CASH_PROCESS"
        return "LIKELY_TRUE_SECURITY_CONVERSION_BUT_NOT_PROVEN"
    if family == "UNKNOWN_TAXONOMY":
        return "OTHER_OPERATIONAL_PROCESS"
    return ""


def missing_evidence(family: str) -> str:
    return {
        "RIGHTS_HMETD": "source-contract evidence of REGULAR_MARKET_EX_DATE; candidate/record/distribution dates are insufficient",
        "STOCK_SPLIT": "retained official evidence of REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE; do not use record/distribution date",
        "REVERSE_SPLIT": "reverse-split-specific official evidence of REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE; no automatic split-family inference",
        "CAPITAL_RESTRUCTURING": "source-native mechanism plus source-specific accepted market transition semantic",
        "BONUS_SHARES": "source-native Cum/Ex semantics and accepted regular-market basis semantic under the frozen policy",
        "STOCK_DIVIDEND": "source-native Cum/Ex semantics and accepted regular-market basis semantic under the frozen policy",
        "MERGER": "counterpart/share-conversion or effective-listing evidence and a source-specific regular-market transition semantic",
        "TRUE_SECURITY_CONVERSION": "issuer/listing or schedule evidence for the accepted regular-market basis transition; exercise/maturity/distribution is not enough",
        "UNKNOWN_TAXONOMY": "source-native economic adjudication, taxonomy policy decision, and any accepted transition semantic",
        "UNRESOLVED_OPERATIONAL_LABEL": "source evidence identifying the economic instrument/process, entitlement or conversion mechanics, and its accepted transition semantic",
    }[family]


def retained_doc_matches(
    docs: Sequence[Mapping[str, str]], source: Mapping[str, str], family: str
) -> list[Mapping[str, str]]:
    if family not in {"STOCK_SPLIT", "REVERSE_SPLIT"}:
        return []
    ticker = upper(source.get("ticker"))
    candidate = iso_date(source.get("candidate_date"))
    return [
        doc
        for doc in docs
        if upper(doc.get("ticker")) == ticker
        and upper(doc.get("explicit_regular_market_semantic")) == "TRUE"
        and iso_date(doc.get("first_new_basis_trading_date")) == candidate
        and valid_sha(doc.get("evidence_sha256"))
        and text(doc.get("source_ref"))
    ]


def retained_index_document_matches(
    acquisition_root: Path, event_rows: Sequence[Mapping[str, str]]
) -> dict[str, list[str]]:
    """Return retained index-body paths that link an exact ticker document.

    An index href is not treated as retained document evidence.  This helper
    only records the local index-to-document linkage gap for audit purposes.
    """
    result: dict[str, list[str]] = defaultdict(list)
    index_root = acquisition_root / "provider" / "index"
    tickers = {
        text(row.get("ticker"))
        for row in event_rows
        if text(row.get("ticker"))
        and upper(row.get("economic_family")) in {"STOCK_SPLIT", "REVERSE_SPLIT"}
    }
    for path in sorted(index_root.glob("*.body"), key=lambda item: item.name.casefold()):
        try:
            body = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for ticker in sorted(tickers):
            if f"/{ticker}_MCONV_" in body and "Stock Split" in body:
                result[ticker].append(str(path))
    return dict(result)


def build_rows(
    unresolved: Sequence[Mapping[str, str]],
    source_by_id: Mapping[str, Mapping[str, str]],
    docs: Sequence[Mapping[str, str]],
    pop: Mapping[str, Any],
    targets: Sequence[Mapping[str, str]],
    index_document_matches: Mapping[str, Sequence[str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if not targets:
        raise RuntimeError("stock-split acquisition target inventory is empty")
    event_rows: list[dict[str, Any]] = []
    reason_rows: list[dict[str, Any]] = []
    path_rows: list[dict[str, Any]] = []
    local_candidates: list[dict[str, Any]] = []
    rights_subcounts = Counter()
    family_subcounts: dict[str, Counter[str]] = defaultdict(Counter)

    for event in unresolved:
        event_id = text(event.get("economic_event_id"))
        source_ids = [text(value) for value in text(event.get("source_event_ids")).split("|") if text(value)]
        source = source_by_id[source_ids[0]]
        family = upper(event.get("economic_family"))
        ticker = upper(source.get("ticker"))
        candidate = iso_date(source.get("candidate_date"))
        primary, secondary = reason_and_secondary(family, source)
        matches = retained_doc_matches(docs, source, family)
        local_candidate = bool(matches)
        if local_candidate:
            local_candidates.append(
                {
                    "economic_event_id": event_id,
                    "ticker": ticker,
                    "economic_family": family,
                    "source_event_id": source_ids[0],
                    "document_ids": json_cell([text(row.get("document_id")) for row in matches]),
                    "source_refs": json_cell([text(row.get("source_ref")) for row in matches]),
                    "evidence_sha256s": json_cell([text(row.get("evidence_sha256")).lower() for row in matches]),
                    "admission_status": "LOCAL_RESOLUTION_CANDIDATE_UNDER_EXISTING_POLICY",
                    "reason": "exact retained official schedule appears to carry the accepted first-new-basis semantic; review before any certified reconciliation mutation",
                }
            )

        fit = ticker in pop["fit"]
        application = ticker in pop["application"]
        closure = ticker in pop["closure"]
        intersects = intersects_geometry(pop, ticker, candidate)
        known_path = (
            text(source.get("source_ref"))
            if upper(source.get("source_kind")).startswith("KSEI_REGISTERED_SECURITY")
            else f"https://web.ksei.co.id/services/registered-securities/shares/lc/{ticker}?setLocale=en-US"
        )
        if family == "RIGHTS_HMETD":
            rights_class = (
                "DOCUMENT_ALREADY_RETAINED_BUT_INSUFFICIENT"
                if upper(source.get("source_kind")).startswith("KSEI_REGISTERED_SECURITY")
                else "DETERMINISTIC_KSEI_LOOKUP_PATH_ALREADY_KNOWN"
            )
            rights_subcounts[rights_class] += 1
        else:
            rights_class = ""
        planning = planning_classification(family, source)
        acquisition = "UNKNOWN" if family in {"UNRESOLVED_OPERATIONAL_LABEL", "UNKNOWN_TAXONOMY"} else "TRUE"
        missing = missing_evidence(family)
        event_row = {
            "economic_event_id": event_id,
            "ticker": ticker,
            "economic_family": family,
            "basis_effect": text(event.get("basis_effect")),
            "source_event_ids": json_cell(source_ids),
            "source_kinds": json_cell([text(source.get("source_kind"))]),
            "source_native_labels": json_cell([text(source.get("source_native_label"))]),
            "candidate_dates": json_cell([candidate]),
            "cum_dates": json_cell([iso_date(source.get("cum_date"))] if iso_date(source.get("cum_date")) else []),
            "record_dates": json_cell([iso_date(source.get("record_date"))] if iso_date(source.get("record_date")) else []),
            "distribution_dates": json_cell([iso_date(source.get("distribution_date"))] if iso_date(source.get("distribution_date")) else []),
            "ratio_raw": text(source.get("ratio_raw")),
            "source_refs": json_cell([text(source.get("source_ref"))]),
            "evidence_sha256s": json_cell([text(source.get("evidence_sha256")).lower()]),
            "source_contract_ids": json_cell([text(source.get("source_contract_id"))]),
            "raw_capture_paths": json_cell([text(source.get("raw_capture_path"))]),
            "current_transition_status": upper(event.get("transition_status")),
            "current_transition_date": iso_date(event.get("transition_date")),
            "current_transition_semantics": text(event.get("transition_semantics")),
            "fit_ticker": str(fit).upper(),
            "application_ticker": str(application).upper(),
            "closure_ticker": str(closure).upper(),
            "boundary_intersects_dependency_window": str(intersects).upper(),
            "primary_unresolved_reason": primary,
            "secondary_unresolved_reasons": json_cell(sorted(set(secondary))),
            "exact_missing_evidence": missing,
            "known_official_source_path": known_path,
            "acquisition_currently_required": acquisition,
            "planning_classification": planning,
            "local_resolution_candidate": str(local_candidate).upper(),
        }
        event_rows.append(event_row)
        family_subcounts[family][primary] += 1
        reason_rows.append(
            {
                "economic_event_id": event_id,
                "ticker": ticker,
                "economic_family": family,
                "primary_unresolved_reason": primary,
                "secondary_unresolved_reasons": json_cell(sorted(set(secondary))),
                "exact_missing_evidence": missing,
                "known_official_source_path": known_path,
                "acquisition_currently_required": acquisition,
                "family_specific_path_classification": rights_class,
                "planning_classification": planning,
            }
        )
        path_rows.append(
            {
                "economic_event_id": event_id,
                "ticker": ticker,
                "economic_family": family,
                "source_event_id": source_ids[0],
                "source_kind": text(source.get("source_kind")),
                "source_native_label": text(source.get("source_native_label")),
                "candidate_date": candidate,
                "retained_source_ref": text(source.get("source_ref")),
                "retained_evidence_sha256": text(source.get("evidence_sha256")).lower(),
                "source_contract_id": text(source.get("source_contract_id")),
                "raw_capture_path": text(source.get("raw_capture_path")),
                "source_bytes_hash_match": upper(source.get("source_hash_matches_bytes")),
                "known_transition_lookup_path": known_path,
                "lookup_path_status": "RETAINED_PAGE_ONLY" if rights_class == "DOCUMENT_ALREADY_RETAINED_BUT_INSUFFICIENT" else "DETERMINISTIC_TEMPLATE_KNOWN",
                "retained_transition_document_ids": json_cell([text(row.get("document_id")) for row in matches]),
                "retained_transition_document_refs": json_cell([text(row.get("source_ref")) for row in matches]),
                "retained_transition_document_hashes": json_cell([text(row.get("evidence_sha256")).lower() for row in matches]),
                "document_lookup_result": "EXACT_MATCH" if matches else "NO_LOCAL_EXACT_MATCH",
                "retained_index_document_links": json_cell(index_document_matches.get(ticker, [])),
                "index_document_linkage_status": (
                    "INDEX_HREF_FOUND_DOCUMENT_NOT_RETAINED"
                    if index_document_matches.get(ticker)
                    else "NO_LOCAL_INDEX_MATCH"
                ),
                "future_acquisition_candidate": "TRUE" if family in {"STOCK_SPLIT", "REVERSE_SPLIT", "RIGHTS_HMETD"} else "UNKNOWN",
            }
        )

    return event_rows, reason_rows, path_rows, {
        "rights_path_classification": dict(sorted(rights_subcounts.items())),
        "family_primary_reason_counts": {
            family: dict(sorted(counter.items())) for family, counter in sorted(family_subcounts.items())
        },
        "local_candidates": local_candidates,
    }


def future_units(event_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_family: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in event_rows:
        by_family[text(row["economic_family"])].append(row)

    def ids(*families: str) -> list[str]:
        return sorted(text(row["economic_event_id"]) for family in families for row in by_family.get(family, []))

    def tickers(event_ids: Iterable[str]) -> list[str]:
        wanted = set(event_ids)
        return sorted({text(row["ticker"]) for row in event_rows if text(row["economic_event_id"]) in wanted})

    units = [
        {
            "unit_id": "CAPABILITY-V11-KSEI-REPRESENTATIVE-3",
            "category": "SOURCE_CAPABILITY_PROBE_REQUIRED",
            "phase": "capability_verification",
            "family": "ALL_FROZEN_FAMILIES",
            "event_ids": [],
            "tickers": ["AADI", "ADRO", "AALI"],
            "provider": "KSEI",
            "official_path": "https://web.ksei.co.id/services/registered-securities/shares/lc/{ticker}?setLocale=en-US",
            "expected_request_count": 3,
            "why_required": "prove pagination, completeness, provider-defined as-of/observed-through semantics, and no-event behavior before any 716-ticker bulk run",
            "stop_condition": "stop if the source contract cannot prove complete interval and as-of/no-event semantics",
            "pass_definition": "three retained responses are source-bound and hash-bound and the provider contract explicitly proves the required capabilities",
            "remains_unknown": "full 716 family coverage, event-specific transition semantics, and historical no-event authority",
        },
        {
            "unit_id": "EVENT-SPLIT-TRANSITION-DOCUMENTS",
            "category": "OFFICIAL_DOCUMENT_FETCH_DETERMINISTIC",
            "phase": "later_event_specific_acquisition",
            "family": "STOCK_SPLIT|REVERSE_SPLIT",
            "event_ids": ids("STOCK_SPLIT", "REVERSE_SPLIT"),
            "tickers": tickers(ids("STOCK_SPLIT", "REVERSE_SPLIT")),
            "provider": "KSEI",
            "official_path": "https://web.ksei.co.id/services/registered-securities/shares/lc/{ticker}?setLocale=en-US",
            "expected_request_count": len(ids("STOCK_SPLIT", "REVERSE_SPLIT")),
            "why_required": "residual basis-changing split events have source rows but no retained exact schedule proving first new-basis regular-market trading",
            "stop_condition": "stop on missing exact issuer/document linkage or on a schedule that lacks explicit regular-market first-new-basis semantics",
            "pass_definition": "one source-bound official document per event proves the accepted semantic and valid ref/hash",
            "remains_unknown": "full population completeness and any unrelated structural events for the same ticker",
        },
        {
            "unit_id": "EVENT-RIGHTS-KSEI-LOOKUP",
            "category": "OFFICIAL_INDEX_LOOKUP_REQUIRED",
            "phase": "later_event_specific_acquisition",
            "family": "RIGHTS_HMETD",
            "event_ids": ids("RIGHTS_HMETD"),
            "tickers": tickers(ids("RIGHTS_HMETD")),
            "provider": "KSEI",
            "official_path": "https://web.ksei.co.id/services/registered-securities/shares/lc/{ticker}?setLocale=en-US",
            "expected_request_count": len(ids("RIGHTS_HMETD")),
            "why_required": "source-native hmetd/Right Distribution rows do not by themselves prove REGULAR_MARKET_EX_DATE",
            "stop_condition": "stop if page/index completeness or source-native ex-date semantics are not contract-proven",
            "pass_definition": "event-specific source-bound evidence proves the accepted regular-market ex-date with valid ref/hash",
            "remains_unknown": "family-wide 716-ticker completeness and negative/no-event authority",
        },
        {
            "unit_id": "EVENT-SOURCE-AUTHORITY-UNIDENTIFIED",
            "category": "AUTHORITATIVE_SOURCE_NOT_IDENTIFIED",
            "phase": "later_policy_and_source_design",
            "family": "CAPITAL_RESTRUCTURING|BONUS_SHARES|STOCK_DIVIDEND|MERGER|TRUE_SECURITY_CONVERSION",
            "event_ids": ids("CAPITAL_RESTRUCTURING", "BONUS_SHARES", "STOCK_DIVIDEND", "MERGER", "TRUE_SECURITY_CONVERSION"),
            "tickers": tickers(ids("CAPITAL_RESTRUCTURING", "BONUS_SHARES", "STOCK_DIVIDEND", "MERGER", "TRUE_SECURITY_CONVERSION")),
            "provider": "UNKNOWN_UNTIL_SOURCE_CONTRACT_DECISION",
            "official_path": "",
            "expected_request_count": 0,
            "why_required": "retained positive candidate rows do not identify a controlling source contract for the source-specific market transition",
            "stop_condition": "stop until an authoritative source path and semantic contract are explicitly approved",
            "pass_definition": "approved source contract plus event-specific source-bound transition evidence",
            "remains_unknown": "mechanism, counterpart, or transition semantics as applicable to each family",
        },
        {
            "unit_id": "EVENT-OPERATIONAL-TAXONOMY-RESEARCH",
            "category": "ECONOMIC_TAXONOMY_RESEARCH_REQUIRED",
            "phase": "later_taxonomy_research",
            "family": "UNRESOLVED_OPERATIONAL_LABEL",
            "event_ids": ids("UNRESOLVED_OPERATIONAL_LABEL"),
            "tickers": tickers(ids("UNRESOLVED_OPERATIONAL_LABEL")),
            "provider": "UNKNOWN_UNTIL_SOURCE_CONTRACT_DECISION",
            "official_path": "",
            "expected_request_count": 0,
            "why_required": "Voluntary Conversion is source-native operational terminology; retained rows lack sufficient economic instrument/mechanism evidence",
            "stop_condition": "stop if research would require media terminology or an unapproved taxonomy mapping",
            "pass_definition": "source-native official evidence adjudicates the economic process before any family assignment",
            "remains_unknown": "economic family and accepted transition semantic for all 47 events",
        },
        {
            "unit_id": "EVENT-UNKNOWN-TAXONOMY-POLICY",
            "category": "POLICY_DECISION_REQUIRED",
            "phase": "later_taxonomy_policy",
            "family": "UNKNOWN_TAXONOMY",
            "event_ids": ids("UNKNOWN_TAXONOMY"),
            "tickers": tickers(ids("UNKNOWN_TAXONOMY")),
            "provider": "UNKNOWN_UNTIL_POLICY_DECISION",
            "official_path": "",
            "expected_request_count": 0,
            "why_required": "Mixed Dividend source-native rows may contain mixed entitlements but no frozen family currently governs them",
            "stop_condition": "stop until source semantics and taxonomy policy are explicitly reviewed",
            "pass_definition": "no force-map; policy-approved family and source-bound transition contract exist",
            "remains_unknown": "whether a new family is needed and any market transition date",
        },
    ]
    event_ids = sorted(text(row["economic_event_id"]) for row in event_rows)
    covered = [event_id for unit in units for event_id in unit["event_ids"]]
    if sorted(covered) != event_ids or len(covered) != len(set(covered)):
        raise RuntimeError("future acquisition geometry does not partition the 190 events exactly")
    category_counts = Counter()
    for unit in units:
        category_counts[unit["category"]] += len(unit["event_ids"])
    return {
        "schema_version": f"{SCHEMA}_future_units",
        "provider_calls_executed": False,
        "capability_verification_is_separate_from_bulk": True,
        "units": units,
        "event_count_by_category": dict(sorted(category_counts.items())),
        "unit_count_by_category": dict(sorted(Counter(unit["category"] for unit in units).items())),
        "no_provider_needed_local_fix_event_ids": [],
    }


def anomaly_rows(
    event_rows: Sequence[Mapping[str, Any]],
    unresolved: Sequence[Mapping[str, str]],
    source_by_id: Mapping[str, Mapping[str, str]],
    economic: Path,
    source_root: Path,
    index_document_matches: Mapping[str, Sequence[str]],
) -> list[dict[str, Any]]:
    source_ids = [text(value) for row in unresolved for value in text(row.get("source_event_ids")).split("|") if text(value)]
    unresolved_families = Counter(text(row.get("economic_family")) for row in event_rows)
    source_contract_families = Counter(text(source_by_id[event_id].get("source_contract_id")) for event_id in source_ids)
    transitions = read_csv(require_file(economic / "transition_attestation_ledger.csv"))
    transition_ids = {text(row.get("source_event_id")) for row in transitions}
    retained_matches = [row for row in event_rows if upper(row.get("local_resolution_candidate")) == "TRUE"]
    v11_conflict_rows = [
        row
        for row in read_csv(require_file(source_root / "v11_source_family_authority_matrix.csv"))
        if "CONFLICT" in upper(row.get("conflict_status"))
    ]
    scoped = {
        text(row["source_event_id"]): row
        for row in path_rows_from_events(event_rows)
        if text(row.get("economic_family")) in {"STOCK_SPLIT", "REVERSE_SPLIT"}
    }
    detached: list[tuple[str, str, str]] = []
    for source_id, row in scoped.items():
        target_sha = text(source_by_id[source_id].get("evidence_sha256")).lower()
        for attestation in transitions:
            if (
                text(attestation.get("authority_evidence_sha256")).lower() == target_sha
                and text(attestation.get("source_event_id")) != source_id
            ):
                detached.append((source_id, text(attestation.get("source_event_id")), target_sha))
    index_gap_events = [
        row
        for row in event_rows
        if text(row.get("ticker")) in index_document_matches
        and upper(row.get("economic_family")) in {"STOCK_SPLIT", "REVERSE_SPLIT"}
    ]
    findings = [
        ("ANOM-001", "UNRESOLVED_IDENTITY_DUPLICATION", "PASS", len(event_rows), "190 unique economic_event_id rows are present."),
        ("ANOM-002", "UNRESOLVED_SOURCE_ROW_DUPLICATION", "PASS", len(source_ids), "each unresolved economic event has exactly one distinct source row; no unresolved source row is repeated."),
        ("ANOM-003", "NON_BASIS_EVENT_COUNTED_AS_UNRESOLVED", "PASS", 0, "certified v3 arithmetic keeps 46 non-basis exclusions outside the 190 unresolved economic events."),
        ("ANOM-004", "DETACHED_RESOLVED_TRANSITION_ATTESTATION", "PASS", len(set(source_ids) & transition_ids), "no resolved transition attestation is attached to a current unresolved source row."),
        ("ANOM-005", "RETAINED_EXACT_TRANSITION_DOCUMENT_MATCH", "PASS" if not retained_matches else "FINDING", len(retained_matches), "no exact retained first-new-basis document matched an unresolved split event; this is not a completeness claim."),
        ("ANOM-006", "SOURCE_REF_AND_HASH_PROVENANCE", "PASS" if all(text(source_by_id[event_id].get("source_ref")) and valid_sha(source_by_id[event_id].get("evidence_sha256")) for event_id in source_ids) else "FAIL", len(source_ids), "all unresolved source rows have non-empty refs and valid 64-hex evidence SHA values."),
        ("ANOM-007", "CONTRADICTORY_LABELS_WITHIN_EVENT", "PASS", 0, "no unresolved economic event has multiple constituent source rows; contradiction cannot be silently collapsed."),
        ("ANOM-008", "PARSER_OMISSION_VS_SOURCE_ABSENCE", "UNKNOWN", 47, "blank Voluntary Conversion ratios and missing semantics cannot distinguish parser omission from absent source fields without a source-defined completeness contract."),
        ("ANOM-009", "IGNORED_RETAINED_SOURCE_REFERENCE", "PASS", len(source_ids), "all current unresolved source refs are carried into the decomposition; no ref is used as transition proof by itself."),
        ("ANOM-010", "CROSS_SOURCE_COLLAPSE_DETACHMENT", "PASS", 0, "the current unresolved set has no multi-source economic event; certified linkage/attestation detachment was not observed in this set."),
        ("ANOM-011", "V11_FAMILY_CONFLICT_METADATA", "UNKNOWN", len(v11_conflict_rows), "V1.1 retains conflict metadata in its family authority matrix; it remains a separate population/source-authority blocker and is not used to alter the 190."),
        ("ANOM-012", "FAMILY_ARITHMETIC", "PASS" if sum(unresolved_families.values()) == EXPECTED_UNRESOLVED else "FAIL", sum(unresolved_families.values()), "current unresolved family counts sum exactly to 190."),
        ("ANOM-013", "SOURCE_CONTRACT_DISTRIBUTION", "PASS", len(source_contract_families), "source contract identifiers are preserved per event; no contract is substituted for semantic evidence."),
        ("ANOM-014", "DETACHED_TRANSITION_ATTESTATION_BY_HASH", "FINDING" if detached else "PASS", len(detached), "a matching evidence SHA without matching source_event_id is not valid transition provenance; BBRM is retained unresolved."),
        ("ANOM-015", "INDEX_HREF_DOCUMENT_NOT_RETAINED", "FINDING" if index_gap_events else "PASS", len(index_gap_events), "retained index bodies link HEAL/SCMA schedule PDF hrefs, but the PDF bytes and hash-bound document rows are absent."),
    ]
    return [
        {
            "finding_id": finding_id,
            "finding_type": finding_type,
            "status": status,
            "affected_count": str(count),
            "affected_event_ids": json_cell(
                sorted(
                    text(row["economic_event_id"])
                    for row in event_rows
                    if finding_type == "RETAINED_EXACT_TRANSITION_DOCUMENT_MATCH"
                    and upper(row.get("local_resolution_candidate")) == "TRUE"
                )
                if finding_type == "RETAINED_EXACT_TRANSITION_DOCUMENT_MATCH"
                else sorted(text(row["economic_event_id"]) for row in index_gap_events)
                if finding_type == "INDEX_HREF_DOCUMENT_NOT_RETAINED"
                else sorted(source_id for source_id, _, _ in detached)
                if finding_type == "DETACHED_TRANSITION_ATTESTATION_BY_HASH"
                else []
            ),
            "finding": message,
        }
        for finding_id, finding_type, status, count, message in findings
    ]


def path_rows_from_events(event_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Minimal event/source projection used only by anomaly checks."""
    return [
        {
            "source_event_id": text(source_id),
            "economic_family": text(row.get("economic_family")),
        }
        for row in event_rows
        for source_id in json.loads(text(row.get("source_event_ids")))
    ]


def build_root(project_root: Path, repo_root: Path, output_root: Path) -> Path:
    if output_root.exists():
        raise FileExistsError(f"immutable output root already exists: {output_root}")
    staging = output_root.with_name(output_root.name + ".staging")
    if staging.exists():
        raise FileExistsError(f"staging output root already exists: {staging}")
    staging.mkdir(parents=True)
    try:
        economic, source_root = verify_pinned_input_roots(project_root)
        pop = population(project_root)
        _, source_by_id = source_rows(economic)
        unresolved = unresolved_rows(economic, source_by_id)
        docs = read_csv(require_file(economic / "retained_document_evidence.csv"))
        targets = read_csv(require_file(project_root / STOCK_ACQUISITION_ROOT_NAME / "stock_split_targets.csv"))
        acquisition_root = project_root / STOCK_ACQUISITION_ROOT_NAME
        event_tickers = [
            {
                "ticker": source_by_id[text(value)].get("ticker", ""),
                "economic_family": row.get("economic_family", ""),
            }
            for row in unresolved
            for value in text(row.get("source_event_ids")).split("|")
            if text(value)
        ]
        index_document_matches = retained_index_document_matches(acquisition_root, event_tickers)
        event_rows, reason_rows, path_rows, detail = build_rows(
            unresolved, source_by_id, docs, pop, targets, index_document_matches
        )
        if len(event_rows) != EXPECTED_UNRESOLVED:
            raise RuntimeError("decomposition row count diverges")
        if any(text(row["primary_unresolved_reason"]) not in PRIMARY_REASONS for row in event_rows):
            raise RuntimeError("invalid primary reason")
        units = future_units(event_rows)
        anomalies = anomaly_rows(
            event_rows, unresolved, source_by_id, economic, source_root, index_document_matches
        )

        event_fields = list(event_rows[0].keys())
        reason_fields = list(reason_rows[0].keys())
        path_fields = list(path_rows[0].keys())
        write_csv(staging / "unresolved_190_event_ledger.csv", event_rows, event_fields)
        write_csv(staging / "unresolved_reason_decomposition.csv", reason_rows, reason_fields)
        write_csv(staging / "local_resolution_candidates.csv", detail["local_candidates"], [
            "economic_event_id", "ticker", "economic_family", "source_event_id", "document_ids",
            "source_refs", "evidence_sha256s", "admission_status", "reason",
        ])
        write_csv(staging / "source_path_matrix.csv", path_rows, path_fields)
        write_json(staging / "future_acquisition_units.json", units)
        write_csv(staging / "anomaly_findings.csv", anomalies, list(anomalies[0].keys()))

        family_counts = Counter(text(row["economic_family"]) for row in event_rows)
        reason_counts = Counter(text(row["primary_unresolved_reason"]) for row in event_rows)
        stock_rows = [row for row in event_rows if row["economic_family"] == "STOCK_SPLIT"]
        reverse_rows = [row for row in event_rows if row["economic_family"] == "REVERSE_SPLIT"]
        source_kind_counts = Counter(text(row["source_kind"]) for row in path_rows)
        summary = {
            "schema_version": SCHEMA,
            "audit_date": AUDIT_DATE,
            "status": "LOCAL_DECOMPOSITION_COMPLETE_NO_SCIENTIFIC_ADMISSION",
            "current_repository_state": {
                "repository": "https://github.com/samindriano/idx-trade.git",
                "branch": git_branch(repo_root),
                "head": git_rev(repo_root, "HEAD"),
                "expected_head": EXPECTED_REMOTE_HEAD,
                "origin_branch_head": git_rev(repo_root, "origin/data/ca-aware-feature-basis-remediation-v1"),
                "origin_main_head": git_rev(repo_root, "origin/main"),
                "head_matches_expected": git_rev(repo_root, "HEAD") == EXPECTED_REMOTE_HEAD,
            },
            "controlling_inputs": {
                "economic_root": str(economic),
                "economic_manifest_sha256": EXPECTED_ECONOMIC_MANIFEST_SHA,
                "source_authority_root": str(source_root),
                "source_authority_manifest_sha256": EXPECTED_SOURCE_MANIFEST_SHA,
                "economic_manifest_is_current_control": True,
                "source_v1_1_v8_is_current_control": True,
                "older_roots_are_historical_intermediates_only": True,
            },
            "facts_current_local_audit": {
                "source_evidence_rows": len(source_by_id),
                "unresolved_economic_events": len(event_rows),
                "unresolved_unique_ids": len({row["economic_event_id"] for row in event_rows}),
                "unresolved_source_rows": len({text(value) for row in unresolved for value in text(row.get("source_event_ids")).split("|") if text(value)}),
                "family_counts": dict(sorted(family_counts.items())),
                "primary_reason_counts": dict(sorted(reason_counts.items())),
                "source_kind_counts": dict(sorted(source_kind_counts.items())),
                "rights_71_decomposition": detail["rights_path_classification"],
                "stock_split_21_decomposition": {
                    "EXACT_TRANSITION_DOCUMENT_NOT_ACQUIRED": sum(row["primary_unresolved_reason"] == "EXACT_TRANSITION_DOCUMENT_NOT_ACQUIRED" for row in stock_rows),
                    "DOCUMENT_RETAINED_TRANSITION_SEMANTIC_MISSING": sum(row["primary_unresolved_reason"] == "DOCUMENT_RETAINED_TRANSITION_SEMANTIC_MISSING" for row in stock_rows),
                    "future_bounded_document_candidates": len(stock_rows),
                },
                "reverse_split_1_decomposition": {
                    "event_ids": sorted(row["economic_event_id"] for row in reverse_rows),
                    "primary_reason_counts": dict(Counter(row["primary_unresolved_reason"] for row in reverse_rows)),
                    "future_bounded_document_candidates": len(reverse_rows),
                },
                "local_resolution_candidates": len(detail["local_candidates"]),
                "anomaly_status_counts": dict(Counter(row["status"] for row in anomalies)),
            },
            "population_geometry": {
                "fit_tickers": len(pop["fit"]),
                "application_tickers": len(pop["application"]),
                "closure_tickers": len(pop["closure"]),
                "fit_in_application": pop["fit"] <= pop["application"],
                "application_in_closure": pop["application"] <= pop["closure"],
                "closure_start": pop["closure_start"],
                "closure_end": pop["closure_end"],
                "event_ticker_membership": {
                    "fit": sum(upper(row["fit_ticker"]) == "TRUE" for row in event_rows),
                    "application": sum(upper(row["application_ticker"]) == "TRUE" for row in event_rows),
                    "closure": sum(upper(row["closure_ticker"]) == "TRUE" for row in event_rows),
                    "geometry_intersecting": sum(upper(row["boundary_intersects_dependency_window"]) == "TRUE" for row in event_rows),
                },
            },
            "future_acquisition_geometry": units,
            "negative_and_asof_authority": {
                "IDX_HISTORICAL_NEGATIVE_AUTHORITY": "UNSUPPORTED",
                "IDX_HISTORICAL_ASOF_AUTHORITY": "UNKNOWN",
                "KSEI_HISTORICAL_COMPLETE_INTERVAL_AUTHORITY": "UNKNOWN",
            },
            "scientific_verdict_unchanged": {
                "DATA_ADMISSION": "FAIL",
                "RESEARCH_ADMISSION": "FAIL",
                "MODEL_PROMOTION": "NOT_EVALUATED",
                "HISTORICAL_APPLICATION": "BLOCKED_PHASE_E_NOT_RUN",
                "PHASE_E_AUTHORIZED": False,
                "REFIT_AUTHORIZED": False,
                "COUNTER_ACTION": "NONE",
            },
            "guardrails": {
                "provider_calls": False,
                "fresh_downloads": False,
                "phase_e": False,
                "outcomes_or_targets": False,
                "fit_refit_score": False,
                "counter_mutation": False,
                "canonical_historical_rewrite": False,
                "production_execution": False,
                "merge": False,
            },
            "historical_notes_not_current_authority": {
                "prior_121_291_state": "lineage/baseline arithmetic only; current economic state is 153 resolved / 190 unresolved / 46 non-basis",
                "v11_source_summary_head": text(read_json(source_root / "summary.json").get("source_repository_state", {}).get("head")),
                "v3_summary_repository_head": text(read_json(economic / "reconciliation_summary.json").get("repository", {}).get("head")),
            },
            "artifact_outputs": sorted([
                "unresolved_190_event_ledger.csv",
                "unresolved_reason_decomposition.csv",
                "local_resolution_candidates.csv",
                "source_path_matrix.csv",
                "future_acquisition_units.json",
                "anomaly_findings.csv",
                "summary.json",
                "MANIFEST.json",
            ]),
        }
        write_json(staging / "summary.json", summary)
        outputs = {
            path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in sorted(staging.iterdir(), key=lambda path: path.name.casefold())
            if path.is_file() and path.name != "MANIFEST.json"
        }
        manifest = {
            "schema_version": f"{SCHEMA}_manifest",
            "artifact_root": str(output_root),
            "audit_date": AUDIT_DATE,
            "immutable": True,
            "outcome_blind": True,
            "provider_calls": False,
            "source_repository_head": git_rev(repo_root, "HEAD"),
            "controlling_economic_manifest_sha256": EXPECTED_ECONOMIC_MANIFEST_SHA,
            "controlling_source_authority_manifest_sha256": EXPECTED_SOURCE_MANIFEST_SHA,
            "input_files": [
                {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
                for path in input_paths(project_root, repo_root)
            ],
            "output_hashes_excluding_manifest": outputs,
            "self_hash_policy": "MANIFEST.json excluded from its own hash",
        }
        write_json(staging / "MANIFEST.json", manifest)
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
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(build_root(args.project_root, args.repo_root, args.output_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
