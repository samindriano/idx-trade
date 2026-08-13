from __future__ import annotations

import io
import json
import zipfile
from decimal import Decimal

import pytest

from idx_trade.financial_fact_table import (
    FactExtractionStatus,
    VersionedFactStore,
    _parse_decimal,
    extract_filing_facts,
)


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1.25E+3", Decimal("1250")),
        ("-4.5e-2", Decimal("-0.045")),
        ("+7E2", Decimal("700")),
        ("(1.2E+4)", Decimal("-12000")),
        ("(7.5e-3)", Decimal("-0.0075")),
    ],
)
def test_parse_decimal_accepts_strict_scientific_notation_and_signed_parentheses(
    raw: str, expected: Decimal
) -> None:
    assert _parse_decimal(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "1.2E",
        "1.2E+",
        "1.2E--3",
        "1.2E3.4",
        "1.2.3E4",
        "N/A",
        "",
    ],
)
def test_parse_decimal_rejects_malformed_exponents_and_nonnumeric_text(raw: str) -> None:
    assert _parse_decimal(raw) is None


def test_parse_decimal_explicitly_treats_comma_as_grouping_before_exponent() -> None:
    # The accepted extractor strips commas before Decimal parsing.  Therefore
    # this is a grouped integer under the frozen grammar, not locale decimal
    # notation; future locale parsing must not be introduced implicitly.
    assert _parse_decimal("1,2E3") == Decimal("12000")


def _xlsx_fixture(
    *,
    hidden_scope: str | None = None,
    visible_scope: str = "Entitas grup / Group entity",
    presentation_currency: str = "Rupiah / IDR",
    presentation_scale: str = "Satuan Penuh / Full Amount",
    operating_cash_flow: bool = False,
    conflicting_operating: bool = False,
) -> bytes:
    workbook = f'''<?xml version="1.0" encoding="UTF-8"?>
    <workbook xmlns="{MAIN_NS}" xmlns:r="{REL_NS}"><sheets>
      <sheet name="1000000" sheetId="1" r:id="rId1"/>
      <sheet name="1210000" sheetId="2" r:id="rId2"/>
      {('<sheet name="template" sheetId="3" state="hidden" r:id="rId3"/>' if hidden_scope else '')}
    </sheets></workbook>'''
    rels = f'''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Target="worksheets/sheet1.xml" Type="worksheet"/>
      <Relationship Id="rId2" Target="worksheets/sheet2.xml" Type="worksheet"/>
      {('<Relationship Id="rId3" Target="worksheets/sheet3.xml" Type="worksheet"/>' if hidden_scope else '')}
    </Relationships>'''
    cash_flow = '''<sheet name="1510000" sheetId="3" r:id="rId3"/>''' if operating_cash_flow else ''
    cash_rel = '''<Relationship Id="rId3" Target="worksheets/sheet3.xml" Type="worksheet"/>''' if operating_cash_flow else ''
    workbook = workbook.replace('</sheets></workbook>', f'{cash_flow}</sheets></workbook>')
    rels = rels.replace('</Relationships>', f'{cash_rel}</Relationships>')
    sheet1 = f'''<worksheet xmlns="{MAIN_NS}"><sheetData>
      <row r="29"><c r="A29" t="inlineStr"><is><t>Mata uang pelaporan / Reporting currency</t></is></c><c r="B29" t="inlineStr"><is><t>{presentation_currency}</t></is></c></row>
      <row r="31"><c r="A31" t="inlineStr"><is><t>Pembulatan yang digunakan / Rounding used</t></is></c><c r="B31" t="inlineStr"><is><t>{presentation_scale}</t></is></c></row>
      <row r="20"><c r="B20" t="inlineStr"><is><t>{visible_scope}</t></is></c></row>
    </sheetData></worksheet>'''
    sheet2 = f'''<worksheet xmlns="{MAIN_NS}"><sheetData>
      <row r="4"><c r="B4" t="inlineStr"><is><t>CurrentYearInstant</t></is></c></row>
      <row r="8"><c r="A8" t="inlineStr"><is><t>Kas dan setara kas</t></is></c><c r="B8"><v>100</v></c></row>
      <row r="128"><c r="A128" t="inlineStr"><is><t>Jumlah aset</t></is></c><c r="B128"><v>200</v></c></row>
    </sheetData></worksheet>'''
    hidden = f'''<worksheet xmlns="{MAIN_NS}"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>{hidden_scope or ''}</t></is></c></row></sheetData></worksheet>'''
    conflict_row = '<row r="48"><c r="A48" t="inlineStr"><is><t>Jumlah arus kas bersih yang diperoleh dari (digunakan untuk) aktivitas operasi</t></is></c><c r="B48"><v>21</v></c></row>' if conflicting_operating else ''
    cash_sheet = f'''<worksheet xmlns="{MAIN_NS}"><sheetData>
      <row r="4"><c r="B4" t="inlineStr"><is><t>CurrentYearDuration</t></is></c></row>
      <row r="24"><c r="A24" t="inlineStr"><is><t>Kas diperoleh dari (digunakan untuk) operasi</t></is></c><c r="B24"><v>10</v></c></row>
      <row r="47"><c r="A47" t="inlineStr"><is><t>Jumlah arus kas bersih yang diperoleh dari (digunakan untuk) aktivitas operasi</t></is></c><c r="B47"><v>20</v></c></row>
      {conflict_row}
    </sheetData></worksheet>'''
    content_types = '''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/></Types>'''
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        for name, value in {
            "xl/workbook.xml": workbook,
            "xl/_rels/workbook.xml.rels": rels,
            "xl/worksheets/sheet1.xml": sheet1,
            "xl/worksheets/sheet2.xml": sheet2,
            "[Content_Types].xml": content_types,
        }.items():
            archive.writestr(name, value)
        if operating_cash_flow:
            archive.writestr("xl/worksheets/sheet3.xml", cash_sheet)
        if hidden_scope:
            archive.writestr("xl/worksheets/sheet3.xml", hidden)
    return payload.getvalue()


