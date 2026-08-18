from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import probe_v4_ca_fren_post_78437 as probe


def test_endpoint_set_is_bounded_and_exact_post_scoped() -> None:
    assert len(probe.ENDPOINTS) == 9
    assert any("year/78437" in url for url in probe.ENDPOINTS)
    assert all("smartfren.com" in url for url in probe.ENDPOINTS)


def test_relevant_json_strings_surfaces_hidden_pdf() -> None:
    payload = {
        "id": 78437,
        "meta": {
            "attachment": "https://www.smartfren.com/app/uploads/2024/04/Prospektus-PMHMETD-V.pdf"
        },
    }
    result = probe._relevant_json_strings(payload)
    assert result
    assert any("Prospektus-PMHMETD-V.pdf" in row["value"] for row in result)


def test_irrelevant_json_strings_are_not_reported() -> None:
    assert probe._relevant_json_strings({"id": 78437, "title": "ordinary"}) == []
