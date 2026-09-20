from __future__ import annotations

import json
from pathlib import Path

from research.alpha_official_announcement_surface_v1 import (
    audit_effective_date_text,
    audit_payload,
)


def _write_payload(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "Items": [
                    {
                        "Id": "20250101-1",
                        "AnnouncementNo": "Peng-1",
                        "PublishDate": "2025-01-22T23:30:50",
                        "Title": "Perubahan Klasifikasi Industri",
                        "Code": " AAA ",
                        "Jenis": "STOCK",
                        "Attachments": [{"FullSavePath": "https://example.test/a.pdf"}],
                    }
                ],
                "ItemCount": 1,
                "PageSize": 100,
                "PageNumber": 1,
                "PageCount": 1,
            }
        ),
        encoding="utf-8",
    )


def test_payload_shape_and_code_normalization(tmp_path: Path) -> None:
    path = tmp_path / "payload.json"
    _write_payload(path)
    result = audit_payload(path)
    assert result["items_observed"] == 1
    assert result["item_count"] == 1
    assert result["codes"] == ["AAA"]
    assert result["unique_ids"] == 1


def test_effective_date_is_kept_separate_from_api_publish_date(tmp_path: Path) -> None:
    root = tmp_path / "attachments" / "2025-01-22__AAA"
    root.mkdir(parents=True)
    text = root / "01__announcement.txt"
    text.write_text(
        "Perubahan tersebut mulai efektif pada tanggal 24 Juni 2024\n",
        encoding="utf-8",
    )
    result = audit_effective_date_text(root.parent, {"AAA": "2025-01-22T23:30:50"})
    assert result["codes_with_explicit_effective_date"] == ["AAA"]
    assert result["records"][0]["effective_date_text"] == ["24 Juni 2024"]
    assert result["records"][0]["publish_date_after_document_effective"] is True


def test_missing_effective_text_does_not_create_an_inferred_date(tmp_path: Path) -> None:
    root = tmp_path / "attachments" / "2025-01-22__AAA"
    root.mkdir(parents=True)
    (root / "01__announcement.txt").write_text("No effective date stated.\n", encoding="utf-8")
    result = audit_effective_date_text(root.parent, {"AAA": "2025-01-22T23:30:50"})
    assert result["records"] == []