def _xbrl_fixture(
    *,
    context: str = "CurrentYearInstant",
    plain_label: bool = False,
    second_value: str | None = None,
    taxonomy: bool = True,
    schema_version: str | None = None,
    unit: str = "IDR",
    scale: str = "0",
) -> bytes:
    concept = "idx-dei:WhetherTheFinancialStatementsAreOfAnIndividualEntityOrAGroupOfEntities"
    scope = "Entitas grup / Group entity"
    scope_block = f'<ix:nonNumeric name="{concept}" contextRef="{context}">{scope}</ix:nonNumeric>' if not plain_label else f"<p>{scope}</p>"
    second = f'<ix:nonFraction name="idx-cor:Assets" contextRef="CurrentYearInstant" unitRef="{unit}" scale="{scale}">{second_value}</ix:nonFraction>' if second_value else ""
    taxonomy_ns = 'xmlns:idx-cor="http://www.idx.co.id/xbrl/taxonomy/2020-01-01/cor" xmlns:idx-dei="http://www.idx.co.id/xbrl/taxonomy/2020-01-01/dei"' if taxonomy else ''
    schema = f'<link:schemaRef xmlns:link="http://www.xbrl.org/2003/linkbase" xlink:href="https://www.idx.co.id/xbrl/taxonomy/{schema_version}/cor/idx-cor.xsd" xmlns:xlink="http://www.w3.org/1999/xlink"/>' if schema_version else ''
    html = f'''<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"><head>
      {schema}
      </head><body {taxonomy_ns}>{scope_block}
      <ix:nonFraction name="idx-cor:Assets" contextRef="{context}" unitRef="{unit}" scale="{scale}">100</ix:nonFraction>{second}
    </body></html>'''
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("1000000.html", html)
    return payload.getvalue()


def _kwargs(fmt: str) -> dict[str, object]:
    return {
        "ticker": "TEST",
        "fiscal_year": 2025,
        "fiscal_period": "tw1",
        "statement_scope": "CONSOLIDATED",
        "publication_at_utc": "2025-05-01T02:00:00Z",
        "source_ref": "IDX/TEST/1",
        "representation_format": fmt,
    }


def test_xlsx_uses_visible_current_period_and_explicit_unit() -> None:
    records, diagnostic = extract_filing_facts(_xlsx_fixture(), **_kwargs("XLSX"))
    assert diagnostic.industry_class == "GENERAL"
    assert {record.fact_identity for record in records} == {"cash_and_cash_equivalents", "total_assets"}
    assert all(record.extraction_status is FactExtractionStatus.EXTRACTED for record in records)
    assert all(record.currency == "IDR" and record.scale == 1 for record in records)


def test_xlsx_uses_presentation_metadata_not_statement_body_currency() -> None:
    records, _ = extract_filing_facts(
        _xlsx_fixture(
            presentation_currency="Dollar Amerika / USD",
            presentation_scale="Ribuan / In Thousand",
        ),
        **_kwargs("XLSX"),
    )
    assert records
    assert all(record.currency == "USD" and record.scale == 1_000 for record in records)


def test_xlsx_selects_authoritative_operating_cash_flow_total() -> None:
    records, _ = extract_filing_facts(_xlsx_fixture(operating_cash_flow=True), **_kwargs("XLSX"))
    operating = [record for record in records if record.fact_identity == "operating_cash_flow"]
    assert len(operating) == 1
    assert operating[0].extraction_status is FactExtractionStatus.EXTRACTED
    assert operating[0].value == "20"
    assert "label_cell=A47" in operating[0].source_location
    assert "discarded_lower_priority=A24:B24" in operating[0].detail


def test_xlsx_conflicting_authoritative_totals_remain_unresolved() -> None:
    records, _ = extract_filing_facts(
        _xlsx_fixture(operating_cash_flow=True, conflicting_operating=True),
        **_kwargs("XLSX"),
    )
    operating = [record for record in records if record.fact_identity == "operating_cash_flow"]
    assert len(operating) == 1
    assert operating[0].extraction_status is FactExtractionStatus.CONFLICTING_FACTS


