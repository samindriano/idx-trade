from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pandas as pd

from research.alpha_idx_authority_crosswalk_v1 import (
    file_modified_lag_audit,
    instance_attachment,
    materialize_xbrl,
    period_from_context,
    ratio_classification_audit,
    trading_panel_key_crosswalk,
    xbrl_semantic_collision_audit,
)


def test_instance_attachment_requires_exact_instance_zip() -> None:
    row = {
        "Attachments": [
            {"File_Name": "inlineXBRL.zip", "File_ID": "wrong"},
            {"File_Name": "instance.zip", "File_ID": "right", "File_Path": "/instance.zip"},
        ]
    }

    assert instance_attachment(row)["File_ID"] == "right"
    assert instance_attachment({"Attachments": [{"File_Name": "FinancialStatement.xlsx"}]}) is None


def test_file_modified_lag_is_descriptive_not_pit_authority() -> None:
    result = file_modified_lag_audit(
        [
            {"KodeEmiten": "AAA", "Report_Year": "2024", "File_Modified": "2025-04-01T00:00:00"},
            {"KodeEmiten": "BBB", "Report_Year": "2024", "File_Modified": None},
        ]
    )

    assert result["rows_with_valid_dates"] == 1
    assert result["lag_days_negative_count"] == 0
    assert "does not prove publication" in result["interpretation"]


def test_period_from_context_preserves_dimensions() -> None:
    import xml.etree.ElementTree as ET

    context = ET.fromstring(
        """
        <context xmlns='http://www.xbrl.org/2003/instance' id='c1'>
          <entity><identifier scheme='x'>AAA</identifier></entity>
          <period><startDate>2024-01-01</startDate><endDate>2024-12-31</endDate></period>
          <scenario><x:explicitMember xmlns:x='http://xbrldi'>x:Member</x:explicitMember></scenario>
        </context>
        """
    )

    result = period_from_context(context)

    assert result["start"] == "2024-01-01"
    assert result["end"] == "2024-12-31"
    assert result["has_dimensions"] is True
    assert result["dimension_count"] == 1


def test_materialize_xbrl_keeps_undimensioned_selected_facts(tmp_path: Path) -> None:
    archive = tmp_path / "2025-audit" / "AAA.instance.zip"
    archive.parent.mkdir()
    xml = """
    <xbrl xmlns='http://www.xbrl.org/2003/instance' xmlns:ex='http://example'>
      <context id='i'><entity><identifier scheme='x'>AAA</identifier></entity><period><instant>2025-12-31</instant></period></context>
      <context id='d'><entity><identifier scheme='x'>AAA</identifier></entity><period><startDate>2025-01-01</startDate><endDate>2025-12-31</endDate></period></context>
      <ex:Assets contextRef='i' unitRef='u'>100</ex:Assets>
      <ex:SalesAndRevenue contextRef='d' unitRef='u'>200</ex:SalesAndRevenue>
    </xbrl>
    """
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("instance.xbrl", xml)
    output = tmp_path / "facts.jsonl"

    result = materialize_xbrl({("2025", "AAA"): archive}, output)

    assert result["archives_parsed"] == 1
    assert result["field_archive_counts"] == {"revenue": 1, "total_assets": 1}
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert {row["field"] for row in rows} == {"revenue", "total_assets"}
    assert {row["period_shape"] for row in rows} == {"INSTANT", "DURATION"}


def test_xbrl_semantic_collision_audit_preserves_ambiguity(tmp_path: Path) -> None:
    output = tmp_path / "facts.jsonl"
    rows = [
        {
            "field": "net_income",
            "concept": "ProfitLoss",
            "unit_ref": "IDR",
            "period_shape": "DURATION",
            "ticker": "AAA",
            "report_year": "2025",
            "period_end": "2025-12-31",
        },
        {
            "field": "net_income",
            "concept": "ProfitLossAttributableToParentEntity",
            "unit_ref": "USD",
            "period_shape": "DURATION",
            "ticker": "AAA",
            "report_year": "2025",
            "period_end": "2025-12-31",
        },
    ]
    output.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    result = xbrl_semantic_collision_audit(output)

    assert result["duplicate_code_year_period_groups"]["net_income"] == 1
    assert result["units_by_field"]["net_income"] == ["IDR", "USD"]


def test_trading_panel_crosswalk_separates_key_and_field_agreement(tmp_path: Path) -> None:
    (tmp_path / "AAA.json").write_text(
        json.dumps(
            {
                "KodeEmiten": "AAA",
                "replies": [
                    {"Date": "2021-04-29T00:00:00", "High": 11, "Low": 9, "Close": 10, "Volume": 100},
                    {"Date": "2021-04-30T00:00:00", "High": 12, "Low": 10, "Close": 11, "Volume": 200},
                ],
            }
        ),
        encoding="utf-8",
    )
    panel = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA"],
            "date": ["2021-04-29", "2021-05-03"],
            "high": [11, 13],
            "low": [9, 11],
            "close": [10, 12],
            "volume": [100, 300],
        }
    )

    result = trading_panel_key_crosswalk(tmp_path, panel)

    assert result["exact_key_intersection"] == 1
    assert result["panel_keys_missing_from_official_trading"] == 1
    assert result["official_trading_keys_not_in_panel"] == 1
    assert result["field_mismatch_counts_on_intersection"] == {}


def test_ratio_classification_audit_does_not_promote_fsdate_to_pit(tmp_path: Path) -> None:
    (tmp_path / "2026-01.raw").write_text(
        json.dumps(
            {
                "data": [
                    {
                        "code": "AAA",
                        "fsDate": "2024-12-31",
                        "sector": "Energy",
                        "subSector": "Oil",
                        "industry": "Coal",
                        "subIndustry": "Mining",
                        "sectorCode": "A",
                        "subSectorCode": "A1",
                        "industryCode": "A11",
                        "subIndustryCode": "A111",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "2026-02.raw").write_text(
        json.dumps(
            {
                "data": [
                    {
                        "code": "AAA",
                        "fsDate": "2024-12-31",
                        "sector": "Materials",
                        "subSector": "Oil",
                        "industry": "Coal",
                        "subIndustry": "Mining",
                        "sectorCode": "B",
                        "subSectorCode": "A1",
                        "industryCode": "A11",
                        "subIndustryCode": "A111",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = ratio_classification_audit(tmp_path)

    assert result["status"] == "BOUNDED_SNAPSHOT_CLASSIFICATION_ONLY"
    assert result["observed_code_count"] == 1
    assert result["codes_with_adjacent_snapshot_change_by_field"]["sector"] == 1
    assert "effective time" in result["interpretation"]
