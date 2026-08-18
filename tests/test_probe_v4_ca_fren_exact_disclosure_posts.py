from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import probe_v4_ca_fren_exact_disclosure_posts as probe


def test_exact_posts_are_frozen_and_bounded() -> None:
    assert [row["post_id"] for row in probe.POSTS] == [78197, 78122, 74393]
    assert len(probe.POSTS) * 2 == 6
    assert all("smartfren.com" in row["permalink"] for row in probe.POSTS)


def test_locator_extraction_keeps_relevant_issuer_asset_only() -> None:
    payload = b'''
    <a href="https://www.smartfren.com/app/uploads/2024/04/FREN-PMHMETD-V.pdf">download</a>
    <a href="https://example.com/fake-PMHMETD.pdf">bad</a>
    <a href="https://www.smartfren.com/about/">ordinary</a>
    '''
    result = probe.extract_relevant_locators(payload, "https://www.smartfren.com/")
    assert result == ("https://www.smartfren.com/app/uploads/2024/04/FREN-PMHMETD-V.pdf",)


def test_visible_text_marker_context_can_surface_exact_schedule() -> None:
    payload = b'''
    <html><body>
    PMHMETD V - Pasar Reguler dan Pasar Negosiasi - Ex Right 17 April 2024.
    Record Date 18 April 2024.
    </body></html>
    '''
    text = probe._visible_text(payload)
    contexts = probe._marker_contexts(text)
    assert any(row["marker"] == "17 April 2024" for row in contexts)
    assert any(row["marker"] == "Ex Right" for row in contexts)
