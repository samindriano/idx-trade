import json
from pathlib import Path

import pytest

from research.alpha_idx_profile_detail_surface_v1 import audit_raw_file, summarize_raw


def _write_raw(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / "TEST.json"
    path.write_text(
        json.dumps(
            {
                "Profiles": [{"KodeEmiten": "TEST", "NamaEmiten": "Example", "TanggalPencatatan": "2020-01-01", "Status": 0}],
                "BondsAndSukuk": [{"ISINCode": "ID0000000000"}],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_audit_separates_stock_profile_fields_from_bond_isin(tmp_path: Path):
    result = audit_raw_file(_write_raw(tmp_path))
    assert result["profile_count"] == 1
    assert result["stock_profile_isin_fields"] == []
    assert result["bond_rows_with_isin"] == 1
    assert result["listing_date_present"] is True


def test_summarize_requires_raw_json(tmp_path: Path):
    with pytest.raises(ValueError):
        summarize_raw(tmp_path)
