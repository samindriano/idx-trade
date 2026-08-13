"""Bounded, version-aware extraction of canonical IDX financial facts.

This module is intentionally a feasibility layer, not a market-wide loader.  It
extracts only facts whose label/concept, period context, unit and source
location are explicit in an already accepted filing attachment.  Ambiguity is
represented as a non-extracted diagnostic; no value is silently guessed.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import posixpath
import re
import zipfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from xml.etree import ElementTree

from .financial_scope_resolver import ScopeResolution, _xml_text


class FactExtractionStatus(StrEnum):
    EXTRACTED = "EXTRACTED"
    UNRESOLVED_LABEL = "UNRESOLVED_LABEL"
    UNRESOLVED_PERIOD = "UNRESOLVED_PERIOD"
    UNRESOLVED_UNIT = "UNRESOLVED_UNIT"
    CONFLICTING_FACTS = "CONFLICTING_FACTS"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    NOT_APPLICABLE = "NOT_APPLICABLE"


FACT_LABELS: dict[str, tuple[str, ...]] = {
    "revenue": (
        "penjualan dan pendapatan usaha",
        "sales and revenue",
    ),
    "net_income": (
        "jumlah laba (rugi)",
        "profit (loss)",
        "profit or loss",
    ),
    "net_income_attributable": (
        "laba (rugi) yang dapat diatribusikan ke entitas induk",
        "laba (rugi) yang dapat diatribusikan kepada pemilik entitas induk",
        "profit (loss) attributable to parent entity",
    ),
    "total_assets": ("jumlah aset", "total assets"),
    "total_liabilities": ("jumlah liabilitas", "total liabilities"),
    "total_equity": ("jumlah ekuitas", "total equity"),
    "cash_and_cash_equivalents": (
        "kas dan setara kas",
        "cash and cash equivalents",
    ),
    "cash": ("kas", "cash"),
    "operating_cash_flow": (
        "jumlah arus kas bersih yang diperoleh dari (digunakan untuk) aktivitas operasi",
        "arus kas neto diperoleh dari aktivitas operasi",
        "kas diperoleh dari (digunakan untuk) operasi",
        "net cash flows received from (used in) operating activities",
    ),
}

XBRL_FACTS: dict[str, str] = {
    "idx-cor:SalesAndRevenue": "revenue",
    "idx-cor:ProfitLoss": "net_income",
    "idx-cor:ProfitLossAttributableToParentEntity": "net_income_attributable",
    "idx-cor:Assets": "total_assets",
    "idx-cor:Liabilities": "total_liabilities",
    "idx-cor:Equity": "total_equity",
    "idx-cor:CashAndCashEquivalents": "cash_and_cash_equivalents",
    "idx-cor:NetCashFlowsReceivedFromUsedInOperatingActivities": "operating_cash_flow",
}

_NUMERIC = re.compile(r"^[+-]?(?:\d+(?:[.,]\d+)?|[.,]\d+)$")
_SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def _norm(value: str) -> str:
    return " ".join(str(value).replace("\xa0", " ").split()).strip().casefold()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"not JSON serializable: {type(value)!r}")


def _parse_decimal(value: str) -> Decimal | None:
    text = str(value).strip().replace("\xa0", "")
    if not text or text in {"-", "—", "–"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    text = text.replace(",", "")
    if not _NUMERIC.fullmatch(text):
        return None
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None
    return -number if negative else number


@dataclass(frozen=True)
class FinancialFactRecord:
    ticker: str
    fiscal_year: int
    fiscal_period: str
    statement_scope: str
    publication_at_utc: str
    knowledge_at_utc: str
    attachment_sha256: str
    source_ref: str
    representation_format: str
    statement_identity: str
    fact_identity: str
    value: str | None
    currency: str | None
    unit: str | None
    scale: int | None
    fiscal_period_covered: Mapping[str, Any]
    source_location: str
    evidence_kind: str
    raw_label: str | None
    taxonomy: str | None
    taxonomy_version: str | None
    version_id: str
    extraction_status: FactExtractionStatus
    detail: str = ""
    parser_version: str = "financial_fact_table_v1"

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["extraction_status"] = self.extraction_status.value
        return result


@dataclass(frozen=True)
class FilingFactDiagnostics:
    ticker: str
    fiscal_year: int
    fiscal_period: str
    representation_format: str
    industry_class: str
    attachment_sha256: str
    statement_count: int
    candidate_count: int
    extracted_count: int
    status_counts: Mapping[str, int]
    missing_facts: tuple[str, ...]
    unit_evidence: tuple[Mapping[str, Any], ...]
    taxonomy: str | None
    taxonomy_version: str | None
    version_id: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VersionedFactStore:
    """An append-only fact collection; versions are never overwritten."""

    records: tuple[FinancialFactRecord, ...] = ()

    def append(self, *records: FinancialFactRecord) -> "VersionedFactStore":
        existing = list(self.records)
        for candidate in records:
            for prior in existing:
                same_observation = (
                    prior.ticker,
                    prior.fiscal_year,
                    prior.fiscal_period,
                    prior.statement_scope,
                    prior.statement_identity,
                    prior.fact_identity,
                    prior.knowledge_at_utc,
                ) == (
                    candidate.ticker,
                    candidate.fiscal_year,
                    candidate.fiscal_period,
                    candidate.statement_scope,
                    candidate.statement_identity,
                    candidate.fact_identity,
                    candidate.knowledge_at_utc,
                )
                if same_observation and prior.attachment_sha256 != candidate.attachment_sha256:
                    raise ValueError("conflicting attachment hashes for same logical fact and knowledge time")
            existing.append(candidate)
        return VersionedFactStore(records=self.records + tuple(records))

    def versions(self, logical_key: tuple[Any, ...]) -> tuple[FinancialFactRecord, ...]:
        return tuple(
            record
            for record in self.records
            if (
                record.ticker,
                record.fiscal_year,
                record.fiscal_period,
                record.statement_scope,
                record.statement_identity,
                record.fact_identity,
            )
            == logical_key
        )


@dataclass(frozen=True)
class _Cell:
    sheet: str
    coordinate: str
    row: int
    column: int
    value: str
    numeric: Decimal | None


def _column_number(coordinate: str) -> int:
    letters = re.match(r"[A-Z]+", coordinate.upper())
    if not letters:
        return 0
    result = 0
    for char in letters.group(0):
        result = result * 26 + ord(char) - ord("A") + 1
    return result


def _cell_value(cell: ElementTree.Element, shared: Sequence[str]) -> tuple[str, Decimal | None]:
    value_node = cell.find(f"{{{_SHEET_NS}}}v")
    inline_node = cell.find(f"{{{_SHEET_NS}}}is")
    if value_node is None and inline_node is None:
        return "", None
    if cell.attrib.get("t") == "s" and value_node is not None:
        try:
            value = shared[int(value_node.text or "-1")]
        except (ValueError, IndexError):
            value = ""
        return " ".join(value.split()), None
    if inline_node is not None:
        return " ".join(_xml_text(inline_node).split()), None
    value = (value_node.text or "").strip()
    return value, _parse_decimal(value)


def _visible_xlsx_cells(payload: bytes) -> tuple[list[_Cell], str]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = set(archive.namelist())
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        rels = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_map: dict[str, str] = {}
        for rel in rels:
            rid = rel.attrib.get("Id")
            target = rel.attrib.get("Target", "")
            if rid:
                rel_map[rid] = target
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = [" ".join(_xml_text(item).split()) for item in root]
        ns = {"m": _SHEET_NS, "r": _REL_NS}
        cells: list[_Cell] = []
        sheet_kinds: list[str] = []
        for sheet in workbook.findall("m:sheets/m:sheet", ns):
            if sheet.attrib.get("state", "visible") != "visible":
                continue
            target = rel_map.get(sheet.attrib.get(f"{{{_REL_NS}}}id", ""), "")
            target = posixpath.normpath(posixpath.join("xl", target))
            if target not in names:
                continue
            name = sheet.attrib.get("name", "")
            if name:
                sheet_kinds.append(name)
            root = ElementTree.fromstring(archive.read(target))
            for cell in root.findall(".//m:c", ns):
                value, numeric = _cell_value(cell, shared)
                if value == "" and numeric is None:
                    continue
                coordinate = cell.attrib.get("r", "")
                row_match = re.search(r"\d+", coordinate)
                row = int(row_match.group(0)) if row_match else 0
                cells.append(
                    _Cell(
                        sheet=name,
                        coordinate=coordinate,
                        row=row,
                        column=_column_number(coordinate),
                        value=value,
                        numeric=numeric,
                    )
                )
        industry = "FINANCIAL_SHARIA" if any(re.match(r"^(42|43|44|45)", x) for x in sheet_kinds) else "GENERAL"
        return cells, industry


def _statement_identity(sheet: str) -> str | None:
    if re.match(r"^12", sheet):
        return "statement_of_financial_position"
    if re.match(r"^13", sheet):
        return "income_statement"
    if re.match(r"^14", sheet):
        return "statement_of_changes_in_equity"
    if re.match(r"^15", sheet):
        return "cash_flow_statement"
    if re.match(r"^42", sheet):
        return "statement_of_financial_position"
    if re.match(r"^43", sheet):
        return "income_statement"
    if re.match(r"^44", sheet):
        return "statement_of_changes_in_equity"
    if re.match(r"^45", sheet):
        return "cash_flow_statement"
    return None


def _unit_evidence(cells: Sequence[_Cell]) -> tuple[str | None, str | None, int | None, tuple[Mapping[str, Any], ...], str]:
    evidence: list[dict[str, Any]] = []
    for cell in cells:
        text = _norm(cell.value)
        currency: str | None = None
        if "rupiah / idr" in text or text in {"idr", "rupiah"}:
            currency = "IDR"
        elif "dolar amerika serikat" in text or "us dollar" in text or text in {"usd", "as$"}:
            currency = "USD"
        if currency is None:
            continue
        if cell.sheet != "1000000" and cell.row > 12:
            continue
        scale = 1
        if "jutaan" in text or "millions" in text or "million" in text:
            scale = 1_000_000
        elif "ribuan" in text or "thousands" in text:
            scale = 1_000
        evidence.append({"location": f"sheet={cell.sheet};cell={cell.coordinate}", "text": cell.value, "currency": currency, "scale": scale})
    currencies = {item["currency"] for item in evidence}
    scales = {item["scale"] for item in evidence}
    if len(currencies) > 1 or len(scales) > 1:
        return None, None, None, tuple(evidence), "conflicting explicit presentation currency or scale"
    if not evidence:
        return None, None, None, (), "no explicit presentation currency/unit evidence"
    currency = next(iter(currencies))
    scale = next(iter(scales))
    return currency, currency, scale, tuple(evidence), ""


def _context_columns(cells: Sequence[_Cell], sheet: str) -> dict[int, tuple[str, str]]:
    result: dict[int, tuple[str, str]] = {}
    for cell in cells:
        if cell.sheet != sheet or cell.row > 8:
            continue
        if cell.value in {"CurrentYearInstant", "CurrentYearDuration"}:
            result[cell.column] = (cell.value, cell.coordinate)
    return result


def _fact_from_label(value: str) -> str | None:
    text = _norm(value)
    for fact, labels in FACT_LABELS.items():
        if text in {_norm(label) for label in labels}:
            return fact
    return None


def _period_covered(year: int, period: str, context_ref: str) -> dict[str, Any]:
    return {
        "report_year": year,
        "report_period": period,
        "context_ref": context_ref,
        "period_kind": "instant" if context_ref.endswith("Instant") else "duration",
        "period_start": None,
        "period_end": None,
    }


def _version_id(ticker: str, year: int, period: str, publication: str, sha: str) -> str:
    material = f"{ticker}|{year}|{period}|{publication}|{sha}".encode()
    return hashlib.sha256(material).hexdigest()


def _base_record_kwargs(*, ticker: str, year: int, period: str, scope: str, publication: str, sha: str, source_ref: str, fmt: str) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "fiscal_year": year,
        "fiscal_period": period,
        "statement_scope": scope,
        "publication_at_utc": publication,
        "knowledge_at_utc": publication,
        "attachment_sha256": sha,
        "source_ref": source_ref,
        "representation_format": fmt,
        "version_id": _version_id(ticker, year, period, publication, sha),
    }


def _xlsx_extract(
    payload: bytes,
    *,
    ticker: str,
    year: int,
    period: str,
    scope: str,
    publication: str,
    source_ref: str,
) -> tuple[list[FinancialFactRecord], FilingFactDiagnostics]:
    sha = _sha256_bytes(payload)
    cells, industry = _visible_xlsx_cells(payload)
    currency, unit, scale, units, unit_detail = _unit_evidence(cells)
    base = _base_record_kwargs(ticker=ticker, year=year, period=period, scope=scope, publication=publication, sha=sha, source_ref=source_ref, fmt="XLSX")
    records: list[FinancialFactRecord] = []
    statuses: Counter[str] = Counter()
    found: set[str] = set()
    statement_sheets = sorted({cell.sheet for cell in cells if _statement_identity(cell.sheet)})
    for sheet in statement_sheets:
        statement = _statement_identity(sheet)
        if statement is None:
            continue
        contexts = _context_columns(cells, sheet)
        current = {column: context for column, context in contexts.items() if context[0].startswith("CurrentYear")}
        labels = [cell for cell in cells if cell.sheet == sheet and cell.column == 1 and _fact_from_label(cell.value)]
        by_fact: dict[str, list[tuple[_Cell, _Cell, str]]] = defaultdict(list)
        for label in labels:
            fact = _fact_from_label(label.value)
            if fact is None:
                continue
            for column, (context_ref, context_coord) in current.items():
                value_cell = next((x for x in cells if x.sheet == sheet and x.row == label.row and x.column == column and x.numeric is not None), None)
                if value_cell is not None:
                    by_fact[fact].append((label, value_cell, context_ref))
        for fact, matches in by_fact.items():
            found.add(fact)
            values = {str(item[1].numeric) for item in matches}
            status = FactExtractionStatus.EXTRACTED
            detail = ""
            if len(values) > 1:
                status = FactExtractionStatus.CONFLICTING_FACTS
                detail = "multiple explicit current-period values for one canonical fact"
            elif unit_detail:
                status = FactExtractionStatus.UNRESOLVED_UNIT
                detail = unit_detail
            label, value_cell, context_ref = matches[0]
            record = FinancialFactRecord(
                **base,
                statement_identity=statement,
                fact_identity=fact,
                value=str(value_cell.numeric) if value_cell.numeric is not None else None,
                currency=currency,
                unit=unit,
                scale=scale,
                fiscal_period_covered=_period_covered(year, period, context_ref),
                source_location=f"sheet={sheet};label_cell={label.coordinate};value_cell={value_cell.coordinate};context_cell={next((c[1] for c in contexts.values() if c[0] == context_ref), 'UNRESOLVED')}",
                evidence_kind="xlsx_visible_label_current_period",
                raw_label=label.value,
                taxonomy=industry,
                taxonomy_version="IDX_XLSX_TEMPLATE_UNVERSIONED",
                extraction_status=status,
                detail=detail,
            )
            records.append(record)
            statuses[status.value] += 1
    missing = tuple(sorted(set(FACT_LABELS) - found))
    diagnostics = FilingFactDiagnostics(
        ticker=ticker,
        fiscal_year=year,
        fiscal_period=period,
        representation_format="XLSX",
        industry_class=industry,
        attachment_sha256=sha,
        statement_count=len(statement_sheets),
        candidate_count=len(records),
        extracted_count=sum(1 for record in records if record.extraction_status is FactExtractionStatus.EXTRACTED),
        status_counts=dict(sorted(statuses.items())),
        missing_facts=missing,
        unit_evidence=units,
        taxonomy=industry,
        taxonomy_version="IDX_XLSX_TEMPLATE_UNVERSIONED",
        version_id=base["version_id"],
        detail=unit_detail,
    )
    return records, diagnostics


_XBRL_OPEN = re.compile(r"<ix:nonFraction\b(?P<attrs>[^>]*)>(?P<body>.*?)</ix:nonFraction\s*>", re.I | re.S)
_ATTR = re.compile(r"(?P<key>[A-Za-z_:][\w:.-]*)\s*=\s*(?P<q>[\"'])(?P<value>.*?)(?P=q)", re.S)
_ALLOWED_CONTEXTS = {"CurrentYearInstant", "CurrentYearDuration"}


def _attrs(text: str) -> dict[str, str]:
    return {match.group("key"): match.group("value") for match in _ATTR.finditer(text)}


def _xbrl_extract(
    payload: bytes,
    *,
    ticker: str,
    year: int,
    period: str,
    scope: str,
    publication: str,
    source_ref: str,
) -> tuple[list[FinancialFactRecord], FilingFactDiagnostics]:
    sha = _sha256_bytes(payload)
    base = _base_record_kwargs(ticker=ticker, year=year, period=period, scope=scope, publication=publication, sha=sha, source_ref=source_ref, fmt="XBRL")
    records: list[FinancialFactRecord] = []
    statuses: Counter[str] = Counter()
    found: set[str] = set()
    evidence_units: list[Mapping[str, Any]] = []
    taxonomy_version: str | None = None
    values_by_fact: dict[str, list[tuple[Decimal, str, dict[str, str], str, str]]] = defaultdict(list)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for member in archive.namelist():
            if not member.lower().endswith((".html", ".xhtml", ".xml")):
                continue
            text = archive.read(member).decode("utf-8", "ignore")
            if taxonomy_version is None:
                schema = re.search(r"schemaRef[^>]+href\s*=\s*['\"]([^'\"]+)", text, re.I)
                taxonomy_version = schema.group(1) if schema else "UNRESOLVED_SCHEMA_REF"
            for ordinal, match in enumerate(_XBRL_OPEN.finditer(text)):
                attr = _attrs(match.group("attrs"))
                name = attr.get("name", "")
                fact = XBRL_FACTS.get(name)
                if fact is None:
                    continue
                context = attr.get("contextRef", "")
                raw_body = re.sub(r"<[^>]+>", " ", match.group("body"))
                raw_body = " ".join(raw_body.split())
                number = _parse_decimal(raw_body)
                if attr.get("sign") == "-" and number is not None:
                    number = -number
                unit = attr.get("unitRef")
                try:
                    parsed_scale = int(attr.get("scale", ""))
                except ValueError:
                    parsed_scale = None
                location = f"member={member};element_index={ordinal};name={name};context={context}"
                if context not in _ALLOWED_CONTEXTS or number is None or not unit or parsed_scale is None:
                    status = FactExtractionStatus.UNRESOLVED_PERIOD if context not in _ALLOWED_CONTEXTS else FactExtractionStatus.UNRESOLVED_UNIT
                    records.append(FinancialFactRecord(
                        **base,
                        statement_identity="cash_flow_statement" if fact == "operating_cash_flow" else ("statement_of_financial_position" if context.endswith("Instant") else "income_statement"),
                        fact_identity=fact,
                        value=str(number) if number is not None else None,
                        currency=unit,
                        unit=unit,
                        scale=parsed_scale,
                        fiscal_period_covered=_period_covered(year, period, context or "UNRESOLVED"),
                        source_location=location,
                        evidence_kind="ixbrl_numeric_concept",
                        raw_label=name,
                        taxonomy="IDX_COR",
                        taxonomy_version=taxonomy_version,
                        extraction_status=status,
                        detail="explicit concept lacks valid context, numeric value, unitRef or scale",
                    ))
                    statuses[status.value] += 1
                    continue
                values_by_fact[fact].append((number, location, attr, unit, context))
                evidence_units.append({"location": location, "unit": unit, "scale": parsed_scale, "context": context})
    for fact, matches in values_by_fact.items():
        found.add(fact)
        value_set = {str(item[0]) for item in matches}
        status = FactExtractionStatus.EXTRACTED if len(value_set) == 1 else FactExtractionStatus.CONFLICTING_FACTS
        detail = "" if status is FactExtractionStatus.EXTRACTED else "conflicting authoritative numeric facts"
        number, location, attr, unit, context = matches[0]
        scale = int(attr["scale"])
        records.append(FinancialFactRecord(
            **base,
            statement_identity="cash_flow_statement" if fact == "operating_cash_flow" else ("statement_of_financial_position" if context.endswith("Instant") else "income_statement"),
            fact_identity=fact,
            value=str(number),
            currency=unit,
            unit=unit,
            scale=scale,
            fiscal_period_covered=_period_covered(year, period, context),
            source_location=location,
            evidence_kind="ixbrl_numeric_concept",
            raw_label=attr.get("name"),
            taxonomy="IDX_COR",
            taxonomy_version=taxonomy_version,
            extraction_status=status,
            detail=detail,
        ))
        statuses[status.value] += 1
    diagnostics = FilingFactDiagnostics(
        ticker=ticker,
        fiscal_year=year,
        fiscal_period=period,
        representation_format="XBRL",
        industry_class="UNKNOWN_UNLESS_EXPLICIT_IN_TAXONOMY",
        attachment_sha256=sha,
        statement_count=len({record.statement_identity for record in records}),
        candidate_count=len(records),
        extracted_count=sum(1 for record in records if record.extraction_status is FactExtractionStatus.EXTRACTED),
        status_counts=dict(sorted(statuses.items())),
        missing_facts=tuple(sorted(set(FACT_LABELS) - found)),
        unit_evidence=tuple(evidence_units),
        taxonomy="IDX_COR",
        taxonomy_version=taxonomy_version,
        version_id=base["version_id"],
        detail="",
    )
    return records, diagnostics


def extract_filing_facts(
    payload: bytes,
    *,
    ticker: str,
    fiscal_year: int,
    fiscal_period: str,
    statement_scope: str,
    publication_at_utc: str,
    source_ref: str,
    representation_format: str,
) -> tuple[list[FinancialFactRecord], FilingFactDiagnostics]:
    """Extract one accepted attachment without network access or mutation."""

    if representation_format == "XLSX":
        return _xlsx_extract(payload, ticker=ticker, year=fiscal_year, period=fiscal_period, scope=statement_scope, publication=publication_at_utc, source_ref=source_ref)
    if representation_format == "XBRL":
        return _xbrl_extract(payload, ticker=ticker, year=fiscal_year, period=fiscal_period, scope=statement_scope, publication=publication_at_utc, source_ref=source_ref)
    sha = _sha256_bytes(payload)
    diagnostic = FilingFactDiagnostics(
        ticker=ticker,
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period,
        representation_format=representation_format,
        industry_class="UNKNOWN",
        attachment_sha256=sha,
        statement_count=0,
        candidate_count=0,
        extracted_count=0,
        status_counts={FactExtractionStatus.UNSUPPORTED_FORMAT.value: 1},
        missing_facts=tuple(sorted(FACT_LABELS)),
        unit_evidence=(),
        taxonomy=None,
        taxonomy_version=None,
        version_id=_version_id(ticker, fiscal_year, fiscal_period, publication_at_utc, sha),
        detail="format is outside the bounded XLSX/XBRL feasibility scope",
    )
    return [], diagnostic


def select_representative_sample(rows: Sequence[Mapping[str, Any]], target: int = 36) -> list[Mapping[str, Any]]:
    """Choose a deterministic, coverage-oriented subset without refetching."""

    eligible = [row for row in rows if row.get("pit_ready") and row.get("representation_format") in {"XLSX", "XBRL"}]
    financial = {"BBCA", "BMRI", "BBNI", "BBRI", "BTPS", "TUGU", "PNBN", "BJBR", "BBTN", "BRIS"}
    preferred = sorted(
        eligible,
        key=lambda row: (
            0 if row.get("representation_format") == "XBRL" else 1,
            0 if row.get("ticker") in financial else 1,
            int(row.get("year", 0)),
            str(row.get("period", "")),
            str(row.get("ticker", "")),
        ),
    )
    selected: list[Mapping[str, Any]] = []
    covered: set[tuple[str, str, int, str, bool]] = set()
    periods = {"audit", "tw1", "tw2", "tw3"}
    for row in preferred:
        key = (str(row.get("representation_format")), str(row.get("scope")), int(row.get("year")), str(row.get("period")), row.get("ticker") in financial)
        if row.get("representation_format") == "XBRL" or key not in covered:
            selected.append(row)
            covered.add(key)
        if len(selected) >= target:
            break
    if len(selected) < target:
        for row in preferred:
            if row not in selected:
                selected.append(row)
            if len(selected) >= target:
                break
    return selected


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")


def run_sample_audit(reclassification_root: Path, attachments_root: Path, output_root: Path, target: int = 36) -> dict[str, Any]:
    """Run the bounded offline sample and persist hashes/manifests externally."""

    rows = _load_jsonl(reclassification_root / "scope_reclassification_rows.jsonl")
    sample = select_representative_sample(rows, target=target)
    output_root.mkdir(parents=True, exist_ok=True)
    fact_path = output_root / "fact_records.jsonl"
    diag_path = output_root / "filing_diagnostics.jsonl"
    selected_path = output_root / "sample_selection.json"
    facts: list[FinancialFactRecord] = []
    diagnostics: list[FilingFactDiagnostics] = []
    selection: list[dict[str, Any]] = []
    for row in sample:
        attachment = attachments_root / str(row["source_attachment_path"])
        payload = attachment.read_bytes()
        actual_sha = _sha256_bytes(payload)
        if actual_sha != row["source_attachment_sha256"]:
            raise ValueError(f"attachment hash mismatch: {attachment}")
        records, diagnostic = extract_filing_facts(
            payload,
            ticker=str(row["ticker"]),
            fiscal_year=int(row["year"]),
            fiscal_period=str(row["period"]),
            statement_scope=str(row["scope"]),
            publication_at_utc=str(row["publication_at_utc"]),
            source_ref=str((row.get("source_refs") or [""])[0]),
            representation_format=str(row["representation_format"]),
        )
        facts.extend(records)
        diagnostics.append(diagnostic)
        selection.append({
            "ticker": row["ticker"], "year": row["year"], "period": row["period"],
            "scope": row["scope"], "representation_format": row["representation_format"],
            "publication_at_utc": row["publication_at_utc"],
            "source_attachment_sha256": row["source_attachment_sha256"],
            "source_attachment_path": row["source_attachment_path"],
            "source_refs": row.get("source_refs", []),
            "scope_evidence": row.get("evidence", []),
            "industry_class": diagnostic.industry_class,
        })
    fact_path.write_text("".join(json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True, default=_json_default) + "\n" for record in facts), encoding="utf-8")
    diag_path.write_text("".join(json.dumps(item.to_dict(), ensure_ascii=False, sort_keys=True, default=_json_default) + "\n" for item in diagnostics), encoding="utf-8")
    _write_json(selected_path, selection)
    counts = Counter(record.extraction_status.value for record in facts)
    format_counts = Counter(item.representation_format for item in diagnostics)
    fact_status_by_identity: dict[str, Counter[str]] = defaultdict(Counter)
    fact_unit_scales: Counter[str] = Counter()
    for record in facts:
        fact_status_by_identity[record.fact_identity][record.extraction_status.value] += 1
        if record.currency is not None and record.scale is not None:
            fact_unit_scales[f"{record.currency}*{record.scale}"] += 1
    missing_fact_counts = Counter(fact for item in diagnostics for fact in item.missing_facts)
    period_counts = Counter(f"{item.fiscal_year}:{item.fiscal_period}" for item in diagnostics)
    summary = {
        "status": "BOUNDED_OFFLINE_FACT_EXTRACTION_FEASIBILITY",
        "sample_filings": len(sample),
        "fact_candidates": len(facts),
        "fact_status_counts": dict(sorted(counts.items())),
        "extracted_facts": counts[FactExtractionStatus.EXTRACTED.value],
        "extracted_fraction_of_candidates": round(counts[FactExtractionStatus.EXTRACTED.value] / len(facts), 6) if facts else 0.0,
        "fact_status_by_identity": {fact: dict(sorted(statuses.items())) for fact, statuses in sorted(fact_status_by_identity.items())},
        "unit_scale_distribution": dict(sorted(fact_unit_scales.items())),
        "missing_fact_counts": dict(sorted(missing_fact_counts.items())),
        "filings_by_format": dict(sorted(format_counts.items())),
        "filings_by_scope": dict(sorted(Counter(row.get("scope") for row in sample).items())),
        "filings_by_industry": dict(sorted(Counter(item.industry_class for item in diagnostics).items())),
        "filings_by_year_period": dict(sorted(period_counts.items())),
        "diagnostic_status_counts": dict(sorted(Counter(status for item in diagnostics for status, count in item.status_counts.items() for _ in range(count)).items())),
        "source_artifact_sha256": {
            "reclassification_rows": _sha256_file(reclassification_root / "scope_reclassification_rows.jsonl"),
        },
        "version_semantics": {
            "version_id": "sha256(ticker|year|period|publication_at_utc|attachment_sha256)",
            "storage": "append-only; no overwrite",
            "history_finding": "accepted census contains one selected attachment/version per logical period; correction history is not complete evidence",
        },
        "market_wide_fact_table_verdict": "NOT_YET_DEFENSIBLE",
        "market_wide_blockers": [
            "bounded sample only; no market-wide extraction was run",
            "accepted census does not preserve a complete correction/restatement version history",
            "XLSX templates have taxonomy/label and unit-scale conflicts in representative filings",
            "XBRL taxonomy/schema version and period-context coverage require a broader bounded audit",
        ],
    }
    summary_path = output_root / "summary.json"
    _write_json(summary_path, summary)
    manifest_files = [selected_path, fact_path, diag_path, summary_path]
    manifest = {
        "manifest_version": "financial_fact_table_v1",
        "files": {path.name: {"sha256": _sha256_file(path), "bytes": path.stat().st_size} for path in manifest_files},
        "source": {
            "reclassification_root": str(reclassification_root),
            "reclassification_rows_sha256": _sha256_file(reclassification_root / "scope_reclassification_rows.jsonl"),
        },
    }
    manifest_path = output_root / "MANIFEST.json"
    _write_json(manifest_path, manifest)
    summary["artifact_hashes"] = {path.name: _sha256_file(path) for path in [selected_path, fact_path, diag_path, summary_path, manifest_path]}
    _write_json(summary_path, summary)
    manifest["files"][summary_path.name] = {"sha256": _sha256_file(summary_path), "bytes": summary_path.stat().st_size}
    _write_json(manifest_path, manifest)
    return summary | {"artifact_hashes": {path.name: _sha256_file(path) for path in [selected_path, fact_path, diag_path, summary_path, manifest_path]}}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample", choices=["sample"])
    parser.add_argument("--reclassification-root", type=Path, required=True)
    parser.add_argument("--attachments-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--target", type=int, default=36)
    args = parser.parse_args()
    print(json.dumps(run_sample_audit(args.reclassification_root, args.attachments_root, args.output_root, args.target), indent=2, sort_keys=True))


if __name__ == "__main__":
    _main()
