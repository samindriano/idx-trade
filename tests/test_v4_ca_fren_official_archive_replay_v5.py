from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_v4_ca_fren_official_archive_replay_v5 as v5


def test_focused_cms_endpoints_are_bounded_media_queries() -> None:
    endpoints = v5._focused_cms_endpoints()
    assert len(endpoints) == 4
    assert all("/wp-json/wp/v2/media?" in url for url in endpoints)
    assert all("per_page=100" in url for url in endpoints)


def test_candidate_relevance_prefers_pmhmetd_pdf() -> None:
    urls = [
        "https://www.smartfren.com/app/uploads/2024/04/generic.pdf",
        "https://www.smartfren.com/app/uploads/2024/04/Prospektus-PMHMETD-V-FREN.pdf",
    ]
    assert sorted(urls, key=v5._candidate_relevance)[0].endswith(
        "Prospektus-PMHMETD-V-FREN.pdf"
    )


def test_fast_discovery_has_no_broad_v3_fallback() -> None:
    source = Path(v5.__file__).read_text(encoding="utf-8")
    assert "fallback_disabled" in source
    assert "discover_and_verify_rights_pdf_v3(" not in source


def test_timeout_contract_is_bounded() -> None:
    assert v5.CMS_TIMEOUT == (5, 12)
    assert v5.PDF_TIMEOUT == (5, 25)
    assert v5.MAX_PDF_CANDIDATES == 12
