from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str, relative: str):
    path = ROOT / relative

    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(module)

    return module


downloader = load_script(
    "capture_dividend_candidate_identity_test",
    "scripts/"
    "capture_forward_dividend_candidate_attachments_v1.py",
)

reviewer = load_script(
    "review_dividend_candidate_identity_test",
    "scripts/"
    "review_forward_dividend_candidate_attachments_v1.py",
)


def test_downloader_selects_by_announcement_number_when_id_missing():
    discovery = {
        "candidates": [
            {
                "ticker": "BBCA",
                "announcement_id": "",
                "announcement_number": "005/TEST/2026",
                "classification": "CASH_DIVIDEND_CANDIDATE",
            }
        ]
    }

    result = downloader.select_exact_candidate(
        discovery,
        ticker="BBCA",
        announcement_number="005/TEST/2026",
    )

    assert (
        result["announcement_number"]
        == "005/TEST/2026"
    )


def test_downloader_requires_exactly_one_identity_selector():
    discovery = {
        "candidates": []
    }

    with pytest.raises(
        RuntimeError,
        match="EXACTLY_ONE_REQUIRED",
    ):
        downloader.select_exact_candidate(
            discovery,
            ticker="BBCA",
        )

    with pytest.raises(
        RuntimeError,
        match="EXACTLY_ONE_REQUIRED",
    ):
        downloader.select_exact_candidate(
            discovery,
            ticker="BBCA",
            announcement_id="A1",
            announcement_number="N1",
        )


def test_reviewer_raw_provenance_can_bind_by_announcement_number(
    tmp_path,
):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    raw_path = raw_dir / "BBCA_p001.json"

    payload = {
        "Replies": [
            {
                "pengumuman": {
                    "Kode_Emiten": "BBCA",
                    "Id2": "",
                    "Id": "",
                    "NoPengumuman": "005/TEST/2026",
                }
            }
        ]
    }

    raw_path.write_text(
        json.dumps(
            payload,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    raw_sha = hashlib.sha256(
        raw_path.read_bytes()
    ).hexdigest()

    discovery_path = (
        tmp_path
        / "DISCOVERY_MANIFEST.json"
    )

    discovery = {
        "raw_artifacts": [
            {
                "ticker": "BBCA",
                "path": "raw/BBCA_p001.json",
                "sha256": raw_sha,
            }
        ]
    }

    result = reviewer.exact_announcement_raw_sha(
        discovery_path=discovery_path,
        discovery=discovery,
        ticker="BBCA",
        announcement_number="005/TEST/2026",
    )

    assert result == raw_sha
