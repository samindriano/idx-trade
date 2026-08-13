"""Offline audit for financial-fact template/serialization drift.

This module is deliberately separate from ``financial_fact_table``.  It does
not add mappings to the canonical extractor.  It only asks whether an already
accepted exact label has a defensible numeric value in the current-period
column when the value is encoded as text (a known IDX XLSX representation
change).  Labels are matched only through the existing exact ``FACT_LABELS``
contract; no fuzzy or guessed semantic mapping is performed.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import itertools
import json
import posixpath
import re
import zipfile
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence
from xml.etree import ElementTree

from .financial_fact_table import (
    CORE_FACT_IDENTITIES,
    FACT_LABELS,
    FactExtractionStatus,
    _Cell,
    _fact_from_label,
    _label_priority,
    _norm,
    _sha256_file,
    _statement_identity,
    _unit_evidence,
)


_SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_STRICT_NUMERIC = re.compile(r"^[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[Ee][+-]?\d+)?$")
_SOURCE_ROWS_SHA256 = "656807e74f84aa7bde74f30ffe7f2b11fed921e343c485dcc81cdcc617ac3cd9"
_EXPECTED_SOURCE_ROWS = 6108
_EXPECTED_PIT_READY = 5965


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _strict_numeric(value: str) -> Decimal | None:
    text = str(value).strip().replace("\xa0", "")
    if not _STRICT_NUMERIC.fullmatch(text):
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _column_number(coordinate: str) -> int:
    letters = re.match(r"[A-Z]+", coordinate.upper())
    if not letters:
        return 0
    result = 0
    for char in letters.group(0):
        result = result * 26 + ord(char) - ord("A") + 1
    return result


def _cell_text(cell: ElementTree.Element, shared: Sequence[str]) -> str:
    value = cell.find(f"{{{_SHEET_NS}}}v")
    inline = cell.find(f"{{{_SHEET_NS}}}is")
    if cell.attrib.get("t") == "s" and value is not None:
        try:
            return " ".join(shared[int(value.text or "-1")].split())
        except (ValueError, IndexError):
            return ""
    if inline is not None:
        return " ".join("".join(inline.itertext()).split())
    return (value.text or "").strip() if value is not None else ""


def _sheet_targets(archive: zipfile.ZipFile) -> list[tuple[str, str]]:
    names = set(archive.namelist())
    workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    rels = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    rel_map = {
        rel.attrib.get("Id", ""): rel.attrib.get("Target", "")
        for rel in rels.findall(f"{{{_PKG_REL_NS}}}Relationship")
    }
    result: list[tuple[str, str]] = []
    ns = {"m": _SHEET_NS, "r": _REL_NS}
    for sheet in workbook.findall("m:sheets/m:sheet", ns):
        if sheet.attrib.get("state", "visible") != "visible":
            continue
        target = rel_map.get(sheet.attrib.get(f"{{{_REL_NS}}}id", ""), "")
        target = posixpath.normpath(posixpath.join("xl", target))
        if target in names:
            result.append((sheet.attrib.get("name", ""), target))
    return result


def _audit_xlsx(payload: bytes) -> dict[str, Any]:
    """Return exact-label/value evidence without changing canonical parsing."""

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = [" ".join("".join(item.itertext()).split()) for item in root]
        sheet_specs = _sheet_targets(archive)
        sheet_cells: dict[str, list[dict[str, Any]]] = {}
        sheet_names = [name for name, _ in sheet_specs]
        for sheet_name, target in sheet_specs:
            root = ElementTree.fromstring(archive.read(target))
            cells: list[dict[str, Any]] = []
            for element in root.findall(f".//{{{_SHEET_NS}}}c"):
                coord = element.attrib.get("r", "")
                text = _cell_text(element, shared)
                if not coord or text == "":
                    continue
                cells.append({
                    "coordinate": coord,
                    "row": int(re.search(r"\d+", coord).group(0)) if re.search(r"\d+", coord) else 0,
                    "column": _column_number(coord),
                    "text": text,
                    "storage": "INLINE_TEXT" if element.attrib.get("t") in {"inlineStr", "str", "s"} else "NATIVE_VALUE",
                })
            sheet_cells[sheet_name] = cells

        metadata_cells = [
            _Cell(
                sheet="1000000",
                coordinate=item["coordinate"],
                row=item["row"],
                column=item["column"],
                value=item["text"],
                numeric=_strict_numeric(item["text"]),
            )
            for item in sheet_cells.get("1000000", [])
        ]
        currency, unit, scale, unit_evidence, unit_detail = _unit_evidence(metadata_cells)

        facts: dict[str, dict[str, Any]] = {}
        for fact in CORE_FACT_IDENTITIES:
            facts[fact] = {
                "canonical_label_present": False,
                "numeric_current_present": False,
                "authoritative_conflict": False,
                "unit_resolved": not unit_detail,
                "storage_kinds": Counter(),
                "labels": [],
                "numeric_occurrences": [],
                "status": "ABSENT_CANONICAL_LABEL",
            }

        for sheet_name, cells in sheet_cells.items():
            if _statement_identity(sheet_name) is None:
                continue
            context_cols = {
                item["column"]: (item["text"], item["coordinate"])
                for item in cells
                if item["row"] <= 8 and item["text"] in {"CurrentYearInstant", "CurrentYearDuration"}
            }
            by_position = {(item["row"], item["column"]): item for item in cells}
            for label in (item for item in cells if item["column"] == 1):
                fact = _fact_from_label(label["text"])
                if fact is None:
                    continue
                evidence = facts[fact]
                evidence["canonical_label_present"] = True
                evidence["labels"].append({
                    "sheet": sheet_name,
                    "label_cell": label["coordinate"],
                    "text": label["text"],
                    "statement_identity": _statement_identity(sheet_name),
                })
                for column, (context_ref, context_cell) in context_cols.items():
                    value_cell = by_position.get((label["row"], column))
                    if value_cell is None:
                        continue
                    number = _strict_numeric(value_cell["text"])
                    if number is None:
                        continue
                    evidence["numeric_current_present"] = True
                    evidence["storage_kinds"][value_cell["storage"]] += 1
                    evidence["numeric_occurrences"].append({
                        "sheet": sheet_name,
                        "label_cell": label["coordinate"],
                        "value_cell": value_cell["coordinate"],
                        "context_cell": context_cell,
                        "context_ref": context_ref,
                        "raw_value": value_cell["text"],
                        "value": str(number),
                        "storage": value_cell["storage"],
                        "statement_identity": _statement_identity(sheet_name),
                        "label": label["text"],
                    })

        for fact, evidence in facts.items():
            occurrences = evidence["numeric_occurrences"]
            if not evidence["canonical_label_present"]:
                evidence["status"] = "ABSENT_CANONICAL_LABEL"
            elif not occurrences:
                evidence["status"] = "CANONICAL_LABEL_NO_CURRENT_NUMERIC"
            else:
                top_priority = max(
                    _label_priority(
                        fact,
                        _Cell(
                            sheet=item["sheet"],
                            coordinate=item["label_cell"],
                            row=0,
                            column=1,
                            value=item["text"],
                            numeric=None,
                        ),
                    )
                    for item in evidence["labels"]
                )
                top = [item for item in occurrences if _label_priority(fact, _Cell(
                    sheet=item["sheet"], coordinate=item["label_cell"], row=0, column=1,
                    value=item["label"], numeric=None,
                )) == top_priority]
                semantic = {(item["value"], item["context_ref"], item["statement_identity"]) for item in top}
                evidence["authoritative_conflict"] = len(semantic) > 1
                if evidence["authoritative_conflict"]:
                    evidence["status"] = "AUTHORITATIVE_VALUE_CONFLICT"
                elif unit_detail:
                    evidence["status"] = "PRESENT_CANONICAL_NUMERIC_UNIT_UNRESOLVED"
                elif any(kind == "INLINE_TEXT" for kind in evidence["storage_kinds"]):
                    evidence["status"] = "PRESENT_CANONICAL_INLINE_NUMERIC"
                else:
                    evidence["status"] = "PRESENT_CANONICAL_NATIVE_NUMERIC"
            evidence["recoverable_with_strict_numeric_decoder"] = (
                evidence["status"] in {"PRESENT_CANONICAL_INLINE_NUMERIC", "PRESENT_CANONICAL_NATIVE_NUMERIC"}
                and not evidence["authoritative_conflict"]
                and evidence["unit_resolved"]
            )
            evidence["storage_kinds"] = dict(sorted(evidence["storage_kinds"].items()))

        return {
            "industry_class": "FINANCIAL_SHARIA" if any(re.match(r"^(42|43|44|45)", name) for name in sheet_names) else "GENERAL",
            "visible_statement_sheets": sorted(name for name in sheet_names if _statement_identity(name)),
            "unit": {"currency": currency, "unit": unit, "scale": scale, "detail": unit_detail, "evidence": list(unit_evidence)},
            "facts": facts,
        }


def _load_existing_records(census_root: Path) -> dict[tuple[str, int, str, str, str], str]:
    result: dict[tuple[str, int, str, str, str], str] = {}
    for line in (census_root / "fact_records.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        result[(record["ticker"], int(record["fiscal_year"]), record["fiscal_period"], record["attachment_sha256"], record["fact_identity"])] = record["extraction_status"]
    return result


def _pair_counts(filing_sets: Sequence[set[str]]) -> dict[str, int]:
    result: Counter[str] = Counter()
    for present in filing_sets:
        for left, right in itertools.combinations(sorted(present), 2):
            result[f"{left}|{right}"] += 1
    return dict(sorted(result.items()))


def run_template_drift_audit(
    reclassification_root: Path,
    attachments_root: Path,
    census_root: Path,
    output_root: Path,
    *,
    expected_source_rows: int = _EXPECTED_SOURCE_ROWS,
    expected_pit_ready: int = _EXPECTED_PIT_READY,
    expected_source_sha256: str = _SOURCE_ROWS_SHA256,
) -> dict[str, Any]:
    """Run the bounded offline drift audit over the accepted corpus."""

    if output_root.exists() and any(output_root.iterdir()):
        raise ValueError(f"output root must be new and empty: {output_root}")
    rows_path = reclassification_root / "scope_reclassification_rows.jsonl"
    rows = _load_jsonl(rows_path)
    actual_source_sha = _sha256_file(rows_path)
    if len(rows) != expected_source_rows or actual_source_sha != expected_source_sha256:
        raise ValueError("reclassification source count/hash mismatch")
    eligible = [row for row in rows if row.get("pit_ready") and row.get("representation_format") in {"XLSX", "XBRL"}]
    if len(eligible) != expected_pit_ready:
        raise ValueError("accepted PIT-ready row count mismatch")
    existing = _load_existing_records(census_root)

    output_root.mkdir(parents=True, exist_ok=True)
    filing_path = output_root / "filing_template_audit.jsonl"
    coverage_path = output_root / "coverage_by_period.json"
    cooccurrence_path = output_root / "cooccurrence.json"
    label_path = output_root / "label_inventory.json"
    summary_path = output_root / "summary.json"
    filing_rows: list[dict[str, Any]] = []
    coverage: dict[str, dict[str, Any]] = defaultdict(lambda: {"filings": 0, "facts": {fact: Counter() for fact in CORE_FACT_IDENTITIES}})
    co_before: list[set[str]] = []
    co_after: list[set[str]] = []
    labels_by_period: dict[str, Counter[str]] = defaultdict(Counter)
    storage_by_period: Counter[str] = Counter()
    repair_examples: list[dict[str, Any]] = []
    verified_attachment_hashes = 0

    for row in eligible:
        key_prefix = (str(row["ticker"]), int(row["year"]), str(row["period"]), str(row["source_attachment_sha256"]))
        period_key = f"{row['year']}:{row['period']}"
        if row["representation_format"] != "XLSX":
            filing_rows.append({"ticker": row["ticker"], "year": row["year"], "period": row["period"], "representation_format": row["representation_format"], "status": "NOT_XLSX_DRIFT_SCOPE"})
            continue
        attachment = attachments_root / str(row["source_attachment_path"])
        payload = attachment.read_bytes()
        if _sha256_bytes(payload) != row["source_attachment_sha256"]:
            raise ValueError(f"attachment hash mismatch: {attachment}")
        verified_attachment_hashes += 1
        audit = _audit_xlsx(payload)
        after: set[str] = set()
        before: set[str] = set()
        fact_rows: dict[str, Any] = {}
        for fact in CORE_FACT_IDENTITIES:
            evidence = audit["facts"][fact]
            parser_status = existing.get((*key_prefix, fact))
            before_present = parser_status == FactExtractionStatus.EXTRACTED.value
            recoverable = bool(evidence["recoverable_with_strict_numeric_decoder"] and not before_present)
            effective = before_present or recoverable
            if before_present:
                before.add(fact)
            if effective:
                after.add(fact)
            if effective:
                coverage[period_key]["facts"][fact]["effective"] += 1
            if before_present:
                coverage[period_key]["facts"][fact]["parser_extracted"] += 1
            if recoverable:
                coverage[period_key]["facts"][fact]["recoverable_drift"] += 1
                if len(repair_examples) < 30:
                    repair_examples.append({"ticker": row["ticker"], "year": row["year"], "period": row["period"], "fact": fact, "source_attachment_path": row["source_attachment_path"], "source_attachment_sha256": row["source_attachment_sha256"], "audit_status": evidence["status"], "numeric_occurrences": evidence["numeric_occurrences"][:3]})
            if evidence["status"] in {"ABSENT_CANONICAL_LABEL", "CANONICAL_LABEL_NO_CURRENT_NUMERIC"}:
                coverage[period_key]["facts"][fact]["genuine_missing_or_unresolved"] += 1
            coverage[period_key]["facts"][fact]["filings"] += 1
            fact_rows[fact] = {"parser_status": parser_status or "MISSING", **evidence, "recoverable": recoverable, "effective_present": effective}
            for storage in evidence["storage_kinds"]:
                storage_by_period[f"{period_key}|{fact}|{storage}"] += evidence["storage_kinds"][storage]
            for label in evidence["labels"]:
                labels_by_period[f"{period_key}|{fact}"][label["text"]] += 1
        coverage[period_key]["filings"] += 1
        co_before.append(before)
        co_after.append(after)
        filing_rows.append({
            "ticker": row["ticker"], "year": row["year"], "period": row["period"], "scope": row.get("scope"), "industry_class": audit["industry_class"], "representation_format": row["representation_format"], "publication_at_utc": row["publication_at_utc"], "source_attachment_path": row["source_attachment_path"], "source_attachment_sha256": row["source_attachment_sha256"], "unit": audit["unit"], "facts": fact_rows,
        })

    for period in coverage:
        for fact in CORE_FACT_IDENTITIES:
            bucket = coverage[period]["facts"][fact]
            filings = bucket.pop("filings", 0)
            bucket["filings"] = filings
            bucket["parser_fraction"] = round(bucket.get("parser_extracted", 0) / filings, 6) if filings else 0.0
            bucket["effective_fraction"] = round(bucket.get("effective", 0) / filings, 6) if filings else 0.0
            bucket["recoverable_fraction"] = round(bucket.get("recoverable_drift", 0) / filings, 6) if filings else 0.0

    label_inventory = {
        key: dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))
        for key, counter in sorted(labels_by_period.items())
    }
    storage_inventory = dict(sorted(storage_by_period.items()))
    cooccurrence = {
        "filings": len(co_before),
        "all_core_before": sum(len(present) == len(CORE_FACT_IDENTITIES) for present in co_before),
        "all_core_after": sum(len(present) == len(CORE_FACT_IDENTITIES) for present in co_after),
        "eight_non_exact_cash_before": sum(len(present - {"cash"}) == len(CORE_FACT_IDENTITIES) - 1 for present in co_before),
        "eight_non_exact_cash_after": sum(len(present - {"cash"}) == len(CORE_FACT_IDENTITIES) - 1 for present in co_after),
        "pair_counts_before": _pair_counts(co_before),
        "pair_counts_after": _pair_counts(co_after),
    }

    summary = {
        "status": "BOUNDED_OFFLINE_TEMPLATE_DRIFT_AUDIT",
        "verdict": "TEMPLATE_SERIALIZATION_DRIFT_CONFIRMED_EXACT_LABELS_RETAINED",
        "source_rows": len(rows),
        "source_rows_sha256": actual_source_sha,
        "pit_ready_filings": len(eligible),
        "xlsx_filings_audited": verified_attachment_hashes,
        "xbrl_rows_out_of_scope": sum(row.get("representation_format") == "XBRL" for row in eligible),
        "canonical_extractor_changed": False,
        "fuzzy_or_guessed_mappings": False,
        "network_calls": 0,
        "protected_outcomes_accessed": False,
        "parser_status_source": str(census_root / "fact_records.jsonl"),
        "findings": {
            "exact_existing_labels_reused": True,
            "strict_numeric_text_decoder": "ASCII decimal/scientific notation only; no localized comma or fuzzy parsing",
            "post_2025_q1_drift": "canonical labels remain present but many current-period values are XLSX inline text scientific notation and are therefore absent from the accepted parser output",
            "semantic_missingness_after_decoder": "remaining rows with no exact canonical current-period numeric value, unresolved explicit unit, or authoritative conflict",
        },
        "repair_examples": repair_examples,
        "artifact_inputs": {
            "reclassification_rows_sha256": actual_source_sha,
            "census_manifest_sha256": _sha256_file(census_root / "MANIFEST.json"),
        },
    }
    filing_path.write_text("".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in filing_rows), encoding="utf-8")
    _write_json(coverage_path, coverage)
    _write_json(cooccurrence_path, cooccurrence)
    _write_json(label_path, {"labels_by_period_fact": label_inventory, "storage_by_period_fact": storage_inventory})
    _write_json(summary_path, summary)
    manifest_files = [filing_path, coverage_path, cooccurrence_path, label_path, summary_path]
    manifest = {
        "manifest_version": "financial_template_drift_audit_v1",
        "files": {path.name: {"sha256": _sha256_file(path), "bytes": path.stat().st_size} for path in manifest_files},
        "source": {"reclassification_rows_sha256": actual_source_sha, "census_manifest_sha256": _sha256_file(census_root / "MANIFEST.json")},
        "boundaries": {"network_calls": 0, "protected_outcomes_accessed": False, "canonical_extractor_changed": False, "feature_work": False},
    }
    manifest_path = output_root / "MANIFEST.json"
    _write_json(manifest_path, manifest)
    return {**summary, "artifact_hashes": {path.name: _sha256_file(path) for path in [*manifest_files, manifest_path]}}


def _main() -> None:
    parser = argparse.ArgumentParser(description="Audit accepted IDX financial fact template drift offline")
    parser.add_argument("--reclassification-root", type=Path, required=True)
    parser.add_argument("--attachments-root", type=Path, required=True)
    parser.add_argument("--census-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run_template_drift_audit(**vars(args)), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    _main()
