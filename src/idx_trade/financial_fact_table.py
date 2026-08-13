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
    UNRESOLVED_TAXONOMY = "UNRESOLVED_TAXONOMY"
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
    """Read only the presentation metadata block on the visible template sheet.

    Statement-body labels such as ``IDR`` or ``AS$`` are not presentation
    semantics.  In particular, a breakdown row may legitimately use a
    different currency from the filing's reporting unit.  The IDX templates
    expose the authoritative pair in the rows labelled ``Mata uang
    pelaporan`` and ``Pembulatan yang digunakan``.
    """

    metadata = [cell for cell in cells if cell.sheet == "1000000"]
    currency_labels = {"mata uang pelaporan", "reporting currency"}
    scale_labels = {"pembulatan yang digunakan", "rounding used"}
    currency_label = next((cell for cell in metadata if any(token in _norm(cell.value) for token in currency_labels)), None)
    scale_label = next((cell for cell in metadata if any(token in _norm(cell.value) for token in scale_labels)), None)

    evidence: list[dict[str, Any]] = []

    def value_after(label: _Cell | None) -> _Cell | None:
        if label is None:
            return None
        candidates = [cell for cell in metadata if cell.row == label.row and cell.column > label.column and cell.value.strip()]
        return min(candidates, key=lambda cell: cell.column, default=None)

    currency_cell = value_after(currency_label)
    scale_cell = value_after(scale_label)
    currency_text = _norm(currency_cell.value) if currency_cell is not None else ""
    scale_text = _norm(scale_cell.value) if scale_cell is not None else ""

    currency: str | None = None
    if currency_text in {
        "rupiah / idr", "rupiah/idr", "idr", "rupiah",
        "dollar amerika / usd", "dolar amerika / usd",
        "dollar amerika serikat / usd", "dolar amerika serikat / usd",
        "usd", "us dollar",
    }:
        currency = "USD" if "usd" in currency_text or "dollar" in currency_text or "dolar" in currency_text else "IDR"
    scale: int | None = None
    if scale_text in {"satuan penuh / full amount", "satuan penuh", "full amount", "full amounts"}:
        scale = 1
    elif "jutaan" in scale_text or "million" in scale_text:
        scale = 1_000_000
    elif "ribuan" in scale_text or "thousand" in scale_text:
        scale = 1_000

    if currency_cell is not None:
        evidence.append({"location": f"sheet=1000000;cell={currency_cell.coordinate}", "label_location": f"sheet=1000000;cell={currency_label.coordinate if currency_label else 'UNRESOLVED'}", "text": currency_cell.value, "currency": currency})
    if scale_cell is not None:
        evidence.append({"location": f"sheet=1000000;cell={scale_cell.coordinate}", "label_location": f"sheet=1000000;cell={scale_label.coordinate if scale_label else 'UNRESOLVED'}", "text": scale_cell.value, "scale": scale})

    if currency is None or scale is None:
        return None, None, None, tuple(evidence), "missing or unrecognized explicit presentation currency/unit or scale metadata"
    currencies = {currency}
    scales = {scale}
    if len(currencies) > 1 or len(scales) > 1:
        return None, None, None, tuple(evidence), "conflicting explicit presentation currency or scale"
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


_FACT_LABEL_PRIORITY: dict[str, dict[str, int]] = {
    "operating_cash_flow": {
        _norm("jumlah arus kas bersih yang diperoleh dari (digunakan untuk) aktivitas operasi"): 100,
        _norm("arus kas neto diperoleh dari aktivitas operasi"): 100,
        _norm("net cash flows received from (used in) operating activities"): 100,
        # This is an intermediate subtotal in the IDX cash-flow template,
        # not the canonical total operating cash-flow fact.
        _norm("kas diperoleh dari (digunakan untuk) operasi"): 10,
    },
}


