import hashlib
import json

import pandas as pd
import pytest

from idx_trade.official_open_evidence_v1 import (
    AUTHORITY,
    DIRECT_TRANSPORT,
    FALLBACK_POLICY,
    FIELD_SEMANTICS,
    SCHEMA_VERSION,
    TRANSPORT_POLICY,
    UPSTREAM_PATH,
    ZAPI_RAW_TRANSPORT,
    ZAPI_RAW_URL,
    OfficialOpenEvidenceError,
    capture_official_open_with_transport_fallback,
    certify_official_open_raw_response,
    fetch_direct_idx_stock_summary,
    fetch_zapi_raw_idx_stock_summary,
    normalize_idx_stock_summary_payload,
)


def _payload(rows, **extra):
    return json.dumps(
        {
            "data": rows,
            "recordsTotal": len(rows),
            "recordsFiltered": len(rows),
            **extra,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def _zapi_payload(rows, *, provider="idx", path=UPSTREAM_PATH, **extra):
    inner = {
        "data": rows,
        "recordsTotal": len(rows),
        "recordsFiltered": len(rows),
        "provider": provider,
        "path": path,
        **extra,
    }
    return json.dumps(
        {"data": inner, "project": "finance:idx", "timestamp": "2026-08-22T00:00:00Z"},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


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
        {
            "StockCode": "ZERO",
            "Date": "2026-06-12T00:00:00",
            "OpenPrice": 0,
            "FirstTrade": 1000,
        },
    ]


class _Response:
    def __init__(self, content, status_code=200):
        self.content = content
        self.status_code = status_code


def test_normalization_preserves_openprice_and_firsttrade_as_distinct_fields():
    frame, counts = normalize_idx_stock_summary_payload(
        _payload(_rows()), expected_session_date="2026-06-12"
    )
    aadi = frame.set_index("ticker").loc["AADI"]
    zero = frame.set_index("ticker").loc["ZERO"]
    assert aadi.open_price == 8100
    assert aadi.first_trade == 8075
    assert zero.open_price == 0
    assert zero.first_trade == 1000
    assert counts == {
        "records_total": 3,
        "records_filtered": 3,
        "row_count": 3,
        "unique_ticker_count": 3,
    }


def test_normalization_unwraps_real_zapi_raw_data_envelope():
    frame, counts = normalize_idx_stock_summary_payload(
        _zapi_payload(_rows()), expected_session_date="2026-06-12"
    )
    assert counts["row_count"] == 3
    assert counts["records_total"] == 3
    assert frame.set_index("ticker").loc["BBCA", "open_price"] == 6000


def test_normalization_requires_complete_unfiltered_session():
    raw = json.dumps(
        {
            "data": _rows()[:2],
            "recordsTotal": 3,
            "recordsFiltered": 2,
        }
    ).encode()
    with pytest.raises(OfficialOpenEvidenceError, match="FULL_SESSION_COUNT_MISMATCH"):
        normalize_idx_stock_summary_payload(raw, expected_session_date="2026-06-12")


def test_certification_writes_manifest_last_with_hash_bound_source(tmp_path):
    raw = _payload(_rows())
    manifest_path = certify_official_open_raw_response(
        raw,
        session_date="2026-06-12",
        output_dir=tmp_path / "official_open" / "2026-06-12",
        transport_metadata={"http_status": 200},
    )
    payload = json.loads(manifest_path.read_text())
    raw_path = manifest_path.parent / payload["raw_artifact_path"]
    normalized_path = manifest_path.parent / payload["normalized_artifact_path"]

    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["authority"] == AUTHORITY
    assert payload["upstream_path"] == UPSTREAM_PATH
    assert payload["transport"] == DIRECT_TRANSPORT
    assert payload["transport_policy"] == TRANSPORT_POLICY
    assert payload["field_semantics"] == FIELD_SEMANTICS
    assert payload["fallback_policy"] == FALLBACK_POLICY
    assert payload["execution_grade"] is True
    assert payload["positive_openprice_count"] == 2
    assert payload["unavailable_openprice_count"] == 1
    assert hashlib.sha256(raw_path.read_bytes()).hexdigest() == payload["raw_artifact_sha256"]
    assert hashlib.sha256(normalized_path.read_bytes()).hexdigest() == payload["normalized_artifact_sha256"]

    frame = pd.read_parquet(normalized_path).set_index("ticker")
    assert frame.loc["ZERO", "open_price"] == 0
    assert frame.loc["ZERO", "first_trade"] == 1000


def test_certification_refuses_overwrite(tmp_path):
    raw = _payload(_rows())
    output = tmp_path / "session"
    certify_official_open_raw_response(raw, session_date="2026-06-12", output_dir=output)
    with pytest.raises(OfficialOpenEvidenceError, match="ALREADY_EXISTS"):
        certify_official_open_raw_response(raw, session_date="2026-06-12", output_dir=output)


def test_direct_fetch_uses_full_session_request_without_ticker_filter():
    observed = {}

    def fake_get(url, *, params, headers, timeout):
        observed.update(url=url, params=params, headers=headers, timeout=timeout)
        return _Response(_payload(_rows()))

    raw, meta = fetch_direct_idx_stock_summary(
        "2026-06-12", get=fake_get, timeout_seconds=7
    )
    assert raw == _payload(_rows())
    assert observed["params"] == {"date": "20260612", "start": 0, "length": 9999}
    assert "code" not in observed["params"]
    assert meta["transport"] == DIRECT_TRANSPORT
    assert meta["upstream_path"] == UPSTREAM_PATH
    assert meta["http_status"] == 200


def test_zapi_raw_fetch_uses_full_session_passthrough_without_code_filter():
    observed = {}

    def fake_get(url, *, params, headers, timeout):
        observed.update(url=url, params=params, headers=headers, timeout=timeout)
        return _Response(_zapi_payload(_rows()))

    raw, meta = fetch_zapi_raw_idx_stock_summary(
        "2026-06-12", api_key="secret-key", get=fake_get, timeout_seconds=7
    )
    assert raw == _zapi_payload(_rows())
    assert observed["url"] == ZAPI_RAW_URL
    assert observed["params"]["path"] == UPSTREAM_PATH
    assert observed["params"]["query"] == "date=20260612&start=0&length=9999"
    assert "code" not in observed["params"]["query"]
    assert observed["headers"]["x-api-key"] == "secret-key"
    assert "secret-key" not in json.dumps(meta)
    assert meta["transport"] == ZAPI_RAW_TRANSPORT
    assert meta["provider"] == "idx"
    assert meta["response_envelope"] == "data"


def test_zapi_raw_provenance_must_identify_idx_and_exact_upstream_path():
    def wrong_provider(url, *, params, headers, timeout):
        return _Response(_zapi_payload(_rows(), provider="other"))

    with pytest.raises(OfficialOpenEvidenceError, match="ZAPI_RAW_PROVIDER_MISMATCH"):
        fetch_zapi_raw_idx_stock_summary(
            "2026-06-12", api_key="key", get=wrong_provider
        )

    def wrong_path(url, *, params, headers, timeout):
        return _Response(_zapi_payload(_rows(), path="Other/GetThing"))

    with pytest.raises(OfficialOpenEvidenceError, match="ZAPI_RAW_PATH_MISMATCH"):
        fetch_zapi_raw_idx_stock_summary(
            "2026-06-12", api_key="key", get=wrong_path
        )


def test_transport_chain_prefers_direct_and_does_not_call_zapi_when_direct_works(tmp_path):
    zapi_calls = 0

    def direct_get(url, *, params, headers, timeout):
        return _Response(_payload(_rows()))

    def zapi_get(url, *, params, headers, timeout):
        nonlocal zapi_calls
        zapi_calls += 1
        raise AssertionError("Zapi must not be called when direct IDX succeeds")

    manifest = capture_official_open_with_transport_fallback(
        "2026-06-12",
        output_root=tmp_path,
        zapi_api_key="key",
        direct_get=direct_get,
        zapi_get=zapi_get,
    )
    payload = json.loads(manifest.read_text())
    assert payload["transport"] == DIRECT_TRANSPORT
    assert zapi_calls == 0


def test_transport_chain_falls_back_to_zapi_raw_on_direct_http_failure(tmp_path):
    direct_calls = 0
    zapi_calls = 0

    def direct_get(url, *, params, headers, timeout):
        nonlocal direct_calls
        direct_calls += 1
        return _Response(b"forbidden", status_code=403)

    def zapi_get(url, *, params, headers, timeout):
        nonlocal zapi_calls
        zapi_calls += 1
        return _Response(_zapi_payload(_rows()))

    manifest = capture_official_open_with_transport_fallback(
        "2026-06-12",
        output_root=tmp_path,
        zapi_api_key="key",
        direct_get=direct_get,
        zapi_get=zapi_get,
    )
    payload = json.loads(manifest.read_text())
    assert direct_calls == 1
    assert zapi_calls == 1
    assert payload["transport"] == ZAPI_RAW_TRANSPORT
    assert payload["transport_policy"] == TRANSPORT_POLICY
    assert payload["authority"] == AUTHORITY
    assert payload["upstream_path"] == UPSTREAM_PATH
    assert payload["fallback_policy"] == "NONE"
    assert payload["transport_metadata"]["response_envelope"] == "data"
    assert payload["transport_metadata"]["primary_transport_error"] == "OFFICIAL_OPEN_DIRECT_IDX_HTTP_403"


def test_transport_chain_does_not_hide_direct_schema_failure_with_zapi(tmp_path):
    zapi_calls = 0

    def direct_get(url, *, params, headers, timeout):
        raw = json.dumps(
            {"data": _rows()[:2], "recordsTotal": 3, "recordsFiltered": 2}
        ).encode()
        return _Response(raw)

    def zapi_get(url, *, params, headers, timeout):
        nonlocal zapi_calls
        zapi_calls += 1
        return _Response(_zapi_payload(_rows()))

    with pytest.raises(OfficialOpenEvidenceError, match="FULL_SESSION_COUNT_MISMATCH"):
        capture_official_open_with_transport_fallback(
            "2026-06-12",
            output_root=tmp_path,
            zapi_api_key="key",
            direct_get=direct_get,
            zapi_get=zapi_get,
        )
    assert zapi_calls == 0
