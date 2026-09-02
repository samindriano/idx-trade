"""Build the local, outcome-blind INC-001 economic-event reconciliation.

This runner consumes only retained V1.1 source rows, retained official
documents, and the already completed capability/probe ledgers.  It does not
call providers, acquire data, inspect outcomes, or rewrite canonical history.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from idx_trade import ca_economic_event_reconciliation_v1 as econ
from idx_trade import ca_source_authority_audit_v11 as source_audit


AUDIT_DATE = "2026-08-29"
ARTIFACT_SCHEMA = "inc001_ca_economic_event_reconciliation_v1"
EXPECTED = {
    "source_evidence_rows": 412,
    "cross_source_collapses": 20,
    "same_source_collapses": 3,
    "economic_event_count": 389,
    "resolved_transitions": 153,
    "unresolved_transitions": 190,
    "non_basis_excluded": 46,
}
MONTHS = {
    "Januari": 1,
    "Februari": 2,
    "Maret": 3,
    "April": 4,
    "Mei": 5,
    "Juni": 6,
    "Juli": 7,
    "Agustus": 8,
    "September": 9,
    "Oktober": 10,
    "November": 11,
    "Desember": 12,
}
DATE_RE = re.compile(
    r"\b(\d{1,2})\s+(Januari|Februari|Maret|April|Mei|Juni|Juli|"
    r"Agustus|September|Oktober|November|Desember)\s+(\d{4})\b",
    re.IGNORECASE,
)
RATIO_RE = re.compile(r"Rasio pemecahan unit saham\s+([^\r\n]+)", re.IGNORECASE)
NOMINAL_RE = re.compile(
    r"Nilai Nominal Lama\s+Rp\s*([0-9.,]+).*?Nominal baru\s+Rp\s*([0-9.,]+)",
    re.IGNORECASE | re.DOTALL,
)
REFERENCE_RE = re.compile(r"KSEI-\d+/JKU/\d+", re.IGNORECASE)
STOCK_SPLIT_TITLE = "Pemecahan Saham (Stock Split)"
DOC_FIELDS = [
    "document_id",
    "ticker",
    "document_number",
    "retrieval_mode",
    "status_code",
    "source_ref",
    "raw_path",
    "text_path",
    "document_reference",
    "evidence_sha256",
    "actual_sha256",
    "bytes_ledger",
    "bytes_actual",
    "hash_matches_bytes",
    "publication_date",
    "last_old_basis_trading_date",
    "first_new_basis_trading_date",
    "recording_date",
    "distribution_date",
    "ratio",
    "old_nominal",
    "new_nominal",
    "explicit_regular_market_semantic",
    "parser_status",
]
SOURCE_FIELDS = [
    "source_event_id",
    "source_kind",
    "ticker",
    "event_family",
    "source_native_label",
    "candidate_date",
    "cum_date",
    "record_date",
    "distribution_date",
    "ratio_raw",
    "ratio_left_security",
    "ratio_left_value",
    "ratio_right_security",
    "ratio_right_value",
    "status",
    "source_ref",
    "evidence_sha256",
    "source_contract_id",
    "raw_capture_path",
    "source_hash_matches_bytes",
    "raw_date_set",
    "raw_source_row_index",
    "idx_action_id",
    "idx_date_native",
    "idx_shares",
    "idx_shares_after",
]
ADJ_FIELDS = [
    "source_event_id",
    "adjudication_status",
    "economic_family",
    "basis_effect",
    "authority_source_ref",
    "authority_evidence_sha256",
    "source_native_label",
    "ticker",
    "candidate_date",
    "ratio_raw",
    "adjudication_reason",
]
LINK_FIELDS = [
    "left_source_event_id",
    "right_source_event_id",
    "relation",
    "authority_source_ref",
    "authority_evidence_sha256",
    "ticker",
    "source_families",
    "linkage_reason",
]
TRANSITION_FIELDS = [
    "source_event_id",
    "transition_status",
    "transition_semantic",
    "transition_date",
    "authority_source_ref",
    "authority_evidence_sha256",
    "source_kind",
    "ticker",
    "event_family",
    "candidate_date",
    "transition_reason",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid_sha(value: Any) -> bool:
    return econ.valid_sha256(value)


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def upper(value: Any) -> str:
    return text(value).upper()


def ticker(value: Any) -> str:
    return upper(value).replace(".JK", "")


def iso(value: Any) -> str:
    value = text(value)
    if not value:
        return ""
    candidate = value[:10]
    try:
        from datetime import date

        return date.fromisoformat(candidate).isoformat()
    except ValueError:
        return ""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def ratio_key(value: Any) -> tuple[str, str]:
    numbers = re.findall(r"\d+(?:[.,]\d+)?", text(value))
    return tuple(numbers[-2:]) if len(numbers) >= 2 else ("", "")


def raw_event_id(row: Mapping[str, Any]) -> str:
    return text(row.get("raw_row_identity") or row.get("event_id"))


def _relative_or_absolute(path: Path) -> str:
    return str(path)


def parse_document(entry: Mapping[str, Any], acquisition_root: Path, document_id: str) -> dict[str, Any] | None:
    raw_path = Path(text(entry.get("raw_path")))
    text_path = acquisition_root / "provider" / "text" / (raw_path.stem + ".txt")
    if not text_path.is_file():
        raise RuntimeError(f"missing retained extracted text for {raw_path}")
    body = text_path.read_text(encoding="utf-8", errors="replace")
    if STOCK_SPLIT_TITLE not in body:
        return None
    dates = []
    for day, month, year in DATE_RE.findall(body):
        dates.append(f"{int(year):04d}-{MONTHS[month.title()]:02d}-{int(day):02d}")
    ratio_match = RATIO_RE.search(body)
    nominal_match = NOMINAL_RE.search(body)
    reference = text((REFERENCE_RE.search(body) or [""])[0])
    parsed = {
        "document_id": document_id,
        "ticker": ticker(entry.get("ticker_hint")),
        "document_number": text(entry.get("document_number")),
        "retrieval_mode": text(entry.get("retrieval_mode")),
        "status_code": text(entry.get("status_code")),
        "source_ref": text(entry.get("final_url") or entry.get("requested_url")),
        "raw_path": _relative_or_absolute(raw_path),
        "text_path": _relative_or_absolute(text_path),
        "document_reference": reference,
        "evidence_sha256": text(entry.get("sha256")).lower(),
        "actual_sha256": sha256_file(raw_path) if raw_path.is_file() else "",
        "bytes_ledger": text(entry.get("bytes")),
        "bytes_actual": str(raw_path.stat().st_size) if raw_path.is_file() else "",
        "hash_matches_bytes": str(
            raw_path.is_file()
            and valid_sha(entry.get("sha256"))
            and sha256_file(raw_path).lower() == text(entry.get("sha256")).lower()
        ).lower(),
        "publication_date": dates[0] if len(dates) > 0 else "",
        "last_old_basis_trading_date": dates[1] if len(dates) > 1 else "",
        "first_new_basis_trading_date": dates[2] if len(dates) > 2 else "",
        "recording_date": dates[3] if len(dates) > 3 else "",
        "distribution_date": dates[4] if len(dates) > 4 else "",
        "ratio": text(ratio_match.group(1)) if ratio_match else "",
        "old_nominal": nominal_match.group(1) if nominal_match else "",
        "new_nominal": nominal_match.group(2) if nominal_match else "",
        "explicit_regular_market_semantic": str(
            "Mulai perdagangan saham dengan Nilai Nominal Baru" in body
            and "Pasar Reguler" in body
        ).lower(),
        "parser_status": "PARSED_EXACT_STOCK_SPLIT_SCHEDULE"
        if len(dates) >= 5 and ratio_match and nominal_match
        else "PARSED_BUT_INCOMPLETE_STOCK_SPLIT_SCHEDULE",
    }
    return parsed


def source_rows(context: Mapping[str, Any]) -> list[dict[str, Any]]:
    primary, _ = source_audit._build_primary_rows(context)
    rows: list[dict[str, Any]] = []
    for row in primary:
        normalized = {
            "source_event_id": raw_event_id(row),
            "source_kind": text(row.get("source_kind")),
            "ticker": ticker(row.get("ticker")),
            "event_family": text(row.get("event_family")),
            "source_native_label": text(row.get("source_native_label")),
            "candidate_date": iso(row.get("candidate_date")),
            "cum_date": iso(row.get("cum_date")),
            "record_date": iso(row.get("record_date")),
            "distribution_date": iso(row.get("distribution_date")),
            "ratio_raw": text(row.get("ratio_raw")),
            "ratio_left_security": text(row.get("ratio_left_security")),
            "ratio_left_value": text(row.get("ratio_left_value")),
            "ratio_right_security": text(row.get("ratio_right_security")),
            "ratio_right_value": text(row.get("ratio_right_value")),
            "status": text(row.get("status")),
            "source_ref": text(row.get("source_ref")),
            "evidence_sha256": text(row.get("evidence_sha256")).lower(),
            "source_contract_id": text(row.get("source_contract_id")),
            "raw_capture_path": text(row.get("raw_capture_path")),
            "source_hash_matches_bytes": text(row.get("source_hash_matches_bytes")),
            "raw_date_set": text(row.get("raw_date_set")),
            "raw_source_row_index": text(row.get("raw_source_row_index")),
            "idx_action_id": text(row.get("idx_action_id")),
            "idx_date_native": text(row.get("idx_date_native")),
            "idx_shares": text(row.get("idx_shares")),
            "idx_shares_after": text(row.get("idx_shares_after")),
        }
        if not normalized["source_event_id"]:
            raise RuntimeError("source row without immutable event identity")
        if not normalized["source_ref"] or not valid_sha(normalized["evidence_sha256"]):
            raise RuntimeError(f"source row lacks ref/hash: {normalized['source_event_id']}")
        rows.append(normalized)
    return sorted(rows, key=lambda row: (row["source_kind"], row["ticker"], row["candidate_date"], row["source_event_id"]))


def document_inventory(acquisition_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entries = read_json(acquisition_root / "provider" / "document_request_ledger.json")
    documents: list[dict[str, Any]] = []
    parsed: list[dict[str, Any]] = []
    for entry in entries:
        document_id = f"ACQ-DOC-{int(entry['document_number']):03d}"
        document = parse_document(entry, acquisition_root, document_id)
        if document is None:
            continue
        documents.append(document)
        if (
            text(entry.get("status_code")) == "200"
            and document["parser_status"] == "PARSED_EXACT_STOCK_SPLIT_SCHEDULE"
        ):
            parsed.append(document)
    return documents, parsed


def probe_inventory(probe_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entries = read_json(probe_root / "provider" / "documents" / "document_request_ledger.json")
    documents: list[dict[str, Any]] = []
    stock_split_documents: list[dict[str, Any]] = []
    for entry in entries:
        request_number = int(entry["request_number"])
        raw_path = Path(text(entry["raw_path"]))
        text_path = raw_path.with_suffix(".txt")
        body = text_path.read_text(encoding="utf-8", errors="replace")
        dates = [
            f"{int(year):04d}-{MONTHS[month.title()]:02d}-{int(day):02d}"
            for day, month, year in DATE_RE.findall(body)
        ]
        ratio_match = RATIO_RE.search(body)
        document = {
            "document_id": f"PROBE-DOC-{request_number:03d}",
            "ticker": ticker(Path(text(entry.get("requested_url"))).stem.split("_")[0]),
            "document_number": str(request_number),
            "retrieval_mode": text(entry.get("retrieval_mode")),
            "status_code": text(entry.get("status_code")),
            "source_ref": text(entry.get("final_url") or entry.get("requested_url")),
            "raw_path": str(raw_path),
            "text_path": str(text_path),
            "document_reference": text((REFERENCE_RE.search(body) or [""])[0]),
            "evidence_sha256": text(entry.get("sha256")).lower(),
            "actual_sha256": sha256_file(raw_path),
            "bytes_ledger": text(entry.get("bytes")),
            "bytes_actual": str(raw_path.stat().st_size),
            "hash_matches_bytes": str(
                valid_sha(entry.get("sha256"))
                and sha256_file(raw_path).lower() == text(entry.get("sha256")).lower()
            ).lower(),
            "publication_date": dates[0] if dates else "",
            "last_old_basis_trading_date": dates[1] if len(dates) > 1 else "",
            "first_new_basis_trading_date": dates[2] if len(dates) > 2 else "",
            "recording_date": dates[3] if len(dates) > 3 else "",
            "distribution_date": dates[4] if len(dates) > 4 else "",
            "ratio": text(ratio_match.group(1)) if ratio_match else "",
            "old_nominal": "",
            "new_nominal": "",
            "explicit_regular_market_semantic": str(
                "Mulai perdagangan saham dengan Nilai Nominal Baru" in body
                and "Pasar Reguler" in body
            ).lower(),
            "parser_status": "PARSED_PROBE_DOCUMENT",
        }
        documents.append(document)
        if ticker(entry.get("requested_url").split("/")[-1].split("_")[0]) in {"ERAA", "MLPT"}:
            stock_split_documents.append(document)
    return documents, stock_split_documents


def standalone_schedule_inventory(project_root: Path) -> list[dict[str, Any]]:
    schedule_root = project_root / "idx-v4-ca-schedule-evidence-20260818-v3"
    specs = [
        {
            "document_id": "RETAINED-SCHEDULE-CYBR",
            "ticker": "CYBR",
            "candidate_date": "2026-05-18",
            "first_new_basis_trading_date": "2026-05-13",
            "document_reference": "KSEI-10461/JKU/0526",
            "source_ref": "KSEI-10461/JKU/0526",
            "evidence_sha256": "0ce4387eb987edf80a6a463aa631ae038a05f5760261430cac0a19057b0ed5fe",
            "raw_path": schedule_root / "raw" / "documents" / "KSEI-10461_JKU_0526_attempt_01.pdf",
            "ratio": "1:2",
        },
        {
            "document_id": "RETAINED-SCHEDULE-DSSA-2024",
            "ticker": "DSSA",
            "candidate_date": "2024-07-17",
            "first_new_basis_trading_date": "2024-07-18",
            "document_reference": "KSEI-17101/JKU/0724",
            "source_ref": "KSEI-17101/JKU/0724",
            "evidence_sha256": "002c41c2875b2cf48067f85bfe1f44064c0c7d41cdbc2172f4ade672ae7c6c97",
            "raw_path": schedule_root / "raw" / "documents" / "KSEI-17101_JKU_0724_attempt_01.pdf",
            "ratio": "1:10",
        },
        {
            "document_id": "RETAINED-SCHEDULE-NETV",
            "ticker": "NETV",
            "candidate_date": "2024-10-21",
            "first_new_basis_trading_date": "2024-10-22",
            "document_reference": "KSEI-24744/JKU/1024",
            "source_ref": "KSEI-24744/JKU/1024",
            "evidence_sha256": "7dd3bd41b82367907586d23d60b966d3cc354c24730e03f8db2e2360ec65a1f4",
            "raw_path": schedule_root / "raw" / "documents" / "KSEI-24744_JKU_1024_attempt_01.pdf",
            "ratio": "2:1",
        },
    ]
    for row in specs:
        path = Path(row["raw_path"])
        row["raw_path"] = str(path)
        row["actual_sha256"] = sha256_file(path) if path.is_file() else ""
        row["hash_matches_bytes"] = str(
            path.is_file() and row["actual_sha256"].lower() == row["evidence_sha256"]
        ).lower()
    return specs


def find_source(rows: Sequence[Mapping[str, Any]], event_id: str) -> Mapping[str, Any]:
    for row in rows:
        if text(row.get("source_event_id")) == event_id:
            return row
    raise RuntimeError(f"unknown source event {event_id}")


def target_document_map(
    source: Sequence[Mapping[str, Any]],
    acquisition_documents: Sequence[Mapping[str, Any]],
    probe_documents: Sequence[Mapping[str, Any]],
    acquisition_root: Path,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    targets = read_csv(acquisition_root / "stock_split_targets.csv")
    docs = [*acquisition_documents, *probe_documents]
    by_event: dict[str, dict[str, Any]] = {}
    adjudication_documents: list[dict[str, Any]] = []
    target_ids = {text(row["event_id"]) for row in targets}
    for target in targets:
        event_id = text(target["event_id"])
        candidates = [
            doc
            for doc in docs
            if doc.get("ticker") == ticker(target["ticker"])
            and doc.get("first_new_basis_trading_date") == iso(target["candidate_date"])
            and doc.get("parser_status") == "PARSED_EXACT_STOCK_SPLIT_SCHEDULE"
        ]
        if not candidates:
            continue
        candidates.sort(key=lambda doc: (text(doc.get("document_id")), text(doc.get("evidence_sha256"))))
        chosen = dict(candidates[0])
        chosen["target_event_id"] = event_id
        chosen["target_candidate_date"] = iso(target["candidate_date"])
        by_event[event_id] = chosen
        adjudication_documents.append(chosen)
    if not target_ids.issuperset(by_event):
        raise RuntimeError("target document map contains an unknown target event")
    return by_event, adjudication_documents


def probe_transition_rows(probe_root: Path) -> list[dict[str, Any]]:
    rows = read_csv(probe_root / "representative_linkage_results.csv")
    result: list[dict[str, Any]] = []
    for row in rows:
        classification = upper(row.get("result_classification"))
        if not classification.startswith("RESOLVED"):
            continue
        event_id = text(row.get("event_id"))
        if event_id not in {
            "2d3d3f62ee9f5553dcbe3cf5db962eefbfdf6437f37cc1185edb3c1c3a0877e0",
            "38b59adf7e0ede37b0cd1d102f941783adcc0d308dfa4a1c758a5678031e159a",
            "be7065dfbb3f479026d0701928b1eb26bc39de606e4e2e2bc20b4b925442a16a",
        }:
            continue
        result.append(
            {
                "source_event_id": event_id,
                "transition_status": "RESOLVED",
                "transition_semantic": text(row.get("accepted_transition_semantic")),
                "transition_date": iso(row.get("accepted_transition_date")),
                "authority_source_ref": text(row.get("official_document_url")),
                "authority_evidence_sha256": text(row.get("official_document_sha256")).lower(),
                "transition_reason": text(row.get("notes")),
            }
        )
    return result


def build_adjudications(
    source: Sequence[Mapping[str, Any]],
    target_docs: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    mconv = [row for row in source if upper(row.get("event_family")) == "MANDATORY_CONVERSION"]
    vconv = [row for row in source if upper(row.get("event_family")) == "VOLUNTARY_CONVERSION"]
    for row in mconv:
        event_id = text(row["source_event_id"])
        source_ref = text(row["source_ref"])
        source_sha = text(row["evidence_sha256"]).lower()
        raw_right = upper(row.get("ratio_right_security"))
        raw_left = upper(row.get("ratio_left_security"))
        if raw_right and raw_right != raw_left:
            family = "TRUE_SECURITY_CONVERSION"
            reason = "source-native ratio names a different receiving security"
        elif row.get("source_kind", "").upper().startswith("IDX") and upper(row.get("source_native_label")) == "OBLIGASIWajibKONVERSI".upper():
            family = "TRUE_SECURITY_CONVERSION"
            reason = "source-native IDX obligasiWajibKonversi action is a security-conversion instrument"
        elif raw_right == raw_left and ratio_key(row.get("ratio_raw")):
            left, right = ratio_key(row.get("ratio_raw"))
            family = "REVERSE_SPLIT" if float(right.replace(",", ".")) < float(left.replace(",", ".")) else "STOCK_SPLIT"
            reason = "source-native KSEI Mandatory Conversion row has same-security nominal ratio"
        else:
            family = "TRUE_SECURITY_CONVERSION" if upper(row.get("source_native_label")) == "OBLIGASIWajibKONVERSI".upper() else "UNRESOLVED_OPERATIONAL_LABEL"
            reason = "source-native mechanism is not sufficiently specific"
        authority_ref = source_ref
        authority_sha = source_sha
        if event_id in target_docs:
            doc = target_docs[event_id]
            authority_ref = text(doc.get("source_ref"))
            authority_sha = text(doc.get("evidence_sha256")).lower()
            reason += "; exact retained official schedule binds ticker, ratio, and dates"
        rows.append(
            {
                "source_event_id": event_id,
                "adjudication_status": "PROVEN",
                "economic_family": family,
                "basis_effect": "BASIS_CHANGING",
                "authority_source_ref": authority_ref,
                "authority_evidence_sha256": authority_sha,
                "source_native_label": text(row.get("source_native_label")),
                "ticker": ticker(row.get("ticker")),
                "candidate_date": iso(row.get("candidate_date")),
                "ratio_raw": text(row.get("ratio_raw")),
                "adjudication_reason": reason,
            }
        )
    for row in vconv:
        event_id = text(row["source_event_id"])
        if upper(row.get("ratio_right_security")) != "IDR":
            continue
        rows.append(
            {
                "source_event_id": event_id,
                "adjudication_status": "PROVEN",
                "economic_family": "TENDER_OFFER_OR_CASH_PROCESS",
                "basis_effect": "NON_BASIS",
                "authority_source_ref": text(row.get("source_ref")),
                "authority_evidence_sha256": text(row.get("evidence_sha256")).lower(),
                "source_native_label": text(row.get("source_native_label")),
                "ticker": ticker(row.get("ticker")),
                "candidate_date": iso(row.get("candidate_date")),
                "ratio_raw": text(row.get("ratio_raw")),
                "adjudication_reason": "retained KSEI row explicitly records Voluntary Conversion with IDR consideration and no receiving security; source-native evidence supports non-basis cash process, not ratio shape alone",
            }
        )
    return sorted(rows, key=lambda row: row["source_event_id"])


def build_linkages(
    source: Sequence[Mapping[str, Any]],
    target_docs: Mapping[str, Mapping[str, Any]],
    probe_documents: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    idx_splits = [
        row
        for row in source
        if row.get("source_kind") == "IDX_GET_ISSUED_HISTORY"
        and upper(row.get("event_family")) == "STOCK_SPLIT"
    ]
    all_docs = list(target_docs.values()) + list(probe_documents)
    links: list[dict[str, Any]] = []
    used_pairs: set[tuple[str, str]] = set()
    for mconv in [row for row in source if upper(row.get("event_family")) == "MANDATORY_CONVERSION"]:
        candidates = [
            doc
            for doc in all_docs
            if doc.get("ticker") == ticker(mconv.get("ticker"))
            and iso(mconv.get("candidate_date")) in {
                doc.get("last_old_basis_trading_date"),
                doc.get("first_new_basis_trading_date"),
                doc.get("recording_date"),
                doc.get("distribution_date"),
            }
            and ratio_key(doc.get("ratio")) == ratio_key(mconv.get("ratio_raw"))
            and doc.get("parser_status") in {
                "PARSED_EXACT_STOCK_SPLIT_SCHEDULE",
                "PARSED_PROBE_DOCUMENT",
            }
        ]
        if not candidates:
            continue
        candidates.sort(key=lambda doc: (text(doc.get("document_id")), text(doc.get("evidence_sha256"))))
        doc = candidates[0]
        idx_candidates = [
            row
            for row in idx_splits
            if ticker(row.get("ticker")) == doc.get("ticker")
            and iso(row.get("candidate_date")) == doc.get("first_new_basis_trading_date")
        ]
        for idx in idx_candidates:
            pair = tuple(sorted((text(mconv["source_event_id"]), text(idx["source_event_id"]))))
            if pair in used_pairs:
                continue
            used_pairs.add(pair)
            links.append(
                {
                    "left_source_event_id": pair[0],
                    "right_source_event_id": pair[1],
                    "relation": "PROVEN_SAME_ECONOMIC_EVENT",
                    "authority_source_ref": text(doc.get("source_ref")),
                    "authority_evidence_sha256": text(doc.get("evidence_sha256")).lower(),
                    "ticker": doc.get("ticker"),
                    "source_families": "MANDATORY_CONVERSION|STOCK_SPLIT",
                    "linkage_reason": "same issuer, same nominal ratio, and one retained official schedule explicitly binds old-basis last trading date to first new-basis regular-market trading date",
                }
            )
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in idx_splits:
        grouped[(ticker(row.get("ticker")), iso(row.get("candidate_date")))].append(row)
    for key, group in sorted(grouped.items()):
        if len(group) < 2:
            continue
        event_ids = sorted(text(row["source_event_id"]) for row in group)
        doc = next((target_docs[event_id] for event_id in event_ids if event_id in target_docs), None)
        if not doc:
            continue
        for right_id in event_ids[1:]:
            pair = tuple(sorted((event_ids[0], right_id)))
            if pair in used_pairs:
                continue
            used_pairs.add(pair)
            links.append(
                {
                    "left_source_event_id": pair[0],
                    "right_source_event_id": pair[1],
                    "relation": "PROVEN_SAME_ECONOMIC_EVENT",
                    "authority_source_ref": text(doc.get("source_ref")),
                    "authority_evidence_sha256": text(doc.get("evidence_sha256")).lower(),
                    "ticker": key[0],
                    "source_families": "STOCK_SPLIT|STOCK_SPLIT",
                    "linkage_reason": "same IDX source kind, issuer, candidate date, and one exact official schedule; duplicate source representations are collapsed without dropping either source ID",
                }
            )
    return sorted(links, key=lambda row: (row["left_source_event_id"], row["right_source_event_id"]))


def build_transitions(
    source: Sequence[Mapping[str, Any]],
    context: Mapping[str, Any],
    target_docs: Mapping[str, Mapping[str, Any]],
    probe_root: Path,
    standalone_docs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    primary, _ = source_audit._build_primary_rows(context)
    baseline, _summary = source_audit._transition_reconstruction(primary, context)
    source_by_id = {text(row["source_event_id"]): row for row in source}
    rows: dict[str, dict[str, Any]] = {}
    for item in baseline:
        if item.get("record_kind") != "RAW_SOURCE_EVENT" or upper(item.get("v11_raw_recomputed_class")) != "RESOLVED":
            continue
        event_id = text(item.get("event_id"))
        source_row = source_by_id[event_id]
        rows[event_id] = {
            "source_event_id": event_id,
            "transition_status": "RESOLVED",
            "transition_semantic": "REGULAR_MARKET_EX_DATE",
            "transition_date": iso(item.get("transition_date")),
            "authority_source_ref": text(source_row.get("source_ref")),
            "authority_evidence_sha256": text(source_row.get("evidence_sha256")).lower(),
            "source_kind": source_row.get("source_kind"),
            "ticker": source_row.get("ticker"),
            "event_family": source_row.get("event_family"),
            "candidate_date": source_row.get("candidate_date"),
            "transition_reason": text(item.get("resolution_reason")),
        }
    for row in probe_transition_rows(probe_root):
        source_row = source_by_id[row["source_event_id"]]
        row.update(
            {
                "source_kind": source_row.get("source_kind"),
                "ticker": source_row.get("ticker"),
                "event_family": source_row.get("event_family"),
                "candidate_date": source_row.get("candidate_date"),
            }
        )
        rows[row["source_event_id"]] = row
    for event_id, doc in target_docs.items():
        source_row = source_by_id[event_id]
        rows[event_id] = {
            "source_event_id": event_id,
            "transition_status": "RESOLVED",
            "transition_semantic": "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE",
            "transition_date": doc["first_new_basis_trading_date"],
            "authority_source_ref": text(doc["source_ref"]),
            "authority_evidence_sha256": text(doc["evidence_sha256"]).lower(),
            "source_kind": source_row.get("source_kind"),
            "ticker": source_row.get("ticker"),
            "event_family": source_row.get("event_family"),
            "candidate_date": source_row.get("candidate_date"),
            "transition_reason": "exact retained KSEI schedule explicitly states first trading with new nominal in Pasar Reguler dan Pasar Negosiasi",
        }
    standalone_by_key = {
        (doc["ticker"], doc["candidate_date"]): doc for doc in standalone_docs
    }
    for source_row in source:
        key = (ticker(source_row.get("ticker")), iso(source_row.get("candidate_date")))
        doc = standalone_by_key.get(key)
        if not doc:
            continue
        rows[text(source_row["source_event_id"])] = {
            "source_event_id": text(source_row["source_event_id"]),
            "transition_status": "RESOLVED",
            "transition_semantic": "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE",
            "transition_date": doc["first_new_basis_trading_date"],
            "authority_source_ref": doc["source_ref"],
            "authority_evidence_sha256": doc["evidence_sha256"],
            "source_kind": source_row.get("source_kind"),
            "ticker": source_row.get("ticker"),
            "event_family": source_row.get("event_family"),
            "candidate_date": source_row.get("candidate_date"),
            "transition_reason": "retained official schedule explicitly states first new-basis regular-market trading date",
        }
    return sorted(rows.values(), key=lambda row: row["source_event_id"])


def source_evidence_documents(documents: Sequence[Mapping[str, Any]], standalone: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for doc in [*documents, *standalone]:
        row = dict(doc)
        row["evidence_role"] = "OFFICIAL_STOCK_SPLIT_OR_TRANSITION_DOCUMENT"
        rows.append(row)
    return sorted(rows, key=lambda row: (text(row.get("ticker")), text(row.get("document_id"))))


def economic_csv_rows(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for event in result["economic_events"]:
        row = dict(event)
        row["source_event_ids"] = "|".join(event["source_event_ids"])
        row["source_kinds"] = "|".join(event["source_kinds"])
        row["transition_semantics"] = "|".join(event["transition_semantics"])
        rows.append(row)
    return sorted(rows, key=lambda row: text(row.get("economic_event_id")))


def gap_rows(result: Mapping[str, Any], source_by_id: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for event in result["economic_events"]:
        if event["transition_status"] == "UNRESOLVED":
            grouped[event["economic_family"]].append(event)
    rows = []
    for family, events in sorted(grouped.items()):
        members = [member for event in events for member in event["source_event_ids"]]
        tickers = sorted({ticker(source_by_id[member].get("ticker")) for member in members})
        sources = sorted({text(source_by_id[member].get("source_kind")) for member in members})
        missing = {
            "RIGHTS_HMETD": "accepted REGULAR_MARKET_EX_DATE",
            "STOCK_SPLIT": "accepted REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE",
            "REVERSE_SPLIT": "accepted REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE",
            "TRUE_SECURITY_CONVERSION": "source-specific accepted transition semantic",
            "CAPITAL_RESTRUCTURING": "source-specific accepted transition semantic",
            "BONUS_SHARES": "accepted regular-market ex/basis semantic",
            "STOCK_DIVIDEND": "accepted regular-market ex/basis semantic",
            "MERGER": "source-specific accepted transition semantic",
            "UNRESOLVED_OPERATIONAL_LABEL": "source-bound economic adjudication and accepted transition semantic",
            "UNKNOWN_TAXONOMY": "taxonomy policy plus source semantics and transition semantic",
        }.get(family, "source-contract transition semantic")
        rows.append(
            {
                "economic_family": family,
                "economic_event_count": len(events),
                "ticker_count": len(tickers),
                "tickers": "|".join(tickers),
                "economic_event_ids": "|".join(sorted(text(event["economic_event_id"]) for event in events)),
                "source_kinds": "|".join(sources),
                "missing_semantic": missing,
            }
        )
    return rows


def manifest_for(root: Path, source_head: str) -> dict[str, Any]:
    outputs = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.json":
            outputs[str(path.relative_to(root)).replace("\\", "/")] = {
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
    return {
        "manifest_version": f"{ARTIFACT_SCHEMA}_manifest",
        "artifact_root": str(root),
        "audit_date": AUDIT_DATE,
        "source_head": source_head,
        "outcome_blind": True,
        "provider_calls": False,
        "output_hashes_excluding_manifest": outputs,
        "self_hash_policy": "MANIFEST.json excluded from its own hash",
    }


def git_head(repo_root: Path) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(repo_root), "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def build_root(
    project_root: Path,
    repo_root: Path,
    acquisition_root: Path,
    probe_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    if output_root.exists():
        raise FileExistsError(f"immutable output root already exists: {output_root}")
    staging = output_root.with_name(output_root.name + ".staging")
    if staging.exists():
        raise FileExistsError(f"staging output root already exists: {staging}")
    staging.mkdir(parents=True)
    try:
        population = source_audit._load_population(project_root)
        context = source_audit._load_raw_context(project_root, population)
        source = source_rows(context)
        if len(source) != EXPECTED["source_evidence_rows"]:
            raise RuntimeError(f"source row count diverges: {len(source)}")
        acquisition_documents, acquisition_stock_splits = document_inventory(acquisition_root)
        probe_documents, probe_stock_splits = probe_inventory(probe_root)
        standalone = standalone_schedule_inventory(project_root)
        target_docs, target_doc_rows = target_document_map(
            source, acquisition_stock_splits, probe_stock_splits, acquisition_root
        )
        adjudications = build_adjudications(source, target_docs)
        linkages = build_linkages(source, target_docs, probe_stock_splits)
        transitions = build_transitions(source, context, target_docs, probe_root, standalone)
        source_by_id = {row["source_event_id"]: row for row in source}

        core_adjudications = [{key: row[key] for key in (
            "source_event_id", "adjudication_status", "economic_family", "basis_effect",
            "authority_source_ref", "authority_evidence_sha256",
        )} for row in adjudications]
        core_linkages = [{key: row[key] for key in (
            "left_source_event_id", "right_source_event_id", "relation",
            "authority_source_ref", "authority_evidence_sha256",
        )} for row in linkages]
        core_transitions = [{key: row[key] for key in (
            "source_event_id", "transition_status", "transition_semantic", "transition_date",
            "authority_source_ref", "authority_evidence_sha256",
        )} for row in transitions]
        result = econ.reconcile_economic_events(
            source,
            adjudications=core_adjudications,
            linkages=core_linkages,
            transition_attestations=core_transitions,
        )
        actual = {key: result[key] for key in EXPECTED}
        comparison = {
            key: {"expected": EXPECTED[key], "actual": actual[key], "match": EXPECTED[key] == actual[key]}
            for key in EXPECTED
        }
        exact_working_verdict = "CERTIFIED" if all(item["match"] for item in comparison.values()) else "REJECTED_WITH_DIFFERENCES"

        index_ledger = read_json(acquisition_root / "provider" / "index_request_ledger.json")
        request_numbers = [int(row["request_number"]) for row in index_ledger]
        request_duplicates = sorted(number for number, count in Counter(request_numbers).items() if count > 1)
        continuity = request_numbers == list(range(1, len(request_numbers) + 1))
        if not continuity or request_duplicates:
            raise RuntimeError("merged request ledger is not continuous and unique")

        source_doc_rows = source_evidence_documents([*acquisition_documents, *probe_documents], standalone)
        source_hash_failures = [row for row in source_doc_rows if row.get("hash_matches_bytes") != "true"]
        if source_hash_failures:
            raise RuntimeError(f"retained document hash failures: {len(source_hash_failures)}")

        family_distribution = Counter(event["economic_family"] for event in result["economic_events"])
        source_distribution = Counter(
            kind
            for event in result["economic_events"]
            for kind in event["source_kinds"]
        )
        mconv_ids = {row["source_event_id"] for row in source if upper(row.get("event_family")) == "MANDATORY_CONVERSION"}
        vconv_ids = {row["source_event_id"] for row in source if upper(row.get("event_family")) == "VOLUNTARY_CONVERSION"}
        event_by_source = {
            member: event for event in result["economic_events"] for member in event["source_event_ids"]
        }
        mconv_counts = Counter(event_by_source[event_id]["economic_family"] for event_id in mconv_ids)
        vconv_counts = Counter(event_by_source[event_id]["economic_family"] for event_id in vconv_ids)
        unresolved_by_source = Counter(
            source_by_id[member]["source_kind"]
            for event in result["economic_events"]
            if event["transition_status"] == "UNRESOLVED"
            for member in event["source_event_ids"]
        )
        validation = {
            "request_ledger_before_count": 20,
            "continuation_rows_merged": 2,
            "request_ledger_after_count": len(index_ledger),
            "request_ledger_duplicates": request_duplicates,
            "request_ledger_continuous_1_to_n": continuity,
            "source_evidence_rows": len(source),
            "retained_document_rows_verified": len(source_doc_rows),
            "retained_document_hash_failures": len(source_hash_failures),
            "adjudication_rows": len(adjudications),
            "proven_linkage_rows": len(linkages),
            "transition_attestation_rows": len(transitions),
            "collapse_arithmetic": len(source) - result["cross_source_collapses"] - result["same_source_collapses"] == result["economic_event_count"],
            "transition_arithmetic": result["resolved_transitions"] + result["unresolved_transitions"] + result["non_basis_excluded"] == result["economic_event_count"],
            "all_proven_adjudications_have_ref_and_valid_sha": all(text(row["authority_source_ref"]) and valid_sha(row["authority_evidence_sha256"]) for row in adjudications),
            "all_proven_linkages_have_ref_and_valid_sha": all(text(row["authority_source_ref"]) and valid_sha(row["authority_evidence_sha256"]) for row in linkages),
            "all_resolved_transitions_have_accepted_semantic_date_ref_sha": all(
                row["transition_semantic"] in econ.ACCEPTED_TRANSITION_SEMANTICS
                and iso(row["transition_date"])
                and text(row["authority_source_ref"])
                and valid_sha(row["authority_evidence_sha256"])
                for row in transitions
            ),
        }
        summary = {
            "schema_version": ARTIFACT_SCHEMA,
            "audit_date": AUDIT_DATE,
            "status": "LOCAL_ECONOMIC_EVENT_RECONCILIATION_COMPLETE_NO_SCIENTIFIC_ADMISSION",
            "repository": {
                "branch": "data/ca-aware-feature-basis-remediation-v1",
                "head": git_head(repo_root),
                "successor_module": "src/idx_trade/ca_economic_event_reconciliation_v1.py",
            },
            "population": {
                "fit_tickers": len(population["fit_tickers"]),
                "application_tickers": len(population["app_tickers"]),
                "closure_tickers": len(population["closure_tickers"]),
                "closure_start": population["closure_start"],
                "closure_end": population["closure_end"],
            },
            "request_ledger": {
                "before_count": 20,
                "continuation_rows_merged": 2,
                "after_count": len(index_ledger),
                "duplicates": request_duplicates,
                "request_numbers": request_numbers,
            },
            "counts": actual,
            "working_count_comparison": comparison,
            "working_389_153_190_46_verdict": exact_working_verdict,
            "mconv_adjudication": {
                "economic_stock_split": mconv_counts["STOCK_SPLIT"],
                "economic_reverse_split": mconv_counts["REVERSE_SPLIT"],
                "true_security_conversion": mconv_counts["TRUE_SECURITY_CONVERSION"],
                "unresolved": mconv_counts["UNRESOLVED_OPERATIONAL_LABEL"],
            },
            "vconv_adjudication": {
                "tender_or_cash": vconv_counts["TENDER_OFFER_OR_CASH_PROCESS"],
                "true_security_conversion": vconv_counts["TRUE_SECURITY_CONVERSION"],
                "other": sum(vconv_counts[key] for key in vconv_counts if key not in {"TENDER_OFFER_OR_CASH_PROCESS", "TRUE_SECURITY_CONVERSION", "UNRESOLVED_OPERATIONAL_LABEL"}),
                "unresolved_operational_label": vconv_counts["UNRESOLVED_OPERATIONAL_LABEL"],
            },
            "family_distribution": dict(sorted(family_distribution.items())),
            "source_distribution": dict(sorted(source_distribution.items())),
            "unresolved_by_source": dict(sorted(unresolved_by_source.items())),
            "residual_geometry": gap_rows(result, source_by_id),
            "validation": validation,
            "scientific_verdict_unchanged": {
                "DATA_ADMISSION": "FAIL",
                "RESEARCH_ADMISSION": "FAIL",
                "MODEL_PROMOTION": "NOT_EVALUATED",
                "HISTORICAL_APPLICATION": "BLOCKED_PHASE_E_NOT_RUN",
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
        }

        write_json(staging / "merged_index_request_ledger.json", index_ledger)
        write_csv(staging / "source_evidence_ledger.csv", source, SOURCE_FIELDS)
        write_csv(staging / "retained_document_evidence.csv", source_doc_rows, DOC_FIELDS + ["evidence_role"])
        write_csv(staging / "economic_adjudication_ledger.csv", adjudications, ADJ_FIELDS)
        write_csv(staging / "proven_same_event_linkage_ledger.csv", linkages, LINK_FIELDS)
        write_csv(staging / "transition_attestation_ledger.csv", transitions, TRANSITION_FIELDS)
        write_csv(staging / "economic_event_ledger.csv", economic_csv_rows(result), [
            "economic_event_id", "source_event_ids", "source_kinds", "economic_family", "basis_effect",
            "classification_conflict", "transition_status", "transition_date", "transition_semantics",
        ])
        unresolved = [
            row for row in economic_csv_rows(result) if row["transition_status"] == "UNRESOLVED"
        ]
        non_basis = [
            row for row in economic_csv_rows(result) if row["transition_status"] == "NOT_APPLICABLE_NON_BASIS"
        ]
        write_csv(staging / "unresolved_economic_event_ledger.csv", unresolved, [
            "economic_event_id", "source_event_ids", "source_kinds", "economic_family", "basis_effect",
            "classification_conflict", "transition_status", "transition_date", "transition_semantics",
        ])
        write_csv(staging / "non_basis_exclusion_ledger.csv", non_basis, [
            "economic_event_id", "source_event_ids", "source_kinds", "economic_family", "basis_effect",
            "classification_conflict", "transition_status", "transition_date", "transition_semantics",
        ])
        write_csv(staging / "remaining_gap_geometry.csv", gap_rows(result, source_by_id), [
            "economic_family", "economic_event_count", "ticker_count", "tickers", "economic_event_ids",
            "source_kinds", "missing_semantic",
        ])
        write_json(staging / "reconciliation_summary.json", summary)
        write_json(staging / "validation_report.json", validation)
        source_authority_root = project_root / source_audit.AUDIT_ROOT_NAME.replace("-final", "-deterministic-rerun-v8")
        write_json(staging / "deterministic_input_pins.json", {
            "source_authority_root": str(source_authority_root),
            "source_authority_manifest_sha256": sha256_file(source_authority_root / "MANIFEST.json"),
            "acquisition_root": str(acquisition_root),
            "acquisition_index_ledger_sha256": sha256_file(acquisition_root / "provider" / "index_request_ledger.json"),
            "acquisition_document_ledger_sha256": sha256_file(acquisition_root / "provider" / "document_request_ledger.json"),
            "probe_root": str(probe_root),
            "probe_manifest_sha256": sha256_file(probe_root / "MANIFEST.json"),
            "repo_head": git_head(repo_root),
            "expected_counts": EXPECTED,
        })
        output_manifest = manifest_for(staging, git_head(repo_root))
        write_json(staging / "MANIFEST.json", output_manifest)
        staging.rename(output_root)
        return summary
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def compare_non_manifest(first: Path, second: Path) -> dict[str, Any]:
    first_files = {str(path.relative_to(first)).replace("\\", "/") for path in first.rglob("*") if path.is_file() and path.name != "MANIFEST.json"}
    second_files = {str(path.relative_to(second)).replace("\\", "/") for path in second.rglob("*") if path.is_file() and path.name != "MANIFEST.json"}
    all_files = sorted(first_files | second_files)
    differences = []
    for name in all_files:
        left = first / name
        right = second / name
        if not left.is_file() or not right.is_file() or left.read_bytes() != right.read_bytes():
            differences.append(name)
    return {
        "first_root": str(first),
        "second_root": str(second),
        "compared_file_count": len(all_files),
        "differences": differences,
        "verdict": "PASS" if not differences and first_files == second_files else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(r"D:\Documents\Project"))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--acquisition-root", type=Path, default=Path(r"D:\Documents\Project\idx-ca-stock-split-acquisition-20260829-v1"))
    parser.add_argument("--probe-root", type=Path, default=Path(r"D:\Documents\Project\idx-ca-transition-capability-probe-20260829-v1"))
    parser.add_argument("--output-root", type=Path, default=Path(r"D:\Documents\Project\idx-ca-economic-event-reconciliation-20260829-v1"))
    parser.add_argument("--rerun-root", type=Path, default=Path(r"D:\Documents\Project\idx-ca-economic-event-reconciliation-20260829-v1-rerun"))
    args = parser.parse_args()
    first = build_root(args.project_root, args.repo_root, args.acquisition_root, args.probe_root, args.output_root)
    second = build_root(args.project_root, args.repo_root, args.acquisition_root, args.probe_root, args.rerun_root)
    comparison = compare_non_manifest(args.output_root, args.rerun_root)
    write_json(args.output_root / "deterministic_non_manifest_comparison.json", comparison)
    write_json(args.rerun_root / "deterministic_non_manifest_comparison.json", comparison)
    write_json(args.output_root / "MANIFEST.json", manifest_for(args.output_root, git_head(args.repo_root)))
    write_json(args.rerun_root / "MANIFEST.json", manifest_for(args.rerun_root, git_head(args.repo_root)))
    print(json.dumps({"summary": first, "rerun_summary": second, "comparison": comparison}, sort_keys=True))
    return 0 if comparison["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
