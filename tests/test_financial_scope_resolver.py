from __future__ import annotations

import io
import zipfile

from idx_trade.financial_scope_resolver import (
    ScopeResolution,
    resolve_statement_scope,
)


def _xlsx(*, visible_values: list[str], hidden_values: list[str] = ()) -> bytes:
    shared = list(dict.fromkeys([*visible_values, *hidden_values]))
    shared_xml = "".join(
        f"<si><t>{value}</t></si>" for value in shared
    )

    def sheet_xml(values: list[str]) -> str:
        cells = []
        for row, value in enumerate(values, start=1):
            cells.append(f'<c r="A{row}" t="s"><v>{shared.index(value)}</v></c>')
        return (
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f"<sheetData><row r=\"1\">{''.join(cells)}</row></sheetData></worksheet>"
        )

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            """<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
            <sheets><sheet name="1000000" sheetId="1" r:id="rId1"/> 
            <sheet name="hidden" sheetId="2" state="hidden" r:id="rId2"/></sheets></workbook>""",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            """<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
            <Relationship Id="rId1" Target="worksheets/sheet1.xml"/>
            <Relationship Id="rId2" Target="worksheets/sheet2.xml"/></Relationships>""",
        )
        archive.writestr(
            "xl/sharedStrings.xml",
            f"""<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
            {shared_xml}</sst>""",
        )
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml(visible_values))
        archive.writestr("xl/worksheets/sheet2.xml", sheet_xml(list(hidden_values)))
    return output.getvalue()


def _xbrl(value: str) -> bytes:
    html = f"""<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL">
    <ix:nonNumeric name="idx-dei:WhetherTheFinancialStatementsAreOfAnIndividualEntityOrAGroupOfEntities"
      contextRef="CurrentYearInstant">{value}</ix:nonNumeric></html>"""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("1000000.html", html)
    return output.getvalue()


def _xbrl_with_context(value: str, context: str | None) -> bytes:
    context_attr = f' contextRef="{context}"' if context is not None else ""
    html = f"""<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL">
    <ix:nonNumeric name="idx-dei:WhetherTheFinancialStatementsAreOfAnIndividualEntityOrAGroupOfEntities"
      {context_attr}>{value}</ix:nonNumeric></html>"""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("1000000.html", html)
    return output.getvalue()


def _xbrl_facts(values: list[tuple[str, str]]) -> bytes:
    facts = "".join(
        f'''<ix:nonNumeric name="idx-dei:WhetherTheFinancialStatementsAreOfAnIndividualEntityOrAGroupOfEntities"
        contextRef="{context}">{value}</ix:nonNumeric>'''
        for value, context in values
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("1000000.html", f"<html>{facts}</html>")
    return output.getvalue()


def _xbrl_plain(text: str) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("1000000.html", f"<html><p>{text}</p></html>")
    return output.getvalue()


def test_xlsx_group_scope_uses_visible_selector_and_ignores_hidden_template_option():
    result = resolve_statement_scope(
        _xlsx(
            visible_values=["Entitas grup / Group entity"],
            hidden_values=["Entitas tunggal / Single entity", "Entitas grup / Group entity"],
        ),
        file_name="misleading-separate-name.xlsx",
    )

    assert result.scope is ScopeResolution.CONSOLIDATED
    assert result.evidence[0].location == "sheet=1000000;cell=A1"
    assert result.source_sha256


def test_xlsx_mixed_visible_scope_fails_closed():
    result = resolve_statement_scope(
        _xlsx(
            visible_values=[
                "Entitas grup / Group entity",
                "Entitas tunggal / Single entity",
            ]
        ),
        file_name="FinancialStatement.xlsx",
    )

    assert result.scope is ScopeResolution.UNRESOLVED
    assert {item.scope for item in result.evidence} == {
        ScopeResolution.CONSOLIDATED,
        ScopeResolution.SEPARATE,
    }


def test_hidden_xlsx_title_without_visible_scope_is_unresolved():
    result = resolve_statement_scope(
        _xlsx(visible_values=[], hidden_values=["Laporan keuangan tersendiri"]),
        file_name="statement.xlsx",
    )

    assert result.scope is ScopeResolution.UNRESOLVED
    assert result.evidence == ()


def test_visible_xlsx_selector_wins_over_hidden_conflicting_title():
    result = resolve_statement_scope(
        _xlsx(
            visible_values=["Entitas grup / Group entity"],
            hidden_values=["Laporan keuangan tersendiri"],
        ),
        file_name="statement.xlsx",
    )

    assert result.scope is ScopeResolution.CONSOLIDATED
    assert all("hidden" not in item.location for item in result.evidence)


def test_xbrl_scope_preserves_concept_context_evidence():
    result = resolve_statement_scope(_xbrl("Entitas grup / Group entity"), file_name="filing_inlineXBRL.zip")

    assert result.scope is ScopeResolution.CONSOLIDATED
    assert result.evidence[0].evidence_kind == "ixbrl_scope_concept_context"
    assert "context=CurrentYearInstant" in result.evidence[0].location


def test_xbrl_conflicting_scope_values_fail_closed():
    result = resolve_statement_scope(
        _xbrl_facts(
            [
                ("Entitas grup / Group entity", "CurrentYearInstant"),
                ("Entitas tunggal / Single entity", "CurrentYearInstant"),
            ]
        ),
        file_name="filing_inlineXBRL.zip",
    )

    assert result.scope is ScopeResolution.UNRESOLVED


def test_xbrl_plain_scope_label_without_idx_dei_concept_is_unresolved():
    result = resolve_statement_scope(
        _xbrl_plain("Entitas grup / Group entity"),
        file_name="filing_inlineXBRL.zip",
    )

    assert result.scope is ScopeResolution.UNRESOLVED


def test_xbrl_wrong_or_missing_context_is_unresolved():
    for context in ("PriorYearInstant", None):
        result = resolve_statement_scope(
            _xbrl_with_context("Entitas grup / Group entity", context),
            file_name="filing_inlineXBRL.zip",
        )
        assert result.scope is ScopeResolution.UNRESOLVED
        assert result.evidence
        assert result.evidence[0].evidence_kind == "ixbrl_scope_concept_wrong_context"


def test_pdf_scope_is_content_based_and_conflict_is_unresolved(monkeypatch):
    class Page:
        def extract_text(self):
            return "Laporan keuangan konsolidasian\nLaporan keuangan tersendiri"

    class Reader:
        pages = [Page()]

    import pypdf

    monkeypatch.setattr(pypdf, "PdfReader", lambda _: Reader())
    result = resolve_statement_scope(b"%PDF-synthetic", file_name="consolidated.pdf")

    assert result.file_format == "PDF"
    assert result.scope is ScopeResolution.UNRESOLVED


def test_filename_or_issuer_metadata_cannot_create_scope():
    result = resolve_statement_scope(
        b"not a recognized filing",
        file_name="BBCA-consolidated-2024.xlsx",
        file_type=".xlsx",
    )

    assert result.scope is ScopeResolution.UNRESOLVED
    assert result.evidence == ()
