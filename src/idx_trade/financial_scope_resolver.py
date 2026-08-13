"""Fail-closed scope evidence extraction for captured IDX filings.

This module is deliberately limited to statement-scope evidence.  It does not
parse numeric facts, derive financial features, or infer scope from filenames,
issuer class, report period, or endpoint metadata.
"""

from __future__ import annotations

import hashlib
import io
import re
import zipfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree


class ScopeResolution(StrEnum):
    CONSOLIDATED = "CONSOLIDATED"
    SEPARATE = "SEPARATE"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class ScopeEvidence:
    """One auditable content-level scope marker."""

    location: str
    evidence_kind: str
    text: str
    scope: ScopeResolution


@dataclass(frozen=True)
class ScopeResolutionResult:
    """Resolution plus the exact source evidence used to reach it."""

    scope: ScopeResolution
    file_format: str
    source_sha256: str
    evidence: tuple[ScopeEvidence, ...] = ()
    detail: str = ""


_GROUP_LABEL = re.compile(r"^entitas\s+grup\s*/\s*group\s+entity$", re.IGNORECASE)
_SEPARATE_LABEL = re.compile(r"^entitas\s+tunggal\s*/\s*single\s+entity$", re.IGNORECASE)
_CONSOLIDATED_TITLE = re.compile(r"\blaporan\s+keuangan\s+konsolidasian\b", re.IGNORECASE)
_SEPARATE_TITLE = re.compile(r"\blaporan\s+keuangan\s+tersendiri\b", re.IGNORECASE)
_XBRL_SCOPE_CONCEPT = re.compile(
    r"(?:IndividualEntityOrAGroupOfEntities|AreOfAnIndividualEntityOrAGroupOfEntities)",
    re.IGNORECASE,
)
_XBRL_VALUE = re.compile(
    r"entitas\s+(?:grup|tunggal)\s*/\s*(?:group|single)\s+entity",
    re.IGNORECASE,
)


