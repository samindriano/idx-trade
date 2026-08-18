from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import inspect_v4_ca_fren_saved_html as forensic


def test_extracts_escaped_same_domain_pdf() -> None:
    payload = b'<script>{"file":"https:\\/\\/www.smartfren.com\\/app\\/uploads\\/2024\\/04\\/Prospektus-PMHMETD-V.pdf"}</script>'
    result = forensic.inspect(payload)
    assert "https://www.smartfren.com/app/uploads/2024/04/Prospektus-PMHMETD-V.pdf" in result["same_domain_locators"]


def test_rejects_off_domain_pdf() -> None:
    payload = b'<a href="https://example.com/app/uploads/2024/04/Prospektus-PMHMETD-V.pdf">x</a>'
    result = forensic.inspect(payload)
    assert result["same_domain_locators"] == []


def test_surfaces_iframe_fragment() -> None:
    payload = b'<iframe src="/viewer?file=/app/uploads/2024/04/prospektus.pdf"></iframe>'
    result = forensic.inspect(payload)
    assert result["relevant_tag_fragments"]
