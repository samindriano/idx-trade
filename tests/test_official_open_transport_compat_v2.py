from __future__ import annotations

import json

import pytest

from idx_trade import official_open_evidence_v1 as v1
from idx_trade.official_open_transport_compat_v2 import (
    LEGACY_PROJECT_ENVELOPE,
    TOP_LEVEL_RAW_ENVELOPE,
    capture_official_open_with_transport_fallback_v2,
    fetch_zapi_raw_idx_stock_summary_v2,
    validate_zapi_raw_provenance_v2,
)


SESSION = "2026-06-12"


def _rows():
    return [
        {
            "StockCode": "AADI",
            "Date": "2026-06-12T00:00:00",
            "OpenPrice": 8100,
            "FirstTrade": 8075,
        },
        {
            "StockCode": "BBCA",
            "Date": "2026-06-12T00:00:00",
            "OpenPrice": 6000,
            "FirstTrade": 5975,
        },
    ]


def _top_level(*, provider="idx", path=v1.UPSTREAM_PATH, data=None):
    rows = _rows() if data is None else data
    return json.dumps(
        {
            "provider": provider,
            "path": path,
            "recordsTotal": len(rows) if isinstance(rows, list) else 2,
            "recordsFiltered": len(rows) if isinstance(rows, list) else 2,
            "data": rows,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def _legacy(*, project=v1.ZAPI_PROJECT, timestamp="2026-08-22T00:00:00Z"):
    inner = json.loads(_top_level().decode())
    return json.dumps(
        {"project": project, "timestamp": timestamp, "data": inner},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


class _Response:
    def __init__(self, content: bytes, status_code: int = 200):
        self.content = content
        self.status_code = status_code


def test_current_top_level_raw_shape_is_admitted_with_exact_provenance():
    assert validate_zapi_raw_provenance_v2(_top_level()) == TOP_LEVEL_RAW_ENVELOPE


def test_legacy_project_envelope_remains_strict_and_admitted():
    assert validate_zapi_raw_provenance_v2(_legacy()) == LEGACY_PROJECT_ENVELOPE
    with pytest.raises(v1.OfficialOpenEvidenceError, match="ZAPI_RAW_PROJECT_MISMATCH"):
        validate_zapi_raw_provenance_v2(_legacy(project="finance:other"))
    with pytest.raises(v1.OfficialOpenEvidenceError, match="ZAPI_RAW_TIMESTAMP_MISSING"):
        validate_zapi_raw_provenance_v2(_legacy(timestamp=""))


@pytest.mark.parametrize(
    ("raw", "error"),
    [
        (_top_level(provider="other"), "ZAPI_RAW_PROVIDER_MISMATCH"),
        (_top_level(path="Other/GetThing"), "ZAPI_RAW_PATH_MISMATCH"),
        (_top_level(data={"unexpected": "wrapper"}), "ZAPI_RAW_DATA_MISSING"),
    ],
)
def test_top_level_raw_cannot_bypass_authority_path_or_data_shape(raw, error):
    with pytest.raises(v1.OfficialOpenEvidenceError, match=error):
        validate_zapi_raw_provenance_v2(raw)


def test_fetch_records_truthful_top_level_envelope_metadata():
    observed = {}

    def fake_get(url, *, params, headers, timeout):
        observed.update(url=url, params=params, headers=headers, timeout=timeout)
        return _Response(_top_level())

    raw, meta = fetch_zapi_raw_idx_stock_summary_v2(
        SESSION, api_key="secret", get=fake_get, timeout_seconds=7
    )
    assert raw == _top_level()
    assert observed["params"] == {
        "path": v1.UPSTREAM_PATH,
        "query": "date=20260612&start=0&length=9999",
    }
    assert meta["transport"] == v1.ZAPI_RAW_TRANSPORT
    assert meta["provider"] == "idx"
    assert meta["response_envelope"] == TOP_LEVEL_RAW_ENVELOPE
    assert "secret" not in json.dumps(meta)


def test_full_fallback_certifies_top_level_raw_and_restores_legacy_globals(tmp_path):
    original_fetch = v1.fetch_zapi_raw_idx_stock_summary
    original_inner = v1._zapi_inner_payload

    def direct_403(url, *, params, headers, timeout):
        return _Response(b"forbidden", status_code=403)

    def zapi_ok(url, *, params, headers, timeout):
        return _Response(_top_level())

    manifest = capture_official_open_with_transport_fallback_v2(
        SESSION,
        output_root=tmp_path,
        zapi_api_key="secret",
        direct_get=direct_403,
        zapi_get=zapi_ok,
        timeout_seconds=1,
    )
    payload = json.loads(manifest.read_text())

    assert payload["transport"] == v1.ZAPI_RAW_TRANSPORT
    assert payload["transport_policy"] == v1.TRANSPORT_POLICY
    assert payload["authority"] == v1.AUTHORITY
    assert payload["upstream_path"] == v1.UPSTREAM_PATH
    assert payload["records_total"] == 2
    assert payload["records_filtered"] == 2
    assert payload["execution_grade"] is True
    assert payload["transport_metadata"]["response_envelope"] == TOP_LEVEL_RAW_ENVELOPE
    assert v1.fetch_zapi_raw_idx_stock_summary is original_fetch
    assert v1._zapi_inner_payload is original_inner


def test_full_fallback_restores_globals_after_certification_failure(tmp_path):
    original_fetch = v1.fetch_zapi_raw_idx_stock_summary
    original_inner = v1._zapi_inner_payload

    def direct_403(url, *, params, headers, timeout):
        return _Response(b"forbidden", status_code=403)

    # Provenance is valid but normalization must reject the empty full session.
    def zapi_empty(url, *, params, headers, timeout):
        return _Response(_top_level(data=[]))

    with pytest.raises(v1.OfficialOpenEvidenceError, match="RAW_DATA_MISSING"):
        capture_official_open_with_transport_fallback_v2(
            SESSION,
            output_root=tmp_path,
            zapi_api_key="secret",
            direct_get=direct_403,
            zapi_get=zapi_empty,
            timeout_seconds=1,
        )

    assert v1.fetch_zapi_raw_idx_stock_summary is original_fetch
    assert v1._zapi_inner_payload is original_inner