def _normalise_text(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def _scope_from_text(value: str) -> ScopeResolution | None:
    text = _normalise_text(value)
    if _GROUP_LABEL.fullmatch(text):
        return ScopeResolution.CONSOLIDATED
    if _SEPARATE_LABEL.fullmatch(text):
        return ScopeResolution.SEPARATE
    return None


def _title_scope(value: str) -> ScopeResolution | None:
    text = _normalise_text(value)
    if _CONSOLIDATED_TITLE.search(text) and not _SEPARATE_TITLE.search(text):
        return ScopeResolution.CONSOLIDATED
    if _SEPARATE_TITLE.search(text) and not _CONSOLIDATED_TITLE.search(text):
        return ScopeResolution.SEPARATE
    return None


def _finish(
    *,
    file_format: str,
    payload: bytes,
    evidence: Iterable[ScopeEvidence],
    detail: str,
) -> ScopeResolutionResult:
    items = tuple(evidence)
    scopes = {item.scope for item in items if item.scope is not ScopeResolution.UNRESOLVED}
    if len(scopes) == 1:
        scope = next(iter(scopes))
    elif len(scopes) > 1:
        scope = ScopeResolution.UNRESOLVED
        detail = detail or "conflicting consolidated/separate content markers"
    else:
        scope = ScopeResolution.UNRESOLVED
    return ScopeResolutionResult(
        scope=scope,
        file_format=file_format,
        source_sha256=hashlib.sha256(payload).hexdigest(),
        evidence=items,
        detail=detail,
    )


def _xml_text(element: ElementTree.Element) -> str:
    return _normalise_text("".join(element.itertext()))


def _xlsx_scope(payload: bytes) -> ScopeResolutionResult:
    evidence: list[ScopeEvidence] = []
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            names = set(archive.namelist())
            workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
            rels = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            rel_map = {
                item.attrib["Id"]: item.attrib["Target"] for item in rels
            }
            shared: list[str] = []
            if "xl/sharedStrings.xml" in names:
                shared_root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
                shared = [_xml_text(item) for item in shared_root]
            ns = {
                "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
                "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
            }
            for sheet in workbook.findall("main:sheets/main:sheet", ns):
                # Hidden sheets in the official files contain template choices
                # for both scopes.  They are not evidence that both scopes are
                # present in the submitted statement.
                if sheet.attrib.get("state", "visible") != "visible":
                    continue
                rel_id = sheet.attrib.get("{%s}id" % ns["rel"])
                target = rel_map.get(rel_id or "")
                if not target:
                    continue
                sheet_path = "xl/" + target.lstrip("/")
                if sheet_path not in names:
                    continue
                root = ElementTree.fromstring(archive.read(sheet_path))
                for cell in root.findall(".//main:c", ns):
                    value_node = cell.find("main:v", ns)
                    inline_node = cell.find("main:is", ns)
                    if value_node is None and inline_node is None:
                        continue
                    if cell.attrib.get("t") == "s" and value_node is not None:
                        index = int(value_node.text or "-1")
                        value = shared[index] if 0 <= index < len(shared) else ""
                    elif inline_node is not None:
                        value = _xml_text(inline_node)
                    else:
                        value = value_node.text or ""
                    scope = _scope_from_text(value)
                    if scope is not None:
                        evidence.append(
                            ScopeEvidence(
                                location=f"sheet={sheet.attrib.get('name', '')};cell={cell.attrib.get('r', '')}",
                                evidence_kind="xlsx_visible_scope_label",
                                text=_normalise_text(value),
                                scope=scope,
                            )
                        )
    except (KeyError, ValueError, zipfile.BadZipFile, ElementTree.ParseError, UnicodeDecodeError) as exc:
        return _finish(
            file_format="XLSX",
            payload=payload,
            evidence=(),
            detail=f"malformed XLSX scope evidence: {exc}",
        )

    # If the exact scope selector is absent, a visible title is still usable
    # content evidence, but only when it is unambiguous.
    if not evidence:
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                for name in archive.namelist():
                    if not name.startswith("xl/worksheets/") or not name.endswith(".xml"):
                        continue
                    text = _normalise_text(archive.read(name).decode("utf-8", "ignore"))
                    for match in _CONSOLIDATED_TITLE.finditer(text):
                        evidence.append(
                            ScopeEvidence(
                                location=name,
                                evidence_kind="xlsx_visible_statement_title",
                                text=match.group(0),
                                scope=ScopeResolution.CONSOLIDATED,
                            )
                        )
                    for match in _SEPARATE_TITLE.finditer(text):
                        evidence.append(
                            ScopeEvidence(
                                location=name,
                                evidence_kind="xlsx_visible_statement_title",
                                text=match.group(0),
                                scope=ScopeResolution.SEPARATE,
                            )
                        )
        except (zipfile.BadZipFile, UnicodeDecodeError):
            pass
    return _finish(
        file_format="XLSX",
        payload=payload,
        evidence=evidence,
        detail="" if evidence else "no visible authoritative scope marker",
    )


def _xbrl_scope(payload: bytes) -> ScopeResolutionResult:
    evidence: list[ScopeEvidence] = []
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            for name in archive.namelist():
                if not name.lower().endswith((".xml", ".xhtml", ".html")):
                    continue
                text = archive.read(name).decode("utf-8", "ignore")
                for match in _XBRL_VALUE.finditer(text):
                    value = _normalise_text(match.group(0))
                    scope = (
                        ScopeResolution.CONSOLIDATED
                        if re.search(r"entitas\s+grup", value, re.IGNORECASE)
                        else ScopeResolution.SEPARATE
                    )
                    start = max(0, match.start() - 260)
                    end = min(len(text), match.end() + 260)
                    snippet = _normalise_text(text[start:end])
                    kind = "ixbrl_scope_concept_context" if _XBRL_SCOPE_CONCEPT.search(snippet) else "ixbrl_scope_label"
                    evidence.append(
                        ScopeEvidence(
                            location=f"{name};context={_context_ref(snippet)}",
                            evidence_kind=kind,
                            text=snippet,
                            scope=scope,
                        )
                    )
    except (KeyError, zipfile.BadZipFile, UnicodeDecodeError) as exc:
        return _finish(
            file_format="XBRL_ZIP",
            payload=payload,
            evidence=(),
            detail=f"malformed XBRL ZIP scope evidence: {exc}",
        )
    return _finish(
        file_format="XBRL_ZIP",
        payload=payload,
        evidence=evidence,
        detail="" if evidence else "no explicit XBRL scope concept/value",
    )


def _context_ref(snippet: str) -> str:
    match = re.search(r"contextRef\s*=\s*['\"]([^'\"]+)['\"]", snippet, re.IGNORECASE)
    return match.group(1) if match else "UNSPECIFIED"


def _pdf_scope(payload: bytes) -> ScopeResolutionResult:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(payload))
        evidence: list[ScopeEvidence] = []
        for index, page in enumerate(reader.pages, start=1):
            text = _normalise_text(page.extract_text() or "")
            for match in _CONSOLIDATED_TITLE.finditer(text):
                evidence.append(
                    ScopeEvidence(
                        location=f"page={index}",
                        evidence_kind="pdf_statement_title",
                        text=match.group(0),
                        scope=ScopeResolution.CONSOLIDATED,
                    )
                )
            for match in _SEPARATE_TITLE.finditer(text):
                evidence.append(
                    ScopeEvidence(
                        location=f"page={index}",
                        evidence_kind="pdf_statement_title",
                        text=match.group(0),
                        scope=ScopeResolution.SEPARATE,
                    )
                )
        return _finish(
            file_format="PDF",
            payload=payload,
            evidence=evidence,
            detail="" if evidence else "no explicit PDF statement title",
        )
    except Exception as exc:  # fail closed for unavailable/malformed extraction
        return _finish(
            file_format="PDF",
            payload=payload,
            evidence=(),
            detail=f"PDF scope extraction unavailable or malformed: {exc}",
        )


