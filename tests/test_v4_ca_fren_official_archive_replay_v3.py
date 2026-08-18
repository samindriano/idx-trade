from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import run_v4_ca_fren_official_archive_replay_v3 as v3


def test_canonicalizes_english_upload_asset_path() -> None:
    result = v3._canonical_asset_variants(
        "https://www.smartfren.com/en/app/uploads/2025/03/report.pdf",
        "https://www.smartfren.com/en/investor/",
    )
    assert "https://www.smartfren.com/app/uploads/2025/03/report.pdf" in result
    assert "https://www.smartfren.com/en/app/uploads/2025/03/report.pdf" in result


def test_canonicalizes_trailing_pdf_slash() -> None:
    result = v3._canonical_asset_variants(
        "https://www.smartfren.com/app/uploads/2024/04/fren.pdf/",
        "https://www.smartfren.com/",
    )
    assert "https://www.smartfren.com/app/uploads/2024/04/fren.pdf" in result


def test_extracts_json_escaped_attachment_url() -> None:
    payload = (
        b'<script>window.__DATA__={"attachment":"https:\\/\\/www.smartfren.com'
        b'\\/app\\/uploads\\/2024\\/04\\/Prospektus-PMHMETD-V.pdf"}</script>'
    )
    result = v3.extract_hidden_asset_candidates(
        payload,
        "https://www.smartfren.com/en/connect-with-us/whats-new/year/example/",
    )
    assert (
        "https://www.smartfren.com/app/uploads/2024/04/Prospektus-PMHMETD-V.pdf"
        in result
    )


def test_rejects_off_domain_hidden_asset() -> None:
    payload = b'<script>{"attachment":"https://example.com/app/uploads/x.pdf"}</script>'
    result = v3.extract_hidden_asset_candidates(payload, "https://www.smartfren.com/")
    assert result == tuple()


def test_priority_prefers_pmhmetd_before_annual_report() -> None:
    urls = [
        "https://www.smartfren.com/app/uploads/2025/03/Smartfren-AR-2024.pdf",
        "https://www.smartfren.com/app/uploads/2024/04/Prospektus-PMHMETD-V.pdf",
    ]
    assert sorted(urls, key=v3._priority)[0].endswith("Prospektus-PMHMETD-V.pdf")
