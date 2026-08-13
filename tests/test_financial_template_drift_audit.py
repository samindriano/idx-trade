from __future__ import annotations

import io
import zipfile

from idx_trade.financial_fact_table import FactExtractionStatus, extract_filing_facts
from idx_trade.financial_template_drift_audit import _audit_xlsx


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _inline_fixture(*, value: str = "1.4002934741E10", label: str = "Jumlah aset") -> bytes:
    workbook = f'''<workbook xmlns="{MAIN_NS}" xmlns:r="{REL_NS}"><sheets>
      <sheet name="1000000" sheetId="1" r:id="rId1"/>
      <sheet name="1210000" sheetId="2" r:id="rId2"/>
    </sheets></workbook>'''
    rels = '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Target="worksheets/sheet1.xml"/>
      <Relationship Id="rId2" Target="worksheets/sheet2.xml"/>
    </Relationships>'''
    metadata = f'''<worksheet xmlns="{MAIN_NS}"><sheetData>
      <row r="29"><c r="A29" t="inlineStr"><is><t>Mata uang pelaporan / Reporting currency</t></is></c><c r="B29" t="inlineStr"><is><t>Rupiah / IDR</t></is></c></row>
      <row r="31"><c r="A31" t="inlineStr"><is><t>Pembulatan yang digunakan / Rounding used</t></is></c><c r="B31" t="inlineStr"><is><t>Satuan penuh / Full Amount</t></is></c></row>
    </sheetData></worksheet>'''
    statement = f'''<worksheet xmlns="{MAIN_NS}"><sheetData>
      <row r="4"><c r="B4" t="inlineStr"><is><t>CurrentYearInstant</t></is></c></row>
      <row r="128"><c r="A128" t="inlineStr"><is><t>{label}</t></is></c><c r="B128" t="inlineStr"><is><t>{value}</t></is></c></row>
    </sheetData></worksheet>'''
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", rels)
        archive.writestr("xl/worksheets/sheet1.xml", metadata)
        archive.writestr("xl/worksheets/sheet2.xml", statement)
    return output.getvalue()


def _kwargs() -> dict[str, object]:
    return {
        "ticker": "TEST",
        "fiscal_year": 2025,
        "fiscal_period": "tw2",
        "statement_scope": "CONSOLIDATED",
        "publication_at_utc": "2025-08-01T02:00:00Z",
        "source_ref": "IDX/TEST/1",
        "representation_format": "XLSX",
    }


def test_audit_detects_exact_label_with_inline_scientific_numeric() -> None:
    payload = _inline_fixture()
    audit = _audit_xlsx(payload)
    evidence = audit["facts"]["total_assets"]
    assert evidence["status"] == "PRESENT_CANONICAL_INLINE_NUMERIC"
    assert evidence["recoverable_with_strict_numeric_decoder"] is True
    # The accepted canonical parser remains unchanged and therefore does not
    # silently gain this mapping from the audit.
    records, _ = extract_filing_facts(payload, **_kwargs())
    assert not any(record.fact_identity == "total_assets" and record.extraction_status is FactExtractionStatus.EXTRACTED for record in records)


def test_audit_rejects_non_numeric_inline_text_without_guessing() -> None:
    audit = _audit_xlsx(_inline_fixture(value="N/A"))
    evidence = audit["facts"]["total_assets"]
    assert evidence["status"] == "CANONICAL_LABEL_NO_CURRENT_NUMERIC"
    assert evidence["recoverable_with_strict_numeric_decoder"] is False


def test_audit_does_not_map_unrecognized_label_fuzzily() -> None:
    audit = _audit_xlsx(_inline_fixture(label="Total assets excluding something"))
    assert audit["facts"]["total_assets"]["status"] == "ABSENT_CANONICAL_LABEL"
