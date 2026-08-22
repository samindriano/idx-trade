from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]

SCRIPT = (
    ROOT
    / "scripts"
    / "run_forward_dividend_acquisition_batch_v1.py"
)

spec = importlib.util.spec_from_file_location(
    "forward_dividend_batch_test",
    SCRIPT,
)

assert spec is not None
assert spec.loader is not None

batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)


def candidate(
    *,
    announcement_id="A1",
    announcement_number="N1",
):
    return {
        "ticker": "BBCA",
        "announcement_id": announcement_id,
        "announcement_number": announcement_number,
        "classification": "CASH_DIVIDEND_CANDIDATE",
    }


def test_journal_identity_prefers_stable_number():
    result = batch.canonical_announcement_identity(
        candidate(
            announcement_id="IDX-A1",
            announcement_number="005/TEST/2026",
        )
    )

    assert result == (
        "BBCA|NUMBER|005/TEST/2026"
    )


def test_journal_identity_falls_back_to_id():
    result = batch.canonical_announcement_identity(
        candidate(
            announcement_id="IDX-A1",
            announcement_number="",
        )
    )

    assert result == "BBCA|ID|IDX-A1"


def test_download_selector_prefers_id():
    result = batch.candidate_selector_args(
        candidate(
            announcement_id="IDX-A1",
            announcement_number="N1",
        )
    )

    assert result == [
        "--announcement-id",
        "IDX-A1",
    ]


def test_download_selector_falls_back_to_number():
    result = batch.candidate_selector_args(
        candidate(
            announcement_id="",
            announcement_number="N1",
        )
    )

    assert result == [
        "--announcement-number",
        "N1",
    ]


def test_candidate_directory_name_is_deterministic():
    first = batch.candidate_directory_name(
        candidate()
    )

    second = batch.candidate_directory_name(
        candidate()
    )

    assert first == second
    assert first.startswith("BBCA_")
    assert "/" not in first
    assert "\\" not in first


def test_batch_manifest_seal_roundtrip():
    raw = {
        "schema_version": batch.SCHEMA,
        "status": "COMPLETE",
        "value": 123,
    }

    sealed = batch.seal_batch_manifest(
        raw
    )

    verified = (
        batch.verify_batch_manifest_payload(
            sealed
        )
    )

    assert verified == sealed


def test_batch_manifest_tamper_fails_closed():
    raw = {
        "schema_version": batch.SCHEMA,
        "status": "COMPLETE",
        "value": 123,
    }

    sealed = batch.seal_batch_manifest(
        raw
    )

    sealed["value"] = 999

    with pytest.raises(
        batch.DividendAcquisitionBatchError,
        match="HASH_MISMATCH",
    ):
        batch.verify_batch_manifest_payload(
            sealed
        )


def test_discovery_duplicate_announcement_identity_fails_closed(tmp_path):
    path = tmp_path / "DISCOVERY_MANIFEST.json"
    payload = {
        "status": "COMPLETE",
        "required_tickers": ["BBCA"],
        "date_from": "2025-08-22",
        "date_to": "2026-08-22",
        "candidates": [candidate(), candidate()],
        "raw_artifacts": [
            {
                "ticker": "BBCA",
                "path": "page.json",
                "sha256": "a" * 64,
            }
        ],
    }
    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(
        batch.DividendAcquisitionBatchError,
        match="DUPLICATE_CANDIDATE",
    ):
        batch.verify_discovery_manifest(
            path,
            expected_tickers=("BBCA",),
            expected_from="2025-08-22",
            expected_to="2026-08-22",
        )
