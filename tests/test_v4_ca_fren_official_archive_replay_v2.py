from __future__ import annotations

from pathlib import Path
import sys

import requests

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_v4_ca_fren_official_archive_replay_v2 as v2


def _reset() -> None:
    v2._KSEI_RESULTS.clear()


def test_all_ksei_unavailable_is_explicit_not_silently_complete() -> None:
    _reset()
    for url in v2._KSEI_URLS:
        v2._KSEI_RESULTS[url] = {
            "corroboration_status": "UNAVAILABLE",
            "status_code": 500,
            "evidence_accepted": False,
        }
    status = v2._ksei_status()
    assert status["status"] == "UNAVAILABLE"
    assert status["available_count"] == 0
    assert status["expected_count"] == 5


def test_partial_ksei_availability_is_explicit() -> None:
    _reset()
    first = sorted(v2._KSEI_URLS)[0]
    v2._KSEI_RESULTS[first] = {"corroboration_status": "AVAILABLE"}
    for url in v2._KSEI_URLS - {first}:
        v2._KSEI_RESULTS[url] = {"corroboration_status": "UNAVAILABLE"}
    assert v2._ksei_status()["status"] == "PARTIAL"


def test_complete_ksei_availability_is_explicit() -> None:
    _reset()
    for url in v2._KSEI_URLS:
        v2._KSEI_RESULTS[url] = {"corroboration_status": "AVAILABLE"}
    assert v2._ksei_status()["status"] == "COMPLETE"


def test_non_ksei_sources_stay_strict() -> None:
    assert not v2._is_ksei_news("https://www.smartfren.com/en/investor/")
    assert v2._is_ksei_news(next(iter(v2._KSEI_URLS)))


def test_issuer_transport_exception_is_normalized_not_accepted(monkeypatch, tmp_path) -> None:
    def fail(*args, **kwargs):
        raise requests.ConnectionError("read timed out")

    monkeypatch.setattr(v2, "_ORIGINAL_GET", fail)
    try:
        v2.get_v2(
            "https://www.smartfren.com/app/uploads/2024/04/example.pdf",
            tmp_path / "candidate.bin",
        )
    except RuntimeError as exc:
        text = str(exc)
        assert "FREN_ISSUER_TRANSPORT_FAILED" in text
        assert "ConnectionError" in text
    else:
        raise AssertionError("issuer transport error must not be treated as evidence")


def test_combined_hash_filters_unavailable_empty_payloads() -> None:
    digest = v2.combined_evidence_sha_v2([b"issuer-a", b"", b"issuer-b"])
    expected = v2._ORIGINAL_COMBINED_SHA([b"issuer-a", b"issuer-b"])
    assert digest == expected


def test_all_empty_evidence_fails_closed() -> None:
    try:
        v2.combined_evidence_sha_v2([b"", b""])
    except RuntimeError as exc:
        assert "NO_ACCEPTED_OFFICIAL_EVIDENCE_PAYLOADS" in str(exc)
    else:
        raise AssertionError("all-empty official evidence must fail closed")
