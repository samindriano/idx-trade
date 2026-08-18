from __future__ import annotations

import json
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_v4_ca_fren_official_archive_replay_v4 as v4


def test_extracts_wordpress_media_source_url() -> None:
    payload = json.dumps([
        {
            "id": 123,
            "slug": "prospektus-pmhmetd-v",
            "source_url": "https://www.smartfren.com/app/uploads/2024/04/Prospektus-PMHMETD-V.pdf",
        }
    ]).encode()
    result = v4.extract_cms_asset_candidates(
        payload, "https://www.smartfren.com/wp-json/wp/v2/media"
    )
    assert result == (
        "https://www.smartfren.com/app/uploads/2024/04/Prospektus-PMHMETD-V.pdf",
    )


def test_cms_extractor_rejects_off_domain_url() -> None:
    payload = json.dumps([
        {"source_url": "https://example.com/app/uploads/2024/04/x.pdf"}
    ]).encode()
    assert v4.extract_cms_asset_candidates(
        payload, "https://www.smartfren.com/wp-json/wp/v2/media"
    ) == tuple()


def test_cms_extractor_ignores_non_json() -> None:
    assert v4.extract_cms_asset_candidates(
        b"<html>not json</html>", "https://www.smartfren.com/"
    ) == tuple()


def test_cms_queries_are_bounded_and_issuer_only() -> None:
    endpoints = v4._cms_endpoints()
    assert len(endpoints) == len(v4.CMS_QUERIES) * 2
    assert len(endpoints) == 10
    assert all(url.startswith("https://www.smartfren.com/wp-json/wp/v2/") for url in endpoints)
    assert all("per_page=100" in url for url in endpoints)
