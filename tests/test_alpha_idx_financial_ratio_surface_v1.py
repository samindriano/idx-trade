import json
from pathlib import Path

import pytest

from research.alpha_idx_financial_ratio_surface_v1 import audit_file, summarize


def _write_ratio(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / "ratio-2024-12-pagesize1000.raw"
    path.write_text(
        json.dumps(
            {
                "data": [
                    {"code": "AAA", "stockName": "A", "fsDate": "2024-09-30", "assets": 1, "liabilities": 1, "equity": 1, "sales": 1, "profitPeriod": 1},
                    {"code": "BBB", "stockName": "B", "fsDate": "2024-06-30", "assets": 1, "liabilities": 1, "equity": 1, "sales": 1, "profitPeriod": 1},
                ],
                "meta": {"totalItems": 2},
            }
        ),
        encoding="utf-8",
    )
    return path


def test_audit_records_snapshot_and_fs_date_range(tmp_path: Path):
    result = audit_file(_write_ratio(tmp_path), 2024, 12)
    assert result["rows"] == 2
    assert result["unique_codes"] == 2
    assert result["fs_date_min"] == "2024-06-30"
    assert result["fs_date_max"] == "2024-09-30"
    assert result["missing_required_field_rows"] == 0


def test_summarize_requires_retained_snapshots(tmp_path: Path):
    with pytest.raises(ValueError):
        summarize(tmp_path)
