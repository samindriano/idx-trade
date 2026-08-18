from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import inspect_v4_ca_fren_saved_disclosure_archive as forensic


def test_extracts_post_id_and_href_near_title() -> None:
    payload = b'''<article id="post-78123"><a href="/connect-with-us/whats-new/year/perubahan-jadwal-pmhmetd-v/">Perubahan Jadwal PMHMETD V</a></article>'''
    result = forensic.inspect(payload)
    item = result["items"][0]
    assert item["occurrences"] == 1
    assert item["matches"][0]["post_ids"] == ["78123"]
    assert "/connect-with-us/whats-new/year/perubahan-jadwal-pmhmetd-v/" in item["matches"][0]["hrefs"]


def test_extracts_shortlink_if_present() -> None:
    payload = b'''<div id="post-78400">Informasi Tambahan PMHMETD V FREN<link rel="shortlink" href="https://www.smartfren.com/?p=78400" /></div>'''
    result = forensic.inspect(payload)
    item = result["items"][1]
    assert item["matches"][0]["shortlinks"] == ["https://www.smartfren.com/?p=78400"]


def test_missing_title_is_reported_without_guessing() -> None:
    result = forensic.inspect(b"<html>ordinary archive</html>")
    assert all(item["occurrences"] == 0 for item in result["items"])