def test_xlsx_hidden_scope_does_not_create_evidence() -> None:
    records, diagnostic = extract_filing_facts(
        _xlsx_fixture(hidden_scope="Entitas tunggal / Single entity", visible_scope=""),
        **_kwargs("XLSX"),
    )
    assert diagnostic.industry_class == "GENERAL"
    assert records
    # The fact parser is intentionally independent from scope; this test uses
    # the accepted scope resolver only to assert the source fixture boundary.
    from idx_trade.financial_scope_resolver import _xlsx_scope

    assert _xlsx_scope(_xlsx_fixture(hidden_scope="Entitas tunggal / Single entity", visible_scope="")).scope.value == "UNRESOLVED"


def test_xbrl_exact_concept_and_context_only() -> None:
    records, diagnostic = extract_filing_facts(_xbrl_fixture(), **_kwargs("XBRL"))
    assert diagnostic.taxonomy == "IDX_COR"
    assert any(record.fact_identity == "total_assets" and record.extraction_status is FactExtractionStatus.EXTRACTED for record in records)
    wrong, _ = extract_filing_facts(_xbrl_fixture(context="PriorYearInstant"), **_kwargs("XBRL"))
    assert any(record.extraction_status is FactExtractionStatus.UNRESOLVED_PERIOD for record in wrong)
    plain, _ = extract_filing_facts(_xbrl_fixture(plain_label=True), **_kwargs("XBRL"))
    assert not any(record.fact_identity == "revenue" for record in plain)


def test_xbrl_namespace_taxonomy_is_authoritative_without_schema_ref() -> None:
    records, diagnostic = extract_filing_facts(_xbrl_fixture(), **_kwargs("XBRL"))
    assert diagnostic.taxonomy_version == "2020-01-01"
    assert any(record.extraction_status is FactExtractionStatus.EXTRACTED for record in records)


def test_xbrl_missing_or_conflicting_taxonomy_fails_closed() -> None:
    missing, _ = extract_filing_facts(_xbrl_fixture(taxonomy=False), **_kwargs("XBRL"))
    assert any(record.extraction_status is FactExtractionStatus.UNRESOLVED_TAXONOMY for record in missing)
    conflict, _ = extract_filing_facts(_xbrl_fixture(schema_version="2021-01-01"), **_kwargs("XBRL"))
    assert any(record.extraction_status is FactExtractionStatus.UNRESOLVED_TAXONOMY for record in conflict)


def test_xbrl_invalid_unit_or_scale_fails_closed() -> None:
    records, _ = extract_filing_facts(_xbrl_fixture(unit="shares", scale=""), **_kwargs("XBRL"))
    assert any(record.extraction_status is FactExtractionStatus.UNRESOLVED_UNIT for record in records)


def test_xbrl_conflicting_authoritative_values_fail_closed() -> None:
    records, _ = extract_filing_facts(_xbrl_fixture(second_value="200"), **_kwargs("XBRL"))
    assets = [record for record in records if record.fact_identity == "total_assets"]
    assert len(assets) == 1
    assert assets[0].extraction_status is FactExtractionStatus.CONFLICTING_FACTS


def test_versioned_store_preserves_replacement_and_knowledge_time() -> None:
    payload = _xlsx_fixture()
    first, _ = extract_filing_facts(payload, **_kwargs("XLSX"))
    later_kwargs = _kwargs("XLSX") | {"publication_at_utc": "2025-06-01T02:00:00Z"}
    later, _ = extract_filing_facts(payload, **later_kwargs)
    store = VersionedFactStore().append(*first).append(*later)
    key = ("TEST", 2025, "tw1", "CONSOLIDATED", "statement_of_financial_position", "total_assets")
    assert len(store.versions(key)) == 2
    assert {record.knowledge_at_utc for record in store.versions(key)} == {"2025-05-01T02:00:00Z", "2025-06-01T02:00:00Z"}


def test_versioned_store_rejects_same_time_different_attachment_hash() -> None:
    first, _ = extract_filing_facts(_xlsx_fixture(), **_kwargs("XLSX"))
    second, _ = extract_filing_facts(_xlsx_fixture(hidden_scope="unused"), **_kwargs("XLSX"))
    # The parser may produce the same facts, but the immutable source bytes
    # are different and therefore cannot share one knowledge timestamp.
    try:
        VersionedFactStore().append(first[0]).append(second[0])
    except ValueError as exc:
        assert "conflicting attachment hashes" in str(exc)
    else:
        raise AssertionError("same-time conflicting source hash was accepted")


def test_unsupported_format_is_not_extracted() -> None:
    records, diagnostic = extract_filing_facts(b"pdf", **_kwargs("PDF"))
    assert records == []
    assert diagnostic.status_counts == {FactExtractionStatus.UNSUPPORTED_FORMAT.value: 1}
