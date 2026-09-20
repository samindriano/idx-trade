import json
from pathlib import Path

import pytest

from research.alpha_idx_financial_report_surface_v1 import (
    _official_url,
    run,
    summarize,
)


def _write_index(root: Path, year: int = 2023, period: str = "audit") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"all-{year}-{period}-pagesize1000.idxid.raw"
    path.write_text(
        json.dumps(
            {
                "Search": {},
                "ResultCount": 2,
                "Results": [
                    {
                        "KodeEmiten": "AAA",
                        "Report_Year": str(year),
                        "Report_Period": "Audit",
                        "File_Modified": "2024-01-10T00:00:00",
                        "Attachments": [
                            {"File_ID": "1", "File_Name": "instance.zip", "File_Type": ".zip", "File_Size": 20, "File_Path": "/x/AAA/instance.zip"},
                            {"File_ID": "2", "File_Name": "statement.xlsx", "File_Type": ".xlsx", "File_Size": 0, "File_Path": "/x/AAA/statement.xlsx"},
                        ],
                    },
                    {
                        "KodeEmiten": "BBB",
                        "Report_Year": str(year),
                        "Report_Period": "Audit",
                        "File_Modified": "2026-01-10T00:00:00",
                        "Attachments": [
                            {"File_ID": "3", "File_Name": "inlineXBRL.zip", "File_Type": ".zip", "File_Size": 20, "File_Path": "/x/BBB/inlineXBRL.zip"},
                        ],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_summarize_records_coverage_and_late_modified_surface(tmp_path: Path):
    root = tmp_path / "indexes"
    _write_index(root)
    result = summarize(root)
    period = result["periods"][0]
    assert period["rows"] == 2
    assert period["unique_tickers"] == 2
    assert period["instance_zip_tickers"] == 1
    assert period["instance_zip_missing_tickers"] == ["BBB"]
    assert period["modified_after_report_year_plus_one_rows"] == 1
    assert period["zero_size_by_type"] == {".xlsx": 1}


def test_official_url_encodes_spaces_and_rejects_other_hosts():
    url = _official_url("/Portals/Report Folder/instance.zip")
    assert url == "https://www.idx.id/Portals/Report%20Folder/instance.zip"
    with pytest.raises(ValueError):
        _official_url("https://example.com/instance.zip")


def test_run_writes_only_inside_staging_marker(tmp_path: Path):
    root = tmp_path / "indexes"
    _write_index(root)
    with pytest.raises(ValueError):
        run(
            type(
                "Args",
                (),
                {
                    "index_root": root,
                    "output": tmp_path / "result.json",
                    "download_year": None,
                    "download_period": None,
                    "download_root": None,
                    "download_limit": None,
                    "delay_seconds": 1.0,
                },
            )()
        )
