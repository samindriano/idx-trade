import json
from pathlib import Path

import pytest

from research.alpha_idx_issued_history_surface_v1 import (
    audit_raw_file,
    parse_codes,
    summarize_raw,
)


def _write_raw(root: Path, code: str = "TEST") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{code}.json"
    path.write_text(
        json.dumps(
            {
                "recordsTotal": 2,
                "data": [
                    {
                        "KodeEmiten": code,
                        "TanggalPencatatan": "2024-01-02T00:00:00",
                        "JenisTindakan": "Stock Split",
                        "JumlahSaham": 100,
                    },
                    {
                        "KodeEmiten": code,
                        "TanggalPencatatan": "2024-02-02T00:00:00",
                        "JenisTindakan": "Partial Delisting",
                        "JumlahSaham": 80,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_audit_preserves_event_types_and_dates(tmp_path: Path):
    result = audit_raw_file(_write_raw(tmp_path))
    assert result["rows"] == 2
    assert result["date_min"] == "2024-01-02"
    assert result["date_max"] == "2024-02-02"
    assert result["action_counts"] == {"Partial Delisting": 1, "Stock Split": 1}
    assert result["missing_required_field_rows"] == 0


def test_summarize_requires_raw_json(tmp_path: Path):
    with pytest.raises(ValueError):
        summarize_raw(tmp_path)


def test_parse_codes_deduplicates_and_rejects_bad_codes():
    assert parse_codes("bbca, CNTX,BBCA") == ["BBCA", "CNTX"]
    with pytest.raises(ValueError):
        parse_codes("BAD")