def resolve_statement_scope(
    payload: bytes,
    *,
    file_name: str = "",
    file_type: str = "",
) -> ScopeResolutionResult:
    """Resolve only explicit content-level scope evidence.

    ``file_name`` and ``file_type`` select the parser only.  They never decide
    the returned scope.  Ambiguous, mixed, absent, or malformed evidence is
    always returned as ``UNRESOLVED``.
    """

    lower_name = file_name.lower()
    lower_type = file_type.lower()
    if payload[:2] == b"PK" and ("xlsx" in lower_name or "spreadsheet" in lower_type or b"xl/workbook.xml" in payload):
        # XBRL ZIP is handled first when it contains HTML/XML filing content;
        # XLSX is identified by its workbook member.
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                names = set(archive.namelist())
            if "xl/workbook.xml" in names:
                return _xlsx_scope(payload)
            if any(name.lower().endswith((".xhtml", ".html")) for name in names):
                return _xbrl_scope(payload)
        except zipfile.BadZipFile:
            pass
    if payload[:2] == b"PK" and ("xbrl" in lower_name or "inline" in lower_name or lower_type in {".zip", "zip"}):
        return _xbrl_scope(payload)
    if lower_name.endswith(".pdf") or "pdf" in lower_type or payload.startswith(b"%PDF"):
        return _pdf_scope(payload)
    return _finish(
        file_format="UNKNOWN",
        payload=payload,
        evidence=(),
        detail="unsupported or ambiguous filing representation",
    )


def resolve_statement_scope_path(path: str | Path) -> ScopeResolutionResult:
    """Resolve a captured attachment without using its name as scope evidence."""

    target = Path(path)
    return resolve_statement_scope(
        target.read_bytes(),
        file_name=target.name,
        file_type=target.suffix,
    )