def _label_priority(fact: str, label: _Cell) -> int:
    return _FACT_LABEL_PRIORITY.get(fact, {}).get(_norm(label.value), 100)


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
        by_fact: dict[str, list[tuple[_Cell, _Cell, str, str]]] = defaultdict(list)
        for label in labels:
            fact = _fact_from_label(label.value)
            if fact is None:
                continue
            for column, (context_ref, context_coord) in current.items():
                value_cell = next((x for x in cells if x.sheet == sheet and x.row == label.row and x.column == column and x.numeric is not None), None)
                if value_cell is not None:
                    by_fact[fact].append((label, value_cell, context_ref, context_coord))
        for fact, matches in by_fact.items():
            found.add(fact)
            top_priority = max(_label_priority(fact, item[0]) for item in matches)
            top_matches = [item for item in matches if _label_priority(fact, item[0]) == top_priority]
            semantic_keys = {
                (str(item[1].numeric), item[2], statement)
                for item in top_matches
            }
            status = FactExtractionStatus.EXTRACTED
            detail = ""
            if len(semantic_keys) > 1:
                status = FactExtractionStatus.CONFLICTING_FACTS
                detail = "multiple authoritative current-period values or contexts for one canonical fact"
            elif unit_detail:
                status = FactExtractionStatus.UNRESOLVED_UNIT
                detail = unit_detail
            # Deterministic only after semantic filtering.  If equivalent
            # duplicate cells remain, their values/context agree; choosing the
            # earliest location preserves reproducibility without treating file
            # order as semantic authority.
            label, value_cell, context_ref, context_coord = sorted(
                top_matches,
                key=lambda item: (item[0].row, item[0].column, item[1].column),
            )[0]
            discarded = [
                f"{item[0].coordinate}:{item[1].coordinate}:priority={_label_priority(fact, item[0])}"
                for item in matches
                if item not in top_matches
            ]
            selection_detail = (
                f"selected label priority={top_priority}; candidates={len(matches)}; "
                f"discarded_lower_priority={','.join(discarded) if discarded else 'none'}"
            )
            if detail:
                detail = f"{detail}; {selection_detail}"
            else:
                detail = selection_detail
            record = FinancialFactRecord(
                **base,
                statement_identity=statement,
                fact_identity=fact,
                value=str(value_cell.numeric) if value_cell.numeric is not None else None,
                currency=currency,
                unit=unit,
                scale=scale,
                fiscal_period_covered=_period_covered(year, period, context_ref),
                source_location=f"sheet={sheet};label_cell={label.coordinate};value_cell={value_cell.coordinate};context_cell={context_coord}",
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
_IDX_TAXONOMY_URI = re.compile(
    r"^https?://www\.idx\.co\.id/xbrl/taxonomy/(?P<version>\d{4}-\d{2}-\d{2})/(?P<family>cor|dei)(?:/.*)?$",
    re.I,
)
_SCHEMA_REF = re.compile(r"<(?:[A-Za-z_][\w.-]*:)?schemaRef\b(?P<attrs>[^>]*)/?>", re.I | re.S)
_NS_DECL = re.compile(r"\bxmlns:(?P<prefix>idx-cor|idx-dei)\s*=\s*(?P<q>[\"'])(?P<uri>.*?)(?P=q)", re.I | re.S)
_ISO_CURRENCY = {"IDR", "USD", "EUR", "JPY", "GBP", "AUD", "SGD", "CNY", "HKD", "CAD"}


def _attrs(text: str) -> dict[str, str]:
    return {match.group("key"): match.group("value") for match in _ATTR.finditer(text)}


def _xbrl_taxonomy_metadata(text: str) -> tuple[str | None, str, bool]:
    """Resolve IDX taxonomy identity from namespace and optional schemaRef."""

    namespace_versions: dict[str, set[str]] = {"cor": set(), "dei": set()}
    namespace_evidence: list[str] = []
    for match in _NS_DECL.finditer(text):
        uri = match.group("uri").strip()
        parsed = _IDX_TAXONOMY_URI.fullmatch(uri)
        if parsed is None:
            continue
        family = parsed.group("family").casefold()
        namespace_versions[family].add(parsed.group("version"))
        namespace_evidence.append(f"xmlns:{match.group('prefix')}={uri}")

    schema_versions: set[str] = set()
    schema_families: set[str] = set()
    schema_evidence: list[str] = []
    for match in _SCHEMA_REF.finditer(text):
        attrs = _attrs(match.group("attrs"))
        href = attrs.get("xlink:href") or attrs.get("href") or ""
        parsed = _IDX_TAXONOMY_URI.search(href)
        if parsed is None:
            schema_evidence.append(f"unresolved_schemaRef={href or 'EMPTY'}")
            continue
        schema_versions.add(parsed.group("version"))
        schema_families.add(parsed.group("family").casefold())
        schema_evidence.append(f"schemaRef={href}")

    cor_versions = namespace_versions["cor"]
    dei_versions = namespace_versions["dei"]
    all_versions = cor_versions | dei_versions | schema_versions
    valid = bool(cor_versions) and len(all_versions) == 1 and schema_families.issubset({"cor", "dei"})
    if schema_evidence and any(item.startswith("unresolved_schemaRef=") for item in schema_evidence):
        valid = False
    if len(cor_versions) > 1 or len(dei_versions) > 1 or len(schema_versions) > 1:
        valid = False
    if schema_families and "cor" not in schema_families:
        valid = False
    version = next(iter(all_versions), None) if valid else None
    detail = "; ".join(namespace_evidence + schema_evidence) or "missing official IDX taxonomy namespace/schemaRef"
    return version, detail, valid


def _valid_xbrl_unit(unit: str | None) -> bool:
    if unit is None:
        return False
    normalized = unit.strip().upper()
    return normalized in _ISO_CURRENCY or bool(re.fullmatch(r"ISO4217:[A-Z]{3}", normalized))


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
    taxonomy_versions: set[str] = set()
    taxonomy_details: list[str] = []
    taxonomy_valid = True
    taxonomy_seen = False
    values_by_fact: dict[str, list[tuple[Decimal, str, dict[str, str], str, str, int]]] = defaultdict(list)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for member in archive.namelist():
            if not member.lower().endswith((".html", ".xhtml", ".xml")):
                continue
            text = archive.read(member).decode("utf-8", "ignore")
            if "idx-cor" in text.lower() or "schemaRef" in text or "idx-dei" in text.lower():
                taxonomy_seen = True
                member_version, member_detail, member_valid = _xbrl_taxonomy_metadata(text)
                if member_version is not None:
                    taxonomy_versions.add(member_version)
                taxonomy_details.append(f"member={member};{member_detail}")
                taxonomy_valid = taxonomy_valid and member_valid
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
                if context not in _ALLOWED_CONTEXTS or number is None or not _valid_xbrl_unit(unit) or parsed_scale is None:
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
                        taxonomy_version=next(iter(taxonomy_versions), None),
                        extraction_status=status,
                        detail="explicit concept lacks valid context, numeric value, ISO currency unitRef or integer scale",
                    ))
                    statuses[status.value] += 1
                    continue
                values_by_fact[fact].append((number, location, attr, unit.upper(), context, parsed_scale))
                evidence_units.append({"location": location, "unit": unit, "scale": parsed_scale, "context": context})
    for fact, matches in values_by_fact.items():
        found.add(fact)
        value_set = {str(item[0]) for item in matches}
        context_set = {item[4] for item in matches}
        unit_set = {item[3] for item in matches}
        scale_set = {item[5] for item in matches}
        if not taxonomy_seen or not taxonomy_valid or len(taxonomy_versions) != 1:
            status = FactExtractionStatus.UNRESOLVED_TAXONOMY
            detail = "missing, conflicting, or non-official IDX taxonomy/schemaRef; " + "; ".join(taxonomy_details)
        elif len(value_set) > 1 or len(context_set) > 1 or len(unit_set) > 1 or len(scale_set) > 1:
            status = FactExtractionStatus.CONFLICTING_FACTS
            detail = "conflicting authoritative numeric facts, contexts, units, or scales"
        else:
            status = FactExtractionStatus.EXTRACTED
            detail = ""
        number, location, attr, unit, context, scale = matches[0]
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
            taxonomy_version=next(iter(taxonomy_versions), None),
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
        taxonomy_version=next(iter(taxonomy_versions), None),
        version_id=base["version_id"],
        detail="; ".join(taxonomy_details),
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
