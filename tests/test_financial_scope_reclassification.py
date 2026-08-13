from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from idx_trade.financial_scope_reclassification import (
    OfflineReclassificationError,
    _has_mixed_authoritative_scope,
    classify_exact_join,
    run_offline_reclassification,
)
from idx_trade.financial_scope_resolver import ScopeResolution


def _xlsx(label: str) -> bytes:
    output = __import__("io").BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="1000000" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>',
        )
        archive.writestr(
            "xl/sharedStrings.xml",
            f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>{label}</t></si></sst>',
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetData><row r="1"><c r="A1" t="s"><v>0</v></c></row></sheetData></worksheet>',
        )
    return output.getvalue()


def _fixture_root(tmp_path: Path, *, status: str = "SCOPE_UNRESOLVED") -> tuple[Path, Path, bytes]:
    census = tmp_path / "census"
    (census / "raw").mkdir(parents=True)
    (census / "attachments").mkdir()
    payload = _xlsx("Entitas grup / Group entity")
    attachment = census / "attachments" / "report_TEST_2024_tw1_FinancialStatement-2024-I-TEST.xlsx"
    attachment.write_bytes(payload)
    source_hash = hashlib.sha256(payload).hexdigest()
    report = {
        "Results": [
            {
                "KodeEmiten": "TEST",
                "Attachments": [
                    {
                        "File_Name": "FinancialStatement-2024-I-TEST.xlsx",
                        "File_Path": "/official/FinancialStatement-2024-I-TEST.xlsx",
                    }
                ],
            }
        ]
    }
    (census / "raw" / "financial_reports_2024_tw1.json").write_text(
        json.dumps(report), encoding="utf-8"
    )
    row = {
        "ticker": "TEST",
        "year": 2024,
        "period": "tw1",
        "status": status,
        "report_found": True,
        "announcement_found": True,
        "exact_attachment_join": True,
        "publication_at_utc": "2025-05-01T01:02:03Z",
        "source_sha256": [source_hash, source_hash],
        "source_refs": ["TEST/REF"],
        "pit_ready": False,
    }
    (census / "coverage_rows.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    (census / "MANIFEST__rerun_v6.json").write_text("{}\n", encoding="utf-8")
    return census, attachment, payload


def test_exact_join_records_scope_evidence_and_prior_chain_gates(tmp_path):
    census, _, _ = _fixture_root(tmp_path)
    from idx_trade.financial_scope_reclassification import _load_report_inventory

    row = json.loads((census / "coverage_rows.jsonl").read_text())
    result = classify_exact_join(
        census_root=census,
        row=row,
        report_inventory=_load_report_inventory(census),
    )
    assert result.scope == ScopeResolution.CONSOLIDATED.value
    assert result.representation_format == "XLSX"
    assert result.evidence[0]["location"] == "sheet=1000000;cell=A1"
    assert result.prior_chain_gates_pass is True
    assert result.file_hash_matches_chain is True
    assert result.pit_ready is True


def test_non_exact_join_is_not_reclassified_or_ready(tmp_path):
    census, _, _ = _fixture_root(tmp_path, status="ATTACHMENT_AMBIGUOUS")
    rows = (census / "coverage_rows.jsonl").read_text()
    row = json.loads(rows)
    row["exact_attachment_join"] = False
    (census / "coverage_rows.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(OfflineReclassificationError, match="expected 6108 exact joins"):
        run_offline_reclassification(census_root=census, output_root=tmp_path / "out")


def test_scope_hash_disagreement_fails_closed(tmp_path):
    census, _, _ = _fixture_root(tmp_path)
    row = json.loads((census / "coverage_rows.jsonl").read_text())
    row["source_sha256"] = ["0" * 64, "0" * 64]
    with pytest.raises(OfflineReclassificationError, match="hash disagrees"):
        from idx_trade.financial_scope_reclassification import _load_report_inventory

        classify_exact_join(
            census_root=census,
            row=row,
            report_inventory=_load_report_inventory(census),
        )


def test_mixed_scope_is_counted_per_join_not_across_the_dataset():
    assert _has_mixed_authoritative_scope(
        ({"scope": "CONSOLIDATED"}, {"scope": "SEPARATE"})
    )
    assert not _has_mixed_authoritative_scope(({"scope": "CONSOLIDATED"},))
